"""
キャッシュあり/なしの結果が完全同一であることを検証するテスト
"""
import sys
import os
import json
import time

# プロジェクトルートをパスに追加
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from services.main_service import MainService
from services.cache_service import CacheService
from config.config_service import ConfigService

def compare_results(result1, result2, path=""):
    """2つの結果を再帰的に比較"""
    differences = []

    if type(result1) != type(result2):
        differences.append(f"{path}: 型が異なる ({type(result1)} vs {type(result2)})")
        return differences

    if isinstance(result1, dict):
        keys1 = set(result1.keys())
        keys2 = set(result2.keys())

        if keys1 != keys2:
            differences.append(f"{path}: キーが異なる")
            differences.append(f"  result1のみ: {keys1 - keys2}")
            differences.append(f"  result2のみ: {keys2 - keys1}")

        for key in keys1 & keys2:
            new_path = f"{path}.{key}" if path else key
            differences.extend(compare_results(result1[key], result2[key], new_path))

    elif isinstance(result1, list):
        if len(result1) != len(result2):
            differences.append(f"{path}: リスト長が異なる ({len(result1)} vs {len(result2)})")
        else:
            for i in range(len(result1)):
                new_path = f"{path}[{i}]"
                differences.extend(compare_results(result1[i], result2[i], new_path))

    elif isinstance(result1, float):
        # 浮動小数点の比較（許容誤差1e-10）
        if abs(result1 - result2) > 1e-10:
            differences.append(f"{path}: 値が異なる ({result1} vs {result2})")

    else:
        if result1 != result2:
            differences.append(f"{path}: 値が異なる ({result1} vs {result2})")

    return differences

def main():
    print("=" * 80)
    print("キャッシュあり/なしの結果同一性検証テスト")
    print("=" * 80)
    print()

    # テストファイルパス
    swi_file = "data/Z__C_RJTD_20250101000000_SRF_GPV_Ggis1km_Psw_Aper10min_ANAL_grib2.bin"
    guidance_file = "data/guid_msm_grib2_20250101000000_rmax00.bin"

    if not os.path.exists(swi_file) or not os.path.exists(guidance_file):
        print("[NG] テストファイルが見つかりません")
        return

    print(f"SWIファイル: {swi_file}")
    print(f"ガイダンスファイル: {guidance_file}")
    print()

    # キャッシュサービス初期化
    config_service = ConfigService()
    cache_service = CacheService()

    # キャッシュキー
    cache_key = "swi_20250101000000_guid_20250101000000"

    # 既存のキャッシュを削除
    print("既存キャッシュをクリア...")
    cache_service.invalidate_cache(cache_key)
    print()

    # ==========================================
    # テスト1: キャッシュなしで実行
    # ==========================================
    print("=" * 80)
    print("[テスト1] キャッシュなしで実行")
    print("=" * 80)

    start_time = time.time()
    main_service = MainService()
    result_no_cache = main_service.main_process_from_files(swi_file, guidance_file)
    time_no_cache = time.time() - start_time

    print(f"処理時間: {time_no_cache:.2f}秒")
    print(f"メッシュ数: {sum(len(area['meshes']) for pref in result_no_cache.get('prefectures', {}).values() for area in pref.get('areas', []))}")
    print()

    # キャッシュに保存
    print("キャッシュに保存...")
    cache_service.set_cached_result(cache_key, result_no_cache, '2025-01-01T00:00:00', '2025-01-01T00:00:00')
    print()

    # ==========================================
    # テスト2: キャッシュありで実行
    # ==========================================
    print("=" * 80)
    print("[テスト2] キャッシュから読み込み")
    print("=" * 80)

    # キャッシュが存在することを確認
    if not cache_service.exists(cache_key):
        print("[NG] キャッシュが存在しません")
        return

    print("[OK] キャッシュが存在します")

    start_time = time.time()
    result_with_cache = cache_service.get_cached_result(cache_key)
    time_with_cache = time.time() - start_time

    print(f"読み込み時間: {time_with_cache:.2f}秒")
    print(f"メッシュ数: {sum(len(area['meshes']) for pref in result_with_cache.get('prefectures', {}).values() for area in pref.get('areas', []))}")
    print()

    # ==========================================
    # テスト3: 結果の比較
    # ==========================================
    print("=" * 80)
    print("[テスト3] 結果の比較")
    print("=" * 80)

    # 比較（calculation_timeは除外）
    result1 = {k: v for k, v in result_no_cache.items() if k != 'calculation_time'}
    result2 = {k: v for k, v in result_with_cache.items() if k != 'calculation_time'}

    differences = compare_results(result1, result2)

    if not differences:
        print("[OK] 完全一致！")
        print()
        print("キャッシュあり/なしで結果が100%同一であることを確認しました。")
    else:
        print(f"[NG] 差異が見つかりました（{len(differences)}件）:")
        for i, diff in enumerate(differences[:20], 1):  # 最初の20件のみ表示
            print(f"  {i}. {diff}")
        if len(differences) > 20:
            print(f"  ... 他 {len(differences) - 20} 件")

    print()

    # ==========================================
    # テスト4: パフォーマンス比較
    # ==========================================
    print("=" * 80)
    print("[テスト4] パフォーマンス比較")
    print("=" * 80)
    print(f"キャッシュなし: {time_no_cache:.2f}秒")
    print(f"キャッシュあり: {time_with_cache:.2f}秒")
    print(f"高速化倍率: {time_no_cache / time_with_cache:.1f}x")
    print(f"時間短縮: {time_no_cache - time_with_cache:.2f}秒 ({(1 - time_with_cache/time_no_cache)*100:.1f}%削減)")
    print()

    # クリーンアップ
    print("=" * 80)
    print("クリーンアップ")
    print("=" * 80)
    cache_service.invalidate_cache(cache_key)
    print(f"キャッシュ削除完了: {cache_key}")
    print()

    print("=" * 80)
    print("テスト完了")
    print("=" * 80)

if __name__ == "__main__":
    main()
