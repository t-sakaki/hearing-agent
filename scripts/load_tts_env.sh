#!/usr/bin/env bash
# 既存キーをシェルのメモリーへ読み込む。値を表示・ファイル保存しない。
if [[ -n "${GEMINI_TTS_API_KEY:-}" ]]; then return 0 2>/dev/null || exit 0; fi
TTS_ENV_SOURCE="${CIVIC_TTS_ENV_FILE:-/home/taira/civic-lens/.env}"
if [[ ! -r "$TTS_ENV_SOURCE" ]]; then
  echo "参考プロジェクトのTTSキーを読み込めません。Edge TTSを使用できます。" >&2
  return 1 2>/dev/null || exit 1
fi
eval "$(python3 - "$TTS_ENV_SOURCE" <<'PY'
import shlex,sys
from pathlib import Path
for raw in Path(sys.argv[1]).read_text(encoding='utf-8').splitlines():
    if '=' not in raw or raw.lstrip().startswith('#'):continue
    key,value=raw.split('=',1)
    if key.strip()=='GEMINI_API_KEY':
        value=value.strip().strip('"').strip("'")
        if value:print('export GEMINI_TTS_API_KEY='+shlex.quote(value))
        break
PY
)"
unset TTS_ENV_SOURCE
