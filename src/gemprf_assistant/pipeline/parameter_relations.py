import json
import re
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path


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
        ("measured_data.batches",), "definition",
        "measured_data is the config section holding the observed fMRI signals GEM-pRF "
        "fits: measured_data_filepath points to one or more NIfTI fMRI runs (iterated by "
        "the analysis loop), and their Y-signal columns are the total_y_signals the fit "
        "runs over.",
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
        "these increases compute and memory demands. Coarse fitting holds all "
        "prediction time courses in GPU memory at once, so the whole product must "
        "fit; the paper's remedy when it does not is to reduce sampling density "
        "(fewer grid points), not to trade one knob for another.",
        "website.config_generator",
    ),
    Relation(
        ("search_space.default_spatial_grid.num_horizontal_prfs",
         "search_space.default_spatial_grid.num_vertical_prfs",
         "search_space.default_spatial_grid.visual_field_radius"), "scales",
        "Candidate pRF centres are np.linspace(-visual_field_radius, "
        "+visual_field_radius) with num_horizontal_prfs points on x and "
        "num_vertical_prfs on y, so the spacing between adjacent centres is "
        "2 * visual_field_radius / (num_horizontal_prfs - 1) (and likewise for y). "
        "At a fixed radius, adding pRFs makes the grid finer; at a fixed pRF count, "
        "a larger radius spreads the same points wider (coarser), so reach and "
        "resolution trade off unless both are raised together.",
        "website.config_generator",
    ),
    Relation(
        ("search_space.default_spatial_grid.num_horizontal_prfs",
         "search_space.default_spatial_grid.num_vertical_prfs",
         "search_space.default_spatial_grid.visual_field_radius"), "constrain",
        "Centres outside the disc x^2 + y^2 < visual_field_radius^2 are discarded "
        "before fitting, so the usable candidate count is smaller than "
        "(num_horizontal_prfs x num_vertical_prfs) and shrinks as visual_field_radius "
        "tightens relative to the grid span.",
        "website.config_generator",
    ),
    Relation(
        ("search_space.default_sigmas.num_sigmas",), "scales",
        "Candidate pRF sizes are np.linspace(min_sigma, max_sigma, num_sigmas) "
        "(num_sigmas equally-spaced values, endpoints included), so the sigma "
        "spacing is (max_sigma - min_sigma) / (num_sigmas - 1); widening the "
        "[min_sigma, max_sigma] range at a fixed num_sigmas coarsens size sampling, "
        "while adding sigmas refines it.",
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
    Relation(
        ("stimulus.width", "stimulus.height"), "effect",
        "stimulus width and height set the resampled stimulus geometry: GEM resamples the "
        "loaded stimulus to this width and height before HRF convolution and uses them in "
        "signal-synthesis memory calculations, so a larger width or height raises the stimulus "
        "pixel count, the flattened model-curve size in GPU signal computation, and memory use.",
        "website.config_generator",
    ),
    Relation(
        ("input.BIDS.run_type",), "effect",
        "BIDS run_type selects whether analysis runs per input or over concatenated blocks: "
        "'individual' resolves a flat list of matching files, while 'concatenated' builds "
        "grouped blocks and drives task-specific stimulus handling.",
        "website.config_generator",
    ),
    Relation(
        ("input.BIDS.input_file_extension",), "constrain",
        "BIDS input_file_extension restricts matching to surface files, volume files, or both, "
        "accepting only .nii.gz, .gii, or 'both'; an unsupported value aborts the run with a "
        "validation error.",
        "website.config_generator",
    ),
    Relation(
        ("input.BIDS.space",), "constrain",
        "BIDS space selects the spatial reference of the input files: fsnative loads each "
        "subject's own surface, fsaverage the group-averaged surface, T1w volumetric files, and "
        "'all' overrides the per-subject choice to load every available space; selecting a space "
        "the derivatives do not contain produces an empty input set.",
        "website.config_generator",
    ),
    Relation(
        ("gpu.default_gpu",), "effect",
        "default_gpu is the primary GPU selected in the config: during setup GEM builds "
        "CUDA_VISIBLE_DEVICES from it and remaps its internal default device to index 0 of that "
        "filtered list; an invalid value falls back to using all available GPUs.",
        "website.config_generator",
    ),
    Relation(
        ("gpu.additional_available_gpus",), "effect",
        "additional_available_gpus is an optional list of extra GPU ids for multi-GPU execution: "
        "setup dedupes and validates them and exports the combined list through "
        "CUDA_VISIBLE_DEVICES, so adding valid GPUs splits model-signal computation across more "
        "devices while invalid ids fall back to using all available GPUs.",
        "website.config_generator",
    ),
    Relation(
        ("search_space.default_sigmas.min_sigma", "search_space.default_sigmas.max_sigma"), "constrain",
        "min_sigma and max_sigma are the lower and upper bounds of the default sigma range and "
        "are used as the start and end of the sigma linspace when custom sigmas are not loaded "
        "from file, so changing them shifts the edges of the sigma search space without changing "
        "the number of samples (that is num_sigmas).",
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
    "measured_data.batches": ("batch", "measured_data", "measured data"),
    "search_space.default_spatial_grid.num_horizontal_prfs": ("num_horizontal_prfs", "horizontal prf"),
    "search_space.default_spatial_grid.num_vertical_prfs": ("num_vertical_prfs", "vertical prf"),
    "search_space.default_sigmas.num_sigmas": ("num_sigmas", "sigma", "min_sigma", "max_sigma"),
    "search_space.default_spatial_grid.visual_field_radius": ("visual_field_radius", "visual field radius"),
    "stimulus.visual_field": ("visual_field", "visual field"),
    "refine_fitting.enable": ("refine fitting", "refine_fitting", "refine fit"),
    "refine_fitting.refinefit_on_gpu": ("refinefit_on_gpu", "refinefit on gpu", "refine fitting on gpu"),
    "stimulus.high_temporal_resolution.num_frames_downsampled": ("num_frames_downsampled", "downsampled"),
    "stimulus.high_temporal_resolution.slice_time_ref": ("slice_time_ref", "slice time"),
    "stimulus.binarization.threshold": ("binariz", "threshold"),
    "search_space.default_hrf": ("hrf from file", "default_hrf", "hrf"),
    "stimulus.width": ("stimulus width", "width"),
    "stimulus.height": ("stimulus height", "height"),
    "input.BIDS.run_type": ("run_type", "run type"),
    "input.BIDS.input_file_extension": ("input_file_extension", "file extension"),
    "input.BIDS.space": ("bids space", "output space", "surface space", "reference space"),
    "gpu.default_gpu": ("default_gpu", "default gpu"),
    "gpu.additional_available_gpus": ("additional_available_gpus", "additional gpus", "multi gpu", "multi-gpu"),
    "search_space.default_sigmas.min_sigma": ("min_sigma", "minimum sigma"),
    "search_space.default_sigmas.max_sigma": ("max_sigma", "maximum sigma"),
}


def _keyword_re(keyword: str) -> re.Pattern:
    """Compile a keyword so spaces/hyphens/underscores may split it (e.g. "N dct" matches
    "ndct"), anchored at a leading word boundary so it can't glue onto an adjacent word."""
    chars = re.sub(r"[\s_-]+", "", keyword.lower())
    return re.compile(r"\b" + r"[\s_-]*".join(re.escape(c) for c in chars), re.IGNORECASE)


_TRIGGER_RES: dict[str, tuple[re.Pattern, ...]] = {
    pid: tuple(_keyword_re(kw) for kw in kws) for pid, kws in _TRIGGERS.items()
}


def question_names_param(question: str, pid: str, extra_terms: Iterable[str] = ()) -> bool:
    """True if the question literally names this param via a curated trigger or an extra term,
    tolerant to spaces/hyphens/underscores that split a keyword (e.g. "N dct" matches nDCT)."""
    patterns = (*_TRIGGER_RES.get(pid, ()), *(_keyword_re(t) for t in extra_terms if t and len(t) >= 3))
    return any(r.search(question) for r in patterns)


def named_param_ids(question: str) -> list[str]:
    """Covered parameter ids whose distinctive keyword appears in the question, tolerant
    to spaces/hyphens/underscores that split a keyword (e.g. "N dct" matches nDCT)."""
    return [pid for pid in _TRIGGERS if question_names_param(question, pid)]


# Compact, universal, corpus-grounded map of how the main parameters relate;
# shown as a general reference when a refusal can't be targeted to one parameter.
PARAMETER_MATRIX = (
    "I can't ground a specific answer to that, but here is how the main GEM-pRF "
    "parameters relate to each other (general reference from the docs):\n\n"
    "Coarse-fit grid (extent and count jointly set resolution)\n"
    "- Candidate centres = np.linspace(-visual_field_radius, +visual_field_radius) with "
    "num_horizontal_prfs points on x and num_vertical_prfs on y, so adjacent-centre spacing "
    "= 2 * visual_field_radius / (num_horizontal_prfs - 1). At a fixed radius, more pRFs -> "
    "finer grid; at a fixed pRF count, a larger radius spreads the same points wider "
    "(coarser) -- reach and resolution trade off unless both rise together (sample 51 x 51, "
    "radius 12).\n"
    "- Candidate sizes = np.linspace(min_sigma, max_sigma, num_sigmas), so sigma spacing = "
    "(max_sigma - min_sigma) / (num_sigmas - 1). Widening [min_sigma, max_sigma] at fixed "
    "num_sigmas coarsens size sampling; adding sigmas refines it (sample 8 over 0.5..5).\n"
    "- Centres outside the disc x^2 + y^2 < visual_field_radius^2 are dropped, so usable "
    "candidates are fewer than the raw num_horizontal_prfs x num_vertical_prfs and shrink as "
    "the radius tightens relative to the grid span.\n\n"
    "Size, cost & memory (the whole product moves together)\n"
    "- Total candidates searched = num_horizontal_prfs x num_vertical_prfs x num_sigmas; "
    "raising any one multiplies the grid and its compute and memory. Coarse fitting holds "
    "all prediction time courses in GPU memory at once, so the full product must fit; the "
    "documented remedy on overflow is to reduce sampling density, not to lower a single knob.\n"
    "- nDCT generates (2 * nDCT + 1) cosine drift regressors stacked as nuisance columns, so "
    "more nDCT -> more design-matrix columns (sample nDCT 1, giving 3).\n"
    "- batches sets per-batch size = max(1, total_y_signals / batches): more batches -> "
    "smaller batches (lower peak memory), fewer -> larger.\n\n"
    "Toggles (act only when enabled)\n"
    "- Refine fitting runs per-voxel quadratic refinement (adds compute and memory) and "
    "gates refinefit_on_gpu, which has no effect while refine fitting is off.\n"
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


# ---------------------------------------------------------------------------
# Code-entity fallback: grounded cards for GEM-pRF modules/classes/functions.
# The artifact is generated from the tool source AST (kb/code_index.py); every field here is
# read back from that file, so nothing is asserted beyond what the code states. This is a
# last-resort safety net on the refusal path, behind the curated parameter relations.
# ---------------------------------------------------------------------------
_CODE_ENTITIES_PATH = Path(__file__).resolve().parents[1] / "kb" / "corpus" / "code_entities.json"

# Generic tokens that occur in ordinary GEM-pRF questions; never trigger a code card on their own,
# so a code entity that happens to be named "run" or "data" can't hijack a normal question.
_CODE_TRIGGER_STOPWORDS = frozenset({
    "run", "main", "model", "models", "data", "space", "value", "values", "config", "configs",
    "file", "files", "path", "paths", "name", "info", "load", "save", "build", "reset", "setup",
    "create", "update", "process", "result", "results", "input", "output", "grid", "batch",
    "batches", "gpu", "hrf", "prf", "stimulus", "signal", "signals", "analysis", "fitting", "utils",
})
_MIN_CODE_TRIGGER_LEN = 4


@lru_cache(maxsize=1)
def _code_entities() -> tuple[dict, ...]:
    """Load the generated code-entity artifact once, or empty when it is absent."""
    try:
        return tuple(json.loads(_CODE_ENTITIES_PATH.read_text(encoding="utf-8"))["entities"])
    except (OSError, KeyError, ValueError):
        return ()


def _is_triggerable_name(name: str) -> bool:
    """A public, distinctive simple name worth matching literally (drops dunders, privates, generics)."""
    return (
        not name.startswith("_")
        and len(name) >= _MIN_CODE_TRIGGER_LEN
        and name.lower() not in _CODE_TRIGGER_STOPWORDS
    )


@lru_cache(maxsize=1)
def _code_trigger_index() -> dict[str, tuple[int, ...]]:
    """Map each triggerable simple name / dotted module qualname to the entities that carry it."""
    index: dict[str, list[int]] = {}
    for i, e in enumerate(_code_entities()):
        keys = set()
        if _is_triggerable_name(e["name"]):
            keys.add(e["name"].lower())
        if e["kind"] == "module":
            keys.add(e["qualname"].lower())  # dotted names are distinctive regardless of length
        for key in keys:
            index.setdefault(key, []).append(i)
    return {k: tuple(v) for k, v in index.items()}


@lru_cache(maxsize=512)
def _code_trigger_res() -> tuple[tuple[re.Pattern, str], ...]:
    """(pattern, key) pairs for every code trigger, longest key first so specific names win."""
    keys = sorted(_code_trigger_index(), key=len, reverse=True)
    return tuple((_keyword_re(k), k) for k in keys)


def named_code_entity_ids(question: str) -> list[int]:
    """Entity indices whose triggerable name the question literally contains, most-specific key first."""
    index = _code_trigger_index()
    hits: list[int] = []
    seen: set[int] = set()
    for pattern, key in _code_trigger_res():
        if pattern.search(question):
            for i in index[key]:
                if i not in seen:
                    seen.add(i)
                    hits.append(i)
    return hits


def _relation_clauses(e: dict) -> str:
    """Grounded relation clauses (contains / subclass-of / calls / imports) present on the entity."""
    clauses: list[str] = []
    if e.get("bases"):
        clauses.append(f"It subclasses {', '.join(e['bases'])}.")
    contains = [c for c in e.get("contains", ()) if not c.startswith("_")]
    if contains:
        shown = ", ".join(contains[:12])
        more = "" if len(contains) <= 12 else f", and {len(contains) - 12} more"
        singular = "member" if e["kind"] == "module" else "method"
        noun = singular if len(contains) == 1 else f"{singular}s"
        clauses.append(f"It defines {len(contains)} public {noun}: {shown}{more}.")
    if e.get("imports"):
        clauses.append(f"It imports {', '.join(e['imports'][:10])}.")
    if e.get("calls"):
        clauses.append(f"It calls {', '.join(e['calls'][:10])}.")
    return " ".join(clauses)


def _render_code_card(e: dict) -> str:
    """A one-entity grounded card: what it is, where, its signature/doc, and its relations."""
    where = f"{e['file']}:{e['line']}"
    if e["kind"] == "module":
        head = f"`{e['qualname']}` is a GEM-pRF module ({where})."
    elif e["kind"] == "class":
        head = f"`{e['name']}` is a class in {e['module']} ({where})."
    else:
        sig = e.get("signature", "")
        head = f"`{e['name']}{sig}` is a {e['kind']} in {e['module']} ({where})."
    doc = f" {e['doc']}" if e.get("doc") else ""
    rel = _relation_clauses(e)
    return f"{head}{doc}{(' ' + rel) if rel else ''}".rstrip()


def render_code_entity_answer(question: str) -> str | None:
    """Grounded card(s) for a code entity the question names, or None when it names none.

    One match renders its full card; several sharing a name are disclosed as a short grounded list
    rather than guessing which one is meant."""
    entities = _code_entities()
    ids = named_code_entity_ids(question)
    if not ids:
        return None
    if len(ids) == 1:
        return _render_code_card(entities[ids[0]])
    primary = entities[ids[0]]
    lead = f"`{primary['name']}` names {len(ids)} things in the GEM-pRF code:"
    rows = [
        f"- {e['kind']} `{e['qualname']}` in {e['module']} ({e['file']}:{e['line']})"
        + (f" -- {e['doc']}" if e.get("doc") else "")
        for e in (entities[i] for i in ids[:8])
    ]
    return "\n".join([lead, *rows])
