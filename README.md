# nbpipeline
Snakemake-like pipelines for Jupyter Notebooks

### Install & general remarks

these are still early days of this software so please bear in mind that it is not ready for packaging and distribution yet.
If you wish to continue and evaluate it as-is, please follow these steps:

Note: for simplicity I assume that you are using a recent Ubuntu with git installed.

```bash
git clone https://github.com/krassowski/nbpipeline
cd nbpipeline
pip install -r requirements.txt
ln -s $(pwd)/nbpipeline/nbpipeline.py ~/bin/nbpipeline
```

### Quickstart

Create `pipeline.py` file with list of rules for your pipeline. For example:

```python
from rules import NotebookRule

NotebookRule(
    'Extract protein data',  # a nice name for the step
    input={'protein_data_path': 'data/raw/Protein/data_from_wetlab.xlsx'},
    output={'output_path': 'data/clean/protein/levels.csv'},
    notebook='protein/Data_extraction.ipynb',
    group='Proteomics', # this is optional
)


NotebookRule(
    'Quality control and PCA on proteins',
    input={'protein_levels_path': 'data/clean/protein/levels.csv'},
    output={'qc_report_path': 'reports/proteins_failing_qc.csv'},
    notebook='protein/Exploration_and_quality_control.ipynb',
    group='Proteomics'
)
```

the keys of the input and output variables should correspond to variables in one of the first cells
in the corresponding notebook, which should be tagged as "parameters".
You will be warned if your notebook has no cell tagged as "parameters".

#### Run the pipeline:

```
nbpipepline
```

On any consecutive run the notebooks which did not change will not be run again.
To disable this cache, use `--disable_cache` switch.

To generate an interactive diagram of the rules graph, together with reproducibility report add `-i` switch:

```
nbpipepline -i
```

The software defaults to `google-chrome` for graph visualization display, which can be changed with a CLI option.

If you named your definition files differently (e.g. `my_rules.py` instead of `pipeline.py`), use:

```
nbpipepline --definitions_file my_rules.py
```


To display all command line options use:

```
nbpipepline -h
```
