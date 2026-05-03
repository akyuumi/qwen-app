# Qwen Local Agent

ローカルの Ollama/Qwen と Docker サンドボックスを使う最小構成の AI エージェントです。

## 機能

- FastAPI によるチャット API
- Ollama `/api/chat` 連携
- プロファイル編集（model / Ollama URL / system prompt）
- Docker 隔離での `run_python`
- SQLite への実行履歴保存
- 静的 Web UI

## 前提

- Python 3.11+
- Docker
- Ollama と Qwen 系モデル

例:

```powershell
ollama pull qwen2.5-coder
```

## セットアップ

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
docker pull python:3.11-slim
```

## 起動

```powershell
uvicorn app.main:app --reload
```

ブラウザで `http://127.0.0.1:8000` を開きます。

## API

- `POST /api/chat` `{ "text": "..." }`
- `POST /api/run-python` `{ "code": "print('hello')" }`
- `GET /api/executions`
- `GET /api/profile`
- `PUT /api/profile`

## セキュリティ方針

`run_python` は AST による最低限の危険構文検知を行ったうえで、次の Docker オプションで 1 リクエスト 1 コンテナとして実行します。

```bash
--rm
--network none
--memory 512m
--cpus 1
--pids-limit 100
--read-only
--security-opt no-new-privileges
--tmpfs /tmp:rw,nosuid,nodev,size=64m
```

完全防御ではありません。LLM 出力と生成コードは常に非信頼入力として扱います。
# qwen-app
