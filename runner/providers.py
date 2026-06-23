"""
cf-modeleval-v1 — provider adapter layer.

Unifies Anthropic / OpenAI / Groq behind a single `LLMClient` interface so the
runner is provider-agnostic. The judge (scorer Stage 2) is held constant on
Anthropic Claude Haiku 4.5 across all target providers — varying the judge would
confound the planted-twin Δ measurement.

Each adapter exposes the v0-compatible surface the existing runner expects:

    client.messages.create(
        model=...,
        max_tokens=...,
        system=...,
        messages=[{"role": "user", "content": "..."}],
    )
    -> response, where response.content[0].text is the completion text.

This shim keeps the legacy v0 runner code intact while making OpenAI + Groq
work uniformly. The adapter does NOT use streaming, tool use, or vision.
"""

import os
from dataclasses import dataclass
from typing import Any, List, Dict


# ── unified return type ─────────────────────────────────────────────────────


@dataclass
class _Block:
    text: str


@dataclass
class _Response:
    content: List[_Block]


# ── Anthropic adapter (passes through; matches the v0 native client) ────────


class AnthropicClient:
    """
    Thin wrapper around anthropic.Anthropic — keeps the v0 native client surface.

    The judge re-uses this same client when target_provider == 'anthropic'.
    """

    provider = "anthropic"

    def __init__(self, api_key: str | None = None):
        import anthropic
        self._client = anthropic.Anthropic(api_key=api_key or os.environ.get("ANTHROPIC_API_KEY", ""))
        self._model: str = ""  # set by the runner
        self.messages = self  # so client.messages.create(...) routes to .create

    def create(self, *, model: str, max_tokens: int, messages: List[Dict[str, str]], system: str | None = None) -> _Response:
        # system is optional: the scorer's Stage 2 judge does not pass one.
        kwargs = {"model": model, "max_tokens": max_tokens, "messages": messages}
        if system is not None:
            kwargs["system"] = system
        resp = self._client.messages.create(**kwargs)
        return _Response(content=[_Block(text=resp.content[0].text)])


# ── OpenAI adapter (Chat Completions) ───────────────────────────────────────


class OpenAIClient:
    """
    Adapter around openai.OpenAI Chat Completions, surface-compatible with the
    v0 Anthropic-style call signature. system is optional (judge calls omit it).
    """

    provider = "openai"

    def __init__(self, api_key: str | None = None):
        from openai import OpenAI
        self._client = OpenAI(api_key=api_key or os.environ.get("OPENAI_API_KEY", ""))
        self._model: str = ""
        self.messages = self

    def create(self, *, model: str, max_tokens: int, messages: List[Dict[str, str]], system: str | None = None) -> _Response:
        oai_messages: List[Dict[str, str]] = []
        if system is not None:
            oai_messages.append({"role": "system", "content": system})
        oai_messages.extend(messages)
        resp = self._client.chat.completions.create(
            model=model,
            max_tokens=max_tokens,
            messages=oai_messages,
        )
        text = resp.choices[0].message.content or ""
        return _Response(content=[_Block(text=text)])


# ── Groq adapter (OpenAI-compatible chat completions) ───────────────────────


class GroqClient:
    """
    Adapter around groq.Groq Chat Completions. Same surface as OpenAIClient.
    Tested against llama-3.3-70b-versatile + llama-3.1-8b-instant.
    """

    provider = "groq"

    def __init__(self, api_key: str | None = None):
        from groq import Groq
        self._client = Groq(api_key=api_key or os.environ.get("GROQ_API_KEY", ""))
        self._model: str = ""
        self.messages = self

    def create(self, *, model: str, max_tokens: int, messages: List[Dict[str, str]], system: str | None = None) -> _Response:
        groq_messages: List[Dict[str, str]] = []
        if system is not None:
            groq_messages.append({"role": "system", "content": system})
        groq_messages.extend(messages)
        resp = self._client.chat.completions.create(
            model=model,
            max_tokens=max_tokens,
            messages=groq_messages,
        )
        text = resp.choices[0].message.content or ""
        return _Response(content=[_Block(text=text)])


# ── Factory ─────────────────────────────────────────────────────────────────


PROVIDERS = {
    "anthropic": AnthropicClient,
    "openai": OpenAIClient,
    "groq": GroqClient,
}


# Default judge model per Stage 2 of the scorer. Held constant across all
# target providers — varying the judge across legs would confound discrimination Δ.
JUDGE_PROVIDER = "anthropic"
JUDGE_MODEL = "claude-haiku-4-5"


def make_target_client(provider: str) -> Any:
    """Return a v0-runner-compatible client for the target provider."""
    if provider not in PROVIDERS:
        raise ValueError(f"unknown provider {provider!r}; expected one of {sorted(PROVIDERS)}")
    return PROVIDERS[provider]()


def make_judge_client() -> Any:
    """Return the judge client (always Anthropic per JUDGE_PROVIDER)."""
    return PROVIDERS[JUDGE_PROVIDER]()


# Per-provider default model IDs used in CI matrix + run_live.sh.
# Picked to fit the ≤$50 spend envelope per the A2 dispatch.
DEFAULT_MODELS = {
    "anthropic": ["claude-sonnet-4-6", "claude-haiku-4-5"],
    "openai": ["gpt-4o-mini"],
    # llama-3.3-70b-versatile = current production model on Groq's free tier as of 2025–26.
    "groq": ["llama-3.3-70b-versatile"],
}
