---
source: paper.full
---
mrVista in the GEM-pRF paper. mrVista (Dumoulin and Wandell, 2008) is one of the two most-used pRF mapping software packages and follows the gold-standard, two-step coarse-then-refine fitting approach. mrVista is CPU-only, which results in long processing times for large datasets. The paper benchmarks GEM-pRF against mrVista's prfanalyze-vista Docker container (version 2.3.1_3.1.2; Lerma-Usabiaga et al., 2020) on V1 of the NYU dataset. Across roughly 1.65 million voxels, agreement was Pearson r = 1.00 for μx, μy, and ρ², and r = 0.98 for σ. GEM-pRF was nearly two orders of magnitude faster than mrVista on the same task.
