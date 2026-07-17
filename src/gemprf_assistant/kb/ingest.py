"""Offline index build: corpus documents -> chunks -> embeddings -> Weaviate + kg.ttl (full wipe-and-reload)."""
from dataclasses import replace

import numpy as np

from ..models import ParameterSpec, SourceMeta
from .chunking import ChunkingConfig, split_documents
from .knowledge_graph import ChunkTriple, KnowledgeGraphStore

_BREADCRUMB_TOKEN_LIMIT = 80


def source_to_parameter_ids(
    sources: dict[str, SourceMeta], parameters: dict[str, ParameterSpec]
) -> dict[str, tuple[str, ...]]:
    """Build the source_id -> (parameter_id, ...) inverse index used during ingest."""
    tags: dict[str, list[str]] = {sid: [] for sid in sources}
    for parameter in parameters.values():
        for sid in (*parameter.source_ids, *parameter.code_source_ids):
            if sid in tags:
                tags[sid].append(parameter.id)
    return {sid: tuple(ids) for sid, ids in tags.items()}


def build_index(
    *,
    documents,
    sources: dict[str, SourceMeta],
    parameters: dict[str, ParameterSpec],
    embedding_backend,
    vector_store,
    knowledge_graph: KnowledgeGraphStore,
    chunking_config: ChunkingConfig | None = None,
) -> dict:
    """Rebuild the vector store and the knowledge graph from scratch."""
    tags = source_to_parameter_ids(sources, parameters)
    doc_pairs: list[tuple[SourceMeta, str]] = []
    for doc in documents:
        source = sources.get(doc.metadata["source_id"])
        if source is None:
            continue
        doc_pairs.append((source, doc.page_content))

    chunks, parents = split_documents(doc_pairs, tags, config=chunking_config or ChunkingConfig())

    # Short chunks lose their context without the heading breadcrumb prepended to the embedded text.
    chunks = [
        replace(c, text=f"{' > '.join(c.metadata.heading_path)}\n\n{c.text}")
        if c.metadata.heading_path and c.metadata.token_count < _BREADCRUMB_TOKEN_LIMIT
        else c
        for c in chunks
    ]

    chunk_vectors = (
        embedding_backend.embed_texts([c.text for c in chunks]) if chunks else np.zeros((0, 1), dtype=np.float32)
    )
    parent_vectors = (
        embedding_backend.embed_texts([p.summary for p in parents]) if parents else np.zeros((0, 1), dtype=np.float32)
    )

    vector_store.reset()
    vector_store.insert_chunks(chunks, chunk_vectors)
    vector_store.insert_sections(parents, parent_vectors)

    triples = [
        ChunkTriple(
            chunk_id=c.metadata.chunk_id,
            source_id=c.metadata.source_id,
            section_id=c.metadata.parent_id,
            parameter_ids=c.metadata.parameter_ids,
        )
        for c in chunks
    ]
    knowledge_graph.build(
        sources=sources.values(),
        parameters=parameters.values(),
        sections=parents,
        chunks=triples,
    )
    knowledge_graph.save()
    return {
        "chunks": len(chunks),
        "sections": len(parents),
        "parameters": len(parameters),
        "sources": len(sources),
    }
