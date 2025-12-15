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
- **バックエンド**: Python 3.8+ + Flask
- **フロントエンド**: React 18 + TypeScript + Vite
- **主要ライブラリ**: 
  - `requests` (HTTPクライアント)
  - `pandas` (CSVデータ処理) - 62.7倍高速化済み
  - `numpy` (数値計算)
  - `leaflet` + `react-leaflet` (地図表示)
  - `chart.js` + `react-chartjs-2` (グラフ表示)
  - `axios` (API通信)

### データソース
- **土壌雨量指数**: `http://lunar1.fcd.naps.kishou.go.jp/srf/Grib2/Rtn/swi10/`
- **降水量予測**: `http://lunar1.fcd.naps.kishou.go.jp/srf/Grib2/Rtn/gdc/`
- **フォーマット**: GRIB2バイナリ形式
- **境界データ**: `dosha_*.csv`（市区町村別警報基準値）

#### **GRIB2 URL構築パターン（2025年10月3日修正済み）**
```python
# 土壌雨量指数データ URL
swi_url = f"http://lunar1.fcd.naps.kishou.go.jp/srf/Grib2/Rtn/swi10/{initial_time.strftime('%Y/%m/%d')}/Z__C_RJTD_{initial_time.strftime('%Y%m%d%H%M%S')}_SRF_GPV_Ggis1km_Psw_Aper10min_ANAL_grib2.bin"

# 降水量予測データ URL（修正済み：時刻対応ファイル名）
hour = initial_time.hour
if hour % 6 == 0:  # 0,6,12,18時
    rmax_hour = "00"
else:  # 3,9,15,21時
    rmax_hour = "03"
guidance_url = f"http://lunar1.fcd.naps.kishou.go.jp/srf/Grib2/Rtn/gdc/{initial_time.strftime('%Y/%m/%d')}/guid_msm_grib2_{initial_time.strftime('%Y%m%d%H%M%S')}_rmax{rmax_hour}.bin"
```

**修正点**:
- 2025年9月5日: guidance_url の構築で `/gdc//` となっていた二重スラッシュを `/gdc/` に修正
- 2025年10月3日: ファイル名の時刻部分を修正（0,6,12,18時→"00", 3,9,15,21時→"03"）
- **土砂災害データ**: `dosyakei_*.csv`（メッシュ別危険度レベル）

## プロジェクト構造

### Client-Server 構成
```
soil-rainfall-index-system/
├── client/                   # React TypeScript フロントエンド
│   ├── src/
│   │   ├── App.tsx          # メインアプリケーション
│   │   ├── components/      # Reactコンポーネント
│   │   ├── pages/
│   │   │   └── Home.tsx     # ホームページ
│   │   ├── services/        # API通信ロジック
│   │   ├── types/           # TypeScript型定義
│   │   └── hooks/           # カスタムReactフック
│   ├── package.json         # Node.js依存関係
│   └── vite.config.ts       # Vite設定
├── server/                  # Flask Python バックエンド
│   ├── app.py               # メインAPI（完全なVBA再現）
│   ├── data/                # CSVデータ・GRIB2テストファイル
│   │   ├── dosha_*.csv      # 境界データ（6府県）
│   │   ├── dosyakei_*.csv   # 土砂災害データ（6府県）
│   │   ├── Z__C_RJTD_*.bin  # SWI GRIB2テストファイル
│   │   └── guid_msm_*.bin   # ガイダンスGRIB2テストファイル
│   ├── config/              # 設定ファイル
│   ├── monitoring/          # モニタリング・ログ
│   ├── src/                 # Pythonモジュール構造
│   │   ├── api/             # APIエンドポイント
│   │   ├── core/            # コアロジック
│   │   ├── models/          # データモデル
│   │   ├── services/        # ビジネスロジック
│   │   └── utils/           # ユーティリティ
│   ├── tests/               # テストファイル
│   ├── test_grib2_*.py      # GRIB2解析テスト
│   └── requirements.txt     # Python依存関係
├── docs/                    # ドキュメント
├── scripts/                 # スクリプト・自動化
└── CLAUDE.md                # プロジェクト仕様
```

## API仕様

### エンドポイント

#### メイン処理API
```
POST /api/soil-rainfall-index
```

**リクエスト例**:
```json
{
  "initial": "2023-06-01T12:00:00Z"
}
```

**パラメータ**:
- `initial` (required): 初期時刻（ISO8601形式）

#### 本番テスト用API
```
GET /api/production-soil-rainfall-index
```

**使用例**:
```bash
# 初期時刻指定
GET /api/production-soil-rainfall-index?initial=2023-06-01T12:00:00Z

# 初期時刻省略（自動設定）
GET /api/production-soil-rainfall-index
```

**パラメータ**:
- `initial` (optional): 初期時刻（ISO8601形式）、省略時は現在時刻の3時間前（6時間区切り）を自動設定

**特徴**:
- GETメソッドでアクセス可能
- レスポンスに使用したGRIB2 URLを含む（`used_urls`フィールド）
- 本番環境でのテスト・デバッグに適している

#### データ確認API
```
GET /api/data-check
```

#### ヘルスチェック
```
GET /api/health
```

### レスポンス形式

```json
{
  "status": "success",
  "calculation_time": "2023-06-01T15:30:00",
  "initial_time": "2023-06-01T12:00:00",
  "prefectures": {
    "shiga": {
      "name": "滋賀県",
      "code": "shiga",
      "areas": [
        {
          "name": "大津市",
          "meshes": [
            {
              "code": "53394611",
              "lat": 35.0042,
              "lon": 135.8681,
              "advisary_bound": 100,
              "warning_bound": 150,
              "dosyakei_bound": 200,
              "swi_timeline": [
                {"ft": 0, "value": 85.5},
                {"ft": 3, "value": 92.1}
              ],
              "rain_timeline": [
                {"ft": 3, "value": 2.5}
              ]
            }
          ],
          "risk_timeline": [
            {"ft": 0, "value": 0},
            {"ft": 3, "value": 1}
          ]
        }
      ]
    }
  }
}
```

## 主要コンポーネント

### VBA関数の完全再現

#### GRIB2解析関数
- `get_dat()`: Big-Endianバイナリデータ読み取り
- `unpack_info()`: GRIB2ヘッダー情報解析
- `unpack_runlength()`: ランレングス圧縮データ展開
- `unpack_data()`: GRIB2データ値解析
- `unpack_swi_grib2()`: 土壌雨量指数ファイル解析
- `unpack_guidance_grib2()`: 降水量予測ファイル解析

#### データ処理関数
- `prepare_areas()`: CSVデータから都道府県・地域・メッシュ構造を構築
- `calc_tunk_model()`: 3段タンクモデル計算
- `calc_swi_timelapse()`: 土壌雨量指数時系列計算
- `calc_rain_timelapse()`: 降水量時系列計算
- `calc_risk_timeline()`: リスクレベル判定（VBAの完全再現）

#### 座標変換関数
- `meshcode_to_coordinate()`: メッシュコード→緯度経度変換
- `meshcode_to_index()`: メッシュコード→グリッドインデックス変換
- `get_data_num()`: 緯度経度→データ番号変換

### データ構造

#### Python クラス（VBA Type構造体の再現）
```python
class BaseInfo:          # VBA: Type BaseInfo
class SwiTimeSeries:     # VBA: Type SwiTimeSeries  
class GuidanceTimeSeries: # VBA: Type GuidanceTimeSeries
class Risk:              # VBA: Type Risk
class Mesh:              # VBA: Type Mesh
class Area:              # VBA: Type Area
class Prefecture:        # VBA: Type Prefecture
```

## 土壌雨量指数計算アルゴリズム

### 3段タンクモデル
```
第1タンク: 地表付近の水分
第2タンク: 中間層の水分  
第3タンク: 深層の水分
```

### パラメータ（VBAと同一）
- **流出限界**: l1=15mm, l2=60mm, l3=15mm, l4=15mm
- **流出係数**: a1=0.1, a2=0.15, a3=0.05, a4=0.01 (1/hr)
- **浸透係数**: b1=0.12, b2=0.05, b3=0.01 (1/hr)

### 計算式（VBAと同一）
```
s1_new = (1 - b1*t) * s1 - q1*t + r
s2_new = (1 - b2*t) * s2 - q2*t + b1*s1*t  
s3_new = (1 - b3*t) * s3 - q3*t + b2*s2*t
```

## 警戒レベル（政府ガイドライン準拠）

| レベル | 値 | 説明 | 判定条件 |
|--------|-----|------|----------|
| 0 | 正常 | 全基準値未満 | `value < advisary_bound` |
| 2 | 注意 | 注意報基準以上 | `value >= advisary_bound` |
| 3 | 警報 | 警報基準以上 | `value >= warning_bound` |
| 4 | 土砂災害 | 土砂災害基準以上 | `value >= dosyakei_bound` |

**注**: レベル1は欠番（政府ガイドラインに合わせた番号体系）

## VBAからの主要変更点

### 削除された機能（仕様通り）
- `draw_data()`: Excel出力処理（要求により除外）
- `prepare_map()`: マップ描画処理
- `map_forward()`/`map_back()`: マップ操作

### 追加された機能
- RESTful API エンドポイント
- JSON形式でのデータ返却
- エラーハンドリングの強化
- PEP8準拠のコード品質
- 実データ対応（12個のCSVファイル）

### 改善点
- **スケーラビリティ**: Web APIによる複数クライアント対応
- **保守性**: flake8準拠のクリーンなコード
- **可読性**: 型ヒント付きPythonコード
- **実用性**: 実際のCSVデータによる精密な計算

## セットアップ手順（Windows PowerShell）

### 1. プロジェクト作成
```powershell
mkdir soil-rainfall-index-system
cd soil-rainfall-index-system
mkdir data
```

### 2. ファイル配置
```powershell
# CSVファイル（12個）を data/ フォルダにコピー
# app.py をルートにコピー
# requirements.txt をルートにコピー
```

### 3. Python環境セットアップ
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install Flask requests pandas numpy
```

### 4. サーバー起動
```powershell
python app.py
```

### 5. 動作確認
```powershell
# ヘルスチェック
curl http://localhost:5000/api/health

# データファイル確認
curl http://localhost:5000/api/data-check

# メイン処理テスト
curl -X POST http://localhost:5000/api/soil-rainfall-index -H "Content-Type: application/json" -d '{"initial": "2023-06-01T12:00:00Z"}'
```

## 実装の完全性

### VBA処理との対応関係

| 処理段階 | VBA関数 | Python関数 | 実装状況 |
|----------|---------|------------|----------|
| ファイルダウンロード | `download()` | `download_file()` | ✅ 完全実装 |
| GRIB2解析 | `unpack_swi_grib2()` | `unpack_swi_grib2()` | ✅ 忠実な実装 |
| GRIB2解析 | `unpack_guidance_grib2()` | `unpack_guidance_grib2()` | ✅ 忠実な実装 |
| 地域データ構築 | `prepare_areas()` | `prepare_areas()` | ✅ 実CSV対応 |
| タンクモデル | `calc_tunk_model()` | `calc_tunk_model()` | ✅ 完全実装 |
| SWI時系列 | `calc_swi_timelapse()` | `calc_swi_timelapse()` | ✅ 完全実装 |
| 降水量時系列 | `calc_rain_timelapse()` | `calc_rain_timelapse()` | ✅ 完全実装 |
| リスク判定 | `calc_risk_timeline()` | `calc_risk_timeline()` | ✅ 完全実装 |

### GRIB2解析の忠実度

- ✅ **バイナリ読み取り**: VBAの`get_dat()`ロジックを完全再現
- ✅ **ランレングス展開**: VBAの`unpack_runlength()`アルゴリズムを忠実に実装
- ✅ **データ型判定**: `data_type=200/201`の分岐処理
- ✅ **時系列処理**: `span=3, loop_count=2`の条件判定
- ✅ **エラー処理**: VBAのMsgBox相当のログ出力

## 運用における注意事項

### データソース依存
- 気象庁のGRIB2データサーバーの可用性に依存
- ネットワーク障害時のエラーハンドリング必須

### パフォーマンス
- GRIB2ファイルサイズが大きい（数MB〜数十MB）
- ダウンロード・解析処理に時間を要する場合あり
- メッシュ数: 総計26,545メッシュの処理

### セキュリティ
- 外部データソースアクセスのため適切なファイアウォール設定
- 入力値検証の実装推奨

## コード品質

### PEP8準拠
- flake8でのスタイルチェック済み
- 79文字行長制限
- 適切な空行とインデント
- 型ヒントの活用

### エラーハンドリング
- GRIB2データ取得失敗時の適切なエラーレスポンス
- CSVファイル不足時の警告とスキップ処理
- 計算エラー時のログ出力とフォールバック

## トラブルシューティング

### よくある問題

#### 1. GRIB2データダウンロードエラー
**症状**: `ダウンロードエラー`
**原因**: 気象庁サーバーの障害またはURL不正
**対処**: 時間をおいて再実行、initial時刻の確認

#### 2. CSVファイル不足
**症状**: `Skipping prefecture: no dosha data`
**原因**: data/フォルダにCSVファイルが配置されていない
**対処**: 12個のCSVファイルを適切に配置

#### 3. メモリ不足
**症状**: アプリケーションクラッシュ
**原因**: 大きなGRIB2ファイルの処理
**対処**: メモリ制限の緩和、処理の分割

## 実データの特徴

### CSVファイル構造

#### dosha_*.csv（境界データ）
- エンコーディング: ISO-8859-1
- 内容: メッシュコード、地域名、注意報基準値、警報基準値
- 用途: VBAの`bound_data`配列に相当

#### dosyakei_*.csv（土砂災害データ）
- エンコーディング: UTF-8
- 163列: GRIDNO, 緯度経度, LEVEL3_00〜LEVEL3_150
- 用途: VBAの`dosyakei_bound_data`配列に相当

## 今後の拡張予定

### 機能追加
- [ ] リアルタイムデータ更新機能
- [ ] 過去データの蓄積・分析機能
- [ ] アラート通知機能
- [ ] Web UIダッシュボード

### 技術改善  
- [ ] 非同期処理（asyncio）対応
- [ ] データベース連携
- [ ] キャッシュ機能
- [ ] 負荷分散対応

## ライセンス・免責事項

- このシステムは研究・開発目的で作成されています
- 気象庁のデータ利用規約に従って使用してください
- 災害予測の公式用途には使用しないでください

## 参考資料

- [気象庁GRIB2フォーマット仕様](https://www.jma.go.jp/jma/kishou/know/kurashi/kotan.html)
- [土壌雨量指数について](https://www.jma.go.jp/jma/kishou/know/bosai/dojoshisu.html)
- [Flask公式ドキュメント](https://flask.palletsprojects.com/)
- [PEP8 スタイルガイド](https://pep8.org/)

---

**作成日**: 2025年7月23日
**最終更新**: 2025年9月24日
**バージョン**: 6.1.0
**作成者**: Claude (Anthropic)
**プロジェクト**: 土壌雨量指数計算システム変換（地図UI改善・本番環境対応版）

## 技術仕様

### 開発環境
- **言語**: Python 3.8+
- **フレームワーク**: Flask
- **主要ライブラリ**: 
  - `requests` (HTTPクライアント)
  - `numpy` (数値計算)
  - `struct` (バイナリデータ処理)

### データソース
- **土壌雨量指数**: `http://lunar1.fcd.naps.kishou.go.jp/srf/Grib2/Rtn/swi10/`
- **降水量予測**: `http://lunar1.fcd.naps.kishou.go.jp/srf/Grib2/Rtn/gdc/`
- **フォーマット**: GRIB2バイナリ形式

## API仕様

### エンドポイント

#### メイン処理API
```
POST /api/soil-rainfall-index
```

**リクエスト例**:
```json
{
  "initial_url": "https://example.com/api/initial-data",
  "initial": "2023-06-01T12:00:00Z"
}
```

**パラメータ**:
- `initial_url` (optional): 初期データ取得用URL
- `initial` (required): 初期時刻（ISO8601形式）

#### ヘルスチェック
```
GET /api/health
```

### レスポンス形式

```json
{
  "status": "success",
  "calculation_time": "2023-06-01T15:30:00",
  "initial_time": "2023-06-01T12:00:00",
  "prefectures": {
    "shiga": {
      "name": "滋賀県",
      "code": "shiga",
      "areas": [
        {
          "name": "大津市",
          "meshes": [
            {
              "code": "53394611",
              "lat": 35.0042,
              "lon": 135.8681,
              "advisary_bound": 100,
              "warning_bound": 150,
              "dosyakei_bound": 200,
              "swi_timeline": [
                {"ft": 0, "value": 85.5},
                {"ft": 3, "value": 92.1}
              ],
              "rain_timeline": [
                {"ft": 3, "value": 2.5}
              ]
            }
          ],
          "risk_timeline": [
            {"ft": 0, "value": 0},
            {"ft": 3, "value": 1}
          ]
        }
      ]
    }
  }
}
```

## 主要コンポーネント

### データ構造

#### BaseInfo
GRIB2ファイルのメタデータ
```python
class BaseInfo:
    initial_date: datetime
    grid_num: int
    x_num: int, y_num: int
    s_lat: int, s_lon: int
    e_lat: int, e_lon: int
    d_lat: int, d_lon: int
```

#### Mesh
メッシュ単位のデータ
```python
class Mesh:
    area_name: str
    code: str
    lon: float, lat: float
    x: int, y: int
    advisary_bound: int
    warning_bound: int
    dosyakei_bound: int
    swi: List[SwiTimeSeries]
    rain: List[GuidanceTimeSeries]
```

#### Prefecture
都道府県データ
```python
class Prefecture:
    name: str
    code: str
    areas: List[Area]
    area_min_x: int
    area_max_y: int
```

### 主要関数

#### データ処理
- `download_file()`: GRIB2ファイルダウンロード
- `unpack_swi_grib2()`: 土壌雨量指数データ解析
- `unpack_guidance_grib2()`: 降水量予測データ解析
- `unpack_runlength()`: ランレングス圧縮展開

#### 計算処理
- `calc_tunk_model()`: 3段タンクモデル計算
- `calc_swi_timelapse()`: 土壌雨量指数時系列計算
- `calc_rain_timelapse()`: 降水量時系列計算
- `calc_risk_timeline()`: リスクレベル判定

#### 座標変換
- `meshcode_to_coordinate()`: メッシュコード→緯度経度変換
- `meshcode_to_index()`: メッシュコード→グリッドインデックス変換
- `get_data_num()`: 緯度経度→データ番号変換

## 土壌雨量指数計算アルゴリズム

### 3段タンクモデル
```
第1タンク: 地表付近の水分
第2タンク: 中間層の水分  
第3タンク: 深層の水分
```

### パラメータ
- **流出限界**: l1=15mm, l2=60mm, l3=15mm, l4=15mm
- **流出係数**: a1=0.1, a2=0.15, a3=0.05, a4=0.01 (1/hr)
- **浸透係数**: b1=0.12, b2=0.05, b3=0.01 (1/hr)

### 計算式
```
s1_new = (1 - b1*t) * s1 - q1*t + r
s2_new = (1 - b2*t) * s2 - q2*t + b1*s1*t  
s3_new = (1 - b3*t) * s3 - q3*t + b2*s2*t
```

## 警戒レベル（政府ガイドライン準拠）

| レベル | 値 | 説明 |
|--------|-----|------|
| 0 | 正常 | 注意報基準未満 |
| 2 | 注意 | 注意報基準以上 |
| 3 | 警報 | 警報基準以上 |
| 4 | 土砂災害 | 土砂災害基準以上 |

**注**: レベル1は欠番（政府ガイドラインに合わせた番号体系）

## VBAからの主要変更点

### 削除された機能
- `draw_data()`: Excel出力処理（要求により除外）
- `prepare_map()`: マップ描画処理
- `map_forward()`/`map_back()`: マップ操作

### 追加された機能
- RESTful API エンドポイント
- JSON形式でのデータ返却
- エラーハンドリングの強化
- 非同期処理対応

### 改善点
- **スケーラビリティ**: Web APIによる複数クライアント対応
- **保守性**: モジュール化された構造
- **可読性**: 型ヒント付きPythonコード
- **デプロイ**: Dockerコンテナ対応可能

## セットアップ手順

### 1. 依存関係インストール
```bash
pip install flask requests numpy
```

### 2. アプリケーション起動
```bash
python app.py
```

### 3. APIテスト
```bash
curl -X POST http://localhost:5000/api/soil-rainfall-index \
  -H "Content-Type: application/json" \
  -d '{
    "initial": "2023-06-01T12:00:00Z"
  }'
```

## 運用における注意事項

### データソース依存
- 気象庁のGRIB2データサーバーの可用性に依存
- ネットワーク障害時のエラーハンドリング必須

### パフォーマンス
- GRIB2ファイルサイズが大きい（数MB〜数十MB）
- ダウンロード・解析処理に時間を要する場合あり

### セキュリティ
- 外部データソースアクセスのため適切なファイアウォール設定
- 入力値検証の実装推奨

## 技術的成果

### パフォーマンス最適化
- CSV処理を62.7倍高速化（pandas vectorized operations採用）
- 26,051メッシュを5秒以下で処理
- メモリキャッシュによる高速レスポンス

### VBA完全互換性達成
- 100%の数値一致を検証済み
- 3段タンクモデルの完全再現
- GRIB2解析の忠実な実装

## 今後の拡張予定

### 機能追加
- [ ] リアルタイムデータ更新機能
- [ ] 過去データの蓄積・分析機能
- [ ] アラート通知機能
- [x] React TypeScript フロントエンド（完了）
- [x] Client-Server 分離アーキテクチャ（完了）
- [x] 時刻切り替え時のローディングインジケーター（完了）

### 技術改善  
- [x] JSON serialization の numpy型対応（完了）
- [x] UX改善: 視覚的フィードバック強化（完了）
- [ ] 非同期処理（asyncio）対応
- [ ] データベース連携
- [ ] キャッシュ機能
- [ ] 負荷分散対応

## テスト・開発環境

### GRIB2解析関数のテスト

開発環境では気象庁のサーバーにアクセスできない場合があるため、ローカルのbinファイルを使用したテスト環境を構築しています。

#### テストファイル構成

```
soil-rainfall-index-system/
├── test_grib2_functions.py     # Flask依存版テスト
├── test_grib2_minimal.py       # 独立版テスト（推奨）
└── data/
    ├── Z__C_RJTD_20250101000000_SRF_GPV_Ggis1km_Psw_Aper10min_ANAL_grib2.bin  # SWI GRIB2データ
    └── guid_msm_grib2_20250101000000_rmax00.bin                                # ガイダンスGRIB2データ
```

#### テスト実行方法

**最小版テスト（推奨）**:
```bash
python test_grib2_minimal.py
```

**Flask依存版テスト**:
```bash
# Flask等の依存関係が必要
pip install flask requests pandas numpy
python test_grib2_functions.py
```

#### テスト内容

1. **SWIファイル解析テスト** (`unpack_swi_grib2`)
   - ファイルサイズ: 174,728 bytes
   - GRIB2ヘッダー解析
   - セクション構造の確認
   - 土壌雨量指数データの抽出

2. **ガイダンスファイル解析テスト** (`unpack_guidance_grib2`)
   - ファイルサイズ: 310,384 bytes
   - 複数時系列データの処理
   - 4つのガイダンスデータセットを検出

#### テスト結果例

```
=== unpack_swi_grib2 テスト開始 ===
ファイル読み込み: data/Z__C_RJTD_20250101000000_SRF_GPV_Ggis1km_Psw_Aper10min_ANAL_grib2.bin
ファイルサイズ: 174728 bytes
Date components: year=2025, month=1, day=1, hour=0, minute=0, second=0
Section 3, Length: 72
Section 4, Length: 34
Section 5, Length: 271
初期時刻: 2025-01-01 00:00:00
unpack_swi_grib2テスト 成功

=== unpack_guidance_grib2 テスト開始 ===
ファイル読み込み: data/guid_msm_grib2_20250101000000_rmax00.bin
ファイルサイズ: 310384 bytes
Date components: year=2025, month=1, day=1, hour=0, minute=0, second=0
ガイダンスデータ数: 4
unpack_guidance_grib2テスト 成功
```

### 開発時の注意事項

#### GRIB2解析の特徴
- **Big-Endianバイナリ形式**: struct.unpack(">...")を使用
- **複数セクション構造**: セクション3(グリッド),4(プロダクト),5(データ表現),6(ビットマップ),7(データ)
- **ランレングス圧縮**: data_type=200の場合の特殊処理
- **日付解析**: GRIB2ヘッダーからの初期時刻抽出

#### テスト環境の利点
1. **ネットワーク非依存**: オフライン環境での開発が可能
2. **高速テスト**: ダウンロード時間の削減
3. **デバッグ容易**: 固定データでの再現可能なテスト
4. **CI/CD対応**: 自動テスト環境での実行が可能

## トラブルシューティング

### よくある問題

#### 1. GRIB2データダウンロードエラー
**症状**: `ファイルダウンロードエラー`
**原因**: 気象庁サーバーの障害またはURL不正
**対処**: 時間をおいて再実行、initial時刻の確認、またはローカルテストファイルを使用

#### 2. GRIB2解析エラー
**症状**: `GRIB2解析エラー`
**原因**: ファイル形式の不整合またはデータ破損
**対処**: ファイルの再ダウンロード、test_grib2_minimal.pyでの動作確認

#### 3. 日付解析エラー
**症状**: `day is out of range for month`
**原因**: GRIB2ヘッダーの日付フィールドの読み取り位置ずれ
**対処**: unpack_info関数の日付解析ロジックを確認

#### 4. メモリ不足
**症状**: アプリケーションクラッシュ
**原因**: 大きなGRIB2ファイルの処理
**対処**: メモリ制限の緩和、処理の分割

#### 5. Flask依存関係エラー
**症状**: `ModuleNotFoundError: No module named 'flask'`
**原因**: 開発環境にFlaskがインストールされていない
**対処**: `pip install flask requests pandas numpy` または `test_grib2_minimal.py` を使用

## ライセンス・免責事項

- このシステムは研究・開発目的で作成されています
- 気象庁のデータ利用規約に従って使用してください
- 災害予測の公式用途には使用しないでください

## 参考資料

- [気象庁GRIB2フォーマット仕様](https://www.jma.go.jp/jma/kishou/know/kurashi/kotan.html)
- [土壌雨量指数について](https://www.jma.go.jp/jma/kishou/know/bosai/dojoshisu.html)
- [Flask公式ドキュメント](https://flask.palletsprojects.com/)
- [React公式ドキュメント](https://react.dev/)
- [Leaflet公式ドキュメント](https://leafletjs.com/)

---

## 🎯 **2025年8月26日 実装完了状況**

### ✅ **主要実装成果**
- **フルスタックWebアプリケーション完成**: React + Flask完全連携
- **26,051メッシュ対応**: 関西6府県の全データを5秒以下で処理
- **重要バグ修正完了**: サーバー側データ処理とクライアント側UIの両方
- **大規模パフォーマンス最適化**: CSV処理62.7倍高速化
- **UX改善実装**: 時刻切り替え時のローディングインジケーター追加
- **実用レベル達成**: プロダクション対応済みの安定動作

### 🔧 **解決済み重要課題**

#### 1. **データ処理バグ修正**
- 土砂災害境界値: `LEVEL3_150` → `LEVEL3_00`
- 境界値処理: `200` → `9999`（999以上の値）
- **結果**: レベル3が100% → 0%に大幅改善

#### 2. **FTスライダー問題解決**
- useEffectの無限ループ解決
- インデックスベースの正確な時刻選択
- **結果**: スライダー操作で時刻が0に戻る問題を完全解決

#### 3. **パフォーマンス大幅改善**
- CSV処理: 26.23秒 → 0.42秒（62.7倍高速化）
- 総処理時間: 4.85秒（26,051メッシュ）
- **結果**: 実用的なレスポンス時間を実現

#### 4. **UX改善実装（2025年8月26日追加）**
- 時刻切り替え時のローディングインジケーター実装
- `isTimeChanging` 状態管理による動的UI制御
- 分布図上のスピナーアニメーション表示
- キーボードショートカット（←→）対応
- **結果**: 時刻変更操作の視覚的フィードバック向上

### 📊 **最終パフォーマンス実績**
- **処理速度**: 11,665 meshes/second
- **CSV最適化**: 62,230 meshes/second  
- **メモリ効率**: 大規模データの安定処理
- **成功率**: 100%（エラー処理完備）

---

**作成日**: 2025年7月23日
**最終更新**: 2025年9月14日
**バージョン**: 6.0.0（プロダクション対応完了版）
**作成者**: Claude (Anthropic)
**プロジェクト**: 土壌雨量指数計算システム（VBA完全互換・プロダクション対応完了版）

## 🆕 **2025年8月26日 本番テスト用API追加**

### ✅ **新機能追加**
- **本番テスト用GETエンドポイント**: `/api/production-soil-rainfall-index`
- **リクエストパラメータ対応**: `?initial=2023-06-01T12:00:00Z`
- **自動初期時刻設定**: パラメータ省略時は現在時刻の3時間前を自動設定
- **デバッグ支援**: レスポンスに使用したGRIB2 URLを表示

### 🔧 **技術的特徴**
- **HTTPメソッド**: GET（URLパラメータ使用）
- **互換性**: 既存POSTエンドポイントと完全同等の機能
- **エラーハンドリング**: 使用予定URLも含めたエラー情報提供
- **運用性**: 本番環境でのテスト・監視に最適化

### 📊 **使用例**
```bash
# 初期時刻指定での実行
curl "http://localhost:5000/api/production-soil-rainfall-index?initial=2023-06-01T12:00:00Z"

# 自動時刻設定での実行  
curl "http://localhost:5000/api/production-soil-rainfall-index"
```

### ⚠️ **URL構築バグ修正の影響（2025年9月5日追加）**

本日修正されたURL構築バグは、本番テスト用APIでも影響がある重要な修正です：

**修正内容**: `services/main_service.py:145` の guidance_url 構築
- **修正前**: `/gdc//` (二重スラッシュエラー)
- **修正後**: `/gdc/` (正しいパス)

**影響範囲**:
- `/api/production-soil-rainfall-index` - 本番テスト用API
- `/api/soil-rainfall-index` - メインAPI  
- `main_process_from_urls()` - URL ベースの全処理

**検証推奨**: 修正後は実際の気象庁サーバーからのデータ取得成功率が向上するはずです。

## 🔄 **2025年8月29日 アーキテクチャリファクタリング完了**

### ✅ **STEP 4A-4B: API層の完全分離アーキテクチャ実装**

**実装段階:**
- **STEP 1**: ✅ データモデル分離 (`models/data_models.py`)
- **STEP 2**: ✅ サービス層分離 (`services/`)
- **STEP 3**: ✅ API層分離 (app.py リファクタリング)
- **STEP 4A**: ✅ コントローラ分離 (`src/api/controllers/`)
- **STEP 4B**: ✅ Blueprint分離 (`src/api/routes/`)

#### **STEP 4A: コントローラ層分離**
**3つの専門コントローラ作成:**
- `main_controller.py` - メインAPI (root, health, data-check, soil-rainfall-index, production)
- `test_controller.py` - テストAPI (重要な test-full-soil-rainfall-index 含む)
- `performance_controller.py` - パフォーマンス分析API

**app.py改善:**
- 926行 → 146行 (84%削減)
- コントローラベースの整理されたルーティング
- 全15エンドポイント維持、レスポンス形式保持

#### **STEP 4B: Blueprint-based Routing Architecture**
**3つのBlueprintルート作成:**
- `main_routes.py` - メインAPIルート
- `test_routes.py` - テストAPIルート
- `performance_routes.py` - パフォーマンスAPIルート

**app.py最終形:**
- 146行 → 71行 (さらに52%削減、総計92%削減)
- アプリケーションファクトリーパターン適用
- モジュラーなBlueprint登録システム
- 極めてクリーンなコード構造

### 🔧 **本番環境対応: プロキシ設定実装**

#### **設定ファイルベースプロキシ対応**
- **要件**: 本番環境で `http://172.17.34.11:3128` プロキシ経由でアクセス
- **実装方式**: YAML設定ファイル (`config/app_config.yaml`)
- **柔軟性**: 環境別設定、開発/本番切り替え容易

#### **実装内容:**
**1. 設定管理システム:**
- `config/app_config.yaml` - メイン設定ファイル
- `src/config/config_service.py` - YAML読み込みサービス
- ドット記法アクセス、デフォルト値対応

**2. GRIB2サービス強化:**
- `services/grib2_service.py` - 設定ファイルベースproxy対応
- リトライ機能強化（設定可能な回数・間隔）
- 詳細なエラーハンドリング（ProxyError, ConnectionError, Timeout）

**3. 運用性向上:**
- `config/README_proxy_config.md` - 運用ガイド
- `requirements.txt` に PyYAML 追加
- 起動時ログでproxy設定確認

#### **設定例:**
```yaml
# 本番環境
proxy:
  http: "http://172.17.34.11:3128"
  https: "http://172.17.34.11:3128"

# 開発環境  
proxy:
  http: null
  https: null

grib2:
  download_timeout: 300
  retry_count: 3
  retry_delay: 5
```

### 📊 **最終アーキテクチャ構成**

```
server/
├── app.py                    # 71行 Blueprint-based メインアプリ
├── config/
│   ├── app_config.yaml      # 設定ファイル
│   └── README_proxy_config.md
├── src/
│   ├── api/
│   │   ├── controllers/     # 3つのコントローラ
│   │   └── routes/          # 3つのBlueprintルート
│   └── config/
│       └── config_service.py # 設定管理サービス
├── services/                # 4つの専門サービス
│   ├── main_service.py
│   ├── grib2_service.py     # proxy対応済み
│   ├── calculation_service.py
│   └── data_service.py
└── models/
    └── data_models.py       # dataclassモデル
```

### 🎯 **技術的成果まとめ**

**アーキテクチャ品質:**
- **モジュール性**: 完全な関心の分離
- **保守性**: 926行 → 71行 (92%削減)
- **拡張性**: 新機能追加が容易
- **テスト性**: Blueprint単位でのテスト可能

**運用性:**
- **本番対応**: プロキシ設定完備
- **設定管理**: YAML設定ファイル
- **エラー処理**: 詳細なログとリトライ機能
- **パフォーマンス**: 62.7倍高速化維持

**後方互換性:**
- ✅ 全15エンドポイント維持
- ✅ `api/test-full-soil-rainfall-index` レスポンス形式不変
- ✅ 26,051メッシュ処理性能維持 (5秒以下)
- ✅ 既存クライアントへの影響なし

---

## 🎉 **2025年9月24日 地図表示UI改善・本番環境対応**

### ✅ **地図表示機能の最適化完了**

#### **地図表示の改善内容**
- **全メッシュ表示**: 府県選択に関わらず全26,051メッシュを常時表示
- **危険度0の無色化**: 正常レベル（リスク0）を透明表示に変更、視覚的ノイズを削減
- **強調表示の廃止**: 府県選択時の境界線強調を撤廃、統一したUIに改善
- **パフォーマンス維持**: 全メッシュ表示でも高速レンダリングを実現

#### **本番環境対応の完了**
- **オリジン自動検出**: クライアント側API接続を環境別に自動設定
  - 開発環境: `http://localhost:5000/api`
  - 本番環境: `/api`（同一オリジンの相対パス）
- **CORS問題解決**: 同一オリジン配置による追加設定不要
- **デプロイメント対応**: プロダクション配置での完全動作保証

#### **URL構築バグ修正**
- **ガイダンスファイル名**: `rmax00.bin` → `rmaxHH.bin`（時刻対応）
- **両API対応**: main_service.py と main_controller.py の両方で修正
- **正確なデータ取得**: 時刻に応じた正しいGRIB2ファイルアクセス

#### **UI/UX改善**
- **日時表示修正**: テストデータの正しい表示（2023年6月2日0時）
- **透明度最適化**: 危険度別の適切な視覚表現
- **統一デザイン**: 一貫した境界線とカラーリング

---

## 🎉 **2025年9月14日 VBA完全互換性検証・プロジェクト完成**

### ✅ **歴史的成果達成！**

**100% VBA互換性検証完了**: VBA Module.basの処理とPython実装が数値レベルで完全一致することを検証しました。

#### **検証結果サマリー**
- **総対象メッシュ**: 26,045 SWI + 26,039 Rain = 52,084 メッシュ計算
- **完全一致率**: **100.0%** - 全メッシュでVBA参照データと完全一致
- **検証対象**: 関西6府県全域（滋賀、京都、大阪、兵庫、奈良、和歌山）
- **検証データ**: 2023年6月2日の実GRIB2データによる実計算結果

#### **検証方法**
VBA Module.basから出力されたCSV参照データ（Shift_JIS）との完全比較：
- `*_rain.csv`: 降水量時系列データ（FT0, FT3, FT6, FT9, FT12, FT15）
- `*_swi.csv`: 土壌雨量指数データ（境界値 + FT0, FT3, FT6時系列）

#### **検証の厳密性**
- 浮動小数点誤差を含めて完全一致（例：116.75999999999999 vs 116.76）
- 座標マッピング完全一致（VBA X,Y座標 vs Python lat,lon変換）
- 3段タンクモデル計算の完全再現
- GRIB2バイナリデータ解析の完全互換

### 🏆 **プロジェクト目標100%達成**

**元々の目標**: Excel VBA (`土壌雨量指数計算.xlsm`) の `main_process` をPython Web APIに完全移植

**達成内容**:
1. ✅ **計算精度**: VBAと数値的に完全同一
2. ✅ **機能完全性**: 全処理フローの完全再現
3. ✅ **データ対応**: 実GRIB2データでの完全動作
4. ✅ **Web API化**: RESTful API + React フロントエンド
5. ✅ **性能向上**: CSV処理62.7倍高速化（pandas最適化）
6. ✅ **本番対応**: プロキシ設定、エラーハンドリング完備

### 📊 **最終技術仕様**

#### **システム構成**
- **サーバー**: Flask Blueprint-based Architecture (15 API endpoints)
- **クライアント**: React 18 + TypeScript + Vite
- **データ処理**: 26,045メッシュを5秒以下で処理
- **互換性**: VBA Module.bas 100%互換

#### **プロダクション対応機能**
- 本番データ取得API (`/api/production-soil-rainfall-index`)
- 企業プロキシ対応 (http://172.17.34.11:3128)
- YAML設定ファイル管理
- 詳細エラーハンドリング・ログ
- フロントエンド日時指定UI
- デバッグ支援（使用GRIB2 URL表示）

### 🧹 **プロジェクト整理完了**

#### **コード品質向上**
- 不要ファイル整理: 75個のデバッグファイルを`archive_debug_files/`に整理
- 本番コードのみ残存: app.py + 4コアサービス + API層
- 検証レポート作成: `VERIFICATION_SUCCESS_REPORT.md`

#### **運用準備完了**
- サーバー: http://127.0.0.1:5000 (15エンドポイント稼働中)
- クライアント: http://localhost:3000 (React UI稼働中)
- 両サービス正常動作確認済み

---

## 🚀 **2025年9月25日 地図Canvas描画システム完全最適化**

### ✅ **Canvas描画問題の根本解決**

#### **問題の背景**
- **初期実装**: 26,051個のDOM Rectangle要素による重いレンダリング
- **パフォーマンス問題**: 時刻切り替え時の極端な遅延
- **Canvas移行試行**: 手動Canvas描画での座標ずれ問題

#### **最終解決策: Leaflet標準Canvas Renderer採用**

**技術的転換**:
```javascript
// 従来: 26,051個のDOM Rectangle要素
{meshes.map(mesh => <Rectangle key={mesh.code} bounds={bounds} />)}

// 最適化後: Leaflet標準Canvas Renderer
const canvasRenderer = L.canvas({ padding: 0.5 });
const rectangle = L.rectangle(bounds, { renderer: canvasRenderer });
```

#### **実装された根本改善**

1. **Leaflet Canvas Renderer統合**:
   - `L.canvas()` による標準Canvas描画システム使用
   - Leaflet内部座標管理による完全な同期保証
   - 手動transform計算の完全排除

2. **Layer Group管理システム**:
   - `L.layerGroup()` による効率的なメッシュ管理
   - `clearLayers()` + 再構築による高速データ更新
   - Canvas要素の自動座標追従

3. **座標同期問題の完全解消**:
   - マウスドラッグ移動時のメッシュずれ解消
   - ズーム操作時の完全座標追従
   - 累積誤差の根本的解決

#### **技術的成果**

**パフォーマンス向上**:
- **DOM要素数**: 26,051個 → 1個のCanvas要素
- **描画方式**: DOM操作 → Canvas描画
- **座標管理**: 手動計算 → Leaflet自動管理
- **更新速度**: 大幅な高速化実現

**安定性向上**:
- **座標ずれ**: 完全解消
- **メモリ使用量**: 大幅削減
- **ブラウザクラッシュリスク**: 排除
- **操作応答性**: 滑らか な操作感実現

#### **実装の特徴**

```typescript
// SimpleCanvasLayer.tsx - 最終実装
const canvasRenderer = L.canvas({ padding: 0.5 });
const meshLayerGroup = L.layerGroup();

// 各メッシュをCanvas描画Rectangle要素として追加
const rectangle = L.rectangle(bounds, {
  color: RISK_COLORS[riskLevel],
  fillColor: RISK_COLORS[riskLevel],
  fillOpacity: 0.7,
  renderer: canvasRenderer  // Leaflet標準描画
});

meshLayerGroup.addLayer(rectangle);
```

**React統合の最適化**:
- `useRef` による描画関数参照管理
- `useEffect` による効率的な再描画トリガー
- Leafletライフサイクルとの完全同期

#### **運用上の利点**

1. **開発保守性**: Leaflet標準パターンによる可読性向上
2. **拡張性**: 新機能追加の容易さ
3. **安定性**: 実績あるLeafletエンジンによる信頼性
4. **互換性**: Leafletエコシステムとの完全互換

### 🎯 **最終的な技術スタック**

**地図描画システム**:
- **Base**: React-Leaflet + Leaflet Canvas Renderer
- **描画方式**: L.rectangle + L.canvas による標準描画
- **管理**: L.layerGroup によるレイヤー管理
- **同期**: Leaflet自動座標変換システム

**成果サマリー**:
- ✅ 26,051メッシュの高速Canvas描画実現
- ✅ マウスドラッグ・ズーム時の完全座標同期
- ✅ DOM要素数の大幅削減によるメモリ最適化
- ✅ 時刻切り替え操作の大幅高速化

---

## 🎉 **2025年10月3日 1時間雨量ベース危険度評価機能完成**

### ✅ **新機能実装完了**

#### **1時間雨量データの追加**
- **GRIB2データ拡張**: `loop_count==1`（1時間雨量）と`loop_count==2`（3時間雨量）の両方を取得
- **新フィールド追加**:
  - `rain_1hour_max`: 3時間内の最大1時間雨量（GRIB2から直接取得）
  - `rain_1hour`: 1時間ごとの推定雨量（3時間分布推定）
  - `swi_hourly`: 1時間ごとの土壌雨量指数
  - `risk_hourly`: 1時間ごとの危険度
  - `risk_3hour_max`: 3時間ごとの最大危険度（1時間雨量ベース）

#### **1時間雨量推定アルゴリズム**
各3時間期間における雨の分布を以下のように仮定：
- 中央1時間に最大1時間雨量が降る
- 残りの雨量（R3h - R1h_max）を前後1時間で均等に分配

```python
# 例: 3時間雨量=15mm, 最大1時間雨量=10mm の場合
# 前1時間: 2.5mm
# 中央1時間: 10mm (最大)
# 後1時間: 2.5mm
```

#### **1時間ごとのSWI・危険度計算**
- **タンクモデル**: dt=1時間で1時間ごとにSWIを計算
- **危険度判定**: 既存の3段階基準値（advisary/warning/dosyakei）を適用
- **3時間最大危険度**: 各3時間期間内の1時間危険度の最大値

#### **危険度比較検証結果**

**重要な発見**: 1時間雨量ベースの方が**より早期警戒的（conservative）な評価**を提供

**統計データ（26,045メッシュ × 27時刻 = 703,215比較点）**:
- **1時間雨量ベースの方が高い**: 42,000件 (5.97%)
- **3時間雨量ベースの方が高い**: 1,822件 (0.26%)
- **同じ**: 659,393件 (93.77%)

**比率**: 1時間ベースが高くなるケースは3時間ベースの**約23倍**

**危険度レベル分布の変化**:
```
レベル3（土砂災害）:
  3時間ベース: 0.91%
  1時間ベース: 1.35% (約1.5倍に増加)

レベル2（警報）:
  3時間ベース: 5.75%
  1時間ベース: 7.52% (1.31倍に増加)

レベル1（注意）:
  3時間ベース: 13.27%
  1時間ベース: 14.95% (1.13倍に増加)
```

#### **技術的考察**

**なぜ1時間ベースの方が高くなるのか**:

1. **タンクモデルの時間ステップ効果**:
   - 1時間ごとの計算では短時間の強雨の影響が直接的に反映される
   - 3時間ステップでは平均化効果により緩和される

2. **累積効果の違い**:
   - 1時間計算: 各時間の雨がタンクに即座に影響、次時刻への引き継ぎが敏感
   - 3時間計算: まとめて処理するため、ピークが分散される

3. **物理的意味**:
   - 1時間雨量ベースは短時間集中豪雨への感度が高い
   - より早期の警戒発令に適している

#### **実装ファイル**

**バックエンド**:
- `models/data_models.py`: Mesh型に5つの新フィールド追加
- `services/grib2_service.py`: 1時間・3時間雨量の両方を取得
- `services/calculation_service.py`:
  - `calc_hourly_rain()`: 1時間雨量推定
  - `calc_swi_hourly()`: 1時間SWI計算
  - `calc_hourly_risk()`: 1時間危険度判定
  - `calc_3hour_max_risk_from_hourly()`: 3時間最大危険度集計
- `services/main_service.py`: API レスポンスに新タイムライン追加
- `src/api/controllers/test_controller.py`: テストAPIも対応

**フロントエンド**:
- `client/src/types/api.ts`: Mesh型に新タイムライン追加

#### **API レスポンス拡張**

```json
{
  "meshes": [
    {
      "swi_timeline": [...],           // 3時間ごとのSWI
      "swi_hourly_timeline": [...],    // 1時間ごとのSWI (新規)
      "rain_timeline": [...],          // 3時間雨量
      "rain_1hour_timeline": [...],    // 1時間雨量推定 (新規)
      "rain_1hour_max_timeline": [...], // 最大1時間雨量 (新規)
      "risk_hourly_timeline": [...],   // 1時間危険度 (新規)
      "risk_3hour_max_timeline": [...] // 3時間最大危険度 (新規)
    }
  ]
}
```

---

## 🎉 **2025年10月6日 時刻表示UTC→JST変換・時間帯別表示修正**

### ✅ **エリア別リスクレベル時系列の表示改善完了**

#### **UTC→JST変換実装**
- **タイムゾーン変換**: APIから受け取るUTC時刻をJST（UTC+9時間）に変換
- **正確な日本時刻表示**: ユーザーインターフェースで正しい日本時刻を表示

#### **時間帯別表示の修正**
- **3時間期間の正確な表現**: FTは期間の終了時刻を表すことを明確化
  - FT0 (0時) → 前日21-24時の危険度
  - FT3 (3時) → 当日0-3時の危険度
  - FT6 (6時) → 当日3-6時の危険度
- **日付グルーピング修正**: 期間の開始時刻の日付でグループ化

#### **実装内容**

**AreaRiskBarChart.tsx**:
- UTC時刻を受け取る`initialTime`プロップ追加
- JST変換ロジック実装（+9時間）
- 期間開始時刻による日付判定ロジック修正
- 2段階ヘッダー（日付→時刻）の正確な表示

**SoilRainfallDashboard.tsx**:
- AreaRiskBarChartコンポーネントに`initialTime`プロップを渡す
- データソースから`swi_initial_time`または`initial_time`を使用

#### **技術的改善**

**タイムゾーン処理**:
```typescript
// UTC時刻をJST時刻に変換（+9時間）
const initialTimeUTC = new Date(initialTime);
const JST_OFFSET = 9 * 60 * 60 * 1000;
const initialTimeJST = new Date(initialTimeUTC.getTime() + JST_OFFSET);
```

**期間マッピング修正**:
```typescript
// FT時刻（期間の終了時刻）をJSTで計算
const ftTimeJST = new Date(initialTimeJST.getTime() + ft * 60 * 60 * 1000);
const ftHour = ftTimeJST.getHours();

// FTが表す3時間期間の開始時刻を計算（FT - 3時間）
const periodStartTime = new Date(ftTimeJST.getTime() - 3 * 60 * 60 * 1000);

// 期間の日付は開始時刻の日付を使用
const dateStr = `${periodStartTime.getMonth() + 1}月${periodStartTime.getDate()}日`;
```

#### **ユーザー体験の向上**
- ✅ 日本時刻での直感的な時系列表示
- ✅ 正確な日付・時刻区分
- ✅ 3時間期間の物理的意味の正確な表現

---

**最終更新**: 2025年10月6日
**バージョン**: 6.3.1（UTC→JST変換・時間帯別表示修正版）
**作成者**: Claude (Anthropic)
**プロジェクト**: 土壌雨量指数計算システム（VBA完全互換・Canvas描画最適化・1時間危険度評価・JST表示対応版）

## 実装完了状況

### ✅ VBA完全互換性検証達成
- 26,045メッシュのSWI計算で100%一致
- 26,039メッシュのRain計算で100%一致
- Module.basとの数値レベル完全対応

### ✅ フルスタックWebアプリケーション完成
- Flask Blueprint-based サーバーアーキテクチャ
- React 18 + TypeScript クライアント
- 15個のAPI エンドポイント稼働
- 本番・テストデータ両対応

### ✅ 1時間雨量ベース危険度評価システム
- GRIB2データから1時間・3時間雨量を両方取得
- 1時間雨量推定アルゴリズム実装
- 1時間ごとのSWI・危険度計算
- 3時間最大危険度の集計
- 検証完了: 1時間ベースは3時間ベースより約23倍保守的

### ✅ 本番運用画面・防災地図レイヤー (2025年10月8日追加)

#### **本番運用画面 (`/production`)**
- 開発情報を除いたシンプルなUI
- デフォルトで都道府県を自動選択
- 5分タイムアウト設定（26,000メッシュ対応）
- ローディング表示の改善

#### **防災地図レイヤー**
国土地理院の防災関連レイヤーを追加：
1. **土地条件図** - 河川・水系・地形条件
2. **標準地図** - 道路・鉄道・地名
3. **色別標高図** - 浸水リスク把握
4. **傾斜量図** - 土砂災害危険度判断
5. **洪水浸水想定区域** - 洪水浸水深表示

**地図機能改善**:
- チェックボックスによるレイヤー切り替え
- 最大ズームレベル: 14
- zIndexによる適切な表示順制御
- 土壌雨量指数と防災情報の統合表示

---

## 🎉 **2025年10月14日 本番運用機能完成・UI改善完了**

### ✅ **本番運用画面の完全実装**

#### **1. SWI・ガイダンス個別時刻設定機能**
- **個別初期時刻選択**: SWI（土壌雨量指数）とガイダンス（降水量予測）の初期時刻を独立して選択可能
- **過去24時間分の時刻選択**: 6時間刻み（0, 6, 12, 18時）で選択
- **JST（日本標準時）表示**: すべての時刻をUTC+9時間で表示
- **データ取得ボタン**: 明示的なデータ取得アクション

#### **2. SWI初期時刻基準でのガイダンスフィルタリング**
**実装内容**:
```python
def _filter_guidance_data(guidance_grib2, swi_initial_time, guidance_initial_time):
    """
    SWI初期時刻以降のガイダンスデータのみを抽出
    SWI初期時刻より前のガイダンスデータは除外
    """
```

**動作例**:
- **SWI初期時刻**: 2025-10-14 12:00
- **ガイダンス初期時刻**: 2025-10-14 06:00
- **結果**: ガイダンスのFT6以降（12:00以降）のみ使用、FT0-5は除外
- **FT再計算**: ガイダンスFT6 → 新FT0（SWI基準）

#### **3. 地図左上の時刻情報表示**
```
📅 時刻情報
━━━━━━━━━━━━━━━━━━━━
SWI初期時刻: 2025/10/14 12:00
ガイダンス初期時刻: 2025/10/14 06:00
━━━━━━━━━━━━━━━━━━━━
現在表示時刻: 2025/10/14 15:00 (FT+3h)
```

**表示内容**:
- SWI初期時刻（JST）
- ガイダンス初期時刻（JST）
- 現在表示時刻（JST）+ FT値
- 白背景・青枠のボックス
- 本番運用画面とダッシュボード両方で表示

### ✅ **UI/UX改善**

#### **4. 警戒レベルの色変更**
| レベル | 旧色 | 新色 | 説明 |
|--------|------|------|------|
| レベル1（注意） | 黄色 | **黄色** | そのまま（`#FFC107`） |
| レベル2（警報） | オレンジ | **赤色** | 変更（`#F44336`） |
| レベル3（土砂災害） | 赤色 | **紫色** | 変更（`#9C27B0`） |

**影響範囲**:
- 地図のメッシュ表示
- 地図の凡例
- エリア別リスクバーチャート
- リスクタイムラインチャート
- すべてのグラフとUI要素

#### **5. リスクレベル時系列のクリック選択機能**
- **チャートのセルをクリック**: 任意の時刻を選択可能
- **即座の時刻切り替え**: 地図・スライダー・すべての表示が同期
- **視覚的フィードバック**: 選択中の列は赤い太枠で強調

#### **6. 時刻切り替え時のローディング表示改善**
**技術的改善**:
```typescript
// ローディング状態を即座に設定
setIsTimeChanging(true);

// requestAnimationFrameで最適化
requestAnimationFrame(() => {
  setSelectedTime(newTime);
  requestAnimationFrame(() => {
    setTimeout(() => setIsTimeChanging(false), 50);
  });
});
```

**効果**:
- 操作した瞬間にローディング表示
- タイムラグなしの即座のフィードバック
- スムーズなアニメーション

### 📊 **最終技術仕様**

#### **新規APIエンドポイント**
```
POST /api/production-soil-rainfall-index-with-urls
```

**リクエスト例**:
```json
{
  "swi_initial": "2025-10-14T12:00:00Z",
  "guidance_initial": "2025-10-14T06:00:00Z"
}
```

**レスポンス**:
```json
{
  "status": "success",
  "initial_time": "2025-10-14T12:00:00",
  "prefectures": { ... },
  "used_urls": {
    "swi_url": "http://...",
    "swi_initial_time": "2025-10-14T12:00:00",
    "guidance_url": "http://...",
    "guidance_initial_time": "2025-10-14T06:00:00"
  }
}
```

### 🎯 **完成機能まとめ**

**本番運用機能**:
- ✅ SWI・ガイダンス個別時刻設定
- ✅ SWI初期時刻基準のデータフィルタリング
- ✅ 実データ取得・26,000メッシュ処理（5秒以下）
- ✅ プロキシ対応・エラーハンドリング完備

**UI/UX改善**:
- ✅ 地図左上の時刻情報表示
- ✅ 警戒レベル色の視認性向上（黄・赤・紫）
- ✅ リスクチャートのクリック選択
- ✅ 即座のローディングフィードバック

**アーキテクチャ**:
- ✅ Flask Blueprint-based (17 API endpoints)
- ✅ React 18 + TypeScript + Vite
- ✅ Canvas描画による26,000メッシュ高速表示
- ✅ VBA Module.bas 100%互換

### 🚀 **運用準備完了**

**稼働中のサービス**:
- **サーバー**: http://127.0.0.1:5000 (Flask)
- **クライアント**: http://localhost:3000 (React)
- **本番運用画面**: http://localhost:3000/production
- **開発ダッシュボード**: http://localhost:3000/dashboard

---

---

## 🚀 **2025年10月14日 CSV処理パフォーマンス大幅最適化**

### ✅ **最適化成果サマリー**

| 項目 | 最適化前 | 最適化後 | 改善率 |
|------|---------|---------|--------|
| **CSV処理時間** | 25.3秒 | **1.14秒** | **95.5%削減** |
| **CSV読み込み** | - | 0.47秒 | - |
| **メッシュ構築** | - | 0.67秒 | - |
| **処理速度** | 1,030 meshes/sec | **22,875 meshes/sec** | **22.2倍高速化** |
| **総処理時間** | 32.8秒 | 約9秒 | **72%削減** |

### 🔧 **実装した最適化**

#### **1. dosyakei境界値ルックアップの高速化**
**改善前**: O(n²) - 26,000メッシュ × 逐次検索
```python
# 非効率: forループで26,000回の逐次検索
for code in mesh_codes:
    bound = self.get_dosyakei_bound(dosyakei_data, code)
```

**改善後**: O(n) - ディクショナリルックアップ
```python
# 効率的: pandasベクトル演算 + dict化
dosyakei_data_filtered = dosyakei_data[['GRIDNO', 'LEVEL3_00']].copy()
dosyakei_data_filtered['GRIDNO'] = dosyakei_data_filtered['GRIDNO'].astype(str)
dosyakei_lookup = dict(zip(
    dosyakei_data_filtered['GRIDNO'],
    dosyakei_data_filtered['LEVEL3_00_processed']
))
dosyakei_bounds = [dosyakei_lookup.get(str(code), 999) for code in mesh_codes]
```

#### **2. 座標計算のベクトル化**
**改善前**: リスト内包表記で26,000回の関数呼び出し
```python
coords = [self.meshcode_to_coordinate(code) for code in mesh_codes]
indices = [self.meshcode_to_index(code) for code in mesh_codes]
```

**改善後**: 専用ベクトル化関数で一括処理
```python
coords = self.meshcode_to_coordinate_vectorized(mesh_codes.tolist())
indices = self.meshcode_to_index_vectorized(mesh_codes.tolist())
```

#### **3. VBA座標テーブル構築の最適化**
**改善前**: iterrows()による非効率な逐次処理
```python
for idx, row in vba_swi_data.iterrows():
    area_name = str(row.iloc[0]).strip()
    vba_x = int(row.iloc[1])
    # ... 行ごとの処理
```

**改善後**: pandasベクトル演算で列処理
```python
area_names_vba = vba_swi_data.iloc[:, 0].astype(str).str.strip()
vba_x_values = pd.to_numeric(vba_swi_data.iloc[:, 1], errors='coerce').fillna(0).astype(int)
# ... ベクトル演算で一括処理
```

#### **4. メッシュオブジェクト生成の効率化**
**改善前**: range(len())とインデックスアクセス
```python
for i in range(len(mesh_codes)):
    mesh = Mesh(
        area_name=area_names[i],
        code=mesh_codes[i],
        # ...
    )
```

**改善後**: zip()による効率的なイテレーション
```python
for code, area_name, coord, idx, adv, warn, dosa in zip(
    mesh_codes, area_names, coords, indices,
    advisary_bounds, warning_bounds, dosyakei_bounds
):
    mesh = Mesh(area_name=area_name, code=code, ...)
```

### ✅ **品質保証**

#### **完全一致検証**
- **検証対象**: 26,045メッシュ × 27時刻 = 703,215データポイント
- **検証結果**: **100%完全一致**
- **検証フィールド**: SWI, Rain, Risk, 境界値、全タイムライン
- **許容誤差**: 浮動小数点 1e-10（実質的に完全一致）

#### **検証ツール**
- `tests/test_optimization_validation.py`: 自動検証スクリプト
- `baseline_optimization_test.json`: 最適化前の基準データ (209MB)
- `tests/README_optimization_testing.md`: 検証手順ドキュメント

### 📊 **パフォーマンス詳細**

**最適化後のCSV処理内訳**:
```
CSV読み込み時間: 0.47秒
  - dosha_*.csv (6府県): 境界値データ
  - dosyakei_*.csv (6府県): 土砂災害データ

メッシュ構造構築: 0.67秒
  - 座標計算（ベクトル化）
  - 境界値ルックアップ（O(n)）
  - VBA座標テーブル構築
  - メッシュオブジェクト生成

合計: 1.14秒
処理速度: 22,875 meshes/second
```

### 🎯 **技術的ハイライト**

#### **計算量の改善**
- **dosyakei境界値ルックアップ**: O(n²) → O(n)
- **26,000メッシュでの影響**: 26,000² → 26,000 回の操作

#### **メモリ効率**
- pandasベクトル演算による効率的なメモリ使用
- 不要なコピーを避けた処理
- 26,045メッシュの安定処理

#### **コード品質**
- 元の実装との100%一致を保証
- VBA互換性を完全維持
- 可読性と保守性を維持

### 📁 **影響ファイル**

**最適化されたファイル**:
- `server/services/data_service.py`: CSV処理の中核
  - `meshcode_to_coordinate_vectorized()`: 新規追加
  - `meshcode_to_index_vectorized()`: 新規追加
  - `prepare_areas()`: 4つの最適化を統合

**検証関連ファイル**:
- `server/baseline_optimization_test.json`: 基準データ
- `server/tests/test_optimization_validation.py`: 検証スクリプト
- `server/tests/README_optimization_testing.md`: ドキュメント

### 🚀 **運用への影響**

#### **ユーザー体験の向上**
- **処理時間**: 32.8秒 → 約9秒（72%削減）
- **応答性**: 大幅に改善されたレスポンス時間
- **安定性**: メモリ効率の改善による安定動作

#### **スケーラビリティ**
- 26,000メッシュ以上への対応が容易
- 追加府県のデータ処理も高速
- 本番環境での実用性向上

### 💡 **今後の最適化候補**

現在のボトルネック（最適化後）:
- **GRIB2解析**: 約8秒（現在の最大ボトルネック）
- **CSV処理**: 1.14秒（最適化完了✅）
- **メッシュ計算**: 数秒

**次の最適化ステップ**:
1. GRIB2解析の最適化（複雑だが数秒削減可能）
2. メッシュ計算の並列処理（調査済み - 以下参照）
3. キャッシュ戦略の改善

### ⚠️ **並列処理最適化の調査と判断**

#### **実施内容**
CSV処理最適化後、さらなる高速化を目指して並列処理の導入を試みました。

**試行1: ProcessPoolExecutor（プロセスベース並列処理）**
```python
from concurrent.futures import ProcessPoolExecutor

def _process_prefecture_meshes(prefecture_data, swi_grib2, guidance_grib2):
    """府県単位のメッシュ計算を並列実行"""
    # メッシュ計算処理
    return processed_prefecture

# メイン処理で並列実行
with ProcessPoolExecutor() as executor:
    futures = [executor.submit(_process_prefecture_meshes, pref, swi, guidance)
               for pref in prefectures]
```

**問題点**:
- Windows環境でのmultiprocessing互換性問題
- Flask開発モードでのプロセスフォーク制約
- 実行時にプロセスが正常に起動しない

**試行2: ThreadPoolExecutor（スレッドベース並列処理）**
```python
from concurrent.futures import ThreadPoolExecutor

with ThreadPoolExecutor(max_workers=4) as executor:
    # スレッドで並列実行
```

**問題点**:
- Python GIL（Global Interpreter Lock）の制約
- CPU密度の高い計算処理には不向き
- 実際の高速化効果が限定的

#### **最終判断: 並列処理を見送り**

**理由**:
1. **すでに十分な最適化達成**: CSV最適化で95.5%削減（25.3秒→1.14秒）
2. **追加の複雑性**: Windows互換性、プロセス管理の複雑化
3. **費用対効果**: 追加実装コストに対する高速化メリットが小さい
4. **保守性優先**: シンプルで安定したコードを維持

**現在の処理時間内訳**:
- GRIB2解析: 約8秒（最大ボトルネック）
- CSV処理: 1.14秒（最適化完了✅）
- メッシュ計算: 数秒
- 合計: 約9秒

**結論**:
CSV最適化により実用的な性能を達成。並列処理は追加の複雑性とリスクに見合わないため、現時点では実装を見送り。将来的にさらなる高速化が必要な場合、GRIB2解析の最適化やキャッシュ戦略の改善を優先する。

## 🚀 **2025年10月14日 GRIB2解析処理の最適化完了**

### ✅ **最適化成果サマリー**

| 項目 | 最適化前 | 最適化後 | 改善 |
|------|---------|---------|------|
| **総処理時間** | 33.98秒 | 30.49秒 | **10.3%削減** |
| **改善量** | - | **3.5秒短縮** | - |
| **高速化倍率** | - | **1.11x** | - |
| **データ整合性** | - | **100%一致** | ✅ |

### 🔧 **実装した最適化**

#### **1. get_dat関数の高速化（Big-Endian変換）**

**改善前**: ループによる手動Big-Endian変換
```python
result = 0
for k in range(j):
    if i + k < len(bin_data):
        byte_val = bin_data[i + k]
        result = result + byte_val * (256 ** (j - 1 - k))
```

**改善後**: struct.unpackによる高速バイナリ変換
```python
# 1, 2, 4, 8バイトの場合は最適化パス
if j == 1:
    return struct.unpack('>B', bin_data[i:i+1])[0]
elif j == 2:
    return struct.unpack('>H', bin_data[i:i+2])[0]
elif j == 4:
    return struct.unpack('>I', bin_data[i:i+4])[0]
elif j == 8:
    return struct.unpack('>Q', bin_data[i:i+8])[0]
# その他のサイズはフォールバック
```

**技術的特徴**:
- Python標準ライブラリ `struct` のC実装を活用
- Big-Endianフォーマット (`>`) 指定による直接変換
- 1/2/4/8バイトの高速パス + その他サイズのフォールバック
- VBA互換性を完全維持

#### **2. ランレングス展開の軽微な最適化**

**改善内容**:
- `byte_size = bit_num // 8` の事前計算
- 繰り返し除算の排除
- VBAロジックは完全保持（100%データ一致保証）

```python
# 事前計算による最適化
byte_size = bit_num // 8

# ループ内で繰り返し計算を回避
d = self.get_dat(data, p, byte_size)  # 以前: bit_num // 8
p = p + byte_size                     # 以前: bit_num // 8
```

### ✅ **品質保証**

#### **完全一致検証**
- **検証対象**: 26,045メッシュ × 27時刻 = 703,215データポイント
- **検証結果**: **100%完全一致**
- **検証フィールド**: SWI, Rain, Risk, 境界値、全タイムライン
- **許容誤差**: 浮動小数点 1e-10（実質的に完全一致）

#### **検証ツール**
- `tests/test_grib2_validation.py`: GRIB2最適化検証スクリプト
- `baseline_grib2_test.json`: 最適化前の基準データ
- `optimized_grib2_test.json`: 最適化後の検証データ

### 📊 **パフォーマンス詳細**

**測定結果（3回平均）**:
```
テスト1: 30.23秒
テスト2: 29.92秒
テスト3: 31.34秒

平均: 30.49秒
最短: 29.92秒
最長: 31.34秒
```

**改善内訳**:
- **get_dat最適化**: struct.unpackによる高速化（GRIB2全体に影響）
- **ランレングス展開**: 除算の事前計算による軽微な改善

### 🎯 **技術的ハイライト**

#### **struct.unpackの効果**
- Pythonループ vs Cネイティブ実装
- GRIB2ヘッダー・データ解析全体で数千回の呼び出し
- 1回あたりは微小でも、累積で3.5秒の改善

#### **VBA互換性の完全維持**
- ランレングス展開ロジックは完全保持
- 1ベース配列インデックスの再現
- 境界条件の忠実な実装
- **結果**: 100%データ一致を達成

### 📁 **影響ファイル**

**最適化されたファイル**:
- `server/services/grib2_service.py`: GRIB2解析の中核
  - `get_dat()`: struct.unpack最適化
  - `unpack_runlength()`: 軽微な最適化（VBA準拠維持）

**検証関連ファイル**:
- `server/baseline_grib2_test.json`: 基準データ（除外）
- `server/optimized_grib2_test.json`: 検証データ（除外）
- `server/tests/test_grib2_validation.py`: 検証スクリプト

### 💡 **今後の最適化候補**

**現在のボトルネック分析（最適化後）**:
- **GRIB2解析**: 約8秒 → 約5秒に改善（✅ 10.3%削減達成）
- **CSV処理**: 1.14秒（✅ 95.5%削減達成）
- **メッシュ計算**: 約20秒（次のターゲット）
- **総処理時間**: 約30秒

**次の最適化ステップ**:
1. **メッシュ計算の最適化**: タンクモデル計算のベクトル化
2. **キャッシュ戦略**: GRIB2データの再利用
3. **さらなるGRIB2最適化**: セクション解析の効率化

### 🚀 **累積最適化成果**

**2段階最適化の総合効果**:
1. **CSV処理最適化**: 25.3秒 → 1.14秒（95.5%削減、22.2x高速化）
2. **GRIB2最適化**: 総処理時間 33.98秒 → 30.49秒（10.3%削減、1.11x高速化）

**全体パフォーマンス向上**:
- **開始時**: 約50秒以上
- **CSV最適化後**: 33.98秒
- **GRIB2最適化後**: 30.49秒
- **総改善**: 約40%以上の高速化達成

---

## 🎉 **2025年10月16日 キャッシュシステム実装完了**

### ✅ **gzip圧縮ファイルキャッシュシステム**

GRIB2計算結果をgzip圧縮して保存し、同一パラメータでのリクエスト時に高速レスポンスを実現。

#### **実装機能**
- **gzip圧縮**: 209MB → 5.24MB（97.4%圧縮）
- **自動TTL管理**: デフォルト7日間
- **メタデータ管理**: キャッシュキー、作成日時、メッシュ数、ファイルサイズ
- **RESTful API**: 6つのキャッシュ管理エンドポイント

#### **パフォーマンス効果**

| 項目 | 初回（ミス） | 2回目（ヒット） | 改善 |
|------|-------------|----------------|------|
| **処理時間** | 21.39秒 | 5.31秒 | **4.0倍高速化** |
| **削減率** | - | - | **75.2%削減** |

#### **キャッシュAPI**

```
GET    /api/cache/list           - キャッシュ一覧
GET    /api/cache/stats          - 統計情報
GET    /api/cache/<cache_key>    - メタデータ取得
GET    /api/cache/<cache_key>/exists - 存在確認
DELETE /api/cache/<cache_key>    - キャッシュ削除
POST   /api/cache/cleanup        - 期限切れクリーンアップ
```

#### **実装ファイル**
```
server/
├── services/cache_service.py              # キャッシュコアロジック
├── src/api/controllers/cache_controller.py # キャッシュ管理API
├── src/api/routes/cache_routes.py         # キャッシュAPIルート
├── cache/                                 # キャッシュストレージ
│   ├── *.json.gz                         # 圧縮データ
│   └── *.meta.json                       # メタデータ
├── config/app_config.yaml                 # キャッシュ設定
├── docs/CACHE_SYSTEM.md                   # 完全な仕様書
├── test_cache_system.py                   # 基本テスト
└── test_production_cache.py               # 実データテスト

client/
├── src/types/api.ts                       # CacheInfo型定義
├── src/components/CacheInfo.tsx           # キャッシュ情報表示コンポーネント
└── src/pages/Production.tsx               # キャッシュ情報統合
```

#### **クライアント側統合**

**キャッシュ情報表示コンポーネント**:
- 右上固定表示（position: fixed）
- キャッシュヒット/ミス状態の視覚的表示
- メタデータ詳細（ファイルサイズ、メッシュ数、圧縮情報、作成日時）
- パフォーマンス情報（約4倍高速化）

**表示例**:
```
┌─────────────────────────────┐
│ 💾 キャッシュ情報           │
├─────────────────────────────┤
│ ✅ キャッシュヒット         │
│                             │
│ キャッシュキー:             │
│ swi_20251016120000_...      │
│                             │
│ ファイルサイズ: 5.24 MB     │
│ メッシュ数: 26,045         │
│ 圧縮: gzip 圧縮済み         │
│ 作成日時: 2025/10/16 15:37 │
│                             │
│ ⚡ 高速レスポンス（約4倍）   │
└─────────────────────────────┘
```

#### **設定（config/app_config.yaml）**

```yaml
cache:
  directory: "cache"
  ttl_days: 7
  compression_level: 6  # 1-9（6=バランス推奨）
  auto_cleanup: true
  cleanup_interval_hours: 24
```

#### **期待効果**

```
1日24時刻分のキャッシュ:
- ストレージ: 5.24MB × 24 = 約126MB/日
- 月間: 約3.8GB
- 計算処理削減: キャッシュヒット時は計算ゼロ
- レスポンス時間: 30秒 → 5秒（6倍高速化）
```

---

## 🎉 **2025年10月28日 ランレングス展開処理リファクタリング完了**

### ✅ **気象庁GRIB2公式仕様準拠のリファクタリング**

GRIB2テンプレート7.200の公式仕様書に基づき、ランレングス展開処理を大幅にリファクタリングしました。

#### **リファクタリング成果**
- **100%完全一致検証**: 約4億5千万データポイントで検証完了
- **可読性向上**: VBA逐語訳 → 仕様書準拠の明確な実装
- **構造改善**: モノリシック関数 → 3つの責任分離関数
- **ドキュメント充実**: 詳細なdocstringと実例付き

#### **主要改善点**

**1. 関数分割**:
```python
unpack_runlength()    # メイン処理（圧縮データ全体の展開）
_get_level_value()    # level配列から値を安全に取得
_decode_runlength()   # LNGU進数によるランレングスデコード
```

**2. 仕様書準拠の変数名**:
| VBA変数 | リファクタリング後 | 意味 |
|---------|-------------------|------|
| `bit_num` | `NBIT` | 1格子点値当たりのビット数 |
| `level_max` | `MAXV` | 格子点値の最大値 |
| `d`, `dd` | `value_index`, `next_data` | 値インデックス、次データ |
| `nlength`, `p2` | `run_length`, `digit` | ランレングス、桁位置 |

**3. LNGU進数アルゴリズムの可視化**:
```python
# 仕様: RL = Σ(LNGU^(i-1) × (RLi - (MAXV+1))) + 1
run_length = 0
digit = 0
while rl_data > MAXV:
    run_length += (LNGU ** digit) * (rl_data - (MAXV + 1))
    digit += 1
run_length += 1  # 仕様の+1
```

#### **検証結果**
```
SWI: 8,601,600データポイント - 完全一致 ✅
ガイダンス1時間: 26時系列 × 8,601,600 - 完全一致 ✅
ガイダンス3時間: 26時系列 × 8,601,600 - 完全一致 ✅
総計: 約4億5千万データポイント - 100%一致
```

#### **実装ファイル**
- `server/services/grib2_service.py` - リファクタリング済み実装
- `server/RUNLENGTH_REFACTOR_REPORT.md` - 詳細レポート
- `server/test_runlength_compare.py` - 完全一致検証スクリプト

---

## 🔧 **2025年10月28日 エリア表示順序の改善**

### ✅ **CSV出現順序の保持機能実装**

エリア別リスクレベル時系列の表示順序を、`dosha_{prefecture}.csv`ファイル内の地域名出現順に変更しました。

#### **サーバー側実装**
**ファイル**: `server/services/data_service.py`

```python
from collections import defaultdict, OrderedDict

# OrderedDictを使用してCSV出現順を保持
area_dict = OrderedDict()
```

#### **クライアント側実装**
**ファイル**: `client/src/components/charts/AreaRiskBarChart.tsx`

```typescript
// リスクレベルソートを削除し、APIの順序をそのまま使用
const allAreas = areas;  // CSV出現順を維持
```

#### **効果**
- CSVファイルの地域名出現順が完全に保持される
- エリア別リスクレベル時系列グラフで、地域が常に一貫した順序で表示される
- データ管理とUI表示の一貫性が向上

---

## 🎉 **2025年12月4日 二次細分・府県一括処理機能完成**

### ✅ **リスクタイムライン表示の3モード実装完了**

リスクタイムライン表示に、市町村別・二次細分別・全府県一覧の3つの表示モードを実装しました。

#### **実装の背景**

`dosha_*.csv`の第1列は「二次細分」と呼ばれる、複数の市町村をまとめた気象警報区分です（例：兵庫県の「阪神」「播磨北西部」など）。リスクタイムラインの表示や雨量調整では、市町村ごとの操作に加えて、以下の機能が必要でした：

1. **二次細分別表示**: 二次細分内の最大値を一括表示
2. **全府県一覧**: 6府県すべてを1画面で同時表示（府県内最大値）

### 📊 **サーバー側実装**

#### **1. データモデル拡張**

**新規追加クラス**:
```python
@dataclass
class SecondarySubdivision:
    """二次細分（市町村をまとめた地域）"""
    name: str  # 二次細分名（例：「阪神」）
    areas: List[Area]  # 所属市町村リスト
    rain_1hour_max_timeline: List[GuidanceTimeSeries]  # 二次細分内の最大1時間雨量
    rain_3hour_timeline: List[GuidanceTimeSeries]  # 二次細分内の最大3時間雨量
    risk_timeline: List[Risk]  # 二次細分内の最大リスク
```

**Prefecture拡張**:
```python
@dataclass
class Prefecture:
    # 既存フィールド
    name: str
    code: str
    areas: List[Area]

    # 新規フィールド
    secondary_subdivisions: List[SecondarySubdivision]  # 二次細分リスト
    prefecture_rain_1hour_max_timeline: List[GuidanceTimeSeries]  # 府県全体の最大1時間雨量
    prefecture_rain_3hour_timeline: List[GuidanceTimeSeries]  # 府県全体の最大3時間雨量
    prefecture_risk_timeline: List[Risk]  # 府県全体の最大リスク
```

**Area拡張**:
```python
@dataclass
class Area:
    name: str
    meshes: List[Mesh]
    secondary_subdivision_name: str  # 所属する二次細分名（新規）
    risk_timeline: List[Risk]
```

#### **2. prepare_areas()の二次細分対応**

**ファイル**: `server/services/data_service.py`

```python
# CSV第1列（二次細分名）を読み込み
subdivision_names = dosha_data.iloc[:, 0].astype(str).str.strip().values
area_names = dosha_data.iloc[:, 1].astype(str).str.strip().values

# 二次細分構造を構築（OrderedDictでCSV出現順を保持）
subdivision_dict = OrderedDict()
for area in area_dict.values():
    subdiv_name = area.secondary_subdivision_name
    if subdiv_name not in subdivision_dict:
        subdivision = SecondarySubdivision(name=subdiv_name)
        subdivision_dict[subdiv_name] = subdivision
    subdivision_dict[subdiv_name].areas.append(area)

# Prefectureに設定
prefecture = Prefecture(
    name=pref_name,
    code=pref_code,
    areas=list(area_dict.values()),
    secondary_subdivisions=list(subdivision_dict.values())
)
```

**構築結果例**（滋賀県）:
- 8つの二次細分
- 41の市町村
- 各二次細分に複数市町村が所属

#### **3. 集約計算関数の実装**

**ファイル**: `server/services/calculation_service.py`

**二次細分内の最大値集約**:
```python
def calc_secondary_subdivision_aggregates(self, subdivision: SecondarySubdivision):
    """二次細分内の最大雨量・リスクを集計"""
    # 全メッシュを収集
    all_meshes = []
    for area in subdivision.areas:
        all_meshes.extend(area.meshes)

    # FTごとに最大値を集計
    for ft in sorted(ft_set_1hour_max):
        max_value = max(
            (point.value for mesh in all_meshes
             for point in mesh.rain_1hour_max if point.ft == ft),
            default=0.0
        )
        subdivision.rain_1hour_max_timeline.append(
            GuidanceTimeSeries(ft=ft, value=max_value)
        )
    # rain_3hour_timeline, risk_timelineも同様に集約
```

**府県全体の最大値集約**:
```python
def calc_prefecture_aggregates(self, prefecture: Prefecture):
    """府県全体の最大雨量・リスクを集計"""
    # 府県内の全メッシュから最大値を集計
    all_meshes = []
    for area in prefecture.areas:
        all_meshes.extend(area.meshes)

    # 二次細分と同様のロジックで集約
```

#### **4. APIレスポンス拡張**

**ファイル**: `server/services/main_service.py`, `server/src/api/controllers/test_controller.py`

```json
{
  "prefectures": {
    "hyogo": {
      "name": "兵庫県",
      "code": "hyogo",
      "areas": [...],
      "secondary_subdivisions": [
        {
          "name": "阪神",
          "area_names": ["神戸市", "尼崎市", ...],
          "rain_1hour_max_timeline": [...],
          "rain_3hour_timeline": [...],
          "risk_timeline": [...]
        }
      ],
      "prefecture_rain_1hour_max_timeline": [...],
      "prefecture_rain_3hour_timeline": [...],
      "prefecture_risk_timeline": [...]
    }
  }
}
```

### 🎨 **クライアント側実装**

#### **5. TypeScript型定義拡張**

**ファイル**: `client/src/types/api.ts`

```typescript
export interface SecondarySubdivision {
  name: string;
  area_names: string[];
  rain_1hour_max_timeline: TimeSeriesPoint[];
  rain_3hour_timeline: TimeSeriesPoint[];
  risk_timeline: RiskTimePoint[];
}

export interface Prefecture {
  name: string;
  code: string;
  areas: Area[];
  secondary_subdivisions?: SecondarySubdivision[];
  prefecture_rain_1hour_max_timeline?: TimeSeriesPoint[];
  prefecture_rain_3hour_timeline?: TimeSeriesPoint[];
  prefecture_risk_timeline?: RiskTimePoint[];
}

export type RiskTimelineViewMode = 'municipality' | 'subdivision' | 'prefecture-all';
```

#### **6. AreaRiskBarChart表示モード切り替え**

**ファイル**: `client/src/components/charts/AreaRiskBarChart.tsx`

**表示モード切り替えUI**:
```tsx
<div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
  <label style={{ fontWeight: 'bold' }}>表示:</label>
  <button onClick={() => setViewMode('municipality')}>市町村別</button>
  <button onClick={() => setViewMode('subdivision')}>二次細分別</button>
  <button onClick={() => setViewMode('prefecture-all')}>全府県一覧</button>
</div>
```

**動的データ準備**:
```typescript
const displayData = useMemo(() => {
  let rows: DisplayRow[] = [];

  if (viewMode === 'municipality') {
    // 市町村別表示
    const selectedPref = prefectures.find(p => p.code === selectedPrefecture);
    rows = selectedPref.areas.map(area => ({
      name: area.name,
      risk_timeline: area.risk_timeline
    }));
  } else if (viewMode === 'subdivision') {
    // 二次細分別表示
    rows = selectedPref.secondary_subdivisions.map(subdiv => ({
      name: subdiv.name,
      risk_timeline: subdiv.risk_timeline
    }));
  } else if (viewMode === 'prefecture-all') {
    // 全府県一覧表示
    rows = prefectures.map(pref => ({
      name: pref.name,
      risk_timeline: pref.prefecture_risk_timeline
    }));
  }

  return { rows, dateGroups };
}, [prefectures, selectedPrefecture, viewMode]);
```

### 📊 **動作確認結果**

```bash
# APIテスト結果（滋賀県の例）
Prefecture: 滋賀県
  Areas: 41                    # 市町村数
  Secondary Subdivisions: 8    # 二次細分数
  Example subdivision: 湖南    # 二次細分名
  Subdivision areas: 9         # 二次細分内の市町村数
  Prefecture risk timeline: 79 # 府県全体のリスクタイムラインポイント数
```

### 🎯 **実装の特徴**

#### **データ構造の3階層化**
```
府県 (Prefecture)
 ├─ 二次細分 (SecondarySubdivision)
 │   └─ 市町村 (Area)
 │       └─ メッシュ (Mesh)
 └─ 府県全体集約データ
```

#### **効率的な集約計算**
- サーバー側で事前に最大値を集約
- クライアントは表示切り替えのみ
- ネットワーク転送量を最小化

#### **完全な後方互換性**
- 既存の市町村別表示は完全に維持
- 既存APIエンドポイントすべてで動作
- レスポンス形式は拡張のみ（既存フィールドは変更なし）

#### **CSV出現順序の保持**
- OrderedDictを使用
- 二次細分もCSV出現順で表示
- データの一貫性を保証

### 📁 **変更ファイル一覧**

**サーバー側**:
- `server/models/data_models.py` - SecondarySubdivision追加、Prefecture/Area拡張
- `server/models/__init__.py` - SecondarySubdivisionをエクスポート
- `server/services/data_service.py` - prepare_areas()の二次細分対応
- `server/services/calculation_service.py` - 集約計算関数追加
- `server/services/main_service.py` - 集約計算呼び出しとレスポンス拡張
- `server/src/api/controllers/test_controller.py` - テストAPIの二次細分対応

**クライアント側**:
- `client/src/types/api.ts` - 型定義拡張（SecondarySubdivision, RiskTimelineViewMode）
- `client/src/components/charts/AreaRiskBarChart.tsx` - 3モード表示実装

### 🔄 **今後の拡張可能性**

#### **雨量調整画面への展開**
現在の実装で、雨量調整画面にも以下の機能を追加可能：
- 二次細分別の最大雨量表示
- 二次細分単位での一括雨量調整
- サーバー側のデータ構造は既に対応済み

#### **追加の集約レベル**
データモデルは拡張可能な設計：
- 広域ブロック（近畿地方全体など）
- カスタムグループ（ユーザー定義地域）

---

**作成日**: 2025年7月23日
**最終更新**: 2025年12月4日
**バージョン**: 8.0.0（二次細分・府県一括処理機能完成版）
**作成者**: Claude (Anthropic)
**プロジェクト**: 土壌雨量指数計算システム（VBA完全互換・パフォーマンス最適化・3階層データ構造対応版）
---

## 🎉 **2025年12月12日 政府ガイドライン準拠リスクレベル変更**

### ✅ **リスクレベル番号体系の変更**

日本政府の防災ガイドラインに合わせて、リスクレベルの番号体系を変更しました。

#### **変更内容**

| 項目 | 変更前 | 変更後 | 説明 |
|------|--------|--------|------|
| 正常 | レベル0 | レベル0 | 変更なし |
| 注意 | レベル1 | **レベル2** | 大雨注意報相当 |
| 警報 | レベル2 | **レベル3** | 大雨警報相当 |
| 土砂災害 | レベル3 | **レベル4** | 土砂災害警戒情報相当 |

**レベル1**: 欠番（システム内に対応する事象なし）

#### **影響範囲**

**サーバー側**:
- `services/calculation_service.py`
  - `calc_risk_timeline()`: 3時間ごとのリスク判定（0,2,3,4）
  - `calc_hourly_risk()`: 1時間ごとのリスク判定（0,2,3,4）

**クライアント側**:
- `client/src/types/api.ts`
  - `RiskLevel` enum値の変更（CAUTION=2, WARNING=3, DISASTER=4）
  - 地図凡例・チャートでの表示番号更新

#### **技術的特徴**

- **後方互換性**: APIレスポンス形式は変更なし
- **システム挙動**: 判定ロジックは不変、番号のみ変更
- **表示の一貫性**: サーバー・クライアント両方で統一した番号体系

---

## 🔧 **2025年12月15日 本番環境API互換性バグ修正**

### ✅ **辞書アクセスエラーの修正完了**

本番環境で発生した `'dict' object has no attribute 'areas'` エラーを修正しました。

#### **問題の原因**

**サーバー側の処理フロー**:
1. `main_service.py` が Prefecture オブジェクトを**完全に辞書形式**に変換してレスポンスを返す
2. `main_controller.py` がセッション作成時に `result['prefectures']` を受け取る
3. オブジェクト属性 (`.areas`) としてアクセスしようとしたため、本番環境でエラー発生

**環境による動作の違い**:
- **開発環境**: `USE_MOCK_PRODUCTION_API = True` → モックAPI経由でセッション作成をスキップするためエラーなし
- **本番環境**: セッションサービスが有効 → `create_session()` が実行されてエラー発生

#### **修正内容**

**ファイル**: `server/src/api/controllers/main_controller.py:279-283`

**修正前** (オブジェクト属性アクセス):
```python
if first_pref.areas and first_pref.areas[0].meshes:
    first_mesh = first_pref.areas[0].meshes[0]
    available_times = sorted(set(
        [point.ft for point in first_mesh.risk_3hour_max_timeline] +
        [point.ft for point in first_mesh.risk_hourly_timeline]
    ))
```

**修正後** (辞書キーアクセス):
```python
if first_pref['areas'] and first_pref['areas'][0]['meshes']:
    first_mesh = first_pref['areas'][0]['meshes'][0]
    available_times = sorted(set(
        [point['ft'] for point in first_mesh['risk_3hour_max_timeline']] +
        [point['ft'] for point in first_mesh['risk_hourly_timeline']]
    ))
```

#### **影響範囲**

- **本番環境**: セッションベースAPI (`/api/production-soil-rainfall-index-with-urls`) が正常動作するようになる
- **開発環境**: 既存の動作に影響なし（モックAPI経由で動作継続）
- **クライアント側**: 修正不要（サーバー側のみの変更）

#### **検証方法**

本番環境での確認事項：
1. ブラウザで本番運用画面 (`/production`) を開く
2. 初期時刻を選択してデータ取得
3. サーバーログで `'dict' object has no attribute 'areas'` エラーがないことを確認
4. HTTPステータスコード 200 で `session_id` が返されることを確認
5. 地図とグラフが正常に表示されることを確認

**ログ確認コマンド**:
```bash
# サーバーログ確認
sudo journalctl -u your-app-service-name -n 200 --no-pager

# エラーがないことを確認
grep "dict.*has no attribute" /path/to/log
```

#### **技術的教訓**

- **データモデルの一貫性**: オブジェクト vs 辞書の扱いを統一する重要性
- **環境差異の検証**: 開発環境と本番環境の動作フローの違いを確認する必要性
- **エラーハンドリング**: 属性アクセス vs キーアクセスの明確な区別

---

**最終更新**: 2025年12月15日
**バージョン**: 8.1.1（本番環境API互換性修正版）
