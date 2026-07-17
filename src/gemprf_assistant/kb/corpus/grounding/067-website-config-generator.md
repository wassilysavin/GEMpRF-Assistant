---
source: website.config_generator
---
Nonlinear or compressive spatial summation in GEM-pRF. The 2D Gaussian model that GEM-pRF currently provides has a single isotropic size σ and no compressive exponent, so a compressive or nonlinear (subadditive) spatial-summation response is NOT supported by the 2D Gaussian model in GEM-pRF. The configurator lists a CSS option in the pRF Model dropdown alongside DoG as the kind of alternative model that would be needed for such a response, but neither the GEM-pRF paper nor the package code defines or implements what CSS computes, and like DoG it is marked not available and cannot be selected.
