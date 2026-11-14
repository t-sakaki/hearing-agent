"""ドラフト生成モジュール（M1）."""

from pathlib import Path
from typing import Tuple

from .llm import complete

SYSTEM_PROMPT = (
    "あなたは不服審査・口頭意見陳述の練習を支援するアシスタントです。"
    "これは架空の模擬審理（ダミー）です。実在の事件・当事者・資料を用いてはいけません。"
    "審理員の質問に対し、請求人側の短い口頭意見陳述用の反論案を日本語で作成してください。"
    "文体は丁寧（です・ます調）、長さは3〜5文程度で簡潔に。"
    "事実を断定せず、説明・釈明のトーンで。"
    "出力は反論案本文のみ（前置き・見出し不要）。"
)


def build_messages(question: str) -> list:
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"以下の審理員質問への反論案を作成してください（ダミー模擬審理）。\n\n{question}"},
    ]


def generate_draft(question: str) -> Tuple[str, str, str, float]:
    messages = build_messages(question)
    text, provider, model, latency = complete(messages)
    return text, provider, model, latency
