import sys
import types
import pytest
from llm_chat_node.detectors import try_init_onnxruntime_session


def test_try_init_onnxruntime_session_missing(monkeypatch):
    # Simulate ImportError
    monkeypatch.setitem(sys.modules, 'onnxruntime', None)
    with pytest.raises(Exception):
        try_init_onnxruntime_session('nonexistent.onnx')


def test_try_init_onnxruntime_session_fake(monkeypatch, tmp_path):
    # Provide a fake onnxruntime module with InferenceSession returning an object
    fake_ort = types.SimpleNamespace()

    class FakeSession:
        def __init__(self, model_path, providers):
            self.model_path = model_path
            self.providers = providers

    fake_ort.InferenceSession = FakeSession
    monkeypatch.setitem(sys.modules, 'onnxruntime', fake_ort)

    # create dummy file
    p = tmp_path / 'm.onnx'
    p.write_text('0')

    sess = try_init_onnxruntime_session(str(p))
    assert hasattr(sess, 'model_path')

*** End Patch