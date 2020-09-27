import json
from pathlib import Path

from jinja2 import Environment, select_autoescape, FileSystemLoader

from ..rules import Group


def render_template(path, **kwargs):
    templates_path = Path(__file__).parent / 'templates'
    env = Environment(
        loader=FileSystemLoader(str(templates_path)),
        autoescape=select_autoescape(['html', 'xml'])
    )
    template = env.get_template(path)
    return template.render(**kwargs)


def generate_graph(rules_dag, **kwargs):

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
            for cluster in Group.groups.values()
        ]
    })

    kwargs['json'] = json_dag
    kwargs = {
        'json': json_dag,
    }

    return render_template('graph.html', **kwargs)
