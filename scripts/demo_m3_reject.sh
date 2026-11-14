#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${PROJECT_ROOT}"
PYTHON="/home/taira/hearing-agent-venv/bin/python"
[[ -x "${PYTHON}" ]] || PYTHON="${PROJECT_ROOT}/.venv/bin/python"
printf 'reject\n' | "${PYTHON}" "${PROJECT_ROOT}/scripts/run_m3_gate.py" --stdin