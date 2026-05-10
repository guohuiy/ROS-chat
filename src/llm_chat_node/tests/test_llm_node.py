import time
import json
import types
import pytest

from std_msgs.msg import String
from llm_chat_node.__init__ import LLMChatNode


class DummyPub:
    def __init__(self):
        self.published = []

    def publish(self, msg):
        self.published.append(msg.data)


class DummyLogger:
    def info(self, *args, **kwargs):
        pass

    def debug(self, *args, **kwargs):
        pass

    def error(self, *args, **kwargs):
        pass


def make_node_stub():
    # Create instance without running __init__
    node = object.__new__(LLMChatNode)

    # Basic parameters used by handle_input
    node.min_input_length = 1
    node.max_input_length = 2000
    node.request_cooldown_seconds = 0.0
    node.requests_per_minute = 5
    node._client_requests = {}
    node._last_request_time = 0.0

    node.system_prompt = 'System'
    node.enable_vision = False
    node.vision_auto_context = False
    node.latest_detection_text = 'No visual'
    node.enable_history = True
    node.conversation_history = []
    node.history_window = 10

    node.model = 'test-model'
    node.ollama_url = 'http://localhost'
    node.max_tokens = 64
    node.temperature = 0.7
    node.timeout = 5

    node.stream_output = False
    node.max_response_chars = 10000

    node.pub = DummyPub()
    node.stream_pub = DummyPub()
    node.history_pub = DummyPub()

    node.get_logger = lambda: DummyLogger()

    # default implementations to be replaced by tests as needed
    node._call_ollama_with_retry = lambda payload: {'response': 'ok'}
    node._call_ollama_stream = lambda payload: 'stream-ok'

    return node


def make_msg(s):
    m = String()
    m.data = s
    return m


def test_input_too_short():
    node = make_node_stub()
    node.min_input_length = 5

    node.handle_input(make_msg('hi'))
    assert any('Error: input too short' in p for p in node.pub.published)


def test_input_too_long():
    node = make_node_stub()
    node.max_input_length = 5
    node.handle_input(make_msg('this is long'))
    assert any('Error: input too long' in p for p in node.pub.published)


def test_global_cooldown():
    node = make_node_stub()
    node.request_cooldown_seconds = 10.0
    node._last_request_time = time.time()
    node.handle_input(make_msg('hello world'))
    assert any('Error: requests are too frequent' in p for p in node.pub.published)


def test_per_client_rate_limit():
    node = make_node_stub()
    now = time.time()
    node.requests_per_minute = 1
    node._client_requests['client1'] = [now]
    node.handle_input(make_msg(json.dumps({'client_id': 'client1', 'text': 'hello'})))
    assert any('Error: client rate limit exceeded' in p for p in node.pub.published)


def test_successful_response_and_history():
    node = make_node_stub()

    def fake_call(payload):
        return {'response': 'Hello from model'}

    node._call_ollama_with_retry = fake_call
    node.stream_output = False

    node.handle_input(make_msg('tell me a joke'))

    # last published should include full response
    assert any('Hello from model' in p for p in node.pub.published)
    # history published as JSON
    assert len(node.history_pub.published) >= 1
    hist = json.loads(node.history_pub.published[-1])
    assert isinstance(hist, list)
