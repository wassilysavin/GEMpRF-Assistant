---
source: website.config_generator
---
Time Range t in GEM-pRF Default HRF. The configurator's 'Time Range t' field under Default HRF Parameters maps to /root/search_space/default_hrf/@t and is parsed as a tuple (start, stop) of seconds. Only effective when 'Use HRF from File' is unchecked. At runtime, the analysis appends the TR (or the stimulus header's pixdim[4] if the configurator's TR field is empty) as the third value, then calls np.arange(start, stop, TR) to build the time grid sampled by the SPM HRF. The sample config default is t="(0, 45)", giving a 45-second support window.
