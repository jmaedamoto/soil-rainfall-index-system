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
  {cache_key}.calculating.json
  session_refs/
    {session_id}.json
```

`*.json.gz` は計算結果本体です。保存時は一時ファイルに書き出してから rename し、中途半端なgzipを読まないようにします。

`*.calculating.json` は計算中ロックです。古いロックはタイムアウト判定で破棄します。

`session_refs` はセッションIDからキャッシュキーへ戻す参照ファイルです。プロセス内メモリにセッションがない場合でも、キャッシュが残っていればベースセッションを復元できます。

## 本番リクエストの流れ

1. `POST /production-soil-rainfall-index-with-urls` を受け取る
2. 入力時刻、ガイダンス種別、危険度ルール、地方を検証する
3. キャッシュキーを生成する
4. キャッシュが存在すればGRIB2取得前にセッションレスポンスを返す
5. キャッシュ保存中または計算中であれば最大600秒待つ
6. ロックを取得できたリクエストだけが計算する
7. 計算結果をgzipキャッシュへ保存する
8. ロックを解放し、ベースセッションを作成して軽量レスポンスを返す

フロントエンドは504 Gateway Timeoutを受けた場合、1秒後に同じリクエストを1回再試行します。サーバー側で計算や保存が継続していれば、再試行はキャッシュ待機またはキャッシュヒット経路に入ります。

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
