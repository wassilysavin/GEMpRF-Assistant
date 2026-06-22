import os
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

import numpy as np

import weaviate
from weaviate.classes.config import Configure, DataType, Property, VectorDistances
from weaviate.classes.data import DataObject
from weaviate.classes.query import Filter, MetadataQuery
from weaviate.util import generate_uuid5

from ..models import Chunk, ChunkMetadata, ParentSection


SECTION_COLLECTION = "GemPrfSection"
CHUNK_COLLECTION = "GemPrfChunk"


@dataclass(frozen=True)
class SectionHit:
    section_id: str
    source_id: str
    source_kind: str
    heading_path: tuple[str, ...]
    parameter_ids: tuple[str, ...]
    summary: str
    score: float


@dataclass(frozen=True)
class ChunkHit:
    chunk: Chunk
    score: float


class WeaviateHierarchicalStore:

    def __init__(
        self,
        persistence_path: str | None = None,
        connect_to: str | None = None,
        host: str | None = None,
        http_port: int | None = None,
        grpc_port: int | None = None,
    ) -> None:
        self._persistence_path = persistence_path or os.getenv(
            "GEMPRF_ASSISTANT_WEAVIATE_PATH",
            str(Path.cwd() / "data" / "weaviate"),
        )
        self._mode = (connect_to or os.getenv("GEMPRF_ASSISTANT_WEAVIATE_MODE", "embedded")).strip().lower()
        self._host = host or os.getenv("GEMPRF_ASSISTANT_WEAVIATE_HOST", "localhost")
        self._http_port = http_port or int(os.getenv("GEMPRF_ASSISTANT_WEAVIATE_HTTP_PORT", "8080"))
        self._grpc_port = grpc_port or int(os.getenv("GEMPRF_ASSISTANT_WEAVIATE_GRPC_PORT", "50051"))
        self._client: weaviate.WeaviateClient | None = None

    @property
    def client(self) -> weaviate.WeaviateClient:
        if self._client is None:
            self._client = self._connect()
        return self._client

    def _connect(self) -> weaviate.WeaviateClient:
        if self._mode == "local":
            return weaviate.connect_to_local(
                host=self._host,
                port=self._http_port,
                grpc_port=self._grpc_port,
            )
        Path(self._persistence_path).mkdir(parents=True, exist_ok=True)
        return weaviate.connect_to_embedded(
            persistence_data_path=self._persistence_path,
            environment_variables={"LOG_LEVEL": "panic"},
        )

    def close(self) -> None:
        if self._client is not None:
            try:
                self._client.close()
            finally:
                self._client = None

    def __enter__(self) -> "WeaviateHierarchicalStore":
        _ = self.client
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    def ensure_schema(self) -> None:
        client = self.client
        if not client.collections.exists(SECTION_COLLECTION):
            client.collections.create(
                name=SECTION_COLLECTION,
                vectorizer_config=Configure.Vectorizer.none(),
                vector_index_config=Configure.VectorIndex.hnsw(distance_metric=VectorDistances.COSINE),
                properties=[
                    Property(name="section_id", data_type=DataType.TEXT),
                    Property(name="source_id", data_type=DataType.TEXT),
                    Property(name="source_kind", data_type=DataType.TEXT),
                    Property(name="heading_path", data_type=DataType.TEXT_ARRAY),
                    Property(name="summary", data_type=DataType.TEXT),
                    Property(name="parameter_ids", data_type=DataType.TEXT_ARRAY),
                    Property(name="child_chunk_ids", data_type=DataType.TEXT_ARRAY),
                    Property(name="char_start", data_type=DataType.INT),
                    Property(name="char_end", data_type=DataType.INT),
                ],
            )
        if not client.collections.exists(CHUNK_COLLECTION):
            client.collections.create(
                name=CHUNK_COLLECTION,
                vectorizer_config=Configure.Vectorizer.none(),
                vector_index_config=Configure.VectorIndex.hnsw(distance_metric=VectorDistances.COSINE),
                properties=[
                    Property(name="chunk_id", data_type=DataType.TEXT),
                    Property(name="source_id", data_type=DataType.TEXT),
                    Property(name="source_kind", data_type=DataType.TEXT),
                    Property(name="parent_id", data_type=DataType.TEXT),
                    Property(name="heading_path", data_type=DataType.TEXT_ARRAY),
                    Property(name="parameter_ids", data_type=DataType.TEXT_ARRAY),
                    Property(name="doc_kind", data_type=DataType.TEXT),
                    Property(name="text", data_type=DataType.TEXT),
                    Property(name="token_count", data_type=DataType.INT),
                    Property(name="char_start", data_type=DataType.INT),
                    Property(name="char_end", data_type=DataType.INT),
                ],
            )

    def reset(self) -> None:
        client = self.client
        for name in (SECTION_COLLECTION, CHUNK_COLLECTION):
            if client.collections.exists(name):
                client.collections.delete(name)
        self.ensure_schema()

    def count_chunks(self) -> int:
        coll = self.client.collections.get(CHUNK_COLLECTION)
        return coll.aggregate.over_all(total_count=True).total_count or 0

    def count_sections(self) -> int:
        coll = self.client.collections.get(SECTION_COLLECTION)
        return coll.aggregate.over_all(total_count=True).total_count or 0

    def insert_sections(self, sections: Sequence[ParentSection], vectors: np.ndarray) -> None:
        if len(sections) != len(vectors):
            raise ValueError("sections and vectors must be the same length")
        if not sections:
            return
        coll = self.client.collections.get(SECTION_COLLECTION)
        coll.data.insert_many([
            DataObject(
                properties={
                    "section_id": s.section_id,
                    "source_id": s.source_id,
                    "source_kind": s.source_kind,
                    "heading_path": list(s.heading_path),
                    "summary": s.summary,
                    "parameter_ids": list(s.parameter_ids),
                    "child_chunk_ids": list(s.child_chunk_ids),
                    "char_start": int(s.char_span[0]),
                    "char_end": int(s.char_span[1]),
                },
                uuid=generate_uuid5(s.section_id),
                vector=vectors[i].astype(np.float32).tolist(),
            )
            for i, s in enumerate(sections)
        ])

    def insert_chunks(self, chunks: Sequence[Chunk], vectors: np.ndarray) -> None:
        if len(chunks) != len(vectors):
            raise ValueError("chunks and vectors must be the same length")
        if not chunks:
            return
        coll = self.client.collections.get(CHUNK_COLLECTION)
        coll.data.insert_many([
            DataObject(
                properties={
                    "chunk_id": c.metadata.chunk_id,
                    "source_id": c.metadata.source_id,
                    "source_kind": c.metadata.source_kind,
                    "parent_id": c.metadata.parent_id or "",
                    "heading_path": list(c.metadata.heading_path),
                    "parameter_ids": list(c.metadata.parameter_ids),
                    "doc_kind": c.metadata.doc_kind,
                    "text": c.text,
                    "token_count": int(c.metadata.token_count),
                    "char_start": int(c.metadata.char_span[0]),
                    "char_end": int(c.metadata.char_span[1]),
                },
                uuid=generate_uuid5(c.metadata.chunk_id),
                vector=vectors[i].astype(np.float32).tolist(),
            )
            for i, c in enumerate(chunks)
        ])

    def hybrid_sections(
        self,
        query: str,
        vector: np.ndarray,
        limit: int,
        alpha: float,
        source_kinds: tuple[str, ...] | None = None,
    ) -> list[SectionHit]:
        """alpha: 1.0 = pure vector, 0.0 = pure BM25. BM25 restricted to 'summary'.
        """
        coll = self.client.collections.get(SECTION_COLLECTION)
        filters = self._kind_filter(source_kinds)
        response = coll.query.hybrid(
            query=query,
            vector=vector.astype(np.float32).tolist(),
            alpha=alpha,
            limit=limit,
            query_properties=["summary"],
            return_metadata=MetadataQuery(score=True),
            filters=filters,
        )
        out: list[SectionHit] = []
        for item in response.objects:
            props = item.properties or {}
            score = float(item.metadata.score) if item.metadata and item.metadata.score is not None else 0.0
            out.append(
                SectionHit(
                    section_id=str(props.get("section_id", "")),
                    source_id=str(props.get("source_id", "")),
                    source_kind=str(props.get("source_kind", "")),
                    heading_path=tuple(props.get("heading_path") or ()),
                    parameter_ids=tuple(props.get("parameter_ids") or ()),
                    summary=str(props.get("summary", "")),
                    score=score,
                )
            )
        return out

    def hybrid_chunks(
        self,
        query: str,
        vector: np.ndarray,
        limit: int,
        alpha: float,
        parent_ids: tuple[str, ...] | None = None,
        source_kinds: tuple[str, ...] | None = None,
    ) -> list[ChunkHit]:
        """BM25 restricted to 'text' 
        """
        coll = self.client.collections.get(CHUNK_COLLECTION)
        filters = _and_filters(self._parent_filter(parent_ids), self._kind_filter(source_kinds))
        response = coll.query.hybrid(
            query=query,
            vector=vector.astype(np.float32).tolist(),
            alpha=alpha,
            limit=limit,
            query_properties=["text"],
            return_metadata=MetadataQuery(score=True),
            filters=filters,
        )
        return self._chunk_hits(response)

    def chunks_by_parameters(
        self,
        query: str,
        vector: np.ndarray,
        limit: int,
        alpha: float,
        parameter_ids: tuple[str, ...],
        source_kinds: tuple[str, ...] | None = None,
    ) -> list[ChunkHit]:
        """Hybrid search constrained to chunks tagged with ANY of `parameter_ids`
        (the KG recall arm); returns in-filter hybrid scores for fair fusion."""
        if not parameter_ids:
            return []
        coll = self.client.collections.get(CHUNK_COLLECTION)
        filters = _and_filters(self._parameter_filter(parameter_ids), self._kind_filter(source_kinds))
        response = coll.query.hybrid(
            query=query,
            vector=vector.astype(np.float32).tolist(),
            alpha=alpha,
            limit=limit,
            query_properties=["text"],
            return_metadata=MetadataQuery(score=True),
            filters=filters,
        )
        return self._chunk_hits(response)

    @staticmethod
    def _chunk_hits(response) -> list[ChunkHit]:
        """Parse a chunk hybrid-query response into ordered ChunkHit objects."""
        out: list[ChunkHit] = []
        for item in response.objects:
            props = item.properties or {}
            score = float(item.metadata.score) if item.metadata and item.metadata.score is not None else 0.0
            chunk_meta = ChunkMetadata(
                chunk_id=str(props.get("chunk_id", "")),
                source_id=str(props.get("source_id", "")),
                source_kind=str(props.get("source_kind", "")),
                parent_id=str(props.get("parent_id") or "") or None,
                heading_path=tuple(props.get("heading_path") or ()),
                char_span=(int(props.get("char_start") or 0), int(props.get("char_end") or 0)),
                token_count=int(props.get("token_count") or 0),
                parameter_ids=tuple(props.get("parameter_ids") or ()),
                doc_kind=str(props.get("doc_kind") or "prose"),
            )
            out.append(ChunkHit(chunk=Chunk(metadata=chunk_meta, text=str(props.get("text", ""))), score=score))
        return out

    @staticmethod
    def _parameter_filter(parameter_ids: tuple[str, ...] | None):
        if not parameter_ids:
            return None
        return Filter.by_property("parameter_ids").contains_any(list(parameter_ids))

    @staticmethod
    def _kind_filter(source_kinds: tuple[str, ...] | None):
        if not source_kinds:
            return None
        return Filter.by_property("source_kind").contains_any(list(source_kinds))

    @staticmethod
    def _parent_filter(parent_ids: tuple[str, ...] | None):
        if not parent_ids:
            return None
        return Filter.by_property("parent_id").contains_any(list(parent_ids))


def _and_filters(*filters):
    active = [f for f in filters if f is not None]
    if not active:
        return None
    if len(active) == 1:
        return active[0]
    combined = active[0]
    for nxt in active[1:]:
        combined = combined & nxt
    return combined
