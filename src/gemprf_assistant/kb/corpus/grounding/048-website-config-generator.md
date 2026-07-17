---
source: website.config_generator
---
TR in GEM-pRF Default HRF. The configurator's TR field under Default HRF Parameters maps to /root/search_space/default_hrf/@TR and is the repetition time in seconds used as the sample step when constructing the SPM-style HRF curve via np.arange(start, stop, TR). When the field is empty (TR is None), the run reads pixdim[4] from the stimulus NIfTI header and logs a yellow message that the HRF time-grid step has been set from the stimulus TR. Only effective when 'Use HRF from File' is unchecked. The sample config default is TR="1.0".
