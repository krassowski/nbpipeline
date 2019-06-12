from networkx import DiGraph, topological_sort
from pandas import DataFrame, read_csv

from rules import Rule


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


class RulesGraph:

    def __init__(self, rules):

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

        self.graph = graph

    def iterate_rules(self):
        return reversed([
            node
            for node in topological_sort(self.graph)
            if isinstance(node, Rule)
        ])


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
