"""Serviço de integração com LLM (OpenRouter, Gemini ou OpenAI)."""

import json
import re
from urllib import request as url_request

from openai import OpenAI

from app.config import settings

_client: OpenAI | None = None

GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"


def _get_client() -> OpenAI | None:
    """Retorna o cliente OpenAI (ou OpenRouter, que é compatível) se a chave estiver configurada."""
    global _client
    if settings.ai_provider == "openrouter" and settings.openrouter_api_key and _client is None:
        _client = OpenAI(
            api_key=settings.openrouter_api_key,
            base_url=settings.openrouter_base_url,
        )
    elif settings.ai_provider == "openai" and settings.openai_api_key and _client is None:
        _client = OpenAI(api_key=settings.openai_api_key)
    return _client


def _has_llm() -> bool:
    """Retorna True se algum provedor de IA estiver configurado."""
    if settings.ai_provider == "gemini":
        return bool(settings.gemini_api_key)
    if settings.ai_provider == "openrouter":
        return bool(settings.openrouter_api_key)
    return bool(settings.openai_api_key)


def _gemini_response(messages: list[dict[str, str]], system_prompt: str | None = None) -> str | None:
    """Gera uma resposta usando o Google Gemini via API REST."""
    if not settings.gemini_api_key:
        return None
    try:
        contents = []
        for m in messages:
            role = "model" if m["role"] == "assistant" else "user"
            contents.append({"role": role, "parts": [{"text": m["content"]}]})

        payload: dict = {"contents": contents}
        if system_prompt:
            payload["systemInstruction"] = {"parts": [{"text": system_prompt}]}
        payload["generationConfig"] = {"maxOutputTokens": 300}

        url = GEMINI_URL.format(model=settings.gemini_model)
        req = url_request.Request(
            f"{url}?key={settings.gemini_api_key}",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with url_request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))

        candidates = data.get("candidates") or []
        if candidates:
            parts = candidates[0].get("content", {}).get("parts") or []
            if parts:
                return parts[0].get("text", "").strip() or None
        return None
    except Exception as exc:
        print(f"[GEMINI ERROR] {type(exc).__name__}: {exc}")
        return None


def llm_response(messages: list[dict[str, str]], system_prompt: str | None = None) -> str | None:
    """Gera uma resposta usando o provedor de IA configurado (OpenRouter, Gemini ou OpenAI)."""
    if settings.ai_provider == "gemini":
        return _gemini_response(messages, system_prompt)

    client = _get_client()
    if client is None:
        return None
    try:
        model = (
            settings.openrouter_model
            if settings.ai_provider == "openrouter"
            else settings.openai_model
        )
        completion = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt or "Você é o assistente virtual do Banco Ágil."},
                *messages,
            ],
            max_tokens=300,
        )
        return completion.choices[0].message.content
    except Exception as exc:
        print(f"[LLM ERROR] {type(exc).__name__}: {exc}")
        return None