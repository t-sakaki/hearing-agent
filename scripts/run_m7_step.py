#!/usr/bin/env python3
"""M7 の STT / ドラフト / 承認ゲート / TTS をファイル経由で実行する。

承認ゲートは M4 と同じくプロジェクトルートを sys.path に入れ、
`from src.approval import run_gate` で呼び出す（相対 import の ImportError を避ける）。
ドラフトや final_text は一時ファイル / JSON に全文を書く（一行 grep しない）。
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


DRAFT_SYSTEM = (
    "あなたは行政不服審査の審理員補助です。"
    "請求人の口頭意見陳述の書き起こしから、審理員向けの要点整理ドラフトを簡潔に作成してください。"
    "事実関係・争点・請求人の主張を箇条書きで。"
    "専門用語（緑地保全仮許可、審理員、処分庁、請求人）を適切に使用してください。"
    "200文字程度で。"
)


def _write_json(path: Path, obj: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def cmd_stt(args: argparse.Namespace) -> int:
    from src.stt import transcribe

    text, elapsed, model = transcribe(args.wav, use_terms=True)
    _write_text(Path(args.out_text), text)
    _write_json(
        Path(args.out_json),
        {"transcript": text, "elapsed": elapsed, "model": model},
    )
    return 0


def cmd_draft(args: argparse.Namespace) -> int:
    from src.llm import complete

    transcript = Path(args.transcript_file).read_text(encoding="utf-8")
    messages = [
        {"role": "system", "content": DRAFT_SYSTEM},
        {"role": "user", "content": transcript},
    ]
    text, provider, model, latency = complete(messages, temperature=0.3, max_tokens=300)
    _write_text(Path(args.out_text), text)
    _write_json(
        Path(args.out_json),
        {
            "draft": text,
            "provider": provider,
            "model": model,
            "latency": latency,
        },
    )
    return 0


def cmd_gate(args: argparse.Namespace) -> int:
    from src.approval import run_gate

    draft = Path(args.draft_file).read_text(encoding="utf-8")
    mode = "stdin" if args.stdin else "interactive"
    timeout = args.timeout if args.timeout and args.timeout > 0 else None
    result = run_gate(draft, mode=mode, project_root=ROOT, timeout_sec=timeout)
    payload = result.to_dict()
    _write_json(Path(args.out_json), payload)
    final = result.final_text if result.final_text is not None else ""
    if args.final_text_file:
        _write_text(Path(args.final_text_file), final)
    return 0


def cmd_tts(args: argparse.Namespace) -> int:
    from src.tts_speak import speak_to_file

    text = Path(args.text_file).read_text(encoding="utf-8")
    if not text.strip():
        print("TTS する文が空です", file=sys.stderr)
        return 1
    out = speak_to_file(text, args.out_mp3)
    _write_json(Path(args.out_json), {"tts_path": str(out)})
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="M7 pipeline steps")
    sub = p.add_subparsers(dest="cmd", required=True)

    stt = sub.add_parser("stt")
    stt.add_argument("--wav", required=True)
    stt.add_argument("--out-json", required=True)
    stt.add_argument("--out-text", required=True)
    stt.set_defaults(func=cmd_stt)

    draft = sub.add_parser("draft")
    draft.add_argument("--transcript-file", required=True)
    draft.add_argument("--out-json", required=True)
    draft.add_argument("--out-text", required=True)
    draft.set_defaults(func=cmd_draft)

    gate = sub.add_parser("gate")
    gate.add_argument("--draft-file", required=True)
    gate.add_argument("--out-json", required=True)
    gate.add_argument("--final-text-file", required=True)
    gate.add_argument("--stdin", action="store_true")
    gate.add_argument("--timeout", type=int, default=120)
    gate.set_defaults(func=cmd_gate)

    tts = sub.add_parser("tts")
    tts.add_argument("--text-file", required=True)
    tts.add_argument("--out-mp3", required=True)
    tts.add_argument("--out-json", required=True)
    tts.set_defaults(func=cmd_tts)

    return p


def main() -> int:
    args = build_parser().parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
