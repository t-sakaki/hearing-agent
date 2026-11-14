#!/bin/bash
# M7 マイクテスト 一気通貫スクリプト
# 流れ: 録音 N秒 → バッチSTT（用語ヒント標準の transcribe()） → 文字起こしと所要秒表示 →
#       Gemini無料でドラフト → 承認ゲート（M4 と同じ run_gate） → 承認時のみ edge-tts
#
# 用法: ./scripts/run_m7_mic.sh [オプション]
#   --seconds N      録音秒数（既定 20、最大20）
#   --input-wav PATH 既存WAVを使う（録音スキップ）
#   --stdin          非対話モード（stdin プロトコルで承認入力を受け取る）
#   --clear-stop     古い STOP フラグを削除してから実行
#   --device NAME    Windows側マイクデバイス名（既定 "Microphone Array (AMD Audio Device)"）
#   --no-tts         TTSをスキップ（承認ゲートまで）
#   --help           このヘルプを表示

set -euo pipefail

PROJECT_ROOT="/mnt/c/Users/taira/hearing-agent"
VENV_PYTHON="/home/taira/hearing-agent-venv/bin/python"
STEP_PY="$PROJECT_ROOT/scripts/run_m7_step.py"

SECONDS_ARG=20
INPUT_WAV=""
USE_STDIN=false
CLEAR_STOP=false
DEVICE_NAME="Microphone Array (AMD Audio Device)"
NO_TTS=false

# 引数パース
while [[ $# -gt 0 ]]; do
    case $1 in
        --seconds)
            SECONDS_ARG="$2"
            shift 2
            ;;
        --input-wav)
            INPUT_WAV="$2"
            shift 2
            ;;
        --stdin)
            USE_STDIN=true
            shift
            ;;
        --clear-stop)
            CLEAR_STOP=true
            shift
            ;;
        --device)
            DEVICE_NAME="$2"
            shift 2
            ;;
        --no-tts)
            NO_TTS=true
            shift
            ;;
        --help)
            sed -n '2,18p' "$0" | sed 's/^# //'
            exit 0
            ;;
        -*)
            echo "Unknown option: $1" >&2
            exit 1
            ;;
        *)
            echo "Unexpected argument: $1" >&2
            exit 1
            ;;
    esac
done

# 20秒上限チェック
if [[ $SECONDS_ARG -gt 20 ]]; then
    echo "Error: 最大20秒までです (指定: $SECONDS_ARG 秒)" >&2
    exit 1
fi

# STOPフラグチェック・クリア
RUNTIME_DIR="$PROJECT_ROOT/runtime"
OUTPUT_DIR="$PROJECT_ROOT/output"
RUNTIME_STOP="$RUNTIME_DIR/STOP"
OUTPUT_STOP="$OUTPUT_DIR/STOP"
mkdir -p "$RUNTIME_DIR" "$OUTPUT_DIR"

if [[ -f "$RUNTIME_STOP" || -f "$OUTPUT_STOP" ]]; then
    echo "[WARNING] Existing STOP flag(s) detected:"
    [[ -f "$RUNTIME_STOP" ]] && echo "  $RUNTIME_STOP"
    [[ -f "$OUTPUT_STOP" ]] && echo "  $OUTPUT_STOP"
    if [[ "$CLEAR_STOP" == "true" ]]; then
        echo "Clearing STOP flags (--clear-stop specified)..."
        rm -f "$RUNTIME_STOP" "$OUTPUT_STOP"
    else
        echo "Use --clear-stop to remove them before running."
        echo "Aborting (STOP flag would cause immediate kill)."
        exit 1
    fi
    echo ""
fi

cd "$PROJECT_ROOT"

# 環境変数読み込み（LLM/API 呼び出し前に必要）。キー値は表示しない。
source "$PROJECT_ROOT/scripts/load_env.sh"

# タイムスタンプ（JST）
TS=$(TZ=Asia/Tokyo date +%Y%m%d_%H%M%S)
LOG_DIR="$PROJECT_ROOT/logs"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/run_m7_${TS}.log"

json_get() {
    # $1=json path, $2=key。値は1行に正規化せず、改行を含む場合はそのまま出す。
    "$VENV_PYTHON" -c '
import json, sys
obj = json.load(open(sys.argv[1], encoding="utf-8"))
val = obj.get(sys.argv[2])
if val is None:
    sys.exit(0)
if isinstance(val, bool):
    print("true" if val else "false")
elif isinstance(val, float):
    print(repr(val) if val != int(val) else str(val))
else:
    sys.stdout.write(str(val))
' "$1" "$2"
}

# ログ関数（複数行もそのまま記録）
log() {
    local timestamp
    timestamp=$(TZ=Asia/Tokyo date '+%Y-%m-%dT%H:%M:%S%z')
    # 先頭行にタイムスタンプ。2行目以降はそのまま。
    {
        printf '[%s] ' "$timestamp"
        printf '%s\n' "$1"
    } | tee -a "$LOG_FILE"
}

redact_and_log() {
    # 失敗時の標準エラーをログへ。キーらしい行は出さない。
    grep -v -E '(API_KEY|api_key|key=|token=|sk-[A-Za-z0-9]|AIza)' || true
}

log "=== M7 Microphone Test Started ==="
log "Project: $PROJECT_ROOT"
log "Seconds: $SECONDS_ARG"
log "Device:  $DEVICE_NAME"
log "Stdin:   $USE_STDIN"
log "No-TTS:  $NO_TTS"

# 録音ステップ
if [[ -n "$INPUT_WAV" ]]; then
    if [[ ! -f "$INPUT_WAV" ]]; then
        log "[ERROR] Input WAV not found: $INPUT_WAV"
        exit 1
    fi
    WAV_PATH="$INPUT_WAV"
    log "Using existing WAV: $WAV_PATH"
else
    WAV_PATH="$PROJECT_ROOT/data/mic/mic_${TS}.wav"
    log "Recording $SECONDS_ARG seconds to $WAV_PATH ..."

    REC_START=$(date +%s.%N)
    if ! bash "$PROJECT_ROOT/scripts/record_mic.sh" "$SECONDS_ARG" "$WAV_PATH" --device "$DEVICE_NAME"; then
        log "[ERROR] Recording failed"
        exit 1
    fi
    REC_END=$(date +%s.%N)
    REC_DUR=$(echo "$REC_END - $REC_START" | bc)
    log "Recording completed in ${REC_DUR}s"
fi

STT_JSON="$RUNTIME_DIR/m7_stt_${TS}.json"
STT_TXT="$RUNTIME_DIR/m7_transcript_${TS}.txt"
DRAFT_JSON="$RUNTIME_DIR/m7_draft_${TS}.json"
DRAFT_TXT="$RUNTIME_DIR/m7_draft_${TS}.txt"
GATE_JSON="$RUNTIME_DIR/m7_gate_${TS}.json"
FINAL_TXT="$RUNTIME_DIR/m7_final_${TS}.txt"
TTS_JSON="$RUNTIME_DIR/m7_tts_${TS}.json"

# STTステップ（バッチ・用語ヒント標準）
log "Starting batch STT (with terms)..."
STT_START=$(date +%s.%N)
STT_ERR=$(mktemp)
set +e
"$VENV_PYTHON" "$STEP_PY" stt --wav "$WAV_PATH" --out-json "$STT_JSON" --out-text "$STT_TXT" 2>"$STT_ERR"
STT_RC=$?
set -e
STT_END=$(date +%s.%N)
STT_DUR=$(echo "$STT_END - $STT_START" | bc)

if [[ $STT_RC -ne 0 || ! -s "$STT_TXT" ]]; then
    log "[ERROR] STT failed"
    redact_and_log < "$STT_ERR" | tee -a "$LOG_FILE"
    rm -f "$STT_ERR"
    exit 1
fi
rm -f "$STT_ERR"

TRANSCRIPT=$(cat "$STT_TXT")
STT_ELAPSED=$(json_get "$STT_JSON" elapsed)
STT_MODEL=$(json_get "$STT_JSON" model)

log "STT completed: model=$STT_MODEL elapsed=${STT_ELAPSED}s"
log "Transcript: $TRANSCRIPT"

echo ""
echo "=== 文字起こし結果 ==="
echo "$TRANSCRIPT"
echo ""
echo "STT所要時間: ${STT_ELAPSED}s (model: $STT_MODEL)"
echo ""

# LLMドラフト生成（Gemini無料）。全文をファイルへ。
log "Generating draft via Gemini (free)..."
LLM_START=$(date +%s.%N)
DRAFT_ERR=$(mktemp)
set +e
"$VENV_PYTHON" "$STEP_PY" draft --transcript-file "$STT_TXT" --out-json "$DRAFT_JSON" --out-text "$DRAFT_TXT" 2>"$DRAFT_ERR"
DRAFT_RC=$?
set -e
LLM_END=$(date +%s.%N)
LLM_DUR=$(echo "$LLM_END - $LLM_START" | bc)

if [[ $DRAFT_RC -ne 0 || ! -s "$DRAFT_TXT" ]]; then
    log "[ERROR] LLM draft generation failed"
    redact_and_log < "$DRAFT_ERR" | tee -a "$LOG_FILE"
    rm -f "$DRAFT_ERR"
    exit 1
fi
rm -f "$DRAFT_ERR"

DRAFT=$(cat "$DRAFT_TXT")
LLM_PROVIDER=$(json_get "$DRAFT_JSON" provider)
LLM_MODEL=$(json_get "$DRAFT_JSON" model)
LLM_LATENCY=$(json_get "$DRAFT_JSON" latency)

log "Draft generated: provider=$LLM_PROVIDER model=$LLM_MODEL latency=${LLM_LATENCY}s"
log "Draft (full, also at $DRAFT_TXT):"
{
    printf '[%s] ' "$(TZ=Asia/Tokyo date '+%Y-%m-%dT%H:%M:%S%z')"
    echo "----- BEGIN DRAFT -----"
    cat "$DRAFT_TXT"
    echo
    echo "----- END DRAFT -----"
} | tee -a "$LOG_FILE"

echo ""
echo "=== ドラフト（審理員向け要点整理） ==="
cat "$DRAFT_TXT"
echo ""
echo ""

# 承認ゲート（M4 と同じ src.approval.run_gate）
DECISION_TIMESTAMP=$(TZ=Asia/Tokyo date '+%Y-%m-%dT%H:%M:%S%z')
GATE_ERR=$(mktemp)
GATE_ARGS=("$VENV_PYTHON" "$STEP_PY" gate --draft-file "$DRAFT_TXT" --out-json "$GATE_JSON" --final-text-file "$FINAL_TXT" --timeout 120)
if [[ "$USE_STDIN" == "true" ]]; then
    log "Running approval gate (stdin mode, via src.approval.run_gate)..."
    GATE_ARGS+=(--stdin)
else
    log "Running approval gate (interactive mode, via src.approval.run_gate)..."
fi

set +e
"${GATE_ARGS[@]}" 2>"$GATE_ERR"
GATE_RC=$?
set -e

if [[ $GATE_RC -ne 0 || ! -f "$GATE_JSON" ]]; then
    log "[ERROR] Approval gate failed"
    redact_and_log < "$GATE_ERR" | tee -a "$LOG_FILE"
    rm -f "$GATE_ERR"
    exit 1
fi
rm -f "$GATE_ERR"

DECISION=$(json_get "$GATE_JSON" decision)
EDITED=$(json_get "$GATE_JSON" edited)
log "Gate decision: $DECISION"
if [[ -s "$FINAL_TXT" ]]; then
    log "Final text (full, also at $FINAL_TXT):"
    {
        echo "----- BEGIN FINAL TEXT -----"
        cat "$FINAL_TXT"
        echo
        echo "----- END FINAL TEXT -----"
    } | tee -a "$LOG_FILE"
fi

# TTSステップ（承認時のみ、final_text ファイルの全文を使う）
TTS_PATH="no_tts"
TTS_TIMESTAMP=""
TTS_DUR="0"

if [[ "$DECISION" == "approve" || "$DECISION" == "edit_approve" ]] && [[ "$NO_TTS" != "true" ]]; then
    if [[ ! -s "$FINAL_TXT" ]]; then
        log "[ERROR] Approved but final text is empty; skipping TTS"
        TTS_PATH="tts_failed"
    else
        log "Generating TTS (edge-tts) from full final text..."
        TTS_START=$(date +%s.%N)
        TTS_OUT="$OUTPUT_DIR/m7_approved_${TS}.mp3"
        TTS_ERR=$(mktemp)
        set +e
        "$VENV_PYTHON" "$STEP_PY" tts --text-file "$FINAL_TXT" --out-mp3 "$TTS_OUT" --out-json "$TTS_JSON" 2>"$TTS_ERR"
        TTS_RC=$?
        set -e
        TTS_END=$(date +%s.%N)
        TTS_DUR=$(echo "$TTS_END - $TTS_START" | bc)
        if [[ $TTS_RC -eq 0 && -f "$TTS_OUT" ]]; then
            TTS_PATH="$TTS_OUT"
            TTS_TIMESTAMP=$(TZ=Asia/Tokyo date '+%Y-%m-%dT%H:%M:%S%z')
            log "TTS generated: $TTS_PATH (${TTS_DUR}s)"
        else
            log "[ERROR] TTS failed"
            redact_and_log < "$TTS_ERR" | tee -a "$LOG_FILE"
            TTS_PATH="tts_failed"
        fi
        rm -f "$TTS_ERR"
    fi
else
    if [[ "$NO_TTS" == "true" ]]; then
        log "TTS skipped (--no-tts)"
    else
        log "TTS skipped (decision: $DECISION)"
    fi
fi

# 総合ログ書き出し（M7形式）
{
    echo ""
    echo "=== SUMMARY ==="
    echo "timestamp_jst: $(TZ=Asia/Tokyo date '+%Y-%m-%dT%H:%M:%S%z')"
    echo "wav_path: $WAV_PATH"
    echo "rec_sec: ${REC_DUR:-0}"
    echo "stt_model: $STT_MODEL"
    echo "stt_sec: $STT_ELAPSED"
    echo "transcript: $TRANSCRIPT"
    echo "provider: $LLM_PROVIDER"
    echo "model: $LLM_MODEL"
    echo "llm_sec: $LLM_LATENCY"
    echo "draft_file: $DRAFT_TXT"
    echo "draft:"
    cat "$DRAFT_TXT"
    echo
    echo "decision: $DECISION"
    echo "edited: $EDITED"
    echo "decision_timestamp_jst: $DECISION_TIMESTAMP"
    echo "final_text_file: $FINAL_TXT"
    echo "tts_path: $TTS_PATH"
    echo "tts_sec: $TTS_DUR"
    echo "tts_timestamp_jst: ${TTS_TIMESTAMP:-}"
} >> "$LOG_FILE"

# 追記ログ
M7_LOG="$LOG_DIR/m7.log"
{
    echo "[$(TZ=Asia/Tokyo date '+%Y-%m-%dT%H:%M:%S%z')] decision=$DECISION tts=$TTS_PATH rec=${REC_DUR:-0}s stt=$STT_ELAPSED llm=$LLM_LATENCY tts=${TTS_DUR}"
    echo "  TRANSCRIPT: ${TRANSCRIPT:0:200}"
    echo "  DRAFT_FILE: $DRAFT_TXT"
} >> "$M7_LOG"

echo ""
echo "=== M7 Complete ==="
echo "Log: $LOG_FILE"
echo "Decision: $DECISION"
echo "TTS: $TTS_PATH"
echo "Draft file: $DRAFT_TXT"
echo ""

# STOPフラグが立っていれば警告
if [[ -f "$RUNTIME_STOP" || -f "$OUTPUT_STOP" ]]; then
    echo "[NOTE] STOP flag is set (runtime/STOP or output/STOP)."
fi

exit 0
