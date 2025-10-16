"""
本番APIキャッシュテストスクリプト

テスト内容:
1. 初回リクエスト（キャッシュミス）の時間測定
2. 2回目リクエスト（キャッシュヒット）の時間測定
3. キャッシュファイルサイズ確認
4. 圧縮効果の確認
"""

import time
from datetime import datetime
from services.main_service import MainService
from services.cache_service import get_cache_service

def test_production_cache():
    """本番データでキャッシュテスト"""
    print("=" * 80)
    print("本番APIキャッシュテスト")
    print("=" * 80)

    # サービス初期化
    main_service = MainService(data_dir="data")
    cache_service = get_cache_service()

    # テストデータ: ローカルbinファイル使用
    swi_file = "data/Z__C_RJTD_20250101000000_SRF_GPV_Ggis1km_Psw_Aper10min_ANAL_grib2.bin"
    guidance_file = "data/guid_msm_grib2_20250101000000_rmax00.bin"

    print(f"\nSWIファイル: {swi_file}")
    print(f"ガイダンスファイル: {guidance_file}")

    # キャッシュキー生成（初期時刻は2025-01-01 00:00:00を想定）
    swi_initial = "2025-01-01T00:00:00"
    guidance_initial = "2025-01-01T00:00:00"
    cache_key = cache_service.generate_cache_key(swi_initial, guidance_initial)

    print(f"\nキャッシュキー: {cache_key}")

    # 既存キャッシュ削除（クリーンテスト）
    if cache_service.exists(cache_key):
        print("\n既存キャッシュを削除中...")
        cache_service.invalidate_cache(cache_key)

    # テスト1: 初回リクエスト（キャッシュミス）
    print("\n" + "=" * 80)
    print("[テスト1] 初回リクエスト（キャッシュミス）")
    print("=" * 80)

    start_time = time.time()
    result1 = main_service.main_process_from_files(swi_file, guidance_file)
    elapsed1 = time.time() - start_time

    print(f"\n処理時間: {elapsed1:.2f}秒")
    print(f"メッシュ数: {sum(len(area['meshes']) for pref in result1['prefectures'].values() for area in pref['areas'])}")

    # キャッシュに手動保存（本来はmain_process_from_separate_urlsが自動保存）
    print(f"\nキャッシュ保存中...")
    cache_start = time.time()
    cache_service.set_cached_result(cache_key, result1, swi_initial, guidance_initial)
    cache_save_time = time.time() - cache_start
    print(f"キャッシュ保存時間: {cache_save_time:.2f}秒")

    # キャッシュメタデータ確認
    metadata = cache_service.get_metadata(cache_key)
    if metadata:
        print(f"\nキャッシュメタデータ:")
        print(f"  - ファイルサイズ: {metadata['file_size_mb']:.2f} MB")
        print(f"  - メッシュ数: {metadata['mesh_count']}")
        print(f"  - 圧縮形式: {metadata['compression_format']}")
        print(f"  - 作成日時: {metadata['created_at']}")

    # テスト2: 2回目リクエスト（キャッシュヒット）
    print("\n" + "=" * 80)
    print("[テスト2] 2回目リクエスト（キャッシュヒット）")
    print("=" * 80)

    start_time = time.time()
    result2 = cache_service.get_cached_result(cache_key)
    elapsed2 = time.time() - start_time

    if result2:
        print(f"\n[OK] キャッシュヒット成功")
        print(f"読み込み時間: {elapsed2:.2f}秒")
        print(f"メッシュ数: {sum(len(area['meshes']) for pref in result2['prefectures'].values() for area in pref['areas'])}")
        print(f"\nデータ一致: {result1 == result2}")
    else:
        print(f"[NG] キャッシュ読み込み失敗")

    # テスト3: パフォーマンス比較
    print("\n" + "=" * 80)
    print("[テスト3] パフォーマンス比較")
    print("=" * 80)

    print(f"\n初回処理時間: {elapsed1:.2f}秒")
    print(f"キャッシュヒット時間: {elapsed2:.2f}秒")
    print(f"高速化倍率: {elapsed1 / elapsed2:.1f}x")
    print(f"時間短縮: {elapsed1 - elapsed2:.2f}秒 ({(1 - elapsed2/elapsed1) * 100:.1f}%削減)")

    # テスト4: キャッシュ統計
    print("\n" + "=" * 80)
    print("[テスト4] キャッシュ統計")
    print("=" * 80)

    stats = cache_service.get_cache_stats()
    print(f"\nキャッシュ数: {stats['cache_count']}")
    print(f"総サイズ: {stats['total_size_mb']:.2f} MB")
    print(f"総メッシュ数: {stats['total_meshes']}")
    print(f"TTL: {stats['ttl_days']}日")

    # テスト5: クリーンアップ
    print("\n" + "=" * 80)
    print("[テスト5] クリーンアップ")
    print("=" * 80)

    cache_service.invalidate_cache(cache_key)
    print(f"\nキャッシュ削除完了: {cache_key}")

    print("\n" + "=" * 80)
    print("テスト完了")
    print("=" * 80)


if __name__ == "__main__":
    test_production_cache()
