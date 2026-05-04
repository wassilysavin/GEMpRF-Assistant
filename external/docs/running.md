# Running GEM-pRF

Source URL: https://gemprf.github.io/running.html

## Quick Overview

- Prepare your XML configuration file.
- Run GEM-pRF directly from Python (recommended).
- Advanced users can also run GEM-pRF from its entry script.

Make sure you have installed GEM-pRF via `pip install gemprf` and a matching CuPy build.

## Step-by-Step Guide

### Option A: Run GEM-pRF from Python (recommended)

This is the simplest way to use GEM-pRF. No cloning, no manual entry points.

Import the package:

```python
import gemprf as gp
```

Run GEM-pRF by providing the path to your XML config file (see a [sample config](https://github.com/siddmittal/GEMpRF_Demo/blob/main/sample_configs/sample_config.xml)):

```python
import gemprf as gp
gp.run("path/to/your_config.xml")
```

This works in any Python environment: scripts, Jupyter, VS Code, PyCharm.

### Option B: Advanced — Run from entry script (GitHub codebase)

For users with full access to the GEM-pRF source code (e.g. debugging, modifying kernels), you can execute GEM from its terminal entry point.

- Activate your environment and navigate to the `GEMpRF` folder.
- Run:

```bash
python run_gem.py PATH_TO_YOUR_XML_CONFIG_FILE
```

### Option C: Run from an IDE (source-code users)

- Open the GEM-pRF code folder in VS Code or PyCharm.
- Edit `run_gem.py` to point to your XML config file.
- Execute the script directly inside the IDE.
