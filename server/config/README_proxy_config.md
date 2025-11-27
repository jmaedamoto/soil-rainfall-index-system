# プロキシ・URL設定ガイド

## 概要
土壌雨量指数計算システムは、気象庁のGRIB2データサーバーにアクセスするため、以下の設定が必要です：
- **プロキシサーバー**: 本番環境での外部接続用
- **データ取得元URL**: GRIB2データのダウンロード先

**重要**: 運用開始後にこれらの設定が変更される場合があります。詳細な変更手順は `URL_CONFIG_GUIDE.md` を参照してください。

## 設定ファイル
設定は `config/app_config.yaml` で集中管理されます。

## プロキシ設定

### 本番環境用設定
```yaml
proxy:
  http: "http://172.17.34.11:3128"
  https: "http://172.17.34.11:3128"
```

### 開発環境用設定（プロキシ不使用）
```yaml
proxy:
  http: null
  https: null
```

## GRIB2データ取得元URL設定

### データ取得元サーバー設定
```yaml
grib2:
  # データ取得元ベースURL
  base_url: "http://lunar1.fcd.naps.kishou.go.jp/srf/Grib2/Rtn"

  # SWI（土壌雨量指数）データパス
  swi_path: "/swi10"

  # ガイダンス（降水量予測）データパス
  guidance_path: "/gdc"

  # ダウンロードタイムアウト（秒）
  download_timeout: 300

  # 接続リトライ回数
  retry_count: 3

  # リトライ間隔（秒）
  retry_delay: 5
```

**注意**: 運用開始後にドメイン名やパスが変更される場合は、上記の設定を変更してください。詳細は `URL_CONFIG_GUIDE.md` を参照してください。

## 設定の確認
アプリケーション起動時のログで設定を確認できます：

```
INFO:services.grib2_service:Proxy設定: HTTP=http://172.17.34.11:3128, HTTPS=http://172.17.34.11:3128
```

または

```
INFO:services.grib2_service:Proxy設定なし（直接接続）
```

## トラブルシューティング

### プロキシエラーが発生する場合
1. `config/app_config.yaml` のproxy設定を確認
2. プロキシサーバーのアドレスとポート番号を確認
3. ネットワーク接続を確認

### タイムアウトエラーが発生する場合
1. `download_timeout` の値を増加（例：600秒）
2. `retry_count` の値を増加（例：5回）

## 関連ファイル
- `config/app_config.yaml` - メイン設定ファイル
- `config/URL_CONFIG_GUIDE.md` - URL・プロキシ設定変更の詳細ガイド
- `src/config/config_service.py` - 設定管理サービス
- `services/main_service.py` - URL構築処理
- `services/grib2_service.py` - HTTPクライアント実装
- `src/api/controllers/main_controller.py` - APIエンドポイント実装