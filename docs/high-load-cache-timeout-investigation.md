# 高負荷時キャッシュタイムアウト調査メモ

## 現在の状態

本メモの調査対象だった stale tmp 起因の10分タイムアウトは、以下のコミットで対処済み。

- `6a85156 Prevent calculation timeouts under concurrent load`
- `99692bb Handle stale cache temp files`

主な対応内容:

- 同一条件の計算中は短時間だけ待機し、未完了の場合は `202 Accepted` と `Retry-After` を返す。
- クライアントは `202` または計算リクエストの gateway timeout 後も、最大10分まで同じ条件を再確認する。
- 別条件の重い計算は `calculation-slot` で直列化し、高負荷時の同時実行数を抑える。
- 完成 `.json.gz` がなく、計算ロックもない古い保存用 `.tmp` は stale と判定して削除し、再計算へ進める。
- キャッシュ保存は一時ファイル経由の atomic rename とし、保存完了後に計算ロックを解放する。

検証:

- `PYTHONDONTWRITEBYTECODE=1 python scripts/check_production_promotion.py` は成功。

残確認:

- 実環境の高負荷再試験で `202 Accepted` / `Retry-After` とクライアント再確認が期待通り動くこと。
- 実環境 Apache/mod_wsgi 設定がリポジトリ内の `server/deploy/apache-soil-rainfall.conf`、`server/deploy/DEPLOY_GUIDE.md` と一致していること。
- 未来時刻または未提供データを選択した場合の扱いを、必要に応じてフロントまたはサーバーで明示化すること。

## 背景

高負荷試験で複数ユーザーが同時アクセスしたところ、フロントエンドで以下のエラーが発生した。

```text
エラー：計算が10分以内に完了しませんでした。しばらくして再実行してください。
```

調査元ログ:

- `docs/error_log.txt`

## 直接原因

対象キャッシュキー:

```text
swi_20260617120000_guid_msm_20260617120000_risk_legacy_region_kinki
```

キャッシュフォルダに以下の一時ファイルだけが残っていた。

```text
swi_20260617120000_guid_msm_20260617120000_risk_legacy_region_kinki.json.gz.sq4ylso4.tmp
```

確認事項:

- `.tmp` のタイムスタンプは 09:59 で、同時アクセス実施時刻と一致する。
- `.tmp` のサイズは `6,315,302 bytes`。
- 完成版 `.json.gz` は作成されていなかった。
- `.tmp` 削除後に再取得すると `.json.gz` が作成された。
- 再作成された完成 gzip のサイズは `11,100,688 bytes`。

このため、残っていた `.tmp` は保存途中で中断された不完全な gzip と評価できる。

## 当時のコード上の問題

`server/src/services/cache_service.py` の `is_cache_write_in_progress()` は、保存中一時ファイルの存在だけを見る。

```text
*.json.gz.*.tmp
```

そのため、完成 `.json.gz` がなく、計算ロックもない状態でも、古い `.tmp` が残っているだけで「キャッシュ保存中」と判断する。

ログ上の典型状態:

```text
calculating=False, tmp=True, materializing=False
```

この状態で `server/src/api/controllers/main_controller.py` は同一条件に `202 calculating` を返し続ける。実際には保存処理はもう動いていないため、キャッシュは永遠に完成しない。

フロントエンドは `client/src/services/api.ts` で最大10分ポーリングし、`200 success` を得られなければ以下のエラーを出す。

```text
計算が10分以内に完了しませんでした。しばらくして再実行してください。
```

つまり、このエラーはサーバーが明示的に返した計算失敗ではなく、stale tmp によって `202` が続いた結果のクライアント側タイムアウトである。

現在は `cleanup_stale_cache_write_temps()` により、完成 `.json.gz` がなく、計算ロックもない古い `.tmp` を削除して再計算できる。

## ログ上の関連所見

`docs/error_log.txt` には以下が多数出ている。

```text
Truncated or oversized response headers received from daemon process 'soilrsi'
Timeout when reading response headers from daemon process 'soilrsi'
Apache/mod_wsgi request data read error: Partial results are valid but processing is incomplete.
```

このため、同時アクセス中に WSGI プロセス中断、Apache/mod_wsgi 側タイムアウト、接続断、プロセス再起動などが発生し、キャッシュ保存が途中で止まった可能性が高い。

また、ログ上の daemon 名は `soilrsi` で、複数 pid が見える。一方、リポジトリ内の `server/deploy/apache-soil-rainfall.conf` は `soilrsi-staging processes=1 threads=5` である。実環境の Apache 設定とリポジトリ内設定が一致していない可能性がある。

## 条件混在

「同一条件」とされていたが、ログ上は少なくとも以下のキャッシュキーが混在していた。

```text
swi_20260617120000_guid_msm_20260617120000_risk_lead_time_to_level4_region_kinki
swi_20260617120000_guid_msm_20260617120000_risk_legacy_region_kinki
swi_20260618120000_guid_msm_20260618120000_risk_lead_time_to_level4_region_kinki
swi_20260617210000_guid_msm_20260617210000_risk_legacy_region_kinki
```

特に `2026-06-18 12:00` の SWI URL は 404 になっていた。

```text
Z__C_RJTD_20260618120000_SRF_GPV_Ggis1km_Psw_Aper10min_ANAL_grib2.bin
404 Client Error: Not Found
```

試験時刻が 2026-06-18 10時台 UTC だったため、未来時刻または未提供データを選択した可能性がある。これは stale tmp の直接原因ではないが、計算スロットを占有し、高負荷時の詰まりを悪化させる。

## gzip 作成後もフロントが取得中になる件

`.tmp` 削除後、再取得で `.json.gz` は作成されたが、フロント側では「データ取得中」が続く現象が確認された。

これは `gzip 作成完了 = フロント完了` ではないため、別途切り分けが必要。

フロントの `loading` は `client/src/features/production-session/hooks/useProductionSession.ts` の `loadData()` で管理される。`loading=false` になるのは、初期計算 API だけでなく以下の後続処理も完了した後である。

1. 初期計算 API 成功
2. `setSessionInfo`
3. `setSessionId`
4. 最初の府県データ取得: `/session/<session_id>/prefecture/<prefecture_code>`
5. 初期時刻の全メッシュリスク取得: `/session/<session_id>/risk-at-time`

したがって、gzip ができていても以下のどこかで待てば画面は「データ取得中」のままになる。

- gzip 保存後のセッション作成
- 軽量レスポンス返却
- 初回府県データ取得
- 初期時刻 risk-at-time 取得
- Apache/mod_wsgi の応答待ちタイムアウト

現在は初期計算 API が計算中に長時間リクエストを保持し続けず、短時間待機後に `202 Accepted` を返す。gzip 作成後の取得中表示が続く場合は、セッション作成後の軽量レスポンス返却、府県データ取得、`risk-at-time` のどこで止まっているかをログで確認する。

## 再試験時に確認すべきログ

再取得時の `.json.gz` 作成直後に、以下のログがどこまで出ているか確認する。

```text
キャッシュ保存完了
キャッシュ保存完了後に計算ロック解放
軽量セッションレスポンス返却
Base session created
/session/<session_id>/prefecture
/session/<session_id>/risk-at-time
Timeout when reading response headers
```

加えて、対策後は以下を確認する。

```text
古いキャッシュ保存tmpを削除
キャッシュ作成中のため再試行応答
計算ロック取得失敗後に再試行応答
別条件の計算が実行中のため再試行応答
```

判断基準:

- `キャッシュ保存完了` はあるが `軽量セッションレスポンス返却` がない場合、サーバー側で gzip 作成後からレスポンス前までに詰まっている。
- `軽量セッションレスポンス返却` はあるが画面が取得中の場合、後続の府県データ取得または risk-at-time で詰まっている。
- 同時刻に `Timeout when reading response headers` が出る場合、Apache/mod_wsgi 側の応答待ちタイムアウトが濃厚。

## 評価

主要な問題は2系統。

1. stale tmp 問題
   - キャッシュ保存中断で `.tmp` が残る。
   - 以後、永続的に「保存中」扱いされる。
   - これが10分エラーの直接原因。
   - 対応済み: 古い `.tmp` を stale と判定して削除する。

2. 高負荷時の返却遅延・WSGI タイムアウト問題
   - gzip 完成後も、セッション作成や後続 API、Apache/mod_wsgi 応答待ちで詰まる可能性がある。
   - 対応済み: 計算中は短時間待機後に `202 Accepted` を返し、クライアント側で再確認する。
   - 残確認: 実環境 Apache/mod_wsgi 設定と高負荷再試験。

## 改修済み項目

- 古い `.tmp` を stale と判定して削除する。
- `.tmp` だけで完成 `.json.gz` がなく、計算ロックもない場合は再計算へ進ませる。
- キャッシュ保存完了後、レスポンス前のログを強化する。
- 同一条件の後続リクエストは短時間だけ待ち、未完了なら `202 Accepted` で返す。
- 別条件の計算は `calculation-slot` で直列化する。
- クライアントは `202 Accepted` と一部 timeout を受けて同じ条件を再確認する。
- Apache/mod_wsgi の timeout 設定方針を `server/deploy/DEPLOY_GUIDE.md` に反映する。

## 残課題候補

- 実環境 Apache/mod_wsgi 設定を確認し、リポジトリ内設定と一致させる。
- 未来または未提供の SWI 時刻をフロントまたはサーバーで選べないようにする、または明示エラーにする。
- 実環境高負荷再試験で、stale tmp 削除、`202 Accepted`、クライアント再確認、後続セッション API の挙動を確認する。
