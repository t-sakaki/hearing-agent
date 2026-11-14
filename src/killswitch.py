"""キルスイッチ（M4）.

非対話環境でも確実に停止できるよう、フラグファイルで停止要求を伝える。
対応フラグパス: <project_root>/runtime/STOP および <project_root>/output/STOP
（どちらが作成されても検知する）。
"""

import os
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import List


def resolve_project_root(project_root=None) -> Path:
    if project_root is not None:
        return Path(project_root)
    env = os.environ.get("HEARING_PROJECT_ROOT", "").strip()
    if env:
        return Path(env)
    return Path.cwd()


def stop_flag_paths(project_root=None) -> List[Path]:
    root = resolve_project_root(project_root)
    return [root / "runtime" / "STOP", root / "output" / "STOP"]


def is_stop_requested(project_root=None) -> bool:
    return any(p.exists() for p in stop_flag_paths(project_root))


def request_stop(project_root=None, note: str = "") -> Path:
    """停止フラグを作成する（runtime/STOP を主、output/STOP も作成）。"""
    root = resolve_project_root(project_root)
    primary = root / "runtime" / "STOP"
    primary.parent.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone(timedelta(hours=9))).strftime("%Y-%m-%dT%H:%M:%S%z")
    primary.write_text(f"STOP requested at {ts} {note}".strip() + "\n", encoding="utf-8")
    secondary = root / "output" / "STOP"
    secondary.parent.mkdir(parents=True, exist_ok=True)
    try:
        secondary.write_text(primary.read_text(encoding="utf-8"), encoding="utf-8")
    except Exception:
        pass
    return primary


def clear_stop(project_root=None) -> None:
    for p in stop_flag_paths(project_root):
        try:
            p.unlink()
        except FileNotFoundError:
            pass


def jst_now_str() -> str:
    return datetime.now(timezone(timedelta(hours=9))).strftime("%Y-%m-%dT%H:%M:%S%z")
