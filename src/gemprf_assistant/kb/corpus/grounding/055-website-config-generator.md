---
source: website.config_generator
---
Default Sigmas in GEM-pRF. The configurator's Default Sigmas section (XML: /root/search_space/default_sigmas with attributes @num_sigmas, @min_sigma, @max_sigma) defines the candidate pRF sizes (σ) used in coarse grid fitting. At runtime (GEMpRFAnalysis.get_additional_dimensions) the analysis builds the sigma range as np.linspace(min_sigma, max_sigma, num_sigmas) — i.e. num_sigmas equally-spaced sigma values inclusive of both endpoints. Only effective when 'Use Sigmas from File' is unchecked. Sample defaults: num_sigmas=8, min_sigma=0.5, max_sigma=5. The product of (num_horizontal_prfs × num_vertical_prfs × num_sigmas) is the size of the candidate pRF parameter grid the coarse fit searches.
