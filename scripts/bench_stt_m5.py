#!/usr/bin/env python3
"""M5 STT ベンチマーク: バッチ vs 逐次 + 用語ヒント比較."""

import sys
import time
import json
from pathlib import Path

# プロジェクトルートをパスに追加
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.stt import transcribe as transcribe_batch
from src.stt_stream import (
    transcribe_stream,
    transcribe_batch_with_terms,
    load_terms,
)

AUDIO_PATH = Path(__file__).parent.parent / "data" / "dummy_question.wav"
TERMS_TO_CHECK = [
    "緑地保全仮許可",
    "審理員",
    "追加資料B",
    "処分庁",
    "模擬審理",
]


def check_terms(text: str, terms: list) -> dict:
    """用語ヒット判定（完全一致または明らかな部分一致）."""
    hits = {}
    for term in terms:
        hits[term] = term in text
    return hits


def run_benchmark():
    print("=" * 60)
    print("M5 STT Benchmark")
    print("=" * 60)
    print(f"Audio: {AUDIO_PATH}")
    print(f"Terms to check: {TERMS_TO_CHECK}")
    print()
    
    results = {}
    
    # (i) 現行バッチ STT（用語ヒントなし、M4相当）
    print("-" * 40)
    print("(i) Batch STT (no terms, M4 equivalent)")
    print("-" * 40)
    text1, elapsed1, model1 = transcribe_batch(AUDIO_PATH)
    hits1 = check_terms(text1, TERMS_TO_CHECK)
    print(f"Time: {elapsed1:.2f}s")
    print(f"Text: {text1}")
    print(f"Hits: {hits1}")
    results["batch_no_terms"] = {
        "text": text1,
        "elapsed_sec": round(elapsed1, 3),
        "model": model1,
        "term_hits": hits1,
    }
    print()
    
    # (ii) バッチ STT + 用語ヒント
    print("-" * 40)
    print("(ii) Batch STT + Terms")
    print("-" * 40)
    text2, elapsed2, model2 = transcribe_batch_with_terms(AUDIO_PATH)
    hits2 = check_terms(text2, TERMS_TO_CHECK)
    print(f"Time: {elapsed2:.2f}s")
    print(f"Text: {text2}")
    print(f"Hits: {hits2}")
    results["batch_with_terms"] = {
        "text": text2,
        "elapsed_sec": round(elapsed2, 3),
        "model": model2,
        "term_hits": hits2,
    }
    print()
    
    # (iii) 逐次 STT + 用語ヒント
    print("-" * 40)
    print("(iii) Streaming STT + Terms")
    print("-" * 40)
    text3, elapsed3, model3, chunk_results = transcribe_stream(AUDIO_PATH, verbose=True)
    hits3 = check_terms(text3, TERMS_TO_CHECK)
    
    # 最初の部分結果までの時間
    first_partial_time = chunk_results[0]["total_elapsed_sec"] if chunk_results else 0
    
    print(f"\nTotal time: {elapsed3:.2f}s")
    print(f"First partial result at: {first_partial_time:.2f}s")
    print(f"Text: {text3}")
    print(f"Hits: {hits3}")
    results["streaming_with_terms"] = {
        "text": text3,
        "total_elapsed_sec": round(elapsed3, 3),
        "first_partial_sec": round(first_partial_time, 3),
        "model": model3,
        "term_hits": hits3,
        "num_chunks": len(chunk_results),
        "chunk_results": chunk_results,
    }
    print()
    
    # 比較サマリ
    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"{'Mode':<25} {'Time(s)':>8} {'FirstPartial(s)':>14} {'Terms Hit':>10}")
    print("-" * 60)
    for key, label in [
        ("batch_no_terms", "Batch (no terms)"),
        ("batch_with_terms", "Batch + terms"),
        ("streaming_with_terms", "Streaming + terms"),
    ]:
        r = results[key]
        t = r["elapsed_sec"] if "elapsed_sec" in r else r["total_elapsed_sec"]
        fp = r.get("first_partial_sec", "N/A")
        hits = sum(1 for v in r["term_hits"].values() if v)
        total = len(r["term_hits"])
        print(f"{label:<25} {t:>8.2f} {str(fp):>14} {hits}/{total}")
    
    # 詳細用語ヒット
    print("\nTerm hit details:")
    for term in TERMS_TO_CHECK:
        row = f"  {term}:"
        for key in ["batch_no_terms", "batch_with_terms", "streaming_with_terms"]:
            hit = results[key]["term_hits"].get(term, False)
            row += f"  {'✓' if hit else '✗'}"
        print(row)
    
    # 結果保存
    out_path = Path(__file__).parent.parent / "logs" / "bench_m5_results.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nResults saved to {out_path}")
    
    return results


if __name__ == "__main__":
    run_benchmark()