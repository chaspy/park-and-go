# API Reference

Base URL: `http://127.0.0.1:8787`

## POST /api/analyze

店舗の駐車場情報を解析して判定を返します。

### Request

```json
{
  "google_maps_url": "https://www.google.com/maps/place/...",
  "name": "店舗名",
  "address": "住所",
  "lat": 35.0,
  "lng": 139.0,
  "force_refresh": false
}
```

- `google_maps_url`, `name`, `address` のいずれか1つ以上が必須
- `force_refresh: true` でキャッシュを無視して再解析

### Response

```json
{
  "place_key": "normalized-key",
  "place_name": "店名",
  "address": "住所",
  "location": { "lat": 35.0, "lng": 139.0 },
  "verdict": "nearby_only",
  "confidence": 0.73,
  "vehicle_fit": "tight",
  "summary": "店専用駐車場の明示は確認できませんでしたが...",
  "evidence": [
    {
      "source": "google_places",
      "kind": "parking_option",
      "text": "No parking information from Google Places",
      "weight": 0.1
    }
  ],
  "nearby_parking": [
    {
      "name": "タイムズXX",
      "distance_m": 120,
      "walking_minutes": 2,
      "lat": 35.001,
      "lng": 139.001
    }
  ],
  "fetched_at": "2026-03-22T10:00:00Z"
}
```

### Verdict values

| Value | Description |
|-------|-------------|
| `onsite` | 店専用駐車場あり |
| `partner` | 提携駐車場あり |
| `nearby_only` | 近隣コインパーキング前提 |
| `unknown` | 判断材料不足 |
| `avoid` | 駐車困難 |

### Vehicle fit values

| Value | Description |
|-------|-------------|
| `easy` | 余裕あり |
| `ok` | 問題なし |
| `tight` | 狭い可能性 |
| `unknown` | 情報不足 |
| `avoid` | サイズ超過 |

## GET /api/place/{place_key}

解析済みの結果を取得します。

### Response

POST /api/analyze と同じ形式。

## GET /api/recent?limit=20

最近解析した店の一覧を取得します。

### Query Parameters

| Name | Type | Default | Description |
|------|------|---------|-------------|
| limit | int | 20 | 取得件数 |

### Response

AnalyzeResponse の配列。

## GET /api/health

```json
{ "status": "ok", "service": "parking-judge" }
```

## GET /api/config

```json
{
  "vehicle": {
    "name": "XC40",
    "length_mm": 4440,
    "width_mm": 1875,
    "height_mm": 1655,
    "notes": "default user vehicle"
  },
  "enable_llm": false,
  "llm_provider": ""
}
```
