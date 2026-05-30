プロジェクトを再開します。

まず `docs/DAILY_START_CONTEXT.md` を読んでください。現在は 504 対策としての地方別ページ分割、動作確認、`staging` 反映確認まで完了し、次の機能追加に入る前の区切り段階です。

前提:
- 504 問題は、開発側で直接対処できない外部要因として扱う
- 対応方針は「近畿・中国・四国の3ページに分割し、各 API の戻り値を削減する」
- 分割実装、動作確認、`staging` 反映確認は完了済み
- 中国・四国8県の CSV は保持する
- 14府県は地方別に扱う前提で、六府県運用へ戻す作業は不要
- 未追跡の調査・メモファイルは本体変更と分けて扱う
- `server/src/services/main_service.py` に別件のローカル未整理変更が残っている可能性があるので、勝手に混ぜない

まず確認してほしいこと:
1. `git status --short`
2. `git log --oneline -5`
3. 現在ブランチ
4. 直近の作業メモと差分

現在の目的:
1. 504 調査へ戻らず、地方別ページ分割は完了済みとして扱う
2. 次の機能追加に入る前に、作業ツリーの未整理変更を把握する
3. 新しい作業を始める場合は、既存のローカル変更と混ぜない

地方分割に関係する主なファイル:
- `client/src/App.tsx`
- `client/src/features/production-session/regions.ts`
- `client/src/features/production-session/hooks/useProductionSession.ts`
- `client/src/pages/ProductionSession.tsx`
- `client/src/services/api.ts`
- `client/src/types/session.ts`
- `server/src/api/controllers/main_controller.py`
- `server/src/models/data_models.py`
- `server/src/services/cache_service.py`
- `server/src/services/data_service.py`

進め方:
- まず現状確認
- 既存の未整理変更を把握
- 次の機能追加の内容を確認
- 必要な変更だけを小さく入れる
- 最後に変更内容、検証結果、残課題を短く要約

回答は簡潔にしてください。
