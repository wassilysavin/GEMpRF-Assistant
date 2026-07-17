from collections import defaultdict
from dataclasses import dataclass

import numpy as np

from ..config import get_settings
from ..models import RetrievedChunk
from .knowledge_graph import KnowledgeGraphStore
from .vector_store import ChunkHit, SectionHit, WeaviateHierarchicalStore


def _diverse_topk(
    ordered: list[RetrievedChunk],
    limit: int,
    cap: int | None,
) -> list[RetrievedChunk]:
    """Trim a score-sorted list to `limit`, capping hits per source_id at `cap`."""
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


def _minmax(hits: list[ChunkHit]) -> dict[str, float]:
    """Min-max normalise an arm's hybrid scores onto [0, 1] (keyed by chunk id),
    keeping the relevance-gap magnitude that plain rank fusion discards."""
    if not hits:
        return {}
    scores = [h.score for h in hits]
    lo, hi = min(scores), max(scores)
    rng = hi - lo
    if rng <= 0:
        return {h.chunk.metadata.chunk_id: 1.0 for h in hits}
    return {h.chunk.metadata.chunk_id: (h.score - lo) / rng for h in hits}


def _minmax_values(values: dict[str, float]) -> dict[str, float]:
    """Min-max normalise an id->score mapping onto [0, 1]."""
    if not values:
        return {}
    lo, hi = min(values.values()), max(values.values())
    rng = hi - lo
    if rng <= 0:
        return {k: 1.0 for k in values}
    return {k: (v - lo) / rng for k, v in values.items()}


def _default_alpha() -> float:
    """Read the env-tunable hybrid alpha for Weaviate's vector/BM25 blend."""
    value = get_settings().hybrid_alpha
    return max(0.0, min(1.0, value))


@dataclass(frozen=True)
class RetrievalConfig:
    parent_top_n: int = 6
    child_per_parent: int = 6
    backfill_children: int = 12
    graph_recall: int = 12                # chunks fetched by matched-parameter tag
    # Additive boosts (scaled by a [0,1] signal) that nudge ordering without
    # swamping a chunk's own normalised hybrid relevance.
    parent_score_weight: float = 0.25     # boost for living in a strongly-matched parent
    graph_boost: float = 0.15             # boost for being about a matched parameter
    hybrid_alpha: float = -1.0
    max_per_source: int | None = 3


class HierarchicalRetriever:
    """Three-arm recall pipeline (parent-constrained children, global backfill,
    graph parameter recall) fused by one magnitude-preserving scoring pass.
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
                graph_recall=cfg.graph_recall,
                parent_score_weight=cfg.parent_score_weight,
                graph_boost=cfg.graph_boost,
                hybrid_alpha=_default_alpha(),
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
        """Run the three recall arms and fuse them in one scoring pass: each
        chunk's own normalised hybrid score plus parent/graph membership boosts."""
        # Arm 1. Parent recall (hybrid: BM25 catches unique header tokens).
        parent_hits = self.vector_store.hybrid_sections(
            query=question,
            vector=question_vector,
            limit=self.config.parent_top_n,
            alpha=self.config.hybrid_alpha,
            source_kinds=source_kinds,
        )
        parent_score: dict[str, float] = {p.section_id: float(p.score) for p in parent_hits}

        # Arm 1 (cont). Children filtered to the recalled parents.
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

        # Arm 2. Unconstrained backfill — catches strong chunks in weak parents.
        backfill = self.vector_store.hybrid_chunks(
            query=question,
            vector=question_vector,
            limit=self.config.backfill_children,
            alpha=self.config.hybrid_alpha,
            source_kinds=source_kinds,
        )

        # Arm 3. Graph recall — chunks tagged with the matched (+1-hop expanded)
        # parameters, fetched directly; adds chunks the open search missed.
        expanded = self.knowledge_graph.expand_parameters(matched_parameter_ids) if matched_parameter_ids else set()
        graph_children: list[ChunkHit] = []
        if expanded:
            graph_children = self.vector_store.chunks_by_parameters(
                query=question,
                vector=question_vector,
                limit=self.config.graph_recall,
                alpha=self.config.hybrid_alpha,
                parameter_ids=tuple(sorted(expanded)),
                source_kinds=source_kinds,
            )

        # Merge into one candidate pool, keeping the best raw hybrid score seen.
        pool: dict[str, ChunkHit] = {}
        for hit in (*constrained_children, *backfill, *graph_children):
            cid = hit.chunk.metadata.chunk_id
            if cid not in pool or pool[cid].score < hit.score:
                pool[cid] = hit

        # Single magnitude-preserving scoring pass over the pool.
        # Collects the raw hybrid scores, finds lo/hi, and rescales each to [0, 1]
        n_constrained = _minmax(constrained_children)
        n_backfill = _minmax(backfill)
        n_graph = _minmax(graph_children)
        n_parent = _minmax_values(parent_score)

        ranked: list[RetrievedChunk] = []
        for cid, hit in pool.items():
            # Base relevance: the chunk's strongest normalised hybrid score
            # across the arms that surfaced it (magnitude, not rank).
            base = max(n_constrained.get(cid, 0.0), n_backfill.get(cid, 0.0), n_graph.get(cid, 0.0))
            parent_id = hit.chunk.metadata.parent_id or ""
            parent_norm = n_parent.get(parent_id, 0.0)
            score = base
            score += self.config.parent_score_weight * parent_norm
            score += self.config.graph_boost * n_graph.get(cid, 0.0)
            ranked.append(
                RetrievedChunk(
                    chunk=hit.chunk,
                    score=score,
                    parent_score=parent_score.get(parent_id) if parent_id in parent_score else None,
                )
            )

        ranked.sort(key=lambda r: r.score, reverse=True)
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
