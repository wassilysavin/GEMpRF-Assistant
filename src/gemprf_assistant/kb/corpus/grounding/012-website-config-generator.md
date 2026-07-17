---
source: website.config_generator
---
fsnative in GEM-pRF. fsnative is one of four values the BIDS space field accepts (alongside fsaverage, T1w, and all). fsnative refers to each subject's own FreeSurfer cortical surface space; the BIDS handler filters derivatives to this per-subject surface. Selecting all overrides the per-subject choice and loads every available space variant.
