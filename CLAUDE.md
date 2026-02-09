# 土壌雨量指数計算システム

## 概要

気象庁のGRIB2形式データを解析し、土壌雨量指数を計算するWebシステム。

## 対象地域

関西6府県（26,051メッシュ）：
- 滋賀県、京都府、大阪府、兵庫県、奈良県、和歌山県

## 技術スタック

- **バックエンド**: Python 3.9+ / Flask
- **フロントエンド**: React 18 / TypeScript / Vite
- **データソース**: 気象庁GRIB2データ

## APIエンドポイント

### メインAPI
| メソッド | パス | 説明 |
|---------|------|------|
| GET | `/health` | ヘルスチェック |
| POST | `/production-soil-rainfall-index-with-urls` | 計算実行（セッション作成） |

### セッション管理API
| メソッド | パス | 説明 |
|---------|------|------|
| GET | `/session/<id>` | セッション情報取得 |
| GET | `/session/<id>/prefecture/<code>` | 府県データ取得 |
| GET | `/session/<id>/risk-at-time?ft=<ft>` | 指定時刻リスク値 |
| POST | `/session/<id>/recalculate` | 雨量調整後再計算 |

## 本番環境設定

- リバースプロキシが `/api` プレフィックスを付与
- キャッシュディレクトリ: 環境変数 `CACHE_DIR` で設定

## バージョン

v8.14.0 - NumPyベクトル化による高速化対応
