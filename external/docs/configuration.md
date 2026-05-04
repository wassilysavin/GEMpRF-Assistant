# Configuration — GEM-pRF

Source URL: https://gemprf.github.io/configuration.html

## Quick Overview

- GEM-pRF uses a simple XML configuration file.
- All analysis settings, paths, and parameters live inside this file.
- Your Python code stays tiny — you only call `gp.run(CONFIG_FILEPATH)`.
- Create multiple XML files to run multiple analyses easily.
- GEM-pRF stores a copy of your XML file inside the analysis output folder.
- Use the Configuration Generator to create XML files through an interactive web interface.
- Download a sample config file to get started quickly.

The configuration file is the **heart of GEM-pRF**. If the XML file is correct, GEM-pRF will run smoothly — no code changes needed.

## Why an XML configuration file?

GEM-pRF keeps analysis settings separate from the code. Instead of editing Python scripts, you adjust the XML — flexible, simple, safe, and easy to automate.

- **No code editing:** all parameters are defined in the XML.
- **Batch processing:** create multiple config files and run them in sequence.
- **Automation:** call `gp.run()` in a loop or run a bash script over a folder of XML files.
- **Reproducibility:** GEM-pRF automatically saves the XML file inside the analysis output directory.
- **Clarity:** well-named XML files make it easy to track analyses.

## Recommended naming conventions

While not required, giving your XML files meaningful names makes your work much easier to understand later. A BIDS-style naming convention works very well:

```
study-CHN_task-fixedbar123_run-concat_analysis-02_desc-hres.xml
```

Clear naming helps you recognize what the analysis did even years later.

## How to run GEM-pRF using a config file

Once `gemprf` and the matching CuPy build are installed, run GEM-pRF using:

```python
import gemprf as gp
gp.run("path/to/your_config.xml")
```

GEM-pRF reads everything from the XML file — data paths, stimuli, parameters, output locations — and executes the full analysis automatically.

## Where to edit the XML file

Use an editor that highlights XML tags clearly so you can avoid small mistakes and see the structure of the configuration file at a glance.

- VS Code (recommended, easy to use and has great XML highlighting)
- Notepad++ (lightweight, works well on Windows)
- Sublime Text, Atom, or any editor that provides XML syntax coloring and indentation support

## Configuration Tools & Resources

### Interactive Configuration Generator

Need help creating a configuration file? Use the interactive generator to build your XML configuration step-by-step at `gemprf-configs/config_generator.html`.

### Download Sample Configuration

A sample configuration file is provided on the site as a starting point for your own analyses.

### Configuration Archives

Looking for configuration files for older GEM-pRF versions? Browse the archive at `gemprf-configs/list-configs-archive.html`.
