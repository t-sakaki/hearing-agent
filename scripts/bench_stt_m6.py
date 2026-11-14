#!/usr/bin/env python3
"""M6 STT ベンチマーク: 用語標準化 + 逐次STT重複除去/高速化の比較."""

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
from src.killswitch import request_stop, clear_stop, is_stop_requested, resolve_project_root

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


def count_duplicates(chunk_results: list) -> int:
    """逐次STTのチャンク結果から重複除去が適用された回数を数える."""
    return sum(1 for r in chunk_results if r.get("dedup_applied", False))


def run_benchmark():
    print("=" * 60)
    print("M6 STT Benchmark")
    print("=" * 60)
    print(f"Audio: {AUDIO_PATH}")
    print(f"Terms to check: {TERMS_TO_CHECK}")
    print()

    results = {}

    # (i) バッチ STT 用語なし（M4/M5 ベースライン相当）
    print("-" * 40)
    print("(i) Batch STT (no terms, M4/M5 baseline)")
    print("-" * 40)
    text1, elapsed1, model1 = transcribe_batch(AUDIO_PATH, use_terms=False)
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

    # (ii) バッチ STT + 用語ヒント（M6 新標準: use_terms=True 既定）
    print("-" * 40)
    print("(ii) Batch STT + Terms (M6 new default)")
    print("-" * 40)
    text2, elapsed2, model2 = transcribe_batch(AUDIO_PATH, use_terms=True)
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

    # (iii) 逐次 STT + 用語ヒント + 重複除去 + 高速化（M6 改善版）
    print("-" * 40)
    print("(iii) Streaming STT + Terms + Dedup + Speed (M6)")
    print("-" * 40)
    text3, elapsed3, model3, chunk_results = transcribe_stream(AUDIO_PATH, verbose=True)
    hits3 = check_terms(text3, TERMS_TO_CHECK)

    # 最初の部分結果までの時間
    first_partial_time = chunk_results[0]["total_elapsed_sec"] if chunk_results else 0

    # 重複除去回数
    dedup_count = count_duplicates(chunk_results)

    print(f"\nTotal time: {elapsed3:.2f}s")
    print(f"First partial result at: {first_partial_time:.2f}s")
    print(f"Text: {text3}")
    print(f"Hits: {hits3}")
    print(f"Deduplications applied: {dedup_count}")
    results["streaming_m6"] = {
        "text": text3,
        "total_elapsed_sec": round(elapsed3, 3),
        "first_partial_sec": round(first_partial_time, 3),
        "model": model3,
        "term_hits": hits3,
        "num_chunks": len(chunk_results),
        "dedup_count": dedup_count,
        "chunk_results": chunk_results,
    }
    print()

    # 比較サマリ
    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"{'Mode':<30} {'Time(s)':>8} {'FirstPartial(s)':>14} {'Terms Hit':>10} {'Dedup':>6}")
    print("-" * 70)
    for key, label in [
        ("batch_no_terms", "Batch (no terms)"),
        ("batch_with_terms", "Batch + terms (M6 default)"),
        ("streaming_m6", "Streaming M6 (dedup+speed)"),
    ]:
        r = results[key]
        t = r["elapsed_sec"] if "elapsed_sec" in r else r["total_elapsed_sec"]
        fp = r.get("first_partial_sec", "N/A")
        hits = sum(1 for v in r["term_hits"].values() if v)
        total = len(r["term_hits"])
        dedup = r.get("dedup_count", "N/A")
        print(f"{label:<30} {t:>8.2f} {str(fp):>14} {hits}/{total:<4} {str(dedup):>6}")

    # 詳細用語ヒット
    print("\nTerm hit details:")
    for term in TERMS_TO_CHECK:
        row = f"  {term}:"
        for key in ["batch_no_terms", "batch_with_terms", "streaming_m6"]:
            hit = results[key]["term_hits"].get(term, False)
            row += f"  {'✓' if hit else '✗'}"
        print(row)

    # 結果保存
    out_path = Path(__file__).parent.parent / "logs" / "bench_m6_results.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nResults saved to {out_path}")

    return results


def test_killswitch():
    """キルスイッチ動作確認: 逐次STT途中でSTOPを立て、チャンク境界で中断・部分結果残存を確認."""
    print("\n" + "=" * 60)
    print("KILLSWITCH TEST")
    print("=" * 60)

    root = resolve_project_root()
    clear_stop(root)

    # STOPフラグを立てる（3チャンク目あたりで中断される想定で、別スレッドで立てるのは複雑なので
    # ここでは事前に立てて「開始時からSTOPあり」のケースをテスト）
    # 実際の運用では別プロセスから touch runtime/STOP する想定
    request_stop(root, "M6 benchmark killswitch test")
    print(f"STOP flag created. is_stop_requested: {is_stop_requested(root)}")

    # 逐次STT実行（即座に中断されるはず）
    text, elapsed, model, chunk_results = transcribe_stream(
        AUDIO_PATH, verbose=True, chunk_sec=3.0, overlap_sec=0.3
    )

    print(f"Chunks processed: {len(chunk_results)}")
    print(f"Partial transcript: {text[:100]}...")
    print(f"Elapsed: {elapsed:.2f}s")

    # STOPフラグクリア
    clear_stop(root)
    print(f"STOP flag cleared. is_stop_requested: {is_stop_requested(root)}")

    # 部分結果が残っているか確認
    has_partial = len(chunk_results) > 0 and len(text.strip()) > 0
    print(f"Partial results preserved: {has_partial}")

    return {
        "chunks_processed": len(chunk_results),
        "partial_transcript_len": len(text),
        "elapsed_sec": round(elapsed, 3),
        "partial_preserved": has_partial,
    }


def check_stop_flags():
    """古いSTOPフラグの存在をチェックし、警告を出す."""
    root = resolve_project_root()
    runtime_stop = root / "runtime" / "STOP"
    output_stop = root / "output" / "STOP"

    warnings = []
    if runtime_stop.exists():
        warnings.append(f"Found existing STOP flag: {runtime_stop}")
    if output_stop.exists():
        warnings.append(f"Found existing STOP flag: {output_stop}")

    if warnings:
        print("\n[WARNING] Existing STOP flags detected:")
        for w in warnings:
            print(f"  {w}")
        print("  Use --clear-stop to remove them before running.")
    else:
        print("\nNo existing STOP flags found.")

    return warnings


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="M6 STT Benchmark")
    parser.add_argument("--clear-stop", action="store_true",
                        help="Clear existing STOP flags before running")
    parser.add_argument("--test-killswitch", action="store_true",
                        help="Run killswitch test after benchmark")
    args = parser.parse_args()

    # STOPフラグチェック
    warnings = check_stop_flags()
    if args.clear_stop:
        root = resolve_project_root()
        clear_stop(root)
        print("STOP flags cleared.")

    if warnings and not args.clear_stop:
        print("Proceeding with existing STOP flags (may cause immediate abort).")
        print("Re-run with --clear-stop to clear them first.")

    # ベンチマーク実行
    results = run_benchmark()

    # キルスイッチテスト
    if args.test_killswitch:
        ks_result = test_killswitch()
        results["killswitch_test"] = ks_result
        # 再保存
        out_path = Path(__file__).parent.parent / "logs" / "bench_m6_results.json"
        out_path.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"\nUpdated results saved to {out_path}")

    print("\n=== M6 Benchmark Complete ===")