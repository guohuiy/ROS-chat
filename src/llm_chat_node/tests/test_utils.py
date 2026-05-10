import pytest
import requests
from unittest.mock import Mock
from llm_chat_node.utils import build_full_prompt, trim_history, call_ollama_with_retry


def test_build_full_prompt_no_history():
    system = 'System prompt.'
    prompt = build_full_prompt(system, True, '[Visual]\n{detection_text}', 'No objects', False, [], 'Hello')
    assert 'System prompt.' in prompt
    assert 'User: Hello' in prompt


def test_trim_history():
    hist = [{'role': 'user', 'content': 'u1'}, {'role': 'assistant', 'content': 'a1'}, {'role': 'user', 'content': 'u2'}, {'role': 'assistant', 'content': 'a2'}]
    trimmed = trim_history(hist, 1)
    assert len(trimmed) == 2


class DummyResp:
    def __init__(self, json_data=None, raise_exc=False):
        self._json = json_data or {"response": "ok"}
        self._raise = raise_exc

    def raise_for_status(self):
        if self._raise:
            raise requests.HTTPError('err')

    def json(self):
        return self._json


def test_call_ollama_with_retry_success(monkeypatch):
    calls = []

    def fake_post(url, json, timeout):
        calls.append(1)
        return DummyResp({"response": "hello"})

    monkeypatch.setattr('requests.post', fake_post)
    res = call_ollama_with_retry('http://localhost:11434', {'model': 'm'}, max_retries=2, retry_base_delay=0.1, timeout=5)
    assert res.get('response') == 'hello'
    assert len(calls) == 1


def test_call_ollama_with_retry_retry(monkeypatch):
    seq = {'count': 0}

    def fake_post(url, json, timeout):
        seq['count'] += 1
        if seq['count'] == 1:
            raise requests.ConnectionError('conn')
        return DummyResp({"response": "ok"})

    monkeypatch.setattr('requests.post', fake_post)
    res = call_ollama_with_retry('http://localhost:11434', {'model': 'm'}, max_retries=3, retry_base_delay=0.01, timeout=5)
    assert res.get('response') == 'ok'
    assert seq['count'] == 2

*** End Patch