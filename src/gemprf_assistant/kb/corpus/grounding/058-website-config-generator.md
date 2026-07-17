---
source: website.config_generator
---
Default GPU in GEM-pRF. The configurator's Default GPU field maps to /root/gpu/default_gpu and is the primary GPU device ID GEM-pRF uses for coarse fitting and refinement. At runtime gem.init_setup.manage_gpus parses it as an int (raising a clear ValueError if it cannot), then combines it with any IDs from <additional_available_gpus> into the os.environ['CUDA_VISIBLE_DEVICES'] string. The default GPU is also passed to the global GPU manager (ggm) as the default device. If the value is not in [0, max_available_gpus-1] the run logs a red GPU config error and falls back to using all detected GPUs. Sample default is 0.
