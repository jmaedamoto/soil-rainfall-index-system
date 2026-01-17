# 土壌雨量指数計算システム デプロイ手順書

## 対象環境
- OS: Rocky Linux 9.7
- Web Server: Apache httpd + mod_wsgi
- Python: 3.9+

---

## 1. システムパッケージのインストール

```bash
# root権限で実行
sudo dnf update -y

# Python3 と開発ツール
sudo dnf install -y python3 python3-pip python3-devel

# Apache と開発ヘッダー
sudo dnf install -y httpd httpd-devel

# ビルドツール（mod_wsgiコンパイル用）
sudo dnf groupinstall -y "Development Tools"
```

---

## 2. アプリケーションディレクトリの準備

```bash
# ディレクトリ作成
sudo mkdir -p /var/www/soil-rainfall
sudo chown $USER:$USER /var/www/soil-rainfall

# アプリケーションをコピー（開発環境から転送）
# scp -r server/ user@production:/var/www/soil-rainfall/
```

---

## 3. Python仮想環境の構築

```bash
cd /var/www/soil-rainfall

# 仮想環境作成
python3 -m venv venv

# 仮想環境を有効化
source venv/bin/activate

# 依存パッケージインストール
pip install --upgrade pip
pip install -r server/requirements.txt

# mod_wsgi インストール
pip install mod_wsgi
```

---

## 4. mod_wsgi の設定確認

```bash
# mod_wsgi モジュールのパスとPythonホームを確認
source /var/www/soil-rainfall/venv/bin/activate
mod_wsgi-express module-config
```

出力例:
```
LoadModule wsgi_module "/var/www/soil-rainfall/venv/lib64/python3.9/site-packages/mod_wsgi/server/mod_wsgi-py39.cpython-39-x86_64-linux-gnu.so"
WSGIPythonHome "/var/www/soil-rainfall/venv"
```

この出力を `/etc/httpd/conf.d/soil-rainfall.conf` の先頭に追記します。

---

## 5. Apache設定ファイルの配置

```bash
# 設定ファイルをコピー
sudo cp /var/www/soil-rainfall/server/deploy/apache-soil-rainfall.conf \
        /etc/httpd/conf.d/soil-rainfall.conf

# 設定ファイルを編集
sudo vi /etc/httpd/conf.d/soil-rainfall.conf
```

### 編集が必要な箇所:

1. **mod_wsgi モジュールパス** - 手順4の出力に合わせる
2. **ServerName** - 実際のドメイン名またはIPアドレス
3. **WSGIDaemonProcess python-home** - 仮想環境のパス確認

---

## 6. データファイルの配置

```bash
# CSVデータファイルが存在することを確認
ls -la /var/www/soil-rainfall/server/data/

# 必要なファイル:
# - dosha_*.csv (6府県分)
# - dosyakei_*.csv (6府県分)
```

---

## 7. 権限設定

```bash
# Apacheユーザーがアクセスできるように権限設定
sudo chown -R apache:apache /var/www/soil-rainfall
sudo chmod -R 755 /var/www/soil-rainfall

# キャッシュディレクトリに書き込み権限
sudo chmod 775 /var/www/soil-rainfall/server/data/cache
```

---

## 8. SELinux設定（有効な場合）

```bash
# SELinuxの状態確認
getenforce

# httpd がネットワークアクセスできるように設定
sudo setsebool -P httpd_can_network_connect 1

# アプリケーションディレクトリのコンテキスト設定
sudo semanage fcontext -a -t httpd_sys_content_t "/var/www/soil-rainfall(/.*)?"
sudo semanage fcontext -a -t httpd_sys_rw_content_t "/var/www/soil-rainfall/server/data/cache(/.*)?"
sudo restorecon -Rv /var/www/soil-rainfall
```

---

## 9. ファイアウォール設定

```bash
# HTTP/HTTPSポートを開放
sudo firewall-cmd --permanent --add-service=http
sudo firewall-cmd --permanent --add-service=https
sudo firewall-cmd --reload
```

---

## 10. 設定テストと起動

```bash
# Apache設定テスト
sudo apachectl configtest

# Apache起動
sudo systemctl start httpd

# 自動起動設定
sudo systemctl enable httpd

# 状態確認
sudo systemctl status httpd
```

---

## 11. 動作確認

```bash
# ヘルスチェック
curl http://localhost/api/health

# データチェック
curl http://localhost/api/data-check
```

期待されるレスポンス:
```json
{"status": "healthy", "timestamp": "..."}
```

---

## 12. 本番用設定ファイル（オプション）

プロキシが必要な場合は `config/app_config.yaml` を編集:

```yaml
proxy:
  http: "http://proxy.example.com:8080"
  https: "http://proxy.example.com:8080"

grib2:
  base_url: "http://lunar1.fcd.naps.kishou.go.jp/srf/Grib2/Rtn"
  download_timeout: 300
  retry_count: 3
```

---

## トラブルシューティング

### ログ確認
```bash
# Apacheエラーログ
sudo tail -f /var/log/httpd/soil-rainfall-error.log

# Apacheアクセスログ
sudo tail -f /var/log/httpd/soil-rainfall-access.log
```

### よくある問題

| 症状 | 原因 | 対処 |
|-----|------|------|
| 500 Internal Server Error | Pythonパスの問題 | wsgi.pyのsys.path確認 |
| 403 Forbidden | SELinux/権限 | SELinux設定・ファイル権限確認 |
| モジュール読み込みエラー | mod_wsgiパス不正 | `mod_wsgi-express module-config`で再確認 |
| GRIB2ダウンロード失敗 | プロキシ/ネットワーク | app_config.yamlのプロキシ設定確認 |

---

## ディレクトリ構成（本番環境）

```
/var/www/soil-rainfall/
├── venv/                    # Python仮想環境
│   ├── bin/
│   ├── lib/
│   └── lib64/
└── server/                  # アプリケーション
    ├── app.py
    ├── wsgi.py              # WSGIエントリーポイント
    ├── requirements.txt
    ├── config/
    │   └── app_config.yaml
    ├── data/
    │   ├── cache/           # キャッシュ（書き込み可能）
    │   ├── dosha_*.csv
    │   └── dosyakei_*.csv
    ├── deploy/
    │   ├── apache-soil-rainfall.conf
    │   └── DEPLOY_GUIDE.md
    ├── models/
    ├── services/
    └── src/
```

---

**作成日**: 2026年1月
**対象バージョン**: 8.5.0
