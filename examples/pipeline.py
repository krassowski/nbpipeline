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
