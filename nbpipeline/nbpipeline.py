#!/usr/bin/env python
from argparse import FileType
from os import system
from importlib.util import spec_from_file_location, module_from_spec
from pathlib import Path

from declarative_parser import Argument
from declarative_parser.constructor_parser import ConstructorParser
from networkx import DiGraph

from .utils import cd
from .version_control.git import infer_repository_url
from .graph import RulesGraph
from .rules import Rule
from .visualization.interactive_graph import generate_graph
from .visualization.static_graph import static_graph


def load_module(path):
    spec = spec_from_file_location('pipeline', path)
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Pipeline:

    dry_run = Argument(
        action='store_true',
        help='Do not execute anything, just display what would be done.',
        short='n'
    )

    definitions_file = Argument(
        type=FileType(),
        help='The file with rule definitions',
        default='pipeline.py'
    )

    interactive_graph = Argument(
        action='store_true',
        help='Should the interactive graph be plotted',
        short='i'
    )

    static_graph = Argument(
        action='store_true',
        short='s'
    )

    graph_width = Argument(
        type=int,
        short='w',
        default=int(1920/2)
    )

    graph_height = Argument(
        type=int,
        default=int(1050/2)
    )

    just_plot_the_last_graph = Argument(
        action='store_true',
        help='Skip all computations and just display the most recent graph from previous runs',
        short='j'
    )

    repository_url = Argument(
        type=str,
        short='u',
        default=infer_repository_url(),
        help='Path to the repository URL to be used to generate URL links on graphs;'
             ' by default will be inferred from git repository (but this may fail).'
    )

    display_graph_with = Argument(
        type=str,
        default='google-chrome --app="{path}"',
        help='The browser to display the graph with; by default we will try to use google-chrome in app mode.'
             ' The path to the file will be substituted for {path} variable if present or otherwise, appended'
             ' at the end of the command.'
    )

    disable_cache = Argument(
        action='store_true',
        short='d'
    )

    # TODO:
    # output_dir = Argument(
    #     type=str,
    #     default='nbpipe_out/'
    # )
    # to make the output dir work we need to:
    # - have symlinks to all inputs in the 'output_dir'
    # - prefix everything (input and outputs) with 'output_dir'
    # - we would need to detect inputs with symlinks used in outputs and raise in such cases
    #   so that the user would not loose precious input data by accident (but give an option to disable)
    # simple change of cwd does not work as we python can no longer resolve modules

    make_output_dirs = Argument(
        action='store_false',
        short='m'
    )

    run_from_root = Argument(
        action='store_true',
        default=False
    )

    def display(self, path):
        browser = self.display_graph_with

        if not browser or browser == 'none':
            return

        path = f'file://{path}'

        if '{path}' in browser:
            browser = browser.format(path=path)
        else:
            browser += path
        system(browser)

    def export_svg(self, rules_dag, path):

        graph_svg = static_graph(rules_dag)

        with open(path, 'w') as f:
            f.write(graph_svg)

        self.display(path)

    def export_interactive_graph(self, rules_dag: DiGraph, path):

        graph_html = generate_graph(rules_dag, **self.parameters)

        with open(path, 'w') as f:
            f.write(graph_html)

        self.display(path)

    def __init__(self, **kwargs):
        self.status = 1
        self.parameters = kwargs

        for key, value in kwargs.items():
            setattr(self, key, value)

        # execute the pipeline definitions (loads them into Rule.rules)
        load_module(self.definitions_file.name)

        rules = Rule.rules
        Rule.pipeline_config = self

        for rule in rules.values():
            rule.repository_url = self.repository_url

        graph = RulesGraph(rules)
        # TODO
        # Path(self.output_dir).mkdir(exist_ok=True, parents=True)

        if not self.just_plot_the_last_graph:

            for node in graph.iterate_rules():

                if self.dry_run:
                    print(node.name)
                else:
                    if self.make_output_dirs and hasattr(node, 'maybe_create_output_dirs'):
                        node.maybe_create_output_dirs(node)
                    if self.run_from_root or not hasattr(node, 'notebook'):
                        node.run(use_cache=not self.disable_cache)
                    else:
                        with cd(Path(node.notebook).parent):
                            node.run(use_cache=not self.disable_cache)

        dag = RulesGraph(rules).graph

        if self.interactive_graph:
            # TODO add an option to create standalone files by inlining all the css and js dependencies
            self.export_interactive_graph(dag, path='/tmp/graph.html')

        if self.static_graph:
            self.export_svg(dag, path='/tmp/graph.svg')

        self.status = 0


def main():
    parser = ConstructorParser(Pipeline)
    options = parser.parse_args()
    program = parser.constructor(**vars(options))
    return program.status


if __name__ == '__main__':
    main()
