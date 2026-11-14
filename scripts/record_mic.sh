#!/bin/bash
# M7 マイク録音 WSL ラッパー（PowerShell 経由で DirectShow、Pulse/RDPSource フォールバック付き・タイムアウトあり）
# 用法: ./scripts/record_mic.sh [秒数] [出力パス] [--device デバイス名]
#   秒数: 既定 20（最大20秒）
#   出力パス: 既定 data/mic/mic_<YYYYMMDD_HHMMSS>.wav（JST）
#   --device: Windows側デバイス名（既定 "Microphone Array (AMD Audio Device)"）

set -euo pipefail

PROJECT_ROOT="/mnt/c/Users/taira/hearing-agent"

SECONDS_ARG=20
OUTPUT_PATH=""
DEVICE_NAME="Microphone Array (AMD Audio Device)"

# 引数パース
while [[ $# -gt 0 ]]; do
    case $1 in
        --device)
            DEVICE_NAME="$2"
            shift 2
            ;;
        -*)
            echo "Unknown option: $1" >&2
            exit 1
            ;;
        *)
            if [[ "$1" =~ ^[0-9]+$ ]]; then
                SECONDS_ARG="$1"
            else
                OUTPUT_PATH="$1"
            fi
            shift
            ;;
    esac
done

# 20秒上限チェック
if [[ $SECONDS_ARG -gt 20 ]]; then
    echo "Error: 最大20秒までです (指定: $SECONDS_ARG 秒)" >&2
    exit 1
fi

# 出力パス決定
if [[ -z "$OUTPUT_PATH" ]]; then
    TS=$(TZ=Asia/Tokyo date +%Y%m%d_%H%M%S)
    OUTPUT_PATH="$PROJECT_ROOT/data/mic/mic_${TS}.wav"
fi

# data/mic ディレクトリ作成
mkdir -p "$(dirname "$OUTPUT_PATH")"

echo "=== M7 Mic Record (WSL Wrapper) ==="
echo "Project:     $PROJECT_ROOT"
echo "Seconds:     $SECONDS_ARG"
echo "Output:      $OUTPUT_PATH"
echo "Device:      $DEVICE_NAME"
echo ""

# Windows側パスに変換（PowerShellスクリプトへ渡す用）
WIN_OUTPUT_PATH=$(wslpath -w "$OUTPUT_PATH")
PS_SCRIPT=$(wslpath -w "$PROJECT_ROOT/scripts/record_mic.ps1")

record_windows_via_ps() {
    local dev="$1"
    local sec="$2"
    local win_out="$3"
    
    echo "[Windows] Recording via PowerShell -> DirectShow..."
    powershell.exe -NoProfile -ExecutionPolicy Bypass -File "$PS_SCRIPT" \
        -Seconds "$sec" \
        -OutputPath "$win_out" \
        -DeviceName "$dev"
}

record_wsl_pulse() {
    local sec="$1"
    local out="$2"
    local timeout_sec=$((sec + 10))
    
    echo "[WSL] Recording via PulseAudio (RDPSource) with ${timeout_sec}s timeout..."
    timeout "$timeout_sec" ffmpeg -y -f pulse -i "RDPSource" -t "$sec" -ar 16000 -ac 1 -c:a pcm_s16le "$out"
}

# 録音実行（Windows経由を主経路とする）
success=false
if record_windows_via_ps "$DEVICE_NAME" "$SECONDS_ARG" "$WIN_OUTPUT_PATH"; then
    # PowerShell 成功でもファイル確認（終了コード0でも失敗することがあるため）
    if [[ -f "$OUTPUT_PATH" && -s "$OUTPUT_PATH" ]]; then
        success=true
    else
        echo "[WARNING] PowerShell exited 0 but output file missing/empty, trying WSL PulseAudio fallback..."
    fi
else
    echo "[WARNING] Windows DirectShow recording failed, trying WSL PulseAudio fallback..."
fi

if [[ "$success" != "true" ]]; then
    if record_wsl_pulse "$SECONDS_ARG" "$OUTPUT_PATH"; then
        success=true
    else
        echo "[ERROR] Both Windows and WSL recording failed" >&2
        exit 1
    fi
fi

# 結果確認
if [[ -f "$OUTPUT_PATH" && -s "$OUTPUT_PATH" ]]; then
    SIZE=$(stat -c%s "$OUTPUT_PATH")
    echo ""
    echo "=== Recording Complete ==="
    echo "File: $OUTPUT_PATH"
    echo "Size: $SIZE bytes"
    exit 0
else
    echo "[ERROR] Output file not created or empty" >&2
    exit 1
fi