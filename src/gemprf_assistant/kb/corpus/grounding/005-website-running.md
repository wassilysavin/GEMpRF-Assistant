---
source: website.running
---
GEM-pRF running guide. The docs describe three execution modes. Option A (recommended) is to import the package and call gp.run(config_xml_path) from any Python context. Option B runs the repo entry script python run_gem.py PATH_TO_XML. Option C opens the source code in VS Code or PyCharm and edits run_gem.py to point at the config. All three modes rely on a CuPy build that matches the installed CUDA runtime.
