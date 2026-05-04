# GEM-pRF Tutorial — Grid or Refine Fit

Source URL: https://gemprf.github.io/tutorials/fitting-tutorials/grid-or-refine-fit.html

# Grid Fit vs Grid + Refine Fit

One of the key decisions in configuring GEM-pRF is choosing your fitting strategy. GEM-pRF offers two approaches to estimating population receptive fields: **grid fitting only** or **a two-stage approach combining grid fitting with refine fitting**. This choice significantly impacts both the speed and accuracy of your analysis.

## Quick Overview
- ⚙️ Grid Fitting: Fast initial parameter search across a defined space
- 🔧 Refine Fitting: Optional fine-tuning for improved accuracy (little slower)
- 📋 Configure via your XML configuration file
- ⚡ Choose based on your accuracy vs. speed requirements
- 🎯 Two-stage approach is recommended for most analyses

## Grid Fitting

Grid fitting is the initial stage where GEM-pRF searches across a coarse grid of population receptive field parameters. This stage efficiently explores the parameter space and produces reasonable initial estimates for each voxel.

### Characteristics of Grid Fitting:
- **Speed:** Fast, suitable for large-scale analyses
- **Coverage:** Explores the full parameter space systematically
- **Accuracy:** Good estimates, but may not capture fine details
- **Use Case:** Quick exploratory analyses or when computational resources are limited

## Refine Fitting

Refine fitting (also called fine-fit) is an optional second stage that takes the results from grid fitting and performs a more precise optimization around the best grid solution. This can significantly improve parameter estimates. For detailed information about the gridfit and refinefit algorithms, see the [GEM-pRF research paper](/cite.html).

### Characteristics of Refine Fitting:
- **Speed:** Slower than grid fitting alone, but focuses on smaller search space
- **Accuracy:** Higher quality parameter estimates with better convergence
- **Optimization:** Uses gradient-based methods around the grid solution
- **Use Case:** Final, publication-quality analyses

## Comparing the Two Approaches
**Aspect****Grid Fit Only****Grid Fit + Refine Fit****Speed**FastestSlower (but still efficient) [*](/cite.html)**Accuracy**Good initial estimatesExcellent refined estimates [*](/cite.html)**Best For**Exploratory analysis, prototypingPublication-quality analysis**Parameter Quality**Coarse resolutionFine resolution
## How to Configure Your Fitting Strategy

Your choice of fitting strategy is configured through your GEM-pRF XML configuration file. The configuration file controls whether refine fitting is enabled or disabled.

### XML Configuration Parameters

```
<?xml version='1.0' encoding='UTF-8'?>
<root>
  <!-- Enable both grid fit and refine fit (recommended) -->
  <refine_fitting enable="True" refinefit_on_gpu="True"/>

  <!-- REST OF YOUR CONFIGURATION... -->

</root>
```
**Parameter****Values****Description**`enable`True / FalseEnable or disable refine fitting stage`refinefit_on_gpu`True / FalseRun refine fitting on GPU (recommended) or CPU (if memory-limited)
## Recommendations
**💡 For Most Users:** We recommend using grid fitting combined with refine fitting 
        (the two-stage approach) for your final analyses. The extra computation time is well worth the improvement 
        in parameter quality, and GEM-pRF's GPU acceleration makes this quite fast even for large datasets.
      **⚡ For Quick Exploration:** If you're testing configurations or doing preliminary analysis, 
        grid fitting alone is sufficient and much faster. You can always switch to the two-stage approach later.
      
## Next Steps
- **Try it out:** Get started quickly with the [GEM-pRF DemoKit](https://github.com/siddmittal/GEMpRF-DemoKit), which includes example datasets and configuration files you can experiment with
- **Learn about configuration:** Read the [Configuration File Tutorial](/tutorials/config-tutorials/config_file.html) to understand all available options
- **Start with a sample:** Use the sample configuration file as a template and modify the fitting strategy to match your needs
- **Monitor performance:** Compare the analysis time and result quality between the two approaches to inform your choice for future analyses

**📚 Learn More:** For complete details about configuration options and fitting parameters, 
        see the [Configuration File Tutorial](/tutorials/config-tutorials/config_file.html).
