from ..utils import run_command


def deduce_web_url(repo_url: str):
    if repo_url.endswith('.git'):
        repo_url = repo_url[:-4]
    if repo_url.startswith('http'):
        return repo_url
    if repo_url.startswith('ssh://'):
        repo_url = repo_url[6:]
    git, uri = repo_url.split('@')
    if ':' in uri:
        domain, path = uri.split(':')
        return f'https://{domain}/{path}'
    else:
        return f'https://{uri}'


def infer_repository_url():
    try:
        repo_url = run_command('git remote get-url origin').strip()
        return deduce_web_url(repo_url)
    except Exception:
        return

