# 土壌雨量指数計算システム

Excel VBAで運用されていた土壌雨量指数計算を、Python/Flask API と React/TypeScript クライアントへ移植したシステムです。

## 現在の構成

- バックエンド: Python 3.9+ / Flask
- フロントエンド: React / TypeScript / Vite
- 地図: Leaflet / react-leaflet
- グラフ: Chart.js / react-chartjs-2
- 計算データ: 気象庁GRIB2、府県別CSV、1kmメッシュ

## 対象地方

現在の本番クライアントは地方別ページで運用します。

| ページ | 地方 | 対象府県 |
| --- | --- | --- |
| `/kinki` | 近畿地方 | 滋賀、京都、兵庫、大阪、奈良、和歌山 |
| `/chugoku` | 中国地方 | 鳥取、岡山、広島、島根 |
| `/shikoku` | 四国地方 | 愛媛、徳島、香川、高知 |

データファイルは `server/data` に `dosha_*.csv`、`2_2_*.csv`、テスト用GRIB2ファイルを配置します。

## 本番API

`staging` / `main` では `SOIL_RAINFALL_ROUTE_PROFILE=production` を使い、本番クライアントに必要なルートだけを公開します。

- `POST /production-soil-rainfall-index-with-urls`
- `GET /session/<session_id>/prefecture/<prefecture_code>`
- `GET /session/<session_id>/risk-at-time`
- `GET /session/<session_id>/rainfall-data`
- `POST /session/<session_id>/recalculate`

詳しい昇格ルールは `docs/staging-promotion-rules.md` を参照してください。

## 処理概要

1. SWIと降水量ガイダンスの初期時刻を受け取る
2. 設定ファイルからGRIB2 URLを構築する
3. 地方・ガイダンス種別・危険度ルール込みのキャッシュキーを生成する
4. キャッシュがあればGRIB2取得前に軽量セッションレスポンスを返す
5. キャッシュがなければ計算ロックを取得し、同一条件の重複計算を防ぐ
6. 地方内の府県データを構築し、SWI・危険度・雨量時系列を計算する
7. gzipキャッシュへ原子的に保存し、セッションIDを返す
8. クライアントは府県データ・時刻別メッシュ危険度・雨量調整結果をセッションAPIで取得する

## キャッシュとセッション

- キャッシュ: `server/src/services/cache_service.py`
- セッション: `server/src/services/session_service.py`
- 本番計算制御: `server/src/api/controllers/main_controller.py`

キャッシュキーには SWI初期時刻、ガイダンス初期時刻、ガイダンス種別、危険度ルール、地方を含めます。計算中は `.calculating.json` ロックを作成し、同一条件の後続リクエストはキャッシュ確定を待ちます。

セッションは通常メモリに保持します。ベースセッションは `cache_key` 参照を `cache/session_refs` に保存するため、プロセス内メモリにないセッションもキャッシュから復元できます。雨量調整後はフォークセッションとして差分を保持します。

## 雨量調整

本番クライアントはセッションベースの雨量調整を使います。

- 入力モード: 3時間雨量、24時間合計雨量
- 補正モード: 比率補正、入力値塗りつぶし、ガイダンス最大格子塗りつぶし、24時間均等配分、24時間最大メッシュ基準
- ガイダンス最大格子塗りつぶしは入力値を使わず、各市町村内の時刻ごとの最大格子値で全メッシュを更新します
- 境界メッシュは複数領域の入力またはガイダンス最大値を考慮し、保守的な値を採用します
- 調整後は3時間・1時間の雨量/SWI/危険度タイムラインを更新します

## 設定

主要設定は `server/config/app_config.yaml` で管理します。

- `api.route_profile`: `production` または `all`
- `proxy`: GRIB2取得時のHTTP/HTTPSプロキシ
- `grib2.base_url`: GRIB2取得元
- `grib2.swi_path`: SWIパス
- `grib2.guidance_path`: ガイダンスパス
- `grib2.download_timeout`: ダウンロードタイムアウト
- `data.local_grib2_fallback`: ローカルGRIB2フォールバック
- `cache`: キャッシュディレクトリ、TTL、圧縮設定

URL・プロキシ設定の詳細は `server/config/URL_CONFIG_GUIDE.md` を参照してください。

## 開発コマンド

```bash
cd server
python app.py
```

```bash
cd client
npm run dev
```

```bash
cd client
npm run build
```

```bash
python scripts/check_production_promotion.py
```

## 昇格前の注意

`staging` / `main` への昇格前は、production profile のルート確認と不要ファイル確認を行います。`server/tests/`、`.pytest_cache/`、`__pycache__/`、`*.pyc` はリリース payload に含めません。
