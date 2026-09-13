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

本運用では production と staging を同一サーバー上で並列稼働します。

| 環境 | クライアントURL | API URL | キャッシュ |
| --- | --- | --- | --- |
| production | `/dosya` | `/dosya/api` | `/var/cache/myapp/dosya` |
| staging | `/staging/dosya` | `/staging/dosya/api` | `/var/cache/myapp/staging/dosya` |

フロントの本番ビルドは既定で `/dosya/` を使います。staging ビルドでは `VITE_BASE_PATH=/staging/dosya/` を指定します。

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

## 解析雨量GRIB2

`server/src/services/grib2_service.py` は、気象庁「配信資料に関する仕様
No.11601」の1kmメッシュ解析雨量と速報版解析雨量を読み取れます。
`unpack_analyzed_rainfall_grib2()` はバイト列、
`unpack_analyzed_rainfall_grib2_from_file()` はファイルパスを受け取り、1時間積算雨量を
mm単位で返します。レベル0の欠測格子は `NaN` です。

単独でCSVへ変換する場合:

```bash
python server/decode_analyzed_rainfall.py /path/to/Prr60lv_ANAL_grib2.bin
```

入力ファイルと同じディレクトリへ同名の `.csv` を出力します。CSVは格子番号、格子の
x/y番号、緯度、経度、1時間積算雨量を持ち、欠測雨量は空欄になります。出力先を変える
場合は `-o output.csv`、既存ファイルを上書きする場合は `--force` を指定します。

サーバー環境から独立した配布版は `standalone/analyzed-rainfall-decoder/` にあります。
Python標準ライブラリだけで動作し、ライブラリとしても読み込めます。配布用ZIPは
`dist/analyzed-rainfall-decoder-1.0.0.zip` です。対応仕様、API、CSV形式、ZIP再生成方法は
`docs/analyzed-rainfall-grib2.md` を参照してください。

別プロジェクトへ組み込む場合は単独配布版の本体1ファイルをコピーします。
配布ZIPには `example_usage.py` と、移行先のCodex向け引き継ぎ・API・確認手順を
記載した `README.md` も含めます。ZIPはGit管理外で、GitHubには再生成用のソースを保存します。

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

## ドキュメント更新

ソースコードを改修した場合は、同じ作業内で関連する Markdown も確認し、実装内容・運用手順・既知課題と矛盾しないように更新します。特に API、キャッシュ、セッション、デプロイ、調査メモ、作業再開プロンプトに影響する変更では、以下を確認対象に含めます。

- `CLAUDE.md`
- `docs/work-resume-prompt.md`
- `docs/staging-promotion-rules.md`
- `server/docs/CACHE_SYSTEM.md`
- `server/deploy/DEPLOY_GUIDE.md`
- 関連する `docs/*.md`

## 昇格前の注意

`staging` / `main` への昇格前は、production profile のルート確認と不要ファイル確認を行います。`server/tests/`、`.pytest_cache/`、`__pycache__/`、`*.pyc` はリリース payload に含めません。
