# プロキシ・URL設定クイックリファレンス

設定ファイルは `server/config/app_config.yaml` です。詳細な変更手順は `URL_CONFIG_GUIDE.md` を参照してください。

## production profile

```yaml
api:
  route_profile: "production"
```

`staging` / `main` では環境変数 `SOIL_RAINFALL_ROUTE_PROFILE=production` を固定します。

## プロキシ

```yaml
proxy:
  http: "http://172.17.2.163:8080"
  https: "http://172.17.2.163:8080"
```

プロキシを使わない場合:

```yaml
proxy:
  http: null
  https: null
```

## GRIB2

```yaml
grib2:
  base_url: "http://lunar1.fcd.naps.kishou.go.jp/srf/Grib2/Rtn"
  swi_path: "/swi10"
  guidance_path: "/gdc"
  download_timeout: 600
  retry_count: 3
  retry_delay: 5
```

ガイダンス種別は `msm` と `gsm` をサポートします。GSMはUTC 00/06/12/18時のみ有効です。

## 関連ファイル

- `src/config/config_service.py`
- `src/api/controllers/main_controller.py`
- `src/services/grib2_service.py`
- `docs/staging-promotion-rules.md`
