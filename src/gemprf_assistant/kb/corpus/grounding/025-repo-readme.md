---
source: repo.readme
---
GEMpRF-DemoKit. The DemoKit is a separate repository (github.com/siddmittal/GEMpRF-DemoKit) containing sample fMRI/MRI data and example XML configurations. Its top-level runner run_gemprf_demo.py exposes an interactive menu of examples 001–005, covering different input source configurations: BIDS + prfprepare (surface), BIDS + fMRIPrep (surface, volume, or both), and fixed paths + prfprepare (surface). The demo automatically updates XML config paths to the local DemoKit checkout, performs a GPU memory check, and then calls gp.run() with the selected configuration.
