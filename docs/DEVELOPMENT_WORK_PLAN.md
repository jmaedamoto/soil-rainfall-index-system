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
3. その後に GSM 対応を進める

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
- 雨量調整には `adjustment_mode` を導入する
- `adjustment_mode` は最初はリクエスト全体で1つ選ぶ方式にする
- `adjustment_mode` の候補は `ratio` と `fill`
- `adjustment_mode` のデフォルトは `ratio` にして後方互換性を維持する
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

---

## 6. 実装方針案

### 6.1 方針

- 第0段階: 雨量調整を比率補正型へ修正する
- 第1段階: 雨量調整に塗りつぶしモードを追加する
- 第2段階: サーバー先行で GSM 指定時に計算できる API を追加する
- 第3段階: クライアントにガイダンス種別切替 UI を追加する
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
2. `adjustment_mode = "ratio"` のときは既定の比率補正型を適用する
3. `adjustment_mode = "fill"` のときは対象領域の各メッシュ雨量を入力値で直接上書きする

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

- `adjustment_mode` 未指定時は `ratio` とみなす
- 既存クライアントからの payload はそのまま受け付ける

実装の中心:

- `client/src/components/RainfallAdjustmentModalSession.tsx`
- `client/src/features/rainfall-adjustment/types.ts`
- `client/src/features/rainfall-adjustment/utils.ts`
- `client/src/services/sessionApi.ts`
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
  "adjustment_mode": "ratio",
  "guidance_type": "gsm"
}
```

実装上は、未指定時にベースセッションの `guidance_type` を採用するのが安全
`adjustment_mode` 未指定時は `ratio` を採用する

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
8. サーバー設計整理
   `guidance_type` の受け取り方、URL 生成、キャッシュキー方針を確定する
9. サーバー実装
   ConfigService / MainController / MainService / 必要なら Grib2Service を拡張する
10. サーバー検証
   MSM 既存挙動を維持しつつ、GSM 指定で URL とレスポンスが正しいことを確認する
11. クライアント設計整理
   MSM / GSM 切替 UI、時刻候補、既定値、レスポンス表示項目を確定する
12. クライアント実装
   入力 UI・API 呼び出し・型定義・時刻移動ロジックを更新する
13. セッション / 雨量調整対応
   ベースセッション・フォークセッション・再計算 API に `guidance_type` を通す
14. 動作確認
   MSM と GSM の双方で取得・表示・時刻切替・雨量調整が正しく動くことを確認する
15. ドキュメント更新
   必要に応じて API や運用メモを更新する

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
- 第2段階（サーバー GSM 対応）が完了したら、その変更だけを `staging` に反映して確認を依頼する
- 第3段階（クライアント GSM 切替対応）が完了したら、その変更だけを `staging` に反映して確認を依頼する
- セッション / 雨量調整まで含めた GSM 一貫対応が完了したら、その変更だけを `staging` に反映して確認を依頼する

---

## 8. 確認項目

- 雨量調整後、市町村代表雨量の最大値が入力値と一致すること
- 雨量調整後もメッシュごとの差分が残り、一律同値にならないこと
- 境界メッシュで最大比率ルールが適用されること
- 元代表雨量が 0 のケースで破綻しないこと
- `adjustment_mode` を送らない既存 request payload でも `ratio` として利用できること
- `mesh_code_to_rain` に保持される値が市町村一律値ではなく、メッシュ別比率適用後の値になること
- `fill` モードでは対象領域内の全メッシュが入力値で上書きされること
- `fill` モードでも市町村 / 二次細分の代表雨量最大値が入力値と一致すること
- `fill` モードで複数領域が競合した場合に最大値ルールで決定されること
- UI 上で現在の調整モードが識別できること
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
