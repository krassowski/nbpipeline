# nbpipeline
[![Build Status](https://travis-ci.org/krassowski/nbpipeline.svg?branch=master)](https://travis-ci.org/krassowski/nbpipeline)

Snakemake-like pipelines for Jupyter Notebooks, producing interactive pipeline reports like this:

<img src="https://raw.githubusercontent.com/krassowski/nbpipeline/master/examples/screenshots/example_interactive_result.png" width=400>  <img src="https://raw.githubusercontent.com/krassowski/nbpipeline/master/examples/screenshots/example_diff.png" width=400>

### Install & general remarks

These are still early days of this software so please bear in mind that it is not ready for production yet.
Note: for simplicity I assume that you are using a recent Ubuntu with git installed.


```bash
pip install nbpipeline
```

Graphiz is required for static SVG plots:

```bash
sudo apt-get install graphviz libgraphviz-dev graphviz-dev
```

#### Development install

To install the latest development version you may use:

```bash
git clone https://github.com/krassowski/nbpipeline
cd nbpipeline
pip install -r requirements.txt
ln -s $(pwd)/nbpipeline/nbpipeline.py ~/bin/nbpipeline
```

### Quickstart

Create `pipeline.py` file with list of rules for your pipeline. For example:

```python
from nbpipeline.rules import NotebookRule


NotebookRule(
    'Extract protein data',  # a nice name for the step
    input={'protein_data_path': 'data/raw/data_from_wetlab.xlsx'},
    output={'output_path': 'data/clean/protein_levels.csv'},
    notebook='analyses/Data_extraction.ipynb',
    group='Proteomics'  # this is optional
)

NotebookRule(
    'Quality control and PCA on proteins',
    input={'protein_levels_path': 'data/clean/protein_levels.csv'},
    output={'qc_report_path': 'reports/proteins_failing_qc.csv'},
    notebook='analyses/Exploration_and_quality_control.ipynb',
    group='Proteomics'
)
```

the keys of the input and output variables should correspond to variables in one of the first cells
in the corresponding notebook, which should be tagged as "parameters".
You will be warned if your notebook has no cell tagged as "parameters".

For more details, please see the example [pipeline](https://github.com/krassowski/nbpipeline/blob/master/examples/pipeline.py) and [notebooks](https://github.com/krassowski/nbpipeline/tree/master/examples/analyses) in the [examples](https://github.com/krassowski/nbpipeline/tree/master/examples) directory.


#### Run the pipeline:

```bash
nbpipeline
```

On any consecutive run the notebooks which did not change will not be run again.
To disable this cache, use `--disable_cache` switch.

To generate an interactive diagram of the rules graph, together with reproducibility report add `-i` switch:

```bash
nbpipeline -i
```

The software defaults to `google-chrome` for graph visualization display, which can be changed with a CLI option.

If you named your definition files differently (e.g. `my_rules.py` instead of `pipeline.py`), use:

```bash
nbpipeline --definitions_file my_rules.py
```


To display all command line options use:

```bash
nbpipeline -h
```


#### Troubleshooting

If you see `ModuleNotFoundError: No module named 'name_of_your_local_module'`, you may need to enforce the path, running nbpipeline with:

```bash
PYTHONPATH=/path/to/the/parent/of/local/module:$PYTHONPATH nbpipeline
```
