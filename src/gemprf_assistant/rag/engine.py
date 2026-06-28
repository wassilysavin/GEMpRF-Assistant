import os
import re
from dataclasses import asdict, replace
from pathlib import Path
from typing import Iterable

import numpy as np
from langchain_core.prompts import ChatPromptTemplate

from ..embeddings import EmbeddingBackend, build_embedding_backend
from ..knowledge_base import load_documents, parameter_map, source_map
from ..models import (
    AnswerResult,
    Citation,
    Chunk,
    EvidenceItem,
    ParameterSpec,
    QueryAnalysis,
    RetrievedChunk,
    SourceMeta,
)
from .chunking import ChunkingConfig, split_documents
from .knowledge_graph import ChunkTriple, KnowledgeGraphStore
from .parameters import ParameterMatcher
from .prompts import (
    HUMAN_PROMPT,
    HYDE_SYSTEM_PROMPT,
    INSUFFICIENT_EVIDENCE_MESSAGE,
    QUERY_REWRITE_SYSTEM_PROMPT,
    SYSTEM_PROMPT,
)
from .rerank import CrossEncoderReranker, build_reranker
from .retrieval import HierarchicalRetriever, RetrievalConfig
from .vector_store import WeaviateHierarchicalStore

try:
    from langchain_openai import ChatOpenAI
except Exception:  # pragma: no cover
    ChatOpenAI = None


_DEFAULT_TOP_K = 6
_RERANK_POOL_SIZE = 24
_MIN_EVIDENCE_SCORE = 1e-6
_MAX_CITATIONS = 6

_SUBJECT_PATTERNS = (
    re.compile(r"^\s*what\s+does\s+(.+?)\s+(?:stand\s+for|mean|denote|describe|do)\b", re.IGNORECASE),
    re.compile(r"^\s*what\s+is\s+meant\s+by\s+['\"]?(.+?)['\"]?(?:\s+in\b|\s+for\b|$)", re.IGNORECASE),
    re.compile(r"^\s*what\s+(?:kind|type|sort)\s+of\s+(.+?)(?:\s+(?:is|are|do|does)\b|$)", re.IGNORECASE),
    re.compile(r"^\s*what\s+(?:is|are)\s+(.+?)(?:\s+(?:in|for|of|on|at)\b|$)", re.IGNORECASE),
    re.compile(r"^\s*(?:define|explain|describe)\s+(.+?)(?:\s+(?:in|for|of|on|at)\b|$)", re.IGNORECASE),
)

# Tokens specific enough that bare retrieval beats HyDE expansion.
_RARE_ANCHOR_PATTERNS = (
    re.compile(r"\([^)]+\)"),                                # parenthesised: C(θ)
    re.compile(r"[θΘα-ωΑ-Ω∇∑∫]"),                            # Greek / math
    re.compile(r"\b[A-Za-z]{2,}-[A-Za-z]{2,}\b"),            # hyphenated: GEM-pRF
    re.compile(r"\b\w*[a-z][A-Z]\w*\b"),                     # mixed-case: pRF
)


# Strips bracketed source-id citations like [paper.full] or
# [website.config_generator GEM-pRF configuration generator] from LLM
# answers before they reach the user. 
_CITATION_BRACKET_RE = re.compile(r"\s*\[[a-z]+(?:\.[a-z0-9_-]+)+(?:\s[^\]]+)?\]")


def _strip_citations(text: str) -> str:
    """Remove residual '[source.id]' citations from an LLM answer and tidy the whitespace.
    """
    cleaned = _CITATION_BRACKET_RE.sub("", text)
    cleaned = re.sub(r"[ \t]{2,}", " ", cleaned)
    cleaned = re.sub(r"\s+([.,;:!?])", r"\1", cleaned)
    return cleaned.strip()


def _default_kg_path() -> Path:
    return Path(os.getenv("GEMPRF_ASSISTANT_KG_PATH", str(Path.cwd() / "data" / "kg.ttl")))


class GraphRagEngine:

    def __init__(
        self,
        embedding_backend: EmbeddingBackend | None = None,
        vector_store: WeaviateHierarchicalStore | None = None,
        knowledge_graph: KnowledgeGraphStore | None = None,
        retriever: HierarchicalRetriever | None = None,
        reranker: CrossEncoderReranker | None | bool = None,
        llm=None,
        chunking: ChunkingConfig | None = None,
        retrieval_config: RetrievalConfig | None = None,
        auto_ingest: bool = True,
    ) -> None:
    
        self.sources = source_map()
        self.parameters = parameter_map()
        self.documents = load_documents()
        self.embedding_backend = embedding_backend or build_embedding_backend()
        self.vector_store = vector_store or WeaviateHierarchicalStore()
        self.vector_store.ensure_schema()
        self.knowledge_graph = knowledge_graph or KnowledgeGraphStore(path=_default_kg_path())
        self.chunking_config = chunking or ChunkingConfig()
        self.retrieval_config = retrieval_config or RetrievalConfig()
        self.retriever = retriever or HierarchicalRetriever(
            self.vector_store, self.knowledge_graph, self.retrieval_config
        )
        self.reranker = self._resolve_reranker(reranker)
        self.parameter_matcher = ParameterMatcher.from_parameters(
            list(self.parameters.values()), self.embedding_backend.embed_texts
        )
        self.llm = None if llm is False else (llm if llm is not None else self._build_llm())

        if auto_ingest and not self._is_populated():
            self.ingest()
        elif not self.knowledge_graph.load():
            self.ingest()

    @staticmethod
    def _resolve_reranker(value):
        if value is False:
            return None
        if value is None:
            return build_reranker()
        return value

    def close(self) -> None:
        self.vector_store.close()

    def _is_populated(self) -> bool:
        try:
            return self.vector_store.count_chunks() > 0
        except Exception:
            return False

    def ingest(self) -> dict:
        """Rebuild the vector store and the knowledge graph from scratch.
        """
        source_to_parameters = self._source_to_parameter_ids()
        doc_pairs: list[tuple[SourceMeta, str]] = []
        for doc in self.documents:
            source_id = doc.metadata["source_id"]
            source = self.sources.get(source_id)
            if source is None:
                continue
            doc_pairs.append((source, doc.page_content))

        chunks, parents = split_documents(doc_pairs, source_to_parameters, config=self.chunking_config)

        _BREADCRUMB_TOKEN_LIMIT = 80
        chunks = [
            replace(c, text=f"{' > '.join(c.metadata.heading_path)}\n\n{c.text}")
            if c.metadata.heading_path and c.metadata.token_count < _BREADCRUMB_TOKEN_LIMIT
            else c
            for c in chunks
        ]

        # Optional synthetic-question augmentation for dense recall (stored text
        # unchanged); no-op unless HYPO_QUESTIONS=1.
        # For each chunk it generates hypothetical questions the chunk
        # answers and prepends them to the text that gets embedded, 
        # so the chunk's vector carries question-shaped phrasing. 
        from .augment import augment_texts
        embed_inputs = augment_texts([c.text for c in chunks])
        chunk_vectors = (
            self.embedding_backend.embed_texts(embed_inputs)
            if chunks
            else np.zeros((0, 1), dtype=np.float32)
        )
        parent_vectors = (
            self.embedding_backend.embed_texts([p.summary for p in parents])
            if parents
            else np.zeros((0, 1), dtype=np.float32)
        )

        self.vector_store.reset()
        self.vector_store.insert_chunks(chunks, chunk_vectors)
        self.vector_store.insert_sections(parents, parent_vectors)

        triples = [
            ChunkTriple(
                chunk_id=c.metadata.chunk_id,
                source_id=c.metadata.source_id,
                section_id=c.metadata.parent_id,
                parameter_ids=c.metadata.parameter_ids,
            )
            for c in chunks
        ]
        self.knowledge_graph.build(
            sources=self.sources.values(),
            parameters=self.parameters.values(),
            sections=parents,
            chunks=triples,
        )
        self.knowledge_graph.save()
        return {
            "chunks": len(chunks),
            "sections": len(parents),
            "parameters": len(self.parameters),
            "sources": len(self.sources),
        }

    def ask(self, question: str, top_k: int = _DEFAULT_TOP_K) -> AnswerResult:
        analysis = self.analyze(question, top_k=top_k)
        return AnswerResult(
            answer=analysis.answer,
            status=analysis.status,
            matched_parameters=analysis.matched_parameter_labels,
            citations=analysis.citations,
            used_llm=analysis.used_llm,
        )

    def ask_dict(self, question: str, top_k: int = _DEFAULT_TOP_K) -> dict:
        result = self.analyze(question, top_k=top_k)
        return {
            "answer": result.answer,
            "status": result.status,
            "matched_parameters": result.matched_parameter_labels,
            "matched_parameter_ids": result.matched_parameter_ids,
            "evidence": [asdict(item) for item in result.evidence],
            "citations": [asdict(citation) for citation in result.citations],
            "used_llm": result.used_llm,
            "rerank_used": result.rerank_used,
            "rewritten_query": result.rewritten_query,
        }

    def analyze(self, question: str, top_k: int = _DEFAULT_TOP_K) -> QueryAnalysis:
        rewritten = self._hyde_query(question) or self._rewrite_query(question)
        retrieval_query = rewritten or question

        # Use the query-side embedding (applies the model's query prefix for
        # instruction-tuned embedders like e5; a no-op for plain models).
        _embed_q = getattr(self.embedding_backend, "embed_query", self.embedding_backend.embed_texts)
        question_embedding = _embed_q([retrieval_query])[0]

        matched_pairs = self.parameter_matcher.match_with_scores(question_embedding)
        matched_specs = [spec for spec, _ in matched_pairs]
        matched_parameter_scores = {spec.id: float(score) for spec, score in matched_pairs}

        first_pass = self.retriever.retrieve(
            question=retrieval_query,
            question_vector=question_embedding,
            matched_parameter_ids=[spec.id for spec in matched_specs],
            matched_parameter_scores=matched_parameter_scores,
            limit=_RERANK_POOL_SIZE,
        )

        rerank_used = False
        if self.reranker is not None and first_pass:
            first_pass, rerank_used = self.reranker.rerank(retrieval_query, first_pass, top_k=_RERANK_POOL_SIZE)

        evidence = self._select_evidence(first_pass, top_k)
        citations = self._build_citations(evidence, matched_specs)
        if not self._has_supporting_evidence(evidence, rerank_used):
            return QueryAnalysis(
                question=question,
                answer=INSUFFICIENT_EVIDENCE_MESSAGE,
                status="insufficient_evidence",
                matched_parameter_ids=[spec.id for spec in matched_specs],
                matched_parameter_labels=[spec.label for spec in matched_specs],
                evidence=self._to_evidence_items(evidence),
                citations=citations,
                used_llm=False,
                rerank_used=rerank_used,
                rewritten_query=rewritten,
            )

        answer, used_llm = self._generate_answer(question, matched_specs, evidence, rewritten)
        return QueryAnalysis(
            question=question,
            answer=answer,
            status="supported",
            matched_parameter_ids=[spec.id for spec in matched_specs],
            matched_parameter_labels=[spec.label for spec in matched_specs],
            evidence=self._to_evidence_items(evidence),
            citations=citations,
            used_llm=used_llm,
            rerank_used=rerank_used,
            rewritten_query=rewritten,
        )

    def describe(self) -> dict:
        return {
            "engine": "graph-rag",
            "num_sources": len(self.sources),
            "num_parameters": len(self.parameters),
            "num_chunks": self._safe(lambda: self.vector_store.count_chunks()),
            "num_sections": self._safe(lambda: self.vector_store.count_sections()),
            "embedding_backend": self.embedding_backend.backend_name,
            "llm_enabled": self.llm is not None,
            "reranker": self._reranker_status(),
            "kg_path": str(self.knowledge_graph.path) if self.knowledge_graph.path else None,
        }

    @staticmethod
    def _safe(fn):
        try:
            return fn()
        except Exception:
            return 0

    def _reranker_status(self) -> dict:
        if self.reranker is None:
            return {"enabled": False}
        return {
            "enabled": True,
            "model": self.reranker.model_name,
            "available": self.reranker.available,
        }

    def _source_to_parameter_ids(self) -> dict[str, tuple[str, ...]]:
        """Build the source_id -> (parameter_id, ...) inverse index used during ingest.
        """
        tags: dict[str, list[str]] = {sid: [] for sid in self.sources}
        for parameter in self.parameters.values():
            for sid in (*parameter.source_ids, *parameter.code_source_ids):
                if sid in tags:
                    tags[sid].append(parameter.id)
        return {sid: tuple(ids) for sid, ids in tags.items()}

    def _select_evidence(self, candidates: list[RetrievedChunk], top_k: int) -> list[RetrievedChunk]:
        return candidates[:top_k]

    @staticmethod
    def _has_supporting_evidence(evidence: list[RetrievedChunk], rerank_used: bool) -> bool:
        if not evidence:
            return False
        return max(r.score for r in evidence) >= _MIN_EVIDENCE_SCORE

    def _to_evidence_items(self, evidence: list[RetrievedChunk]) -> list[EvidenceItem]:
        return [
            EvidenceItem(
                source_id=r.chunk.metadata.source_id,
                score=float(r.rerank_score) if r.rerank_score is not None else float(r.score),
                text=r.chunk.text,
                heading_path=r.chunk.metadata.heading_path,
                parameter_ids=r.chunk.metadata.parameter_ids,
            )
            for r in evidence
        ]

    def _build_citations(
        self,
        evidence: list[RetrievedChunk],
        matched_specs: list[ParameterSpec],
    ) -> list[Citation]:
        """Build the citation list from retrieved chunks plus matched parameters.
        """
        seen: set[tuple[str, tuple[str, ...]]] = set()
        citations: list[Citation] = []
        for r in evidence:
            sid = r.chunk.metadata.source_id
            heading = r.chunk.metadata.heading_path
            key = (sid, heading)
            if key in seen or sid not in self.sources:
                continue
            source = self.sources[sid]
            citations.append(
                Citation(
                    id=source.id,
                    title=source.title,
                    kind=source.kind,
                    url=source.url,
                    local_path=source.local_path,
                    heading_path=heading,
                )
            )
            seen.add(key)
            if len(citations) >= _MAX_CITATIONS:
                return citations

        for parameter in matched_specs:
            for sid in (*parameter.source_ids, *parameter.code_source_ids):
                if sid not in self.sources:
                    continue
                key = (sid, ())
                if key in seen:
                    continue
                source = self.sources[sid]
                citations.append(
                    Citation(
                        id=source.id,
                        title=source.title,
                        kind=source.kind,
                        url=source.url,
                        local_path=source.local_path,
                    )
                )
                seen.add(key)
                if len(citations) >= _MAX_CITATIONS:
                    return citations
        return citations

    def _build_llm(self):
        if ChatOpenAI is None:
            return None
        provider = os.getenv("GEMPRF_ASSISTANT_LLM_PROVIDER", "").strip().lower()
        has_openai = bool(os.getenv("OPENAI_API_KEY"))
        has_xai = bool(os.getenv("XAI_API_KEY"))

        if provider == "ollama" or (not provider and not has_openai and not has_xai):
            return ChatOpenAI(
                model=os.getenv("GEMPRF_ASSISTANT_OLLAMA_MODEL", "mistral-nemo:12b"),
                api_key=os.getenv("GEMPRF_ASSISTANT_OLLAMA_API_KEY", "ollama"),
                base_url=os.getenv("GEMPRF_ASSISTANT_OLLAMA_BASE_URL", "http://localhost:11434/v1"),
                temperature=0,
                max_tokens=int(os.getenv("GEMPRF_ASSISTANT_OLLAMA_MAX_TOKENS", "768")),
            )
        if provider == "xai" or (not provider and has_xai and not has_openai):
            if not has_xai:
                return None
            return ChatOpenAI(
                model=os.getenv("GEMPRF_ASSISTANT_XAI_MODEL", "grok-4.20-reasoning"),
                api_key=os.getenv("XAI_API_KEY"),
                base_url=os.getenv("GEMPRF_ASSISTANT_XAI_BASE_URL", "https://api.x.ai/v1"),
                temperature=0,
            )
        if not has_openai:
            return None
        return ChatOpenAI(model=os.getenv("GEMPRF_ASSISTANT_MODEL", "gpt-4o-mini"), temperature=0)

    @staticmethod
    def _extract_subject(question: str) -> str | None:
        """Pull out the noun phrase a definitional question is about (the X in "what is X").
        """
        q = question.strip().rstrip("?.!")
        for pattern in _SUBJECT_PATTERNS:
            m = pattern.match(q)
            if m:
                return m.group(1).strip(" '\"")
        return None

    def _subject_has_rare_anchor(self, subject: str) -> bool:
        """True if 'subject' carries a token specific enough that HyDE expansion would dilute retrieval.
        """
        for pattern in _RARE_ANCHOR_PATTERNS:
            if pattern.search(subject):
                return True
        s_lower = subject.lower()
        for spec in self.parameters.values():
            for name in (spec.id, spec.label, *spec.aliases):
                if not name or len(name) < 3:
                    continue
                if re.search(rf"\b{re.escape(name.lower())}\b", s_lower):
                    return True
        return False

    def _hyde_query(self, question: str) -> str | None:
        """HyDE expansion
        """
        if os.getenv("GEMPRF_ASSISTANT_HYDE", "0").strip() != "1":
            return None
        if self.llm is None:
            return None
        # Rare-anchor gate
        subject = self._extract_subject(question) or question
        if self._subject_has_rare_anchor(subject):
            return None
        try:
            prompt = ChatPromptTemplate.from_messages(
                [("system", HYDE_SYSTEM_PROMPT), ("human", "{question}")]
            )
            chain = prompt | self.llm
            response = chain.invoke({"question": question})
            hypothetical = str(response.content).strip()
        except Exception:
            return None
        hypothetical = hypothetical.strip("\"'`")
        # < 20 chars -> almost certainly a refusal/empty completion.
        if len(hypothetical) < 20:
            return None
        return f"{question.strip()} {hypothetical}"

    def _rewrite_query(self, question: str) -> str | None:
        """Append LLM-suggested domain keywords to the original question for retrieval only.
        """
        if os.getenv("GEMPRF_ASSISTANT_QUERY_REWRITE", "1").strip() == "0":
            return None
        if self.llm is None:
            return None
        try:
            prompt = ChatPromptTemplate.from_messages(
                [("system", QUERY_REWRITE_SYSTEM_PROMPT), ("human", "{question}")]
            )
            chain = prompt | self.llm
            response = chain.invoke({"question": question})
            keywords_raw = str(response.content).strip()
        except Exception:
            return None
        keywords_raw = keywords_raw.strip("\"'`")
        parts = re.split(r"[,\n]", keywords_raw)
        keywords: list[str] = []
        seen: set[str] = set()
        for raw in parts:
            kw = raw.strip().lstrip("-•*").strip().strip("\"'`")
            if not kw or len(kw) > 80 or kw.endswith("?"):
                continue
            lower = kw.lower()
            if lower in seen or lower in question.lower():
                continue
            seen.add(lower)
            keywords.append(kw)
        if not keywords:
            return None
        return f"{question.strip()} {' '.join(keywords)}"

    def _generate_answer(
        self,
        question: str,
        matched_specs: list[ParameterSpec],
        evidence: list[RetrievedChunk],
        rewritten_query: str | None = None,
    ) -> tuple[str, bool]:
        if self.llm is not None:
            import time as _time
            attempts = int(os.getenv("GEMPRF_ASSISTANT_LLM_RETRIES", "3"))
            last_exc = None
            for i in range(attempts):
                try:
                    answer = self._generate_with_llm(question, matched_specs, evidence, rewritten_query)
                    if not answer.startswith("INSUFFICIENT_EVIDENCE:"):
                        return _strip_citations(answer), True
                    return INSUFFICIENT_EVIDENCE_MESSAGE, False
                except Exception as exc:  # usually transient (rate limit / timeout)
                    last_exc = exc
                    if i < attempts - 1:
                        _time.sleep(1.5 * (i + 1))
            # Degrade to extractive only after retries; log it so silent
            # fallbacks (Finding H) stay visible instead of looking like real answers.
            import sys as _sys
            print(f"[_generate_answer] LLM failed after {attempts} attempts: "
                  f"{type(last_exc).__name__}: {str(last_exc)[:160]}", file=_sys.stderr, flush=True)
        return self._extractive(evidence), False

    def _generate_with_llm(
        self,
        question: str,
        matched_specs: list[ParameterSpec],
        evidence: list[RetrievedChunk],
        rewritten_query: str | None = None,
    ) -> str:
        prompt = ChatPromptTemplate.from_messages([("system", SYSTEM_PROMPT), ("human", HUMAN_PROMPT)])
        chain = prompt | self.llm
        response = chain.invoke({
            "question": question,
            "expanded_query_context": rewritten_query or "- none",
            "parameter_context": self._parameter_context(matched_specs),
            "evidence_context": self._evidence_context(evidence),
        })
        return str(response.content).strip()

    @staticmethod
    def _parameter_context(matched_specs: list[ParameterSpec]) -> str:
        """Render matched parameters as a bullet list for the human prompt.
        """
        if not matched_specs:
            return "- none"
        return "\n".join(
            f"- {p.label} ({p.xml_path}): {p.summary} {p.significance}"
            for p in matched_specs
        )

    @staticmethod
    def _evidence_context(evidence: list[RetrievedChunk]) -> str:
        """Render retrieved evidence as [source_id heading_path] text blocks.
        """
        if not evidence:
            return "- none"
        return "\n\n".join(
            f"[{r.chunk.metadata.source_id} {' > '.join(r.chunk.metadata.heading_path)}] {r.chunk.text}"
            for r in evidence
        )

    @staticmethod
    def _extractive(evidence: list[RetrievedChunk]) -> str:
        """LLM-free fallback: stitch up to 3 sentences from the top-3 chunks plus a disclaimer.
        """
        if not evidence:
            return INSUFFICIENT_EVIDENCE_MESSAGE
        sentences: list[str] = []
        seen: set[str] = set()
        for r in evidence[:3]:
            for sentence in re.split(r"(?<=[.!?])\s+", r.chunk.text):
                stripped = sentence.strip()
                if len(stripped) < 30 or stripped in seen:
                    continue
                sentences.append(stripped)
                seen.add(stripped)
                if len(sentences) >= 3:
                    break
            if len(sentences) >= 3:
                break
        if not sentences:
            return INSUFFICIENT_EVIDENCE_MESSAGE
        sentences.append("This summary is constrained to the allowed GEM-pRF sources.")
        return " ".join(sentences)
