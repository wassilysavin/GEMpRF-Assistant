---
source: website.config_generator
---
Undershoot Delay in GEM-pRF Default HRF. The configurator's Undershoot Delay field maps to /root/search_space/default_hrf/@under_shoot_delay (float, seconds) and is forwarded to spm_hrf_compat as the under_delay argument: the time of the gamma peak that models the negative lobe (post-stimulus undershoot) of the haemodynamic response. Only effective when 'Use HRF from File' is unchecked. The function uses under_delay/under_disp as the gamma shape parameter for the undershoot lobe. Validation: spm_hrf_compat raises ValueError if under_shoot_delay <= 0. The spm_hrf_compat function-signature default is 16 seconds; the configurator's sample value is 12.0.
