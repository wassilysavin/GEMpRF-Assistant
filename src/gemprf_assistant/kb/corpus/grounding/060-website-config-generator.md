---
source: website.config_generator
---
Append to Base Path in GEM-pRF BIDS. The configurator's Append to Base Path field maps to /root/input_datasrc/BIDS/append_to_basepath and is parsed as a comma-separated list (whitespace stripped) by gem.data.bids_handler.GemBidsHandler. At runtime the BIDS handler joins the listed elements onto <basepath> using os.path.join before scanning for matching input files: base_path = os.path.join(base_path, *append_to_basepath_list). Typical values are 'derivatives, fmriprep' (joined to <basepath>/derivatives/fmriprep) or 'derivatives, prfprepare'.
