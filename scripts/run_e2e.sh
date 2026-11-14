#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${PROJECT_ROOT}"

# 環境変数読み込み
# shellcheck disable=SC1091
source "${SCRIPT_DIR}/load_env.sh"

PYTHON="/home/taira/hearing-agent-venv/bin/python"
if [[ ! -x "${PYTHON}" ]]; then
  PYTHON="${PROJECT_ROOT}/.venv/bin/python"
fi
if [[ ! -x "${PYTHON}" ]]; then
  echo "python が見つかりません" >&2
  exit 1
fi

export HEARING_PROJECT_ROOT="${PROJECT_ROOT}"
exec "${PYTHON}" "${PROJECT_ROOT}/scripts/run_m4_e2e.py" "$@"
