from pathlib import Path

from IPython.core.display import display, HTML


def create_paths(path, **kwargs):
    paths = {
        name: Path(path) / (name + '.' + ext)
        for ext, names in kwargs.items()
        for name in names
    }
    display(HTML(''), metadata={name: str(path) for name, path in paths.items()})
    return paths


def load_inputs(namespace, main_loader, loaders={}, inputs=None, validate=True, silent=False):
    if not inputs:
        inputs = namespace['__inputs__']

    loaded = {}

    for name, path in inputs.items():
        # in order to prevent accidental overwriting of variables:
        if validate and name in namespace:
            raise ValueError(f"Variable '{name}' is already present in the provided namespace")
        loader = loaders[name] if name in loaders else main_loader
        loaded[name] = loader(path)

    namespace.update(loaded)

    if not silent:
        return loaded


def save_outputs(namespace, outputs=None):
    if not outputs:
        outputs = namespace['__outputs__']

    for name, path in outputs.items():
        try:
            obj = namespace[name]
            found = True
        except KeyError:
            found = False
        if not found:
            raise NameError(f"Could not find variable '{name}' in the provided namespace")
        ext = path.name.split('.')[-1]
        try:
            saver = getattr(obj, f'to_{ext}')
        except AttributeError:
            raise AttributeError(f"'{name}'' has no 'to_{ext}()' method, which is needed to save to a {ext} file.")

        saver(path)
