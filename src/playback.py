"""音声再生ユーティリティ（M4）.

WSL/Windows での再生をベストエフォートで行う。
ffplay が無ければ再生をスキップ（ファイル出力のみでOK）。
キルスイッチのフラグファイルが立ったら再生プロセスを終了する。
"""

import shutil
import subprocess
import threading
import time
from pathlib import Path
from typing import Optional


def _player_cmd(path: Path) -> Optional[list]:
    if shutil.which("ffplay"):
        return ["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet", str(path)]
    return None


def play_audio_file(path, project_root=None, timeout: int = 300) -> str:
    """音声ファイルを再生する。戻り値はステータス文字列。"""
    from .killswitch import is_stop_requested, resolve_project_root

    root = resolve_project_root(project_root)
    if is_stop_requested(root):
        return "skipped_killed"

    p = Path(path)
    if not p.exists():
        return "file_missing"

    cmd = _player_cmd(p)
    if cmd is None:
        return "no_player"

    try:
        proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        return "play_failed"

    killed = {"flag": False}

    def monitor():
        while proc.poll() is None:
            if is_stop_requested(root):
                killed["flag"] = True
                try:
                    proc.terminate()
                except Exception:
                    pass
                return
            time.sleep(0.2)

    t = threading.Thread(target=monitor, daemon=True)
    t.start()
    try:
        proc.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        try:
            proc.kill()
        except Exception:
            pass
        t.join(timeout=1)
        return "timeout"
    t.join(timeout=1)
    if killed["flag"]:
        try:
            proc.kill()
        except Exception:
            pass
        return "stopped_by_kill"
    if proc.returncode == 0:
        return "played"
    return f"exit_{proc.returncode}"
