"""逐次・ストリーミング文字起こし + 専門用語ヒント（M5/M6）.

faster-whisper (CPU int8, small) を用い、音声を短いチャンクに分割して
逐次的に文字起こしを行う。キルスイッチ対応・用語ヒント対応。

M6 改善:
- テキストベースの suffix/prefix 最長一致で重複除去（文字レベルで照合）
- 速度改善: overlap 縮小、beam_size=3、短い prefix で文脈維持・幻覚防止
- 用語ヒントは initial_prompt で維持
"""

import time
import wave
from pathlib import Path
from typing import List, Tuple, Optional

import numpy as np

from .killswitch import is_stop_requested, resolve_project_root

DEFAULT_MODEL = "small"
DEFAULT_DEVICE = "cpu"
DEFAULT_COMPUTE_TYPE = "int8"
DEFAULT_LANGUAGE = "ja"
TARGET_SAMPLE_RATE = 16000

# チャンク設定（M6: 高速化のため調整）
CHUNK_DURATION_SEC = 3.0      # 1チャンクの長さ（秒）M5: 3.5 -> 3.0
OVERLAP_DURATION_SEC = 0.3    # オーバーラップ（秒）M5: 0.5 -> 0.3

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
    """WAV を 16kHz mono float32 の numpy 配列として読み込む（av 不使用）。"""
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


def chunk_audio(audio: np.ndarray, chunk_sec: float = CHUNK_DURATION_SEC,
                overlap_sec: float = OVERLAP_DURATION_SEC,
                sample_rate: int = TARGET_SAMPLE_RATE) -> List[Tuple[np.ndarray, float]]:
    """音声をオーバーラップ付きチャンクに分割.

    戻り値: [(chunk_audio, start_time_sec), ...]
    """
    chunk_samples = int(chunk_sec * sample_rate)
    overlap_samples = int(overlap_sec * sample_rate)
    step_samples = chunk_samples - overlap_samples

    if step_samples <= 0:
        step_samples = chunk_samples

    chunks = []
    start = 0
    while start < len(audio):
        end = min(start + chunk_samples, len(audio))
        chunk_data = audio[start:end]
        start_time = start / sample_rate
        chunks.append((chunk_data, start_time))
        if end >= len(audio):
            break
        start += step_samples
    return chunks


def _longest_common_suffix_prefix(text1: str, text2: str) -> int:
    """text1 の接尾辞と text2 の接頭辞の最長一致長（文字数）を返す。

    日本語では単語分割が不安定なため、文字レベルで照合する。
    最小一致長は 2 文字以上とする（1文字は誤一致しやすいため）。
    """
    if not text1 or not text2:
        return 0

    max_len = min(len(text1), len(text2))
    # 2文字以上で最長一致を探す
    for l in range(max_len, 1, -1):
        if text1[-l:] == text2[:l]:
            return l
    return 0


def _dedup_text_suffix_prefix(prev_text: str, curr_text: str) -> Tuple[str, bool]:
    """テキストベースの suffix/prefix 最長一致で重複除去（文字レベル）。

    戻り値: (dedup_text, dedup_applied)
    """
    if not prev_text or not curr_text:
        return curr_text, False

    match_len = _longest_common_suffix_prefix(prev_text, curr_text)
    if match_len >= 2:
        return curr_text[match_len:].lstrip(), True

    return curr_text, False


def transcribe_stream(
    audio_path,
    model_size: str = DEFAULT_MODEL,
    device: str = DEFAULT_DEVICE,
    compute_type: str = DEFAULT_COMPUTE_TYPE,
    language: str = DEFAULT_LANGUAGE,
    project_root: Optional[str] = None,
    chunk_sec: float = CHUNK_DURATION_SEC,
    overlap_sec: float = OVERLAP_DURATION_SEC,
    verbose: bool = True,
    beam_size: int = 3,          # M6: 5 -> 3 で高速化しつつ品質維持
) -> Tuple[str, float, str, List[dict]]:
    """ストリーミング文字起こし（M6: 重複除去・高速化対応）.

    戻り値: (full_transcript, elapsed_sec, model_name, chunk_results)
    chunk_results: [{"chunk": i, "start_sec": float, "text": str,
                     "elapsed_sec": float, "total_elapsed_sec": float,
                     "dedup_applied": bool}, ...]
    """
    from faster_whisper import WhisperModel

    path = Path(audio_path)
    root = resolve_project_root(project_root)

    # 用語読み込み
    terms = load_terms()
    initial_prompt_base = build_initial_prompt(terms)

    if verbose:
        print(f"[stt_stream] Loaded {len(terms)} terms: {terms}")
        if initial_prompt_base:
            print(f"[stt_stream] initial_prompt: {initial_prompt_base[:100]}...")
        print(f"[stt_stream] M6 settings: chunk={chunk_sec}s, overlap={overlap_sec}s, beam_size={beam_size}")

    # 音声読み込み
    audio = _read_wav_as_float32_mono_16k(path)
    total_duration = len(audio) / TARGET_SAMPLE_RATE

    if verbose:
        print(f"[stt_stream] Audio: {total_duration:.1f}s, {len(audio)} samples")

    # チャンク分割
    chunks = chunk_audio(audio, chunk_sec, overlap_sec)
    if verbose:
        print(f"[stt_stream] {len(chunks)} chunks")

    # モデルロード
    model = WhisperModel(model_size, device=device, compute_type=compute_type)

    started = time.monotonic()
    chunk_results = []
    full_text_parts = []
    prev_chunk_text = ""  # 前チャンクの確定テキスト（重複除去用）

    for i, (chunk_data, start_time) in enumerate(chunks):
        # キルスイッチチェック（各チャンク開始前）
        if is_stop_requested(root):
            if verbose:
                print(f"[stt_stream] STOP requested at chunk {i}, aborting")
            break

        chunk_started = time.monotonic()

        # M6: 短い prefix（前チャンク末尾 20 文字）で文脈維持・幻覚防止
        # 長すぎると幻覚・繰り返しの原因になるため厳格に制限
        prefix_prompt = prev_chunk_text[-20:] if prev_chunk_text else ""
        if initial_prompt_base and prefix_prompt:
            initial_prompt = initial_prompt_base + " " + prefix_prompt
        elif initial_prompt_base:
            initial_prompt = initial_prompt_base
        elif prefix_prompt:
            initial_prompt = prefix_prompt
        else:
            initial_prompt = None

        # 文字起こし（用語ヒント + 短い prefix、word_timestamps=False で高速化）
        segments, _info = model.transcribe(
            chunk_data,
            language=language,
            beam_size=beam_size,
            vad_filter=True,
            initial_prompt=initial_prompt,
            word_timestamps=False,
        )
        segments = list(segments)  # イテレータを消費

        # 現在チャンクの生テキスト
        curr_raw_text = "".join(seg.text for seg in segments).strip()

        # 重複除去（suffix/prefix 最長一致・文字レベル）
        curr_text, dedup_applied = _dedup_text_suffix_prefix(prev_chunk_text, curr_raw_text)

        chunk_elapsed = time.monotonic() - chunk_started
        total_elapsed = time.monotonic() - started

        chunk_results.append({
            "chunk": i,
            "start_sec": round(start_time, 2),
            "text": curr_text,
            "raw_text": curr_raw_text,
            "elapsed_sec": round(chunk_elapsed, 3),
            "total_elapsed_sec": round(total_elapsed, 3),
            "dedup_applied": dedup_applied,
        })

        full_text_parts.append(curr_text)
        prev_chunk_text = "".join(full_text_parts).strip()

        if verbose:
            dup_mark = " [dedup]" if dedup_applied else ""
            print(f"[stt_stream] Chunk {i:2d} ({start_time:5.1f}s): {curr_text[:80]}"
                  f"  ({chunk_elapsed:.2f}s, total {total_elapsed:.2f}s){dup_mark}")

    total_elapsed = time.monotonic() - started
    full_transcript = "".join(full_text_parts).strip()

    return full_transcript, total_elapsed, model_size, chunk_results


def transcribe_batch_with_terms(
    audio_path,
    model_size: str = DEFAULT_MODEL,
    device: str = DEFAULT_DEVICE,
    compute_type: str = DEFAULT_COMPUTE_TYPE,
    language: str = DEFAULT_LANGUAGE,
) -> Tuple[str, float, str]:
    """バッチ処理 + 用語ヒント（ベンチマーク比較用）."""
    from faster_whisper import WhisperModel

    path = Path(audio_path)
    terms = load_terms()
    initial_prompt = build_initial_prompt(terms)

    started = time.monotonic()
    audio = _read_wav_as_float32_mono_16k(path)

    model = WhisperModel(model_size, device=device, compute_type=compute_type)
    segments, _info = model.transcribe(
        audio,
        language=language,
        beam_size=5,
        vad_filter=True,
        initial_prompt=initial_prompt if initial_prompt else None,
    )
    text = "".join(seg.text for seg in segments).strip()
    elapsed = time.monotonic() - started

    return text, elapsed, model_size


if __name__ == "__main__":
    import sys
    audio = sys.argv[1] if len(sys.argv) > 1 else "data/dummy_question.wav"
    text, elapsed, model, chunks = transcribe_stream(audio)
    print(f"\n=== Final ({elapsed:.2f}s) ===")
    print(text)