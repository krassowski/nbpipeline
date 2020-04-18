import json
import pickle
import re
from copy import copy
from functools import lru_cache
from os import system
from abc import ABC, abstractmethod
from pathlib import Path
import time
from tempfile import NamedTemporaryFile
from warnings import warn

from .utils import subset_dict_preserving_order, run_command, nice_time


class no_quotes(str):
    
    def __repr__(self):
        original = super().__repr__()
        return original[1:-1]


class Rule(ABC):
    """Design principles (or how does it differ from snakemake):
    
    - fully python3; no strange make/python mishmash
    - prefer verbosity over ambiguity (named inputs/outputs)
    - Jupyter centered
    - interactive graphs
    - implicit passing of arguments to the executing command 
    """

    cache_dir: Path
    tmp_dir: Path
    is_setup = False
    rules = {}

    def __init__(self, name, **kwargs):
        """Notes:
            - input and output will be passed in the same order as it appears in kwargs
            - if the input is a dictionary, the keys will be interpreted as argument names;
              empty key can be used to insert a positional argument
            - the arguments will be serialized preserving the Python type, i.e.
                    input={'name': 1}
                may result in:
                    --name 1
                while:
                    input={'name': "1"}
                would result in
                    --name "1"
                You can force string to be displayed without qoutes usingL
                    input={'name': no_quotes("1")}
        """
        assert name not in self.rules
        self.name = name
        self.execution_time = None
        self.rules[name] = self
        extra_kwargs = set(kwargs) - {'output', 'input', 'group'}
        if extra_kwargs:
            raise Exception(f'Unrecognized keyword arguments to {self.__class__.__name__}: {extra_kwargs}')
        self.arguments = subset_dict_preserving_order(
            kwargs,
            {'input', 'output'}
        )

        self.group = kwargs.get('group', None)
        self.outputs = {}
        self.inputs = {}

        if 'output' in kwargs:
            self.has_outputs = True
            output = kwargs['output']
            # todo support lists of positionals
            self.outputs = output if isinstance(output, dict) else {'': output}
        else:
            self.has_outputs = False
        if 'input' in kwargs:
            self.has_inputs = True
            input = kwargs['input']
            self.inputs = input if isinstance(input, dict) else {'': input} 
        else:
            self.has_inputs = False

    @abstractmethod
    def run(self, use_cache: bool) -> int:
        if not self.is_setup:
            raise ValueError('Please set up the rules class settings with Rule.setup() first!')

    @classmethod
    def setup(cls, cache_dir: Path, tmp_dir: Path):
        cls.cache_dir = Path(cache_dir)
        cls.tmp_dir = Path(tmp_dir)
        cls.is_setup = True

    @abstractmethod
    def to_json(self):
        pass

    def __repr__(self):
        fragments = [repr(self.name)]
        if self.group:
            fragments.append(f'({self.group})')
        if self.has_inputs or self.has_inputs:
            fragments.append('with')
        if self.has_inputs:
            fragments.append(f'{len(self.inputs)} inputs')
        if self.has_outputs:
            fragments.append(f'{len(self.outputs)} outputs')
        fragments = ' '.join(fragments)
        return f'<{self.__class__.__name__} {fragments}>'


class Group:
    """A group of rules"""
    groups = {}

    def __init__(self, name, color='#cccccc'):
        assert name not in self.groups
        self.name = name
        self.color = color
        self.groups[name] = self


class ShellRule(Rule):
    """
    Named arguments will be passed in order,
    preceded with a single dash for single letter names
    or a double dash for longer names.
     """
    def __init__(self, name, command, **kwargs):
        super().__init__(self, name, **kwargs)
        self.command = command

    def serialize(self, arguments_group):
        if isinstance(arguments_group, dict):
            return ' '.join(
                (
                    (
                        ('-' + key if len(key) == 1 else '--' + key)
                        +
                        ' '
                    )
                    if len(key) else
                    ''
                ) + (
                    repr(value)
                )
                for key, value in arguments_group.items()
            )
        else:
            return repr(arguments_group)

    @property
    def serialized_arguments(self):
        return ' '.join({
            self.serialize(arguments_group)
            for arguments_group in self.arguments.values()
        })

    def run(self, use_cache=False) -> int:
        super().run(use_cache)

        start_time = time.time()
        status = system(f'{self.command} {self.serialized_arguments}')
        self.execution_time = time.time() - start_time
        return status

    def to_json(self):
        return {
            'name': self.command,
            'arguments': self.serialized_arguments,
            'execution_time': self.execution_time,
            'type': 'shell'
        }


def expand_run_magics(notebook):
    out_notebook = copy(notebook)
    new_cells = []

    for cell in notebook['cells']:
        if cell['cell_type'] != 'code':
            new_cells.append(cell)
            continue

        if any(line.startswith('%run') for line in cell['source']):
            other_code = []
            for line in cell['source']:
                if line.startswith('%run'):
                    if other_code:
                        split_cell = copy(cell)
                        split_cell['source'] = other_code
                        new_cells.append(split_cell)
                        other_code = []
                    to_include = line[5:].strip()
                    with open(to_include) as o:
                        nb_run = json.load(o)
                    new_cells.extend(nb_run['cells'])
                else:
                    other_code.append(line)
            if other_code:
                split_cell = copy(cell)
                split_cell['source'] = other_code
                new_cells.append(split_cell)
        else:
            new_cells.append(cell)

    out_notebook['cells'] = new_cells
    return out_notebook


class NotebookRule(Rule):

    options: None

    @property
    def output_nb_dir(self) -> Path:
        return self.tmp_dir / 'out'

    @property
    def reference_nb_dir(self) -> Path:
        return self.tmp_dir / 'ref'

    @property
    def stripped_nb_dir(self) -> Path:
        return self.tmp_dir / 'stripped'

    def __init__(
        self, *args, notebook,
        diff=True,
        deduce_io=True,
        deduce_io_from_data_vault=True,
        **kwargs
    ):
        """Rule for Jupyter Notebooks

        Args:
            deduce_io: whether to automatically deduce inputs and outputs from the code cells tagged "inputs" and "outputs";
                local variables defined in the cell will be evaluated and used as inputs or outputs.
                If you want to generate paths with a helper function for brevity, assign a dict of {variable: path}
                to `__inputs__`/`__outputs__` in the tagged cell using `io.create_paths()` helper.
            diff: whether to generate diffs against the current state of the notebook
            deduce_io_from_data_vault: whether to deduce the inputs and outputs from `data_vault` magics
                (`%vault store` and `%vault import`), see https://github.com/krassowski/data-vault
        """
        super().__init__(*args, **kwargs)
        self.todos = []
        self.notebook = notebook
        self.absolute_notebook_path = Path(notebook).absolute()
        self.generate_diff = diff
        self.diff = None
        self.text_diff = None
        self.fidelity = None
        self.images = []
        self.headers = []
        self.status = None

        from datetime import datetime, timedelta
        month_ago = (datetime.today() - timedelta(days=30)).timestamp()
        self.changes = run_command(f'git rev-list --max-age {month_ago} HEAD --count {self.notebook}')

        if deduce_io:
            self.deduce_io_from_tags()

        if deduce_io_from_data_vault:
            self.deduce_io_from_data_vault()

    def deduce_io_from_data_vault(self):
        notebook_json = self.notebook_json
        stored = set()
        for index, cell in enumerate(notebook_json['cells']):
            if 'source' not in cell:
                continue
            for line in cell['source']:
                if line.startswith('%vault'):
                    try:
                        from data_vault import VaultMagics
                        from data_vault.actions import ImportAction, StoreAction
                        from data_vault.parsing import split_variables, unquote
                    except ImportError:
                        warn('Could not deduce I/O from data-vault %vault magics: data_vault not installed')
                        return
                    vault_magics = VaultMagics()
                    arguments = vault_magics.extract_arguments(line[7:])
                    action = vault_magics.select_action(arguments)
                    if isinstance(action, ImportAction):
                        variables = arguments['import']
                        for var_index, variable in enumerate(split_variables(variables)):
                            if 'from' in arguments:
                                import_path = arguments['from'] + '/' + variable
                            else:
                                import_path = unquote(arguments['import'])
                            if import_path in stored:
                                warn(f'Skipping {line} which was previously stored from this notebook to avoid cycles')
                            else:
                                self.inputs[(index, var_index)] = import_path
                        self.has_inputs = True
                    elif isinstance(action, StoreAction):
                        store_path = arguments['in'] + '/' + arguments['store']
                        self.outputs[index] = store_path
                        self.has_outputs = True
                        stored.add(store_path)

    def deduce_io_from_tags(self, io_tags={'inputs', 'outputs'}):
        notebook_json = self.notebook_json
        io_cells = {}

        for index, cell in enumerate(notebook_json['cells']):
            if 'tags' in cell['metadata']:
                cell_io_tags = io_tags.intersection(cell['metadata']['tags'])
                if cell_io_tags:
                    assert len(cell_io_tags) == 1
                    io_cells[list(cell_io_tags)[0]] = cell, index

        for io, (cell, index) in io_cells.items():
            assert not getattr(self, f'has_{io}')
            source = ''.join(cell['source'])
            if f'__{io}__' in source:
                assert len(cell['outputs']) == 1
                # TODO: search through lists
                values = cell['outputs'][0]['metadata']
            else:
                # so we don't want to use eval (we are not within an isolated copy yet!),
                # thus only simple regular expression matching which will fail on multi-line strings
                # (and anything which is dynamically generated)
                assignments = {
                    match.group('key'): match.group('value')
                    for match in re.finditer(r'^\s*(?P<key>.*?)\s*=\s*([\'"])(?P<value>.*)\2', source, re.MULTILINE)
                }
                values = {
                    key: value
                    for key, value in assignments.items()
                    if key.isidentifier() and value
                }
                if len(assignments) != len(values):
                    # TODO: add nice exception or warning
                    raise
            setattr(self, io, values)
            setattr(self, f'has_{io}', True)

    def serialize(self, arguments_group):
        return '-p ' + (' -p '.join(
            f'{key} {value}'
            for key, value in arguments_group.items()
        ))
        
    @property
    def serialized_arguments(self):
        return ' '.join({
            self.serialize(arguments_group)
            for arguments_group in self.arguments.values()
        })

    def outline(self, max_depth=3):
        return self.headers

    @property
    @lru_cache()
    def notebook_json(self):
        with open(self.absolute_notebook_path) as f:
            return expand_run_magics(json.load(f))

    def maybe_create_output_dirs(self):
        if self.has_outputs:
            for name, output in self.outputs.items():
                path = Path(output)
                path = path.parent
                if not path.exists():
                    print(f'Creating path "{path}" for "{name}" output argument')
                    path.mkdir(parents=True, exist_ok=True)

    def run(self, use_cache=True) -> int:
        """
        Run JupyterNotebook using PaperMill and compare the output with reference using nbdime

        Returns: status code from the papermill run (0 if successful)
        """
        super().run(use_cache)

        notebook = self.notebook
        path = Path(notebook)

        output_nb_dir = self.output_nb_dir / path.parent
        output_nb_dir.mkdir(parents=True, exist_ok=True)

        reference_nb_dir = self.reference_nb_dir / path.parent
        reference_nb_dir.mkdir(parents=True, exist_ok=True)

        stripped_nb_dir = self.stripped_nb_dir / path.parent
        stripped_nb_dir.mkdir(parents=True, exist_ok=True)

        output_nb = output_nb_dir / path.name
        reference_nb = reference_nb_dir / path.name
        stripped_nb = stripped_nb_dir / path.name

        md5 = run_command(f'md5sum {str(self.absolute_notebook_path)}').split()[0]

        cache_dir = self.cache_dir / path.parent
        cache_dir.mkdir(parents=True, exist_ok=True)

        cache_nb_file = cache_dir / f'{md5}.json'

        to_cache = ['execution_time', 'fidelity', 'diff', 'text_diff', 'todos', 'headers', 'images']

        if use_cache and cache_nb_file.exists():
            with open(cache_nb_file, 'rb') as f:
                pickled = pickle.load(f)
                print('Reusing cached results:')
                for key in to_cache:
                    setattr(self, key, pickled[key])
                return 0

        notebook_json = self.notebook_json

        self.images = [
            output['data']['image/png']
            for cell in notebook_json['cells']
            for output in cell.get('outputs', [])
            if 'data' in output and 'image/png' in output['data']
        ]

        self.headers = []

        for cell in notebook_json['cells']:
            if cell['cell_type'] == 'markdown':
                for line in cell['source']:
                    if line.startswith('#'):
                        self.headers.append(line)

        for cell in notebook_json['cells']:
            for line in cell.get('source', ''):
                if 'TODO' in line:
                    self.todos.append(line)

        # strip outputs (otherwise if it stops, the diff will be too optimistic)
        system(f'cat {self.absolute_notebook_path} | nbstripout > {stripped_nb}')

        # execute
        start_time = time.time()
        status = system(f'papermill {stripped_nb} {output_nb} {self.serialized_arguments}') or 0
        self.execution_time = time.time() - start_time
        self.status = status

        # inject parameters to a "reference" copy (so that we do not have spurious noise in the diff)
        system(f'papermill {self.absolute_notebook_path} {reference_nb} {self.serialized_arguments} --prepare-only')

        if self.generate_diff:
            with NamedTemporaryFile(delete=False) as tf:
                command = f'nbdiff {reference_nb} {output_nb} --ignore-metadata --ignore-details --out {tf.name}'
                run_command(command)
                with open(tf.name) as f:
                    self.diff = json.load(f)

            command = f'nbdiff {reference_nb} {output_nb} --ignore-metadata --ignore-details --no-use-diff --no-git'
            self.text_diff = run_command(command)

            from ansi2html import Ansi2HTMLConverter
            conv = Ansi2HTMLConverter()
            self.text_diff = conv.convert(self.text_diff)

            changes = len(self.diff[0]['diff']) if self.diff else 0

            # TODO: count only the code cells, not markdown cells?
            total_cells = len(notebook_json['cells'])
            self.fidelity = (total_cells - changes) / total_cells * 100

        if status == 0:
            with open(cache_nb_file, 'wb') as f:
                pickle.dump({
                    key: getattr(self, key)
                    for key in to_cache
                }, f)
        return status

    def to_json(self):

        notebook_name = Path(self.notebook).name
        
        return {
            'name': self.name,
            'arguments': self.serialized_arguments,
            'execution_time': self.execution_time,
            'type': 'notebook',
            'notebook': self.notebook,
            'notebook_name': notebook_name,
            'fidelity': self.fidelity,
            'changes_this_month': self.changes,
            'nice_time': nice_time(self.execution_time),
            'diff': self.diff,
            'text_diff': self.text_diff,
            'images': self.images,
            'label': self.notebook,
            'headers': self.headers,
            'status': self.status,
            'todos': self.todos
        }

    def to_graphiz(self):
        data = self.to_json()

        # TODO: move to static_graph
        buttons = [
            f'<td href="{self.repository_url}/commits/master/{self.notebook}">{self.changes} changes this month</td>'
        ]

        if self.fidelity is not None:
            buttons += [f'<td href="">Reproducibility: {self.fidelity:.2f}%</td>']

        if self.execution_time is not None:
            buttons += [f'<td>Runtime: {nice_time(self.execution_time)}</td>']

        buttons_html = '\n'.join(buttons)
        return {
            **data,
            **{
                'shape': 'plain',
                'label': f"""<<table cellspacing="0">
                <tr><td href="{self.repository_url}/blob/master/{self.notebook}" colspan="{len(buttons)}">{self.name.replace('&', ' and ')} - {data['notebook_name']}</td></tr>
                <tr>
                    { buttons_html }
                </tr>
                </table>>"""
            }
        }
