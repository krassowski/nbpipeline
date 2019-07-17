from argparse import FileType

from declarative_parser import Argument

from .version_control.git import infer_repository_url


class PipelineOptions:

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

    output_dir = Argument(
        type=str,
        default='nbpipe_out/'
    )

    make_output_dirs = Argument(
        action='store_false',
        short='m'
    )
