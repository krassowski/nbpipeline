from ..utils import run_command


def deduce_web_url(repo_url: str):
    if repo_url.endswith('.git'):
        repo_url = repo_url[:-4]
    if repo_url.startswith('http'):
        return repo_url
    git, uri = repo_url.split('@')
    domain, path = uri.split(':')
    if domain == 'github.com':
        return 'https://github.com/' + path
    return path


def infer_repository_url():
    try:
        repo_url = run_command('git remote get-url origin').strip()
        return deduce_web_url(repo_url)
    except Exception:
        return

