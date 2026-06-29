import threading
import urllib.parse
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence

from rdflib import Graph, Literal, Namespace, URIRef
from rdflib.namespace import RDF, RDFS, SKOS

from ..models import ParameterSpec, ParentSection, SourceMeta


SCHEMA = Namespace("https://schema.org/")
GEMPRF = Namespace("https://gemprf.local/ontology#")
PARAM = Namespace("https://gemprf.local/parameter/")
SRC = Namespace("https://gemprf.local/source/")
CHUNK = Namespace("https://gemprf.local/chunk/")
SECTION = Namespace("https://gemprf.local/section/")

# rdflib's SPARQL parser uses pyparsing global state that races under threads; serialize query parsing.
_SPARQL_LOCK = threading.Lock()


def _slug(text: str) -> str:
    """URL-safe transformation for embedding identifiers in URIs.
    """
    return urllib.parse.quote(text.strip().replace(" ", "_"), safe="._-")


def parameter_uri(parameter_id: str) -> URIRef:
    """Build gemprf:parameter/<slug> URI for a ParameterSpec.
    """
    return PARAM[_slug(parameter_id)]


def source_uri(source_id: str) -> URIRef:
    """gemprf:source/<slug> URI for a SourceMeta.
    """
    return SRC[_slug(source_id)]


def chunk_uri(chunk_id: str) -> URIRef:
    """gemprf:chunk/<slug> URI for an indexed chunk.
    """
    return CHUNK[_slug(chunk_id)]


def section_uri(section_id: str) -> URIRef:
    """gemprf:section/<slug> URI for a ParentSection.
    """
    return SECTION[_slug(section_id)]


@dataclass(frozen=True)
class ChunkTriple:
    """Minimal projection of a Chunk for KG ingest.
    """

    chunk_id: str
    source_id: str
    section_id: str | None
    parameter_ids: tuple[str, ...]


class KnowledgeGraphStore:

    def __init__(self, path: str | Path | None = None) -> None:
        self.path = Path(path) if path else None
        self.graph = Graph()
        self._bind_prefixes()

    def _bind_prefixes(self) -> None:
        """Register the schema/gemprf/skos prefixes
        """
        self.graph.bind("schema", SCHEMA)
        self.graph.bind("gemprf", GEMPRF)
        self.graph.bind("skos", SKOS)

    def load(self) -> bool:
        if self.path and self.path.exists():
            self.graph.parse(self.path, format="turtle")
            return True
        return False

    def save(self) -> None:
        if not self.path:
            return
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.graph.serialize(destination=self.path, format="turtle")

    def clear(self) -> None:
        """Drop the current graph and rebind prefixes on a fresh rdflib.Graph.
        """
        self.graph = Graph()
        self._bind_prefixes()

    def build(
        self,
        sources: Iterable[SourceMeta],
        parameters: Iterable[ParameterSpec],
        sections: Iterable[ParentSection],
        chunks: Iterable[ChunkTriple],
    ) -> None:
        """Rebuild the entire graph from the catalog + chunker output.
        """
        self.clear()
        g = self.graph

        for source in sources:
            uri = source_uri(source.id)
            g.add((uri, RDF.type, GEMPRF.Source))
            g.add((uri, RDFS.label, Literal(source.title)))
            g.add((uri, GEMPRF.kind, Literal(source.kind)))
            if source.url:
                g.add((uri, SCHEMA.url, Literal(source.url)))
            if source.description:
                g.add((uri, SCHEMA.description, Literal(source.description)))

        parameter_ids: set[str] = set()
        parameters = list(parameters)
        for parameter in parameters:
            parameter_ids.add(parameter.id)
            uri = parameter_uri(parameter.id)
            g.add((uri, RDF.type, GEMPRF.Parameter))
            g.add((uri, RDFS.label, Literal(parameter.label)))
            g.add((uri, GEMPRF.xmlPath, Literal(parameter.xml_path)))
            g.add((uri, SCHEMA.description, Literal(parameter.summary)))
            for alias in parameter.aliases:
                g.add((uri, SKOS.altLabel, Literal(alias)))
            for src_id in (*parameter.source_ids, *parameter.code_source_ids):
                g.add((uri, GEMPRF.supportedBy, source_uri(src_id)))

        for parameter in parameters:
            uri = parameter_uri(parameter.id)
            for related in parameter.related_parameters:
                if related not in parameter_ids:
                    continue
                other = parameter_uri(related)
                # skos:related is symmetric; rdflib doesn't infer that.
                g.add((uri, SKOS.related, other))
                g.add((other, SKOS.related, uri))

        for section in sections:
            s_uri = section_uri(section.section_id)
            g.add((s_uri, RDF.type, GEMPRF.Section))
            g.add((s_uri, RDFS.label, Literal(" > ".join(section.heading_path))))
            g.add((s_uri, SCHEMA.isPartOf, source_uri(section.source_id)))
            for pid in section.parameter_ids:
                g.add((s_uri, SCHEMA.about, parameter_uri(pid)))

        for chunk in chunks:
            c_uri = chunk_uri(chunk.chunk_id)
            g.add((c_uri, RDF.type, GEMPRF.Chunk))
            g.add((c_uri, SCHEMA.isPartOf, source_uri(chunk.source_id)))
            if chunk.section_id:
                sec = section_uri(chunk.section_id)
                g.add((sec, GEMPRF.containsChunk, c_uri))
            for pid in chunk.parameter_ids:
                g.add((c_uri, SCHEMA.about, parameter_uri(pid)))

    def expand_parameters(self, parameter_ids: Iterable[str]) -> set[str]:
        """One-hop 'skos:related' expansion: returns the seed ids their direct neighbours.
        """
        seeds = {pid for pid in parameter_ids}
        if not seeds:
            return set()
        bindings = ", ".join(f"<{parameter_uri(pid)}>" for pid in seeds)
        query = f"""
            PREFIX skos: <{SKOS}>
            SELECT ?related WHERE {{
              ?seed skos:related ?related .
              FILTER (?seed IN ({bindings}))
            }}
        """
        expanded = set(seeds)
        with _SPARQL_LOCK:
            rows = list(self.graph.query(query))
        for row in rows:
            expanded.add(_strip_uri(str(row.related)))
        return expanded

    def chunks_for_parameters(self, parameter_ids: Iterable[str]) -> set[str]:
        """Set of chunk ids whose 'schema:about' edges include any of the given parameters.
        """
        ids = list(parameter_ids)
        if not ids:
            return set()
        bindings = ", ".join(f"<{parameter_uri(pid)}>" for pid in ids)
        # 'a <Chunk>' excludes sections (which also have schema:about edges).
        query = f"""
            PREFIX schema: <{SCHEMA}>
            SELECT DISTINCT ?chunk WHERE {{
              ?chunk schema:about ?parameter ;
                     a <{GEMPRF.Chunk}> .
              FILTER (?parameter IN ({bindings}))
            }}
        """
        with _SPARQL_LOCK:
            rows = list(self.graph.query(query))
        return {_strip_uri(str(row.chunk)) for row in rows}


def _strip_uri(uri: str) -> str:
    """Recover the original id
    """
    return urllib.parse.unquote(uri.rsplit("/", 1)[-1])
