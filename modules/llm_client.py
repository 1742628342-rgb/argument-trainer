from __future__ import annotations

import json
import os
import re

from dotenv import load_dotenv


load_dotenv()

PROVIDERS = ("gemini", "openrouter", "groq")
KEY_NAMES = {
    "gemini": "GEMINI_API_KEY",
    "openrouter": "OPENROUTER_API_KEY",
    "groq": "GROQ_API_KEY",
}
MODEL_NAMES = {
    "gemini": ("GEMINI_MODEL", "gemini-2.5-flash"),
    "openrouter": ("OPENROUTER_MODEL", "openrouter/free"),
    "groq": ("GROQ_MODEL", "llama-3.1-8b-instant"),
}


class LLMUnavailableError(RuntimeError):
    """Raised when no requested LLM provider can return a response."""


def _get_streamlit_secret(name: str) -> str | None:
    try:
        import streamlit as st

        value = st.secrets.get(name)
    except (FileNotFoundError, KeyError, RuntimeError):
        return None
    return str(value).strip() if value is not None else None


def get_config_value(name: str, default: str = "") -> str:
    env_value = os.getenv(name)
    if env_value is not None:
        return env_value.strip()
    return (_get_streamlit_secret(name) or default).strip()


def get_provider_status() -> dict[str, bool]:
    return {
        provider: bool(get_config_value(key_name))
        for provider, key_name in KEY_NAMES.items()
    }


def get_default_provider() -> str:
    provider = get_config_value("DEFAULT_PROVIDER", "auto").lower()
    return provider if provider in (*PROVIDERS, "auto") else "auto"


def get_model_for_provider(provider: str) -> str:
    normalized = provider.strip().lower()
    if normalized == "auto":
        normalized = get_default_provider()
        if normalized == "auto":
            normalized = "gemini"
    if normalized not in MODEL_NAMES:
        raise ValueError("不支持的 LLM provider。")
    env_name, default_model = MODEL_NAMES[normalized]
    return get_config_value(env_name, default_model) or default_model


def parse_json_response(text: str) -> dict | None:
    if not text or not text.strip():
        return None

    cleaned = text.strip()
    fence_match = re.search(r"```(?:json)?\s*(\{.*\})\s*```", cleaned, re.DOTALL)
    if fence_match:
        cleaned = fence_match.group(1)
    else:
        object_match = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if object_match:
            cleaned = object_match.group(0)

    try:
        parsed = json.loads(cleaned)
    except (json.JSONDecodeError, TypeError):
        return None
    return parsed if isinstance(parsed, dict) else None


def _call_gemini(
    api_key: str,
    system_prompt: str,
    user_prompt: str,
    model: str,
) -> str:
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=api_key)
    response = client.models.generate_content(
        model=model,
        contents=user_prompt,
        config=types.GenerateContentConfig(
            system_instruction=system_prompt,
            temperature=0.2,
        ),
    )
    text = getattr(response, "text", None)
    if not text:
        raise LLMUnavailableError("Gemini 未返回文本。")
    return text


def _call_openai_compatible(
    api_key: str,
    base_url: str,
    system_prompt: str,
    user_prompt: str,
    model: str,
    default_headers: dict[str, str] | None = None,
) -> str:
    from openai import OpenAI

    client = OpenAI(
        api_key=api_key,
        base_url=base_url,
        timeout=30.0,
        default_headers=default_headers,
    )
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.2,
    )
    text = response.choices[0].message.content
    if not text:
        raise LLMUnavailableError("Provider 未返回文本。")
    return text


def _call_provider(
    provider: str,
    system_prompt: str,
    user_prompt: str,
    model: str | None = None,
) -> str:
    api_key = get_config_value(KEY_NAMES[provider])
    if not api_key:
        raise LLMUnavailableError(f"{provider} API Key 未配置。")

    selected_model = model or get_model_for_provider(provider)
    try:
        if provider == "gemini":
            return _call_gemini(
                api_key,
                system_prompt,
                user_prompt,
                selected_model,
            )
        if provider == "openrouter":
            return _call_openai_compatible(
                api_key,
                "https://openrouter.ai/api/v1",
                system_prompt,
                user_prompt,
                selected_model,
                {
                    "HTTP-Referer": "http://localhost:8501",
                    "X-OpenRouter-Title": "Argument Trainer",
                },
            )
        return _call_openai_compatible(
            api_key,
            "https://api.groq.com/openai/v1",
            system_prompt,
            user_prompt,
            selected_model,
        )
    except LLMUnavailableError:
        raise
    except Exception as exc:
        raise LLMUnavailableError(f"{provider} API 调用失败。") from exc


def call_llm(
    provider: str,
    system_prompt: str,
    user_prompt: str,
    model: str | None = None,
) -> str:
    normalized = provider.strip().lower()
    if normalized not in (*PROVIDERS, "auto"):
        raise ValueError("provider 必须是 gemini、openrouter、groq 或 auto。")

    if normalized != "auto":
        return _call_provider(
            normalized,
            system_prompt,
            user_prompt,
            model,
        )

    errors = []
    for candidate in PROVIDERS:
        try:
            return _call_provider(
                candidate,
                system_prompt,
                user_prompt,
                model if model and candidate == get_default_provider() else None,
            )
        except LLMUnavailableError as exc:
            errors.append(str(exc))
    raise LLMUnavailableError("所有 API provider 均不可用。")
