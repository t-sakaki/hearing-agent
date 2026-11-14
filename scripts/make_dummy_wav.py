#!/usr/bin/env python3
"""ダミー質問テキストから WAV を生成する（M2）。"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from src.tts_dummy import make_wav  # noqa: E402


def main() -> int:
    question_path = ROOT / "data" / "dummy_question.txt"
    wav_path = ROOT / "data" / "dummy_question.wav"
    text = question_path.read_text(encoding="utf-8").strip()
    out = make_wav(text, wav_path)
    print(f"wav={out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())