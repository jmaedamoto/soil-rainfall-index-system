# プロキシ設定ガイド

## 概要
土壌雨量指数計算システムは、気象庁のGRIB2データサーバー（lunar1.fcd.naps.kishou.go.jp）にアクセスするため、本番環境ではプロキシ設定が必要です。

## 設定ファイル
設定は `config/app_config.yaml` で管理されます。

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

### その他の設定項目
```yaml
grib2:
  # ダウンロードタイムアウト（秒）
  download_timeout: 300
  
  # 接続リトライ回数
  retry_count: 3
  
  # リトライ間隔（秒）
  retry_delay: 5
```

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
- `src/config/config_service.py` - 設定管理サービス  
- `services/grib2_service.py` - HTTPクライアント実装