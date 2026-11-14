#!/usr/bin/env bash
# ~/.hermes/.env から必要なキーのみを安全に抽出して export する。
# 全体 source は行値の特殊文字で壊れるため禁止。キー値は標準出力に表示しない。
#
# 使い方: source scripts/load_env.sh   (run_m1.sh から source される)

ENV_FILE="${HERMES_ENV_FILE:-/home/taira/.hermes/.env}"

if [[ ! -r "${ENV_FILE}" ]]; then
    echo "env ファイルを読めません: ${ENV_FILE}" >&2
    return 1 2>/dev/null || exit 1
fi

# Python で行を解析し、シェル安全な export 文だけを出力して eval する。
# 値そのものは画面に出力しない。
eval "$(
    python3 - "${ENV_FILE}" <<'PY'
import shlex
import sys
from pathlib import Path

wanted = {"GEMINI_API_KEY_OPENCODE", "NOUS_API_KEY"}
env_path = Path(sys.argv[1])

for raw in env_path.read_text(encoding="utf-8").splitlines():
    line = raw.strip()
    if not line or line.startswith("#") or "=" not in line:
        continue
    key, value = line.split("=", 1)
    key = key.strip()
    if key not in wanted:
        continue
    value = value.strip().strip('"').strip("'")
    print(f"export {key}={shlex.quote(value)}")
PY
)"
