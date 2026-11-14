"""承認文面のみを edge-tts でファイル出力する（M3）.

無料の edge-tts (Microsoft Neural TTS) のみ使用。有料APIは使わない。
承認された文面だけを話す。ドラフト原文はこのモジュールでは扱わない。
"""

import asyncio
from pathlib import Path
from typing import Optional

VOICE = "ja-JP-NanamiNeural"


def speak_to_file(text: str, out_path, voice: Optional[str] = None) -> Path:
    """text を edge-tts で MP3 ファイルとして保存する。"""
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    v = voice or VOICE

    async def _gen() -> None:
        import edge_tts

        communicate = edge_tts.Communicate(text=text, voice=v)
        await communicate.save(str(out_path))

    asyncio.run(_gen())
    if not out_path.exists() or out_path.stat().st_size == 0:
        raise RuntimeError(f"TTSファイル生成に失敗しました: {out_path}")
    return out_path


def make_output_path(output_dir, tag: str = "approved") -> Path:
    from datetime import datetime, timezone, timedelta

    JST = timezone(timedelta(hours=9))
    ts = datetime.now(JST).strftime("%Y%m%d_%H%M%S")
    return Path(output_dir) / f"m3_{tag}_{ts}.mp3"