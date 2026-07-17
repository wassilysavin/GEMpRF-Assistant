---
source: website.config_generator
---
Undershoot Dispersion in GEM-pRF Default HRF. The configurator's Undershoot Dispersion field maps to /root/search_space/default_hrf/@under_disp (float) and is forwarded to spm_hrf_compat as the under_disp argument: the width (dispersion) of the undershoot gamma. It serves as both the divisor of under_shoot_delay (to form the gamma shape) and the scale parameter of the gamma distribution. Only effective when 'Use HRF from File' is unchecked. Validation: spm_hrf_compat raises ValueError if under_disp <= 0. The spm_hrf_compat function-signature default is 1; the configurator's sample value is 0.82. Smaller under_disp produces a sharper undershoot.
