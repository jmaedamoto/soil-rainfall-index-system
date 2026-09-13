# 解析雨量GRIB2対応

気象庁「配信資料に関する仕様 No.11601」に基づき、解析雨量と速報版解析雨量の
GRIB2を読み取ります。仕様資料はリポジトリ直下の `no11601.pdf` です。

## 対応データ

| 項目 | 対応内容 |
| --- | --- |
| 解析雨量 | `..._Prr60lv_ANAL_grib2.bin` |
| 速報版解析雨量 | `..._Prr60lv_Aper10min_ANAL_grib2.bin` |
| プロダクト定義 | テンプレート4.50008 |
| 資料表現 | テンプレート5.200 |
| 圧縮 | テンプレート7.200、8-bitランレングス |
| 格子 | 等緯度経度、走査モード`0x00` |
| 雨量 | 終了時刻までの1時間積算雨量、mm単位 |
| 欠測 | レベル0を`NaN`として扱う |

解析雨量と速報版解析雨量は対象テンプレートとデータ表現が共通であるため、同じ
デコーダーで処理します。ファイル名による種別の分離は行いません。

## システム内での利用

実装は `server/src/services/grib2_service.py` の `Grib2Service` にあります。

```python
service = Grib2Service()

# バイト列から読み取る
base_info, result = service.unpack_analyzed_rainfall_grib2(grib2_bytes)

# ファイルから読み取る
base_info, result = service.unpack_analyzed_rainfall_grib2_from_file("rainfall.bin")

rainfall = result["rainfall"]
valid_time = result["valid_time"]
accumulation_minutes = result["accumulation_minutes"]
```

`result["data"]` は `result["rainfall"]` と同じ配列です。既存の土壌雨量指数・
雨量ガイダンスと同様に、格子情報は `base_info` および `result["base_info"]` から
取得できます。

## サーバー環境でのCSV変換

```bash
python server/decode_analyzed_rainfall.py target_grib2_file.bin
```

入力と同じ場所へ、拡張子を `.csv` に置き換えたファイルを出力します。

```bash
python server/decode_analyzed_rainfall.py target.bin -o output.csv
python server/decode_analyzed_rainfall.py target.bin --force
```

このCLIはサーバー側の `Grib2Service` を利用するため、`server/requirements.txt` の
依存パッケージが必要です。

## 単独配布版

`standalone/analyzed-rainfall-decoder/` はシステムから独立した実装です。Python 3.9
以上と標準ライブラリだけで動作します。

```bash
python analyzed_rainfall_decoder.py target_grib2_file.bin
```

全格子をメモリへ展開せず、デコードしながらCSVへ逐次出力します。全国格子は
8,601,600点あるため、欠測格子が不要な場合は `--omit-missing` を指定できます。

配布用ZIPの生成方法:

```bash
mkdir -p dist
cd standalone/analyzed-rainfall-decoder
python -m zipfile -c ../../dist/analyzed-rainfall-decoder-1.0.0.zip \
  analyzed_rainfall_decoder.py example_usage.py README.md
```

`dist/` は生成物としてGit管理対象外です。配布ZIPは必要な環境で上記コマンドにより
再生成します。

別リポジトリへの移植にはZIP内の `analyzed_rainfall_decoder.py` を利用側の
Pythonファイルと同じディレクトリへコピーします。サーバーの依存パッケージや設定は
不要です。`example_usage.py` は座標取得・欠測除外・最大雨量集計の実行例です。
詳しい配置方法と組み込みAPIは同梱の `README.md` を参照してください。
READMEには移行先のCodex向け依頼文、入力データの準備、欠測・時刻・例外処理の
注意点、実データによる移行後の確認手順も記載しています。

配布物はリポジトリ外の一時ディレクトリへ展開し、Pythonの外部パッケージを
読み込まない環境（`-S`）で、合成2×2格子のランレングス展開、欠測、座標、CSV変換、
上書き防止、組み込みサンプルの動作を確認済みです。移行先の実データによる確認は
別途実施します。

## CSV形式

```text
grid_index,x,y,latitude,longitude,rainfall_mm
0,1,1,47.995833,118.006250,
1,2,1,47.995833,118.018750,0.5
```

- `grid_index`: GRIB2走査順の0始まり格子番号
- `x`, `y`: 1始まりの格子位置
- `latitude`, `longitude`: 格子点中心の緯度・経度
- `rainfall_mm`: 1時間積算雨量。欠測値は空欄

CSVは一時ファイルへ出力してから完成ファイルへ置き換えます。既存ファイルは既定で
上書きせず、`--force` 指定時だけ置き換えます。
