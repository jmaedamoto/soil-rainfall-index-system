# 実機処理時間の記録と共有

雨量調整のプレビューと再計算APIについて、リクエスト全体と主な処理段階の時間を1ファイルに記録します。リクエストIDでイベントをまとめられるJSON Lines形式です。

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

対象は次のセッションAPIです。

- `POST /session/<session_id>/recalculate`
- `POST /session/<session_id>/rainfall-preview`

対象リクエストごとに開始・処理段階・完了のイベントを追記します。主な段階は雨量調整変換、再計算入力データ収集、NumPy再計算、フォーク作成とmaterialize、プレビュー応答組み立てです。完了イベントにはHTTPステータス、総時間、レスポンスサイズを記録します。

記録に含める情報は、リクエストID、ルート、処理段階、所要時間、メッシュ数などの件数です。セッションID、入力値、雨量データ、リクエスト本文は記録しません。行の順番は並行リクエストで前後することがあります。同じリクエストIDの行をまとめてください。

リクエスト開始後にプロセスが強制終了した場合は完了イベントが残らないことがあります。その場合も開始イベントと、終了前までに記録された段階イベントは残ります。

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
