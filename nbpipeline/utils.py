from contextlib import contextmanager
import os
from pathlib import Path


def subset_dict_preserving_order(d, keys):
    return {k: v for k, v in d.items() if k in keys}


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


@contextmanager
def cd(path: Path):
    last_path = Path.cwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(last_path)
