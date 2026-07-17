---
source: website.input_sources
---
BIDS in GEM-pRF. The website tutorial and config generator describe BIDS (Brain Imaging Data Structure) as one of two data-organization types for GEM-pRF inputs (the other is Fixed Paths). For BIDS inputs, GEM-pRF locates files based on subject and session, with options for run type (individual or concatenated), space (fsnative, fsaverage, T1w, or all), input file extension (.nii.gz, .gii, or both), hemisphere, subjects, and analysis ID. The paper's empirical analyses use the NYU retinotopy dataset organised in BIDS format and preprocessed with fMRIPrep.
