#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

if [ ! -d ".venv" ]; then
  python3 -m venv .venv
fi

. .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt

if [ ! -f ".env" ]; then
  cp .env.example .env
  echo "已生成 .env，请填写密钥后重新运行脚本。"
  echo "需要填写：DASHSCOPE_API_KEY, TUSHARE_TOKEN"
  exit 1
fi

python backend/app.py

