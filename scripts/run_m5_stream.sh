#!/bin/bash
# M6 逐次STT 実行スクリプト（M5から改善: 重複除去・高速化・STOPフラグチェック）
# 使い方: ./scripts/run_m5_stream.sh [--clear-stop] [音声ファイルパス]

set -euo pipefail

PROJECT_ROOT="/mnt/c/Users/taira/hearing-agent"
VENV_PYTHON="/home/taira/hearing-agent-venv/bin/python"
AUDIO_FILE="$PROJECT_ROOT/data/dummy_question.wav"
CLEAR_STOP=false

# 引数パース
while [[ $# -gt 0 ]]; do
    case $1 in
        --clear-stop)
            CLEAR_STOP=true
            shift
            ;;
        -*)
            echo "Unknown option: $1" >&2
            exit 1
            ;;
        *)
            AUDIO_FILE="$1"
            shift
            ;;
    esac
done

echo "=== M6 Streaming STT ==="
echo "Project: $PROJECT_ROOT"
echo "Audio:   $AUDIO_FILE"
echo "Venv:    $VENV_PYTHON"
echo

cd "$PROJECT_ROOT"

# STOPフラグチェック
RUNTIME_STOP="$PROJECT_ROOT/runtime/STOP"
OUTPUT_STOP="$PROJECT_ROOT/output/STOP"

if [[ -f "$RUNTIME_STOP" || -f "$OUTPUT_STOP" ]]; then
    echo "[WARNING] Existing STOP flag(s) detected:"
    [[ -f "$RUNTIME_STOP" ]] && echo "  $RUNTIME_STOP"
    [[ -f "$OUTPUT_STOP" ]] && echo "  $OUTPUT_STOP"
    if [[ "$CLEAR_STOP" == "true" ]]; then
        echo "Clearing STOP flags (--clear-stop specified)..."
        rm -f "$RUNTIME_STOP" "$OUTPUT_STOP"
    else
        echo "Use --clear-stop to remove them before running."
        echo "Proceeding anyway (will abort immediately at first chunk)..."
    fi
    echo
fi

# 仮想環境の Python で実行
"$VENV_PYTHON" -m src.stt_stream "$AUDIO_FILE"

echo
echo "=== Done ==="