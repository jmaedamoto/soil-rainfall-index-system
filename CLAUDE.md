# 土壌雨量指数計算システム

## 概要

気象庁のGRIB2形式データを解析し、土壌雨量指数を計算するWebシステム。
ExcelのVBA実装からPython Flask Web APIに変換したシステム。

### 処理フロー
1. 気象庁GRIB2データ（土壌雨量指数・降水量予測）をダウンロード
2. バイナリデータを解析してグリッド情報を抽出
3. CSVデータ（境界値・土砂災害データ）から地域構造を構築
4. 3段タンクモデルによる土壌雨量指数の時系列計算
5. 都道府県・地域・メッシュ別のリスク評価
6. セッションベースのJSONレスポンスを返却

### 対象地域
関西6府県（26,051メッシュ）：
- 滋賀県 (shiga) 3,307 / 京都府 (kyoto) 4,493 / 大阪府 (osaka) 1,885
- 兵庫県 (hyogo) 8,269 / 奈良県 (nara) 3,480 / 和歌山県 (wakayama) 4,611

## 技術スタック

- **バックエンド**: Python 3.9+ / Flask / NumPy / Pandas
- **フロントエンド**: React 18 / TypeScript / Vite / Leaflet.js / Chart.js
- **データソース**: 気象庁GRIB2データ
- **主要ライブラリ**: requests, numpy, pandas, structlog, leaflet, react-leaflet, axios

## ディレクトリ構造

```
soil-rainfall-index-system/
├── server/
│   ├── app.py                   # Flaskアプリエントリーポイント
│   ├── wsgi.py                  # 本番WSGIエントリーポイント
│   ├── requirements.txt         # Python依存関係
│   ├── config/
│   │   └── app_config.yaml      # GRIB2URL・プロキシ・タイムアウト設定
│   └── src/
│       ├── api/
│       │   ├── controllers/
│       │   │   ├── main_controller.py      # 計算実行API
│       │   │   ├── session_controller.py   # セッション管理API
│       │   │   ├── cache_controller.py     # キャッシュ管理API
│       │   │   └── rainfall_controller.py  # 雨量調整API
│       │   └── routes/
│       │       ├── main_routes.py
│       │       ├── session_routes.py
│       │       ├── cache_routes.py
│       │       └── rainfall_routes.py
│       ├── config/
│       │   └── config_service.py    # 設定ファイル読み込み・URL構築
│       ├── models/
│       │   └── data_models.py       # 全データクラス定義
│       └── services/
│           ├── main_service.py              # メイン処理調整
│           ├── calculation_service.py       # タンクモデル計算（VBA完全再現）
│           ├── calculation_service_numpy.py # NumPy最適化版
│           ├── grib2_service.py             # GRIB2データ解析・ダウンロード
│           ├── data_service.py              # CSV読み込み・メッシュ初期化
│           ├── session_service.py           # セッション管理・フォーク機能
│           ├── cache_service.py             # gzip圧縮キャッシュ・重複計算防止
│           ├── rainfall_adjustment_service.py # 雨量調整計算
│           └── response_builder.py          # APIレスポンス構築
├── client/
│   ├── vite.config.ts           # Vite設定（base: '/dosya/'）
│   ├── package.json
│   └── src/
│       ├── main.tsx             # Reactエントリーポイント（BrowserRouter basename設定）
│       ├── App.tsx              # ルーティング（/ → ProductionSession）
│       ├── config/
│       │   └── apiConfig.ts     # APIベースURL設定
│       ├── types/
│       │   └── api.ts           # 全TypeScriptインターフェース定義
│       ├── services/
│       │   ├── api.ts           # APIクライアント（計算実行）
│       │   └── sessionApi.ts    # セッション管理APIクライアント
│       ├── pages/
│       │   └── ProductionSession.tsx  # メインUI（470行）
│       └── components/
│           ├── CacheInfo.tsx
│           ├── RainfallAdjustmentModalSession.tsx
│           ├── charts/
│           │   └── AreaRiskBarChart.tsx
│           └── map/
│               ├── SoilRainfallMap.tsx    # Leaflet地図（minZoom:8, maxZoom:14）
│               ├── SimpleCanvasLayer.tsx  # Canvasメッシュ描画
│               ├── MapLegend.tsx
│               └── LeafletIcons.ts
```

## バックエンド詳細

### data_models.py（データクラス）
| クラス | 説明 |
|--------|------|
| `BaseInfo` | GRIB2基本情報（初期日時・グリッド数・緯度経度範囲） |
| `SwiTimeSeries` | 土壌雨量指数時系列（ft, value） |
| `GuidanceTimeSeries` | ガイダンス時系列（ft, value） |
| `Risk` | リスクレベル（ft, value: 0-4） |
| `Mesh` | メッシュデータ（コード・緯度経度・基準値・各時系列） |
| `Area` | 市町村データ（Meshリスト・リスクタイムライン） |
| `SecondarySubdivision` | 二次細分区域（Areaリスト・集約タイムライン） |
| `Prefecture` | 都道府県（Area・二次細分・集約データ） |
| `PREFECTURES_MASTER` | 6府県マスターデータ定数 |

### calculation_service.py（タンクモデル計算・VBA完全再現）
**タンクモデルパラメータ（VBA完全同一）:**
`l1=15.0, l2=60.0, l3=15.0, l4=15.0 / a1=0.1, a2=0.15, a3=0.05, a4=0.01 / b1=0.12, b2=0.05, b3=0.01`

| メソッド | 説明 |
|---------|------|
| `get_data_num(lat, lon, base_info)` | 緯度経度→データインデックス変換（VBA完全再現） |
| `calc_tunk_model(s1, s2, s3, t, r)` | タンクモデル計算（3タンク状態更新） |
| `calc_swi_timelapse()` | 3時間ごとSWI計算 |
| `calc_hourly_rain()` | 1時間雨量推定 |
| `calc_swi_hourly()` | 1時間ごとSWI計算 |
| `calc_hourly_risk()` | 1時間ごと危険度判定 |
| `calc_3hour_max_risk_from_hourly()` | 3時間ごと最大危険度（FT=0は初期値として単独処理） |
| `process_mesh_calculations(mesh, swi, guidance)` | 単一メッシュ全計算 |
| `recalculate_swi_and_risk(mesh)` | 雨量調整後再計算 |
| `calc_risk_timeline(meshes)` | エリアリスクタイムライン集約 |
| `calc_secondary_subdivision_aggregates()` | 二次細分集約 |
| `calc_prefecture_aggregates()` | 府県全体集約 |

### grib2_service.py
| メソッド | 説明 |
|---------|------|
| `download_file(url)` | ダウンロード（リトライ・タイムアウト対応） |
| `unpack_swi_grib2(bytes)` | SWI GRIB2解析 |
| `unpack_guidance_grib2(bytes)` | ガイダンスGRIB2解析 |

### data_service.py
| メソッド | 説明 |
|---------|------|
| `prepare_areas()` | CSVデータ読み込み・Prefecture/Area/Mesh構造構築（26,051メッシュ初期化） |
| `meshcode_to_coordinate_vectorized()` | メッシュコード→緯度経度変換（NumPy高速版） |
| `meshcode_to_index_vectorized()` | メッシュコード→グリッドインデックス（NumPy高速版） |

### main_service.py
| メソッド | 説明 |
|---------|------|
| `main_process_from_separate_urls(swi_url, guidance_url, ...)` | メイン処理（個別URL指定、フォールバック対応） |
| `main_process_from_urls(initial_time)` | URL自動構築処理 |

### session_service.py（セッション管理）
| メソッド | 説明 |
|---------|------|
| `create_session(prefectures, ...)` | ベースセッション作成（複数ユーザー共有） |
| `create_fork_session()` | フォークセッション作成（編集用・materialize済み） |
| `get_session(session_id)` | セッション取得（フォークは直接返却） |
| `get_prefecture(session_id, pref_code)` | 府県別データ取得 |
| `get_risk_at_time(session_id, ft)` | 指定時刻リスク値取得 |
| `recalculate_and_fork()` | 雨量調整後再計算・フォーク作成 |
| `cleanup_expired_sessions()` | TTL自動クリーンアップ |

**セッション構造:**
- **ベースセッション**: 計算完全結果を保持（複数ユーザーで共有）
- **フォークセッション**: ベース参照 + 編集差分のみ保持（軽量・ユーザー固有）
  - `is_fork: True, base_session_id: <id>, adjustments: {...}, recalculated_meshes: {...}`
  - 作成時にマージ済みデータを保存（materialize）→ 参照は O(1)

### cache_service.py（gzip圧縮キャッシュ・重複計算防止）
- 圧縮率: 209MB → 約20MB
- TTL: 7日

| メソッド | 説明 |
|---------|------|
| `generate_cache_key(swi_initial, guidance_initial)` | キャッシュキー生成 |
| `acquire_calculation_lock()` | 計算ロック取得（Cache Stampede防止） |
| `release_calculation_lock(cache_key, session_id)` | ロック解放・セッションID保存 |
| `is_calculation_in_progress()` | 計算中確認 |
| `wait_for_calculation()` | 計算完了待機（ポーリング、最大5分） |
| `get_base_session_id()` | 完了後のベースセッションID取得 |

### response_builder.py
- `ResponseBuilder.build_prefecture_response()` - Prefecture dict構築
- `_build_risk_timeline()` - リスクタイムライン整形

### config_service.py
- `build_swi_url(initial_time)` - SWI URL構築
- `build_guidance_url(initial_time)` - ガイダンスURL構築
- `get_proxy_config()` - プロキシ設定取得

## フロントエンド詳細

### types/api.ts（TypeScriptインターフェース）
| 型 | 説明 |
|----|------|
| `TimeSeriesPoint` | 時系列データ（ft, value） |
| `RiskTimePoint` | リスク時系列（ft, value: 0-4） |
| `Mesh, Area, SecondarySubdivision, Prefecture` | データ階層 |
| `LightweightCalculationResult` | セッションAPI軽量レスポンス（session_id, available_times） |
| `LightweightPrefectureData` | 府県データ軽量版 |
| `RiskAtTimeResponse` | 時刻指定リスク（mesh_coordsはオプショナル） |
| `RiskLevel` enum | 0: 正常, 2: 注意, 3: 警報, 4: 土砂災害 |

### services/api.ts
- `SoilRainfallAPIClient.calculateProductionSoilRainfallIndexWithUrls(params)` - 本番計算API
- Axios設定: 300秒タイムアウト

### services/sessionApi.ts
- `getSessionInfo(sessionId)` / `getPrefectureData(sessionId, prefCode)`
- `getRiskAtTime(sessionId, ft, includeCoords?)` - 座標はオプション（初回のみ取得してキャッシュ）
- `recalculate(sessionId, adjustments)` - 雨量調整後再計算

### pages/ProductionSession.tsx（メインUI）
**主要State:**
- `sessionId` - 現在のセッションID（フォーク切り替え対応）
- `prefectureRiskData` - 府県別リスクデータキャッシュ
- `meshRisksAtTime` - 指定時刻の全メッシュリスク値
- `swiDate/swiHour, guidanceDate/guidanceHour` - 初期時刻（JST・3時間刻み）

**デフォルト時刻**: 現在時刻 - 3時間（GRIB2ファイル生成遅延のため）

**フォークセッション切り替え**: 雨量調整再計算後に`setSessionId(newSessionId)`で切り替え

## APIエンドポイント

### メインAPI
| メソッド | パス | 説明 |
|---------|------|------|
| GET | `/health` | ヘルスチェック |
| GET | `/data-check` | データファイル確認 |
| POST | `/production-soil-rainfall-index-with-urls` | 計算実行（セッション作成） |

### セッション管理API
| メソッド | パス | 説明 |
|---------|------|------|
| GET | `/session/<id>` | セッション情報取得（available_times含む） |
| GET | `/session/<id>/prefecture/<code>` | 府県データ取得 |
| GET | `/session/<id>/risk-at-time?ft=<ft>&include_coords=<bool>` | 指定時刻リスク値 |
| GET | `/session/<id>/mesh/<code>` | メッシュデータ取得 |
| POST | `/session/<id>/recalculate` | 雨量調整後再計算（フォーク作成） |
| DELETE | `/session/<id>` | セッション削除 |
| POST | `/sessions/cleanup` | TTLクリーンアップ |

### キャッシュAPI
| メソッド | パス | 説明 |
|---------|------|------|
| GET | `/cache/list` | キャッシュ一覧 |
| GET | `/cache/stats` | キャッシュ統計 |
| DELETE | `/cache/<key>` | キャッシュ削除 |

### 雨量API
| メソッド | パス | 説明 |
|---------|------|------|
| GET | `/rainfall-forecast` | ガイダンス予測 |
| POST | `/rainfall-adjustment` | 雨量調整 |

## 本番計算フロー

```
POST /production-soil-rainfall-index-with-urls
  ↓
キャッシュキー生成（swi_initial + guidance_initial）
  ↓
重複計算防止チェック
  ├─ 計算中: wait_for_calculation() → ベースセッションID取得
  └─ 未計算: acquire_calculation_lock()
  ↓
main_process_from_separate_urls(swi_url, guidance_url)
  ├─ キャッシュHIT: 即座に返却
  └─ キャッシュMISS:
      ├─ GRIB2ダウンロード・解析
      ├─ prepare_areas() (26,051メッシュ初期化)
      ├─ 全メッシュ計算（process_mesh_calculations × 26,051）
      │    ├─ calc_swi_timelapse() - 3時間ごとSWI
      │    ├─ calc_hourly_rain() - 1時間雨量推定
      │    ├─ calc_swi_hourly() - 1時間ごとSWI
      │    ├─ calc_hourly_risk() - 1時間ごと危険度
      │    └─ calc_3hour_max_risk_from_hourly() - 3時間最大危険度
      ├─ リスク集約（エリア→二次細分→府県）
      └─ gzip圧縮キャッシュ保存
  ↓
create_session(prefectures) → session_id
  ↓
release_calculation_lock(session_id)
  ↓
軽量レスポンス（session_id + available_times）
```

## 本番環境設定

- リバースプロキシが `/api` プレフィックスを付与（`app.py` の `API_PREFIX = ''`）
- フロントエンドURLベースパス: `/dosya/`（`vite.config.ts`: `base: '/dosya/'`）
- キャッシュディレクトリ: 環境変数 `CACHE_DIR`（未設定時は `cache/` 相対パス）
- Python 3.9対応（requirements.txt: sphinx<=7.4.7）
- `client/src/main.tsx`: `BrowserRouter basename={import.meta.env.BASE_URL}`

## データソース

- **土壌雨量指数**: `http://lunar1.fcd.naps.kishou.go.jp/srf/Grib2/Rtn/swi10/`
- **降水量予測**: `http://lunar1.fcd.naps.kishou.go.jp/srf/Grib2/Rtn/gdc/`
- **境界データ**: `server/data/dosha_*.csv`（市区町村別警報基準値）

## バージョン

v8.14.0 - NumPyベクトル化による高速化対応
