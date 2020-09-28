from pathlib import Path
from tempfile import NamedTemporaryFile

from pytest import warns
from pandas import read_csv

from nbpipeline.nbpipeline import Pipeline
from nbpipeline.rules import NotebookRule, expand_run_magics, Rule
from nbpipeline.version_control.git import deduce_web_url

Rule.setup(cache_dir=Pipeline.cache_dir.default, tmp_dir=Pipeline.tmp_dir.default)


def test_notebook_rule_fail():
    rule = NotebookRule(
        'Simple I/O failure',
        notebook='tests/Simple_input_output.ipynb',
        # input does not exist
        input={'input_file': 'xxx.csv'}
    )
    status_code = rule.run(use_cache=False)
    assert status_code != 0


def test_notebook_rule_parameters(capsys):
    result_path = Path('tests/test_output.csv')
    if result_path.exists():
        result_path.unlink()
    assert not result_path.exists()

    rule = NotebookRule(
        'Simple I/O',
        notebook='tests/Simple_input_output.ipynb',
        input={'input_file': 'tests/input.csv'},
        output={'output_file': result_path.as_posix()},
        parameters={}
    )
    assert str(rule) == "<NotebookRule 'Simple I/O' with 1 inputs and 1 outputs>"

    status_code = rule.run(use_cache=False)
    assert status_code == 0

    assert result_path.exists()

    result = read_csv(result_path)
    reference = read_csv('tests/output.csv')

    assert (result == reference).all().all()
    assert rule.outputs == {'output_file': result_path.as_posix()}

    # test cache:
    _ = capsys.readouterr()
    status_code = rule.run(use_cache=True)
    captured = capsys.readouterr()
    assert status_code == 0
    assert f'Reusing cached results for {rule}' in captured.out


def test_notebook_rule_skip_execute():
    rule = NotebookRule(
        'Simple I/O (to be skipped)',
        notebook='tests/Simple_input_output.ipynb',
        input={'input_file': 'tests/input.csv'},
        execute=False
    )
    assert str(rule) == "<NotebookRule 'Simple I/O (to be skipped)' with 1 inputs>"

    with warns(UserWarning, match='Skipping'):
        status_code = rule.run(use_cache=False)
    assert status_code == 0
    assert rule.execution_time is None


def test_notebook_rule_data_vault():
    with warns(
        UserWarning,
        match='Skipping %vault import output_df from test_result which was previously stored from this notebook to avoid cycles'
    ):
        rule = NotebookRule(
            'Data vault I/O',
            notebook='tests/Data_vault_io.ipynb'
        )
        assert str(rule) == "<NotebookRule 'Data vault I/O' with 4 inputs and 4 outputs>"
    assert rule.inputs == {
        (2, 0): 'io/input_df',
        (3, 0): 'io/a',
        (3, 1): 'io/b',
        (8, 0): 'io/input_df'
    }
    assert rule.outputs == {
        (6, 0): 'test_result/output_df',
        (12, 0): 'test_result/a',
        (12, 1): 'test_result/b',
        (13, 0): 'test_result/z'
    }


NOTEBOOK_TO_INCLUDE = """\
{
 "cells": [
  {
   "cell_type": "code",
   "execution_count": 1,
   "metadata": {},
   "outputs": [],
   "source": [
    "print('included')"
   ]
  }
 ],
 "metadata": {
  "kernelspec": {
   "display_name": "Python 3",
   "language": "python",
   "name": "python3"
  }
 },
 "nbformat": 4,
 "nbformat_minor": 4
}\
"""


def notebook_with_run_magic(path):
    return {
        'cells': [
            {
                "cell_type": "code",
                "execution_count": 1,
                "metadata": {},
                "outputs": [],
                "source": [
                    "print('test0')"
                ],
            },
            {
                "cell_type": "code",
                "execution_count": 2,
                "metadata": {},
                "outputs": [],
                "source": [
                    "print('test1')\n",
                    f"%run {path}\n",
                    "print('test2')"
                ],
            },
            {
                "cell_type": "code",
                "execution_count": 3,
                "metadata": {},
                "outputs": [],
                "source": [
                    "print('test3')"
                ],
            }
        ],
        'metadata': {
            "kernelspec": {
                "display_name": "Python 3",
                "language": "python",
                "name": "python3"
            }
        },
        'nbformat': 4,
        'nbformat_minor': 4
    }


def test_expand_run_magics():
    with NamedTemporaryFile(mode='wt', suffix='.ipynb') as f:
        f.write(NOTEBOOK_TO_INCLUDE)
        f.flush()
        result = expand_run_magics(notebook_with_run_magic(f.name))
    cells = result['cells']
    assert len(cells) == 5
    assert cells[0]['source'] == ["print('test0')"]
    assert cells[1]['source'] == ["print('test1')\n"]
    assert cells[2]['source'] == ["print('included')"]
    assert cells[3]['source'] == ["print('test2')"]
    assert cells[4]['source'] == ["print('test3')"]


def test_repository_url():
    assert deduce_web_url('git@github.com:krassowski/nbpipeline.git') == 'https://github.com/krassowski/nbpipeline'
    assert deduce_web_url('https://github.com/krassowski/nbpipeline.git') == 'https://github.com/krassowski/nbpipeline'
    assert deduce_web_url('ssh://git@github.com/krassowski/nbpipeline') == 'https://github.com/krassowski/nbpipeline'
