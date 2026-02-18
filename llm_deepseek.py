from __future__ import annotations

import json
from typing import Any


def deepseek_chat_completion(
    *,
    api_key: str,
    system_prompt: str,
    user_prompt: str,
    model: str = "deepseek-chat",
    base_url: str = "https://api.deepseek.com/v1/chat/completions",
    temperature: float = 0.2,
    max_tokens: int = 900,
    timeout_s: int = 20,
) -> str:
    """
    Minimal DeepSeek chat completion via OpenAI-compatible REST.
    Requires `requests` at runtime.
    """
    import requests  # local import so app still runs without DeepSeek deps until used

    payload: dict[str, Any] = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": float(temperature),
        "max_tokens": int(max_tokens),
    }

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    resp = requests.post(base_url, headers=headers, data=json.dumps(payload), timeout=int(timeout_s))
    if resp.status_code == 402:
        raise RuntimeError(
            "DeepSeek retornou 402 (Payment Required): sua conta nao tem saldo/credito para usar a API. "
            "Ative billing/adicone credito ou use o fallback (Groq/heuristica)."
        )
    resp.raise_for_status()
    data = resp.json()
    choices = data.get("choices") or []
    if not choices:
        return "DeepSeek: resposta vazia."
    msg = (choices[0] or {}).get("message") or {}
    content = msg.get("content")
    return content if isinstance(content, str) and content.strip() else "DeepSeek: resposta vazia."
