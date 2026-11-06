# 実機処理時間の記録と共有

解析画面を開いてから雨量を調整・再計算するまで、サーバーAPIごとの全体時間と主な処理段階を1ファイルに記録します。リクエストIDで各リクエストのイベントをまとめられるJSON Lines形式です。

## 出力先

既定の出力先は、`CACHE_DIR`配下の次のファイルです。mod_wsgiの既定設定では`wsgi.py`が`CACHE_DIR=/var/cache/myapp/dosya`を設定します。

```text
/var/cache/myapp/dosya/performance_timings.jsonl
```

`CACHE_DIR`が未設定の場合は開発用に`server/cache/performance_timings.jsonl`へ出力します。SELinuxを有効にした環境ではアプリ配置ディレクトリが読み取り専用の場合があるため、書き込み可能なキャッシュ領域に保存します。

別の場所を使う場合は、絶対パスを環境変数 `SOIL_RAINFALL_TIMING_FILE` で指定できます。指定したファイルの親ディレクトリとファイルに、Flask/mod_wsgiの実行ユーザーが書き込める必要があります。

```bash
export SOIL_RAINFALL_TIMING_FILE=/var/cache/myapp/dosya/performance_timings.jsonl
```

## 記録されるAPIとイベント

対象APIは次の4つです。

- `POST /production-soil-rainfall-index-with-urls`（初回データ取得）
- `GET /session/<session_id>/rainfall-data`（雨量調整画面を開く）
- `POST /session/<session_id>/recalculate`
- `POST /session/<session_id>/rainfall-preview`

対象リクエストごとに開始・処理段階・完了のイベントを追記します。データ取得ではキャッシュ照会、GRIB2ダウンロード・解析、地域構築、メッシュ計算、危険度集約、キャッシュ保存、セッション作成を記録します。雨量調整画面の読込ではセッション取得、3時間・24時間雨量集約、府県・一次細分の集約を記録します。プレビューと再計算では従来の調整変換・入力収集・NumPy計算に加え、フォークマージの索引作成・deepcopy・メッシュ更新・再集約を記録します。完了イベントにはHTTPステータス、総時間、リクエスト・レスポンスサイズを記録します。

記録に含める情報は、リクエストID、ルート、処理段階、所要時間、メッシュ数などの件数です。リクエスト本文・入力値・雨量データ・生のセッションIDは記録しません。同一セッションのAPIを関連付けるため、セッションIDをSHA-256で短縮した`session_ref`を記録します。初回データ取得の`base_session_creation`段階イベントに含まれる`metadata.session_ref`と、後続リクエストの`request_started.session_ref`を使って一連の操作をまとめられます。行の順番は並行リクエストで前後することがあるため、リクエストID・時刻・session_refを使ってください。

リクエスト開始後にプロセスが強制終了した場合は完了イベントが残らないことがあります。その場合も開始イベントと、終了前までに記録された段階イベントは残ります。

雨量の手入力はブラウザー内で行われ、入力中にサーバーAPIを呼びません。そのため入力操作そのものの時間は工程時間としては記録せず、編集後に実行したプレビュー・再計算リクエストを記録します。同一`session_ref`の前リクエスト完了時刻と次リクエスト開始時刻の差から、入力などの画面操作にかかった概算時間を見られます。この差にはブラウザー・ネットワークの待ち時間も含まれます。

Apacheなどの前段が先に504を返し、Flask側の処理がその後も続いた場合、完了イベントのHTTPステータスはFlaskが返した値（504ではなく200など）になります。その場合は、実機で504が表示された時刻と、該当リクエストの総処理時間・開始時刻を照合してください。

## 実機での採取手順

1. 必要なら、実機の出力ファイルを退避してから削除し、今回の計測だけにします。
2. 雨量調整画面でプレビューまたは再計算を実行します。成功時だけでなく、504が発生した場合もファイルを採取してください。
3. サーバーから `performance_timings.jsonl` だけをコピーし、このチャットに添付してください。

mod_wsgi既定パスを使う実機では、たとえば次のように採取します。

```bash
sudo cp /var/cache/myapp/dosya/performance_timings.jsonl /tmp/performance_timings.jsonl
```

環境変数で別の出力先を指定している場合は、そのファイルをコピーします。計測を始める前にファイルを退避または削除すれば、以前の実行と混ざらずに解析できます。
