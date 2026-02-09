"""
キャッシュシステムテストスクリプト

テスト内容:
1. キャッシュサービスの基本動作確認
2. gzip圧縮・解凍の確認
3. キャッシュヒット・ミスの確認
4. メタデータ管理の確認
"""

import json
import time
from services.cache_service import CacheService

def test_cache_service():
    """キャッシュサービステスト"""
    print("=" * 60)
    print("キャッシュシステムテスト開始")
    print("=" * 60)

    # キャッシュサービス初期化
    cache_service = CacheService(cache_dir="cache", default_ttl_days=7)

    # テストデータ作成（大規模JSON）
    test_data = {
        "status": "success",
        "prefectures": {
            f"pref_{i}": {
                "name": f"都道府県{i}",
                "areas": [
                    {
                        "name": f"エリア{j}",
                        "meshes": [
                            {
                                "code": f"{i}{j}{k}",
                                "lat": 35.0 + i * 0.1,
                                "lon": 135.0 + j * 0.1,
                                "swi_timeline": [
                                    {"ft": ft, "value": 100.0 + ft}
                                    for ft in range(0, 24, 3)
                                ]
                            }
                            for k in range(100)  # 100メッシュ
                        ]
                    }
                    for j in range(10)  # 10エリア
                ]
            }
            for i in range(5)  # 5府県
        }
    }

    print(f"\nテストデータサイズ: {len(json.dumps(test_data))} bytes")

    # キャッシュキー生成
    swi_initial = "2025-10-16T12:00:00"
    guidance_initial = "2025-10-16T06:00:00"
    cache_key = cache_service.generate_cache_key(
        swi_initial, guidance_initial)

    print(f"キャッシュキー: {cache_key}")

    # テスト1: キャッシュ保存
    print("\n[テスト1] キャッシュ保存")
    start_time = time.time()
    cache_service.set_cached_result(
        cache_key, test_data, swi_initial, guidance_initial)
    save_time = time.time() - start_time
    print(f"保存時間: {save_time:.3f}秒")

    # テスト2: キャッシュ取得（ヒット）
    print("\n[テスト2] キャッシュ取得（ヒット）")
    start_time = time.time()
    cached_data = cache_service.get_cached_result(cache_key)
    load_time = time.time() - start_time

    if cached_data:
        print(f"[OK] キャッシュヒット成功")
        print(f"取得時間: {load_time:.3f}秒")
        print(f"データ一致: {cached_data == test_data}")
    else:
        print("[NG] キャッシュ取得失敗")

    # テスト3: メタデータ確認
    print("\n[テスト3] メタデータ確認")
    metadata = cache_service.get_metadata(cache_key)
    if metadata:
        print(f"[OK] メタデータ取得成功:")
        print(f"  - cache_key: {metadata['cache_key']}")
        print(f"  - created_at: {metadata['created_at']}")
        print(f"  - mesh_count: {metadata['mesh_count']}")
        print(f"  - file_size_mb: {metadata['file_size_mb']} MB")
        print(f"  - compressed: {metadata['compressed']}")
    else:
        print("[NG] メタデータ取得失敗")

    # テスト4: キャッシュ統計
    print("\n[テスト4] キャッシュ統計")
    stats = cache_service.get_cache_stats()
    print(f"[OK] 統計情報:")
    print(f"  - cache_count: {stats['cache_count']}")
    print(f"  - total_size_mb: {stats['total_size_mb']} MB")
    print(f"  - total_meshes: {stats['total_meshes']}")
    print(f"  - cache_dir: {stats['cache_dir']}")
    print(f"  - ttl_days: {stats['ttl_days']}")

    # テスト5: キャッシュ一覧
    print("\n[テスト5] キャッシュ一覧")
    caches = cache_service.list_caches()
    print(f"[OK] キャッシュ数: {len(caches)}")
    for cache in caches:
        print(f"  - {cache['cache_key']}: "
              f"{cache['file_size_mb']}MB, "
              f"{cache['mesh_count']} meshes")

    # テスト6: 圧縮効果確認
    print("\n[テスト6] 圧縮効果確認")
    uncompressed_size = len(json.dumps(test_data))
    compressed_size = metadata['file_size_mb'] * 1024 * 1024
    compression_ratio = (1 - compressed_size / uncompressed_size) * 100

    print(f"非圧縮サイズ: {uncompressed_size / (1024*1024):.2f} MB")
    print(f"圧縮後サイズ: {metadata['file_size_mb']:.2f} MB")
    print(f"圧縮率: {compression_ratio:.1f}%")

    # テスト7: キャッシュ削除
    print("\n[テスト7] キャッシュ削除")
    cache_service.invalidate_cache(cache_key)
    exists = cache_service.exists(cache_key)
    if not exists:
        print(f"[OK] キャッシュ削除成功")
    else:
        print(f"[NG] キャッシュ削除失敗")

    print("\n" + "=" * 60)
    print("テスト完了")
    print("=" * 60)


if __name__ == "__main__":
    test_cache_service()
