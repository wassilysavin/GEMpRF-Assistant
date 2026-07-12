from pathlib import Path

from langchain_core.documents import Document

from .models import ParameterSpec, SourceMeta
from .paths import corpus_root

ROOT = corpus_root()


def _path(relative_path: str) -> str:
    return str((ROOT / relative_path).resolve())


# CURATED_SOURCES: paper.*, website.*, repo.*, code.*
CURATED_SOURCES: tuple[SourceMeta, ...] = (
    SourceMeta(
        id="paper.abstract",
        title="GEM-pRF paper abstract",
        kind="paper",
        url="https://doi.org/10.1016/j.media.2025.103891",
        description=(
            "Paper metadata and abstract for GEM-pRF. It describes the core claim: a GLM reformulation, "
            "direct derivative computation, removal of iterative refinement bottlenecks, and much faster pRF estimation."
        ),
    ),
    SourceMeta(
        id="paper.full",
        title="GEM-pRF full paper (Mittal et al., Medical Image Analysis 2026)",
        kind="paper",
        url="https://doi.org/10.1016/j.media.2025.103891",
        local_path=_path("external/paper/gemprf_paper.md"),
        description=(
            "Full text of the GEM-pRF paper including abstract, introduction (retinotopic mapping "
            "background and visual areas V1, V2, VP, V3, V4), methods (GLM reformulation, coarse "
            "fitting, quadratic refinement, sampling space, multi-GPU, data), validation against "
            "iterative refinement, comparison with mrVista, retinotopic maps, and performance analysis."
        ),
    ),
    SourceMeta(
        id="website.quickstart",
        title="GEM-pRF website quickstart",
        kind="website",
        url="https://gemprf.github.io/",
        local_path=_path("external/docs/index.md"),
        description="Project overview and quickstart positioning GEM-pRF as a standalone tool for pRF mapping.",
    ),
    SourceMeta(
        id="website.installation",
        title="GEM-pRF installation page",
        kind="website",
        url="https://gemprf.github.io/installation.html",
        local_path=_path("external/docs/installation.md"),
        description="Install guidance showing GEM-pRF depends on NVIDIA GPU, CUDA, and CuPy.",
    ),
    SourceMeta(
        id="website.running",
        title="GEM-pRF running guide",
        kind="website",
        url="https://gemprf.github.io/running.html",
        local_path=_path("external/docs/running.md"),
        description="Three ways to run GEM-pRF: gp.run() from Python (recommended), run_gem.py entry script, or an IDE.",
    ),
    SourceMeta(
        id="website.configuration",
        title="GEM-pRF configuration docs",
        kind="website",
        url="https://gemprf.github.io/configuration.html",
        local_path=_path("external/docs/configuration.md"),
        description="Website guidance that GEM-pRF is driven by XML configuration files and run through gp.run(config.xml).",
    ),
    SourceMeta(
        id="website.config_generator",
        title="GEM-pRF configuration generator",
        kind="website",
        url="https://gemprf.github.io/gemprf-configs/config_generator.html",
        local_path=_path("external/docs/gemprf-configs/config_generator.md"),
        description="Public generator listing available XML parameters and their UI labels.",
    ),
    SourceMeta(
        id="website.input_sources",
        title="GEM-pRF input source tutorial",
        kind="website",
        url="https://gemprf.github.io/tutorials/input-source-tutorials/input-source-selection-tutorial.html",
        local_path=_path("external/docs/tutorials/input-source-selection-tutorial.md"),
        description="Tutorial describing BIDS and fixed-path input modes plus example data setups.",
    ),
    SourceMeta(
        id="website.download",
        title="GEM-pRF download page",
        kind="website",
        url="https://gemprf.github.io/download_gemprf.html",
        local_path=_path("external/docs/download_gemprf.md"),
        description="Download instructions: PyPI install, source-code option, and a sample-config download.",
    ),
    SourceMeta(
        id="website.cite",
        title="GEM-pRF citation page",
        kind="website",
        url="https://gemprf.github.io/cite.html",
        local_path=_path("external/docs/cite.md"),
        description="Citation guidance for the paper, the documentation Zenodo DOI, and the PyPI version.",
    ),
    SourceMeta(
        id="website.team",
        title="GEM-pRF team page",
        kind="website",
        url="https://gemprf.github.io/team.html",
        local_path=_path("external/docs/team.md"),
        description="Team roster (Mittal, Woletz, Linhardt, Windischberger) and Windischberger Lab credit.",
    ),
    SourceMeta(
        id="website.support",
        title="GEM-pRF support page",
        kind="website",
        url="https://gemprf.github.io/support.html",
        local_path=_path("external/docs/support.md"),
        description="Support form and pre-contact pointers to installation/running/configuration/tutorials docs.",
    ),
    SourceMeta(
        id="website.tutorials_index",
        title="GEM-pRF tutorials index",
        kind="website",
        url="https://gemprf.github.io/tutorials.html",
        local_path=_path("external/docs/tutorials.md"),
        description="Top-level tutorials landing page (currently a work-in-progress index).",
    ),
    SourceMeta(
        id="website.search",
        title="GEM-pRF search page",
        kind="website",
        url="https://gemprf.github.io/search.html",
        local_path=_path("external/docs/search.md"),
        description="Site search entry point.",
    ),
    SourceMeta(
        id="website.tutorial.config_file",
        title="GEM-pRF tutorial — configuration file",
        kind="website",
        url="https://gemprf.github.io/tutorials/config-tutorials/config_file.html",
        local_path=_path("external/docs/tutorials/config-tutorials/config_file.md"),
        description="Tutorial on the XML config file workflow with gp.run() and links to generator/archive.",
    ),
    SourceMeta(
        id="website.tutorial.grid_or_refine_fit",
        title="GEM-pRF tutorial — grid or refine fit",
        kind="website",
        url="https://gemprf.github.io/tutorials/fitting-tutorials/grid-or-refine-fit.html",
        local_path=_path("external/docs/tutorials/fitting-tutorials/grid-or-refine-fit.md"),
        description="Tutorial comparing grid-only vs grid+refine fitting strategies and the matching XML knobs.",
    ),
    SourceMeta(
        id="website.config_archive_index",
        title="GEM-pRF configuration archive index",
        kind="website",
        url="https://gemprf.github.io/gemprf-configs/list-configs-archive.html",
        local_path=_path("external/docs/gemprf-configs/list-configs-archive.md"),
        description="Index of versioned sample configurations for older GEM-pRF releases.",
    ),
    SourceMeta(
        id="website.config_archive.v0_1_10",
        title="GEM-pRF v0.1.10 archived sample config",
        kind="config",
        url="https://gemprf.github.io/assets/gemprf_config/config-archive/v0.1.10_sample_config.xml",
        local_path=_path("external/docs/gemprf-configs/config-archive/v0.1.10_sample_config.xml"),
        description="Sample XML configuration shipped with GEM-pRF v0.1.10 (archived release).",
    ),
    SourceMeta(
        id="website.config_archive.v0_1_11",
        title="GEM-pRF v0.1.11 archived sample config",
        kind="config",
        url="https://gemprf.github.io/assets/gemprf_config/config-archive/v0.1.11_sample_config.xml",
        local_path=_path("external/docs/gemprf-configs/config-archive/v0.1.11_sample_config.xml"),
        description="Sample XML configuration shipped with GEM-pRF v0.1.11 (archived release).",
    ),
    SourceMeta(
        id="repo.readme",
        title="GEMpRF-DemoKit README",
        kind="repo",
        local_path=_path("external/GEMpRF-DemoKit/README.md"),
        description="DemoKit overview with sample configs and GPU memory utility notes.",
    ),
    SourceMeta(
        id="repo.sample_config",
        title="GEMpRF-DemoKit sample_config.xml",
        kind="repo",
        local_path=_path("external/GEMpRF-DemoKit/sample_configs/sample_config.xml"),
        description="Sample GEM-pRF XML config used as an example of real parameter values.",
    ),
    SourceMeta(
        id="repo.gpu_info",
        title="GEMpRF-DemoKit gpu_info utility",
        kind="repo",
        local_path=_path("external/GEMpRF-DemoKit/utils/gpu_info.py"),
        description="Demo utility that estimates GPU memory capacity from grid size, stimulus size, and dtype.",
    ),
    SourceMeta(
        id="code.config_manager",
        title="gem.configs.config_manager",
        kind="code",
        local_path=_path("external/pypi/gemprf_wheel/gem/configs/config_manager.py"),
        description="XML parsing logic that turns config attributes into runtime configuration fields.",
    ),
    SourceMeta(
        id="code.init_setup",
        title="gem.init_setup",
        kind="code",
        local_path=_path("external/pypi/gemprf_wheel/gem/init_setup.py"),
        description="Setup flow that validates config version, manages CUDA_VISIBLE_DEVICES, and builds the pRF space.",
    ),
    SourceMeta(
        id="code.run_analysis",
        title="gem.run.run_gem_prf_analysis",
        kind="code",
        local_path=_path("external/pypi/gemprf_wheel/gem/run/run_gem_prf_analysis.py"),
        description="Main analysis code that loads stimulus, HRF, search space, orthogonalization matrix, and fitting flow.",
    ),
    SourceMeta(
        id="code.prf_stimulus",
        title="gem.model.prf_stimulus",
        kind="code",
        local_path=_path("external/pypi/gemprf_wheel/gem/model/prf_stimulus.py"),
        description="Stimulus handling code covering binarization, resampling, HRF convolution, and high temporal resolution metadata.",
    ),
    SourceMeta(
        id="code.orthogonalization",
        title="gem.signals.orthogonalization_matrix",
        kind="code",
        local_path=_path("external/pypi/gemprf_wheel/gem/signals/orthogonalization_matrix.py"),
        description="Implementation of the orthogonalization matrix driven by nDCT.",
    ),
    SourceMeta(
        id="code.hrf_generator",
        title="gem.signals.hrf_generator",
        kind="code",
        local_path=_path("external/pypi/gemprf_wheel/gem/signals/hrf_generator.py"),
        description="SPM-style HRF function used by GEM-pRF.",
    ),
    SourceMeta(
        id="code.signal_synthesizer",
        title="gem.signals.signal_synthesizer",
        kind="code",
        local_path=_path("external/pypi/gemprf_wheel/gem/signals/signal_synthesizer.py"),
        description="GPU signal generation code that shows how signal counts and high temporal downsampling affect compute.",
    ),
    SourceMeta(
        id="code.bids_handler",
        title="gem.data.bids_handler",
        kind="code",
        local_path=_path("external/pypi/gemprf_wheel/gem/data/bids_handler.py"),
        description="BIDS input resolution logic including input_file_extension validation and result path rules.",
    ),
)

MANUAL_DOCUMENTS: tuple[Document, ...] = (
    Document(
        page_content=(
            "GEM-pRF paper abstract (Mittal et al., Medical Image Analysis 109, 2026, article 103891; DOI 10.1016/j.media.2025.103891). Population receptive field (pRF) mapping is a fundamental "
            "technique for understanding retinotopic organisation of the human visual system. Since its introduction "
            "in 2008, however, its scalability has been severely hindered by the computational bottleneck of iterative "
            "parameter refinement. Current state-of-the-art implementations either sacrifice precision for speed or "
            "rely on slow iterative parameter updates, limiting their applicability to large-scale datasets. Here, we "
            "present a novel mathematical reformulation of the General Linear Model (GLM), wrapped in a GPU-Empowered "
            "Mapping of population Receptive Fields (GEM-pRF) software implementation. By orthogonalizing the design "
            "matrix, our approach enables the direct and fast computation of the objective function's derivatives, "
            "which are used to eliminate the iterative refinement process. This approach dramatically accelerates pRF "
            "estimation with high accuracy. Validation using empirical and simulated data confirms GEM-pRF's accuracy, "
            "and benchmarking against established tools demonstrates a reduction in computation time of almost two "
            "orders of magnitude. With its modular and extensible design, GEM-pRF provides a critical advancement "
            "for large-scale fMRI retinotopic mapping."
        ),
        metadata={"source_id": "paper.abstract"},
    ),
    Document(
        page_content=(
            "GEM-pRF website quickstart. The docs present GEM-pRF as a standalone, plug-and-play tool for pRF mapping. "
            "The website points users to the installation guide first and then to running GEM-pRF with an XML config. "
            "The docs repeatedly emphasize that analysis behavior is controlled through configuration rather than code edits."
        ),
        metadata={"source_id": "website.quickstart"},
    ),
    Document(
        page_content=(
            "V4 in the GEM-pRF paper. V4 is a visual area region of the human visual cortex. The paper introduction names V1, V2, VP, V3, "
            "and V4 together as visual area regions that Sereno et al. (1995) functionally segmented on the cortical surface using "
            "fMRI-based retinotopic mapping with periodic visual stimulation. The paper cites V4 only in this context and does not "
            "define its functional role beyond naming it as a visual area."
        ),
        metadata={"source_id": "paper.full"},
    ),
    Document(
        page_content=(
            "V1 in the GEM-pRF paper. V1 is the primary visual cortex. The paper uses V1 as the region of interest for single-step fine "
            "fitting validation on the first 22 subjects of the NYU retinotopy dataset, as the ROI for the empirical comparison against "
            "mrVista, and as the cortical area shown in the eccentricity, polar angle, and pRF size retinotopic maps generated for "
            "representative subject wlsubj001."
        ),
        metadata={"source_id": "paper.full"},
    ),
    Document(
        page_content=(
            "GEM-pRF running guide. The docs describe three execution modes. Option A (recommended) is to import the package and call "
            "gp.run(config_xml_path) from any Python context. Option B runs the repo entry script python run_gem.py PATH_TO_XML. "
            "Option C opens the source code in VS Code or PyCharm and edits run_gem.py to point at the config. All three modes rely on "
            "a CuPy build that matches the installed CUDA runtime."
        ),
        metadata={"source_id": "website.running"},
    ),
    Document(
        page_content=(
            "GEM-pRF configuration docs. The website states that the XML configuration file is the heart of GEM-pRF. "
            "The public guidance says all analysis settings, paths, and parameters live in the XML, while Python usage stays small: "
            "import gemprf as gp and call gp.run(config_path). The docs recommend meaningful XML naming and treat the XML as the reproducible record of an analysis."
        ),
        metadata={"source_id": "website.configuration"},
    ),
    Document(
        page_content=(
            "GEM-pRF installation page. The public install docs say GEM-pRF requires an NVIDIA GPU, CUDA, a matching CuPy build, and the gemprf package. "
            "The workflow is create environment, verify CUDA, install CuPy, install gemprf, then run the package with XML configs."
        ),
        metadata={"source_id": "website.installation"},
    ),
    Document(
        page_content=(
            "GEM-pRF input source tutorial. The tutorial says GEM-pRF accepts either BIDS-organized inputs or fixed file paths, both controlled through XML. "
            "The examples cover surface and volume inputs and use the DemoKit to demonstrate how path fixing and source selection work."
        ),
        metadata={"source_id": "website.input_sources"},
    ),
    Document(
        page_content=(
            ".gii (GIFTI) in GEM-pRF. .gii is one of three values the BIDS input_file_extension field accepts (alongside .nii.gz and both). "
            "GEM-pRF processes only filenames matching _bold.func.gii, which corresponds to surface data typically produced by fMRIPrep. "
            "The ObservedData loader reads .gii files as nib.gifti.GiftiImage objects, which contain one or more data arrays. "
            "The BIDS handler validates input_file_extension and aborts with a validation error on any value other than .nii.gz, .gii, or both."
        ),
        metadata={"source_id": "website.config_generator"},
    ),
    Document(
        page_content=(
            ".nii.gz (NIfTI) in GEM-pRF. .nii.gz is one of three values the BIDS input_file_extension field accepts (alongside .gii and both). "
            "GEM-pRF processes only filenames matching _bold.nii.gz, which corresponds to volumetric fMRI data; volumetric files are flattened before analysis. "
            "The website's config generator and the sample configs also require the stimulus directory to be in NIfTI format."
        ),
        metadata={"source_id": "website.config_generator"},
    ),
    Document(
        page_content=(
            "both (input_file_extension) in GEM-pRF. The value both is one of three options the BIDS input_file_extension field accepts (alongside .nii.gz and .gii). "
            "Selecting both makes the BIDS handler load every available variant — surface (.gii) and volume (.nii.gz) files — for the requested analysis."
        ),
        metadata={"source_id": "website.config_generator"},
    ),
    Document(
        page_content=(
            "fsnative in GEM-pRF. fsnative is one of four values the BIDS space field accepts (alongside fsaverage, T1w, and all). "
            "fsnative refers to each subject's own FreeSurfer cortical surface space; the BIDS handler filters derivatives to this per-subject surface. "
            "Selecting all overrides the per-subject choice and loads every available space variant."
        ),
        metadata={"source_id": "website.config_generator"},
    ),
    Document(
        page_content=(
            "fsaverage in GEM-pRF. fsaverage is one of four values the BIDS space field accepts (alongside fsnative, T1w, and all). "
            "fsaverage refers to the FreeSurfer group-averaged cortical surface space; the BIDS handler filters derivatives to this group surface. "
            "Selecting all overrides the per-subject choice and loads every available space variant."
        ),
        metadata={"source_id": "website.config_generator"},
    ),
    Document(
        page_content=(
            "T1w in GEM-pRF. T1w is one of four values the BIDS space field accepts (alongside fsnative, fsaverage, and all). "
            "T1w refers to the volumetric (T1-weighted) reference space; the BIDS handler filters derivatives to this volumetric space. "
            "Selecting all overrides the per-subject choice and loads every available space variant."
        ),
        metadata={"source_id": "website.config_generator"},
    ),
    Document(
        page_content=(
            "all (space) in GEM-pRF. The value all is one of four options the BIDS space field accepts (alongside fsnative, fsaverage, and T1w). "
            "Selecting all overrides any per-subject space choice and loads every available variant — fsnative, fsaverage, and T1w — that the derivatives contain."
        ),
        metadata={"source_id": "website.config_generator"},
    ),
    Document(
        page_content=(
            "Individual run type in GEM-pRF. Individual is one of two values the BIDS run_type field accepts (the other is concatenated). "
            "The website's config generator describes Individual Task Analysis as: exactly one task name (no all, no spaces or commas), "
            "with Session and Run as comma-separated values or all. The BIDS handler treats this as run_type=individual, "
            "where the user may specify multiple session/run values for a single task and the handler resolves them to a flat list of matching files."
        ),
        metadata={"source_id": "website.config_generator"},
    ),
    Document(
        page_content=(
            "Concatenated run type in GEM-pRF. Concatenated is one of two values the BIDS run_type field accepts (the other is individual). "
            "The website's config generator describes Concatenated Analysis as a list of concatenate_item blocks — each item needs ses, task, and run, "
            "with one value each (no spaces or commas). The BIDS handler iterates through the concatenate_item blocks and gathers the matching files per block, "
            "driving task-specific stimulus handling."
        ),
        metadata={"source_id": "website.config_generator"},
    ),
    # --- External tools and pipelines named in the corpus ---
    Document(
        page_content=(
            "fMRIPrep in GEM-pRF. The paper reports that the NYU dataset preprocessing was carried out by the dataset authors using fMRIPrep v20.0.1 (Esteban et al., 2019). "
            "Anatomical preprocessing included intensity inhomogeneity correction, skull-stripping, tissue segmentation, and cortical surface reconstruction with FreeSurfer. "
            "Functional preprocessing involved distortion correction with topup, motion correction, slice-time correction, and co-registration of functional to anatomical images, applied in a single interpolation step; "
            "preprocessed functional data were resampled to individual cortical surfaces. "
            "The website's input-source tutorial lists fMRIPrep as one of the two BIDS-derivative input styles GEM-pRF accepts (alongside prfprepare)."
        ),
        metadata={"source_id": "paper.full"},
    ),
    Document(
        page_content=(
            "FreeSurfer in GEM-pRF. The paper names FreeSurfer as the tool fMRIPrep used for cortical surface reconstruction during anatomical preprocessing of the NYU dataset (Esteban et al., 2019). "
            "The BIDS space field uses FreeSurfer-derived spaces — fsnative (per-subject surface) and fsaverage (group-averaged surface) — as two of its four allowed values."
        ),
        metadata={"source_id": "paper.full"},
    ),
    Document(
        page_content=(
            "prfprepare in GEM-pRF. The website's input-source tutorial names prfprepare as one of the two BIDS-derivative input styles GEM-pRF accepts for surface data (the other is fMRIPrep). "
            "DemoKit example 001 demonstrates BIDS + prfprepare (surface, individual runs); example 005 demonstrates fixed paths + prfprepare (surface). "
            "The corpus does not contain a deeper definition of prfprepare beyond this usage."
        ),
        metadata={"source_id": "website.input_sources"},
    ),
    Document(
        page_content=(
            "mrVista in the GEM-pRF paper. mrVista (Dumoulin and Wandell, 2008) is one of the two most-used pRF mapping software packages and follows the gold-standard, "
            "two-step coarse-then-refine fitting approach. mrVista is CPU-only, which results in long processing times for large datasets. "
            "The paper benchmarks GEM-pRF against mrVista's prfanalyze-vista Docker container (version 2.3.1_3.1.2; Lerma-Usabiaga et al., 2020) on V1 of the NYU dataset. "
            "Across roughly 1.65 million voxels, agreement was Pearson r = 1.00 for μx, μy, and ρ², and r = 0.98 for σ. "
            "GEM-pRF was nearly two orders of magnitude faster than mrVista on the same task."
        ),
        metadata={"source_id": "paper.full"},
    ),
    Document(
        page_content=(
            "prfanalyze-vista in the GEM-pRF paper. prfanalyze-vista is the Docker container distribution of mrVista (version 2.3.1_3.1.2; Lerma-Usabiaga et al., 2020) "
            "used in the paper's empirical comparison. The paper computes mrVista pRF estimates with its default configuration through this container."
        ),
        metadata={"source_id": "paper.full"},
    ),
    Document(
        page_content=(
            "SamSrf in the GEM-pRF paper. SamSrf (D. Sam Schwarzkopf, 2018) is one of the two most-used pRF mapping software packages, alongside mrVista. "
            "Both follow the gold-standard, straight-forward two-fitting-step approach but are limited to CPU-only computation, resulting in long processing times for large datasets."
        ),
        metadata={"source_id": "paper.full"},
    ),
    Document(
        page_content=(
            "BIDS in GEM-pRF. The website tutorial and config generator describe BIDS (Brain Imaging Data Structure) as one of two data-organization types for GEM-pRF inputs (the other is Fixed Paths). "
            "For BIDS inputs, GEM-pRF locates files based on subject and session, with options for run type (individual or concatenated), space (fsnative, fsaverage, T1w, or all), "
            "input file extension (.nii.gz, .gii, or both), hemisphere, subjects, and analysis ID. "
            "The paper's empirical analyses use the NYU retinotopy dataset organised in BIDS format and preprocessed with fMRIPrep."
        ),
        metadata={"source_id": "website.input_sources"},
    ),
    Document(
        page_content=(
            "GEMpRF-DemoKit. The DemoKit is a separate repository (github.com/siddmittal/GEMpRF-DemoKit) containing sample fMRI/MRI data and example XML configurations. "
            "Its top-level runner run_gemprf_demo.py exposes an interactive menu of examples 001–005, covering different input source configurations: "
            "BIDS + prfprepare (surface), BIDS + fMRIPrep (surface, volume, or both), and fixed paths + prfprepare (surface). "
            "The demo automatically updates XML config paths to the local DemoKit checkout, performs a GPU memory check, and then calls gp.run() with the selected configuration."
        ),
        metadata={"source_id": "repo.readme"},
    ),
    Document(
        page_content=(
            "V2 in the GEM-pRF paper. V2 is a visual area region of the human visual cortex. The paper introduction names V1, V2, VP, V3, and V4 together "
            "as visual area regions that Sereno et al. (1995) functionally segmented on the cortical surface using fMRI-based retinotopic mapping with periodic visual stimulation. "
            "The paper does not define V2's functional role beyond naming it as a visual area."
        ),
        metadata={"source_id": "paper.full"},
    ),
    Document(
        page_content=(
            "V3 in the GEM-pRF paper. V3 is a visual area region of the human visual cortex. The paper introduction names V1, V2, VP, V3, and V4 together "
            "as visual area regions that Sereno et al. (1995) functionally segmented on the cortical surface using fMRI-based retinotopic mapping with periodic visual stimulation. "
            "The paper does not define V3's functional role beyond naming it as a visual area."
        ),
        metadata={"source_id": "paper.full"},
    ),
    Document(
        page_content=(
            "VP in the GEM-pRF paper. VP is a visual area region of the human visual cortex. The paper introduction names V1, V2, VP, V3, and V4 together "
            "as visual area regions that Sereno et al. (1995) functionally segmented on the cortical surface using fMRI-based retinotopic mapping with periodic visual stimulation. "
            "The paper does not define VP's functional role beyond naming it as a visual area."
        ),
        metadata={"source_id": "paper.full"},
    ),
    Document(
        page_content=(
            "NYU retinotopy dataset in the GEM-pRF paper. The NYU retinotopy dataset is the empirical fMRI dataset the paper uses for validation. "
            "The single-step fine-fitting comparison (Section 2.7 / 3.1) is restricted to V1 of the first 22 subjects of the NYU dataset. "
            "The head-to-head comparison against mrVista uses V1 of the NYU dataset across n = 1,649,655 voxels. "
            "The NYU stimulus has a 24.8° diameter, and the paper uses a 187 × 187 × 24 sampling space (positions × pRF sizes) for these analyses. "
            "NYU data was preprocessed by the dataset authors using fMRIPrep v20.0.1 and FreeSurfer."
        ),
        metadata={"source_id": "paper.full"},
    ),
    Document(
        page_content=(
            "wlsubj001 in the GEM-pRF paper. wlsubj001 is the representative subject from the NYU retinotopy dataset for which the paper generates retinotopic maps — "
            "eccentricity, polar angle, and pRF size — together with a V1 coverage map, using the plotting function in github.com/dlinhardt/prfclass. "
            "The maps are derived from the joint analysis of 12 runs for this subject at the same 187 × 187 × 24 grid configuration used elsewhere in the paper."
        ),
        metadata={"source_id": "paper.full"},
    ),
    Document(
        page_content=(
            "HCP (Human Connectome Project) in the GEM-pRF paper. The paper references the HCP dataset (Benson et al., 2018) only in its discussion of related work: "
            "Ribeiro et al. (2021) trained a geometric deep-learning model on HCP to predict retinotopy maps from anatomical brain segmentation alone, without requiring functional scans. "
            "GEM-pRF itself does not use HCP data."
        ),
        metadata={"source_id": "paper.full"},
    ),
    Document(
        page_content=(
            "Why GEM-pRF's accuracy matches mrVista (paper §4.5 Speed, second paragraph). The paper explicitly attributes the parity to a shared mathematical core: "
            "'The underlying mathematics for GEM-pRF is a reformulated version of the originally proposed pRF mapping methodology by Dumoulin and Wandell (2008). "
            "Therefore, the pRF parameters and retinotopic maps calculated with GEM-pRF are similar to those obtained by the mrVista gold-standard approach.' "
            "In other words, GEM-pRF is a reformulated, equivalent solver of the same GLM problem mrVista solves; the empirical parity (Pearson r = 1.00 for μx, μy, ρ²; r = 0.98 for σ across ~1.65 million NYU voxels) is a consequence of that equivalence, not a coincidence of tuning. "
            "This is the paper's stated rationale for why GEM-pRF's accuracy holds up under empirical comparison."
        ),
        metadata={"source_id": "paper.full"},
    ),
    Document(
        page_content=(
            "What happens if GPU memory is exceeded in GEM-pRF (paper §4.8 Scalability). The paper states the user-facing constraint directly: "
            "'GEM-pRF employs a batching procedure to handle memory-intensive execution steps on GPUs. Since the estimation of pRF parameters for each voxel's fMRI time series y is independent, the minimum batch size can even be reduced to a single voxel. "
            "However, during coarse fitting, the vector projection of a voxel's fMRI time series y is computed with respect to all prediction time courses, so the current implementation requires holding all prediction time series data in GPU memory. "
            "The user must select a sampling space Θ configuration such that the prediction time courses fit in available GPU memory.' "
            "So if a configuration would exceed GPU memory, the paper's prescribed remedy is to reduce the sampling-space density (fewer points in the Θ grid) until the prediction time courses fit. "
            "GEM-pRF cannot transparently fall back to CPU for this step — coarse fitting requires the prediction time courses to be GPU-resident."
        ),
        metadata={"source_id": "paper.full"},
    ),
    Document(
        page_content=(
            "GEM-pRF math symbol glossary (paper notation). "
            "θ (theta) = a parameter combination for the pRF model; θ ∈ R^K. For the 2D Gaussian pRF used in the paper, K = 3 and θ = (μx, μy, σ). "
            "Θ (capital theta) = the set of N candidate parameter combinations searched during coarse fitting; θ ∈ Θ. "
            "θ̂ (theta hat) = the best-fitting parameter combination that maximises the objective function. "
            "θ̂_c = the best-fitting coarse parameter combination from the discrete grid Θ. "
            "ê (e-hat) = the residual vector between the measured fMRI time course y and the prediction ŷ; ê = [I − X(X^T X)^(−1) X^T] y (Eq. 3). "
            "ê^T ê = residual sum of squares (RSS) — the quantity ordinary least squares minimises. "
            "X = the design matrix, X = [p(θ) R] (Eq. 2). "
            "X' = the orthonormalized version of the design matrix, X' = [p'(θ) R] (Eq. 4). "
            "R = the regressor matrix. The paper states that R may contain different nuisance regressors and low-frequency functions, but for the purpose of this work must at least contain a constant term. The paper itself does not give a rationale for the constant-term requirement. "
            "p(θ) = the pRF model time course for parameter combination θ. "
            "p'(θ) = the orthogonalised and normalised prediction time course (orthogonal to R). "
            "C(θ) = the objective function maximised during fitting; C(θ) = y^T p'(θ) (Eq. 6). Maximising C(θ) corresponds to finding the prediction time course that minimises residual error. "
            "f_ij(θ) = the pRF as a function of θ at visual-field spatial position (i, j). "
            "h(t) = the haemodynamic response function (HRF) describing the linear BOLD response to a neural event. "
            "S_ij(t) = the visual stimulus indicator at spatial position (i, j) and time t; Ŝ_ij is the time-aggregated stimulus. "
            "y = the measured fMRI time course; ŷ = the prediction (the projection of y onto the column space of the design matrix X, used implicitly in Eq. 3 ê = [I − X(X^T X)^(−1) X^T] y). The paper notes elsewhere that its reformulation eliminates the need to compute beta weights explicitly. "
            "K = the number of parameters per pRF model (3 for the 2D Gaussian)."
        ),
        metadata={"source_id": "paper.full"},
    ),
    Document(
        page_content=(
            "GEM-pRF acronym glossary. "
            "GEM-pRF = GPU-Empowered Mapping of population Receptive Fields — also written GPU-empowered mapping of population receptive fields in the paper title. "
            "pRF = population receptive field. "
            "fMRI = functional magnetic resonance imaging. "
            "BOLD = blood-oxygen-level-dependent (signal) — the contrast that fMRI measures, modelled with the HRF. "
            "HRF = haemodynamic response function — the linear response of the BOLD signal to a neural event, denoted h(t). "
            "GLM = General Linear Model — the statistical framework GEM-pRF reformulates. "
            "RSS = residual sum of squares; ê^T ê. "
            "ROI = region of interest (e.g. V1 used in the paper's validation). "
            "GPU = graphics processing unit; HPC = high-performance computing (the paper benchmarks on a consumer laptop and an HPC node). "
            "DoG = Difference of Gaussians — an alternative pRF model the paper discusses but does not implement as a default. "
            "BIDS = Brain Imaging Data Structure — one of the input organisations GEM-pRF accepts via its XML config. "
            "NYU = New York University — provider of the retinotopy dataset used for empirical validation. "
            "HCP = Human Connectome Project — referenced only in related-work discussion. "
            "SIMD = Single Instruction, Multiple Data — a parallelism model relevant to GPU execution. "
            "BCI = brain–computer interface — the paper's introduction mentions BCI devices only as an application of retinotopic mapping, citing work on decoding visual information from cortical activity (Senden et al. 2019; Takagi and Nishimoto 2023). The paper does not present GEM-pRF itself as a BCI tool. "
            "DOI = Digital Object Identifier; the paper's DOI is 10.1016/j.media.2025.103891. "
            "FWF = the Austrian Science Fund — funder of the work, per the paper's Funding section (grant https://doi.org/10.55776/P35583). The paper uses 'Austrian Science Fund (FWF)' and does not give the German expansion."
        ),
        metadata={"source_id": "paper.full"},
    ),
    Document(
        page_content=(
            "GEM-pRF paper section index — full list of sections and their titles. "
            "1. Introduction. "
            "2. Methods (with subsections: 2.1 pRF modelling and fitting in GEM-pRF; 2.1.1 Coarse fitting; 2.1.2 Refine fitting; 2.1.2.1 Quadratic approximation for refinement; 2.1.3 Variance explained; 2.2 Multiple runs; 2.3 Sampling space; 2.4 Data transfer considerations; 2.5 Multi-GPU environment; 2.6 Data; 2.6.1 Simulated data; 2.6.2 Empirical data; 2.7 Validation of single-step fine fitting in GEM-pRF; 2.8 Comparison with state-of-the-art; 2.8.1 Comparison using simulated data; 2.8.2 Comparison using empirical data; 2.9 Retinotopic maps; 2.10 Performance analysis). "
            "3. Results (with subsections: 3.1 Validation of single-step fine-fitting in GEM-pRF; 3.2 Comparison with state-of-the-art; 3.2.1 Comparison using simulated data; 3.2.2 Comparison using empirical data; 3.3 Retinotopy maps; 3.4 Performance analysis). "
            "4. Discussion (with subsections: 4.1 Validation of single-step fine fitting in GEM-pRF; 4.2 Comparison using simulated data; 4.3 Comparison using empirical data; 4.4 Retinotopy maps; 4.5 Speed; 4.6 Sampling space; 4.7 Joint analysis; 4.8 Scalability; 4.9 Future scope of work). "
            "5. Conclusion. "
            "Back matter: Code availability; Funding; Key visual area references. "
            "Quick lookup of the most-asked sections: §2.4 is 'Data transfer considerations'; §4.5 is 'Speed'; §4.7 is 'Joint analysis'; §2.8 is 'Comparison with state-of-the-art'; §3.4 is 'Performance analysis'."
        ),
        metadata={"source_id": "paper.full"},
    ),
    Document(
        page_content=(
            "GEM-pRF paper metadata block (title, authorship, publication, funding). "
            "Title: 'GEM-pRF: GPU-empowered mapping of population receptive fields for large-scale fMRI analysis'. "
            "Authors: Siddharth Mittal, Michael Woletz, David Linhardt, Christian Windischberger. "
            "Affiliation / institute (verbatim from paper): High Field MR Center, Center for Medical Physics and Biomedical Engineering, Medical University of Vienna, Austria. The paper labels this as 'Affiliation' for all four authors, which conventionally identifies the research group / lab the work originates from. "
            "Corresponding author: Christian Windischberger (christian.windischberger@meduniwien.ac.at). "
            "Published in: Medical Image Analysis, volume 109 (2026), article 103891. "
            "DOI: 10.1016/j.media.2025.103891 (https://doi.org/10.1016/j.media.2025.103891). "
            "Keywords: Retinotopy; Population receptive fields; fMRI; General linear model; GPU-empowered pRF mapping. "
            "Funding / funder / institute that funded the work: Austrian Science Fund (FWF), grant https://doi.org/10.55776/P35583. "
            "Code: published on PyPI (https://pypi.org/project/gemprf/) with a demo kit at https://github.com/siddmittal/GEMpRF-DemoKit."
        ),
        metadata={"source_id": "paper.full"},
    ),
    Document(
        page_content=(
            "Additional Available GPUs in GEM-pRF. The configurator's Additional Available GPUs field "
            "(XML: /root/gpu/additional_available_gpus, populated as one or more <gpu> child elements) "
            "lists extra GPU device IDs to use alongside the Default GPU. At runtime gem.init_setup.manage_gpus "
            "parses the listed IDs, removes any duplicate of the Default GPU ID, sorts the rest, validates that "
            "every ID is in [0, max_available_gpus-1], and exports the combined set via os.environ['CUDA_VISIBLE_DEVICES']. "
            "If validation fails the error path falls back to using all detected GPUs. With more than one GPU ID "
            "exposed, gem.signals.signal_synthesizer.SignalSynthesizer.compute_signals_batches loops over GPU "
            "indices and dispatches per-GPU batches of the model-signal computation; with a single ID the loop "
            "runs once on that GPU."
        ),
        metadata={"source_id": "website.config_generator"},
    ),
    Document(
        page_content=(
            "Use Custom Parameters from File (Optional Analysis Parameters) in GEM-pRF. The configurator's "
            "'Use Custom Parameters from File' checkbox sets /root/search_space/optional_analysis_params/@enable=\"true\" "
            "and is the top-level switch that gates the per-section overrides — Use HRF from File, Use Sigmas from "
            "File, and Use Spatial Grid XY from File. The configurator also exposes a File Path field "
            "(@filepath) pointing at an HDF5 file. When the top-level enable is False the per-section flags are "
            "ignored and the analysis uses the values parsed from <default_hrf>, <default_sigmas>, and "
            "<default_spatial_grid>. When enable is True, each per-section flag is consulted independently: "
            "any subsection whose use_from_file is True loads its value from the configured H5 file at the "
            "per-subsection key; subsections with use_from_file=False still fall back to their default block."
        ),
        metadata={"source_id": "website.config_generator"},
    ),
    Document(
        page_content=(
            "Use HRF from File in GEM-pRF. The configurator's 'Use HRF from File' checkbox sets "
            "/root/search_space/optional_analysis_params/hrf/@use_from_file=\"true\" and is paired with an HRF Key "
            "field (@key, e.g. analysis_params/hrf_values). It only takes effect when the parent 'Use Custom "
            "Parameters from File' (optional_analysis_params/@enable) is True. When active, the run loader reads the "
            "HRF curve directly from the configured H5 file at the supplied key via H5FileManager.get_key_value and "
            "skips the SPM-style construction in spm_hrf_compat that would otherwise build the curve from the "
            "<default_hrf> attributes (TR, peak_delay, under_shoot_delay, peak_disp, under_disp, peak_to_undershoot, "
            "normalize). If the H5 read returns no value the run aborts with an explicit error. When inactive (or when "
            "optional_analysis_params is disabled), <default_hrf> is used in full."
        ),
        metadata={"source_id": "website.config_generator"},
    ),
    Document(
        page_content=(
            "Use Sigmas from File in GEM-pRF. The configurator's 'Use Sigmas from File' checkbox sets "
            "/root/search_space/optional_analysis_params/sigmas/@use_from_file=\"true\" with a Sigmas Key "
            "field (@key, e.g. analysis_params/sigmas). It only takes effect when 'Use Custom Parameters from File' "
            "(optional_analysis_params/@enable) is True. When active, the sigma grid is read from the configured H5 "
            "file at the supplied key, replacing the values that would otherwise be generated from <default_sigmas> "
            "(min_sigma, max_sigma, num_sigmas). When inactive, the run uses the <default_sigmas> attributes."
        ),
        metadata={"source_id": "website.config_generator"},
    ),
    Document(
        page_content=(
            "Normalize HRF in GEM-pRF. The configurator's 'Normalize HRF' checkbox under Default HRF Parameters "
            "maps to /root/search_space/default_hrf/@normalize. The flag is forwarded to spm_hrf_compat in "
            "gem.signals.hrf_generator, where, when True, the constructed HRF curve is divided by the sum of its "
            "values before being returned (so the curve sums to 1); when False, the unnormalised curve is returned "
            "as-is. This only affects the SPM-style HRF built from <default_hrf> attributes; if 'Use HRF from File' "
            "is enabled the curve is loaded from H5 and Normalize HRF has no effect."
        ),
        metadata={"source_id": "website.config_generator"},
    ),
    Document(
        page_content=(
            "Write Debug Info in GEM-pRF. The configurator's 'Write Debug Info' checkbox under Search Space maps "
            "to /root/search_space/@write_debug_info. When True the run initialises gem.utils.gem_write_to_file."
            "GemWriteToFile (a singleton) with debugging_enabled=True and writes a sibling file debug_model_data.h5 "
            "in the analysis result directory. The file accumulates intermediate analysis arrays under hierarchical "
            "HDF5 paths via repeated write_array_to_h5 calls — including the pRF spatial grid, the HRF curve, the "
            "stimulus resampled and HRF-convolved arrays, the model-signal batches, the orthogonalisation matrix, "
            "and per-parameter derivative and orthonormalised model-signal variants. When False, GemWriteToFile is "
            "initialised in a no-op mode and no debug_model_data.h5 is produced."
        ),
        metadata={"source_id": "website.config_generator"},
    ),
    Document(
        page_content=(
            "Binarization in GEM-pRF. The configurator's Binarization toggle (XML: "
            "/root/stimulus/binarization/@enable, paired with /root/stimulus/binarization/@threshold) controls "
            "whether the loaded stimulus is binarised after read. When @enable=\"True\", the stimulus loader "
            "(gem.model.prf_stimulus.PRFStimulus.__init__) first checks whether the loaded array already contains "
            "only 0 and 1; if it does, no transformation is applied. If the stimulus contains other values, the "
            "loader logs a yellow warning ('Warning: Stimulus data contains values other than 0 and 1. "
            "Binarizing...') and converts the array element-wise: every value strictly greater than @threshold is "
            "set to 1, every other value is set to 0, and the array is cast to numpy uint8. When @enable=\"False\", "
            "the stimulus is loaded unchanged regardless of @threshold. @threshold is parsed as a float; the sample "
            "config default is 0, which means any value greater than 0 becomes 1."
        ),
        metadata={"source_id": "website.config_generator"},
    ),
    Document(
        page_content=(
            "High Temporal Resolution in GEM-pRF. The configurator's High Temporal Resolution section (XML: "
            "/root/stimulus/high_temporal_resolution with attributes @enable, @num_frames_downsampled, "
            "@slice_time_ref) configures stimulus-to-fMRI temporal alignment when the supplied stimulus has more "
            "frames than the fMRI timecourse. When @enable=\"true\", the run reads @num_frames_downsampled (int) "
            "and @slice_time_ref (float) and passes them to PRFStimulus; the signal synthesizer "
            "(gem.signals.signal_synthesizer.SignalSynthesizer.compute_signals_batches) then downsamples the "
            "synthesised model signals along time so the output length equals @num_frames_downsampled. The "
            "downsampling indices are computed as np.linspace(0, num_high_res_frames, num_frames_downsampled, "
            "endpoint=False, dtype=int) and then shifted by round(np.diff(idx).mean() * slice_time_ref); "
            "@slice_time_ref scales the within-bin offset applied to each downsample index. If "
            "@num_frames_downsampled exceeds the actual number of stimulus frames, the run aborts with a red "
            "error. When @enable=\"false\", the stimulus frame count is used as-is and @num_frames_downsampled "
            "and @slice_time_ref are ignored."
        ),
        metadata={"source_id": "website.config_generator"},
    ),
    Document(
        page_content=(
            "Stimulus Directory and Visual Field Radius in GEM-pRF. The stimulus geometry section groups three "
            "fields: /root/stimulus/directory (filesystem path; the loader source comment states 'The file paths "
            "are resolved relative to the current Python script file instead of the current working directory "
            "(cwd)' and the code calls os.path.join(os.path.dirname(os.path.abspath(__file__)), relative_file_path)), "
            "/root/stimulus/visual_field (the half-width of the stimulus coordinate range in degrees of visual "
            "angle; the loader uses this to build a symmetric coordinate grid from -visual_field to +visual_field "
            "along both axes via np.linspace), and /root/stimulus/width and /root/stimulus/height (the resampled "
            "stimulus pixel grid). The /root/stimulus@comment attribute notes 'Only in Nifti Format'."
        ),
        metadata={"source_id": "website.config_generator"},
    ),
    Document(
        page_content=(
            "Time Range t in GEM-pRF Default HRF. The configurator's 'Time Range t' field under Default HRF "
            "Parameters maps to /root/search_space/default_hrf/@t and is parsed as a tuple (start, stop) of seconds. "
            "Only effective when 'Use HRF from File' is unchecked. At runtime, the analysis appends the TR (or the "
            "stimulus header's pixdim[4] if the configurator's TR field is empty) as the third value, then calls "
            "np.arange(start, stop, TR) to build the time grid sampled by the SPM HRF. The sample config default is "
            "t=\"(0, 45)\", giving a 45-second support window."
        ),
        metadata={"source_id": "website.config_generator"},
    ),
    Document(
        page_content=(
            "TR in GEM-pRF Default HRF. The configurator's TR field under Default HRF Parameters maps to "
            "/root/search_space/default_hrf/@TR and is the repetition time in seconds used as the sample step when "
            "constructing the SPM-style HRF curve via np.arange(start, stop, TR). When the field is empty (TR is "
            "None), the run reads pixdim[4] from the stimulus NIfTI header and logs a yellow message that the HRF "
            "time-grid step has been set from the stimulus TR. Only effective when 'Use HRF from File' is "
            "unchecked. The sample config default is TR=\"1.0\"."
        ),
        metadata={"source_id": "website.config_generator"},
    ),
    Document(
        page_content=(
            "Peak Delay in GEM-pRF Default HRF. The configurator's Peak Delay field maps to "
            "/root/search_space/default_hrf/@peak_delay (float, seconds) and is forwarded to spm_hrf_compat as the "
            "peak_delay argument: the time of the gamma peak that models the positive lobe of the haemodynamic "
            "response. Only effective when 'Use HRF from File' is unchecked. The function uses peak_delay/peak_disp "
            "as the gamma shape parameter, with peak_disp as scale. Validation: spm_hrf_compat raises ValueError if "
            "peak_delay <= 0. The spm_hrf_compat function-signature default is 6 seconds; the configurator's sample "
            "value is 6.16."
        ),
        metadata={"source_id": "website.config_generator"},
    ),
    Document(
        page_content=(
            "Undershoot Delay in GEM-pRF Default HRF. The configurator's Undershoot Delay field maps to "
            "/root/search_space/default_hrf/@under_shoot_delay (float, seconds) and is forwarded to spm_hrf_compat "
            "as the under_delay argument: the time of the gamma peak that models the negative lobe (post-stimulus "
            "undershoot) of the haemodynamic response. Only effective when 'Use HRF from File' is unchecked. The "
            "function uses under_delay/under_disp as the gamma shape parameter for the undershoot lobe. Validation: "
            "spm_hrf_compat raises ValueError if under_shoot_delay <= 0. The spm_hrf_compat function-signature "
            "default is 16 seconds; the configurator's sample value is 12.0."
        ),
        metadata={"source_id": "website.config_generator"},
    ),
    Document(
        page_content=(
            "Peak Dispersion in GEM-pRF Default HRF. The configurator's Peak Dispersion field maps to "
            "/root/search_space/default_hrf/@peak_disp (float) and is forwarded to spm_hrf_compat as the peak_disp "
            "argument: the width (dispersion) of the peak gamma. It serves both as the divisor of peak_delay (to "
            "form the gamma shape) and as the scale parameter of the gamma distribution. Only effective when 'Use "
            "HRF from File' is unchecked. Validation: spm_hrf_compat raises ValueError if peak_disp <= 0. The "
            "spm_hrf_compat function-signature default is 1; the configurator's sample value is 0.85. Smaller "
            "peak_disp produces a sharper peak."
        ),
        metadata={"source_id": "website.config_generator"},
    ),
    Document(
        page_content=(
            "Undershoot Dispersion in GEM-pRF Default HRF. The configurator's Undershoot Dispersion field maps to "
            "/root/search_space/default_hrf/@under_disp (float) and is forwarded to spm_hrf_compat as the under_disp "
            "argument: the width (dispersion) of the undershoot gamma. It serves as both the divisor of "
            "under_shoot_delay (to form the gamma shape) and the scale parameter of the gamma distribution. Only "
            "effective when 'Use HRF from File' is unchecked. Validation: spm_hrf_compat raises ValueError if "
            "under_disp <= 0. The spm_hrf_compat function-signature default is 1; the configurator's sample value "
            "is 0.82. Smaller under_disp produces a sharper undershoot."
        ),
        metadata={"source_id": "website.config_generator"},
    ),
    Document(
        page_content=(
            "Peak to Undershoot Ratio in GEM-pRF Default HRF. The configurator's Peak to Undershoot Ratio field "
            "maps to /root/search_space/default_hrf/@peak_to_undershoot (float) and is forwarded to spm_hrf_compat "
            "as the p_u_ratio argument. The HRF curve is built as peak - undershoot/p_u_ratio: a larger ratio "
            "weights the peak more (undershoot becomes shallower), a smaller ratio deepens the undershoot. Only "
            "effective when 'Use HRF from File' is unchecked. The spm_hrf_compat function-signature default is 6; "
            "the configurator's sample value is 2.15."
        ),
        metadata={"source_id": "website.config_generator"},
    ),
    Document(
        page_content=(
            "Default Spatial Grid in GEM-pRF. The configurator's Default Spatial Grid section (XML: "
            "/root/search_space/default_spatial_grid with attributes @visual_field_radius, @num_horizontal_prfs, "
            "@num_vertical_prfs) defines the candidate pRF centres used in coarse grid fitting. At runtime "
            "(gem.run.run_gem_prf_analysis.GEMpRFAnalysis.get_prf_spatial_points) the analysis builds two "
            "np.linspace arrays from -visual_field_radius to +visual_field_radius — one of length "
            "num_horizontal_prfs (x-axis), one of length num_vertical_prfs (y-axis) — then meshgrids them into a "
            "(num_horizontal_prfs × num_vertical_prfs) grid of (x, y) candidate centres in degrees of visual angle. "
            "Only effective when 'Use Spatial Grid XY from File' is unchecked. The pRF Gaussian model later "
            "discards centres outside the disc x²+y² < visual_field_radius² "
            "(PRFGaussianModel.get_validated_sampling_points_indices). Sample defaults: visual_field_radius=12, "
            "num_horizontal_prfs=51, num_vertical_prfs=51 (giving 51×51=2,601 candidates before disc filtering)."
        ),
        metadata={"source_id": "website.config_generator"},
    ),
    Document(
        page_content=(
            "Default Sigmas in GEM-pRF. The configurator's Default Sigmas section (XML: "
            "/root/search_space/default_sigmas with attributes @num_sigmas, @min_sigma, @max_sigma) defines the "
            "candidate pRF sizes (σ) used in coarse grid fitting. At runtime "
            "(GEMpRFAnalysis.get_additional_dimensions) the analysis builds the sigma range as "
            "np.linspace(min_sigma, max_sigma, num_sigmas) — i.e. num_sigmas equally-spaced sigma values inclusive "
            "of both endpoints. Only effective when 'Use Sigmas from File' is unchecked. Sample defaults: "
            "num_sigmas=8, min_sigma=0.5, max_sigma=5. The product of (num_horizontal_prfs × num_vertical_prfs × "
            "num_sigmas) is the size of the candidate pRF parameter grid the coarse fit searches."
        ),
        metadata={"source_id": "website.config_generator"},
    ),
    Document(
        page_content=(
            "Use Spatial Grid XY from File in GEM-pRF. The configurator's 'Use Spatial Grid XY from File' "
            "checkbox sets /root/search_space/optional_analysis_params/spatial_grid_xy/@use_from_file=\"true\" with "
            "a Spatial Grid XY Key field (@key, e.g. analysis_params/spatial_grid_xy). It only takes effect when "
            "'Use Custom Parameters from File' (optional_analysis_params/@enable) is True. When active, "
            "gem.init_setup.run_selected_program calls H5FileManager.get_key_value(filepath, key) to load the "
            "spatial-grid array directly from the configured H5 file, replacing the meshgrid that would otherwise "
            "be built from <default_spatial_grid> attributes. If the H5 read returns None the run aborts with a "
            "red error. When inactive, <default_spatial_grid> is used to compute the grid."
        ),
        metadata={"source_id": "website.config_generator"},
    ),
    Document(
        page_content=(
            "Batches in GEM-pRF Measured Data. The configurator's Batches field maps to "
            "/root/measured_data/batches (parsed as int) and controls how the measured fMRI Y-signal columns are "
            "subdivided when computing error and refinement updates. At runtime (GEMpRFAnalysis run loop) "
            "batch_size is computed as max(1, total_y_signals / num_batches) and the analysis loops over Y-signal "
            "columns in chunks of that size, computing best-fit projections and (if refinement is enabled) "
            "gradient updates per batch. Larger Batches values produce smaller per-batch GPU buffers (lower peak "
            "memory at the cost of more loop iterations); smaller Batches values produce larger per-batch buffers "
            "(higher peak memory, fewer iterations). Sample default is 500."
        ),
        metadata={"source_id": "website.config_generator"},
    ),
    Document(
        page_content=(
            "Default GPU in GEM-pRF. The configurator's Default GPU field maps to /root/gpu/default_gpu and is the "
            "primary GPU device ID GEM-pRF uses for coarse fitting and refinement. At runtime "
            "gem.init_setup.manage_gpus parses it as an int (raising a clear ValueError if it cannot), then "
            "combines it with any IDs from <additional_available_gpus> into the os.environ['CUDA_VISIBLE_DEVICES'] "
            "string. The default GPU is also passed to the global GPU manager (ggm) as the default device. If the "
            "value is not in [0, max_available_gpus-1] the run logs a red GPU config error and falls back to using "
            "all detected GPUs. Sample default is 0."
        ),
        metadata={"source_id": "website.config_generator"},
    ),
    Document(
        page_content=(
            "Results Analysis ID and Overwrite in GEM-pRF BIDS. The configurator's Results Analysis ID field maps "
            "to /root/input_datasrc/BIDS/results_anaylsis_id (the spelling 'anaylsis' is preserved verbatim in the "
            "XML schema) and the Overwrite checkbox to its @overwrite attribute. At runtime "
            "gem.init_setup.run_selected_program assembles the result directory as "
            "<basepath>/derivatives/prfanalyze-gem/analysis-<results_anaylsis_id>. If that directory already "
            "exists and @overwrite is 'False', the existing directory is moved aside with a timestamped suffix "
            "'<dir>_backup-YYYYMMDD-HHMMSS' before the new run starts; if @overwrite is 'True', the existing "
            "directory is reused. The same analysis ID is also passed to the BIDS handler when computing per-file "
            "result paths. Sample defaults: id=GEMDataAnalysisResults, overwrite=False."
        ),
        metadata={"source_id": "website.config_generator"},
    ),
    Document(
        page_content=(
            "Append to Base Path in GEM-pRF BIDS. The configurator's Append to Base Path field maps to "
            "/root/input_datasrc/BIDS/append_to_basepath and is parsed as a comma-separated list (whitespace "
            "stripped) by gem.data.bids_handler.GemBidsHandler. At runtime the BIDS handler joins the listed "
            "elements onto <basepath> using os.path.join before scanning for matching input files: "
            "base_path = os.path.join(base_path, *append_to_basepath_list). Typical values are 'derivatives, "
            "fmriprep' (joined to <basepath>/derivatives/fmriprep) or 'derivatives, prfprepare'."
        ),
        metadata={"source_id": "website.config_generator"},
    ),
    Document(
        page_content=(
            "Fixed Paths in GEM-pRF Input Data Source. The configurator's Fixed Paths section is the alternative "
            "to BIDS for users who want to point GEM-pRF directly at file paths instead of a BIDS-organised tree. "
            "It maps to /root/input_datasrc/fixed_paths and is selected when the BIDS section's @enable is False "
            "(the run code branches on 'if cfg.bids[\\\"@enable\\\"] == \\\"True\\\"' before computing the result "
            "directory). The section contains: <stimulus_filepath> (single NIfTI file, validated by "
            "gem.data.bids_handler with a red error if the path does not exist), <measured_data_filepath> "
            "containing one or more <filepath> children (each a NIfTI fMRI run; iterated by the analysis loop), "
            "and <results> with <basepath> (output directory; created if missing), <custom_filename_postfix> "
            "(string appended to each result filename, default empty), and <prepend_date> (when 'True', "
            "today's date in YYYY-MM-DD format is prefixed to result filenames via str(datetime.date.today()))."
        ),
        metadata={"source_id": "website.config_generator"},
    ),
    Document(
        page_content=(
            "nDCT in GEM-pRF Search Space. The configurator's nDCT field maps to "
            "/root/search_space/nDCT/@value (parsed as int) and controls how many discrete cosine transform "
            "(DCT) regressors are included in the design matrix to absorb low-frequency drift in the fMRI signal. "
            "The XML @comment states verbatim 'DCT bases to account for low frequency drift. Generate "
            "(2 * nDCT + 1) cosine regressors'. At runtime "
            "gem.signals.orthogonalization_matrix.OrthogonalizationMatrix builds (2 * nDCT + 1) cosine basis "
            "functions over the timecourse via 'np.cos(tc.dot(np.arange(0, nDCT + 0.5, 0.5)[None, :]))' (frequencies "
            "[0, 0.5, 1.0, ..., nDCT]) and stacks them as nuisance columns. Sample default is 1, giving 3 cosine "
            "regressors."
        ),
        metadata={"source_id": "website.config_generator"},
    ),
    Document(
        page_content=(
            "Refine Fitting in GEM-pRF. The configurator's Refine Fitting toggle maps to "
            "/root/refine_fitting/@enable. When True, after the coarse-fit grid stage the run flow selects "
            "GridFit.get_error_terms (refinement-aware, computing both the projection and gradient terms) instead "
            "of GridFit.get_only_error_terms; the analysis then runs the single-step quadratic refinement that "
            "the GEM-pRF paper describes (Section 2.1.2.1) to produce refined (μx, μy, σ) per voxel. When False, "
            "the analysis stops at coarse-fit grid matching and returns the best grid candidate as the final "
            "estimate. The companion attribute /root/refine_fitting/@refinefit_on_gpu, when True, keeps the "
            "refinement-stage error terms and derivative products on GPU; the run flow gates this by checking "
            "(cfg.is_refinefit_on_gpu & cfg.refine_fitting_enabled). When refine_fitting is disabled, "
            "refinefit_on_gpu has no effect."
        ),
        metadata={"source_id": "website.config_generator"},
    ),
    Document(
        page_content=(
            "pRF Model Type in GEM-pRF. The configurator's pRF Model field maps to /root/pRF_model/model and "
            "selects which receptive-field shape the analysis fits. At runtime "
            "gem.run.run_gem_prf_analysis.GEMpRFAnalysis.get_selected_prf_model accepts only the value "
            "'2d_gaussian'; any other value raises ValueError('Invalid PRF Model'). Selecting 2d_gaussian "
            "instantiates gem.model.prf_gaussian_model.PRFGaussianModel, which uses three parameters per voxel: "
            "centre coordinates (μx, μy) in degrees of visual angle and the isotropic standard deviation σ. The "
            "XML comment lists 'DoG, CSS not avaiable at the moment' (typo preserved) — these alternative pRF "
            "shapes appear as options in the Configuration Generator UI but cannot currently be selected."
        ),
        metadata={"source_id": "website.config_generator"},
    ),
    Document(
        page_content=(
            "Which pRF models GEM-pRF supports, and which you can select. GEM-pRF currently implements only the 2D "
            "Gaussian model, and it is the only value the runtime accepts and the only option the Configuration "
            "Generator's pRF Model field can actually select. Difference of Gaussians (DoG) and CSS also appear in "
            "the pRF Model dropdown and in the model enum, but both are marked 'not available at the moment': DoG "
            "is an unimplemented stub and CSS has no implementation, so neither can currently be selected. Use this "
            "rule for 'is X supported by the pRF model?' questions: the plain case of a single round receptive "
            "field with a centre and one size is supported by the 2D Gaussian; any property the 2D Gaussian lacks "
            "is not supported today and would require the alternative DoG or CSS models, which are listed in the "
            "configurator but not yet available to select."
        ),
        metadata={"source_id": "website.config_generator"},
    ),
    Document(
        page_content=(
            "Surround suppression and centre–surround receptive fields in GEM-pRF. The 2D Gaussian model that "
            "GEM-pRF currently provides represents only a single isotropic excitatory centre with coordinates "
            "(μx, μy) and one size σ; it has no surround term. An inhibitory surround, a centre–surround profile, "
            "or surround suppression is therefore NOT supported by the 2D Gaussian model in GEM-pRF. Modelling a "
            "surround would instead require a Difference of Gaussians (DoG) model (Zuiderbaan et al., 2012), which "
            "subtracts a second, wider Gaussian to add an inhibitory surround around the excitatory centre. The "
            "GEM-pRF paper names DoG as a possible future addition and the package already ships abstract base "
            "classes for new pRF models, but the DoG class is an unimplemented stub and the configurator lists DoG "
            "as not available, so it cannot currently be selected."
        ),
        metadata={"source_id": "website.config_generator"},
    ),
    Document(
        page_content=(
            "Nonlinear or compressive spatial summation in GEM-pRF. The 2D Gaussian model that GEM-pRF currently "
            "provides has a single isotropic size σ and no compressive exponent, so a compressive or nonlinear "
            "(subadditive) spatial-summation response is NOT supported by the 2D Gaussian model in GEM-pRF. The "
            "configurator lists a CSS option in the pRF Model dropdown alongside DoG as the kind of alternative "
            "model that would be needed for such a response, but neither the GEM-pRF paper nor the package code "
            "defines or implements what CSS computes, and like DoG it is marked not available and cannot be "
            "selected."
        ),
        metadata={"source_id": "website.config_generator"},
    ),
)

PARAMETERS: tuple[ParameterSpec, ...] = (
    ParameterSpec(
        id="refine_fitting.enable",
        label="Enable Refine Fitting",
        aliases=("refine fitting", "refine_fitting", "refine_fitting enable", "enable refine fitting"),
        xml_path="/root/refine_fitting/@enable",
        summary="Turns derivative-based refinement on after the coarse grid stage.",
        significance="When enabled, GEM-pRF computes derivative signals and uses them in the fitting flow instead of stopping at coarse grid matching.",
        impacts=(
            "The analysis computes derivative signal batches only when refinement is enabled.",
            "Refinement adds compute and memory pressure because more model terms are generated and used.",
        ),
        source_ids=("website.config_generator", "repo.sample_config"),
        code_source_ids=("code.config_manager", "code.run_analysis"),
    ),
    ParameterSpec(
        id="refine_fitting.refinefit_on_gpu",
        label="Execute Refine Fitting On GPU",
        aliases=("refinefit_on_gpu", "refine on gpu", "refine fitting on gpu"),
        xml_path="/root/refine_fitting/@refinefit_on_gpu",
        summary="Controls whether refinement calculations stay on GPU when refinement is enabled.",
        significance="It changes where error terms and refinement-related arrays are kept during the refine stage.",
        impacts=(
            "If refinement is enabled and this flag is true, GEM keeps refinement-side computations on GPU.",
            "This can reduce data movement but depends on available GPU memory.",
        ),
        source_ids=("website.config_generator", "repo.sample_config"),
        code_source_ids=("code.config_manager", "code.run_analysis"),
    ),
    ParameterSpec(
        id="stimulus.visual_field",
        label="Stimulus Visual Field",
        aliases=("stimulus visual field", "visual_field", "stimulus visual_field", "stimulus radius"),
        xml_path="/root/stimulus/visual_field",
        summary="Defines the stimulus coordinate range in degrees used when loading and resampling the stimulus.",
        significance="The stimulus object builds x and y ranges from minus visual_field to plus visual_field, so this parameter sets the stimulus-space geometry.",
        impacts=(
            "Changing it changes the stimulus coordinate axes used when generating model signals.",
            "It is distinct from the search-space visual_field_radius used for pRF grid sampling.",
        ),
        source_ids=("website.config_generator", "repo.sample_config"),
        code_source_ids=("code.run_analysis", "code.prf_stimulus"),
    ),
    ParameterSpec(
        id="stimulus.width",
        label="Stimulus Width",
        aliases=("width", "stimulus width"),
        xml_path="/root/stimulus/width",
        summary="Sets the resampled stimulus width.",
        significance="GEM resamples the loaded stimulus to the configured width before HRF convolution and later uses width in signal synthesis memory calculations.",
        impacts=(
            "Larger width increases the flattened model-curve size used in GPU signal computation.",
            "Together with height, it changes both memory load and effective stimulus resolution.",
        ),
        source_ids=("website.config_generator", "repo.sample_config"),
        code_source_ids=("code.run_analysis", "code.prf_stimulus", "code.signal_synthesizer", "repo.gpu_info"),
    ),
    ParameterSpec(
        id="stimulus.height",
        label="Stimulus Height",
        aliases=("height", "stimulus height"),
        xml_path="/root/stimulus/height",
        summary="Sets the resampled stimulus height.",
        significance="Like width, height changes the resampled stimulus geometry and the amount of per-signal pixel work during GPU signal generation.",
        impacts=(
            "Larger height increases stimulus pixel count and memory use.",
            "Height works jointly with width in GPU buffer sizing and signal generation.",
        ),
        source_ids=("website.config_generator", "repo.sample_config"),
        code_source_ids=("code.run_analysis", "code.prf_stimulus", "code.signal_synthesizer", "repo.gpu_info"),
    ),
    ParameterSpec(
        id="stimulus.binarization.threshold",
        label="Binarization Threshold",
        aliases=("binarization", "threshold", "binarization threshold", "stimulus threshold"),
        xml_path="/root/stimulus/binarization/@threshold",
        summary="Threshold used when stimulus binarization is enabled.",
        significance="If the loaded stimulus is not already binary, GEM converts values strictly above threshold to 1 and all other values (including equal-to-threshold) to 0.",
        impacts=(
            "It changes the stimulus values before resampling and HRF convolution.",
            "Its effect only matters when binarization is enabled and the input contains non-binary values.",
        ),
        source_ids=("website.config_generator", "repo.sample_config"),
        code_source_ids=("code.run_analysis", "code.prf_stimulus"),
    ),
    ParameterSpec(
        id="stimulus.high_temporal_resolution.num_frames_downsampled",
        label="Number of Downsampled Frames",
        aliases=("num_frames_downsampled", "downsampled frames", "number of downsampled frames"),
        xml_path="/root/stimulus/high_temporal_resolution/@num_frames_downsampled",
        summary="Target number of frames after high-temporal stimulus signals are downsampled.",
        significance="In high temporal resolution mode GEM computes signals at the high-res stimulus rate, then samples them down to this length.",
        impacts=(
            "If the requested downsampled length exceeds the available frames, GEM aborts with an error.",
            "This parameter changes the time dimension used later in fitting and orthogonalization.",
        ),
        source_ids=("website.config_generator", "repo.sample_config"),
        code_source_ids=("code.config_manager", "code.prf_stimulus", "code.signal_synthesizer", "code.run_analysis"),
    ),
    ParameterSpec(
        id="stimulus.high_temporal_resolution.slice_time_ref",
        label="Slice Time Reference",
        aliases=("slice_time_ref", "slice time reference"),
        xml_path="/root/stimulus/high_temporal_resolution/@slice_time_ref",
        summary="Reference offset used when selecting downsampled indices from a high-temporal stimulus.",
        significance="GEM computes downsample indices and then shifts them by an amount derived from the mean index step times slice_time_ref.",
        impacts=(
            "It changes which high-resolution frames are sampled into the downsampled signal.",
            "Its effect is limited to the high temporal resolution branch.",
        ),
        source_ids=("website.config_generator", "repo.sample_config"),
        code_source_ids=("code.config_manager", "code.prf_stimulus", "code.signal_synthesizer"),
    ),
    ParameterSpec(
        id="input.BIDS.run_type",
        label="BIDS Run Type",
        aliases=("run_type", "bids run type"),
        enum_values=("individual", "concatenated"),
        xml_path="/root/input_datasrc/BIDS/@run_type",
        summary="Selects whether BIDS input analysis is run per input or over concatenated blocks.",
        significance="The BIDS handler branches on this value to either collect individual matching files or iterate through concatenate_item blocks.",
        impacts=(
            "Individual mode resolves a flat list of matching files.",
            "Concatenated mode builds grouped blocks and drives task-specific stimulus handling.",
        ),
        source_ids=("website.config_generator", "website.input_sources", "repo.sample_config"),
        code_source_ids=("code.bids_handler",),
    ),
    ParameterSpec(
        id="input.BIDS.input_file_extension",
        label="Input File Extension",
        aliases=("input_file_extension", "file extension"),
        enum_values=(".nii.gz", ".gii", "both"),
        xml_path="/root/input_datasrc/BIDS/input_file_extension",
        summary="Restricts BIDS matching to surface files, volume files, or both.",
        significance="The BIDS handler validates this field and only accepts .nii.gz, .gii, or both.",
        impacts=(
            "An unsupported value causes GEM to abort with a validation error.",
            "The choice determines which input files are searched and later processed.",
        ),
        source_ids=("website.config_generator", "repo.sample_config"),
        code_source_ids=("code.bids_handler",),
    ),
    ParameterSpec(
        id="input.BIDS.space",
        label="Space",
        aliases=("space", "output space", "surface space", "reference space"),
        enum_values=("fsnative", "fsaverage", "T1w", "all"),
        xml_path="/root/input_datasrc/BIDS/space",
        summary="Selects the spatial reference of BIDS-derived input files to load (FreeSurfer subject surface, fsaverage group surface, T1w volume, or all available).",
        significance="The BIDS handler uses this to filter derivatives to the requested space; selecting 'all' overrides the per-subject choice and loads every available space.",
        impacts=(
            "fsnative loads each subject's own surface; fsaverage loads the group-averaged surface; T1w loads volumetric files; 'all' processes every available variant.",
            "Selecting a space the derivatives don't contain produces an empty input set.",
        ),
        source_ids=("website.config_generator", "repo.sample_config"),
        code_source_ids=("code.bids_handler",),
    ),
    ParameterSpec(
        id="measured_data.batches",
        label="Batches",
        aliases=("batches", "measured data batches"),
        xml_path="/root/measured_data/batches",
        summary="Controls how observed signals are split into batches during fitting.",
        significance="The analysis computes batch_size from total signal count divided by this config value.",
        impacts=(
            "Increasing the number of batches generally makes each fitting batch smaller.",
            "Very small batch sizes can trade throughput for lower per-batch memory pressure.",
        ),
        source_ids=("website.config_generator", "repo.sample_config"),
        code_source_ids=("code.run_analysis",),
    ),
    ParameterSpec(
        id="gpu.default_gpu",
        label="Default GPU",
        aliases=("default_gpu", "default gpu"),
        xml_path="/root/gpu/default_gpu",
        summary="Primary GPU selected by the user in the XML.",
        significance="During setup GEM uses this field to build CUDA_VISIBLE_DEVICES and then maps GEM's internal default device to index 0 of that filtered list.",
        impacts=(
            "If the value is invalid, GEM falls back to using all available GPUs.",
            "This parameter controls which physical GPU becomes the primary device after environment remapping.",
        ),
        source_ids=("website.config_generator", "repo.sample_config"),
        code_source_ids=("code.init_setup", "code.config_manager"),
    ),
    ParameterSpec(
        id="gpu.additional_available_gpus",
        label="Additional Available GPUs",
        aliases=("additional_available_gpus", "additional gpus", "multi gpu"),
        xml_path="/root/gpu/additional_available_gpus/gpu",
        summary="Optional list of extra GPU ids allowed for multi-GPU execution.",
        significance="Setup collects these ids, removes duplicates, validates them, and exports the combined list through CUDA_VISIBLE_DEVICES.",
        impacts=(
            "Adding more valid GPUs allows GEM to split model-signal computation across more devices.",
            "Invalid ids trigger a fallback path that uses all available GPUs.",
        ),
        source_ids=("website.config_generator", "repo.sample_config", "repo.readme"),
        code_source_ids=("code.init_setup", "repo.gpu_info"),
    ),
    ParameterSpec(
        id="search_space.default_hrf",
        label="Default HRF",
        aliases=("default_hrf", "hrf", "peak_delay", "under_shoot_delay", "peak_disp", "under_disp", "peak_to_undershoot", "normalize", "tr"),
        xml_path="/root/search_space/default_hrf/@*",
        summary="SPM-style HRF parameter block used when no HRF is loaded from file.",
        significance="GEM builds the HRF curve from these values, using TR from the config or pixdim[4] from the stimulus NIfTI header when the TR field is left empty.",
        impacts=(
            "Changing these values changes the HRF curve used to convolve the stimulus before fitting.",
            "The resulting HRF directly changes the modeled stimulus time courses.",
        ),
        source_ids=("website.config_generator", "repo.sample_config"),
        code_source_ids=("code.config_manager", "code.hrf_generator", "code.run_analysis"),
    ),
    ParameterSpec(
        id="search_space.default_spatial_grid.visual_field_radius",
        label="Default Spatial Grid Visual Field Radius",
        aliases=("visual_field_radius", "search space radius", "grid radius"),
        xml_path="/root/search_space/default_spatial_grid/@visual_field_radius",
        summary="Radius of the pRF search grid, distinct from stimulus visual_field.",
        significance="GEM uses it as the extent for linspace calls that generate x and y pRF positions, and the Gaussian model later validates points against the radius.",
        impacts=(
            "A larger radius expands the search grid in visual space.",
            "It changes the sampling extent, not just the number of points.",
        ),
        source_ids=("website.config_generator", "repo.sample_config"),
        code_source_ids=("code.config_manager", "code.run_analysis", "repo.gpu_info"),
        related_parameters=("search_space.default_spatial_grid.num_horizontal_prfs", "search_space.default_spatial_grid.num_vertical_prfs"),
    ),
    ParameterSpec(
        id="search_space.default_spatial_grid.num_horizontal_prfs",
        label="Number of Horizontal pRFs",
        aliases=("num_horizontal_prfs", "horizontal prfs", "horizontal grid"),
        xml_path="/root/search_space/default_spatial_grid/@num_horizontal_prfs",
        summary="Number of x-axis grid points in the default pRF search space.",
        significance="GEM creates the spatial x grid with linspace using this count, so it directly changes how many candidate pRF locations exist horizontally.",
        impacts=(
            "Combined with vertical grid count and sigma count, it increases the total number of candidate model signals.",
            "A larger value yields a finer horizontal search grid but increases compute and memory cost.",
        ),
        source_ids=("website.config_generator", "repo.sample_config", "repo.readme"),
        code_source_ids=("code.config_manager", "code.run_analysis", "repo.gpu_info"),
        related_parameters=("search_space.default_spatial_grid.num_vertical_prfs", "search_space.default_sigmas.num_sigmas"),
    ),
    ParameterSpec(
        id="search_space.default_spatial_grid.num_vertical_prfs",
        label="Number of Vertical pRFs",
        aliases=("num_vertical_prfs", "vertical prfs", "vertical grid"),
        xml_path="/root/search_space/default_spatial_grid/@num_vertical_prfs",
        summary="Number of y-axis grid points in the default pRF search space.",
        significance="GEM creates the spatial y grid with linspace using this count, so it directly changes how many candidate pRF locations exist vertically.",
        impacts=(
            "Combined with horizontal grid count and sigma count, it increases the total number of candidate model signals.",
            "A larger value yields a finer vertical search grid but increases compute and memory cost.",
        ),
        source_ids=("website.config_generator", "repo.sample_config", "repo.readme"),
        code_source_ids=("code.config_manager", "code.run_analysis", "repo.gpu_info"),
        related_parameters=("search_space.default_spatial_grid.num_horizontal_prfs", "search_space.default_sigmas.num_sigmas"),
    ),
    ParameterSpec(
        id="search_space.default_sigmas.num_sigmas",
        label="Number of Sigmas",
        aliases=("num_sigmas", "number of sigmas", "sigmas"),
        xml_path="/root/search_space/default_sigmas/@num_sigmas",
        summary="Number of sigma values sampled in the default search space.",
        significance="GEM builds the sigma search dimension with linspace between min_sigma and max_sigma using this count.",
        impacts=(
            "Together with horizontal and vertical grid sizes, it multiplies the total model count.",
            "More sigma values broaden or refine the size search but increase compute and memory demands.",
        ),
        source_ids=("website.config_generator", "repo.sample_config", "repo.readme"),
        code_source_ids=("code.config_manager", "code.run_analysis", "repo.gpu_info"),
        related_parameters=("search_space.default_spatial_grid.num_horizontal_prfs", "search_space.default_spatial_grid.num_vertical_prfs"),
    ),
    ParameterSpec(
        id="search_space.default_sigmas.min_sigma",
        label="Minimum Sigma",
        aliases=("min_sigma", "minimum sigma"),
        xml_path="/root/search_space/default_sigmas/@min_sigma",
        summary="Lower bound of the default sigma range.",
        significance="GEM uses it as the start of the sigma linspace when custom sigma values are not loaded from file.",
        impacts=(
            "Changing it shifts the lower edge of the sigma search space.",
            "It does not change the number of sigma samples by itself.",
        ),
        source_ids=("website.config_generator", "repo.sample_config"),
        code_source_ids=("code.config_manager", "code.run_analysis"),
    ),
    ParameterSpec(
        id="search_space.default_sigmas.max_sigma",
        label="Maximum Sigma",
        aliases=("max_sigma", "maximum sigma"),
        xml_path="/root/search_space/default_sigmas/@max_sigma",
        summary="Upper bound of the default sigma range.",
        significance="GEM uses it as the end of the sigma linspace when custom sigma values are not loaded from file.",
        impacts=(
            "Changing it shifts the upper edge of the sigma search space.",
            "It does not change the number of sigma samples by itself.",
        ),
        source_ids=("website.config_generator", "repo.sample_config"),
        code_source_ids=("code.config_manager", "code.run_analysis"),
    ),
    ParameterSpec(
        id="search_space.nDCT.value",
        label="nDCT",
        aliases=("ndct", "n dct", "dct value"),
        xml_path="/root/search_space/nDCT/@value",
        summary="Number controlling how many cosine regressors are used for low-frequency drift removal.",
        significance="The orthogonalization matrix code generates cosine trends using frequencies from 0 to nDCT in steps of 0.5, which yields 2 * nDCT + 1 regressors.",
        impacts=(
            "Increasing nDCT adds more cosine regressors to the orthogonalization basis.",
            "That changes the projection matrix used before model fitting.",
        ),
        source_ids=("website.config_generator", "repo.sample_config"),
        code_source_ids=("code.config_manager", "code.orthogonalization", "code.run_analysis"),
    ),
)


_GITHUB_REPO_ROOT = Path(_path("external/github/GEMpRF"))
_DEMOKIT_ROOT = Path(_path("external/GEMpRF-DemoKit"))
_WHEEL_RELATIVE_MARKER = "gemprf_wheel/"

_INDEXABLE_EXTS: tuple[tuple[str, str], ...] = (
    (".py", "code"),
    (".md", "markdown"),
    (".xml", "config"),
)

_SKIP_RELATIVE_DIRS: tuple[tuple[str, ...], ...] = (
    ("example_data",),
    ("tests", "temp"),
    ("tests", "testdata"),
)


def _curated_wheel_relative_paths() -> set[str]:
    relatives: set[str] = set()
    for source in CURATED_SOURCES:
        if not source.local_path:
            continue
        posix = Path(source.local_path).as_posix()
        marker_index = posix.find(_WHEEL_RELATIVE_MARKER)
        if marker_index == -1:
            continue
        relatives.add(posix[marker_index + len(_WHEEL_RELATIVE_MARKER):])
    return relatives


def _curated_local_paths() -> set[Path]:
    return {Path(s.local_path).resolve() for s in CURATED_SOURCES if s.local_path}


def _is_skipped(path: Path, root: Path) -> bool:
    if path.name == "__init__.py":
        return True
    rel_parts = path.relative_to(root).parts
    for skip in _SKIP_RELATIVE_DIRS:
        if len(rel_parts) >= len(skip) and tuple(rel_parts[: len(skip)]) == skip:
            return True
        for i in range(len(rel_parts) - len(skip) + 1):
            if tuple(rel_parts[i : i + len(skip)]) == skip:
                return True
    return False


def _discover_tree(
    root: Path,
    id_prefix: str,
    title_prefix: str,
    skip_wheel_relpaths: set[str] | None = None,
) -> list[SourceMeta]:
    if not root.is_dir():
        return []

    discovered: list[SourceMeta] = []
    curated = _curated_local_paths()

    for ext, kind in _INDEXABLE_EXTS:
        for path in sorted(root.rglob(f"*{ext}")):
            if _is_skipped(path, root):
                continue
            resolved = path.resolve()
            if resolved in curated:
                continue
            relative = resolved.relative_to(root)
            if skip_wheel_relpaths and relative.as_posix() in skip_wheel_relpaths:
                continue
            dotted = ".".join(relative.with_suffix("").parts).replace(" ", "_")
            discovered.append(
                SourceMeta(
                    id=f"{id_prefix}.{dotted}",
                    title=f"{title_prefix}: {relative.as_posix()}",
                    kind=kind,
                    local_path=str(resolved),
                    description=(
                        f"Auto-indexed {ext.lstrip('.')} from {title_prefix} "
                        f"({relative.as_posix()})."
                    ),
                )
            )
    return discovered


def _discover_supplementary_sources() -> tuple[SourceMeta, ...]:
    discovered: list[SourceMeta] = []
    discovered.extend(
        _discover_tree(
            _GITHUB_REPO_ROOT,
            id_prefix="github",
            title_prefix="gemprf/GEMpRF",
            skip_wheel_relpaths=_curated_wheel_relative_paths(),
        )
    )
    discovered.extend(
        _discover_tree(
            _DEMOKIT_ROOT,
            id_prefix="demokit",
            title_prefix="GEMpRF-DemoKit",
        )
    )
    return tuple(discovered)


ALL_SOURCES: tuple[SourceMeta, ...] = CURATED_SOURCES + _discover_supplementary_sources()


def source_map() -> dict[str, SourceMeta]:
    return {source.id: source for source in ALL_SOURCES}


def parameter_map() -> dict[str, ParameterSpec]:
    return {parameter.id: parameter for parameter in PARAMETERS}


def ensure_local_sources_exist() -> None:
    missing = []
    for source in ALL_SOURCES:
        if source.local_path and not Path(source.local_path).exists():
            missing.append(source.local_path)
    if missing:
        joined = "\n".join(missing)
        raise FileNotFoundError(
            "Missing required local GEM-pRF sources:\n"
            f"{joined}"
        )


def _load_local_document(source: SourceMeta) -> Document:
    path = Path(source.local_path or "")
    text = path.read_text(encoding="utf-8")
    header = f"{source.title}\nSource type: {source.kind}\nLocal path: {path}\n"
    if source.description:
        header += f"Description: {source.description}\n"
    return Document(page_content=f"{header}\n{text}", metadata={"source_id": source.id})


def load_documents() -> list[Document]:
    ensure_local_sources_exist()
    documents = list(MANUAL_DOCUMENTS)
    for source in ALL_SOURCES:
        if source.local_path:
            documents.append(_load_local_document(source))
    return documents
