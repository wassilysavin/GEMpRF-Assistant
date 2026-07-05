import re
from dataclasses import dataclass
from typing import Callable, Iterable


@dataclass(frozen=True)
class Relation:
    """One corpus-grounded relation attached to one or more matched parameters."""
    param_ids: tuple[str, ...]  # matched-spec ids this relation surfaces for
    kind: str  # formula | effect | scales | gates | override | constrain
    text: str  # the allowed claim, traceable to the cited source
    source_id: str  # citation into the source registry
    compute: Callable[[int], str] | None = None  # optional numeric eval for an integer target


# Every `text` is traceable to the corpus (grounding audit); no degrees-of-freedom,
# accuracy, runtime, or overfitting inferences are asserted here.
RELATIONS: tuple[Relation, ...] = (
    Relation(
        ("search_space.nDCT.value",), "formula",
        "nDCT generates (2 * nDCT + 1) cosine regressors; the sample default is 1, giving 3.",
        "website.config_generator",
        compute=lambda n: f"for nDCT={n} that is {2 * n + 1} cosine regressors",
    ),
    Relation(
        ("search_space.nDCT.value",), "effect",
        "The DCT regressors are stacked as nuisance columns in the design matrix to "
        "absorb low-frequency drift in the fMRI signal.",
        "website.config_generator",
    ),
    Relation(
        ("measured_data.batches",), "formula",
        "Per-batch size is computed as max(1, total_y_signals / batches), where "
        "total_y_signals is the number of measured fMRI Y-signal columns.",
        "website.config_generator",
    ),
    Relation(
        ("search_space.default_spatial_grid.num_horizontal_prfs",
         "search_space.default_spatial_grid.num_vertical_prfs",
         "search_space.default_sigmas.num_sigmas"), "scales",
        "The coarse-fit candidate grid size is the product "
        "(num_horizontal_prfs x num_vertical_prfs x num_sigmas); increasing any of "
        "these increases compute and memory demands.",
        "website.config_generator",
    ),
    Relation(
        ("stimulus.visual_field",
         "search_space.default_spatial_grid.visual_field_radius"), "constrain",
        "Stimulus visual_field sets the stimulus coordinate range and is distinct from "
        "the search-space visual_field_radius, which sets the pRF candidate grid extent.",
        "website.config_generator",
    ),
    Relation(
        ("refine_fitting.enable",), "effect",
        "When enabled, Refine Fitting runs the single-step quadratic refinement to "
        "produce refined per-voxel centre and size estimates, and adds compute and "
        "memory pressure because more model terms are generated and used.",
        "website.config_generator",
    ),
    Relation(
        ("refine_fitting.enable", "refine_fitting.refinefit_on_gpu"), "gates",
        "refinefit_on_gpu only has an effect when Refine Fitting is enabled; when "
        "Refine Fitting is disabled it has no effect.",
        "website.config_generator",
    ),
    Relation(
        ("stimulus.high_temporal_resolution.num_frames_downsampled",
         "stimulus.high_temporal_resolution.slice_time_ref"), "gates",
        "num_frames_downsampled and slice_time_ref are read only when High Temporal "
        "Resolution is enabled; when disabled the stimulus frame count is used as-is "
        "and both are ignored.",
        "website.config_generator",
    ),
    Relation(
        ("stimulus.high_temporal_resolution.num_frames_downsampled",), "constrain",
        "If num_frames_downsampled exceeds the actual number of stimulus frames, the "
        "run aborts with an error.",
        "website.config_generator",
    ),
    Relation(
        ("stimulus.binarization.threshold",), "gates",
        "Binarization applies only when enabled: every stimulus value strictly greater "
        "than threshold becomes 1 and every other value becomes 0; when disabled the "
        "stimulus is loaded unchanged regardless of threshold.",
        "website.config_generator",
    ),
    Relation(
        ("search_space.default_hrf",), "override",
        "When Use Custom Parameters from File is enabled and a section's use_from_file "
        "flag is set, that section's values load from the configured H5 file instead of "
        "the default block; otherwise the default block is used.",
        "website.config_generator",
    ),
)

_INT_RE = re.compile(r"\b(\d+)\b")


def relations_for(spec_ids: Iterable[str]) -> list[Relation]:
    """Return relations attached to any of the given matched-spec ids, order-preserving."""
    wanted = set(spec_ids)
    return [r for r in RELATIONS if wanted.intersection(r.param_ids)]


def _augmented_text(relation: Relation, question: str) -> str:
    """Append an evaluated formula result when the question carries an integer target."""
    if relation.compute is None:
        return relation.text
    nums = _INT_RE.findall(question)
    if not nums:
        return relation.text
    return f"{relation.text} ({relation.compute(int(nums[0]))})"


def render_relation_answer(spec_ids: Iterable[str], question: str) -> str | None:
    """Render a user-facing answer from grounded relations, or None when there are none."""
    rows = relations_for(spec_ids)
    if not rows:
        return None
    return " ".join(_augmented_text(r, question) for r in rows)


def covered_param_ids() -> set[str]:
    """Every parameter id that appears in at least one grounded relation."""
    return {pid for r in RELATIONS for pid in r.param_ids}


# Distinctive lowercase keywords per covered parameter; a refusal is targeted to a
# parameter only when the question literally contains one (embedding score does not
# separate on-topic from off-topic here, but literal naming does).
_TRIGGERS: dict[str, tuple[str, ...]] = {
    "search_space.nDCT.value": ("ndct",),
    "measured_data.batches": ("batch",),
    "search_space.default_spatial_grid.num_horizontal_prfs": ("num_horizontal_prfs", "horizontal prf"),
    "search_space.default_spatial_grid.num_vertical_prfs": ("num_vertical_prfs", "vertical prf"),
    "search_space.default_sigmas.num_sigmas": ("num_sigmas", "sigma"),
    "search_space.default_spatial_grid.visual_field_radius": ("visual_field_radius", "visual field radius"),
    "stimulus.visual_field": ("visual_field", "visual field"),
    "refine_fitting.enable": ("refine fitting", "refine_fitting", "refine fit"),
    "refine_fitting.refinefit_on_gpu": ("refinefit_on_gpu", "refinefit on gpu", "refine fitting on gpu"),
    "stimulus.high_temporal_resolution.num_frames_downsampled": ("num_frames_downsampled", "downsampled"),
    "stimulus.high_temporal_resolution.slice_time_ref": ("slice_time_ref", "slice time"),
    "stimulus.binarization.threshold": ("binariz", "threshold"),
    "search_space.default_hrf": ("hrf from file", "default_hrf", "hrf"),
}


def _term_in(q_lower: str, term: str) -> bool:
    """Separator-tolerant substring test: spaces and underscores are interchangeable."""
    if not term or len(term) < 3:
        return False
    t = term.lower()
    return t in q_lower or t.replace("_", " ") in q_lower or t.replace(" ", "_") in q_lower


def question_names_param(question: str, pid: str, extra_terms: Iterable[str] = ()) -> bool:
    """True if the question literally names this param via a curated trigger or an extra term."""
    q = question.lower()
    return any(_term_in(q, term) for term in (*_TRIGGERS.get(pid, ()), *extra_terms))


def named_param_ids(question: str) -> list[str]:
    """Covered parameter ids whose distinctive keyword literally appears in the question."""
    return [pid for pid in _TRIGGERS if question_names_param(question, pid)]


# Compact, universal, corpus-grounded map of how the main parameters relate;
# shown as a general reference when a refusal can't be targeted to one parameter.
PARAMETER_MATRIX = (
    "I can't ground a specific answer to that, but here is how the main GEM-pRF "
    "parameters relate (general reference from the docs):\n\n"
    "Size & cost\n"
    "- Grid candidates = num_horizontal_prfs x num_vertical_prfs x num_sigmas; raising any "
    "of them increases compute and memory demands (sample grid 51 x 51 x 8).\n"
    "- nDCT generates (2 * nDCT + 1) cosine drift regressors, stacked as nuisance columns "
    "(sample nDCT 1, giving 3).\n"
    "- Batches set the per-batch size = max(1, total_y_signals / batches).\n\n"
    "Toggles (act only when enabled)\n"
    "- Refine fitting runs per-voxel quadratic refinement (adds compute and memory) and "
    "gates refinefit_on_gpu.\n"
    "- High temporal resolution gates num_frames_downsampled and slice_time_ref (both "
    "ignored when off).\n"
    "- Binarization sets stimulus values above the threshold to 1 (threshold ignored when off).\n\n"
    "Overrides & constraints\n"
    "- Use-from-file flags override the matching default block (HRF, sigmas, spatial grid).\n"
    "- num_frames_downsampled must not exceed the stimulus frame count.\n"
    "- visual_field sets stimulus extent; visual_field_radius sets the search-grid extent."
)


def render_parameter_matrix() -> str:
    """Return the compact universal parameter-interaction reference."""
    return PARAMETER_MATRIX


# Corpus-grounded answer for pRF-model capability questions; the local LLM tends to
# refuse yes/no "is X supported by the pRF model?" forms even with the support chunks
# retrieved, so this deterministic answer carries the same grounded content.
MODEL_CAPABILITY_ANSWER = (
    "GEM-pRF currently implements only the 2D Gaussian pRF model, and it is the only option you can "
    "select in the Configuration Generator's pRF Model field. The 2D Gaussian describes a single "
    "isotropic receptive field with a centre position and one size, so that plain centre-and-size case "
    "is what it supports.\n\n"
    "Properties the 2D Gaussian does not capture would need a different model:\n"
    "- A centre-surround receptive field or surround suppression would require the Difference of "
    "Gaussians (DoG) model, which adds an inhibitory surround via a second Gaussian.\n"
    "- A compressive or nonlinear (subadditive) response would require the CSS model.\n\n"
    "Both DoG and CSS appear in the pRF Model dropdown but are marked 'not available at the moment': "
    "DoG is an unimplemented stub and CSS has no implementation, so neither can currently be selected."
)

# Capability-specific phrasings that the model-capability answer covers. Kept narrow
# (this fires only on the refusal path) so it never overrides a legitimate refusal that
# merely mentions "model" or "gaussian" in passing.
_MODEL_CAPABILITY_RE = re.compile(
    r"\b(surround|inhibitory|centre[- ]surround|center[- ]surround|difference[ -]of[ -]gaussian|dog|"
    r"css|compressive|non[- ]?linear|subadditive|isotropic|anisotropic|second gaussian|"
    r"which (?:pr?f )?model|what (?:pr?f )?model|pr?f model|model type)\b"
)


def model_capability_question(question: str) -> bool:
    """True when the question asks what a GEM-pRF pRF model can or cannot represent."""
    return bool(_MODEL_CAPABILITY_RE.search(question.lower()))
