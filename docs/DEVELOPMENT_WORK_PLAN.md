# 開発作業計画

**作成日**: 2026年4月25日
**対象ブランチ**: `develop`
**ステータス**: 作業整理中

---

## 1. 目的

`develop` ブランチで今後追加する機能・改修内容を、実装前に整理する。

このドキュメントでは以下を明確にする:

1. 何を実現したいか
2. どのファイルや機能に影響が出るか
3. 実装前に決めるべき点は何か
4. 作業をどの順序で進めるか
5. 完了条件をどう定義するか

現時点の最優先事項:

1. 雨量調整機能を意図した比率補正型へ修正する
2. 雨量調整に「領域内全格子を入力値で塗りつぶす」モードを追加する
3. 雨量調整に24時間雨量合計入力を追加する
4. その後に GSM 対応を進める

---

## 2. 背景

- 現在の本番系計算では、降水量ガイダンスとして MSM データのみを使用している
- 現在使用しているファイル形式は `guid_msm_grib2_YYYYMMDDHHMMSS_rmax00.bin` または `guid_msm_grib2_YYYYMMDDHHMMSS_rmax03.bin`
- 同じ `gdc` ディレクトリ配下に GSM データ `guid_gsm_grib2_YYYYMMDDHHMMSS_rmax.bin` が存在する
- GSM は MSM と比較して以下が異なる
  - 初期時刻が 6 時間ごと（00, 06, 12, 18）
  - 格子数・領域が異なる
  - FT の最大値が異なる
  - ファイル名規則が異なる
- まずサーバーに GSM を用いた計算エンドポイントを追加し、その後クライアントで MSM / GSM の切り替え機能を追加する

---

## 3. 今回の作業対象

### 3.1 追加・変更したい内容

- 雨量調整機能を「市町村入力値を全格子へ一律適用」ではなく「市町村最大値基準の比率補正型」に修正する
- 雨量調整機能に、ユーザー入力値で領域内全格子を塗りつぶすモードを追加する
- 雨量調整機能に、3時間ごとの入力に加えて24時間雨量合計入力を追加する
- サーバーで GSM ガイダンスを用いた計算を実行できるようにする
- API リクエストでガイダンス種別を指定できるようにする
- クライアントで MSM / GSM を選択できるようにする
- 選択したガイダンス種別に応じて時刻候補や取得処理を切り替える
- 既存の MSM 機能を壊さずに後方互換性を維持する
- 雨量調整機能でも、初回計算に使用したガイダンス種別（MSM/GSM）を引き継げるようにする

### 3.2 対象外とする内容

- SWI データ形式自体の変更
- 既存の土壌雨量指数計算ロジックの大幅な置き換え
- Apache / deploy 構成の追加変更
- 雨量調整 UI の全面改修

---

## 4. 現状整理

### 4.1 関連機能

- `production-soil-rainfall-index-with-urls` が本番系セッション計算の入口
- `MainService.main_process_from_separate_urls()` が SWI / ガイダンス取得と計算実行の中心
- `ConfigService.build_guidance_url()` が現在 MSM 専用 URL を生成している
- `Grib2Service.unpack_guidance_grib2()` が現在のガイダンス GRIB2 解析処理
- `ProductionSession` 画面が SWI / ガイダンス初期時刻入力と取得実行を担当

### 4.2 関連ファイル

- `server/src/config/config_service.py`
- `server/src/services/main_service.py`
- `server/src/services/grib2_service.py`
- `server/src/api/controllers/main_controller.py`
- `server/src/api/routes/main_routes.py`
- `client/src/services/api.ts`
- `client/src/features/production-session/hooks/useProductionSession.ts`
- `client/src/pages/ProductionSession.tsx`
- `client/src/features/production-session/utils/dateTime.ts`
- `client/src/types/api.ts`
- `client/src/types/session.ts`

### 4.3 現状の問題点

- 現在の本番雨量調整再計算は、市町村入力値を対象市町村内の全メッシュへ一律適用している
- そのため、元の格子ごとの降雨分布が失われている
- 意図している「市町村最大値基準の比率補正型」と実装が一致していない
- 雨量調整の方式をユーザーが選択できず、「比率補正」と「塗りつぶし」を使い分けられない
- 雨量調整は3時間ごとの入力前提で、24時間雨量合計を直接入力できない
- 24時間入力時に、3時間系列へどう按分するかの仕様が存在しない
- ガイダンス URL 生成が `guid_msm_*` 固定
- `build_guidance_url()` が MSM の時刻規則（`rmax00` / `rmax03`）に依存している
- API payload にガイダンス種別が存在しない
- キャッシュキーが SWI 初期時刻とガイダンス初期時刻のみで、データ種別を区別していない
- クライアントの時刻候補が 3 時間刻み固定
- クライアントの時刻送り UI が `±3時間` 前提
- `guidance_initial_time` は扱っているが、どのガイダンス種別で計算したかをレスポンスが持っていない
- GSM は MSM / SWI より格子が粗く、1つの GSM 格子に複数の SWI メッシュが対応する
- セッションに `guidance_type` が保存されていない
- フォークセッションにも `guidance_type` が引き継がれない
- 雨量調整 API の `guidance_initial` / `data_source` は未使用で、ガイダンス種別の再現に使えない
- クライアントの雨量調整モーダルは `dataSource="test"` 固定で、初回計算条件を保持していない

---

## 5. 実装前に決めること

- GSM 用エンドポイントを既存エンドポイント拡張で吸収するか、専用エンドポイントを追加するか
- キャッシュキーにガイダンス種別を含めるか
- レスポンスに `guidance_type` または `guidance_source` を含めるか
- クライアントの既定値を MSM にするか、前回選択を保持するか
- GSM の利用可能時刻を UI 側で制限するか、サーバーエラーに委ねるか
- GSM 解析結果が既存 `guidance_grib2` データ構造にそのまま載るか、追加メタデータが必要か

### 5.1 現時点の推奨決定

- 雨量調整は最優先で比率補正型へ修正する
- 雨量調整には `input_mode` を導入する
- `input_mode` の候補は `3hour` と `24hour`
- `input_mode` のデフォルトは `3hour` にして後方互換性を維持する
- 雨量調整には `adjustment_mode` を導入する
- `adjustment_mode` は最初はリクエスト全体で1つ選ぶ方式にする
- `adjustment_mode` の候補は `ratio_3hour`, `fill_3hour`, `fill_24hour_uniform`, `ratio_24hour_uniform`, `ratio_24hour_peak_mesh`
- `adjustment_mode` のデフォルトは `ratio_3hour` にして後方互換性を維持する
- 比率は「市町村または二次細分で表示している代表雨量の最大値」に対して計算する
- 各メッシュへは、元の `rain_timeline` に比率を掛けて反映する
- 市町村境界にまたがるメッシュは、関係市町村の比率の最大値を採用する
- エンドポイントは既存 `POST /production-soil-rainfall-index-with-urls` を拡張する
- request payload に `guidance_type` を追加する
- `guidance_type` のデフォルトは `msm` にして後方互換性を維持する
- cache key には `guidance_type` を含める
- レスポンスにも `guidance_type` を含める
- `used_urls` にも `guidance_type` を含める
- クライアントの既定値は `msm`
- ベースセッションに `guidance_type` を保存する
- フォークセッションにも `guidance_type` を保存し、`get_session_info()` でも返せるようにする
- 雨量調整 API にも `guidance_type` を渡す
  現時点で再計算ロジックが使わなくても、セッション整合性のため保持する

### 5.2 24時間入力まわりの追加推奨決定

- 24時間入力の対象 FT は以下で確定する
  - 第1区間: FT 3, 6, 9, 12, 15, 18, 21, 24
  - 第2区間: FT 27, 30, 33, 36, 39, 42, 45, 48
- FT 0 は 24時間合計に含めない
  - 予報雨量系列としての3時間積算区間だけを対象にする
- 24時間入力 UI は別画面に分けず、既存の雨量調整モーダル内で `3時間ごと` / `24時間合計` を切り替える
  - 既存の操作フローを維持しやすく、段階的な実装にも向く
- 24時間入力の初期表示値はクライアント計算ではなくサーバー集計を正とする
  - `GET /session/<session_id>/rainfall-data` を拡張し、`area_rainfall_24hour` と `subdivision_rainfall_24hour` を追加する
  - サーバー側の再計算ロジックと同じ集計ルールを使い、UI表示と実計算のズレを避ける
- 24時間入力でも、編集対象は現在の view mode に従う
  - `municipality` か `subdivision` のどちらか一方だけを同時に編集する
  - 市町村と二次細分の混在編集は第1版ではサポートしない
- `ratio_24hour_peak_mesh` の競合解決は以下で確定する
  - 通常は各 mesh_code が1つの領域にのみ属する前提で処理する
  - 保険として、同じ mesh_code に複数の編集結果がかかった場合は 24時間目標合計の最大値を採用する
  - その後、そのメッシュ固有の元3時間構成比で 3時間系列に按分する
- 24時間入力の 0 雨量ケースは以下で確定する
  - 元24時間合計が 0 かつ入力値も 0 の場合は変更なし
  - 元24時間合計が 0 かつ入力値が正の場合は変更なし
  - サーバーログに領域名、区間、モードを含む warning を出す
- API の enum 名は以下で確定する
  - `input_mode`: `3hour` | `24hour`
  - `adjustment_mode`: `ratio_3hour` | `fill_3hour` | `fill_24hour_uniform` | `ratio_24hour_uniform` | `ratio_24hour_peak_mesh`
- 既存クライアント互換は以下で確定する
  - `input_mode` 未指定時は `3hour`
  - `adjustment_mode` 未指定時は `ratio_3hour`
  - `aggregate_adjustments` 未指定時は従来どおり `adjustments` のみを使用する

---

## 6. 実装方針案

### 6.1 方針

- 第0段階: 雨量調整を比率補正型へ修正する
- 第1段階: 雨量調整に塗りつぶしモードを追加する
- 第2段階: 雨量調整に24時間雨量合計入力を追加する
- 第3段階: サーバー先行で GSM 指定時に計算できる API を追加する
- 第4段階: クライアントにガイダンス種別切替 UI を追加する
- 既存の MSM 用エンドポイント・レスポンスを壊さない形で、必要最小限の入力パラメータを追加する
- ガイダンス種別に応じて URL 生成ルールを切り替える
- GRIB2 解析は可能なら既存 `guidance_grib2` 形式を維持し、上位ロジックの変更を最小化する

### 6.1.0 雨量調整の修正方針案

意図する方式:

1. 市町村または二次細分ごとに、各 FT の代表雨量最大値を取得する
2. ユーザー入力値 / 元の代表雨量最大値 で比率を計算する
3. その比率を対象市町村に属する各メッシュの元 `rain_timeline` に適用する
4. 調整後の各メッシュ雨量から SWI / リスクを再計算する

避けるべき現在の方式:

1. ユーザー入力した市町村雨量系列を、その市町村の全メッシュに同じ値で上書きする

修正対象の中心:

- `server/src/api/controllers/session_controller.py`
- `server/src/services/rainfall_adjustment_service.py`
- 必要に応じて `server/src/services/calculation_service_numpy.py`

### 6.1.0.1 雨量調整の具体アルゴリズム案

前提:

- クライアントが編集している値は、市町村または二次細分ごとの「代表雨量最大値タイムライン」
- セッション内の各メッシュは、元の `rain_timeline` を保持している

市町村編集時:

1. 対象市町村の各 FT について、元の代表雨量最大値 `original_max` を取得する
2. ユーザー入力値 `adjusted_value` から比率 `ratio = adjusted_value / original_max` を計算する
3. 対象市町村に属する各メッシュの元 `rain_timeline[ft]` に `ratio` を掛ける
4. 境界メッシュは、関係する市町村の比率の最大値を採用する

二次細分編集時:

1. 二次細分の各 FT について、元の代表雨量最大値 `original_max` を取得する
2. 比率 `ratio = adjusted_value / original_max` を計算する
3. 二次細分に属する各市町村の全メッシュへその比率を適用する
4. 市町村境界にまたがるメッシュが複数比率を持つ場合は最大値を採用する

0除算時の扱い:

- `original_max == 0` かつ `adjusted_value == 0` の場合は `ratio = 1.0`
- `original_max == 0` かつ `adjusted_value > 0` の場合は、実装前に方針確定が必要
  推奨:
  - 初回は `ratio = 1.0` として変更なし
  - 将来必要なら「一律付与」など別仕様を設ける

今回の第一段階では、`original_max == 0` の正の入力は警告ログを出して変更なしとする案が安全

### 6.1.0.4 雨量調整の塗りつぶしモード案

目的:

- 比率補正とは別に、ユーザー入力値で対象領域内の全メッシュを同一雨量にしたいケースに対応する

基本方針:

1. 雨量調整再計算 API に `adjustment_mode` を追加する
2. `adjustment_mode = "ratio_3hour"` のときは既定の比率補正型を適用する
3. `adjustment_mode = "fill_3hour"` のときは対象領域の各メッシュ雨量を入力値で直接上書きする

第1版での仕様:

- 1回の再計算 request では `adjustment_mode` を1つだけ選ぶ
- 市町村編集でも二次細分編集でも同じ `adjustment_mode` を適用する
- `adjustments` のデータ構造は既存のまま使う
  - `Record<string, Array<{ ft, value }>>`
- モードだけ追加し、編集 UI のタイムライン構造は変えない

`fill` モードのアルゴリズム:

市町村編集時:

1. 対象市町村の各 FT について、ユーザー入力値 `adjusted_value` を取得する
2. 対象市町村に属する各メッシュの `rain_timeline[ft]` を `adjusted_value` に置き換える
3. 他市町村のメッシュは変更しない

二次細分編集時:

1. 対象二次細分の各 FT について、ユーザー入力値 `adjusted_value` を取得する
2. その二次細分に属する各市町村の全メッシュの `rain_timeline[ft]` を `adjusted_value` に置き換える

境界メッシュの扱い:

- 1つのメッシュに複数の編集結果が競合する場合は、比率補正型と同様に最大値を採用する
- これにより、複数領域を同時編集しても結果が決定的になる

UI 方針:

- 雨量調整モーダルに `比率補正` / `塗りつぶし` の切替 UI を追加する
- 既定値は `比率補正`
- 現在選択中のモードが分かるように表示する

API 互換方針:

- `adjustment_mode` 未指定時は `ratio_3hour` とみなす
- 既存クライアントからの payload はそのまま受け付ける

実装の中心:

- `client/src/components/RainfallAdjustmentModalSession.tsx`
- `client/src/features/rainfall-adjustment/types.ts`
- `client/src/features/rainfall-adjustment/utils.ts`
- `client/src/services/sessionApi.ts`
- `server/src/api/controllers/session_controller.py`
- 必要に応じて `server/src/services/rainfall_adjustment_service.py`

### 6.1.0.5 24時間雨量合計入力モード案

目的:

- 3時間ごとの入力に加えて、24時間単位の合計雨量を直接入力できるようにする
- 初期時刻から24時間後までの1区間目と、その次の24時間の2区間目を編集対象にする

基本方針:

1. 雨量調整再計算 API に `input_mode` を追加する
2. `input_mode = "3hour"` のときは既存の3時間代表雨量タイムラインを扱う
3. `input_mode = "24hour"` のときは 24時間合計雨量の2区間を扱う
4. `input_mode` と `adjustment_mode` を組み合わせて、24時間入力時の配分方式を切り替える

24時間入力の対象区間:

- 第1区間: `FT 0 < t <= 24`
- 第2区間: `FT 24 < t <= 48`

実装上は、3時間系列の FT をもとに以下のバケットに集計する:

- `window_24h_1`: FT 3, 6, 9, 12, 15, 18, 21, 24
- `window_24h_2`: FT 27, 30, 33, 36, 39, 42, 45, 48

第1版の24時間入力モード候補:

1. `fill_24hour_uniform`
   - 入力した24時間合計を8区間に均等按分する
   - 各3時間値を対象領域内の全メッシュに一律で適用する
2. `ratio_24hour_uniform`
   - 入力した24時間合計を8区間に均等按分する
   - その3時間値が代表最大値になるよう、各メッシュの元 `rain_timeline` を比率補正する
3. `ratio_24hour_peak_mesh`
   - 領域内で24時間合計が最大の格子を抽出する
   - その格子の24時間合計が入力値になるよう、元の3時間系列の比率を保ったまま倍率を掛ける
   - 他の格子は「元の24時間合計 / 最大格子の24時間合計」の比率を保って24時間合計を決める
   - その後、各格子で決まった24時間合計を、元の3時間系列の構成比で3時間ごとに按分する

24時間入力のアルゴリズム詳細:

`fill_24hour_uniform`:

1. 各24時間区間の入力値 `input_24h` を取得する
2. `input_3h = input_24h / 8` を計算する
3. 対象区間内の各 FT について、各メッシュの `rain_timeline[ft] = input_3h` とする

`ratio_24hour_uniform`:

1. 各24時間区間の入力値 `input_24h` を取得する
2. `input_3h = input_24h / 8` を計算する
3. 対象領域の各 FT ごとの代表最大値 `original_max_3h` を取得する
4. `ratio = input_3h / original_max_3h` を計算する
5. 各メッシュの元 `rain_timeline[ft]` に `ratio` を掛ける

`ratio_24hour_peak_mesh`:

1. 各24時間区間で、対象領域内の各メッシュの24時間合計 `original_sum_24h` を計算する
2. 最大24時間合計を持つメッシュ `peak_mesh` を選ぶ
3. `peak_ratio = input_24h / peak_mesh_original_sum_24h` を計算する
4. `peak_mesh` の各3時間値は、元の3時間構成比を保ったまま `peak_ratio` を掛ける
5. 他メッシュは `mesh_ratio_24h = mesh_original_sum_24h / peak_mesh_original_sum_24h` を計算する
6. `mesh_target_sum_24h = input_24h * mesh_ratio_24h` を決める
7. 各メッシュの元の3時間構成比を使って、`mesh_target_sum_24h` を3時間ごとに按分する

0除算時の扱い:

- 24時間合計が 0 で入力値も 0 の場合は変更なし
- 最大24時間合計が 0 で入力値が正の場合は、初回実装では変更なしとして警告ログを出す
- 元の3時間構成比の合計が 0 の場合も、変更なしとして警告ログを出す

UI 方針:

- 雨量調整モーダルに入力単位の切替を追加する
  - `3時間ごと`
  - `24時間合計`
- `24時間合計` 選択時は、2つの24時間区間入力欄を表示する
- `24時間合計` 選択時に選べる調整モードは以下の3つに限定する
  - `均等按分して塗りつぶし`
  - `均等按分して比率補正`
  - `最大24時間格子基準で比率補正`

API 方針:

- `input_mode` 未指定時は `3hour`
- 既存の `adjustments` は3時間入力用として維持する
- 24時間入力用には別フィールドを追加する
  - 例: `aggregate_adjustments`
- `GET /session/<session_id>/rainfall-data` は 24時間集計結果も返すように拡張する
  - `area_rainfall_24hour`
  - `subdivision_rainfall_24hour`
- 第1版では以下のような payload を想定する

```json
POST /session/<session_id>/recalculate
{
  "input_mode": "24hour",
  "adjustment_mode": "ratio_24hour_peak_mesh",
  "aggregate_adjustments": {
    "Hyogo_Kobe": [
      {"window_index": 1, "start_ft": 3, "end_ft": 24, "value": 120},
      {"window_index": 2, "start_ft": 27, "end_ft": 48, "value": 80}
    ]
  }
}
```

実装の中心:

- `client/src/components/RainfallAdjustmentModalSession.tsx`
- `client/src/features/rainfall-adjustment/types.ts`
- `client/src/features/rainfall-adjustment/utils.ts`
- `client/src/services/sessionApi.ts`
- `client/src/types/session.ts`
- `client/src/types/api.ts`
- `server/src/api/controllers/session_controller.py`
- 必要に応じて `server/src/services/rainfall_adjustment_service.py`

### 6.1.0.2 実装単位の修正案

`server/src/api/controllers/session_controller.py`

- 現在の `new_rain_timeline` を各メッシュへ一律で入れる処理を廃止する
- セッション中の各メッシュが持つ元 `rain_timeline` を基準に、メッシュごとの調整後 `rain_timeline` を生成する
- `mesh_data_list` には「メッシュごとに異なる調整後 3時間雨量」を渡す
- `mesh_code_to_rain` は比率適用後のメッシュ別タイムラインを保持する

`server/src/services/rainfall_adjustment_service.py`

- 既存の `_calculate_mesh_ratios()` を本番再計算から利用する
- 市町村と二次細分の両方から、`mesh_code -> {ft -> ratio}` を作る補助関数を整理する
- 必要なら辞書形式セッションデータを直接処理できるヘルパーを追加する

`server/src/services/calculation_service_numpy.py`

- 現在は `mesh_data_list[i]['rain_3hour']` をそのまま配列化できるので、構造自体は流用可能
- 一律上書き前提のロジックは controller 側にあるため、NumPy 側の変更は最小の可能性が高い
- ただし 1時間雨量推定の簡易ロジックが意図どおりかは別途確認対象

### 6.1.0.3 実装後の期待挙動

- 同じ市町村内でも、元の格子雨量分布に応じて調整後のメッシュ値は異なる
- 市町村代表値として集約したとき、その FT の最大値がユーザー入力値と一致する
- 二次細分編集時も、二次細分代表値の最大値が入力値と一致する
- 雨量調整前の空間分布パターンは、比率補正後も相対的に維持される

### 6.1.1 API 仕様案

既存エンドポイント:

```json
POST /production-soil-rainfall-index-with-urls
{
  "swi_initial": "2026-04-03T00:00:00Z",
  "guidance_initial": "2026-04-03T00:00:00Z",
  "guidance_type": "gsm"
}
```

`guidance_type` の候補:

- `msm`
- `gsm`

レスポンス追加候補:

```json
{
  "guidance_type": "gsm",
  "used_urls": {
    "swi_url": "...",
    "swi_initial_time": "...",
    "guidance_url": "...",
    "guidance_initial_time": "...",
    "guidance_type": "gsm"
  }
}
```

セッション情報の追加候補:

```json
{
  "session_id": "...",
  "guidance_initial_time": "...",
  "guidance_type": "gsm"
}
```

雨量調整再計算 request の追加候補:

```json
POST /session/<session_id>/recalculate
{
  "adjustments": { "...": [{"ft": 6, "value": 12}] },
  "input_mode": "3hour",
  "adjustment_mode": "ratio_3hour",
  "guidance_type": "gsm"
}
```

実装上は、未指定時にベースセッションの `guidance_type` を採用するのが安全
`adjustment_mode` 未指定時は `ratio_3hour` を採用する
`input_mode` 未指定時は `3hour` を採用する

### 6.1.2 キャッシュキー方針案

現状:

- `swi_YYYYMMDDHHMMSS_guid_YYYYMMDDHHMMSS`

変更案:

- `swi_YYYYMMDDHHMMSS_guid_msm_YYYYMMDDHHMMSS`
- `swi_YYYYMMDDHHMMSS_guid_gsm_YYYYMMDDHHMMSS`

この形式にすると:

- MSM / GSM のキャッシュ衝突を防げる
- 既存キー規則との差分が小さい
- ロックキーとしてもそのまま使える

### 6.2 影響範囲

- フロントエンド:
  - ガイダンス種別選択 UI
  - ガイダンス時刻選択肢
  - API リクエスト payload
  - 利用可能時刻の扱い
- バックエンド:
  - ガイダンス URL 生成
  - ガイダンス種別のバリデーション
  - キャッシュキー生成
  - レスポンスメタデータ
  - 必要に応じて GRIB2 解析の分岐
- 設定・デプロイ:
  - 基本的には不要
  - 必要ならローカルフォールバック用設定の拡張を検討

### 6.3 リスク・懸念点

- 比率補正型へ戻すと、現行の NumPy 一括再計算入力形式を見直す必要がある
- 元のメッシュ別雨量系列を再利用するため、セッションから取り出す雨量データの整形方法を確認する必要がある
- 市町村最大値が 0 の場合の比率定義を明確にする必要がある
- `fill` モード追加後は、UI 上で現在どちらの調整方式なのかを明示しないと誤操作が起きやすい
- `fill` モードでは、広い領域を編集した際に雨量分布が完全に失われるため、意図したモードか分かる表示が必要
- 24時間入力を導入すると、3時間入力と同じ表に混在させると誤解しやすい
- 24時間入力の3モードはアルゴリズム差が大きいため、名称だけでなく説明表示も必要
- `ratio_24hour_peak_mesh` は領域内最大格子の抽出と24時間合計比の扱いがあるため、実装と検証が最も重い
- `rainfall-data` をクライアント側だけで 24時間集計すると、サーバー再計算の基準とずれる可能性がある
- 現行データモデル上は通常メッシュ競合は起きにくいが、保険として重複 `mesh_code` への解決ルールを持っておく
- GSM の格子系が MSM / SWI と異なるため、`get_data_num()` による座標変換結果が十分に整合するか確認が必要
- FT 刻みや最大 FT の違いにより、クライアントの時刻移動ロジックが壊れる可能性がある
- キャッシュキーにガイダンス種別を含めないと MSM / GSM の結果が衝突する
- 既存のテストやドキュメントが MSM 専用前提で書かれている
- 格子サイズ差により、GSM では隣接する複数メッシュが同一雨量値を共有するが、これは仕様として受け入れる必要がある
- `rainfall_controller.py` や調整再計算系にも将来的に `guidance_type` を波及させる必要が出る可能性がある
- セッションに `guidance_type` を持たせないまま UI だけ GSM 対応すると、雨量調整後に元データ種別を追跡できなくなる
- 将来、雨量調整で GRIB2 を再取得する実装に戻した場合、`guidance_type` 未保持だと再現不能になる

---

## 7. 作業タスク

1. 雨量調整の現状差分整理
   現行の一律上書き型と、意図している比率補正型の差分を明文化する
2. 雨量調整サーバー設計整理
   比率計算、境界メッシュ扱い、0除算時の方針、NumPy再計算との接続方法を確定する
3. 雨量調整実装
   `session_controller.py` 中心の本番再計算経路を比率補正型へ修正する
4. 雨量調整検証
   代表雨量最大値が入力値と一致し、格子分布は保持されることを確認する
5. 雨量調整塗りつぶし設計整理
   `adjustment_mode` の渡し方、UI 切替、境界メッシュ時の優先ルールを確定する
6. 雨量調整塗りつぶし実装
   `fill` モードで領域内全格子を入力値で上書きできるようにする
7. 雨量調整塗りつぶし検証
   対象領域の全メッシュが入力値になり、代表雨量最大値も入力値と一致することを確認する
8. 24時間入力設計整理
   `input_mode`、24時間区間定義、3種類の24時間調整モード、payload 形式を確定する
9. 24時間入力実装
   UI・API・サーバー再計算で24時間合計入力を扱えるようにする
10. 24時間入力検証
   各24時間モードで、24時間合計値と3時間系列の変換結果が仕様どおりになることを確認する
11. サーバー設計整理
   `guidance_type` の受け取り方、URL 生成、キャッシュキー方針を確定する
12. サーバー実装
   ConfigService / MainController / MainService / 必要なら Grib2Service を拡張する
13. サーバー検証
   MSM 既存挙動を維持しつつ、GSM 指定で URL とレスポンスが正しいことを確認する
14. クライアント設計整理
   MSM / GSM 切替 UI、時刻候補、既定値、レスポンス表示項目を確定する
15. クライアント実装
   入力 UI・API 呼び出し・型定義・時刻移動ロジックを更新する
16. セッション / 雨量調整対応
   ベースセッション・フォークセッション・再計算 API に `guidance_type` を通す
17. 動作確認
   MSM と GSM の双方で取得・表示・時刻切替・雨量調整が正しく動くことを確認する
18. ドキュメント更新
   必要に応じて API や運用メモを更新する

### 7.4 実装着手順（そのまま作業に入るための詳細）

#### 第0段階: 雨量調整を比率補正型へ修正

1. `session_controller.py` の `recalculate_with_adjusted_rainfall()` に `adjustment_mode` の受け取りを追加する
2. 既定値を `ratio_3hour` にし、既存 request をそのまま受け付ける
3. `adjustments` を現在の市町村一律上書きではなく、`mesh_code -> ft -> ratio` を介して各メッシュへ適用する構造に置き換える
4. `rainfall_adjustment_service.py` に、辞書形式セッションデータから
   - 市町村代表最大値取得
   - 二次細分代表最大値取得
   - `mesh_code -> ft -> ratio` 生成
   を行う helper を追加または整理する
5. `mesh_code_to_rain` へ格納する値を、メッシュ別の調整後 `rain_timeline` に差し替える
6. `CalculationServiceNumpy` へは、メッシュごとに異なる `rain_3hour` を渡す
7. `original_max == 0` の場合は
   - 入力値 0: 変更なし
   - 入力値 正: 変更なし + warning log
   として処理する
8. サーバー動作確認後、`staging` へ昇格、コミット、push、確認依頼を行う

#### 第1段階: 3時間入力の塗りつぶし追加

1. `client/src/features/rainfall-adjustment/types.ts` に `AdjustmentMode` 型を追加する
2. `RainfallAdjustmentModalSession.tsx` に `ratio_3hour` / `fill_3hour` の切替 UI を追加する
3. `sessionApi.ts` の再計算 request に `adjustment_mode` を追加する
4. `session_controller.py` で `adjustment_mode == "fill_3hour"` を分岐処理する
5. `fill_3hour` では対象領域の各メッシュ `rain_timeline[ft]` を入力値で直接上書きする
6. 複数領域が同一 `mesh_code` に作用した場合は最大値を採用する
7. UI 上で現在のモード名を明示する
8. 動作確認後、`staging` へ昇格、コミット、push、確認依頼を行う

#### 第2段階: 24時間入力追加

1. `RainfallAdjustmentModalSession.tsx` に `input_mode` 切替 UI を追加する
   - `3時間ごと`
   - `24時間合計`
2. `client/src/features/rainfall-adjustment/types.ts` に以下を追加する
   - `InputMode`
   - 24時間入力値型
   - 24時間用 adjustment mode 型
3. `sessionApi.ts` の再計算 request を拡張し
   - `input_mode`
   - `aggregate_adjustments`
   を送れるようにする
4. `get_rainfall_data()` を拡張し、以下を返す
   - `area_rainfall_24hour`
   - `subdivision_rainfall_24hour`
5. `RainfallAdjustmentModalSession.tsx` は 24時間入力時に上記 24時間集計値を初期表示に使う
6. `session_controller.py` に `input_mode == "24hour"` の分岐を追加する
7. `fill_24hour_uniform` を実装する
   - 24時間入力値を 8 分割し
   - 各メッシュへ均等値を直接上書きする
8. `ratio_24hour_uniform` を実装する
   - 24時間入力値を 8 分割し
   - FT ごとの代表最大値を基準に比率補正する
9. `ratio_24hour_peak_mesh` を実装する
   - 領域内の最大24時間格子を抽出
   - その格子の24時間合計が入力値になるよう倍率を決める
   - 他格子は元の24時間合計比を維持して24時間目標値を決める
   - 各メッシュの元3時間構成比で 3時間系列へ戻す
10. 24時間合計が 0 のケースは変更なし + warning log とする
11. 動作確認後、`staging` へ昇格、コミット、push、確認依頼を行う

#### 第3段階: サーバー GSM 対応

1. `main_controller.py` で `guidance_type` を受け取る
2. `config_service.py` の `build_guidance_url()` を `msm` / `gsm` 対応にする
3. `cache_service.py` の cache key に `guidance_type` を追加する
4. `main_service.py` に `guidance_type` を通し、`used_urls` とレスポンスへ反映する
5. `guidance_type` 未指定時は `msm` として扱う
6. GSM サンプルで
   - URL 生成
   - GRIB2 読み込み
   - available_times
   を確認する
7. 動作確認後、`staging` へ昇格、コミット、push、確認依頼を行う

#### 第4段階: クライアント GSM 切替

1. `ProductionSession.tsx` に MSM / GSM 切替 UI を追加する
2. `useProductionSession.ts` と `api.ts` に `guidance_type` を通す
3. `dateTime.ts` の時刻候補をガイダンス種別ごとに出し分ける
4. 時刻送り UI を固定 `±3時間` ではなく `available_times` ベースに変更する
5. 取得結果表示に `guidance_type` を出す
6. 動作確認後、`staging` へ昇格、コミット、push、確認依頼を行う

#### 第5段階: セッションと雨量調整まで GSM 一貫対応

1. `session_service.py` のベースセッション保存に `guidance_type` を追加する
2. フォークセッションにも `guidance_type` を引き継ぐ
3. `get_session_info()` で `guidance_type` を返す
4. 雨量調整モーダルが現在セッションの `guidance_type` を保持するようにする
5. 雨量調整再計算 request にも `guidance_type` を含める
6. 画面上で現在の計算種別が見えるようにする
7. MSM / GSM の双方で、雨量調整後も `guidance_type` が失われないことを確認する
8. 動作確認後、`staging` へ昇格、コミット、push、確認依頼を行う

### 7.5 実装開始時の順序

実装は以下の順で進める:

1. 第0段階をサーバー中心に完了させる
2. 第1段階で UI と API に `fill_3hour` を追加する
3. 第2段階で `rainfall-data` 拡張を先に入れ、その後 24時間再計算を実装する
4. 第3段階でサーバー GSM 対応を行う
5. 第4段階でクライアント GSM 切替を行う
6. 第5段階でセッション情報と雨量調整まで GSM 一貫対応にする

### 7.6 実装開始の判断基準

以下が満たされていれば実装を開始してよい:

- API enum 名が確定している
- 24時間対象 FT 範囲が確定している
- 0雨量ケースの扱いが確定している
- `staging` 昇格手順が確定している
- 各段階の変更対象ファイルが整理されている

現時点では、上記条件は満たしている

### 7.1 各段階完了後の必須手順

各段階の実装と検証が終わるたびに、以下を実施する:

1. `develop` 上の変更内容を整理する
2. `staging` に変更内容を反映する
3. `staging` で必要な確認を行う
4. `staging` でコミットする
5. GitHub に反映する
6. ユーザーへ動作確認を依頼する

### 7.2 `develop` から `staging` へ反映する際のルール

`docs/staging-promotion-rules.md` に従い、以下を守る:

- `staging` では `SOIL_RAINFALL_ROUTE_PROFILE=production` を前提に確認する
- 本番クライアント向けルートだけが公開される状態を維持する
- 開発・検証用 route を `staging` に露出させない
- 昇格対象に不要ファイルを含めない
  - `test_*.py`
  - `server/tests/`
  - `.pytest_cache/`
  - `__pycache__/`
  - `*.pyc`
- `develop` から `staging` に反映する際は、`staging` 用の設定や運用差分を壊さないように確認する
- `staging` 反映後は production profile 前提で動作確認する

### 7.3 各段階ごとの反映単位

- 第0段階（雨量調整の比率補正型修正）が完了したら、その変更だけを `staging` に反映して確認を依頼する
- 第1段階（雨量調整の塗りつぶしモード追加）が完了したら、その変更だけを `staging` に反映して確認を依頼する
- 第2段階（雨量調整の24時間入力追加）が完了したら、その変更だけを `staging` に反映して確認を依頼する
- 第3段階（サーバー GSM 対応）が完了したら、その変更だけを `staging` に反映して確認を依頼する
- 第4段階（クライアント GSM 切替対応）が完了したら、その変更だけを `staging` に反映して確認を依頼する
- セッション / 雨量調整まで含めた GSM 一貫対応が完了したら、その変更だけを `staging` に反映して確認を依頼する

---

## 8. 確認項目

- 雨量調整後、市町村代表雨量の最大値が入力値と一致すること
- 雨量調整後もメッシュごとの差分が残り、一律同値にならないこと
- 境界メッシュで最大比率ルールが適用されること
- 元代表雨量が 0 のケースで破綻しないこと
- `adjustment_mode` を送らない既存 request payload でも `ratio_3hour` として利用できること
- `input_mode` を送らない既存 request payload でも `3hour` として利用できること
- `rainfall-data` が 24時間集計値を返し、UI 初期表示とサーバー再計算の基準が一致すること
- `mesh_code_to_rain` に保持される値が市町村一律値ではなく、メッシュ別比率適用後の値になること
- `fill` モードでは対象領域内の全メッシュが入力値で上書きされること
- `fill` モードでも市町村 / 二次細分の代表雨量最大値が入力値と一致すること
- `fill` モードで複数領域が競合した場合に最大値ルールで決定されること
- UI 上で現在の調整モードが識別できること
- 24時間入力 UI で、第1区間・第2区間の入力ができること
- `fill_24hour_uniform` で 24時間合計が入力値と一致し、8区間が均等値になること
- `ratio_24hour_uniform` で 24時間合計が入力値と一致し、各 FT は均等按分を基準に比率補正されること
- `ratio_24hour_peak_mesh` で、領域内最大24時間格子の24時間合計が入力値と一致すること
- `ratio_24hour_peak_mesh` で、他格子の24時間合計が元の最大格子比を保って変化すること
- 元の24時間合計が 0 の領域で正の値を入力しても破綻せず、警告ログで処理されること
- MSM 指定時に既存の URL 形式が維持されること
- GSM 指定時に `guid_gsm_grib2_YYYYMMDDHHMMSS_rmax.bin` が生成されること
- SWI 初期時刻とガイダンス初期時刻の差分フィルタが GSM でも成立すること
- GSM の結果で `available_times` が正しく返ること
- クライアントが MSM / GSM それぞれの初期時刻候補を正しく出し分けること
- キャッシュが MSM と GSM で衝突しないこと
- 6府県の全メッシュが GSM 領域内に収まること
- `get_data_num()` が GSM の `d_lat` / `d_lon` を用いて正常範囲のインデックスを返すこと
- 既存 payload に `guidance_type` を送らない場合でも MSM として処理できること
- GSM で開始したセッションの `guidance_type` がセッション情報に残ること
- GSM で開始したセッションから雨量調整しても `guidance_type` が失われないこと
- フォークセッションでも `guidance_type` がベースセッションと一致すること

---

## 9. 完了条件

- 雨量調整が比率補正型として動作する
- 雨量調整が `ratio` / `fill` の両モードで動作する
- 雨量調整が3時間入力と24時間入力の両方で動作する
- サーバーで MSM / GSM の両方を指定して計算できる
- クライアントで MSM / GSM を切り替えて取得できる
- 雨量調整機能が MSM / GSM の双方で同じ種別を引き継いで動作する
- 既存 MSM 機能が回帰しない
- 主要な時刻パターンで動作確認が完了している

---

## 10. メモ

- 現状の `build_guidance_url()` は MSM 専用実装
- 現状のクライアントは 3 時間刻み前提が複数箇所に分散している
- サーバー先行で実装し、クライアントは後段で切り替え UI を追加する
- GSM サンプル `guid_gsm_grib2_20260403000000_rmax.bin` は既存 `unpack_guidance_grib2()` で読めた
- GSM サンプルでは `FT=6..84`、`grid_num=18271`、`d_lat=0.2度`、`d_lon=0.25度`
- MSM サンプルでは `FT=3..78`、`grid_num=286720`、`d_lat=0.05度`、`d_lon=0.0625度`
- 6府県メッシュの GSM インデックスは確認した範囲で全て正常範囲内
- 6府県メッシュは GSM 領域内に収まっているため、計算不能になるケースは現時点では見えていない
- GSM では同一 GSM 格子に複数メッシュが対応するため、空間分解能低下は仕様として扱う
- 現状の雨量調整再計算はセッション内 `rain_timeline` を使うため、ロジック自体は source-agnostic
- ただし `guidance_type` を保持していないため、GSM 正式対応にはセッション設計の拡張が必要
- 現状の本番雨量調整再計算は比率補正ではなく、市町村ごとの一律上書き型になっている
