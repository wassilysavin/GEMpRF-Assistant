---
source: website.config_generator
---
Concatenated run type in GEM-pRF. Concatenated is one of two values the BIDS run_type field accepts (the other is individual). The website's config generator describes Concatenated Analysis as a list of concatenate_item blocks — each item needs ses, task, and run, with one value each (no spaces or commas). The BIDS handler iterates through the concatenate_item blocks and gathers the matching files per block, driving task-specific stimulus handling.
