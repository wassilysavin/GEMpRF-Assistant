---
source: website.config_generator
---
nDCT in GEM-pRF Search Space. The configurator's nDCT field maps to /root/search_space/nDCT/@value (parsed as int) and controls how many discrete cosine transform (DCT) regressors are included in the design matrix to absorb low-frequency drift in the fMRI signal. The XML @comment states verbatim 'DCT bases to account for low frequency drift. Generate (2 * nDCT + 1) cosine regressors'. At runtime gem.signals.orthogonalization_matrix.OrthogonalizationMatrix builds (2 * nDCT + 1) cosine basis functions over the timecourse via 'np.cos(tc.dot(np.arange(0, nDCT + 0.5, 0.5)[None, :]))' (frequencies [0, 0.5, 1.0, ..., nDCT]) and stacks them as nuisance columns. Sample default is 1, giving 3 cosine regressors.
