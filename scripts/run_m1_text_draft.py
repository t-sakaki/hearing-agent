#!/usr/bin/env python3
"""M1: テキスト入力 → LLM反論ドラフト。"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from src.draft import generate_draft  # noqa: E402
from src.logging_util import write_run_log, now_jst  # noqa: E402


def main() -> int:
    question_path = ROOT / "data" / "dummy_question.txt"
    question = question_path.read_text(encoding="utf-8").strip()

    text, provider, model, latency = generate_draft(question)

    # stdout
    print("=== 反論ドラフト（ダミー模擬審理） ===")
    print(text)
    print()
    print(f"provider={provider} model={model} latency_sec={latency:.3f}")

    entry = {
        "timestamp_jst": now_jst().strftime("%Y-%m-%dT%H:%M:%S%z"),
        "provider": provider,
        "model": model,
        "latency_sec": round(latency, 3),
        "input": question,
        "output": text,
    }
    log_path = write_run_log(ROOT, entry)
    print(f"log={log_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
