"""HTTP deployment smoke tests. --local uses disposable servers/data; no remote deployment.

Remote runs are read-only unless --allow-remote-writes is explicitly supplied.
Even then, writes require a backend advertising DEMO_MODE and ephemeral storage.
"""
import argparse
import json
import os
from pathlib import Path
import signal
import socket
import subprocess
import sys
import tempfile
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]


def request(base, path, data=None, method=None, headers=None):
    req = Request(base.rstrip('/') + path,
                  data=json.dumps(data).encode() if data is not None else None,
                  method=method, headers={'Content-Type': 'application/json', **(headers or {})})
    try:
        response = urlopen(req, timeout=15)
    except HTTPError as exc:
        response = exc
    with response:
        text = response.read().decode()
        try:
            body = json.loads(text)
        except ValueError:
            body = text
        return response.status, body, response.headers


def wait_for(base, path, timeout=120):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            status, data, _ = request(base, path)
            if status == 200:
                return data
        except (OSError, URLError):
            pass
        time.sleep(1)
    raise RuntimeError(f'Timed out waiting for {base}{path}')


def local_url(url):
    return urlsplit(url).hostname in {'127.0.0.1', 'localhost', '::1'}


def verify(backend, frontend=None, allow_remote_writes=False):
    health = wait_for(backend, '/health')
    assert isinstance(health, dict) and health.get('status') == 'ok', health
    assert health.get('model_loaded') and not health.get('order_writes'), health
    assert health.get('demo_mode') and health.get('storage') == 'ephemeral', 'Smoke writes require an isolated public demo, never the local/private DB'
    assert not health.get('llm') and 'tfidf' in health.get('retrieval_backend', ''), health
    checks = ['backend readiness/model/free retrieval/ephemeral policy']
    origin = frontend or 'http://localhost:3000'
    status, _, headers = request(backend, '/tickets', method='OPTIONS', headers={
        'Origin': origin, 'Access-Control-Request-Method': 'POST', 'Access-Control-Request-Headers': 'content-type'})
    assert status == 200 and headers.get('Access-Control-Allow-Origin') == origin, 'Configure this exact frontend origin in CORS_ORIGINS'
    status, _, headers = request(backend, '/tickets', method='OPTIONS', headers={
        'Origin': 'https://not-permitted.invalid', 'Access-Control-Request-Method': 'POST'})
    assert status == 400 and not headers.get('Access-Control-Allow-Origin')
    checks.append('explicit CORS allow/deny')
    if frontend:
        proxied = wait_for(frontend, '/api/backend/health')
        assert proxied.get('status') == 'ok' and proxied.get('demo_mode'), proxied
        status, html, _ = request(frontend, '/evaluation')
        assert status == 200 and 'Evaluation lab' in html and 'Snapshot v' in html and 'Not measured' in html
        status, _, _ = request(frontend, '/api/backend/orders/10877')
        assert status == 404
        checks += ['frontend same-origin proxy connectivity', 'bundled evaluation snapshot', 'proxy endpoint allowlist']
    if not (local_url(backend) and (not frontend or local_url(frontend))) and not allow_remote_writes:
        return checks + ['remote write tests skipped (explicit --allow-remote-writes required)']
    target = frontend.rstrip('/') + '/api/backend' if frontend else backend
    status, ticket, _ = request(target, '/tickets', {'text': 'Where is my order 10233?', 'use_llm': False})
    assert status == 200 and ticket.get('id') and ticket['agent'] == 'fallback', ticket
    metadata = ticket['decision_metadata']
    assert metadata['version'] == 1 and len(metadata['retrieval']['hits']) == 3
    status, stored, _ = request(target, f"/tickets/{ticket['id']}")
    assert status == 200 and stored['decision_metadata'] == metadata
    for data in ({'approved': True}, {'approved': False}, {'corrected_intent': 'complaint'}):
        status, _, _ = request(target, f"/tickets/{ticket['id']}/feedback", data,
                               headers={'Authorization': 'Bearer deployment-smoke-test-token'})
        assert status == 403
    assert request(target, '/tickets', {'text': 'Fictional demo request', 'use_llm': True})[0] == 403
    cancel = request(target, '/tickets', {'text': 'pls cancel my order 10877, bought the wrong size', 'use_llm': False})
    assert cancel[0] == 200 and cancel[1]['status'] == 'needs_review', cancel
    events = [a for a in cancel[1]['actions'] if a['tool'] == 'cancel_order']
    assert events and all(a['output']['cancelled'] is False for a in events)
    assert request(target, '/tickets', {'text': 'x' * 40000})[0] == 413
    checks += ['public request body size limit', 'safe real ticket processing + persisted decision evidence',
               'approval/correction denial, including supplied reviewer token',
               'paid LLM denial', 'blocked order cancellation']
    return checks


def free_port():
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        return sock.getsockname()[1]


def run_local(backend_only=False):
    processes = []
    with tempfile.TemporaryDirectory(prefix='ticketpilot-deployment-smoke-') as folder:
        backend_port, frontend_port = free_port(), free_port()
        backend = f'http://127.0.0.1:{backend_port}'
        frontend = None if backend_only else f'http://127.0.0.1:{frontend_port}'
        env = {**os.environ, 'DEMO_MODE': '1', 'RETRIEVAL_BACKEND': 'tfidf', 'TMPDIR': folder,
               'PORT': str(backend_port), 'CORS_ORIGINS': frontend or 'http://localhost:3000',
               'TICKETPILOT_REVIEWER_TOKEN': 'deployment-smoke-test-token',
               'TICKETPILOT_API_URL': backend, 'HF_HUB_OFFLINE': '1', 'TRANSFORMERS_OFFLINE': '1',
               'PATH': str(Path(sys.executable).parent) + os.pathsep + os.environ['PATH']}
        env.pop('VERCEL', None)
        env.pop('ANTHROPIC_API_KEY', None)
        logs = Path(folder) / 'servers.log'
        with logs.open('w+') as log:
            try:
                processes.append(subprocess.Popen(['sh', 'scripts/start_render.sh'], cwd=ROOT, env=env,
                                                  stdout=log, stderr=log, start_new_session=True))
                if frontend:
                    if not (ROOT / 'frontend/.next/BUILD_ID').exists():
                        raise RuntimeError('Build frontend first: cd frontend && npm run build')
                    import shutil
                    node = shutil.which('node')
                    processes.append(subprocess.Popen([node, 'node_modules/next/dist/bin/next', 'start',
                                                       '--hostname', '127.0.0.1', '--port', str(frontend_port)],
                                                      cwd=ROOT / 'frontend', env=env, stdout=log, stderr=log,
                                                      start_new_session=True))
                results = verify(backend, frontend)
                if frontend:
                    # Exercise Vercel-specific failure modes locally; no Vercel API/CLI is invoked.
                    for upstream, label in [("", "missing Vercel upstream fails closed"),
                                            (backend, "insecure Vercel upstream fails closed")]:
                        config_port = free_port()
                        config_url = f'http://127.0.0.1:{config_port}'
                        config_env = {**env, 'VERCEL': '1', 'TICKETPILOT_API_URL': upstream}
                        processes.append(subprocess.Popen([node, 'node_modules/next/dist/bin/next', 'start',
                                                           '--hostname', '127.0.0.1', '--port', str(config_port)],
                                                          cwd=ROOT / 'frontend', env=config_env,
                                                          stdout=log, stderr=log, start_new_session=True))
                        wait_for(config_url, '/evaluation')
                        assert request(config_url, '/api/backend/health')[0] == 503
                        results.append(label)
                for result in results:
                    print('PASS: ' + result)
                print(f'Deployment smoke: {len(results)} checks passed (disposable local data)')
            except Exception:
                log.flush(); log.seek(0)
                print(log.read()[-6000:], file=sys.stderr)
                raise
            finally:
                for process in reversed(processes):
                    if process.poll() is None:
                        os.killpg(process.pid, signal.SIGTERM)
                        try:
                            process.wait(timeout=10)
                        except subprocess.TimeoutExpired:
                            os.killpg(process.pid, signal.SIGKILL)
                            process.wait()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--local', action='store_true')
    parser.add_argument('--backend-only', action='store_true')
    parser.add_argument('--backend-url')
    parser.add_argument('--frontend-url')
    parser.add_argument('--allow-remote-writes', action='store_true')
    args = parser.parse_args()
    if args.local:
        if args.backend_url or args.frontend_url or args.allow_remote_writes:
            parser.error('--local cannot be combined with remote URLs/write approval')
        run_local(args.backend_only)
    elif args.backend_url and (args.frontend_url or args.backend_only):
        for result in verify(args.backend_url, args.frontend_url, args.allow_remote_writes):
            print('PASS: ' + result)
    else:
        parser.error('Use --local, or explicit --backend-url plus --frontend-url/--backend-only')


if __name__ == '__main__':
    main()
