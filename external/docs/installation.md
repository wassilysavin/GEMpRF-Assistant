# Installation — GEM-pRF

Source URL: https://gemprf.github.io/installation.html

## Quick Overview

- Check your system has an NVIDIA GPU.
- Install CUDA SDK.
- Install CuPy (matching your CUDA version).
- Install GEM-pRF using pip.

## Step-by-Step Guide

GEM-pRF requires an NVIDIA GPU and CUDA for accelerated pRF computation. Ensure your system has a compatible NVIDIA GPU available.

### Step 1. Create a new python environment (recommended)

Create a fresh conda environment:

```bash
conda create --name gemprf python=3.10
conda activate gemprf
```

### Step 2. Set up GPU environment

- Install the [CUDA SDK](https://developer.nvidia.com/cuda-downloads).
- Check your CUDA installation:

```bash
nvcc --version
nvidia-smi
```

- Install a CuPy build that matches your CUDA version:

```bash
pip install cupy-cuda12x   # Replace 12x with your CUDA version
```

### Step 3. Verify CUDA–CuPy compatibility

Run a quick test to confirm CuPy can use the CUDA runtime correctly:

```bash
python -c "import cupy as cp; print(cp.arange(5) ** 2)"
```

If this fails, your CuPy build does not match your CUDA runtime.

### Step 4. Install GEM-pRF via pip

Install from PyPI:

```bash
pip install gemprf
```

Latest releases: [PyPI – gemprf](https://pypi.org/project/gemprf/).

### Step 5. Try the GEMpRF-DemoKit (optional)

Follow the instructions in the [Getting Started with GEMpRF-DemoKit tutorial](tutorials/input-source-tutorials/input-source-selection-tutorial.html) to verify your installation.

Once installed, proceed to [Running GEM-pRF](running.html).
