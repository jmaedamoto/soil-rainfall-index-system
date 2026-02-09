"""
メッシュ計算処理の詳細プロファイリング
"""
import sys
import os
import time
import cProfile
import pstats
from io import StringIO

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from services.main_service import MainService

def profile_mesh_calculation():
    """メッシュ計算処理のプロファイリング"""

    print("=" * 80)
    print("メッシュ計算処理プロファイリング")
    print("=" * 80)
    print()

    # テストファイル
    swi_file = "data/Z__C_RJTD_20250101000000_SRF_GPV_Ggis1km_Psw_Aper10min_ANAL_grib2.bin"
    guidance_file = "data/guid_msm_grib2_20250101000000_rmax00.bin"

    if not os.path.exists(swi_file) or not os.path.exists(guidance_file):
        print("テストファイルが見つかりません")
        return

    # サービス初期化
    main_service = MainService()

    # プロファイラー設定
    profiler = cProfile.Profile()

    print("プロファイリング開始...")
    profiler.enable()

    # メイン処理実行
    start_time = time.time()
    result = main_service.main_process_from_files(swi_file, guidance_file)
    total_time = time.time() - start_time

    profiler.disable()
    print(f"処理完了: {total_time:.2f}秒")
    print()

    # メッシュ数
    mesh_count = sum(
        len(area['meshes'])
        for pref in result.get('prefectures', {}).values()
        for area in pref.get('areas', [])
    )
    print(f"メッシュ数: {mesh_count:,}")
    print()

    # プロファイリング結果を文字列として取得
    s = StringIO()
    ps = pstats.Stats(profiler, stream=s)
    ps.strip_dirs()
    ps.sort_stats('cumulative')

    print("=" * 80)
    print("上位20関数（累積時間順）")
    print("=" * 80)
    ps.print_stats(20)
    print(s.getvalue())

    # 時間がかかっている関数を特定
    s = StringIO()
    ps = pstats.Stats(profiler, stream=s)
    ps.strip_dirs()
    ps.sort_stats('tottime')

    print("=" * 80)
    print("上位20関数（自己時間順）")
    print("=" * 80)
    ps.print_stats(20)
    print(s.getvalue())

    # 特定の関数の詳細
    print("=" * 80)
    print("calculation_service関連の詳細")
    print("=" * 80)
    ps = pstats.Stats(profiler, stream=sys.stdout)
    ps.strip_dirs()
    ps.sort_stats('cumulative')
    ps.print_stats('calculation_service')

if __name__ == "__main__":
    profile_mesh_calculation()
