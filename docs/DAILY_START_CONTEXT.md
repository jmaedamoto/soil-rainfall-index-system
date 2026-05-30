# Daily Start Context

## 現在地

- 一連の 504 対応作業は完了済み
- 現在は作業が一段落し、次の機能追加に入る前の区切り段階
- 中国・四国8県の CSV は `server/data/` に追加済みで、削除しない
- 14府県は地方別ページで扱う前提
- 六府県運用へ戻す前提ではない

## 504 問題の扱い

- 504 は開発側で直接対処できない外部要因によるものとして扱う
- 追加の 504 切り分け作業は不要
- 対応方針は、ページを以下の3つに分割し、各 API の戻り値を削減すること
  - 近畿
  - 中国
  - 四国
- 分割実装、動作確認、`staging` 反映確認は完了済み

## 地方別ページ分割の現仕様

- クライアントの入口:
  - `/kinki`
  - `/chugoku`
  - `/shikoku`
- `/` は `/kinki` にリダイレクトする
- API リクエストには `region` を渡す
- サーバー側は `REGION_PREFECTURES[region]` に基づいて対象府県を絞る
- キャッシュキーにも `region` を含める

## 重要な現在仕様

- 正規入力:
  - `dosha_*.csv`
  - `2_2_*.csv`
- `dosyakei_*.csv` は実行入力から外した
- `Mesh.level4_curve` は内部保持のみ
- 既存互換のため `2_2` の 0mm 列を `dosyakei_bound` に入れている
- API レスポンスには `level4_curve` と boundary を原則出さない
- 再計算時は `mesh_code` から静的 lookup で boundary / `level4_curve` を引く

## レベル判定の現仕様

- `legacy`
  - レベル4: `level4_curve[round(1時間雨量)]` を閾値に使う
  - レベル3: `warning_bound <= SWI < level4`
  - レベル2: `advisary_bound <= SWI < warning_bound`
- `lead_time_to_level4`
  - レベル4判定そのものは上と同じ
  - レベル3は「最初のレベル4到達の3時間前から」
  - レベル2は `legacy` と同じ
  - 旧来のレベル3は残さず、先行3時間だけをレベル3にする

## 直近で入った主な修正

- `2_2_*.csv` から 151 点のレベル4カーブを読み込む
- 雨量調整後も `risk_rule` を保持する
- 雨量調整画面の市町村順を `dosha_*.csv` 出現順に固定した
- `risk-at-time` は常に `mesh_coords` を返す
- クライアント/サーバー内の `300s` タイムアウトを `600s` に引き上げた
- 本番ページを近畿・中国・四国に分割した
- 地方別リクエストに合わせてサーバー処理とキャッシュキーを調整した

## 地方分割に関係する主なファイル

- フロント:
  - `client/src/App.tsx`
  - `client/src/features/production-session/regions.ts`
  - `client/src/features/production-session/hooks/useProductionSession.ts`
  - `client/src/pages/ProductionSession.tsx`
  - `client/src/services/api.ts`
  - `client/src/types/session.ts`
- サーバー:
  - `server/src/api/controllers/main_controller.py`
  - `server/src/models/data_models.py`
  - `server/src/services/cache_service.py`
  - `server/src/services/data_service.py`

## 次回の最優先タスク

1. 504 調査へ戻らず、地方別ページ分割は完了済みとして扱う
2. `git status --short` と直近ログで作業ツリーの状態を確認する
3. `server/src/services/main_service.py` などの既存ローカル変更を、新しい作業に混ぜない
4. 次の機能追加の内容を確認してから着手する

## 毎回の開始手順

1. `git status --short`
2. `git log --oneline -5`
3. 現在ブランチの確認
4. 未追跡ファイルと既存差分の確認
5. 次の作業対象が既存ローカル変更と衝突しないか確認
