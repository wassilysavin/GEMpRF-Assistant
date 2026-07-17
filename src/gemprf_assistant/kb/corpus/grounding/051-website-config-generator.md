---
source: website.config_generator
---
Peak Dispersion in GEM-pRF Default HRF. The configurator's Peak Dispersion field maps to /root/search_space/default_hrf/@peak_disp (float) and is forwarded to spm_hrf_compat as the peak_disp argument: the width (dispersion) of the peak gamma. It serves both as the divisor of peak_delay (to form the gamma shape) and as the scale parameter of the gamma distribution. Only effective when 'Use HRF from File' is unchecked. Validation: spm_hrf_compat raises ValueError if peak_disp <= 0. The spm_hrf_compat function-signature default is 1; the configurator's sample value is 0.85. Smaller peak_disp produces a sharper peak.
