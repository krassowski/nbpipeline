from os import chdir, getcwd
from pathlib import Path

def use_absolute_paths():
    local_dir = getcwd()
    top_level = Path(__file__).parent.parent

    # always use the same, absolute paths - which makes
    # moving the notebooks around easier in the future
    chdir(top_level)