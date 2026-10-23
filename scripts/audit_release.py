"""Check release files without exposing secret values. --tracked is required before any approved push.

--working-tree checks candidate source files when no Git metadata is available;
it cannot certify what was committed or removed from repository history.
--candidate audits the actual index + non-ignored untracked Git paths before staging.
"""
import argparse
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]
REQUIRED = ['models/intent_clf.joblib', 'kb/shipping.md', 'eval/intent_to_kb.json',
            'frontend/src/data/evaluation.v1.json', 'frontend/package-lock.json',
            'requirements-render.txt', 'render.yaml', '.gitignore', '.python-version',
            'src/api.py', 'scripts/start_render.sh', 'scripts/check_runtime.py',
            'frontend/package.json', 'frontend/vercel.json']
DENIED_PARTS = {'.venv', 'venv', 'node_modules', '.next', '.cache', '.aws', '.vercel', '__pycache__', '.pytest_cache', '.huggingface', 'htmlcov', 'out', '.coverage', '.DS_Store', 'test-results', 'playwright-report'}
PATTERNS = [re.compile(p) for p in (
    r'(?:AKIA|ASIA)[0-9A-Z]{16}', r'sk-ant-[A-Za-z0-9_-]{24,}',
    r'sk-(?:(?:proj|svcacct)-)?[A-Za-z0-9_-]{32,}',
    r'gh[pousr]_[A-Za-z0-9]{30,}', r'github_pat_[A-Za-z0-9_]{35,}',
    r'AIza[A-Za-z0-9_-]{30,}', r'xox[baprs]-[A-Za-z0-9-]{20,}',
    r'(?:sk|rk)_live_[A-Za-z0-9]{20,}',
    r'-----BEGIN (?:RSA |EC |OPENSSH |DSA |ENCRYPTED )?PRIVATE KEY-----',
)]


def denied(path):
    p = Path(path)
    generated = {'.tox', '.nox', '.mypy_cache', '.ruff_cache', '.pyright', '.ipynb_checkpoints',
                 'build', 'dist', 'coverage', 'logs', '.idea', '.vscode', '.ssh', '.kube'}
    credential_files = {'secrets.toml', '.envrc', '.netrc', '.npmrc', '.pypirc', '.git-credentials',
                        'credentials.json', 'id_rsa', 'id_ed25519', 'Thumbs.db', 'Desktop.ini'}
    suffixes = {'.db', '.sqlite', '.sqlite3', '.pem', '.key', '.pyc', '.pyo', '.p12', '.pfx',
                '.keystore', '.log', '.prof', '.lprof', '.egg', '.swp', '.swo'}
    return (bool(set(p.parts) & (DENIED_PARTS | generated)) or p.name == '.env' or
            (p.name.startswith('.env.') and p.name != '.env.example') or
            p.name.startswith(('.envrc.', 'service-account', '._')) or p.name in credential_files or
            p.suffix in suffixes or p.name.endswith(('~', '.tsbuildinfo')) or
            any(mark in p.name for mark in ('.db-', '.db.', '.sqlite-', '.sqlite.', '.sqlite3-', '.sqlite3.', '.log.')) or
            any(part.endswith('.egg-info') for part in p.parts) or
            str(p).startswith(('data/raw/', 'data/processed/')) and p.name != '.gitkeep')


def candidate_paths():
    result = subprocess.run(['git', 'ls-files', '--cached', '--others', '--exclude-standard', '-z'],
                            cwd=ROOT, capture_output=True)
    if result.returncode:
        raise RuntimeError('No Git metadata; initialize this repository before --candidate')
    return sorted(set(v for v in result.stdout.decode().split('\0') if v))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    group = p.add_mutually_exclusive_group(required=True)
    group.add_argument('--tracked', action='store_true')
    group.add_argument('--working-tree', action='store_true')
    group.add_argument('--candidate', action='store_true')
    args = p.parse_args()
    if args.tracked:
        result = subprocess.run(['git', 'ls-files', '-z'], cwd=ROOT, capture_output=True)
        if result.returncode:
            raise SystemExit('BLOCKED: no Git metadata; tracked files/history cannot be audited')
        files = [v for v in result.stdout.decode().split('\0') if v]
        for needed in REQUIRED:
            if needed not in files:
                raise SystemExit('BLOCKED: required artifact is not tracked: ' + needed)
    elif args.candidate:
        files = candidate_paths()
        for needed in REQUIRED:
            if needed not in files:
                raise SystemExit('BLOCKED: required artifact is ignored or absent: ' + needed)
    else:
        files = [str(f.relative_to(ROOT)) for base in ('src', 'scripts', 'tests', 'kb', 'eval', 'reports', 'docs', 'models', 'frontend/src', 'frontend/tests')
                 for f in (ROOT / base).rglob('*') if f.is_file() and not denied(str(f.relative_to(ROOT)))]
        files += [str(f.relative_to(ROOT)) for parent in (ROOT, ROOT / 'frontend', ROOT / '.streamlit')
                  for f in parent.iterdir() if f.is_file() and not denied(str(f.relative_to(ROOT)))]
        print('Candidate source scan only; not proof of tracked files or Git history')
    for needed in REQUIRED:
        if not (ROOT / needed).is_file():
            raise SystemExit('BLOCKED: missing required serving artifact: ' + needed)
    for file in files:
        if denied(file):
            raise SystemExit('BLOCKED: private/state/cache file tracked: ' + file)
        path = ROOT / file
        if path.is_symlink():
            raise SystemExit('BLOCKED: review symlink before publication: ' + file)
        if path.is_file():
            if path.stat().st_size > 100 * 1024 * 1024:
                raise SystemExit('BLOCKED: file exceeds GitHub regular Git limit: ' + file)
            if path.stat().st_size > 50 * 1024 * 1024:
                print('REVIEW: GitHub large-file warning threshold: ' + file)
            try:
                text = path.read_bytes().decode('utf-8', errors='ignore')
            except OSError:
                raise SystemExit('BLOCKED: cannot read candidate: ' + file)
            if any(pattern.search(text) for pattern in PATTERNS):
                raise SystemExit('BLOCKED: possible credential in ' + file + ' (value suppressed)')
    print(f'PASS: {len(files)} candidate/tracked paths checked; required artifacts present; no matched credential patterns')
    print('Manual data review and Git-history secret scan remain required before publication')


if __name__ == '__main__':
    main()
