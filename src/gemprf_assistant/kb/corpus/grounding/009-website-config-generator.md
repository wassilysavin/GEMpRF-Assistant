---
source: website.config_generator
---
.gii (GIFTI) in GEM-pRF. .gii is one of three values the BIDS input_file_extension field accepts (alongside .nii.gz and both). GEM-pRF processes only filenames matching _bold.func.gii, which corresponds to surface data typically produced by fMRIPrep. The ObservedData loader reads .gii files as nib.gifti.GiftiImage objects, which contain one or more data arrays. The BIDS handler validates input_file_extension and aborts with a validation error on any value other than .nii.gz, .gii, or both.
