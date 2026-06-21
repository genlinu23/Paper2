from __future__ import annotations

import json
import urllib.error

import pytest

from reactor_agent import llm
from reactor_agent.contracts import Fact, PaperFacts


def _valid_payload(doc_id: str = "doc_0001") -> dict:
    fact = Fact(value="structure fact", chunk_id="0001_01", section_title="Results")
    return PaperFacts(
        doc_id=doc_id,
        doi="10.1/example",
        structure=[fact],
        reaction=[Fact(value="reaction fact", chunk_id="0001_01", section_title="Results")],
        membrane=[Fact(value="membrane fact", chunk_id="0001_01", section_title="Results")],
        feed=[Fact(value="feed fact", chunk_id="0001_01", section_title="Results")],
        performance=[Fact(value="performance fact", chunk_id="0001_01", section_title="Results")],
        failure=[Fact(value="failure fact", chunk_id="0001_01", section_title="Results")],
    ).model_dump(mode="json")


class FakeResponse:
    def __init__(self, payload: dict):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self):
        return json.dumps(self.payload).encode("utf-8")


def test_call_requires_api_key(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("VECTORENGINE_API_KEY", raising=False)
    with pytest.raises(llm.LLMStructuredError, match="VECTORENGINE_API_KEY"):
        llm.call("literature", "system", "user", PaperFacts)


def test_endpoint_from_base_url():
    assert llm._endpoint_from_base_url("https://api.vectorengine.cn") == "https://api.vectorengine.cn/v1/chat/completions"
    assert llm._endpoint_from_base_url("https://api.vectorengine.cn/v1") == "https://api.vectorengine.cn/v1/chat/completions"
    assert (
        llm._endpoint_from_base_url("https://api.vectorengine.cn/v1/chat/completions")
        == "https://api.vectorengine.cn/v1/chat/completions"
    )


def test_call_uses_single_base_url(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("VECTORENGINE_API_KEY", "test-key")
    monkeypatch.setenv("VECTORENGINE_BASE_URL", "https://api.vectorengine.cn/v1")
    urls = []

    def fake_urlopen(req, timeout):
        urls.append(req.full_url)
        return FakeResponse({"choices": [{"message": {"content": json.dumps(_valid_payload())}}]})

    monkeypatch.setattr(llm.urllib.request, "urlopen", fake_urlopen)
    result = llm.call("literature", "system", "user", PaperFacts)
    assert result.doc_id == "doc_0001"
    assert urls == ["https://api.vectorengine.cn/v1/chat/completions"]
