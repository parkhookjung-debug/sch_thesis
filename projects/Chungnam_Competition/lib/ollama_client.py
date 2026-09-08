# -*- coding: utf-8 -*-
"""
선택: Ollama OpenAI-호환 /api/v1/chat/completions 또는 레거시 /api/chat
텍스트 생성 전용. 추천/랭킹에 사용하지 않는다.
"""
from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any

from lib.config import settings


def ollama_chat(
    system: str, user: str, *, temperature: float = 0.35, timeout: float = 12.0
) -> str | None:
    """
    Ollama HTTP API. 실패·타임아웃 시 None.
    """
    base = (getattr(settings, "ollama_base_url", None) or "").strip()
    if not base:
        return None
    model = str(getattr(settings, "ollama_model", "llama3.2") or "llama3.2")
    # OpenAI 호환 엔드포인트(일반적)
    url = base.rstrip("/") + "/v1/chat/completions"
    body = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "temperature": temperature,
    }
    raw = json.dumps(body, ensure_ascii=False).encode("utf-8")
    try:
        req = urllib.request.Request(
            url,
            data=raw,
            method="POST",
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310
            data = json.loads(resp.read().decode("utf-8"))
    except (OSError, urllib.error.URLError, json.JSONDecodeError, ValueError):
        # 네이티브 /api/chat 백오프
        return _ollama_native_chat(base, model, system, user, temperature, timeout)
    if not data:
        return None
    try:
        return str(data["choices"][0]["message"]["content"] or "").strip() or None
    except (KeyError, IndexError, TypeError):
        return None


def _ollama_native_chat(
    base: str,
    model: str,
    system: str,
    user: str,
    temperature: float,
    timeout: float,
) -> str | None:
    url = base.rstrip("/") + "/api/chat"
    body = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "stream": False,
        "options": {"temperature": temperature},
    }
    raw = json.dumps(body, ensure_ascii=False).encode("utf-8")
    try:
        req = urllib.request.Request(
            url,
            data=raw,
            method="POST",
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310
            data = json.loads(resp.read().decode("utf-8"))
    except (OSError, urllib.error.URLError, json.JSONDecodeError, ValueError):
        return None
    try:
        return str(data["message"]["content"] or "").strip() or None
    except (KeyError, TypeError):
        return None


def ollama_available() -> bool:
    return bool((getattr(settings, "ollama_base_url", None) or "").strip())
