---
source: paper.full
---
fMRIPrep in GEM-pRF. The paper reports that the NYU dataset preprocessing was carried out by the dataset authors using fMRIPrep v20.0.1 (Esteban et al., 2019). Anatomical preprocessing included intensity inhomogeneity correction, skull-stripping, tissue segmentation, and cortical surface reconstruction with FreeSurfer. Functional preprocessing involved distortion correction with topup, motion correction, slice-time correction, and co-registration of functional to anatomical images, applied in a single interpolation step; preprocessed functional data were resampled to individual cortical surfaces. The website's input-source tutorial lists fMRIPrep as one of the two BIDS-derivative input styles GEM-pRF accepts (alongside prfprepare).
