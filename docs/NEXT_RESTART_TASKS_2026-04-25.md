# 次回再開タスク

**作成日**: 2026年4月25日
**前提**: 雨量調整の比率補正、塗りつぶし、24時間入力までは実装済み。次は GSM 対応に着手する。

---

## 1. 次回の最優先タスク

1. サーバー API に `guidance_type` を追加する
2. `ConfigService.build_guidance_url()` を MSM / GSM 両対応にする
3. セッション、軽量レスポンス、`used_urls`、キャッシュキーに `guidance_type` を通す
4. サーバー側で GSM 指定時の `available_times` が正しく返ることを確認する
5. その後にクライアントの MSM / GSM 切替 UI を追加する

---

## 2. 具体的な着手順

### 2.1 サーバー

- `POST /production-soil-rainfall-index-with-urls` の request payload に `guidance_type` を追加する
- `guidance_type` 未指定時は `msm` を既定値にする
- `server/src/config/config_service.py` で MSM / GSM の URL 生成を切り替える
- `server/src/api/controllers/main_controller.py` で `guidance_type` を受け取り、レスポンスにも含める
- `server/src/services/session_service.py` でベースセッション・フォークセッションに `guidance_type` を保存する
- `get_session_info()` でも `guidance_type` を返す
- キャッシュキー生成箇所で `guidance_type` を区別する
- `used_urls` にも `guidance_type` を含める

### 2.2 雨量調整との整合

- 雨量調整再計算 API にも `guidance_type` を渡せるようにする
- 再計算時に使わなくても、セッション整合性のため保存・引き継ぎだけは行う
- GSM で開始したセッションを雨量調整しても `guidance_type` が失われないことを確認する

### 2.3 クライアント

- `client/src/services/api.ts` で `guidance_type` を送れるようにする
- `client/src/features/production-session/hooks/useProductionSession.ts` に `guidance_type` を通す
- `client/src/pages/ProductionSession.tsx` に MSM / GSM の選択 UI を追加する
- ガイダンス種別に応じて時刻候補を切り替える
- `±3時間` 前提の時刻送りロジックを見直す

---

## 3. 先に確認するとよいポイント

- GSM の初期時刻は 6 時間ごとであること
- GSM のファイル名は `guid_gsm_grib2_YYYYMMDDHHMMSS_rmax.bin` であること
- MSM の既存動作を壊さないため、既定値は `msm` のままにすること
- GSM は MSM より格子が粗いため、同一 GSM 格子に複数メッシュが載る前提で扱うこと

---

## 4. 次回の完了目安

- サーバー単体で MSM / GSM の両方を指定して計算を開始できる
- レスポンスとセッション情報で `guidance_type` を追跡できる
- キャッシュが MSM と GSM で衝突しない
- 雨量調整後のフォークセッションでも `guidance_type` が保持される

---

## 5. 関連ファイル

- `docs/DEVELOPMENT_WORK_PLAN.md`
- `server/src/config/config_service.py`
- `server/src/api/controllers/main_controller.py`
- `server/src/services/main_service.py`
- `server/src/services/session_service.py`
- `client/src/services/api.ts`
- `client/src/features/production-session/hooks/useProductionSession.ts`
- `client/src/pages/ProductionSession.tsx`
