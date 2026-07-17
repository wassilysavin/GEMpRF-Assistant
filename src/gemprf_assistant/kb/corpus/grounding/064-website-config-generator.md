---
source: website.config_generator
---
pRF Model Type in GEM-pRF. The configurator's pRF Model field maps to /root/pRF_model/model and selects which receptive-field shape the analysis fits. At runtime gem.run.run_gem_prf_analysis.GEMpRFAnalysis.get_selected_prf_model accepts only the value '2d_gaussian'; any other value raises ValueError('Invalid PRF Model'). Selecting 2d_gaussian instantiates gem.model.prf_gaussian_model.PRFGaussianModel, which uses three parameters per voxel: centre coordinates (μx, μy) in degrees of visual angle and the isotropic standard deviation σ. The XML comment lists 'DoG, CSS not avaiable at the moment' (typo preserved) — these alternative pRF shapes appear as options in the Configuration Generator UI but cannot currently be selected.
