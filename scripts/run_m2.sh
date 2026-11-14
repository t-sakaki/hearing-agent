#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${PROJECT_ROOT}"

# 環境変数読み込み（必要なキーのみ）
# shellcheck disable=SC1091
source "${SCRIPT_DIR}/load_env.sh"

# WSL ネイティブ venv を優先（/mnt/c 上の venv が遅い場合の回避）
PYTHON="/home/taira/hearing-agent-venv/bin/python"
if [[ ! -x "${PYTHON}" ]]; then
  PYTHON="${PROJECT_ROOT}/.venv/bin/python"
fi
if [[ ! -x "${PYTHON}" ]]; then
  echo "python が見つかりません" >&2
  exit 1
fi

# ダミー WAV 生成（存在しなければ・毎回再生成して最新を保つ）
"${PYTHON}" "${PROJECT_ROOT}/scripts/make_dummy_wav.py"

exec "${PYTHON}" "${PROJECT_ROOT}/scripts/run_m2_wav_draft.py"