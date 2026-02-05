# 土壌雨量指数計算システム VBA → Python Web API 変換プロジェクト

## プロジェクト概要

ExcelのVBA（Visual Basic for Applications）で実装されていた土壌雨量指数計算システムを、PythonのWeb APIに変換するプロジェクトです。

### 変換対象
- **元システム**: Excel VBA (`土壌雨量指数計算.xlsm`)
- **新システム**: Python Flask Web API
- **メイン処理**: `main_process`関数の完全な移植
- **実データ対応**: 関西6府県の実際のCSVデータを使用

## システム仕様

### 処理概要
1. 気象庁のGRIB2形式データ（土壌雨量指数・降水量予測）をダウンロード
2. バイナリデータを解析してグリッド情報を抽出
3. 実際のCSVデータ（境界値・土砂災害データ）から地域構造を構築
4. 3段タンクモデルによる土壌雨量指数の時系列計算
5. 都道府県・地域・メッシュ別のリスク評価
6. 構造化されたJSONレスポンスを返却

### 対象地域
関西6府県の実データ処理：
- 滋賀県 (shiga) - 3,307メッシュ
- 京都府 (kyoto) - 4,493メッシュ
- 大阪府 (osaka) - 1,885メッシュ
- 兵庫県 (hyogo) - 8,269メッシュ
- 奈良県 (nara) - 3,480メッシュ
- 和歌山県 (wakayama) - 4,611メッシュ
- **総計**: 26,051メッシュ（1km×1kmグリッド）

## 技術仕様

### 開発環境
- **バックエンド**: Python 3.9+ + Flask
- **フロントエンド**: React 18 + TypeScript + Vite
- **主要ライブラリ**:
  - `requests` (HTTPクライアント)
  - `pandas` (CSVデータ処理)
  - `numpy` (数値計算)
  - `leaflet` + `react-leaflet` (地図表示)
  - `chart.js` + `react-chartjs-2` (グラフ表示)
  - `axios` (API通信)

### データソース
- **土壌雨量指数**: `http://lunar1.fcd.naps.kishou.go.jp/srf/Grib2/Rtn/swi10/`
- **降水量予測**: `http://lunar1.fcd.naps.kishou.go.jp/srf/Grib2/Rtn/gdc/`
- **フォーマット**: GRIB2バイナリ形式
- **境界データ**: `dosha_*.csv`（市区町村別警報基準値）

## ディレクトリ構造

```
soil-rainfall-index-system/
├── server/                      # バックエンド（Python Flask）
│   ├── app.py                   # エントリーポイント
│   ├── wsgi.py                  # WSGI エントリーポイント
│   ├── requirements.txt         # Python依存関係
│   ├── cache/                   # 計算結果キャッシュ
│   ├── data/                    # CSVデータ・テストデータ
│   └── src/
│       ├── api/
│       │   ├── controllers/     # APIコントローラー
│       │   └── routes/          # ルーティング定義
│       ├── config/              # 設定サービス
│       ├── models/              # データモデル
│       ├── services/            # ビジネスロジック
│       └── utils/               # ユーティリティ
├── client/                      # フロントエンド（React + TypeScript）
│   ├── src/
│   │   ├── components/          # UIコンポーネント
│   │   ├── pages/               # ページコンポーネント
│   │   ├── services/            # API通信サービス
│   │   └── types/               # TypeScript型定義
│   ├── vite.config.ts           # Vite設定
│   └── package.json             # Node.js依存関係
├── data/                        # CSVデータディレクトリ
│   ├── dosha_*.csv              # 境界値データ
│   └── dosyakei_*.csv           # 土砂災害基準値
└── CLAUDE.md                    # プロジェクト仕様
```

## APIエンドポイント一覧

### メインAPI
| メソッド | パス | 説明 |
|---------|------|------|
| GET | `/` | APIルート情報 |
| GET | `/health` | ヘルスチェック |
| GET | `/data-check` | データ状態確認 |
| POST | `/production-soil-rainfall-index-with-urls` | 本番計算（セッション作成） |

### セッション管理API
| メソッド | パス | 説明 |
|---------|------|------|
| GET | `/session/<id>` | セッション情報取得 |
| GET | `/session/<id>/prefecture/<code>` | 府県データ取得 |
| GET | `/session/<id>/risk-at-time?ft=<ft>` | 指定時刻リスク値 |
| GET | `/session/<id>/mesh/<code>` | メッシュ詳細取得 |
| GET | `/session/<id>/rainfall-data` | 雨量データ取得 |
| POST | `/session/<id>/recalculate` | 雨量調整後再計算 |
| DELETE | `/session/<id>` | セッション削除 |
| GET | `/sessions` | セッション一覧 |
| GET | `/sessions/stats` | セッション統計 |
| POST | `/sessions/cleanup` | 古いセッション削除 |

### キャッシュAPI
| メソッド | パス | 説明 |
|---------|------|------|
| GET | `/cache/list` | キャッシュ一覧 |
| GET | `/cache/stats` | キャッシュ統計 |
| GET | `/cache/<key>` | キャッシュ取得 |
| DELETE | `/cache/<key>` | キャッシュ削除 |
| POST | `/cache/cleanup` | キャッシュクリーンアップ |

### 雨量調整API
| メソッド | パス | 説明 |
|---------|------|------|
| GET | `/rainfall-forecast` | 雨量予測データ取得 |
| POST | `/rainfall-adjustment` | 雨量調整リクエスト |

### 本番環境の注意事項
- リバースプロキシが `/api` プレフィックスを付与するため、Python側のエンドポイントにはプレフィックスなし
- `API_PREFIX` を `app.py` で一元管理（デフォルト: 空文字列）
- キャッシュディレクトリは環境変数 `CACHE_DIR` で設定可能
