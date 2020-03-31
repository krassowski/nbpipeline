from pathlib import Path

from pandas import read_csv

from nbpipeline.rules import NotebookRule


def test_notebook_rule_fail():
    rule = NotebookRule(
        'Simple I/O failure',
        notebook='tests/Simple_input_output.ipynb',
        # input does not exist
        input={'input_file': 'xxx.csv'}
    )
    status_code = rule.run(use_cache=False)
    assert status_code != 0


def test_notebook_rule_parameters():
    result_path = Path('tests/test_output.csv')
    if result_path.exists():
        result_path.unlink()
    assert not result_path.exists()

    rule = NotebookRule(
        'Simple I/O',
        notebook='tests/Simple_input_output.ipynb',
        input={'input_file': 'tests/input.csv'},
        output={'output_file': result_path.as_posix()}
    )
    status_code = rule.run(use_cache=False)
    assert status_code == 0

    assert result_path.exists()

    result = read_csv(result_path)
    reference = read_csv('tests/output.csv')

    assert (result == reference).all().all()
    assert rule.outputs == {'output_file': result_path.as_posix()}


def test_notebook_rule_data_vault():
    rule = NotebookRule(
        'Data vault I/O',
        notebook='tests/Data_vault_io.ipynb'
    )
    assert rule.inputs == {
        (2, 0): 'io/input_df',
        (3, 0): 'io/a',
        (3, 1): 'io/b',
        (8, 0): 'io/input_df'
    }
    assert rule.outputs == {
        6: 'test_result/output_df'
    }
