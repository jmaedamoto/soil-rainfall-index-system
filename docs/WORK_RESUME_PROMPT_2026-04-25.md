# 作業再開プロンプト

以下を前提に、このリポジトリの実装作業を再開してください。

## 前提

- リポジトリ: `soil-rainfall-index-system`
- ブランチ: `develop`
- 雨量調整機能の以下は実装済み
  - 比率補正型
  - 塗りつぶしモード
  - 24時間入力
- 未着手の主作業は GSM 対応

## 最初に確認するファイル

- `docs/DEVELOPMENT_WORK_PLAN.md`
- `docs/NEXT_RESTART_TASKS_2026-04-25.md`
- `server/src/config/config_service.py`
- `server/src/api/controllers/main_controller.py`
- `server/src/services/session_service.py`
- `client/src/features/production-session/hooks/useProductionSession.ts`
- `client/src/pages/ProductionSession.tsx`

## 今回の目的

次の段階として、サーバー側の `guidance_type=msm|gsm` 対応を進める。

## 最初の実装タスク

1. `POST /production-soil-rainfall-index-with-urls` の request payload に `guidance_type` を追加する
2. `guidance_type` 未指定時は `msm` を既定値にする
3. `ConfigService.build_guidance_url()` を MSM / GSM 両対応にする
4. セッション、軽量レスポンス、`used_urls`、キャッシュキーに `guidance_type` を通す
5. 雨量調整後のフォークセッションでも `guidance_type` が失われないようにする

## 実装時の注意

- 既存 MSM 挙動を壊さない
- 後方互換のため `guidance_type` の既定値は `msm`
- GSM のファイル名は `guid_gsm_grib2_YYYYMMDDHHMMSS_rmax.bin`
- GSM の初期時刻は 6 時間ごと
- クライアント UI の切替はサーバー対応後に行う

## 完了条件

- サーバー単体で MSM / GSM の両方を指定して計算開始できる
- レスポンスとセッション情報で `guidance_type` を追跡できる
- キャッシュが MSM と GSM で衝突しない
- 雨量調整後のフォークセッションでも `guidance_type` が保持される

## 補足

- 今日時点の進捗メモは `docs/DEVELOPMENT_WORK_PLAN.md` の「11. 2026年4月25日時点の進捗メモ」に追記済み
- 次回タスクリストは `docs/NEXT_RESTART_TASKS_2026-04-25.md` に整理済み
