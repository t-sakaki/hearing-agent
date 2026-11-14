"""ダミー質問テキストから無料 edge-tts で WAV を生成する（M2）.

ElevenLabs 等の有料APIは使用しない。edge-tts（Microsoft Neural TTS）のみ。
"""

import asyncio
import subprocess
import tempfile
from pathlib import Path
from typing import Optional

VOICE = "ja-JP-NanamiNeural"


def make_wav(text: str, wav_path, voice: Optional[str] = None) -> Path:
    """テキストを edge-tts で MP3 生成し、ffmpeg で WAV(16kHz/mono) に変換して保存。"""
    wav_path = Path(wav_path)
    wav_path.parent.mkdir(parents=True, exist_ok=True)

    v = voice or VOICE
    # voice override via module-level? keep simple
    async def _gen(mp3_path: Path) -> None:
        import edge_tts

        communicate = edge_tts.Communicate(text=text, voice=v)
        await communicate.save(str(mp3_path))

    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
        mp3_path = Path(tmp.name)
    try:
        asyncio.run(_gen(mp3_path))
        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-loglevel",
                "error",
                "-i",
                str(mp3_path),
                "-ar",
                "16000",
                "-ac",
                "1",
                str(wav_path),
            ],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
        )
    finally:
        mp3_path.unlink(missing_ok=True)
    return wav_path
