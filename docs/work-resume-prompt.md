# 作業再開メモ（2026-10-16）

## 現在の作業

雨量調整の入力地域を拡張し、ユーザーによるstaging実機確認を待っています。
開発ブランチは `develop`。誤って作成した `development` は削除済みです。

- develop実装コミット: `d594247`
- staging反映コミット: `23d4f85`（GitHubへpush済み）
- ローカルのstaging作業ツリー: `/tmp/soil-rainfall-staging`（一時パス。再開時に存在を確認）
- 実機への配置・実機試験結果はまだ確認していません。

## 実装内容

- 用語を「市町村等をまとめた地域」に統一。内部識別子 `secondary_subdivisions` 等は互換性のため維持。
- 一次細分の全国対応表: `server/config/forecast_area_hierarchy.json`。
- 入力地域は市町村別、市町村等をまとめた地域別、一次細分ごと、府県ごとの4種類。
- 一次細分・府県モードではセッション内の全府県を同時表示し、府県選択欄は非表示。
- 3時間・24時間入力に対応。補正基準は選択した入力地域全体のメッシュから算出。
- セル内の数値欄から1セルずつ直接編集でき、入力欄クリックでフォーカスと単一選択を同期。
  数値欄以外のセル面で範囲・複数選択を行う。最大格子塗りつぶし中は個別入力を無効化。
- 再計算では現在の入力・表示単位で変更したFTだけを送信。
- APIの `scope_rainfall` / `scope_errors` / `adjustment_scope` を追加。
- 詳細は `RAINFALL_ADJUSTMENT_FEATURE.md` と `server/config/FORECAST_AREA_HIERARCHY.md`。

## 検証と昇格時の注意

- developの既存テストと追加テスト、TypeScript型チェック・ビルドが通過。
- staging上の地域単位テスト24件、DOM操作テスト、フロントビルドが通過。
- stagingのproduction profile公開5ルート・不要ファイル検査が通過。
- 実ブラウザのレイアウト確認はOSライブラリ不足のため未実施。
- stagingのCSV表示順、ツールチップ、キャッシュ・セッション改善、配信パス
  `/staging/dosya/`、画面表記「動作検証環境」を維持して競合を解消。
- developとstagingには従来から差分がある。ファイル全体の上書きで昇格しない。
- テストはdevelopに保持し、staging/mainのリリースpayloadへは含めない。
- 実機ではフロント・バックエンドの両方と追加JSON設定を更新する。
- 現在のdevelopの手元には近畿6府県のCSVのみ存在する。中国・四国の対応表は収録済みだが、
  当該CSVとの照合は未実施。対象14府県を6府県へ減らす意図ではない。

## 次回の進め方

1. `git status --short --branch`、`git branch -vv`、`git log --oneline -5` を確認する。
2. 実機確認の結果・不具合報告を受けてdevelopで修正する。
3. staging反映の指示があれば既存設定を維持して昇格・検証・pushする。
4. 「保存してください」は関連Markdown更新・コミット・GitHub反映まで行う。詳細は `CLAUDE.md`。
