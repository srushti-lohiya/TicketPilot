"""HTTP permission checks use only a disposable DB, local models, and free retrieval."""
import pytest
from fastapi.testclient import TestClient
from src.api import app
from src import store

@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def test_public_mode_and_paid_model_denial(client):
    assert client.get('/health').json()['order_writes'] is False
    assert client.post('/tickets', json={'text': 'hello', 'use_llm': True}).status_code == 403


def test_approval_requires_reviewer_and_is_atomic(client, monkeypatch):
    monkeypatch.setenv('TICKETPILOT_REVIEWER_TOKEN', 'reviewer-test-secret')
    tid = client.post('/tickets', json={'text': 'Where is my order 10233?', 'use_llm': False}).json()['id']
    for headers in ({}, {'Authorization': 'Bearer wrong'}):
        assert client.post(f'/tickets/{tid}/feedback', json={'approved': True}, headers=headers).status_code == 403
        assert client.post(f'/tickets/{tid}/feedback', json={'corrected_intent': 'complaint'}, headers=headers).status_code == 403
    headers = {'Authorization': 'Bearer reviewer-test-secret'}
    assert client.post(f'/tickets/{tid}/feedback', json={'approved': True}, headers=headers).status_code == 200
    count = store.metrics()['feedback_count']
    assert client.post(f'/tickets/{tid}/feedback', json={'approved': True}, headers=headers).status_code == 409
    assert store.metrics()['feedback_count'] == count


@pytest.mark.parametrize('updates', [
    {'actions': [{'tool': 'cancel_order', 'input': {}, 'output': {}}]}, {'status': 'escalated'}, {'status': 'resolved'}, {'priority': 'P1'},
    {'priority': 'P2'}, {'intent': 'cancel_order'}, {'intent': 'get_refund'}, {'guardrail_issues': ['no citation']}, {'risk_reasons': ['security']},
])
def test_reviewer_cannot_approve_restricted_ticket(client, monkeypatch, updates):
    monkeypatch.setenv('TICKETPILOT_REVIEWER_TOKEN', 'reviewer-test-secret')
    row = client.post('/tickets', json={'text': 'Where is my order 10233?', 'use_llm': False}).json()
    row.pop('id'); row.update(updates)
    tid = store.save_ticket(row)
    assert client.post(f'/tickets/{tid}/feedback', json={'approved': True}, headers={
        'Authorization': 'Bearer reviewer-test-secret'}).status_code == 409
    assert store.get_ticket(tid)['status'] == row['status']
    assert client.post(f'/tickets/{tid}/feedback', json={'rating': 4, 'comment': 'reviewed'}).status_code == 200


def test_missing_reviewer_configuration_fails_closed(client, monkeypatch):
    monkeypatch.delenv('TICKETPILOT_REVIEWER_TOKEN', raising=False)
    assert client.post('/tickets/1/feedback', json={'approved': False}, headers={
        'Authorization': 'Bearer anything'}).status_code == 403
