"""
Swappable LLM client.

Set LLM_PROVIDER in your .env:
  LLM_PROVIDER=ollama          # default — local model via Ollama
  LLM_PROVIDER=openai          # OpenAI API
  LLM_PROVIDER=anthropic       # Anthropic Claude API

Provider-specific settings (also in .env):

  Ollama:
    OLLAMA_BASE_URL=http://localhost:11434   (default)
    OLLAMA_MODEL=llama3                     (default)

  OpenAI:
    OPENAI_API_KEY=sk-...
    OPENAI_MODEL=gpt-4o                     (default)

  Anthropic:
    ANTHROPIC_API_KEY=sk-ant-...
    ANTHROPIC_MODEL=claude-3-5-sonnet-20241022  (default)
"""
from __future__ import annotations

import os
from abc import ABC, abstractmethod
from typing import Iterator


# ---------------------------------------------------------------------------
# Base
# ---------------------------------------------------------------------------

class LLMClient(ABC):
    """Minimal interface all providers must implement."""

    @abstractmethod
    def chat(self, messages: list[dict], *, stream: bool = False) -> str | Iterator[str]:
        """
        Send a list of {"role": ..., "content": ...} messages.
        Returns the full response string, or a string iterator if stream=True.
        """
        ...

    @abstractmethod
    def model_name(self) -> str:
        """Human-readable identifier for the model in use."""
        ...


# ---------------------------------------------------------------------------
# Ollama (local)
# ---------------------------------------------------------------------------

class OllamaClient(LLMClient):
    def __init__(
        self,
        base_url: str | None = None,
        model: str | None = None,
    ):
        self._base_url = (base_url or os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")).rstrip("/")
        self._model    = model or os.getenv("OLLAMA_MODEL", "llama3")

    def model_name(self) -> str:
        return f"ollama/{self._model}"

    def chat(self, messages: list[dict], *, stream: bool = False) -> str | Iterator[str]:
        import requests  # already in requirements.txt

        url  = f"{self._base_url}/api/chat"
        body = {"model": self._model, "messages": messages, "stream": stream}

        if not stream:
            resp = requests.post(url, json=body, timeout=300)
            resp.raise_for_status()
            return resp.json()["message"]["content"]

        # Streaming
        def _iter():
            with requests.post(url, json=body, stream=True, timeout=300) as r:
                r.raise_for_status()
                import json
                for line in r.iter_lines():
                    if line:
                        chunk = json.loads(line)
                        yield chunk.get("message", {}).get("content", "")
                        if chunk.get("done"):
                            break

        return _iter()


# ---------------------------------------------------------------------------
# OpenAI
# ---------------------------------------------------------------------------

class OpenAIClient(LLMClient):
    def __init__(self, api_key: str | None = None, model: str | None = None):
        self._model   = model or os.getenv("OPENAI_MODEL", "gpt-4o")
        self._api_key = api_key or os.getenv("OPENAI_API_KEY", "")

    def model_name(self) -> str:
        return f"openai/{self._model}"

    def chat(self, messages: list[dict], *, stream: bool = False) -> str | Iterator[str]:
        from openai import OpenAI  # pip install openai

        client = OpenAI(api_key=self._api_key)

        if not stream:
            resp = client.chat.completions.create(
                model=self._model,
                messages=messages,
            )
            return resp.choices[0].message.content or ""

        def _iter():
            with client.chat.completions.create(
                model=self._model,
                messages=messages,
                stream=True,
            ) as stream_resp:
                for chunk in stream_resp:
                    delta = chunk.choices[0].delta.content
                    if delta:
                        yield delta

        return _iter()


# ---------------------------------------------------------------------------
# Anthropic
# ---------------------------------------------------------------------------

class AnthropicClient(LLMClient):
    def __init__(self, api_key: str | None = None, model: str | None = None):
        self._model   = model or os.getenv("ANTHROPIC_MODEL", "claude-3-5-sonnet-20241022")
        self._api_key = api_key or os.getenv("ANTHROPIC_API_KEY", "")

    def model_name(self) -> str:
        return f"anthropic/{self._model}"

    def chat(self, messages: list[dict], *, stream: bool = False) -> str | Iterator[str]:
        import anthropic  # pip install anthropic

        client = anthropic.Anthropic(api_key=self._api_key)

        # Anthropic separates system prompt from user/assistant turns
        system = ""
        turns  = []
        for m in messages:
            if m["role"] == "system":
                system = m["content"]
            else:
                turns.append(m)

        if not stream:
            resp = client.messages.create(
                model=self._model,
                max_tokens=1024,
                system=system,
                messages=turns,
            )
            return resp.content[0].text

        def _iter():
            with client.messages.stream(
                model=self._model,
                max_tokens=1024,
                system=system,
                messages=turns,
            ) as s:
                for text in s.text_stream:
                    yield text

        return _iter()


# ---------------------------------------------------------------------------
# Factory — reads LLM_PROVIDER from environment
# ---------------------------------------------------------------------------

def get_client(provider: str | None = None) -> LLMClient:
    """
    Return the right LLMClient based on LLM_PROVIDER env var.
    Defaults to Ollama if not set.

    Usage:
        client = get_client()
        answer = client.chat(messages)
    """
    p = (provider or os.getenv("LLM_PROVIDER", "ollama")).lower().strip()

    if p == "openai":
        return OpenAIClient()
    if p in ("anthropic", "claude"):
        return AnthropicClient()
    if p == "ollama":
        return OllamaClient()

    raise ValueError(
        f"Unknown LLM_PROVIDER '{p}'. "
        "Valid options: ollama, openai, anthropic"
    )
