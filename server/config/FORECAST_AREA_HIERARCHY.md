# 一次細分区域の対応設定

`forecast_area_hierarchy.json` は「府県予報区 → 一次細分区域 → 市町村等をまとめた地域」
の対応表です。雨量調整の「一次細分ごと」で代表雨量を集計し、入力値を配下メッシュへ
適用するため、`server/src/services/rainfall_scope_service.py` が読み込みます。

## 出典と範囲

- [気象庁「細分区域等一覧表」](https://www.jma.go.jp/jma/kishou/know/yougo_hp/shichoson_ichiran.html)
- 原表基準日: 2026年5月29日、取得日: 2026年10月16日
- 全国56府県予報区、142一次細分区域、375の市町村等をまとめた地域を収録
- 個々の市町村・二次細分区域や別表の境界定義は収録しない

北海道・沖縄県などは府県予報区が複数に分かれるため、47都道府県の一覧とは異なります。
配列は原表の順序を保持します。

## 形式

| フィールド | 内容 |
| --- | --- |
| `schema_version` | JSON形式のバージョン（1） |
| `source` | 出典URL、原表基準日 `effective_date`、取得HTMLの `html_sha256` |
| `forecast_districts` | 府県予報区キーを持つ辞書 |
| `forecast_districts[key].name` | 府県予報区名 |
| `primary_subdivisions` | 一次細分区域の配列。各要素の `name` が区域名 |
| `municipality_groups` | 一次細分区域配下の市町村等をまとめた地域の配列 |
| 地域の `name` | 照合用名称（名称全体を囲む全角括弧のみ除去） |
| 地域の `source_name` | 原表表記（全角括弧を保持、HTML整形の空白は除去） |

府県予報区キーは出典ページのアンカー（`shiga` など）で、気象庁の数値区域コードでは
ありません。現在の `server/data/prefectures.csv` の14府県では `prefecture_code` と
一致します。他地域を追加する場合はキーの対応を確認してください。

「北部」などは府県間で重複するため、一次細分区域の識別には府県予報区キーと名称の組を
使います。大阪府の一次細分区域は「大阪府」、香川県は「香川県」です。
島根県の「（隠岐）」と愛媛県の「（中予）」などは `name` では括弧を除去し、
`source_name` に原表の括弧付き名称を保持します。

## Pythonでの利用例

リポジトリルートから実行する例です。アプリケーションへの組み込み時は設定ディレクトリを
基準にパスを解決してください。

```python
import json
from pathlib import Path

config = json.loads(
    Path("server/config/forecast_area_hierarchy.json").read_text(encoding="utf-8")
)
district = config["forecast_districts"]["shiga"]
group_to_primary = {
    group["name"]: primary["name"]
    for primary in district["primary_subdivisions"]
    for group in primary["municipality_groups"]
}
assert group_to_primary["湖北"] == "北部"
```

既存モデルの `secondary_subdivisions` / `SecondarySubdivision` は市町村等をまとめた地域を
表すため、その `name` を照合します。未知の地域名は未設定として検出し、任意の区域へ
振り分けないでください。

## 再生成・更新

リポジトリルートで実行します。生成スクリプトはPython標準ライブラリのみを使用します。

```bash
curl -fsSL https://www.jma.go.jp/jma/kishou/know/yougo_hp/shichoson_ichiran.html \
  -o /tmp/jma-subdivisions.html
python -B scripts/build_forecast_area_config.py /tmp/jma-subdivisions.html \
  server/config/forecast_area_hierarchy.json
git diff -- server/config/forecast_area_hierarchy.json
```

原表の結合セル（rowspan）を展開して上位区域を引き継ぎます。見出し・列構造・重複を
検査し、想定外の構造では停止します。更新時は基準日・区域数・所属変更・既存CSVとの
名称対応を確認し、この説明書の取得日と件数も更新してください。
設定変更だけでは既存キャッシュの再集約は行いません。

## 作成時の確認

- JSON読み込み、再生成結果の一致、府県予報区内の地域名の一意性を確認
- `prefectures.csv` の全14府県のキーと名称が一致
- 手元の近畿6府県の `dosha_*.csv` と全35地域が過不足なく一致
- 中国・四国8県は収録済み。ただし当ブランチの手元に対象CSVがないためCSV照合は未実施
