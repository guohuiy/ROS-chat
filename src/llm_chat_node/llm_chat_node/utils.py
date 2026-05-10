"""Utility helpers extracted from LLMChatNode for easier testing.
"""
from typing import List, Dict
import time
import requests
import uuid


def build_full_prompt(system_prompt: str, vision_auto_context: bool, vision_context_prompt: str,
                      latest_detection_text: str, enable_history: bool, conversation_history: List[Dict], user_prompt: str) -> str:
    parts = []
    parts.append(system_prompt or '')

    if vision_auto_context and vision_context_prompt:
        vision_context = vision_context_prompt.format(detection_text=latest_detection_text)
        parts.append(vision_context)

    if enable_history and conversation_history:
        lines = ["Previous conversation:"]
        for turn in conversation_history:
            prefix = "User" if turn.get("role") == "user" else "Assistant"
            lines.append(f"{prefix}: {turn.get('content', '')}")
        parts.append("\n".join(lines))

    parts.append(f"User: {user_prompt}")
    parts.append("Assistant:")

    return "\n\n".join([p for p in parts if p is not None])


def trim_history(conversation_history: List[Dict], history_window: int) -> List[Dict]:
    # keep last history_window * 2 entries (user+assistant pairs)
    max_len = history_window * 2
    if len(conversation_history) <= max_len:
        return conversation_history
    return conversation_history[-max_len:]


def call_ollama_with_retry(ollama_url: str, payload: dict, max_retries: int = 3, retry_base_delay: float = 1.0, timeout: int = 30):
    request_id = uuid.uuid4().hex[:8]
    last_error = None
    for attempt in range(max_retries):
        try:
            resp = requests.post(f"{ollama_url}/api/generate", json=payload, timeout=(5, timeout))
            resp.raise_for_status()
            return resp.json()
        except (requests.ConnectionError, requests.Timeout) as e:
            last_error = e
            if attempt < max_retries - 1:
                wait = retry_base_delay * (2 ** attempt)
                time.sleep(wait)
            else:
                raise
        except Exception as e:
            last_error = e
            raise
    raise last_error
