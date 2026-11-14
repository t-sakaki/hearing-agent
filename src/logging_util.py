"""ログユーティリティ（M1）. JST時刻で入出力・所要秒を記録。APIキー値は記録しない。"""

import json
import os
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict


JST = timezone(timedelta(hours=9))


def now_jst() -> datetime:
    return datetime.now(JST)


def iso_jst(dt: datetime = None) -> str:
    if dt is None:
        dt = now_jst()
    return dt.strftime("%Y-%m-%dT%H:%M:%S%z")


def log_dir(project_root: Path) -> Path:
    d = project_root / "logs"
    d.mkdir(parents=True, exist_ok=True)
    return d


def write_run_log(project_root: Path, entry: Dict[str, Any]) -> Path:
    """1回の実行ログをタイムスタンプ付きファイルに書き、m1.log にも追記する。"""
    d = log_dir(project_root)
    ts = now_jst().strftime("%Y%m%d_%H%M%S")
    path = d / f"run_{ts}.log"
    lines = []
    lines.append(f"timestamp_jst: {entry.get('timestamp_jst')}")
    lines.append(f"provider: {entry.get('provider')}")
    lines.append(f"model: {entry.get('model')}")
    lines.append(f"latency_sec: {entry.get('latency_sec')}")
    lines.append("--- INPUT ---")
    lines.append(str(entry.get("input", "")))
    lines.append("--- OUTPUT ---")
    lines.append(str(entry.get("output", "")))
    if entry.get("error"):
        lines.append("--- ERROR ---")
        lines.append(str(entry.get("error")))
    content = "\n".join(lines) + "\n"
    path.write_text(content, encoding="utf-8")

    # 追記ログ
    append_path = d / "m1.log"
    with append_path.open("a", encoding="utf-8") as f:
        f.write(f"[{entry.get('timestamp_jst')}] provider={entry.get('provider')} latency={entry.get('latency_sec')}s\n")
        f.write(f"  INPUT: {entry.get('input','')[:200]}\n")
        f.write(f"  OUTPUT: {entry.get('output','')[:200]}\n")
    return path


def write_m2_log(project_root: Path, entry: Dict[str, Any]) -> Path:
    """M2実行ログ（JST）。原文・transcript・STT秒・LLM秒・ドラフトを記録。"""
    d = log_dir(project_root)
    ts = now_jst().strftime("%Y%m%d_%H%M%S")
    path = d / f"run_m2_{ts}.log"
    lines = []
    lines.append(f"timestamp_jst: {entry.get('timestamp_jst')}")
    lines.append(f"stt_model: {entry.get('stt_model')}")
    lines.append(f"stt_sec: {entry.get('stt_sec')}")
    lines.append(f"provider: {entry.get('provider')}")
    lines.append(f"model: {entry.get('model')}")
    lines.append(f"llm_sec: {entry.get('llm_sec')}")
    lines.append("--- ORIGINAL TEXT ---")
    lines.append(str(entry.get("original", "")))
    lines.append("--- TRANSCRIPT ---")
    lines.append(str(entry.get("transcript", "")))
    lines.append("--- DRAFT ---")
    lines.append(str(entry.get("draft", "")))
    if entry.get("error"):
        lines.append("--- ERROR ---")
        lines.append(str(entry.get("error")))
    content = "\n".join(lines) + "\n"
    path.write_text(content, encoding="utf-8")

    append_path = d / "m2.log"
    with append_path.open("a", encoding="utf-8") as f:
        f.write(f"[{entry.get('timestamp_jst')}] stt={entry.get('stt_model')} stt_sec={entry.get('stt_sec')} provider={entry.get('provider')} llm_sec={entry.get('llm_sec')}\n")
        f.write(f"  ORIGINAL: {str(entry.get('original',''))[:200]}\n")
        f.write(f"  TRANSCRIPT: {str(entry.get('transcript',''))[:200]}\n")
        f.write(f"  DRAFT: {str(entry.get('draft',''))[:200]}\n")
    return path


def write_m3_log(project_root: Path, entry: Dict[str, Any]) -> Path:
    """M3承認ゲート実行ログ（JST）.

    draft / edit / decision / tts_path(no_tts) / 各タイムスタンプを記録。
    """
    d = log_dir(project_root)
    ts = now_jst().strftime("%Y%m%d_%H%M%S")
    path = d / f"run_m3_{ts}.log"
    lines = []
    lines.append(f"timestamp_jst: {entry.get('timestamp_jst')}")
    lines.append(f"draft_timestamp_jst: {entry.get('draft_timestamp_jst')}")
    lines.append(f"decision_timestamp_jst: {entry.get('decision_timestamp_jst')}")
    lines.append(f"tts_timestamp_jst: {entry.get('tts_timestamp_jst')}")
    lines.append(f"decision: {entry.get('decision')}")
    lines.append(f"tts_path: {entry.get('tts_path')}")
    if entry.get("kill_timestamp_jst"):
        lines.append(f"kill_timestamp_jst: {entry.get('kill_timestamp_jst')}")
    if entry.get("killed_action"):
        lines.append(f"killed_action: {entry.get('killed_action')}")
    lines.append("--- DRAFT ---")
    lines.append(str(entry.get("draft", "")))
    if entry.get("edited"):
        lines.append("--- EDIT ---")
        lines.append(str(entry.get("edited_text", "")))
    if entry.get("error"):
        lines.append("--- ERROR ---")
        lines.append(str(entry.get("error")))
    content = "\n".join(lines) + "\n"
    path.write_text(content, encoding="utf-8")

    append_path = d / "m3.log"
    with append_path.open("a", encoding="utf-8") as f:
        f.write(
            f"[{entry.get('timestamp_jst')}] decision={entry.get('decision')} "
            f"tts={entry.get('tts_path')} draft_ts={entry.get('draft_timestamp_jst')} "
            f"decision_ts={entry.get('decision_timestamp_jst')} tts_ts={entry.get('tts_timestamp_jst')}\n"
        )
        f.write(f"  DRAFT: {str(entry.get('draft',''))[:200]}\n")
        if entry.get("edited"):
            f.write(f"  EDIT: {str(entry.get('edited_text',''))[:200]}\n")
    return path


def write_m4_log(project_root: Path, entry: Dict[str, Any]) -> Path:
    """M4 E2E実行ログ（JST）.

    transcript / draft / edit / decision / tts_path(no_tts) /
    stt_sec / llm_sec / tts_sec / total_sec（承認待ち時間除外）を記録。
    """
    d = log_dir(project_root)
    ts = now_jst().strftime("%Y%m%d_%H%M%S")
    path = d / f"run_m4_{ts}.log"
    lines = []
    lines.append(f"timestamp_jst: {entry.get('timestamp_jst')}")
    lines.append(f"decision: {entry.get('decision')}")
    lines.append(f"tts_path: {entry.get('tts_path')}")
    lines.append(f"stt_model: {entry.get('stt_model')}")
    lines.append(f"stt_sec: {entry.get('stt_sec')}")
    lines.append(f"llm_sec: {entry.get('llm_sec')}")
    lines.append(f"tts_sec: {entry.get('tts_sec')}")
    lines.append(f"total_sec: {entry.get('total_sec')}")
    lines.append(f"provider: {entry.get('provider')}")
    lines.append(f"model: {entry.get('model')}")
    if entry.get("approval_wait_sec") is not None:
        lines.append(f"approval_wait_sec: {entry.get('approval_wait_sec')}")
    if entry.get("kill_timestamp_jst"):
        lines.append(f"kill_timestamp_jst: {entry.get('kill_timestamp_jst')}")
    if entry.get("killed_action"):
        lines.append(f"killed_action: {entry.get('killed_action')}")
    lines.append("--- TRANSCRIPT ---")
    lines.append(str(entry.get("transcript", "")))
    lines.append("--- DRAFT ---")
    lines.append(str(entry.get("draft", "")))
    if entry.get("edit"):
        lines.append("--- EDIT ---")
        lines.append(str(entry.get("edit")))
    if entry.get("error"):
        lines.append("--- ERROR ---")
        lines.append(str(entry.get("error")))
    content = "\n".join(lines) + "\n"
    path.write_text(content, encoding="utf-8")

    append_path = d / "m4.log"
    with append_path.open("a", encoding="utf-8") as f:
        f.write(
            f"[{entry.get('timestamp_jst')}] decision={entry.get('decision')} "
            f"tts={entry.get('tts_path')} stt={entry.get('stt_sec')}s "
            f"llm={entry.get('llm_sec')}s tts={entry.get('tts_sec')}s "
            f"total={entry.get('total_sec')}s\n"
        )
        f.write(f"  TRANSCRIPT: {str(entry.get('transcript',''))[:200]}\n")
        f.write(f"  DRAFT: {str(entry.get('draft',''))[:200]}\n")
        if entry.get("edit"):
            f.write(f"  EDIT: {str(entry.get('edit',''))[:200]}\n")
    return path
