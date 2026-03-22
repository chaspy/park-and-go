# Setup Guide

## Prerequisites

- Python 3.12+
- Node.js 18+
- Google Cloud project with Places API (New) enabled
- Google Maps API Key

## Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

### Environment

プロジェクトルートに `.env` を置きます:

```bash
cp .env.example .env
```

`.env` を編集:

```
GOOGLE_MAPS_API_KEY=your-api-key-here
DATABASE_URL=sqlite:///./parking_judge.db
```

### Run

```bash
uvicorn app.main:app --host 127.0.0.1 --port 8787 --reload
```

### Test

```bash
python -m pytest tests/ -v
```

## Web UI

```bash
cd web
npm install
npm run dev
```

http://localhost:5173 でアクセス。

### API Base URL の変更

デフォルトでは `http://127.0.0.1:8787` に接続します。
変更する場合は `web/.env` に以下を設定:

```
VITE_API_BASE=http://your-host:8787
```

## Chrome Extension

1. `chrome://extensions` を開く
2. Developer mode を ON
3. "Load unpacked" で `extension/` を選択
4. Google Maps で店舗ページを開いて拡張アイコンをクリック

## Tailscale Serve (スマホからのアクセス)

Tailscale がインストール済みの前提:

```bash
# Backend API
tailscale serve --bg --set-path /api http://127.0.0.1:8787

# Web UI (Vite dev server)
tailscale serve --bg --set-path / http://127.0.0.1:5173
```

Web UI の `VITE_API_BASE` を Tailscale の HTTPS URL に変更:

```
VITE_API_BASE=https://your-machine.tailnet.ts.net
```

## Production Build (Web UI)

```bash
cd web
npm run build
```

`dist/` ディレクトリの内容を任意の HTTP サーバで配信できます。

## Google API Key の取得方法

1. [Google Cloud Console](https://console.cloud.google.com/) にアクセス
2. プロジェクトを作成 (または既存プロジェクトを選択)
3. APIs & Services > Enable APIs > "Places API (New)" を検索して有効化
4. APIs & Services > Credentials > Create Credentials > API Key
5. API Key に適切な制限を設定 (IP 制限、API 制限)
6. `.env` の `GOOGLE_MAPS_API_KEY` に設定
