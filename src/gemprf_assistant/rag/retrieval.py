import os
from collections import defaultdict
from dataclasses import dataclass

import numpy as np

from ..models import RetrievedChunk
from .knowledge_graph import KnowledgeGraphStore
from .vector_store import ChunkHit, SectionHit, WeaviateHierarchicalStore


# RRF constant
_RRF_K = 60

# Discount on 1-hop graph neighbors vs. directly-matched seeds.
_NEIGHBOR_DISCOUNT = 0.5


def _diverse_topk(
    ordered: list[RetrievedChunk],
    limit: int,
    cap: int | None,
) -> list[RetrievedChunk]:
    """
    Reorders / filters an already score-sorted list of RetrievedChunk so the final list has length at most limit, 
    but no single source_id contributes more than cap hits 
    """
    if cap is None or cap <= 0:
        return ordered[:limit]
    selected: list[RetrievedChunk] = []
    by_source: defaultdict[str, int] = defaultdict(int)
    overflow: list[RetrievedChunk] = []
    for r in ordered:
        sid = r.chunk.metadata.source_id
        if by_source[sid] >= cap:
            overflow.append(r)
            continue
        selected.append(r)
        by_source[sid] += 1
        if len(selected) >= limit:
            break
    if len(selected) < limit:
        for r in overflow:
            if len(selected) >= limit:
                break
            selected.append(r)
    return selected


def _rrf_combine(rankings: list[list[str]], k: int = _RRF_K) -> dict[str, float]:
    """Reciprocal Rank Fusion over 'rankings'
    """
    score: defaultdict[str, float] = defaultdict(float)
    for ranking in rankings:
        for rank, cid in enumerate(ranking, 1):
            score[cid] += 1.0 / (k + rank)
    return score


def _default_alpha() -> float:
    """Read the env-tunable hybrid alpha for Weaviate's vector/BM25 blend.
    """
    raw = os.getenv("GEMPRF_ASSISTANT_HYBRID_ALPHA", "0.5")
    try:
        value = float(raw)
    except ValueError:
        return 0.5
    return max(0.0, min(1.0, value))


@dataclass(frozen=True)
class RetrievalConfig:
    parent_top_n: int = 6
    child_per_parent: int = 6
    backfill_children: int = 12
    graph_boost: float = 0.08             
    parent_score_weight: float = 0.25    
    hybrid_alpha: float = -1.0
    rrf_k: int = _RRF_K
    max_per_source: int | None = 3


class HierarchicalRetriever:
    """Four-step recall pipeline (parent -> constrained children -> backfill -> graph).
    """

    def __init__(
        self,
        vector_store: WeaviateHierarchicalStore,
        knowledge_graph: KnowledgeGraphStore,
        config: RetrievalConfig | None = None,
    ) -> None:
        self.vector_store = vector_store
        self.knowledge_graph = knowledge_graph
        cfg = config or RetrievalConfig()
        if cfg.hybrid_alpha < 0:
            cfg = RetrievalConfig(
                parent_top_n=cfg.parent_top_n,
                child_per_parent=cfg.child_per_parent,
                backfill_children=cfg.backfill_children,
                graph_boost=cfg.graph_boost,
                parent_score_weight=cfg.parent_score_weight,
                hybrid_alpha=_default_alpha(),
                rrf_k=cfg.rrf_k,
                max_per_source=cfg.max_per_source,
            )
        self.config = cfg

    def retrieve(
        self,
        question: str,
        question_vector: np.ndarray,
        matched_parameter_ids: list[str],
        limit: int,
        source_kinds: tuple[str, ...] | None = None,
        matched_parameter_scores: dict[str, float] | None = None,
    ) -> list[RetrievedChunk]:
        """Run the full four-step recall and return the top 'limit' chunks after RRF fusion.
        """
        # 1. Parent recall (hybrid: BM25 catches unique header tokens).
        parent_hits = self.vector_store.hybrid_sections(
            query=question,
            vector=question_vector,
            limit=self.config.parent_top_n,
            alpha=self.config.hybrid_alpha,
            source_kinds=source_kinds,
        )
        parent_score: dict[str, float] = {p.section_id: float(p.score) for p in parent_hits}

        # 2. Children filtered to the recalled parents.
        constrained_children: list[ChunkHit] = []
        if parent_hits:
            constrained_children = self.vector_store.hybrid_chunks(
                query=question,
                vector=question_vector,
                limit=self.config.parent_top_n * self.config.child_per_parent,
                alpha=self.config.hybrid_alpha,
                parent_ids=tuple(p.section_id for p in parent_hits),
                source_kinds=source_kinds,
            )

        # 3. Unconstrained backfill — catches strong chunks in weak parents.
        backfill = self.vector_store.hybrid_chunks(
            query=question,
            vector=question_vector,
            limit=self.config.backfill_children,
            alpha=self.config.hybrid_alpha,
            source_kinds=source_kinds,
        )

        # 4. Graph signal - chunks already carry parameter_ids tags, so we
        # score against 'expanded' directly without a SPARQL lookup.
        seeds = set(matched_parameter_ids)
        expanded = self.knowledge_graph.expand_parameters(matched_parameter_ids) if matched_parameter_ids else set()
        param_scores = matched_parameter_scores or {}

        pool: dict[str, ChunkHit] = {}
        for hit in (*constrained_children, *backfill):
            cid = hit.chunk.metadata.chunk_id
            if cid not in pool or pool[cid].score < hit.score:
                pool[cid] = hit

        constrained_ids = [h.chunk.metadata.chunk_id for h in constrained_children]
        backfill_ids = [h.chunk.metadata.chunk_id for h in backfill]

        # Parent-projected ranking: pool chunks ordered by their parent's
        # hybrid score (chunks whose parent didn't make top_n are excluded).
        parent_projected_ids = [
            cid
            for cid, _hit in sorted(
                pool.items(),
                key=lambda kv: parent_score.get(kv[1].chunk.metadata.parent_id or "", 0.0),
                reverse=True,
            )
            if (pool[cid].chunk.metadata.parent_id or "") in parent_score
        ]

        # Graph ranking: weighted sum (seeds full, neighbors discounted).
        # Chunks with zero graph score are excluded so missing matches don't
        # pollute the ranking.
        def _graph_score(hit: ChunkHit) -> float:
            """Per-chunk score from the matched-parameter graph signal.
            """
            if not expanded:
                return 0.0
            return sum(
                param_scores.get(pid, 0.0) * (1.0 if pid in seeds else _NEIGHBOR_DISCOUNT)
                for pid in hit.chunk.metadata.parameter_ids
                if pid in expanded
            )

        graph_scored = [(cid, _graph_score(hit)) for cid, hit in pool.items()]
        graph_ranked_ids = [
            cid
            for cid, gs in sorted(graph_scored, key=lambda kv: kv[1], reverse=True)
            if gs > 0
        ]

        rrf_score = _rrf_combine(
            [constrained_ids, backfill_ids, parent_projected_ids, graph_ranked_ids],
            k=self.config.rrf_k,
        )

        # Build full sorted list first so _diverse_topk has visibility for
        # overflow backfill.
        ordered_ids = sorted(rrf_score, key=lambda c: rrf_score[c], reverse=True)
        ranked: list[RetrievedChunk] = []
        for cid in ordered_ids:
            hit = pool[cid]
            parent_id = hit.chunk.metadata.parent_id
            ranked.append(
                RetrievedChunk(
                    chunk=hit.chunk,
                    score=rrf_score[cid],
                    parent_score=parent_score.get(parent_id, 0.0) if parent_id and parent_id in parent_score else None,
                )
            )
        return _diverse_topk(ranked, limit, self.config.max_per_source)

    def parent_hits(
        self,
        question: str,
        question_vector: np.ndarray,
        limit: int | None = None,
        source_kinds: tuple[str, ...] | None = None,
    ) -> list[SectionHit]:
        return self.vector_store.hybrid_sections(
            query=question,
            vector=question_vector,
            limit=limit or self.config.parent_top_n,
            alpha=self.config.hybrid_alpha,
            source_kinds=source_kinds,
        )
