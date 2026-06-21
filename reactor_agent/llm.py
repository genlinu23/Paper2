from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import TypeVar

from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


class LLMStructuredError(RuntimeError):
    pass


ROLE_MODELS = {
    "literature": "gpt-4.1-mini",
    "kg": "gpt-4.1-mini",
    "reasoning": "gpt-5.4",
    "diagnosis": "gpt-5.4",
    "vision": "gpt-4o",
}

DEFAULT_BASE_URL = "https://api.vectorengine.cn/v1"


def _endpoint_from_base_url(base_url: str) -> str:
    base = base_url.rstrip("/")
    if base.endswith("/chat/completions"):
        return base
    if base.endswith("/v1"):
        return f"{base}/chat/completions"
    return f"{base}/v1/chat/completions"


def _base_url_from_env() -> str:
    base_url = os.environ.get("VECTORENGINE_BASE_URL", DEFAULT_BASE_URL).strip()
    if not base_url:
        raise LLMStructuredError("VECTORENGINE_BASE_URL is empty.")
    return base_url


def _model_for_role(role: str) -> str:
    env_key = f"VECTORENGINE_MODEL_{role.upper()}"
    if os.environ.get(env_key):
        return os.environ[env_key]
    if role not in ROLE_MODELS:
        raise LLMStructuredError(f"No model configured for role={role!r}.")
    return ROLE_MODELS[role]


def _extract_message_json(payload: dict) -> dict:
    choices = payload.get("choices")
    if not isinstance(choices, list) or not choices:
        raise LLMStructuredError("LLM response missing choices.")
    message = choices[0].get("message")
    if not isinstance(message, dict):
        raise LLMStructuredError("LLM response missing message.")
    content = message.get("content")
    if not isinstance(content, str) or not content.strip():
        raise LLMStructuredError("LLM response message.content is empty.")
    try:
        parsed = json.loads(content)
    except json.JSONDecodeError as exc:
        raise LLMStructuredError(f"LLM response is not valid JSON: {exc}") from exc
    if not isinstance(parsed, dict):
        raise LLMStructuredError("LLM response JSON must be an object.")
    return parsed


def call(role: str, system: str, user: str, schema: type[T], images: list[str] | None = None) -> T:
    if images:
        raise LLMStructuredError("Image inputs are not wired for this text-only LLM call.")

    api_key = os.environ.get("VECTORENGINE_API_KEY")
    if not api_key:
        raise LLMStructuredError("VECTORENGINE_API_KEY is required.")

    model = _model_for_role(role)
    request_body = {
        "model": model,
        "temperature": 0.1 if role in {"literature", "kg"} else 0.2,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "response_format": {
            "type": "json_schema",
            "json_schema": {
                "name": schema.__name__,
                "schema": schema.model_json_schema(),
                "strict": True,
            },
        },
    }
    data = json.dumps(request_body, ensure_ascii=False).encode("utf-8")
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    endpoint = _endpoint_from_base_url(_base_url_from_env())
    req = urllib.request.Request(endpoint, data=data, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=120) as response:
            response_data = response.read().decode("utf-8")
        raw = json.loads(response_data)
        parsed = _extract_message_json(raw)
        return schema.model_validate(parsed)
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise LLMStructuredError(f"{endpoint}: HTTP {exc.code}: {body[:500]}") from exc
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, LLMStructuredError, ValueError) as exc:
        raise LLMStructuredError(f"{endpoint}: {exc}") from exc
