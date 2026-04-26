# 次回再開タスク

**更新日**: 2026年4月26日
**前提**: GSM 対応はサーバー、クライアント、セッション、雨量調整、staging 実確認まで完了した。

---

## 1. 次回の最優先タスク候補

1. GSM 対応で追加した挙動を恒久テストへ整理する
2. staging で確認した内容を開発ドキュメントへ反映しきる
3. 次の機能テーマを決めて再開用メモを作り直す

---

## 2. 追加してよいテスト候補

- `guidance_type=gsm` で無効な UTC 時刻を送ったときに `400` が返ること
- `guidance_type` がフォークセッションでも保持されること
- キャッシュキーが MSM / GSM で衝突しないこと
- GSM の JST 候補が `03, 09, 15, 21` であること
- GSM セッションの雨量調整がタイムアウトせず完了すること

---

## 3. 今回完了したこと

- `POST /production-soil-rainfall-index-with-urls` が `guidance_type=msm|gsm` を受け付ける
- `ConfigService.build_guidance_url()` が MSM / GSM 両対応になった
- セッション、軽量レスポンス、`used_urls`、キャッシュキーに `guidance_type` が通った
- 雨量調整後のフォークセッションでも `guidance_type` が保持される
- GSM の無効時刻はダウンロード前に `400` で弾くようになった
- クライアントで MSM / GSM の切替と GSM 用 JST 時刻候補が使えるようになった
- staging で GSM 取得と雨量調整の動作確認が完了した

---

## 4. 関連ファイル

- `docs/DEVELOPMENT_WORK_PLAN.md`
- `server/src/config/config_service.py`
- `server/src/api/controllers/main_controller.py`
- `server/src/services/session_service.py`
- `server/src/services/rainfall_adjustment_service.py`
- `client/src/features/production-session/utils/dateTime.ts`
- `client/src/pages/ProductionSession.tsx`
