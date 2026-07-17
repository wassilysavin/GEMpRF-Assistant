---
source: website.config_generator
---
Normalize HRF in GEM-pRF. The configurator's 'Normalize HRF' checkbox under Default HRF Parameters maps to /root/search_space/default_hrf/@normalize. The flag is forwarded to spm_hrf_compat in gem.signals.hrf_generator, where, when True, the constructed HRF curve is divided by the sum of its values before being returned (so the curve sums to 1); when False, the unnormalised curve is returned as-is. This only affects the SPM-style HRF built from <default_hrf> attributes; if 'Use HRF from File' is enabled the curve is loaded from H5 and Normalize HRF has no effect.
