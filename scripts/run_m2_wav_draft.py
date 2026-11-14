#!/usr/bin/env python3
"""M2: dummy WAV -> STT -> ドラフト。"""

import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from src.draft import generate_draft  # noqa: E402
from src.logging_util import write_m2_log, now_jst  # noqa: E402
from src.stt import transcribe  # noqa: E402


def main() -> int:
    wav_path = ROOT / "data" / "dummy_question.wav"
    question_path = ROOT / "data" / "dummy_question.txt"
    original = question_path.read_text(encoding="utf-8").strip()

    if not wav_path.exists():
        print(f"WAV が見つかりません: {wav_path}", file=sys.stderr)
        return 1

    # STT
    transcript, stt_sec, stt_model = transcribe(wav_path)

    # LLM draft
    llm_started = time.monotonic()
    draft_text, provider, model, _latency = generate_draft(transcript)
    llm_sec = time.monotonic() - llm_started

    # stdout
    print("=== M2: dummy WAV -> STT -> ドラフト ===")
    print(f"wav={wav_path}")
    print(f"stt_model={stt_model} stt_sec={stt_sec:.3f}")
    print(f"transcript={transcript}")
    print()
    print(f"draft={draft_text}")
    print()
    print(f"provider={provider} model={model} llm_sec={llm_sec:.3f}")

    entry = {
        "timestamp_jst": now_jst().strftime("%Y-%m-%dT%H:%M:%S%z"),
        "stt_model": stt_model,
        "stt_sec": round(stt_sec, 3),
        "provider": provider,
        "model": model,
        "llm_sec": round(llm_sec, 3),
        "original": original,
        "transcript": transcript,
        "draft": draft_text,
    }
    log_path = write_m2_log(ROOT, entry)
    print(f"log={log_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())