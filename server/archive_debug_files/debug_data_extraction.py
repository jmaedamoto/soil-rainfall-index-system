#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GRIB2データ抽出とVBA対応の詳細デバッグ
座標マッピングと値取得の検証
"""
import sys
import os
import csv

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from services.main_service import MainService
from services.calculation_service import CalculationService

def debug_specific_mesh_data_extraction():
    """
    特定メッシュのGRIB2データ抽出を詳細デバッグ
    """
    print("=== GRIB2データ抽出詳細デバッグ ===")

    # MainServiceでGRIB2データを取得
    main_service = MainService()

    # GRIB2データ解析
    print("1. GRIB2データ解析...")
    swi_file = "data/Z__C_RJTD_20230602000000_SRF_GPV_Ggis1km_Psw_Aper10min_ANAL_grib2.bin"
    guidance_file = "data/guid_msm_grib2_20230602000000_rmax00.bin"

    base_info, swi_grib2 = main_service.grib2_service.unpack_swi_grib2_from_file(swi_file)
    _, guidance_grib2 = main_service.grib2_service.unpack_guidance_grib2_from_file(guidance_file)

    print(f"  Base info: initial_date={base_info.initial_date}")
    print(f"  SWI data count: {len(swi_grib2['swi'])}")
    print(f"  Guidance data count: {len(guidance_grib2['data'])}")

    # SWI base_infoの詳細
    print(f"\nSWI GRIB2 base_info:")
    print(f"  Grid numbers: {base_info.x_num} x {base_info.y_num} = {base_info.grid_num}")
    print(f"  Start lat: {base_info.s_lat/1000000:.6f}, lon: {base_info.s_lon/1000000:.6f}")
    print(f"  End lat: {base_info.e_lat/1000000:.6f}, lon: {base_info.e_lon/1000000:.6f}")
    print(f"  Delta lat: {base_info.d_lat/1000000:.6f}, lon: {base_info.d_lon/1000000:.6f}")

    # Guidance base_infoの詳細
    guidance_base_info = guidance_grib2['base_info']
    print(f"\nGuidance GRIB2 base_info:")
    print(f"  Grid numbers: {guidance_base_info.x_num} x {guidance_base_info.y_num} = {guidance_base_info.grid_num}")
    print(f"  Start lat: {guidance_base_info.s_lat/1000000:.6f}, lon: {guidance_base_info.s_lon/1000000:.6f}")
    print(f"  End lat: {guidance_base_info.e_lat/1000000:.6f}, lon: {guidance_base_info.e_lon/1000000:.6f}")
    print(f"  Delta lat: {guidance_base_info.d_lat/1000000:.6f}, lon: {guidance_base_info.d_lon/1000000:.6f}")

    # VBAの既知の値を確認（滋賀県・大津市南部の具体例）
    test_cases = [
        {"area": "大津市南部", "x": 2869, "y": 4187, "expected_rain": [50.0, 26.0, 19.0], "expected_swi": [70.0, 116.76, 125.7989]},
        {"area": "大津市南部", "x": 2871, "y": 4185, "expected_rain": [50.0, 26.0, 19.0], "expected_swi": [68.0, 114.88, 124.0317]}
    ]

    calc_service = CalculationService()

    for test_case in test_cases:
        print(f"\n=== テストケース: {test_case['area']} x={test_case['x']} y={test_case['y']} ===")

        # 座標からメッシュコード計算（逆算）
        print(f"3. 座標からメッシュコード計算テスト...")
        # VBAのX,Y座標からメッシュコードを逆算
        # 関西地方の1次メッシュ: 523x, 534x
        mesh_1st = "53"  # 仮定
        mesh_2nd_x = test_case['x'] - 2800  # 2800-2899範囲を0-99に
        mesh_2nd_y = test_case['y'] - 4100  # 4100-4199範囲を0-99に

        if mesh_2nd_x < 10:
            mesh_2nd_x_str = f"0{mesh_2nd_x}"
        else:
            mesh_2nd_x_str = str(mesh_2nd_x)

        if mesh_2nd_y < 10:
            mesh_2nd_y_str = f"0{mesh_2nd_y}"
        else:
            mesh_2nd_y_str = str(mesh_2nd_y)

        estimated_mesh_code = f"{mesh_1st}{mesh_2nd_x_str}{mesh_2nd_y_str}00"
        print(f"  推定メッシュコード: {estimated_mesh_code}")

        # メッシュコードから座標を計算
        from services.data_service import DataService
        data_service = DataService()
        lat, lon = data_service.meshcode_to_coordinate(estimated_mesh_code)
        print(f"  メッシュコードから逆算した座標: lat={lat:.6f}, lon={lon:.6f}")

        # get_data_num関数テスト (SWI)
        swi_index = calc_service.get_data_num(lat, lon, base_info)
        print(f"  SWI data_num (VBA 1-based): {swi_index}")
        print(f"  SWI Python index (0-based): {swi_index - 1}")

        if swi_index - 1 < len(swi_grib2['swi']):
            swi_raw = swi_grib2['swi'][swi_index - 1]
            first_tunk_raw = swi_grib2['first_tunk'][swi_index - 1]
            second_tunk_raw = swi_grib2['second_tunk'][swi_index - 1]

            swi_value = swi_raw / 10
            first_tunk = first_tunk_raw / 10
            second_tunk = second_tunk_raw / 10
            third_tunk = swi_value - first_tunk - second_tunk

            print(f"  SWI Raw値: {swi_raw} → {swi_value}")
            print(f"  First tunk raw: {first_tunk_raw} → {first_tunk}")
            print(f"  Second tunk raw: {second_tunk_raw} → {second_tunk}")
            print(f"  Third tunk 計算値: {third_tunk}")
            print(f"  VBA期待SWI初期値: {test_case['expected_swi'][0]}")
        else:
            print(f"  ERROR: SWI index {swi_index-1} が範囲外 (max: {len(swi_grib2['swi'])})")

        # get_data_num関数テスト (Guidance)
        guidance_index = calc_service.get_data_num(lat, lon, guidance_base_info)
        print(f"  Guidance data_num (VBA 1-based): {guidance_index}")
        print(f"  Guidance Python index (0-based): {guidance_index - 1}")

        if guidance_index - 1 < len(guidance_grib2['data'][0]['value']):
            # 最初の時刻のガイダンスデータを取得
            first_guidance = guidance_grib2['data'][0]['value'][guidance_index - 1]
            print(f"  Guidance 最初の値: {first_guidance}")
            print(f"  VBA期待Rain初期値: {test_case['expected_rain'][0]}")
        else:
            print(f"  ERROR: Guidance index {guidance_index-1} が範囲外")

        # 実際の計算テスト
        print(f"4. 実計算との比較...")

        # テスト用Meshオブジェクト作成
        class TestMesh:
            def __init__(self, lat, lon):
                self.lat = lat
                self.lon = lon
                self.advisary_bound = 100
                self.warning_bound = 150
                self.dosyakei_bound = 200
                self.code = estimated_mesh_code

        test_mesh = TestMesh(lat, lon)

        # Rain計算
        rain_result = calc_service.calc_rain_timelapse(test_mesh, guidance_grib2)
        print(f"  計算Rain結果: {[{'ft': r.ft, 'value': r.value} for r in rain_result[:3]]}")
        print(f"  VBA期待Rain: {[{'ft': i*3, 'value': v} for i, v in enumerate(test_case['expected_rain'])]}")

        # SWI計算
        swi_result = calc_service.calc_swi_timelapse(test_mesh, swi_grib2, guidance_grib2)
        print(f"  計算SWI結果: {[{'ft': s.ft, 'value': s.value} for s in swi_result[:3]]}")
        print(f"  VBA期待SWI: {[{'ft': i*3, 'value': v} for i, v in enumerate(test_case['expected_swi'])]}")

def main():
    """
    メイン処理
    """
    debug_specific_mesh_data_extraction()

if __name__ == "__main__":
    main()