# Configuration Generator — GEM-pRF

Source URL: https://gemprf.github.io/gemprf-configs/config_generator.html

## Overview

GEM-pRF provides a configuration generator for creating pRF analysis config files through an interactive web interface.

## Config Filename Builder

- **Data Source** — Identifier for your data source (max 5 words).
- **Stimulus Type** — Type of stimulus used (max 5 words).
- **Description** — Brief description (max 10 words).

## Refine Fitting

- **Enable Refine Fitting** (checkbox).
- **Execute on GPU** (checkbox; if available).

## Stimulus Configuration

- **Stimulus Directory** — Path to stimulus directory (Nifti format).
- **Visual Field Radius**
- **Width**
- **Height**

### Binarization

- **Enable Binarization** (checkbox).
- **Threshold**

### High Temporal Resolution

- **Enable High Temporal Resolution** (checkbox).
- **Number of Downsampled Frames**
- **Slice Time Reference**

## Input Data Source

### Data Organization Type

- BIDS Format
- Fixed Paths

### BIDS Configuration

- **Run Type**: Individual or Concatenated.
- **Base Path**, with optional **Append to Base Path** (comma-separated values).
- **Input Analysis ID** — comma-separated values or "all".
- **Subjects** — comma-separated values or "all".
- **Hemisphere** — comma-separated values or "all".
- **Space** — one of `fsnative`, `fsaverage`, `T1w`, or `all` (overrides other selections).
- **Input File Extension** — one of `.nii.gz`, `.gii`, or `both`.

### Individual Task Analysis

- **Task** — exactly one task name; do not enter "all"; avoid spaces or commas.
- **Session** — comma-separated values or "all".
- **Run** — comma-separated values or "all".

### Concatenated Analysis

- **Concatenate Items** — each item needs `ses`, `task`, and `run`; one value each with no spaces or commas.

### Fixed Paths Configuration

- **Stimulus File Path**
- **Measured Data File Paths** — add one or more measured data file paths.

## Output Results

### Output Configuration (BIDS Format)

- **Data Type**: BIDS Format
- **Analysis ID**
- **Overwrite Existing Results** (checkbox).

### Output Configuration (Fixed Paths)

- **Data Type**: Fixed Paths
- **Results Base Path**
- **Custom Filename Postfix**
- **Prepend Date to Filename** (checkbox).

## pRF Model

- **Model Type**: 2D Gaussian. (DoG and CSS listed but not available.)

## Measured Data

- **Batches** — Number of batches for processing.

## GPU Configuration

- **Default GPU**
- **Additional Available GPUs** — add GPU indices for additional available GPUs.

## Search Space

- **Write Debug Info** (checkbox).

### Optional Analysis Parameters

- **Use Custom Parameters from File** (checkbox) → File Path.
- **Use HRF from File** (checkbox) → HRF Key.
- **Use Sigmas from File** (checkbox) → Sigmas Key.
- **Use Spatial Grid from File** (checkbox) → Spatial Grid Key.

### Default HRF Parameters

- Time Range `t`
- TR
- Peak Delay
- Undershoot Delay
- Peak Dispersion
- Undershoot Dispersion
- Peak to Undershoot Ratio
- Normalize HRF (checkbox)

### Default Spatial Grid

- Visual Field Radius
- Number of Horizontal pRFs
- Number of Vertical pRFs

### Default Sigmas

- Number of Sigmas
- Minimum Sigma
- Maximum Sigma

### nDCT

- **nDCT Value** — DCT bases for low frequency drift. Generates (2 * nDCT + 1) cosine regressors.

## Download Options

- Download XML
- Copy to Clipboard

## Notes

The archive of configurations for older GEM-pRF versions is at `gemprf-configs/list-configs-archive.html`. That page is JavaScript-rendered and its dynamic contents were not captured here.
