"""LLM接続モジュール（M1）.

プライマリ: Gemini (gemini-3.5-flash-lite) via OpenAI互換エンドポイント。
フォールバック: Nous beam (reflection/beam-1.0-501b-a23b:free)。
APIキーの値は一切出力しない。環境変数名のみ参照する。
"""

import os
import time
from typing import List, Dict, Any, Tuple

from openai import OpenAI

GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"
GEMINI_MODEL = "gemini-3.5-flash-lite"
GEMINI_KEY_ENV = "GEMINI_API_KEY_OPENCODE"

NOUS_BASE_URL = "https://inference-api.nousresearch.com/v1"
NOUS_MODEL = "reflection/beam-1.0-501b-a23b:free"
NOUS_KEY_ENV = "NOUS_API_KEY"


def _make_client(base_url: str, key_env: str) -> OpenAI:
    key = os.environ.get(key_env)
    if not key:
        raise RuntimeError(f"環境変数 {key_env} が設定されていません")
    return OpenAI(api_key=key, base_url=base_url)


def complete(
    messages: List[Dict[str, str]],
    temperature: float = 0.4,
    max_tokens: int = 400,
) -> Tuple[str, str, str, float]:
    """LLM呼び出し。失敗時のみ Nous にフォールバック。

    戻り値: (text, provider_name, model_name, latency_sec)
    """
    started = time.monotonic()
    providers = [
        ("gemini", GEMINI_BASE_URL, GEMINI_MODEL, GEMINI_KEY_ENV),
        ("nous", NOUS_BASE_URL, NOUS_MODEL, NOUS_KEY_ENV),
    ]
    last_error = None
    for name, base_url, model, key_env in providers:
        try:
            client = _make_client(base_url, key_env)
            resp = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            text = ""
            if resp.choices and resp.choices[0].message:
                text = (resp.choices[0].message.content or "").strip()
            if not text:
                raise RuntimeError("空の応答")
            latency = time.monotonic() - started
            return text, name, model, latency
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            # 次のプロバイダへフォールバック
            continue
    latency = time.monotonic() - started
    raise RuntimeError(f"全プロバイダが失敗しました: {last_error}") from last_error
