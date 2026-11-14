#!/usr/bin/env python3
"""M4: エンドツーエンド（STT -> LLMドラフト -> 承認ゲート -> 承認時のみ TTS）.

人間の承認待ち時間は total_sec から除外する。
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

from src.approval import run_gate
from src.draft import generate_draft
from src.killswitch import clear_stop, is_stop_requested, resolve_project_root
from src.logging_util import now_jst, write_m4_log
from src.playback import play_audio_file
from src.stt import transcribe
from src.tts_dummy import make_wav
from src.tts_speak import make_output_path, speak_to_file


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--stdin", action="store_true", help="stdin プロトコルで決定を読む")
    p.add_argument("--auto", action="store_true", help="環境変数から決定を読む")
    p.add_argument("--draft", type=str, default=None, help="ドラフト文（STT/LLMをスキップ）")
    p.add_argument("--draft-file", type=str, default=None, help="ドラフト文ファイル")
    p.add_argument("--no-stt", action="store_true", help="STT/LLMをスキップして --draft を使う")
    p.add_argument("--output-dir", type=str, default=str(ROOT / "output"), help="音声出力ディレクトリ")
    p.add_argument("--play", action="store_true", help="生成音声を再生を試みる")
    p.add_argument("--clear-stop", action="store_true", help="開始前に STOP フラグをクリアする")
    p.add_argument("--timeout", type=int, default=None, help="対話承認のタイムアウト秒")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    root = ROOT
    if args.clear_stop:
        clear_stop(root)

    if args.stdin:
        mode = "stdin"
    elif args.auto:
        mode = "auto"
    else:
        mode = None

    pipeline_start = time.monotonic()
    approval_wait = 0.0
    stt_sec = 0.0
    llm_sec = 0.0
    tts_sec = 0.0
    transcript = ""
    draft = ""
    edited_text = None
    final_text = None
    decision = "killed" if is_stop_requested(root) else ""
    tts_path = "no_tts"
    stt_model = None
    provider = None
    model = None
    killed_action = None
    kill_ts = None

    def mark_killed(action: str):
        nonlocal killed_action, kill_ts, decision
        if killed_action is None:
            killed_action = action
            kill_ts = now_jst()
        decision = "killed"

    # 1. dummy WAV
    wav_path = root / "data" / "dummy_question.wav"
    question_path = root / "data" / "dummy_question.txt"
    if not wav_path.exists():
        text = question_path.read_text(encoding="utf-8").strip() if question_path.exists() else "ダミー質問です。"
        make_wav(text, wav_path)
    if not wav_path.exists():
        print(f"WAV が見つかりません: {wav_path}", file=sys.stderr)
        return 1

    if is_stop_requested(root) and killed_action is None:
        mark_killed("pipeline_start")

    # 2. STT
    if decision != "killed" and not args.no_stt:
        if is_stop_requested(root):
            mark_killed("stt_before")
        else:
            s = time.monotonic()
            try:
                transcript, stt_sec, stt_model = transcribe(wav_path)
            except Exception as exc:
                print(f"STT エラー: {exc}", file=sys.stderr)
                transcript = ""
            stt_sec = time.monotonic() - s
            if is_stop_requested(root):
                mark_killed("stt")

    # 3. LLM draft
    if decision != "killed":
        if args.no_stt or args.draft or args.draft_file:
            if args.draft_file:
                draft = Path(args.draft_file).read_text(encoding="utf-8").strip()
            elif args.draft:
                draft = args.draft.strip()
        else:
            if is_stop_requested(root):
                mark_killed("llm_before")
            else:
                s = time.monotonic()
                base_q = transcript if transcript.strip() else (
                    question_path.read_text(encoding="utf-8").strip() if question_path.exists() else ""
                )
                try:
                    draft, provider, model, _lat = generate_draft(base_q)
                except Exception as exc:
                    print(f"LLM エラー: {exc}", file=sys.stderr)
                    draft = ""
                llm_sec = time.monotonic() - s
                if is_stop_requested(root):
                    mark_killed("llm")

    if not draft.strip():
        if args.draft_file:
            draft = Path(args.draft_file).read_text(encoding="utf-8").strip()
        elif args.draft:
            draft = args.draft.strip()
        else:
            draft = "（ダミードラフト）"

    # 4. approval gate
    if decision != "killed":
        if is_stop_requested(root):
            mark_killed("approval_before")
        else:
            approval_start = time.monotonic()
            result = run_gate(draft, mode=mode, project_root=root, timeout_sec=args.timeout)
            approval_wait = time.monotonic() - approval_start
            decision = result.decision
            if decision == "killed":
                mark_killed("approval")
            edited_text = result.edited_text
            final_text = result.final_text

    # 5. TTS (approval only)
    if decision in ("approve", "edit_approve") and final_text and not is_stop_requested(root):
        s = time.monotonic()
        try:
            out_path = make_output_path(args.output_dir, tag=decision)
            speak_to_file(final_text, out_path)
            tts_sec = time.monotonic() - s
            if is_stop_requested(root):
                mark_killed("tts_generation")
                tts_path = str(out_path)
            else:
                tts_path = str(out_path)
                if args.play:
                    play_status = play_audio_file(out_path, root)
                    if play_status == "stopped_by_kill":
                        mark_killed("playback")
        except Exception as exc:
            print(f"TTS エラー: {exc}", file=sys.stderr)
            tts_sec = time.monotonic() - s
            tts_path = "no_tts"

    if decision == "killed":
        # keep tts_path if file was created, else no_tts
        pass

    total_sec = (time.monotonic() - pipeline_start) - approval_wait

    # stdout
    print("=== M4 E2E ===")
    print(f"wav={wav_path}")
    print(f"stt_model={stt_model} stt_sec={stt_sec:.3f}")
    print(f"transcript={transcript}")
    print()
    print(f"draft={draft}")
    print()
    if edited_text:
        print(f"edit={edited_text}")
    print(f"decision={decision}")
    print(f"tts_path={tts_path}")
    print(f"llm_sec={llm_sec:.3f} tts_sec={tts_sec:.3f} total_sec={total_sec:.3f}")
    print(f"approval_wait_sec={approval_wait:.3f} (excluded from total)")

    entry = {
        "timestamp_jst": now_jst().strftime("%Y-%m-%dT%H:%M:%S%z"),
        "transcript": transcript,
        "draft": draft,
        "edit": edited_text,
        "decision": decision,
        "tts_path": tts_path,
        "stt_sec": round(stt_sec, 3),
        "llm_sec": round(llm_sec, 3),
        "tts_sec": round(tts_sec, 3),
        "total_sec": round(total_sec, 3),
        "stt_model": stt_model,
        "provider": provider,
        "model": model,
        "approval_wait_sec": round(approval_wait, 3),
    }
    if killed_action:
        entry["killed_action"] = killed_action
        entry["kill_timestamp_jst"] = kill_ts.strftime("%Y-%m-%dT%H:%M:%S%z") if kill_ts else None

    log_path = write_m4_log(root, entry)
    print(f"log={log_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
