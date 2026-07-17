"""GraphRagEngine: wires the components and orchestrates the online stages
(contextualize -> rewrite -> retrieve -> rerank -> assemble -> generate | fallbacks).
Stage logic lives in the sibling modules; the offline build lives in kb.ingest."""
from dataclasses import asdict
from pathlib import Path

from .. import tracing
from ..config import get_settings
from ..kb.chunking import ChunkingConfig
from ..kb.ingest import build_index
from ..kb.knowledge_graph import KnowledgeGraphStore
from ..kb.loader import load_documents, parameter_map, source_map
from ..models import (
    AnswerResult,
    AnswerStatus,
    FallbackKind,
    QueryAnalysis,
)
from ..providers import EmbeddingBackend, build_chat_llm, build_embedding_backend
from ..store.weaviate import WeaviateHierarchicalStore
from . import assemble, fallbacks, generate, rewrite
from .parameters import ParameterMatcher
from .prompts import INSUFFICIENT_EVIDENCE_MESSAGE
from .rerank import CrossEncoderReranker, build_reranker
from .retrieval import HierarchicalRetriever, RetrievalConfig

_DEFAULT_TOP_K = 6


def _default_kg_path() -> Path:
    return get_settings().resolved_kg_path()


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
        self._documents = None
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
        self.llm = None if llm is False else (llm if llm is not None else build_chat_llm(temperature=0))
        self.last_trace_url: str | None = None  # Langfuse URL of the most recent analyze() trace

        if auto_ingest and not self._is_populated():
            self.ingest()
        elif not self.knowledge_graph.load():
            self.ingest()
        else:
            from ..kb.manifest import verify_compatible

            verify_compatible(self.embedding_backend.backend_name)

    @property
    def documents(self):
        """Corpus documents, loaded lazily: only ingest needs them, so a prebuilt index runs without the corpus."""
        if self._documents is None:
            self._documents = load_documents()
        return self._documents

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
        """Rebuild the vector store and the knowledge graph from scratch (delegates to kb.ingest)."""
        return build_index(
            documents=self.documents,
            sources=self.sources,
            parameters=self.parameters,
            embedding_backend=self.embedding_backend,
            vector_store=self.vector_store,
            knowledge_graph=self.knowledge_graph,
            chunking_config=self.chunking_config,
        )

    def answer(self, question: str, top_k: int = _DEFAULT_TOP_K, history=None,
               clarify: bool = False, input_fn=input, output_fn=print) -> QueryAnalysis:
        """Single entrypoint for every caller: the core pipeline, optionally wrapped in the clarification intake."""
        if not clarify:
            return self.analyze(question, top_k=top_k, history=history)
        from .clarify import answer_with_clarification

        return answer_with_clarification(self, question, input_fn=input_fn, output_fn=output_fn, history=history)

    def ask(self, question: str, top_k: int = _DEFAULT_TOP_K, history=None) -> AnswerResult:
        analysis = self.answer(question, top_k=top_k, history=history)
        return AnswerResult(
            answer=analysis.answer,
            status=analysis.status,
            matched_parameters=analysis.matched_parameter_labels,
            citations=analysis.citations,
            used_llm=analysis.used_llm,
            fallback=analysis.fallback,
        )

    def ask_dict(self, question: str, top_k: int = _DEFAULT_TOP_K, history=None) -> dict:
        result = self.answer(question, top_k=top_k, history=history)
        return {
            "answer": result.answer,
            "status": getattr(result.status, "value", result.status),
            "fallback": getattr(result.fallback, "value", result.fallback),
            "matched_parameters": result.matched_parameter_labels,
            "matched_parameter_ids": result.matched_parameter_ids,
            "evidence": [asdict(item) for item in result.evidence],
            "citations": [asdict(citation) for citation in result.citations],
            "used_llm": result.used_llm,
            "rerank_used": result.rerank_used,
            "rewritten_query": result.rewritten_query,
            "trace_url": self.last_trace_url,
        }

    def analyze(self, question: str, top_k: int = _DEFAULT_TOP_K, history=None) -> QueryAnalysis:
        """Trace-wrapped pipeline: each step of _analyze lands as a Langfuse span (no-op when tracing is off)."""
        with tracing.span("analyze", input={"question": question, "top_k": top_k}) as root:
            analysis = self._analyze(question, top_k=top_k, history=history)
            root.update(output={"status": analysis.status, "used_llm": analysis.used_llm, "answer": analysis.answer})
            self.last_trace_url = tracing.current_trace_url()
        return analysis

    def _analyze(self, question: str, top_k: int = _DEFAULT_TOP_K, history=None) -> QueryAnalysis:
        # Resolve follow-ups ("it", "that value", "what value in my case?") into a standalone query
        # against the session history before retrieval; the LLM condense returns it unchanged if
        # already self-contained.
        with tracing.span("contextualize", input={"question": question}) as sp:
            contextual = history.contextualize(question, self.llm) if history else question
            is_followup = history is not None and rewrite.is_followup_rewrite(question, contextual)
            contextualized = contextual if is_followup else None
            sp.update(output={"contextual": contextual, "is_followup": is_followup})
        with tracing.span("expand_query", input={"question": contextual}) as sp:
            rewritten = (
                rewrite.hyde_query(self.llm, contextual, self.parameters)
                or rewrite.rewrite_query(self.llm, contextual, self.parameters)
            )
            expanded = rewritten is not None
            if rewritten is None and is_followup:
                rewritten = contextual
            retrieval_query = rewritten or question
            sp.update(output={
                "retrieval_query": retrieval_query,
                "expanded": expanded,
                "skip_reason": None if expanded else rewrite.expansion_skip_reason(self.llm, contextual, self.parameters),
            })

        # Use the query-side embedding (applies the model's query prefix for
        # instruction-tuned embedders like e5; a no-op for plain models).
        _embed_q = getattr(self.embedding_backend, "embed_query", self.embedding_backend.embed_texts)
        question_embedding = _embed_q([retrieval_query])[0]

        with tracing.span("match_parameters") as sp:
            matched_pairs = self.parameter_matcher.match_with_scores(question_embedding)
            matched_specs = [spec for spec, _ in matched_pairs]
            matched_parameter_scores = {spec.id: float(score) for spec, score in matched_pairs}
            sp.update(output=matched_parameter_scores)

        rerank_pool = get_settings().rerank_pool
        with tracing.span(
            "retrieve", as_type="retriever", input={"query": retrieval_query, "limit": rerank_pool}
        ) as sp:
            first_pass = self.retriever.retrieve(
                question=retrieval_query,
                question_vector=question_embedding,
                matched_parameter_ids=[spec.id for spec in matched_specs],
                matched_parameter_scores=matched_parameter_scores,
                limit=rerank_pool,
            )
            sp.update(output=assemble.chunk_summaries(first_pass))

        rerank_used = False
        if self.reranker is not None and first_pass:
            with tracing.span("rerank", input={"query": retrieval_query, "pool": len(first_pass)}) as sp:
                first_pass, rerank_used = self.reranker.rerank(retrieval_query, first_pass, top_k=rerank_pool)
                sp.update(output={"rerank_used": rerank_used, "ranking": assemble.chunk_summaries(first_pass)})

        with tracing.span("select_evidence", input={"top_k": top_k}) as sp:
            evidence = assemble.select_evidence(first_pass, top_k)
            # Guarantee a confidently-matched parameter's curated code reaches the LLM: organic
            # retrieval ranks code chunks inconsistently across phrasings. Ranked on the resolved
            # question (contextual), so the logic body wins over stubs like a bare __init__.
            evidence = assemble.inject_code_evidence(
                evidence, matched_specs, matched_parameter_scores, contextual,
                sources=self.sources,
                embedding_backend=self.embedding_backend,
                vector_store=self.vector_store,
                alpha=self.retriever.config.hybrid_alpha,
            )
            sp.update(output=assemble.chunk_summaries(evidence))
        citations = assemble.build_citations(evidence, matched_specs, self.sources)
        if not assemble.has_supporting_evidence(evidence, rerank_used):
            # Retrieval found nothing, but a matched parameter may carry corpus-grounded
            # relations; answer deterministically from those rather than refusing outright.
            with tracing.span("relation_fallback", input={"trigger": "no_supporting_evidence"}) as sp:
                fallback_result = fallbacks.relation_fallback(question, matched_specs, matched_parameter_scores)
                sp.update(output={"answered": fallback_result is not None})
            if fallback_result is not None:
                fallback_answer, fallback_kind = fallback_result
                return QueryAnalysis(
                    question=question,
                    answer=fallback_answer,
                    status=AnswerStatus.DEGRADED,
                    matched_parameter_ids=[spec.id for spec in matched_specs],
                    matched_parameter_labels=[spec.label for spec in matched_specs],
                    evidence=assemble.to_evidence_items(evidence),
                    citations=citations,
                    used_llm=False,
                    rerank_used=rerank_used,
                    rewritten_query=rewritten,
                    contextualized_question=contextualized,
                    fallback=fallback_kind,
                )
            return QueryAnalysis(
                question=question,
                answer=INSUFFICIENT_EVIDENCE_MESSAGE,
                status=AnswerStatus.INSUFFICIENT_EVIDENCE,
                matched_parameter_ids=[spec.id for spec in matched_specs],
                matched_parameter_labels=[spec.label for spec in matched_specs],
                evidence=assemble.to_evidence_items(evidence),
                citations=citations,
                used_llm=False,
                rerank_used=rerank_used,
                rewritten_query=rewritten,
                contextualized_question=contextualized,
            )

        # History feeds the answer prompt only for genuine follow-ups: a self-contained question needs no
        # reference resolution, and prior (often refusal-laden) turns would only bias the fresh answer.
        answer_history = history if is_followup else None
        with tracing.span("generate_answer", input={"question": question}) as sp:
            answer, used_llm, fallback = generate.generate_answer(
                self.llm, question, matched_specs, evidence, rewritten, answer_history
            )
            sp.update(output={"answer": answer, "used_llm": used_llm})
        # Refusal-only fallback: if the LLM refused, back off to corpus-grounded relations
        # rather than perturbing answers it could already ground from retrieval.
        if answer == INSUFFICIENT_EVIDENCE_MESSAGE:
            with tracing.span("relation_fallback", input={"trigger": "llm_refusal"}) as sp:
                fallback_result = fallbacks.relation_fallback(question, matched_specs, matched_parameter_scores)
                sp.update(output={"answered": fallback_result is not None})
            if fallback_result is not None:
                answer, fallback = fallback_result
                used_llm = False
        if answer == INSUFFICIENT_EVIDENCE_MESSAGE:
            status = AnswerStatus.INSUFFICIENT_EVIDENCE
        elif fallback is not FallbackKind.NONE:
            status = AnswerStatus.DEGRADED
        else:
            status = AnswerStatus.SUPPORTED
        return QueryAnalysis(
            question=question,
            answer=answer,
            status=status,
            matched_parameter_ids=[spec.id for spec in matched_specs],
            matched_parameter_labels=[spec.label for spec in matched_specs],
            evidence=assemble.to_evidence_items(evidence),
            citations=citations,
            used_llm=used_llm,
            rerank_used=rerank_used,
            rewritten_query=rewritten,
            contextualized_question=contextualized,
            fallback=fallback,
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
