# Architecture

## Overview

Parking Judge は3つのコンポーネントで構成されるローカルアプリです。

```
┌─────────────────┐   ┌──────────────┐
│  Chrome Extension│   │   Web UI     │
│  (Manifest V3)  │   │ (React + TS) │
└────────┬────────┘   └──────┬───────┘
         │                    │
         └────────┬───────────┘
                  │ HTTP (localhost:8787)
                  ▼
         ┌────────────────────────────────┐
         │     FastAPI Backend            │
         │                                │
         │  ┌──────────────────────────┐  │
         │  │ /api/analyze             │  │
         │  │   → Place Resolution     │  │
         │  │   → Data Collection      │  │
         │  │   → Rule-based Judgment  │  │
         │  │   → Cache & Respond      │  │
         │  └──────────────────────────┘  │
         │                                │
         │  Sources:                      │
         │  ├── Google Places API (New)   │
         │  ├── Official Site Scraper     │
         │  └── Nearby Parking Search     │
         │                                │
         │  Judge:                        │
         │  ├── Rule Engine (primary)     │
         │  └── LLM Judge (optional)      │
         │                                │
         │  Storage:                      │
         │  └── SQLite                    │
         └────────────────────────────────┘
```

## Design Principles

1. **AI に全部やらせない**: まず機械的に取れる事実を集め、ルールベースで判定。曖昧なときだけ LLM を使う
2. **Chrome 拡張は軽く保つ**: DOM からの情報抽出と API 呼び出しのみ
3. **ローカルバックエンドが本体**: データ収集・正規化・キャッシュ・判定をすべて担当
4. **unknown を恐れない**: 情報不足時は confident に wrong ではなく unknown を返す

## Backend Structure

```
backend/app/
├── api/          # FastAPI endpoints
├── core/         # Config, settings
├── db/           # SQLAlchemy setup
├── judge/        # Verdict engine (rule-based + LLM)
├── models/       # SQLAlchemy ORM models
├── schemas/      # Pydantic request/response schemas
├── services/     # Business logic orchestration
├── sources/      # Data source adapters
└── utils/        # Geo calculations, place key normalization
```

## Data Flow

1. ユーザーが店名/住所/URL を入力
2. place_key で正規化・キャッシュ照合
3. キャッシュミスなら:
   a. Google Places API で店舗情報取得
   b. 公式サイトから駐車場文言を抽出
   c. 近隣駐車場を検索
   d. ルールベースエンジンで判定
   e. SQLite に保存
4. レスポンスを返却

## Judgment Categories

| Verdict | 意味 |
|---------|------|
| onsite | 店専用または施設併設の駐車場あり |
| partner | 提携駐車場あり |
| nearby_only | 店専用なし、近隣コインパーキング前提 |
| unknown | 判断材料不足 |
| avoid | 駐車条件が厳しい |

## Vehicle Fit

| Fit | 意味 |
|-----|------|
| easy | 余裕をもって駐車可能 |
| ok | 問題なし |
| tight | 狭い可能性あり |
| unknown | 情報不足 |
| avoid | 車サイズが制限を超過 |
