---
source: website.config_generator
---
Peak Delay in GEM-pRF Default HRF. The configurator's Peak Delay field maps to /root/search_space/default_hrf/@peak_delay (float, seconds) and is forwarded to spm_hrf_compat as the peak_delay argument: the time of the gamma peak that models the positive lobe of the haemodynamic response. Only effective when 'Use HRF from File' is unchecked. The function uses peak_delay/peak_disp as the gamma shape parameter, with peak_disp as scale. Validation: spm_hrf_compat raises ValueError if peak_delay <= 0. The spm_hrf_compat function-signature default is 6 seconds; the configurator's sample value is 6.16.
