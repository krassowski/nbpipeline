import json
import pickle
from os import system
from abc import ABC, abstractmethod
from pathlib import Path
import time
from tempfile import NamedTemporaryFile


def subset_dict_preserving_order(d, keys):
    return {k: v for k, v in d.items() if k in keys}


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
    
    rules = {}

    def __init__(self, name, **kwargs):
        """Notes:
            - input and output will be passed in the same order as it appears in kwargs
            - if the input is a dictionary, the keys will be intepreted as argument names; empty key can be used to insert a positional argument
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
    def run(self):
        pass
    
    @abstractmethod
    def to_json(self):
        pass


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

    def run(self):
        start_time = time.time()
        system(f'{self.command} {self.serialized_arguments}')
        self.execution_time = time.time() - start_time

    def to_json(self):
        return {
            'name': self.command,
            'arguments': self.serialized_arguments,
            'execution_time': self.execution_time,
            'type': 'shell'
        }


def run_command(command) -> str:
    from subprocess import run, PIPE
    result = run(command.split(' '), stdout=PIPE)
    return result.stdout.decode('utf-8')


def nice_time(seconds):
    if seconds is None:
        return
    total = seconds
    if total < 1:
        return f'{seconds * 100:.2f} ns'
    if total < 60:
        return f'{seconds:.2f} s'
    if total < 60*60:
        return f'{seconds/60:.2f} min'


class NotebookRule(Rule):

    cache_dir = '/tmp/nb_cache/'

    def __init__(
        self, *args, notebook,
        diff=True,
        # TODO: make this configurable? ue only relative paths with respect to TemporaryDict?
        # TODO: this has to be project dependent to avoid conflict caches!
        # TODO: moving the execution logic to a separate module might be a good idea
        output_nb_dir='/tmp/nbpipeline/out',
        reference_nb_store='/tmp/nbpipeline/ref/',
        stripped_nb_dir='/tmp/nbpipeline/stripped/',
        **kwargs
    ):
        super().__init__(*args, **kwargs)
        self.todos = []
        self.notebook = notebook
        self.generate_diff = diff
        self.output_nb_dir = output_nb_dir
        self.reference_nb_dir = reference_nb_store
        self.stripped_nb_dir = stripped_nb_dir
        self.diff = None
        self.text_diff = None
        self.fidelity = None
        self.images = []
        self.headers = []
        self.status = None

        from datetime import datetime, timedelta
        month_ago = (datetime.today() - timedelta(days=30)).timestamp()
        self.changes = run_command(f'git rev-list --max-age {month_ago} HEAD --count {self.notebook}')

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
    
    def run(self):
        """
        Run JupyterNotebook using PaperMill and compare the output with reference using nbdime
        """
        
        notebook = self.notebook
        path = Path(notebook)

        output_nb_dir = Path(self.output_nb_dir) / path.parent
        output_nb_dir.mkdir(parents=True, exist_ok=True)

        reference_nb_dir = Path(self.reference_nb_dir) / path.parent
        reference_nb_dir.mkdir(parents=True, exist_ok=True)

        stripped_nb_dir = Path(self.stripped_nb_dir) / path.parent
        stripped_nb_dir.mkdir(parents=True, exist_ok=True)

        output_nb = output_nb_dir / path.name
        reference_nb = reference_nb_dir / path.name
        stripped_nb = stripped_nb_dir / path.name

        md5 = run_command(f'md5sum {notebook}').split()[0]

        cache_dir = Path(self.cache_dir) / path.parent
        cache_dir.mkdir(parents=True, exist_ok=True)

        cache_nb_file = cache_dir / f'{md5}.json'

        to_cache = ['execution_time', 'fidelity', 'diff', 'text_diff', 'todos', 'headers', 'images']

        if cache_nb_file.exists():
            with open(cache_nb_file, 'rb') as f:
                pickled = pickle.load(f)
                print('Reusing cached results:')
                for key in to_cache:
                    setattr(self, key, pickled[key])
                return

        with open(notebook) as f:
            notebook_json = json.load(f)

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
        system(f'cat {notebook} | nbstripout > {stripped_nb}')

        # execute
        start_time = time.time()
        status = system(f'papermill {stripped_nb} {output_nb} {self.serialized_arguments}') or 0
        self.execution_time = time.time() - start_time
        self.status = status

        # inject parameters to a "reference" copy (so that we do not have spurious noise in the diff)
        system(f'papermill {notebook} {reference_nb} {self.serialized_arguments} --prepare-only')

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


"""
maybe something nested like

class Group:
    pass

class GroupSharingDirectory(Group):
    pass

GroupSharingDirectory(
    name='analyeses',
    members=[
        NotebookRule(),
        NotebookRule(),
    ]
)
"""