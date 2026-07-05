# 土壌雨量指数計算システム デプロイ手順

## 対象構成

- OS: Rocky Linux 9系
- Web Server: Apache httpd + mod_wsgi
- Python: 3.9+
- production クライアント配信先例: `/var/www/html/dosya`
- production API配置先例: `/var/www/app/production/soil-rainfall-index-system`
- staging クライアント配信先例: `/var/www/html/staging/dosya`
- staging API配置先例: `/var/www/app/staging/soil-rainfall-index-system`

production と staging は同一サーバー上で並列稼働します。Apache の daemon process、WSGIScriptAlias、`CACHE_DIR` は環境ごとに分離してください。

| 環境 | クライアントURL | API URL | キャッシュ |
| --- | --- | --- | --- |
| production | `/dosya` | `/dosya/api` | `/var/cache/nyapp/dosya` |
| staging | `/staging/dosya` | `/staging/dosya/api` | `/var/cache/myapp/staging/dosya` |

## 1. パッケージ

```bash
sudo dnf update -y
sudo dnf install -y python3 python3-pip python3-devel httpd httpd-devel
sudo dnf groupinstall -y "Development Tools"
```

## 2. 配置先

```bash
sudo mkdir -p /var/www/app/production/soil-rainfall-index-system
sudo mkdir -p /var/www/html/dosya
sudo mkdir -p /var/www/app/staging/soil-rainfall-index-system
sudo mkdir -p /var/www/html/staging/dosya
sudo chown -R $USER:$USER /var/www/app/production/soil-rainfall-index-system
sudo chown -R $USER:$USER /var/www/html/dosya
sudo chown -R $USER:$USER /var/www/app/staging/soil-rainfall-index-system
sudo chown -R $USER:$USER /var/www/html/staging/dosya
```

## 3. Python環境

```bash
cd /var/www/app/production/soil-rainfall-index-system
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r server/requirements.txt
pip install mod_wsgi
mod_wsgi-express module-config
```

`mod_wsgi-express module-config` の出力をApache設定に反映します。

## 4. 設定

`server/config/app_config.yaml` を配置先環境に合わせて確認します。

```yaml
api:
  route_profile: "production"
```

Apache / systemd / WSGI の環境変数でも以下を固定してください。

```text
SOIL_RAINFALL_ROUTE_PROFILE=production
```

キャッシュヒット時の gzip 再展開を抑えるため、プロセス内で保持する展開済みキャッシュ件数を必要に応じて設定できます。未設定時は2件です。メモリ使用量を優先する場合は `0` で無効化します。

```text
CACHE_MEMORY_MAX_RESULTS=2
```

プロキシ、GRIB2取得元、タイムアウトは `server/config/URL_CONFIG_GUIDE.md` を参照してください。

Apache 設定例:

- production: `server/deploy/apache-soil-rainfall-production.conf`
- staging: `server/deploy/apache-soil-rainfall.conf`

production は `/dosya/api` と `/var/cache/nyapp/dosya`、staging は `/staging/dosya/api` と `/var/cache/myapp/staging/dosya` を使います。

フロントビルド:

```bash
cd client
npm run build:production
```

`client/dist-production` の中身を `/var/www/html/dosya` に配置します。

```bash
cd client
npm run build:staging
```

`client/dist-staging` の中身を `/var/www/html/staging/dosya` に配置します。

`build:production` は `/dosya/`、`build:staging` は `/staging/dosya/` で asset path と API base を組み立てます。staging に `dist-production` または通常の `dist` を配置すると、HTML が `/dosya/assets/...` を参照して 404 になります。

## 5. データファイル

`server/data` に対象地方のCSVを配置します。

- 近畿: `shiga`, `kyoto`, `hyogo`, `osaka`, `nara`, `wakayama`
- 中国: `tottori`, `okayama`, `hiroshima`, `shimane`
- 四国: `ehime`, `tokushima`, `kagawa`, `kochi`

必要なファイル:

```text
dosha_*.csv
2_2_*.csv
prefectures.csv
```

検証用にローカルGRIB2を使う場合は `*.bin` も配置します。

## 6. 権限

```bash
sudo chown -R apache:apache /var/www/app/production/soil-rainfall-index-system
sudo chown -R apache:apache /var/www/html/dosya
sudo chown -R apache:apache /var/www/app/staging/soil-rainfall-index-system
sudo chown -R apache:apache /var/www/html/staging/dosya
sudo chmod -R 755 /var/www/app/production/soil-rainfall-index-system
sudo chmod -R 755 /var/www/html/dosya
sudo chmod -R 755 /var/www/app/staging/soil-rainfall-index-system
sudo chmod -R 755 /var/www/html/staging/dosya

sudo mkdir -p /var/cache/nyapp/dosya
sudo mkdir -p /var/cache/myapp/staging/dosya
sudo chown -R apache:apache /var/cache/nyapp
sudo chown -R apache:apache /var/cache/myapp/staging
sudo chmod 775 /var/cache/nyapp
sudo chmod 775 /var/cache/nyapp/dosya
sudo chmod 775 /var/cache/myapp/staging
sudo chmod 775 /var/cache/myapp/staging/dosya
```

## 7. SELinux

SELinuxが有効な環境では以下を設定します。

```bash
sudo setsebool -P httpd_can_network_connect 1
sudo semanage fcontext -a -t httpd_sys_content_t "/var/www/app/production/soil-rainfall-index-system(/.*)?"
sudo semanage fcontext -a -t httpd_sys_content_t "/var/www/html/dosya(/.*)?"
sudo semanage fcontext -a -t httpd_sys_content_t "/var/www/app/staging/soil-rainfall-index-system(/.*)?"
sudo semanage fcontext -a -t httpd_sys_content_t "/var/www/html/staging/dosya(/.*)?"
sudo semanage fcontext -a -t httpd_sys_rw_content_t "/var/cache/nyapp(/.*)?"
sudo semanage fcontext -a -t httpd_sys_rw_content_t "/var/cache/myapp/staging(/.*)?"
sudo restorecon -Rv /var/www/app/production/soil-rainfall-index-system
sudo restorecon -Rv /var/www/html/dosya
sudo restorecon -Rv /var/www/app/staging/soil-rainfall-index-system
sudo restorecon -Rv /var/www/html/staging/dosya
sudo restorecon -Rv /var/cache/nyapp
sudo restorecon -Rv /var/cache/myapp/staging
```

## 8. Apache起動

```bash
sudo apachectl configtest
sudo systemctl restart httpd
sudo systemctl enable httpd
sudo systemctl status httpd
```

## 9. 動作確認

本番プロファイルでは開発用 `/health` や `/data-check` は公開しません。クライアントの地方別ページと本番APIで確認します。

```bash
curl -X POST http://localhost/dosya/api/production-soil-rainfall-index-with-urls \
  -H "Content-Type: application/json" \
  -d '{
    "swi_initial": "2026-06-05T00:00:00.000Z",
    "guidance_initial": "2026-06-05T00:00:00.000Z",
    "guidance_type": "msm",
    "risk_rule": "legacy",
    "region": "kinki"
  }'
```

staging は同じ payload を `/staging/dosya/api/production-soil-rainfall-index-with-urls` に送って確認します。

昇格前のローカル確認:

```bash
python scripts/check_production_promotion.py
```

集中アクセス時は、計算中の後続リクエストへ `202 Accepted` と `Retry-After: 2` が返ることを確認します。クライアントは計算結果のgzipキャッシュが完成するまで自動的に再確認します。

Apache設定は `request-timeout`、`socket-timeout`、`Timeout` を900秒にそろえます。設定変更後は `apachectl configtest` を通してからhttpdを再起動してください。

## 10. 昇格時の不要ファイル

リリースpayloadには以下を含めません。

- `server/tests/`
- `test_*.py`
- `.pytest_cache/`
- `__pycache__/`
- `*.pyc`

## ログ

```bash
sudo tail -f /var/log/httpd/soil-rainfall-error.log
sudo tail -f /var/log/httpd/soil-rainfall-access.log
```

## よくある問題

| 症状 | 確認点 |
| --- | --- |
| 500 | WSGIのPythonパス、仮想環境、Apache設定 |
| 403 | ファイル権限、SELinux |
| GRIB2取得失敗 | プロキシ、取得元URL、対象時刻 |
| 開発APIが404 | production profile では正常。開発時は `SOIL_RAINFALL_ROUTE_PROFILE=all` を使う |
