"""Deployment policies run on temporary DBs; no remote services or real tickets are touched."""
import json
import os
import subprocess
import sys
import time
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from src import api, store, llm, tools
from src.deployment import permitted_origins


@pytest.fixture
def demo_client(tmp_path, monkeypatch):
    monkeypatch.setattr(store, 'DB_PATH', tmp_path / 'isolated-demo.db')
    monkeypatch.setattr(api, 'DEMO_MODE', True)
    monkeypatch.setattr(store, 'DEMO_MODE', True)
    monkeypatch.setattr(tools, 'DEMO_MODE', True)
    monkeypatch.setattr(llm, 'DEMO_MODE', True)
    api._demo_requests.clear()
    with TestClient(api.app) as client:
        yield client
    api._demo_requests.clear()


def test_health_readiness_and_ephemeral_mode(demo_client):
    health = demo_client.get('/health').json()
    assert health['status'] == 'ok' and health['model_loaded']
    assert health['demo_mode'] is True and health['storage'] == 'ephemeral'
    assert not health['llm'] and not health['order_writes'] and not health['approvals']


@pytest.mark.parametrize('value', ['*', 'https://*.vercel.app', 'https://demo.vercel.app/', 'https://demo.vercel.app/path', 'https://user:pass@demo.vercel.app', 'ftp://demo.vercel.app', 'https://demo.vercel.app?x=1'])
def test_cors_configuration_rejects_wildcards_credentials_and_paths(value):
    with pytest.raises(ValueError):
        permitted_origins(value)


def test_exact_cors_origins_and_preflight(demo_client):
    assert permitted_origins('https://demo.vercel.app, http://localhost:3000,https://demo.vercel.app') == ['https://demo.vercel.app', 'http://localhost:3000']
    allowed = demo_client.options('/tickets', headers={'Origin': 'http://localhost:3000', 'Access-Control-Request-Method': 'POST', 'Access-Control-Request-Headers': 'content-type'})
    assert allowed.status_code == 200
    assert allowed.headers['access-control-allow-origin'] == 'http://localhost:3000'
    denied = demo_client.options('/tickets', headers={'Origin': 'https://evil.vercel.app', 'Access-Control-Request-Method': 'POST'})
    assert denied.status_code == 400 and 'access-control-allow-origin' not in denied.headers


def test_demo_blocks_even_a_valid_reviewer_and_paid_processing(demo_client, monkeypatch):
    monkeypatch.setenv('TICKETPILOT_REVIEWER_TOKEN', 'demo-policy-test-token')
    monkeypatch.setenv('ANTHROPIC_API_KEY', 'not-a-real-key')
    ticket = demo_client.post('/tickets', json={'text': 'Where is my order 10233?', 'use_llm': False}).json()
    for data in ({'approved': True}, {'approved': False}, {'corrected_intent': 'complaint'}):
        response = demo_client.post(f"/tickets/{ticket['id']}/feedback", json=data, headers={'Authorization': 'Bearer demo-policy-test-token'})
        assert response.status_code == 403
    assert demo_client.post('/tickets', json={'text': 'demo', 'use_llm': True}).status_code == 403
    assert llm.llm_available() is False
    llm.client.cache_clear()
    with pytest.raises(RuntimeError, match='disabled'):
        llm.client()
    assert demo_client.get(f"/tickets/{ticket['id']}").json()['status'] == ticket['status']


def test_public_and_direct_demo_cancellation_cannot_mutate_orders(demo_client):
    before = store.get_order('10877')
    ticket = demo_client.post('/tickets', json={'text': 'pls cancel my order 10877, bought the wrong size', 'use_llm': False}).json()
    assert ticket['status'] == 'needs_review'
    assert any(a['tool'] == 'cancel_order' and not a['output']['cancelled'] for a in ticket['actions'])
    assert not tools.cancel_order('10877')['cancelled']
    assert store.get_order('10877') == before


def test_demo_bounds_work_storage_and_query_limit(demo_client, monkeypatch):
    api._demo_requests.extend([time.monotonic()] * 10)
    assert demo_client.post('/tickets', json={'text': 'What payment methods do you accept?'}).status_code == 429
    api._demo_requests.clear()
    monkeypatch.setattr(api, 'DEMO_MAX_TICKETS', 0)
    assert demo_client.post('/tickets', json={'text': 'What payment methods do you accept?'}).status_code == 429
    assert demo_client.get('/tickets?limit=-1').status_code == 422
    assert demo_client.get('/tickets?limit=201').status_code == 422
    monkeypatch.setattr(api, 'DEMO_MAX_TICKETS', 200)
    ticket = demo_client.post('/tickets', json={'text': 'What payment methods do you accept?'}).json()
    monkeypatch.setattr(store, 'DEMO_MAX_FEEDBACK', 0)
    assert demo_client.post(f"/tickets/{ticket['id']}/feedback", json={'rating': 5}).status_code == 409
    assert store.metrics()['feedback_count'] == 0


def test_demo_ignores_private_database_path(tmp_path):
    private = tmp_path / 'private.db'
    env = {**os.environ, 'DEMO_MODE': '1', 'DB_PATH': str(private), 'TMPDIR': str(tmp_path)}
    code = 'import json; from src.config import DB_PATH, DEMO_MODE; print(json.dumps({"db":str(DB_PATH),"demo":DEMO_MODE}))'
    result = subprocess.run([sys.executable, '-c', code], env=env, capture_output=True, text=True, check=True)
    config = json.loads(result.stdout)
    assert config['demo'] and Path(config['db']) != private
    assert 'ticketpilot-public-demo' in config['db']
    assert not private.exists()


def test_demo_rejects_oversized_bodies_before_processing(demo_client):
    before = store.metrics()['tickets']
    response = demo_client.post('/tickets', json={'text': 'x' * 40000})
    assert response.status_code == 413
    assert store.metrics()['tickets'] == before


def test_health_is_not_ready_until_warmup_completes(demo_client, monkeypatch):
    monkeypatch.setattr(api.app.state, 'ready', False)
    assert demo_client.get('/health').status_code == 503


def test_remote_smoke_is_read_only_without_explicit_write_flag(monkeypatch):
    from scripts import deployment_smoke as smoke
    health = {'status': 'ok', 'model_loaded': True, 'order_writes': False, 'demo_mode': True,
              'storage': 'ephemeral', 'llm': False, 'retrieval_backend': 'tfidf(word+char)'}
    monkeypatch.setattr(smoke, 'wait_for', lambda *args: health)
    methods = []
    def read_only(base, path, data=None, method=None, headers=None):
        methods.append(method)
        assert data is None and method == 'OPTIONS'
        origin = headers['Origin']
        return (200, {}, {'Access-Control-Allow-Origin': origin}) if origin == 'http://localhost:3000' else (400, {}, {})
    monkeypatch.setattr(smoke, 'request', read_only)
    results = smoke.verify('https://public-demo.invalid')
    assert any('remote write tests skipped' in r for r in results)
    assert methods == ['OPTIONS', 'OPTIONS']


def test_smoke_refuses_writes_to_non_demo_storage(monkeypatch):
    from scripts import deployment_smoke as smoke
    monkeypatch.setattr(smoke, 'wait_for', lambda *args: {'status': 'ok', 'model_loaded': True, 'order_writes': False, 'demo_mode': False, 'storage': 'local'})
    monkeypatch.setattr(smoke, 'request', lambda *args, **kwargs: pytest.fail('No request after failed storage guard'))
    with pytest.raises(AssertionError, match='never the local/private DB'):
        smoke.verify('http://localhost:8000', allow_remote_writes=True)


def test_remote_full_stack_smoke_sends_no_post_without_write_flag(monkeypatch):
    from scripts import deployment_smoke as smoke
    health = {'status': 'ok', 'model_loaded': True, 'order_writes': False, 'demo_mode': True,
              'storage': 'ephemeral', 'llm': False, 'retrieval_backend': 'tfidf(word+char)'}
    monkeypatch.setattr(smoke, 'wait_for', lambda *args: health)
    observed = []
    def read_only(base, path, data=None, method=None, headers=None):
        observed.append((path, method))
        assert data is None and method in {None, 'GET', 'OPTIONS'}
        if method == 'OPTIONS':
            origin = headers['Origin']
            return (200, {}, {'Access-Control-Allow-Origin': origin}) if origin == 'https://front.invalid' else (400, {}, {})
        if path == '/evaluation':
            return 200, 'Evaluation lab Snapshot v1 Not measured', {}
        return 404, {}, {}
    monkeypatch.setattr(smoke, 'request', read_only)
    result = smoke.verify('https://api.invalid', 'https://front.invalid')
    assert any('remote write tests skipped' in r for r in result)
    assert all(method != 'POST' for _, method in observed)
