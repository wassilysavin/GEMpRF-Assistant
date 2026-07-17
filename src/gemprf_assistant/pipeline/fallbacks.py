"""Refusal-path fallbacks: corpus-grounded relation/capability answers, else the parameter matrix."""
from ..config import get_settings
from ..models import FallbackKind, ParameterSpec
from .parameter_relations import (
    MODEL_CAPABILITY_ANSWER,
    covered_param_ids,
    model_capability_question,
    named_param_ids,
    question_names_param,
    render_code_entity_answer,
    render_parameter_matrix,
    render_relation_answer,
)

# Min cosine for targeting the refusal fallback by embedding match; keeps off-topic refusals on the matrix.
_RELATION_FALLBACK_MIN_SCORE = 0.6


def relation_fallback(
    question: str,
    matched_specs: list[ParameterSpec] | None = None,
    matched_scores: dict[str, float] | None = None,
) -> tuple[str, FallbackKind] | None:
    """Grounded fallback for the refusal paths: target the parameter the question names or
    confidently matches, else fall back to the universal parameter-interaction matrix."""
    if not get_settings().relations_enabled:
        return None
    if model_capability_question(question):
        return MODEL_CAPABILITY_ANSWER, FallbackKind.MODEL_CAPABILITY
    named = named_param_ids(question)
    if named:
        answer = render_relation_answer(named, question)
        return (answer, FallbackKind.RELATION) if answer is not None else None
    # No curated trigger (e.g. bare "measured_data"): target the top embedding match when it is a
    # confident, relation-covered hit the question literally names, else the matrix (guards off-topic ~0.7).
    specs = matched_specs or []
    scores = matched_scores or {}
    if specs:
        top = specs[0]
        if (
            top.id in covered_param_ids()
            and scores.get(top.id, 0.0) >= _RELATION_FALLBACK_MIN_SCORE
            and question_names_param(question, top.id, (top.label, *top.aliases, top.id.split(".")[0]))
        ):
            answer = render_relation_answer([top.id], question)
            if answer:
                return answer, FallbackKind.RELATION
    # Last resort before the generic matrix: a grounded card for a code entity the question names.
    code_answer = render_code_entity_answer(question)
    if code_answer is not None:
        return code_answer, FallbackKind.CODE_ENTITY
    return render_parameter_matrix(), FallbackKind.PARAMETER_MATRIX
