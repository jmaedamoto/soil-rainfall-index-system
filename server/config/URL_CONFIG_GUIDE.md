# URL・プロキシ設定変更ガイド

## 概要

本番環境の運用開始後、以下の設定を変更する必要が生じた場合のガイドです：
- プロキシサーバーのアドレス
- GRIB2データ取得元のドメイン名・URL

**重要**: これらの設定は `config/app_config.yaml` ファイルで集中管理されています。コードを変更する必要はありません。

## 設定ファイルの場所

```
server/config/app_config.yaml
```

## プロキシ設定の変更

### 本番環境のプロキシを変更する場合

`app_config.yaml` の以下の部分を編集してください：

```yaml
# プロキシ設定
proxy:
  # 本番環境用プロキシ
  http: "http://172.17.34.11:3128"
  https: "http://172.17.34.11:3128"
```

**変更例**:
```yaml
proxy:
  http: "http://新しいプロキシサーバー:ポート番号"
  https: "http://新しいプロキシサーバー:ポート番号"
```

### プロキシを無効化する場合（開発環境など）

プロキシを使用しない場合は、以下のように `null` を設定してください：

```yaml
proxy:
  http: null
  https: null
```

## GRIB2データ取得元URLの変更

### データ取得元サーバーのドメイン名が変更された場合

`app_config.yaml` の以下の部分を編集してください：

```yaml
# GRIB2データ取得設定
grib2:
  # データ取得元ベースURL
  base_url: "http://lunar1.fcd.naps.kishou.go.jp/srf/Grib2/Rtn"

  # SWI（土壌雨量指数）データパス
  swi_path: "/swi10"

  # ガイダンス（降水量予測）データパス
  guidance_path: "/gdc"
```

### 主な変更パターン

#### パターン1: ドメイン名のみ変更

**変更前**:
```yaml
base_url: "http://lunar1.fcd.naps.kishou.go.jp/srf/Grib2/Rtn"
```

**変更後**:
```yaml
base_url: "http://新しいドメイン名/srf/Grib2/Rtn"
```

#### パターン2: ベースパスも変更

**変更前**:
```yaml
base_url: "http://lunar1.fcd.naps.kishou.go.jp/srf/Grib2/Rtn"
```

**変更後**:
```yaml
base_url: "http://新しいドメイン名/新しいベースパス"
```

#### パターン3: SWI/ガイダンスのパスも変更

**変更前**:
```yaml
swi_path: "/swi10"
guidance_path: "/gdc"
```

**変更後**:
```yaml
swi_path: "/新しいSWIパス"
guidance_path: "/新しいガイダンスパス"
```

### URL構築の仕組み

システムは以下のように自動的にURLを構築します：

**SWI（土壌雨量指数）データURL**:
```
{base_url}{swi_path}/{年/月/日}/Z__C_RJTD_{年月日時分秒}_SRF_GPV_Ggis1km_Psw_Aper10min_ANAL_grib2.bin
```

**例**:
```
http://lunar1.fcd.naps.kishou.go.jp/srf/Grib2/Rtn/swi10/2025/10/28/Z__C_RJTD_20251028120000_SRF_GPV_Ggis1km_Psw_Aper10min_ANAL_grib2.bin
```

**ガイダンス（降水量予測）データURL**:
```
{base_url}{guidance_path}/{年/月/日}/guid_msm_grib2_{年月日時分秒}_rmax{00または03}.bin
```

**例**:
```
http://lunar1.fcd.naps.kishou.go.jp/srf/Grib2/Rtn/gdc/2025/10/28/guid_msm_grib2_20251028120000_rmax00.bin
```

## その他の設定

### タイムアウト・リトライ設定

データ取得時のタイムアウトやリトライ回数も変更できます：

```yaml
grib2:
  # タイムアウト設定（秒）
  download_timeout: 300

  # 接続リトライ設定
  retry_count: 3
  retry_delay: 5
```

- `download_timeout`: ダウンロードのタイムアウト時間（秒）
- `retry_count`: 失敗時のリトライ回数
- `retry_delay`: リトライ間隔（秒）

## 設定変更後の動作確認

### 1. サーバーを再起動

設定ファイルを変更した後は、サーバーを再起動してください：

```bash
# サーバーを停止（Ctrl+Cなど）
# サーバーを再起動
python app.py
```

### 2. ログで設定を確認

サーバー起動時のログで、読み込まれた設定を確認できます：

```
INFO - 設定ファイル読み込み完了: d:\development\soil-rainfall-index-system\server\config\app_config.yaml
INFO - プロキシ設定: http://172.17.34.11:3128
```

### 3. テストAPIで動作確認

以下のエンドポイントでデータ取得をテストしてください：

```bash
# ヘルスチェック
curl http://localhost:5000/api/health

# 本番データ取得テスト（直近の時刻で自動実行）
curl http://localhost:5000/api/production-soil-rainfall-index
```

## トラブルシューティング

### 設定が反映されない場合

1. YAMLの書式が正しいか確認（インデント、コロンの後のスペースなど）
2. サーバーを完全に停止して再起動
3. ログファイルでエラーメッセージを確認

### プロキシ接続エラーの場合

```
ProxyError: HTTPConnectionPool(host='172.17.34.11', port=3128)
```

- プロキシサーバーのアドレス・ポートが正しいか確認
- プロキシサーバーが起動しているか確認
- ファイアウォール設定を確認

### データ取得失敗の場合

```
ファイルダウンロード失敗: http://...
```

- URLが正しく構築されているかログで確認
- データ取得元サーバーが稼働しているか確認
- ネットワーク接続を確認

## 設定ファイルのバックアップ

設定変更前に必ずバックアップを取ってください：

```bash
# Windows
copy config\app_config.yaml config\app_config.yaml.backup

# Linux/Mac
cp config/app_config.yaml config/app_config.yaml.backup
```

## サポート

設定変更で問題が発生した場合は、システム管理者に連絡してください。

---

**ドキュメント作成日**: 2025年10月28日
**対象バージョン**: 7.1.0以降
