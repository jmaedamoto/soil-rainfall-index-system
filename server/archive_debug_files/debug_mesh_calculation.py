#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
メッシュ計算処理の詳細デバッグ
"""
import sys
import os
import traceback

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from services.main_service import MainService
from services.calculation_service import CalculationService

def debug_mesh_calculation():
    """
    メッシュ計算の詳細デバッグ
    """
    print("=== メッシュ計算詳細デバッグ ===")

    try:
        # MainServiceでGRIB2データを取得
        main_service = MainService()

        # GRIB2データ解析
        print("1. GRIB2データ解析...")
        swi_file = "data/Z__C_RJTD_20230602000000_SRF_GPV_Ggis1km_Psw_Aper10min_ANAL_grib2.bin"
        guidance_file = "data/guid_msm_grib2_20230602000000_rmax00.bin"

        base_info, swi_grib2 = main_service.grib2_service.unpack_swi_grib2_from_file(swi_file)
        _, guidance_grib2 = main_service.grib2_service.unpack_guidance_grib2_from_file(guidance_file)

        print(f"   Base info: initial_date={base_info.initial_date}")
        print(f"   SWI data count: {len(swi_grib2['swi'])}")
        print(f"   Guidance data count: {len(guidance_grib2['data'])}")

        # 地域データ構築
        print("\n2. 地域データ構築...")
        prefectures = main_service.data_service.prepare_areas()

        total_meshes = sum(len(area.meshes) for pref in prefectures for area in pref.areas)
        print(f"   総メッシュ数: {total_meshes}")

        # 最初の1つのメッシュで詳細デバッグ
        print("\n3. 最初のメッシュで詳細計算デバッグ...")
        first_mesh = None
        for pref in prefectures:
            for area in pref.areas:
                if area.meshes:
                    first_mesh = area.meshes[0]
                    print(f"   対象メッシュ: {first_mesh.code} (area: {area.name})")
                    print(f"   座標: lat={first_mesh.lat}, lon={first_mesh.lon}")
                    print(f"   境界値: {first_mesh.advisary_bound}/{first_mesh.warning_bound}/{first_mesh.dosyakei_bound}")
                    break
            if first_mesh:
                break

        if not first_mesh:
            print("テスト対象メッシュが見つかりません")
            return

        # 計算サービスを直接テスト
        calc_service = CalculationService()

        print("\n4. Rain Timeline計算テスト...")
        try:
            print(f"   guidance_grib2 keys: {guidance_grib2.keys()}")
            print(f"   guidance_grib2['base_info']: {guidance_grib2.get('base_info', 'なし')}")

            rain_timeline = calc_service.calc_rain_timelapse(first_mesh, guidance_grib2)
            print(f"   結果: {len(rain_timeline)} 個のポイント")
            if rain_timeline:
                print(f"   最初の3ポイント: {rain_timeline[:3]}")
                for i, point in enumerate(rain_timeline[:3]):
                    print(f"     [{i}] ft={point.ft}, value={point.value}")
            else:
                print("   WARNING: rain_timelineが空です")
        except Exception as e:
            print(f"   エラー: {e}")
            traceback.print_exc()

        print("\n5. SWI Timeline計算テスト...")
        try:
            print(f"   swi_grib2 keys: {swi_grib2.keys()}")
            print(f"   swi_grib2['base_info']: {swi_grib2.get('base_info', 'なし')}")

            swi_timeline = calc_service.calc_swi_timelapse(first_mesh, swi_grib2, guidance_grib2)
            print(f"   結果: {len(swi_timeline)} 個のポイント")
            if swi_timeline:
                print(f"   最初の3ポイント: {swi_timeline[:3]}")
                for i, point in enumerate(swi_timeline[:3]):
                    print(f"     [{i}] ft={point.ft}, value={point.value}")
            else:
                print("   WARNING: swi_timelineが空です")
        except Exception as e:
            print(f"   エラー: {e}")
            traceback.print_exc()

        # get_data_num 関数のテスト
        print("\n6. get_data_num関数テスト...")
        try:
            guidance_index = calc_service.get_data_num(first_mesh.lat, first_mesh.lon, guidance_grib2['base_info'])
            print(f"   Guidance index (VBA 1-based): {guidance_index}")
            print(f"   Python index (0-based): {guidance_index - 1}")

            swi_index = calc_service.get_data_num(first_mesh.lat, first_mesh.lon, swi_grib2['base_info'])
            print(f"   SWI index (VBA 1-based): {swi_index}")
            print(f"   Python index (0-based): {swi_index - 1}")

            # インデックスの有効性チェック
            max_guidance_index = len(guidance_grib2['data'][0]['data']) if guidance_grib2['data'] else 0
            max_swi_index = len(swi_grib2['swi']) if swi_grib2['swi'] else 0

            print(f"   Guidance data配列サイズ: {max_guidance_index}")
            print(f"   SWI data配列サイズ: {max_swi_index}")

            if guidance_index - 1 >= max_guidance_index:
                print(f"   ERROR: guidance_index ({guidance_index-1}) が配列サイズ ({max_guidance_index}) を超えています")

            if swi_index - 1 >= max_swi_index:
                print(f"   ERROR: swi_index ({swi_index-1}) が配列サイズ ({max_swi_index}) を超えています")

        except Exception as e:
            print(f"   エラー: {e}")
            traceback.print_exc()

    except Exception as e:
        print(f"全体的なエラー: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    debug_mesh_calculation()