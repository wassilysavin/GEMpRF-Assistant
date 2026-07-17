---
source: website.config_generator
---
Peak to Undershoot Ratio in GEM-pRF Default HRF. The configurator's Peak to Undershoot Ratio field maps to /root/search_space/default_hrf/@peak_to_undershoot (float) and is forwarded to spm_hrf_compat as the p_u_ratio argument. The HRF curve is built as peak - undershoot/p_u_ratio: a larger ratio weights the peak more (undershoot becomes shallower), a smaller ratio deepens the undershoot. Only effective when 'Use HRF from File' is unchecked. The spm_hrf_compat function-signature default is 6; the configurator's sample value is 2.15.
