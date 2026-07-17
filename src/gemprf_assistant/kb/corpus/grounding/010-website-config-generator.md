---
source: website.config_generator
---
.nii.gz (NIfTI) in GEM-pRF. .nii.gz is one of three values the BIDS input_file_extension field accepts (alongside .gii and both). GEM-pRF processes only filenames matching _bold.nii.gz, which corresponds to volumetric fMRI data; volumetric files are flattened before analysis. The website's config generator and the sample configs also require the stimulus directory to be in NIfTI format.
