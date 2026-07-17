---
source: website.config_generator
---
Individual run type in GEM-pRF. Individual is one of two values the BIDS run_type field accepts (the other is concatenated). The website's config generator describes Individual Task Analysis as: exactly one task name (no all, no spaces or commas), with Session and Run as comma-separated values or all. The BIDS handler treats this as run_type=individual, where the user may specify multiple session/run values for a single task and the handler resolves them to a flat list of matching files.
