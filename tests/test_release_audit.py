"""Publication policy: protect local state while retaining real serving/evaluation assets."""
import pytest
from scripts.audit_release import denied, PATTERNS, candidate_paths


@pytest.mark.parametrize('path', [
    '.env', 'frontend/.env.local', '.env.production', '.envrc', 'frontend/.npmrc',
    'data/supportpilot.db', 'data/supportpilot.db-wal', 'backup/tickets.db.bak',
    'db/demo.sqlite-journal', 'db/demo.sqlite3.backup', 'logs/api.log', 'api.log.1',
    '.venv/pyvenv.cfg', 'frontend/node_modules/next/package.json', 'frontend/.next/BUILD_ID',
    'frontend/test-results/result.json', '.pytest_cache/state', '.ruff_cache/state',
    'frontend/tsconfig.tsbuildinfo', '.ssh/id_rsa', 'private/key.p12', '.DS_Store',
    'data/raw/bitext_support.csv', 'data/processed/train.csv', 'build/package.whl',
])
def test_generated_and_sensitive_paths_are_not_release_files(path):
    assert denied(path)


@pytest.mark.parametrize('path', [
    '.env.example', 'frontend/.env.example', 'models/intent_clf.joblib',
    'frontend/src/data/evaluation.v1.json', 'reports/e2e_fallback.csv',
    'eval/realistic_tickets.csv', 'data/raw/.gitkeep', 'frontend/package-lock.json',
    'Dockerfile', 'render.yaml', 'scripts/start_render.sh',
])
def test_required_assets_and_safe_examples_are_preserved(path):
    assert not denied(path)


def test_provider_shaped_keys_are_detected_without_embedding_a_literal_secret():
    examples = ['AK' + 'IA' + 'A' * 16, 'sk-' + 'proj-' + 'a' * 40,
                'github_' + 'pat_' + 'a' * 40, 'sk-' + 'ant-' + 'a' * 32]
    assert all(any(pattern.search(value) for pattern in PATTERNS) for value in examples)


def test_candidate_mode_uses_git_ignore_rules_and_keeps_serving_assets():
    files = candidate_paths()
    assert 'models/intent_clf.joblib' in files
    assert 'frontend/src/data/evaluation.v1.json' in files
    assert 'frontend/.env.example' in files
    assert not any(denied(file) for file in files)
