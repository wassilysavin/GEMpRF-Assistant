# GEM-pRF Tutorial — Input Source Selection

Source URL: https://gemprf.github.io/tutorials/input-source-tutorials/input-source-selection-tutorial.html

## Quick Overview

- Make sure GEM-pRF is installed (see the [Installation page](/installation.html)).
- Download the GEMpRF DemoKit.
- Run the interactive demo script.
- Choose examples 001–005 to explore different input source configurations.

Ensure that you have installed the GEM-pRF package (follow the Installation page).

## Step-by-Step Guide

### Step 1. Download the DemoKit

This repository contains sample fMRI/MRI data and example configurations.

```bash
git clone https://github.com/siddmittal/GEMpRF-DemoKit.git
cd GEMpRF-DemoKit
```

### Step 2. Run the interactive demo

The demo script guides you through multiple examples. To explore input sources, select **options 001–005**.

```bash
python run_gemprf_demo.py
```

### Step 3. What happens during the demo

- **Interactive menu**: choose examples showing different input styles.
- **Automatic path fixing**: XML configs update to your local DemoKit paths.
- **GPU memory check**: prevents running models that won't fit.
- **Full GEM-pRF run**: executes `gp.run()` using the selected configuration.

## How Input Sources Work

GEM-pRF accepts inputs from multiple sources: raw filesystem paths or structured BIDS datasets. Everything is controlled through XML configuration files, not by modifying GEM-pRF code.

- **Filesystem paths**: direct references to your fMRI and stimulus files.
- **BIDS datasets**: GEM-pRF locates the correct files based on subject/session.

## Examples You Will See (001–005)

- **001:** BIDS + prfprepare (surface), individual runs.
- **002:** BIDS + fMRIPrep (surface), individual runs.
- **003:** BIDS + fMRIPrep (volume), individual runs.
- **004:** BIDS + fMRIPrep (surface + volume), individual runs.
- **005:** Fixed paths (non-BIDS) + prfprepare (surface).

## Notes

Ensure GEM-pRF and required dependencies (e.g. CuPy for GPU support) are installed. When adapting examples to your own data, check the XML comments to see which fields control input behaviour.

The 001–005 scenarios are not separate HTML pages — they are numbered options inside the interactive `run_gemprf_demo.py` demo script bundled with GEMpRF-DemoKit.
