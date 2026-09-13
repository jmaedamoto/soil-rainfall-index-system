# 解析雨量GRIB2デコーダー（Python組み込み・CSV変換）

気象庁「配信資料に関する仕様 No.11601」の解析雨量および速報版解析雨量を
CSVへ変換する、単独配布用ツールです。

## 移行先のCodex・開発者向け引き継ぎ

このREADMEと同梱ファイルだけで別プロジェクトへ組み込めます。元リポジトリの
コード・設定・会話履歴は必要ありません。ライブラリとして直接importでき、
CSVを経由せずに雨量と座標を取得できます。

1. 移行先のディレクトリ構成と利用箇所を確認し、`analyzed_rainfall_decoder.py` を
   利用側モジュールからimportできる場所へコピーする。
2. 利用側で入力GRIB2のファイルパスまたはバイト列を用意する。
   データ取得・ダウンロード機能と実データは本配布物に含まない。
3. 下記「組み込みAPI」を使って雨量を読み取り、移行先の処理へ渡す。
   必要な機能は本体に実装済みなので、まず既存APIを利用する。
4. 下記「移行後の確認」を実行し、利用側の処理まで確認する。

入力は解析雨量・速報版解析雨量のGRIB2です。汎用GRIB2デコーダーではなく、
土壌雨量指数や予報ガイダンスのデコード・土壌雨量指数計算は対象外です。
出力雨量は対象終了時刻までの1時間積算値（mm）で、欠測と0 mmを区別します。
速報版も10分間雨量ではありません。

Codexへの依頼例（入力パスと用途を具体化して渡してください）:

```text
同梱README.mdを読み、analyzed_rainfall_decoder.pyをこのプロジェクトへ組み込んでください。
入力GRIB2: <ファイルパス、または既存の取得処理>
利用目的: <雨量・座標を渡す処理、保存先など>
既存のパッケージ構成に合わせて配置とimportを調整し、欠測値は0へ置き換えず扱ってください。
読み込みから全格子の反復までを例外処理に含め、移行後の確認結果を報告してください。
```

## 動作環境

- Python 3.9以上
- 外部パッケージ不要（Python標準ライブラリのみ）
- Windows、macOS、Linux

## 対応形式

- プロダクト定義テンプレート: 4.50008
- 資料表現テンプレート: 5.200
- ランレングス圧縮: 7.200（8 bit）
- ビットマップなし
- 走査モード: `0x00`
- 解析雨量: `..._Prr60lv_ANAL_grib2.bin`
- 速報版解析雨量: `..._Prr60lv_Aper10min_ANAL_grib2.bin`

## 実行方法

ZIPを展開し、次のように実行します。

```bash
python analyzed_rainfall_decoder.py target_grib2_file.bin
```

入力ファイルと同じ場所に、拡張子を `.csv` に置き換えたファイルを作成します。

出力先を指定する場合:

```bash
python analyzed_rainfall_decoder.py target.bin -o rainfall.csv
```

既存CSVを上書きする場合:

```bash
python analyzed_rainfall_decoder.py target.bin --force
```

欠測格子をCSVから除外して容量を抑える場合:

```bash
python analyzed_rainfall_decoder.py target.bin --omit-missing
```

## CSV形式

```text
grid_index,x,y,latitude,longitude,rainfall_mm
0,1,1,47.995833,118.006250,
1,2,1,47.995833,118.018750,0.5
```

- `grid_index`: GRIB2の走査順による0始まりの格子番号
- `x`, `y`: 1始まりの格子位置
- `latitude`, `longitude`: 格子点中心の緯度・経度
- `rainfall_mm`: 終了時刻までの1時間積算雨量。欠測は空欄

標準の全国格子は8,601,600点あるため、CSVは大きくなります。欠測格子が不要な
場合は `--omit-missing` を指定してください。CSVは一時ファイルへ逐次出力した後で
完成ファイルへ置き換えるため、変換中に全格子をメモリへ保持しません。

## Pythonコードからの利用

### 別リポジトリへのコピー

配布一式は次の3ファイルです。

- `analyzed_rainfall_decoder.py`: デコーダー本体とCSV変換CLI（実行に必要な唯一のファイル）
- `example_usage.py`: Pythonからの読み込み・座標取得・欠測除外・最大雨量集計の実行例
- `README.md`: この説明書

別プロジェクトのPythonプログラムと同じディレクトリに本体をコピーしてください。
このシステムの `server/`、設定ファイル、Flask、NumPyは不要です。
`pip install` も不要です。

```text
other-project/
  main.py
  analyzed_rainfall_decoder.py
  example_usage.py
```

まず実データを指定してサンプルを実行できます。

```bash
python example_usage.py /path/to/rainfall.bin
```

`src/` 配下のパッケージへ配置する場合は、そのパッケージ内から
`from .analyzed_rainfall_decoder import decode_file` のように相対importします。

### 組み込みAPI

```python
from analyzed_rainfall_decoder import decode_file

analyzed = decode_file("target.bin")
print(analyzed.valid_time)

for rainfall_mm in analyzed.iter_values():
    print(rainfall_mm)
```

欠測値は `float("nan")` です。全値をリストにする場合は `analyzed.values()` を
使用できますが、全国格子では大きなメモリを使用します。

| API | 用途 |
| --- | --- |
| `decode_file(path)` | ファイルから読み込み（文字列・`Path`対応） |
| `decode(data)` | 取得済みのGRIB2バイト列から読み込み |
| `analyzed.iter_values()` | 走査順に雨量を逐次展開。最後まで反復すると格子数の整合性も検証 |
| `analyzed.grid.coordinates(index)` | 0始まり格子番号から `(緯度, 経度)` を取得 |
| `analyzed.valid_time` | 積算終了時刻（UTC、タイムゾーン情報なしの `datetime`） |
| `analyzed.accumulation_minutes` | 積算時間（分） |
| `export_csv(analyzed, path, force=False, omit_missing=False)` | CSV保存、出力行数を返す |

入力バイト列はメモリに読み込みますが、`iter_values()` は全格子分のリストを
作りません。欠測判定には `math.isnan(value)` を使用してください。
未対応形式や不正データは `ValueError`、ファイル読み書きの失敗は `OSError` 系の
例外として呼び出し側で扱えます。実際の雨量展開は反復時に行うため、例外処理は
`decode_file()` だけでなく反復処理も含めてください。

座標と雨量を利用側へ渡す例:

```python
import math
from analyzed_rainfall_decoder import decode_file

def iter_valid_points(path):
    analyzed = decode_file(path)
    for index, rainfall_mm in enumerate(analyzed.iter_values()):
        if math.isnan(rainfall_mm):
            continue
        latitude, longitude = analyzed.grid.coordinates(index)
        yield latitude, longitude, rainfall_mm

try:
    for latitude, longitude, rainfall_mm in iter_valid_points("target.bin"):
        # ここで利用側の集計・保存処理へ渡す
        pass
except (OSError, ValueError) as error:
    raise RuntimeError(f"解析雨量の読み込みに失敗しました: {error}") from error
```

格子は北西から東向きに並び、行が進むと南へ移動します。`enumerate()` の番号は
元の格子番号です。欠測除外後に番号を振り直して座標を計算しないでください。
反復の途中で不正データが見つかる可能性があるため、DB等への逐次保存で
一括成功が必要な場合は、利用側でトランザクションや一時出力を用意してください。

## 移行後の確認

本体とサンプルを配置したディレクトリで実行します。

```bash
python -c "from analyzed_rainfall_decoder import decode_file; print('import OK')"
python example_usage.py /path/to/rainfall.bin
python analyzed_rainfall_decoder.py /path/to/rainfall.bin -o check.csv
```

サンプルは全格子を反復し、有効格子数・最大雨量・最初の有効5点の座標と雨量を
表示します。CSVの列は上記「CSV形式」のとおりで、欠測は空欄です。
既存の `check.csv` がある場合は別名にするか、上書きする意図があれば `--force` を
指定してください。パッケージ内へ配置した場合はimportとサンプルの起動方法を
そのプロジェクトの構成に合わせます。

配布時にはZIPを元リポジトリ外へ展開し、外部パッケージを読み込まない環境で、
合成GRIB2（2×2格子）によるimport・ランレングス展開・欠測処理・座標・CSV出力・
上書き防止を確認済みです。移行先で使う実データの検証は、上記コマンドと
利用側の処理で実施してください。

## 出典仕様

- 気象庁「配信資料に関する仕様 No.11601 ～解析雨量・速報版解析雨量～」
