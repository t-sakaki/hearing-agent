#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${PROJECT_ROOT}"

source "${SCRIPT_DIR}/load_env.sh"

PYTHON="/home/taira/hearing-agent-venv/bin/python"
if [[ ! -x "${PYTHON}" ]]; then
  PYTHON="${PROJECT_ROOT}/.venv/bin/python"
fi
if [[ ! -x "${PYTHON}" ]]; then
  echo "python が見つかりません" >&2
  exit 1
fi

# デフォルトは対話/自動判定。stdin を渡したい場合は run_m3_gate.py --stdin を直接使う。
exec "${PYTHON}" "${PROJECT_ROOT}/scripts/run_m3_gate.py" "$@"