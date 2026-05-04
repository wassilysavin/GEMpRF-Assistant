from dataclasses import dataclass

import numpy as np

from ..models import ParameterSpec


_MIN_PARAMETER_SCORE = 0.32
_PARAMETER_CUTOFF_MARGIN = 0.05
_MAX_INITIAL_PARAMETER_CANDIDATES = 8
_MAX_RETURNED_PARAMETERS = 4


@dataclass
class ParameterMatcher:
    """Embedding-based matcher over the ParameterSpec catalog.
    """

    parameters: list[ParameterSpec]
    entries: list[dict]
    embeddings: np.ndarray

    @classmethod
    def from_parameters(cls, parameters: list[ParameterSpec], embed_fn) -> "ParameterMatcher":
        """Build a matcher: emit two embedding rows per parameter and embed them eagerly.
        """
        entries: list[dict] = []
        for parameter in parameters:
            # Surface form: aliases + enum values for lexical match.
            surface_tokens = [*parameter.aliases, *parameter.enum_values]
            entries.append({
                "parameter_id": parameter.id,
                "text": (
                    f"{parameter.label}. "
                    f"Aliases: {', '.join(surface_tokens)}. "
                    f"Identifier: {parameter.id}."
                ),
            })
            # Conceptual form: prose for semantic match.
            entries.append({
                "parameter_id": parameter.id,
                "text": (
                    f"XML path: {parameter.xml_path}. "
                    f"Summary: {parameter.summary} Significance: {parameter.significance}"
                ),
            })
        embeddings = embed_fn([entry["text"] for entry in entries]) if entries else np.zeros((0, 1), dtype=np.float32)
        return cls(parameters=parameters, entries=entries, embeddings=embeddings)

    def match(self, question_embedding: np.ndarray) -> list[ParameterSpec]:
        return [spec for spec, _score in self.match_with_scores(question_embedding)]

    def match_with_scores(
        self, question_embedding: np.ndarray
    ) -> list[tuple[ParameterSpec, float]]:
        """Top parameters above a two-stage gate, paired with their cosine scores.
        """
        if not self.entries:
            return []
        scores = np.sum(self.embeddings * question_embedding[None, :], axis=1)
        best: dict[str, float] = {}
        for score, entry in zip(scores, self.entries):
            pid = entry["parameter_id"]
            best[pid] = max(best.get(pid, -1.0), float(score))
        ordered = sorted(best.items(), key=lambda item: item[1], reverse=True)
        if not ordered:
            return []
        top_score = ordered[0][1]
        # Cutoff = max(floor, top - margin)
        cutoff = max(_MIN_PARAMETER_SCORE, top_score - _PARAMETER_CUTOFF_MARGIN)
        kept_pairs = [(pid, score) for pid, score in ordered if score >= cutoff][
            :_MAX_INITIAL_PARAMETER_CANDIDATES
        ]
        spec_lookup = {p.id: p for p in self.parameters}
        return [
            (spec_lookup[pid], score)
            for pid, score in kept_pairs[:_MAX_RETURNED_PARAMETERS]
            if pid in spec_lookup
        ]
