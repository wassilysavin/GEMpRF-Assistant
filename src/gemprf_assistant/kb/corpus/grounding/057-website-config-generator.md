---
source: website.config_generator
---
Batches in GEM-pRF Measured Data. The configurator's Batches field maps to /root/measured_data/batches (parsed as int) and controls how the measured fMRI Y-signal columns are subdivided when computing error and refinement updates. At runtime (GEMpRFAnalysis run loop) batch_size is computed as max(1, total_y_signals / num_batches) and the analysis loops over Y-signal columns in chunks of that size, computing best-fit projections and (if refinement is enabled) gradient updates per batch. Larger Batches values produce smaller per-batch GPU buffers (lower peak memory at the cost of more loop iterations); smaller Batches values produce larger per-batch buffers (higher peak memory, fewer iterations). Sample default is 500.
