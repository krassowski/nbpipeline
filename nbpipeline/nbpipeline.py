#!/usr/bin/env python
import json
from collections import defaultdict
from pathlib import Path

from declarative_parser import Argument
from declarative_parser.constructor_parser import ConstructorParser
from pandas import read_csv, DataFrame

from rules import Rule, Group
from networkx import DiGraph, topological_sort
from argparse import FileType
from importlib.util import spec_from_file_location, module_from_spec
from os import system

from rules import run_command


def load_module(path):
    spec = spec_from_file_location('pipeline', path)
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Node:
    
    def __init__(self):
        pass

    def __repr__(self):
        return self.name.split('/')[-1]


class ArgumentNode(Node):
    
    def __init__(self, name, group):
        super().__init__()
        self.name = name
        self.group = group

    def to_json(self):
        return {
            'name': self.name,
            'type': 'argument',
            'label': self.name,
            'id': self.name.replace('/', '_'),
        }


class InputOutputNode(ArgumentNode):

    def __init__(self, path, group):
        self.path = path
        super().__init__(name=path, group=group)

    @property
    def head(self) -> DataFrame:
        sep = None
        if self.path.endswith('.csv'):
            sep = ','
        elif self.path.endswith('.tsv'):
            sep = '\t'
        if not sep:
            return DataFrame()
        return read_csv(self.path, sep=sep, nrows=10)

    def to_json(self):
        return {
            **super().to_json(),
            **{
                'type': 'io',
                'head': self.head.to_html()
            }
        }


class Cluster(object):

    def __init__(self, related_group=None):
        self.group = related_group
        self.members = set()

    def to_json(self):
        return {
            'name': self.group.name,
            'members': list(self.members),
            'color': self.group.color
        }


class NotebookPipeline:
    
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
        help='Should the graph be plotted',
        short='i'
    )

    graphiz_svg = Argument(
        action='store_true',
        short='g'
    )

    graph_width = Argument(
        type=int,
        short='w',
        default=int(1920/2)
    )

    graph_height = Argument(
        type=int,
        short='f',
        default=int(1050/2)
    )

    reload_graph = Argument(
        action='store_true',
        help='Should the graph be plotted',
        short='r'
    )

    def export_svg(self, rules_dag, path):
        from networkx.drawing.nx_agraph import to_agraph

        graph = to_agraph(rules_dag)
        graph.node_attr['fontname'] = 'Arial, sans-serf'
        graph.edge_attr['fontname'] = 'Arial, sans-serf'

        graph.write('foo.dot')
        graph.clear()

        system(f'dot -Tsvg foo.dot -o {path}')
        with open(path) as f:
            svg = f.read()
            insert_after = 'xmlns:xlink="http://www.w3.org/1999/xlink">'
            n = svg.replace(insert_after, insert_after + """
                <style>
                a:hover polygon {
                    fill: red;
                }
                </style>
                """)
        with open(path + '.svg', 'w') as f:
            f.write(n)

        system(f'google-chrome --app="file://{path}.svg"')

    def export_interactive_graph(self, rules_dag: DiGraph, path):

        groups = defaultdict(Cluster)

        for node in rules_dag.nodes:
            if not node.group:
                continue
            groups[node.group].members.add(node.name)

        for name, cluster in groups.items():
            if name in Group.groups:
                cluster.group = Group.groups[name]
            else:
                cluster.group = Group(name)

        json_dag = json.dumps({
            'nodes': [
                node.to_json()
                for node in rules_dag.nodes
            ],
            'edges': [
                {'from': edge[0].name, 'to': edge[1].name}
                for edge in rules_dag.edges
            ],
            'clusters': [
                cluster.to_json()
                for cluster in groups.values()
            ]
        })

        with open(Path(__file__).parent / 'graph.html') as f:
            template = f.read()

        to_substitute = {
            'json': json_dag,
            'repo_url': repr('https://github.com/krassowski/meningitis-integration')
        }
        graph_html = template
        for variable, value in to_substitute.items():
            graph_html = graph_html.replace('{{ ' + variable + ' }}', value)
        with open(path, 'w') as f:
            f.write(graph_html)

        system(f'google-chrome --app="file://{path}"')

    def iterate_rules(self, dag):
        return reversed([
            node
            for node in topological_sort(dag)
            if isinstance(node, Rule)
        ])

    def __init__(self, definitions_file, dry_run, interactive_graph, graph_width, graph_height, reload_graph,
                 graphiz_svg):
        self.graph_width = graph_width
        self.graph_height = graph_height
        load_module(definitions_file.name)
        rules = Rule.rules

        # TODO this is very fallible strategy, there are also, e.g. the URL could be https as well
        repo_url = run_command('git remote get-url origin')
        git, uri = repo_url.split('@')
        domain, path = uri.split(':')
        if path.endswith('.git'):
            path = path[:-4]
        if domain == 'github.com':
            for rule in rules.values():
                rule.repository_url = 'https://github.com/' + path

        dag = self.dag(rules)
        if not reload_graph:

            if dry_run:
                for node in self.iterate_rules(dag):
                    print(node.name)
            else:
                for node in self.iterate_rules(dag):
                    node.run()

            # refresh dag
        dag = self.dag(rules)

        if interactive_graph:
            self.export_interactive_graph(dag, path='/tmp/graph.html')

        if graphiz_svg:
            self.export_svg(dag, path='/tmp/graph.svg')

    def dag(self, rules) -> DiGraph:
        graph = DiGraph()
        
        for rule in rules.values():
            rule_node = rule
            graph.add_node(rule_node, **rule_node.to_graphiz())

            if rule.has_outputs:
                for key, output in rule.outputs.items():
                    output = InputOutputNode(output, group=rule.group)
                    if not graph.has_node(output):
                        graph.add_node(output, **output.to_json())
                    graph.add_edge(rule_node, output)
            if rule.has_inputs:
                for key, input in rule.inputs.items():
                    input = InputOutputNode(input, group=rule.group)
                    if not graph.has_node(input):
                        graph.add_node(input, **input.to_json())
                    graph.add_edge(input, rule_node)
        return graph
        

if __name__ == '__main__':
    parser = ConstructorParser(NotebookPipeline)

    options = parser.parse_args()
    program = parser.constructor(**vars(options))
