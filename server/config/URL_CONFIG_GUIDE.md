# URL・プロキシ設定変更ガイド

GRIB2取得元、プロキシ、公開APIプロファイルは `server/config/app_config.yaml` で管理します。コード変更なしで運用環境ごとの値を切り替えられます。

## 設定ファイル

```text
server/config/app_config.yaml
```

## API公開プロファイル

```yaml
api:
  route_profile: "production"
```

- `production`: 本番クライアントに必要なルートだけを公開します。
- `all`: 開発・検証用ルート、キャッシュ管理API、テストAPIも公開します。

`staging` / `main` では `SOIL_RAINFALL_ROUTE_PROFILE=production` を環境変数で固定してください。環境変数がある場合は設定ファイルより優先されます。

## プロキシ設定

```yaml
proxy:
  http: "http://172.17.2.163:8080"
  https: "http://172.17.2.163:8080"
```

プロキシを使わない環境では `null` を設定します。

```yaml
proxy:
  http: null
  https: null
```

## GRIB2取得元

```yaml
grib2:
  base_url: "http://lunar1.fcd.naps.kishou.go.jp/srf/Grib2/Rtn"
  swi_path: "/swi10"
  guidance_path: "/gdc"
  download_timeout: 600
  retry_count: 3
  retry_delay: 5
```

SWI URL:

```text
{base_url}{swi_path}/{YYYY/MM/DD}/Z__C_RJTD_{YYYYMMDDHHMMSS}_SRF_GPV_Ggis1km_Psw_Aper10min_ANAL_grib2.bin
```

MSMガイダンスURL:

```text
{base_url}{guidance_path}/{YYYY/MM/DD}/guid_msm_grib2_{YYYYMMDDHHMMSS}_rmax00.bin
{base_url}{guidance_path}/{YYYY/MM/DD}/guid_msm_grib2_{YYYYMMDDHHMMSS}_rmax03.bin
```

GSMガイダンスURL:

```text
{base_url}{guidance_path}/{YYYY/MM/DD}/guid_gsm_grib2_{YYYYMMDDHHMMSS}_rmax.bin
```

GSMはUTC 00/06/12/18時だけを受け付けます。

## ローカルGRIB2フォールバック

外部取得に失敗したときの検証用フォールバックは `data.local_grib2_fallback` で制御します。

```yaml
data:
  local_grib2_fallback:
    enabled: false
    swi_path: null
    guidance_path: null
```

本番運用では通常 `false` のままにします。

## 確認コマンド

開発ルートを含めて動かす場合:

```bash
cd server
SOIL_RAINFALL_ROUTE_PROFILE=all python app.py
```

本番公開ルートだけを確認する場合:

```bash
python scripts/check_production_promotion.py
```

本番プロファイルで公開されるAPIは以下だけです。

- `POST /production-soil-rainfall-index-with-urls`
- `GET /session/<session_id>/prefecture/<prefecture_code>`
- `GET /session/<session_id>/risk-at-time`
- `GET /session/<session_id>/rainfall-data`
- `POST /session/<session_id>/recalculate`

## トラブルシューティング

- プロキシ接続エラー: `proxy.http` / `proxy.https`、プロキシ疎通、ファイアウォールを確認します。
- GRIB2取得失敗: ログに出力される構築済みURL、対象時刻、取得元サーバーを確認します。
- GSM時刻エラー: UTC 00/06/12/18時を指定します。
- 開発APIが404になる: `SOIL_RAINFALL_ROUTE_PROFILE=all` で起動しているか確認します。
