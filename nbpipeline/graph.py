from functools import partial
from pathlib import Path
from typing import List
from warnings import warn

from networkx import DiGraph, simple_cycles
from pandas import DataFrame, read_csv, read_table, read_excel, read_html, read_json

from .rules import Rule


class Node:

    def __init__(self, name, group):
        super().__init__()
        self.name = name
        self.group = group

    def __repr__(self):
        name = self.name.split('/')[-1]
        return f'<{self.__class__.__name__} {name}>'


class ArgumentNode(Node):

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

    readers = {
        'csv': read_csv,
        'tsv': read_table,
        'xls': read_excel,
        'xlsx': read_excel,
        'html': read_html,
        'json': read_json,
        # just read anything as rows, ignore sep
        'txt': partial(read_table, sep='||||||||')
    }

    @property
    def exists(self):
        return Path(self.path).exists()

    @property
    def head(self) -> DataFrame:
        if not self.exists:
            return DataFrame()
        extension = Path(self.path).suffix
        if extension in self.readers:
            read = self.readers[extension]
            try:
                return read(self.path, nrows=10)
            except Exception as e:
                warn(f'Failed to read file {self.path}: {e}')
        return DataFrame()

    def to_json(self):
        return {
            **super().to_json(),
            **{
                'type': 'io',
                'head': self.head.to_html(),
                'exists': self.exists
            }
        }


class RulesGraph:

    def __init__(self, rules):

        graph = DiGraph()
        io_nodes = {}

        for rule in rules.values():
            rule_node = rule
            graph.add_node(rule_node, **rule_node.to_graphiz())

            if rule.has_outputs:
                for output in rule.outputs.values():
                    if output not in io_nodes:
                        output_node = InputOutputNode(output, group=rule.group)
                        io_nodes[output] = output_node
                        graph.add_node(output_node, **output_node.to_json())
                    output_node = io_nodes[output]
                    graph.add_edge(rule_node, output_node)
            if rule.has_inputs:
                for input in rule.inputs.values():
                    if input not in io_nodes:
                        input_node = InputOutputNode(input, group=rule.group)
                        io_nodes[input] = input_node
                        graph.add_node(input_node, **input_node.to_json())
                    input_node = io_nodes[input]
                    graph.add_edge(input_node, rule_node)

        self.graph = graph

    def iterate_rules(self, verbose=False) -> List[Rule]:
        """Order rules (tasks) in an order allowing for sequential execution,

        so that each task has the required inputs available
        at the time it is scheduled to run (where the inputs
        are outputs of previously run tasks, or just inputs
        which do not depend on any other tasks)
        """

        cycles = list(simple_cycles(self.graph))
        if any(cycles):
            for n in cycles[0]:
                if hasattr(n, 'inputs'):
                    print(n.inputs)
                if hasattr(n, 'outputs'):
                    print(n.outputs)
            raise ValueError(f'Could not construct DAG: cycles detected: {cycles}')

        rules = {
            node
            for node in self.graph.nodes()
            if isinstance(node, Rule)
        }

        available_inputs = {
            node
            for node in self.graph.nodes()
            if isinstance(node, InputOutputNode) and len(self.graph.in_edges(node)) == 0
        }

        roots = {
            rule
            for rule in rules
            # no inputs, or all inputs are available from start (do not relay on other rules)
            if not rule.has_inputs or all(
                input in available_inputs
                for input, myself in self.graph.in_edges(rule)
            )
        }

        sort = []

        leads = list(roots)

        if verbose:
            print(f'Starting with: {leads}')
            print(f'Inputs available to start with: {available_inputs}')

        while leads:
            rule = leads.pop(0)
            if rule in sort:
                continue
            if any(input not in available_inputs for input, myself in self.graph.in_edges(rule)):
                # cannot process just yet (some input is missing), move to the back of the queue
                if verbose:
                    print(f'cannot process {rule} just yet (some input is missing), moving it to the back of the queue')
                leads.append(rule)
                continue

            if verbose:
                print(f'processing {rule}')
            # mark as visited
            rules.remove(rule)
            sort.append(rule)

            # add outputs
            for myself, output in self.graph.out_edges(rule):
                assert rule == myself
                if verbose:
                    print(f'got output: {output} ')
                available_inputs.add(output)
                # and start thinking about tasks which can be accomplished using these outputs
                for itself, next_node in self.graph.out_edges(output):
                    assert itself == output
                    assert isinstance(next_node, Rule)
                    if verbose:
                        print(f'adding {next_node} to consider later')
                    leads.append(next_node)

        assert not rules

        return sort


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
