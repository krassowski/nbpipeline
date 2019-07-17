from ..utils import run_command


def infer_repository_url():
    # TODO this is quite fallible strategy
    try:
        repo_url = run_command('git remote get-url origin').strip()
        if repo_url.startswith('http'):
            return repo_url
        git, uri = repo_url.split('@')
        domain, path = uri.split(':')
        if path.endswith('.git'):
            path = path[:-4]
    except Exception:
        return

    if domain == 'github.com':
        return 'https://github.com/' + path
