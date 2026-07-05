# キャッシュシステム

本番計算結果は gzip JSON として保存し、同一条件の再計算を避けます。キャッシュは本番APIのレスポンス高速化、同時アクセス時の重複計算防止、セッション復元に使います。

## 実装箇所

- `server/src/services/cache_service.py`
- `server/src/services/session_service.py`
- `server/src/api/controllers/main_controller.py`

## キャッシュキー

現在のキーは以下の条件から生成します。

- SWI初期時刻
- ガイダンス初期時刻
- ガイダンス種別: `msm` / `gsm`
- 危険度ルール: `legacy` / `lead_time_to_level4`
- 地方: `kinki` / `chugoku` / `shikoku`

例:

```text
swi_20260605000000_guid_msm_20260605000000_risk_legacy_region_kinki
```

地方別に対象府県を絞って計算するため、地方もキーに含めます。

## 保存形式

```text
cache/
  {cache_key}.json.gz
  {cache_key}.summary.json
  {cache_key}.summary.lock.json
  {cache_key}.calculating.json
  session_refs/
    {session_id}.json
```

`*.json.gz` は計算結果本体です。保存時は一時ファイルに書き出してから rename し、中途半端なgzipを読まないようにします。

`*.summary.json` は初期レスポンス用の軽量サマリーです。府県一覧、府県名、利用可能FT、初期時刻、ガイダンス種別、危険度ルールを保持します。キャッシュヒット時の初期APIはこのサマリーだけを読み、gzip全体の展開を避けます。既存gzipにサマリーがない場合は、`*.summary.lock.json` で作成を1件に絞り、同時リクエストは短時間待機または `202 Accepted` で再確認します。

`*.calculating.json` は計算中ロックです。古いロックはタイムアウト判定で破棄します。完成済み `.json.gz` があり保存中tmpが残っていない場合は、gzip保存後に残った計算ロックとして回収します。

`session_refs` はセッションIDからキャッシュキーへ戻す参照ファイルです。プロセス内メモリにセッションがない場合でも、キャッシュが残っていればベースセッションを復元できます。キャッシュヒット時に作成するベースセッションは、最初はサマリーとキャッシュキーだけを保持し、府県データなど完全データが必要になった時点で gzip キャッシュから materialize します。

## 本番リクエストの流れ

1. `POST /production-soil-rainfall-index-with-urls` を受け取る
2. 入力時刻、ガイダンス種別、危険度ルール、地方を検証する
3. キャッシュキーを生成する
4. キャッシュサマリーが存在すればGRIB2取得前に軽量セッションレスポンスを返す
5. 同一条件が計算中なら短時間だけ待ち、未完了の場合は `202 Accepted` と `Retry-After` を返す
6. クライアントは `202` の間、2秒間隔で同じ条件を再確認する
7. キャッシュキー単位のロックとサーバー全体の計算スロットを取得できたリクエストだけが計算する
8. 計算結果をgzipキャッシュへ保存し、軽量サマリーも保存する
9. ロックを解放し、ベースセッションを作成して軽量レスポンスを返す

重い初期計算はサーバー全体で1件に直列化します。異なる地方・時刻のリクエストが集中した場合も、複数計算によるCPU・メモリ競合を避け、後続リクエストはポーリングで順番を待ちます。

計算ロックにはPID、ホスト名、所有トークンを保存します。同じホスト上で所有プロセスが終了している場合は孤立ロックとして回収します。所有トークンが異なるロックは削除せず、古い処理が新しい所有者のロックを誤って解放することを防ぎます。

ロック解放時は削除成否を呼び出し元へ返し、失敗時は本番処理ログに残します。同一プロセスが所有するロックは、CacheServiceインスタンス再生成などでメモリ上の所有トークンが失われていても削除を許可します。これにより、gzipキャッシュ保存後に `.calculating.json` だけが残り、後続リクエストが `202 Accepted` を返し続ける状態を避けます。

キャッシュ本体の gzip 展開結果はプロセス内メモリに短期保持します。同じプロセス内で同じ `cache_key` にアクセスが集中した場合、最初の1スレッドだけが gzip 展開と JSON parse を行い、後続スレッドは同じ結果を共有します。保持数は環境変数 `CACHE_MEMORY_MAX_RESULTS` で制御できます。未設定時は2件です。`0` を指定するとプロセス内メモリキャッシュを無効化します。

## 管理API

キャッシュ管理APIは開発・検証用です。`SOIL_RAINFALL_ROUTE_PROFILE=production` では公開しません。

- `GET /cache/list`
- `GET /cache/stats`
- `GET /cache/<cache_key>`
- `GET /cache/<cache_key>/exists`
- `DELETE /cache/<cache_key>`
- `POST /cache/cleanup`

## 設定

`server/config/app_config.yaml` の `cache` セクションで設定します。

```yaml
cache:
  directory: "cache"
  ttl_days: 7
  compression_level: 6
  auto_cleanup: true
  cleanup_interval_hours: 24
```

現行コードの保存処理は圧縮レベル6を使用します。
