# GEM-pRF Tutorial — Configuration File

Source URL: https://gemprf.github.io/tutorials/config-tutorials/config_file.html

# Configuration Files

GEM-pRF uses XML configuration files to define all analysis inputs and settings. Once `gemprf` and CuPy are installed, you only need to prepare your XML file and pass its path to the `gp.run()` function.

## Running with a Config File

```
import gemprf as gp
gp.run("path/to/your_config.xml")
```

A complete example configuration file can be found here: [sample_config.xml](https://github.com/siddmittal/GEMpRF-DemoKit/blob/main/sample_configs/sample_config.xml).

You can copy this template, modify paths and parameters, and use it as your starting point for running your own analyses.

## Helpful Tools & Resources

### 🛠️ Interactive Configuration Generator

Don't want to manually write XML? Use our interactive configuration generator to build your XML file step-by-step through a user-friendly web interface:

[Open Configuration Generator →](/gemprf-configs/config_generator.html)

### 📚 Configuration Archives

If you're using an older version of GEM-pRF, you can find configuration files for previous releases in our archive:

[Browse Configuration Archive →](/gemprf-configs/list-configs-archive.html)
