from os import system
from tempfile import NamedTemporaryFile


def static_graph(rules_dag):
    from networkx.drawing.nx_agraph import to_agraph

    graph = to_agraph(rules_dag)
    graph.node_attr['fontname'] = 'Arial, sans-serf'
    graph.edge_attr['fontname'] = 'Arial, sans-serf'

    with NamedTemporaryFile(suffix='.dot') as dot_file:
        graph.write(dot_file.name)

    graph.clear()

    with NamedTemporaryFile(mode='r', suffix='.svg') as temp_file:
        system(f'dot -Tsvg {dot_file.name} -o {temp_file.name}')

        # with open(temp_file.name) as f:
        svg = temp_file.read()
        insert_after = 'xmlns:xlink="http://www.w3.org/1999/xlink">'
        processed = svg.replace(insert_after, insert_after + """
            <style>
            a:hover polygon {
                fill: red;
            }
            </style>
        """)

    return processed
