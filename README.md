# Parking Judge (park-and-go)

店舗の駐車しやすさを判定するローカルアプリ。Google Maps で見ている店舗について、駐車場の有無・種類・車サイズ適合を推定します。

## できること

- Google Places API から店舗基本情報・駐車場情報を取得
- 公式サイトから駐車場関連の文言を自動抽出
- 近隣駐車場を検索して距離・徒歩時間を算出
- ルールベースで判定 (onsite / partner / nearby_only / unknown / avoid)
- 車サイズ適合判定 (easy / ok / tight / unknown / avoid)
- SQLite でキャッシュ (再取得不要)
- Chrome 拡張で Google Maps 上から直接利用
- Web UI (スマホ対応) でも利用可能

## できないこと (現時点)

- 満空情報のリアルタイム取得
- 画像認識による駐車場判定
- 食べログ等の外部サイトスクレイピング
- ユーザー認証・マルチユーザー
- クラウドデプロイ

## アーキテクチャ

```
Chrome拡張 / Web UI
        │
        ▼
  FastAPI Backend (localhost:8787)
   ├── Google Places API (店舗情報・近隣駐車場)
   ├── 公式サイトスクレイピング (駐車場文言抽出)
   ├── ルールベース判定エンジン
   ├── LLM統合 (オプション、デフォルトOFF)
   └── SQLite キャッシュ
```

詳細: [docs/architecture.md](docs/architecture.md)

## セットアップ

### 前提

- Python 3.12+
- Node.js 18+
- Google Maps API Key (Places API (New) を有効化)

### 1. Google API Key の設定

1. [Google Cloud Console](https://console.cloud.google.com/) でプロジェクトを作成
2. Places API (New) を有効化
3. API Key を作成

### 2. 環境変数

```bash
cp .env.example .env
# .env を編集して GOOGLE_MAPS_API_KEY を設定
```

### 3. バックエンド起動

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
uvicorn app.main:app --host 127.0.0.1 --port 8787 --reload
```

ヘルスチェック: http://127.0.0.1:8787/api/health

### 4. Web UI 起動

```bash
cd web
npm install
npm run dev
```

ブラウザで http://localhost:5173 を開く

### 5. Chrome 拡張の読み込み

1. Chrome で `chrome://extensions` を開く
2. 「デベロッパーモード」を ON
3. 「パッケージ化されていない拡張機能を読み込む」で `extension/` ディレクトリを選択
4. Google Maps で店舗ページを開き、拡張アイコンをクリック

### 6. Tailscale Serve でスマホからアクセス

```bash
# バックエンド
tailscale serve --bg --set-path /api http://127.0.0.1:8787

# Web UI
tailscale serve --bg --set-path / http://127.0.0.1:5173
```

スマホからは `https://<your-machine>.tailnet-xxx.ts.net/` でアクセス。

## テスト

```bash
cd backend
source .venv/bin/activate
python -m pytest tests/ -v
```

## API

詳細: [docs/api.md](docs/api.md)

| Method | Path | 説明 |
|--------|------|------|
| POST | /api/analyze | 店舗の駐車場を判定 |
| GET | /api/place/{place_key} | 解析済み結果を取得 |
| GET | /api/recent | 最近解析した店の一覧 |
| GET | /api/health | ヘルスチェック |
| GET | /api/config | 設定情報 |

## よくあるハマりどころ

- **GOOGLE_MAPS_API_KEY 未設定**: API Key が空だと Google Places 連携がスキップされ、公式サイト抽出・近隣駐車場検索ができません。verdict は unknown 固定になります
- **Places API (New) の有効化**: 旧 Places API ではなく Places API (New) が必要です
- **CORS エラー**: バックエンドが起動していない場合、Web UI / Chrome 拡張からのリクエストが失敗します
- **Chrome 拡張が動かない**: Google Maps のページで使用してください。他のページでは content script が動きません

## 既知の制約

- Google Maps の DOM 構造変更により Chrome 拡張の情報抽出が壊れる可能性あり (URL fallback あり)
- 公式サイトのスクレイピングは最大5ページまで
- ルールベース判定は完璧ではなく、情報不足時は unknown を返す設計
- LLM 統合はインターフェースのみ (NoOp 実装)

## 今後の TODO

- [ ] LLM 統合の実装 (OpenAI / Anthropic / Gemini)
- [ ] Google Maps URL からの place_id 直接解決
- [ ] レビュー文言からの駐車場情報抽出
- [ ] 画像認識による駐車場サイズ推定
- [ ] 判定ルールの YAML/JSON 外部化
- [ ] ユーザーによる判定結果のフィードバック
- [ ] 車サイズプロファイルの Web UI 編集
- [ ] バッチ分析機能
