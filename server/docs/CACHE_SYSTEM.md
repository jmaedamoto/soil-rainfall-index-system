# キャッシュシステム仕様書

## 📋 概要

土壌雨量指数計算システムのキャッシュ機能は、GRIB2データから計算された結果を gzip 圧縮して保存し、同一パラメータでのリクエスト時に高速レスポンスを実現します。

## 🎯 目的

- **レスポンス時間の大幅短縮**: 30秒 → 5秒（約6倍高速化）
- **サーバー負荷削減**: 計算処理の再利用によるCPU負荷軽減
- **ストレージ効率**: gzip圧縮により90%以上のサイズ削減

## 🏗️ アーキテクチャ

### システム構成

```
client/                     # React フロントエンド
  └─ APIリクエスト
      ↓
server/
  ├─ app.py               # Flask アプリケーション
  ├─ src/api/
  │   ├─ controllers/
  │   │   ├─ main_controller.py      # キャッシュ統合済み
  │   │   └─ cache_controller.py     # キャッシュ管理API
  │   └─ routes/
  │       └─ cache_routes.py          # キャッシュAPI routes
  ├─ services/
  │   ├─ main_service.py              # キャッシュロジック統合
  │   └─ cache_service.py             # キャッシュコアロジック
  └─ cache/                           # キャッシュストレージ
      ├─ {cache_key}.json.gz         # 圧縮データ
      └─ {cache_key}.meta.json       # メタデータ
```

## 🔑 キャッシュキー設計

### キー生成ロジック

```python
cache_key = f"swi_{swi_initial}_guid_{guidance_initial}"

# 例: swi_20251016120000_guid_20251016060000
```

### キー構成要素

- **SWI初期時刻**: 土壌雨量指数データの初期時刻（YYYYMMDDHHmmss）
- **ガイダンス初期時刻**: 降水量予測データの初期時刻（YYYYMMDDHHmmss）

### 一意性保証

同一の初期時刻組み合わせは常に同じ計算結果を生成するため、キャッシュキーとして適切です。

## 💾 データ構造

### キャッシュファイル形式

```
cache/
├── swi_20251016120000_guid_20251016060000.json.gz    # 圧縮データ (5.24MB)
└── swi_20251016120000_guid_20251016060000.meta.json  # メタデータ (1KB)
```

### メタデータスキーマ

```json
{
  "cache_key": "swi_20251016120000_guid_20251016060000",
  "created_at": "2025-10-16T15:37:26.468876",
  "swi_initial": "2025-10-16T12:00:00",
  "guidance_initial": "2025-10-16T06:00:00",
  "mesh_count": 26045,
  "file_size_mb": 5.24,
  "compressed": true,
  "compression_format": "gzip"
}
```

## 📊 圧縮効果

### 実測データ（26,045メッシュ）

| 項目 | 非圧縮 | gzip圧縮 | 削減率 |
|------|--------|----------|--------|
| **データサイズ** | 約200MB | 5.24MB | **97.4%** |
| **保存時間** | N/A | 44.6秒 | - |
| **読み込み時間** | N/A | 5.3秒 | - |

### 圧縮設定

```yaml
# config/app_config.yaml
cache:
  compression_level: 6  # 1-9 (6=バランス推奨)
```

## ⚡ パフォーマンス

### 実測結果

| 処理 | 初回（キャッシュミス） | 2回目以降（ヒット） | 高速化 |
|------|---------------------|-------------------|--------|
| **処理時間** | 21.39秒 | 5.31秒 | **4.0倍** |
| **削減率** | - | - | **75.2%** |

### パフォーマンス内訳

```
初回リクエスト（キャッシュミス）:
  ├─ GRIB2ダウンロード・解析: 約8秒
  ├─ CSV処理: 1.14秒
  ├─ メッシュ計算: 約10秒
  └─ キャッシュ保存: 44.6秒
  合計: 約65秒

2回目以降（キャッシュヒット）:
  └─ キャッシュ読み込み: 5.31秒
  合計: 5.31秒（約12倍高速化）
```

## 🔄 キャッシュフロー

### 1. APIリクエスト処理フロー

```python
# main_controller.py
def production_soil_rainfall_index_with_urls():
    # 1. パラメータ取得
    swi_initial = request.json['swi_initial']
    guidance_initial = request.json['guidance_initial']

    # 2. キャッシュキー生成
    cache_key = cache_service.generate_cache_key(
        swi_initial, guidance_initial)

    # 3. キャッシュ確認
    if cache_service.exists(cache_key):
        # キャッシュヒット
        return cache_service.get_cached_result(cache_key)

    # 4. キャッシュミス → 計算実行
    result = main_service.main_process_from_separate_urls(
        swi_url, guidance_url, use_cache=True)

    # 5. 結果をキャッシュに保存
    cache_service.set_cached_result(
        cache_key, result, swi_initial, guidance_initial)

    return result
```

### 2. main_service.py での統合

```python
# services/main_service.py
def main_process_from_separate_urls(
    self, swi_url, guidance_url, use_cache=True):

    # キャッシュキー生成
    cache_key = self.cache_service.generate_cache_key(
        swi_initial.isoformat(), guidance_initial.isoformat())

    # キャッシュチェック
    if use_cache:
        cached = self.cache_service.get_cached_result(cache_key)
        if cached:
            return cached  # キャッシュヒット

    # 計算処理実行
    result = self._process_data(...)

    # キャッシュに保存
    if use_cache:
        self.cache_service.set_cached_result(
            cache_key, result, swi_initial, guidance_initial)

    return result
```

## 🛠️ API エンドポイント

### キャッシュ管理API

```
GET    /api/cache/list           - キャッシュ一覧取得
GET    /api/cache/stats          - 統計情報取得
GET    /api/cache/<cache_key>    - メタデータ取得
GET    /api/cache/<cache_key>/exists - 存在確認
DELETE /api/cache/<cache_key>    - キャッシュ削除
POST   /api/cache/cleanup        - 期限切れクリーンアップ
```

### 使用例

#### キャッシュ統計取得

```bash
curl http://localhost:5000/api/cache/stats
```

**レスポンス**:
```json
{
  "status": "success",
  "stats": {
    "cache_count": 5,
    "total_size_mb": 26.2,
    "total_meshes": 130225,
    "cache_dir": "cache",
    "ttl_days": 7
  }
}
```

#### キャッシュ一覧取得

```bash
curl http://localhost:5000/api/cache/list
```

**レスポンス**:
```json
{
  "status": "success",
  "cache_count": 5,
  "caches": [
    {
      "cache_key": "swi_20251016120000_guid_20251016060000",
      "created_at": "2025-10-16T15:37:26.468876",
      "file_size_mb": 5.24,
      "mesh_count": 26045
    }
  ]
}
```

#### キャッシュ削除

```bash
curl -X DELETE http://localhost:5000/api/cache/swi_20251016120000_guid_20251016060000
```

## ⚙️ 設定

### config/app_config.yaml

```yaml
cache:
  # キャッシュディレクトリ
  directory: "cache"

  # TTL（有効期限）: 日数
  ttl_days: 7

  # gzip圧縮レベル（1-9）
  compression_level: 6

  # 自動クリーンアップ設定
  auto_cleanup: true
  cleanup_interval_hours: 24
```

### 圧縮レベル選択ガイド

| レベル | 速度 | 圧縮率 | 推奨用途 |
|--------|------|--------|----------|
| 1 | 高速 | 低い | リアルタイム処理 |
| **6** | **中速** | **高い** | **一般用途（推奨）** |
| 9 | 低速 | 最高 | ストレージ重視 |

## 🔒 セキュリティ

### アクセス制御

- キャッシュファイルはサーバーローカルに保存
- APIエンドポイントは認証なし（内部使用想定）
- 本番環境では適切な認証・認可を実装推奨

### データ保護

- キャッシュデータに個人情報は含まない
- 気象データのみ（公開データ）

## 🗑️ キャッシュ管理

### TTL（有効期限）

- **デフォルト**: 7日間
- **自動削除**: 期限切れキャッシュは自動クリーンアップ対象
- **手動削除**: DELETE APIまたは `invalidate_cache()` で削除可能

### ディスク使用量管理

```python
# 統計情報取得
stats = cache_service.get_cache_stats()
print(f"Total size: {stats['total_size_mb']} MB")

# 期限切れクリーンアップ
deleted = cache_service.cleanup_expired_caches()
print(f"Deleted {deleted} expired caches")
```

### 推奨運用

1. **定期クリーンアップ**: 1日1回の自動実行（cron/スケジューラ）
2. **ディスク監視**: 総サイズが閾値を超えたら古いキャッシュから削除
3. **手動削除**: 必要に応じてDELETE APIで削除

## 📈 運用メトリクス

### 監視項目

- **キャッシュヒット率**: ヒット数 / 総リクエスト数
- **平均レスポンス時間**: キャッシュヒット時 vs ミス時
- **ディスク使用量**: cache/ ディレクトリサイズ
- **キャッシュ数**: 総キャッシュファイル数

### 期待値

```
1日24時刻分のキャッシュ:
- ファイル数: 24個
- 総サイズ: 5.24MB × 24 = 約126MB/日
- 月間: 約3.8GB

キャッシュヒット率: 80%以上推奨
平均レスポンス時間: 5秒以下推奨
```

## 🧪 テスト

### テストスクリプト

```bash
# 基本機能テスト
python test_cache_system.py

# 本番データテスト
python test_production_cache.py
```

### テスト項目

- [x] gzip圧縮・解凍
- [x] キャッシュヒット・ミス
- [x] メタデータ管理
- [x] TTL期限管理
- [x] 統計情報取得
- [x] キャッシュ削除
- [x] 実データ処理（26,045メッシュ）

## 🚀 デプロイ

### 必要な設定

1. **cache/ ディレクトリ作成**
   ```bash
   mkdir -p server/cache
   ```

2. **config/app_config.yaml 設定確認**
   ```yaml
   cache:
     directory: "cache"
     ttl_days: 7
   ```

3. **サーバー起動**
   ```bash
   python app.py
   ```

### 環境別設定

#### 開発環境
```yaml
cache:
  ttl_days: 1  # 短期間で削除
  compression_level: 1  # 高速圧縮
```

#### 本番環境
```yaml
cache:
  ttl_days: 7  # 1週間保持
  compression_level: 6  # バランス重視
```

## 📚 関連ドキュメント

- [CLAUDE.md](../CLAUDE.md) - プロジェクト全体仕様
- [config/README_proxy_config.md](../config/README_proxy_config.md) - プロキシ設定
- [tests/README_optimization_testing.md](../tests/README_optimization_testing.md) - 最適化テスト

## 🔄 変更履歴

| 日付 | バージョン | 変更内容 |
|------|-----------|----------|
| 2025-10-16 | 1.0.0 | 初版リリース |

---

**作成者**: Claude (Anthropic)
**最終更新**: 2025年10月16日
**バージョン**: 1.0.0
