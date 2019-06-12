from rules import run_command


def infer_repository_url():
    # TODO this is very fallible strategy, there are also, e.g. the URL could be https as well
    repo_url = run_command('git remote get-url origin')
    git, uri = repo_url.split('@')
    domain, path = uri.split(':')
    if path.endswith('.git'):
        path = path[:-4]

    if domain == 'github.com':
        return 'https://github.com/' + path
