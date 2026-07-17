"""Online query pipeline: engine facade + replaceable stages (rewrite, retrieve, rerank, assemble, generate, fallbacks, clarify)."""
from .engine import GraphRagEngine

__all__ = ["GraphRagEngine"]
