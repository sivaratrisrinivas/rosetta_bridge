from __future__ import annotations

from google import genai

from rosetta_bridge.core.config import Settings


class GeminiClient:
    def __init__(self, model_name: str = "gemini-3-flash-preview") -> None:
        settings = Settings()
        api_key = settings.gemini_api_key
        self._client = genai.Client(api_key=api_key)
        self._model_name = model_name

    def generate_description(self, table_context: str) -> str:
        response = self._client.models.generate_content(
            model=self._model_name,
            contents=table_context,
        )
        return response.text
