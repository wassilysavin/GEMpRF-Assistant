---
source: website.config_generator
---
fsaverage in GEM-pRF. fsaverage is one of four values the BIDS space field accepts (alongside fsnative, T1w, and all). fsaverage refers to the FreeSurfer group-averaged cortical surface space; the BIDS handler filters derivatives to this group surface. Selecting all overrides the per-subject choice and loads every available space variant.
