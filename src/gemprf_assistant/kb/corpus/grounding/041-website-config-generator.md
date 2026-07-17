---
source: website.config_generator
---
Use Sigmas from File in GEM-pRF. The configurator's 'Use Sigmas from File' checkbox sets /root/search_space/optional_analysis_params/sigmas/@use_from_file="true" with a Sigmas Key field (@key, e.g. analysis_params/sigmas). It only takes effect when 'Use Custom Parameters from File' (optional_analysis_params/@enable) is True. When active, the sigma grid is read from the configured H5 file at the supplied key, replacing the values that would otherwise be generated from <default_sigmas> (min_sigma, max_sigma, num_sigmas). When inactive, the run uses the <default_sigmas> attributes.
