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
- リスク時系列表の表示モードは ProductionSession 側で親制御する。全府県一覧へ切り替える前に未ロード府県を取得し、滋賀県など初期府県だけの一覧を表示しない。
- ソースコードを改修した場合は、同じ作業内で関連する Markdown を確認し、実装内容・運用手順・既知課題と矛盾しないように更新する。
- staging/main では server/tests、test_*.py、.pytest_cache、__pycache__、*.pyc をリリース payload に含めない。
- 昇格確認は python scripts/check_production_promotion.py を使う。

作業を始める前に、未コミット差分があれば内容を確認し、ユーザーの変更を勝手に戻さないでください。
```

具体的な作業内容が決まっている場合は、上のプロンプトの末尾に今回のタスクを1行追加してください。
