#!/usr/bin/env bash
set -euo pipefail

# プロジェクトルートへ移動
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${PROJECT_ROOT}"

# 環境変数読み込み（必要なキーのみ、安全に抽出。全体 source は禁止）
# shellcheck disable=SC1091
source "${SCRIPT_DIR}/load_env.sh"

# venv の python を使用
PYTHON="${PROJECT_ROOT}/.venv/bin/python"
if [[ ! -x "${PYTHON}" ]]; then
  echo "venv が見つかりません: ${PYTHON}" >&2
  exit 1
fi

exec "${PYTHON}" "${PROJECT_ROOT}/scripts/run_m1_text_draft.py"
