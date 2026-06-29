# 作業再開プロンプト

次回以降、このリポジトリで作業を始めるときに最初に貼るプロンプトです。

```text
/workspaces/soil-rainfall-index-system の作業を再開します。

まず以下を確認して、現状を短く整理してください。
- git status --short --branch
- git branch -vv
- git log --oneline --decorate --graph -25
- CLAUDE.md
- RAINFALL_ADJUSTMENT_FEATURE.md
- docs/staging-promotion-rules.md
- server/docs/CACHE_SYSTEM.md
- server/deploy/DEPLOY_GUIDE.md
- server/config/URL_CONFIG_GUIDE.md
- docs/high-load-cache-timeout-investigation.md
- client/src/App.tsx
- client/src/features/production-session/regions.ts
- client/src/services/api.ts
- server/src/api/controllers/main_controller.py
- server/src/services/cache_service.py
- server/src/services/session_service.py
- server/config/app_config.yaml

前回把握した前提:
- 現在の主作業ブランチは staging。
- staging は production profile 前提のリリース用ブランチ。
- 本番公開 API は以下のみ:
  - POST /production-soil-rainfall-index-with-urls
  - GET /session/<session_id>/prefecture/<prefecture_code>
  - GET /session/<session_id>/risk-at-time
  - GET /session/<session_id>/rainfall-data
  - POST /session/<session_id>/recalculate
- フロントは /kinki, /chugoku, /shikoku の地方別ページ。
- バックエンドは Flask、フロントは React/TypeScript/Vite。
- キャッシュ、セッション復元、同時計算ロック、雨量調整再計算、フロントのセッション表示状態管理が最近の主要テーマ。
- 高負荷試験で確認された stale tmp 起因の10分タイムアウトは対処済み。詳細は docs/high-load-cache-timeout-investigation.md を参照する。
- キャッシュヒット時の初期APIは `.summary.json` を使い、`.json.gz` 全体を展開せずに軽量セッションレスポンスを返す。summary がない既存gzipでは `*.summary.lock.json` で作成を1件に絞る。
- キャッシュヒットで作るベースセッションは、最初は cache_key と summary だけを保持する。府県データなど完全データが必要になった時点で gzip から materialize する。
- 同一プロセス内では `CACHE_MEMORY_MAX_RESULTS` 件まで gzip 展開済み結果を共有する。未設定時は2件、0で無効。
- `.json.gz` 作成後も `.calculating.json` が残り、フロントがデータ取得中のままになる不具合への対策を追加済み。
  - `POST /production-soil-rainfall-index-with-urls` は先に `get_cached_result(cache_key)` を実行する。`.json.gz` が正常に読める場合は、残留 `.calculating.json` を完成済みキャッシュのロックとして回収してキャッシュ即時返却する。
  - `cache_service.py` の `release_calculation_lock()` / `release_calculation_slot()` は削除成否を返す。同一プロセス所有のロックは、所有 token がメモリから失われていても削除を許可する。
  - `main_controller.py` はロック解放の成否をログへ出す。`キャッシュ保存完了後に計算ロック解放 ... lock_released=True slot_released=True` を確認する。
  - 実環境で再発する場合は、まず実ログで `キャッシュ読み込みエラー`、`完成済みキャッシュの残留計算ロックを削除`、`ロック削除エラー`、`キャッシュ作成中のため再試行応答` の有無を確認する。
  - `.json.gz` 保存後、ロック解放前に Apache/mod_wsgi timeout、daemon 再起動、プロセス終了が起きると gzip と calculating が併存し得る。gzip が正常なら残留ロックは回収されるため、gzip 読み込み失敗や後続セッション API 待ちも併せて切り分ける。
  - フロントは `client/src/services/api.ts` で `202` または 504/timeout を最大10分ポーリングする。サーバーが `202 calculating` を返し続けると画面は「データ取得中」のままになる。
- リスク時系列表の表示モードは ProductionSession 側で親制御する。全府県一覧へ切り替える前に未ロード府県を取得し、滋賀県など初期府県だけの一覧を表示しない。
- ソースコードを改修した場合は、同じ作業内で関連する Markdown を確認し、実装内容・運用手順・既知課題と矛盾しないように更新する。
- staging/main では server/tests、test_*.py、.pytest_cache、__pycache__、*.pyc をリリース payload に含めない。
- 昇格確認は python scripts/check_production_promotion.py を使う。

作業を始める前に、未コミット差分があれば内容を確認し、ユーザーの変更を勝手に戻さないでください。
```

具体的な作業内容が決まっている場合は、上のプロンプトの末尾に今回のタスクを1行追加してください。
