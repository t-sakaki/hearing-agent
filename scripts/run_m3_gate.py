#!/usr/bin/env python3
"""M3: ドラフト -> 承認ゲート -> (承認時のみ) TTS.

非対話:
  --stdin : stdin プロトコルから決定を読む
  --auto  : 環境変数 HEARING_APPROVE_MODE=auto + HEARING_DECISION 等
対話: それ以外 (tty)
"""

import argparse
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from src.approval import run_gate  # noqa: E402
from src.draft import generate_draft  # noqa: E402
from src.logging_util import now_jst, write_m3_log  # noqa: E402
from src.stt import transcribe  # noqa: E402
from src.tts_speak import make_output_path, speak_to_file  # noqa: E402

DEFAULT_DRAFT = (
    "（ダミー模擬審理）審理員の質問への反論案ドラフトです。"
    "追加資料Bの提出遅延について、やむを得ない事情があったことを丁寧に説明いたします。"
)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--stdin", action="store_true", help="stdin プロトコルで決定を読む")
    p.add_argument("--auto", action="store_true", help="環境変数から決定を読む")
    p.add_argument("--draft", type=str, default=None, help="ドラフト文")
    p.add_argument("--draft-file", type=str, default=None, help="ドラフト文ファイル")
    p.add_argument("--from-m2", action="store_true", help="M2パイプライン(STT+LLM)でドラフト生成")
    p.add_argument("--output-dir", type=str, default=str(ROOT / "output"), help="音声出力ディレクトリ")
    return p.parse_args()


def obtain_draft(args) -> str:
    if args.from_m2:
        wav_path = ROOT / "data" / "dummy_question.wav"
        if not wav_path.exists():
            raise SystemExit(f"WAV が見つかりません: {wav_path}")
        transcript, _stt_sec, _stt_model = transcribe(wav_path)
        draft_text, _provider, _model, _latency = generate_draft(transcript)
        return draft_text
    if args.draft_file:
        return Path(args.draft_file).read_text(encoding="utf-8").strip()
    if args.draft:
        return args.draft.strip()
    return DEFAULT_DRAFT


def main() -> int:
    args = parse_args()

    if args.stdin:
        mode = "stdin"
    elif args.auto:
        mode = "auto"
    else:
        mode = None

    draft_ts = now_jst()
    draft = obtain_draft(args)
    draft_ts_str = draft_ts.strftime("%Y-%m-%dT%H:%M:%S%z")

    print("=== M3: ドラフト -> 承認ゲート ===")
    print("--- DRAFT ---")
    print(draft)
    print("-------------")

    decision_ts = now_jst()
    result = run_gate(draft, mode=mode)
    decision_ts_str = decision_ts.strftime("%Y-%m-%dT%H:%M:%S%z")

    print(f"decision={result.decision}")

    tts_path = "no_tts"
    tts_ts_str = None
    if result.decision in ("approve", "edit_approve") and result.final_text:
        out_path = make_output_path(args.output_dir, tag=result.decision)
        speak_to_file(result.final_text, out_path)
        tts_path = str(out_path)
        tts_ts_str = now_jst().strftime("%Y-%m-%dT%H:%M:%S%z")
        print(f"tts_path={tts_path}")

    entry = {
        "timestamp_jst": now_jst().strftime("%Y-%m-%dT%H:%M:%S%z"),
        "draft_timestamp_jst": draft_ts_str,
        "decision_timestamp_jst": decision_ts_str,
        "tts_timestamp_jst": tts_ts_str,
        "decision": result.decision,
        "tts_path": tts_path,
        "draft": draft,
        "edited": result.edited,
        "edited_text": result.edited_text,
    }
    if result.decision == "killed":
        entry["kill_timestamp_jst"] = now_jst().strftime("%Y-%m-%dT%H:%M:%S%z")
        entry["killed_action"] = "approval_gate"
    log_path = write_m3_log(ROOT, entry)
    print(f"log={log_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())