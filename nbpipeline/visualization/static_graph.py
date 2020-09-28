from os import system
from tempfile import NamedTemporaryFile
import json
from warnings import warn


def static_graph(rules_dag, options='{}'):
    from networkx.drawing.nx_agraph import to_agraph

    graph = to_agraph(rules_dag)
    graph.node_attr['fontname'] = 'Arial, sans-serf'
    graph.edge_attr['fontname'] = 'Arial, sans-serf'

    options = json.loads(options)
    top_level_keys = {
        'node': 'node_attr',
        'edge': 'edge_attr',
        'graph': 'graph_attr'
    }

    for key, items in options.items():
        if key not in top_level_keys:
            warn(f'Unknown static plot top-level key: {key}')
        else:
            attributes = getattr(graph, top_level_keys[key])
            for attr, value in items.items():
                attributes[attr] = value

    with NamedTemporaryFile(suffix='.dot') as dot_file:
        graph.write(dot_file.name)
        graph.clear()

        with NamedTemporaryFile(mode='r', suffix='.svg') as temp_file:
            status = system(f'dot -Tsvg {dot_file.name} -o {temp_file.name}')
            assert status == 0

            svg = temp_file.read()
            insert_after = 'xmlns:xlink="http://www.w3.org/1999/xlink">'
            processed = svg.replace(insert_after, insert_after + """
                <style>
                a:hover polygon {
                    fill: yellow;
                }
                </style>
            """)

    return processed
