from __future__ import annotations

import pytest

from rosetta_bridge.inference.client import GeminiClient


def test_generate_description_returns_text(monkeypatch: pytest.MonkeyPatch) -> None:
    class DummyResponse:
        def __init__(self, text: str):
            self.text = text

    class DummyModels:
        def generate_content(self, model: str, contents: str):
            assert model == "gemini-3-flash-preview"
            assert "hello" in contents
            return DummyResponse("ok")

    class DummyClient:
        def __init__(self, api_key: str | None = None):
            self.api_key = api_key
            self.models = DummyModels()

    monkeypatch.setattr("rosetta_bridge.inference.client.genai.Client", DummyClient)

    client = GeminiClient()
    result = client.generate_description("hello world")

    assert result == "ok"
