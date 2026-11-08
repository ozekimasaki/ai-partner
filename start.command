#!/bin/sh
# ダブルクリックで ai-partner を起動する（Mac）
cd "$(dirname "$0")" || exit 1
exec python3 start.py "$@"
