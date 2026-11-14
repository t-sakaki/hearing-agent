"""音声文字起こし（STT）モジュール（M2/M6）.

faster-whisper を CPU/int8 で実行する。無料・ローカルのみ。

PyAV(av) の metadata_errors 非互換を避けるため、WAV を標準ライブラリ
(wave) + numpy で 16kHz mono float32 に読み込み、numpy 配列を
WhisperModel.transcribe に渡す（av 経路を完全に避ける）。

M6: 用語ヒント（data/terms.txt）を既定で有効化。比較用に use_terms=False で無効化可能。
"""

import time
import wave
from pathlib import Path
from typing import Tuple, Optional, List

import numpy as np

DEFAULT_MODEL = "small"
DEFAULT_DEVICE = "cpu"
DEFAULT_COMPUTE_TYPE = "int8"
DEFAULT_LANGUAGE = "ja"
TARGET_SAMPLE_RATE = 16000
TERMS_PATH = Path(__file__).parent.parent / "data" / "terms.txt"


def load_terms(terms_path: Path = TERMS_PATH) -> List[str]:
    """用語ファイルを読み込む（1行1語、#コメント除外）。"""
    if not terms_path.exists():
        return []
    terms = []
    for line in terms_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            terms.append(line)
    return terms


def build_initial_prompt(terms: List[str]) -> str:
    """用語リストから initial_prompt 用文字列を構築。"""
    if not terms:
        return ""
    return "、".join(terms) + "。"


def _read_wav_as_float32_mono_16k(path: Path) -> np.ndarray:
    """WAV を 16kHz mono float32 の numpy 配列として読み込む（av 不使用）."""
    with wave.open(str(path), "rb") as wf:
        n_channels = wf.getnchannels()
        sampwidth = wf.getsampwidth()
        framerate = wf.getframerate()
        n_frames = wf.getnframes()
        raw = wf.readframes(n_frames)

    if sampwidth == 1:
        data = np.frombuffer(raw, dtype=np.uint8).astype(np.float32)
        data = (data - 128.0) / 128.0
    elif sampwidth == 2:
        data = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
    elif sampwidth == 4:
        data = np.frombuffer(raw, dtype=np.int32).astype(np.float32) / 2147483648.0
    else:
        raise ValueError(f"未対応の sample width: {sampwidth} bytes")

    if n_channels > 1:
        if data.shape[0] % n_channels != 0:
            data = data[: (data.shape[0] // n_channels) * n_channels]
        data = data.reshape(-1, n_channels).mean(axis=1)

    if framerate != TARGET_SAMPLE_RATE:
        if data.size == 0:
            return data.astype(np.float32)
        new_len = int(round(data.shape[0] * TARGET_SAMPLE_RATE / framerate))
        if new_len <= 1:
            return np.zeros(0, dtype=np.float32)
        x_old = np.arange(data.shape[0], dtype=np.float64)
        x_new = np.linspace(0.0, data.shape[0] - 1, new_len)
        data = np.interp(x_new, x_old, data).astype(np.float32)

    return np.ascontiguousarray(data, dtype=np.float32)


def transcribe(
    audio_path,
    model_size: str = DEFAULT_MODEL,
    device: str = DEFAULT_DEVICE,
    compute_type: str = DEFAULT_COMPUTE_TYPE,
    language: str = DEFAULT_LANGUAGE,
    use_terms: bool = True,
) -> Tuple[str, float, str]:
    """WAV/音声ファイルを文字起こしする。

    戻り値: (transcript, elapsed_sec, model_name)

    Args:
        use_terms: True の場合、data/terms.txt を initial_prompt として渡す（既定 True）。
                   False で用語ヒントなしの従来動作（M4/M5 ベンチマーク比較用）。
    """
    from faster_whisper import WhisperModel

    path = Path(audio_path)
    started = time.monotonic()
    audio = _read_wav_as_float32_mono_16k(path)

    # 用語ヒントの準備
    initial_prompt = None
    if use_terms:
        terms = load_terms()
        if terms:
            initial_prompt = build_initial_prompt(terms)

    model = WhisperModel(model_size, device=device, compute_type=compute_type)
    segments, _info = model.transcribe(
        audio, language=language, beam_size=5, vad_filter=True,
        initial_prompt=initial_prompt,
    )
    text = "".join(seg.text for seg in segments).strip()
    elapsed = time.monotonic() - started
    return text, elapsed, model_size
