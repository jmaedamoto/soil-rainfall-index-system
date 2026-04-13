# Staging/Main Promotion Rules

`develop` / `refactor` から `staging` / `main` に移すときは、`SOIL_RAINFALL_ROUTE_PROFILE=production` を前提に、本番クライアントが使うルートだけを公開する。

## API公開ルール

- `production` プロファイルで公開するのは本番クライアント導線のみ
- `all` プロファイルは開発・検証用ルートも含む
- staging/main では `production` を使う

本番クライアント向け API:

- `POST /production-soil-rainfall-index-with-urls`
- `GET /session/<session_id>/prefecture/<prefecture_code>`
- `GET /session/<session_id>/risk-at-time`
- `GET /session/<session_id>/rainfall-data`
- `POST /session/<session_id>/recalculate`

開発・検証用 API:

- `root/health/data-check`
- 旧来の計算入口、キャッシュ管理 API、雨量調整 API
- テスト用 API
- セッション詳細/削除/一覧/統計/cleanup

## 昇格手順

1. `staging` / `main` では `SOIL_RAINFALL_ROUTE_PROFILE=production` を設定する
2. 本番不要ファイルを削除する
3. `test_*.py`、`server/tests/`、`.pytest_cache/`、`__pycache__/`、`*.pyc` を残さない
4. PR に「production profile で確認済み」と明記する

## 明示方法

- ブランチ昇格用 PR テンプレートに `route profile: production` を必須項目として入れる
- デプロイ設定に `SOIL_RAINFALL_ROUTE_PROFILE=production` を固定する
- レビュー観点に「開発用 route が露出していないか」を追加する
- `.github/workflows/staging-promotion-check.yml` で production profile の route と不要ファイルを CI 検査する
- `scripts/check_production_promotion.py` を昇格前のローカル確認コマンドとして使う

## ローカル確認

```bash
python scripts/check_production_promotion.py
```
