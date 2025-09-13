#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SWI計算の詳細デバッグ
VBA CSVとの一致しない原因を特定する
"""

import sys
import os
import csv
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from services.main_service import MainService

def debug_swi_calculation():
    """SWI計算の詳細をデバッグ"""
    print("=== SWI計算詳細デバッグ ===")

    # 期待値を読み込み
    swi_expected = {}
    with open('data/shiga_swi.csv', 'r', encoding='shift_jis') as f:
        lines = f.readlines()

    for line in lines[1:]:  # skip header
        parts = line.strip().split(',')
        if len(parts) >= 7 and parts[1] and parts[2]:
            try:
                area = parts[0].strip()
                x = int(parts[1])
                y = int(parts[2])
                advisary = int(parts[3]) if parts[3].strip() != '' else 9999
                warning = int(parts[4]) if parts[4].strip() != '' else 9999
                dosyakei = int(parts[5]) if parts[5].strip() != '' else 9999
                swi_ft0 = float(parts[6])

                swi_expected[(x, y)] = {
                    'area': area,
                    'advisary': advisary,
                    'warning': warning,
                    'dosyakei': dosyakei,
                    'swi_ft0': swi_ft0
                }
            except:
                continue

    # GRIB2データ取得
    main_service = MainService()
    swi_file = "data/Z__C_RJTD_20230602000000_SRF_GPV_Ggis1km_Psw_Aper10min_ANAL_grib2.bin"
    guidance_file = "data/guid_msm_grib2_20230602000000_rmax00.bin"

    base_info, swi_grib2 = main_service.grib2_service.unpack_swi_grib2_from_file(swi_file)
    _, guidance_grib2 = main_service.grib2_service.unpack_guidance_grib2_from_file(guidance_file)

    # 最初の5つのVBA座標について詳細分析
    test_coords = list(swi_expected.keys())[:5]

    for i, (vba_x, vba_y) in enumerate(test_coords):
        expected = swi_expected[(vba_x, vba_y)]

        print(f"\n=== テスト{i+1}: VBA座標({vba_x}, {vba_y}) - {expected['area']} ===")
        print(f"期待SWI値: {expected['swi_ft0']}")

        # VBA座標をメッシュコード形式として緯度経度変換
        lat = (vba_y + 0.5) * 30 / 3600  # メッシュコード変換式
        lon = (vba_x + 0.5) * 45 / 3600 + 100  # メッシュコード変換式

        print(f"変換後緯度経度: lat={lat:.6f}, lon={lon:.6f}")

        # get_data_num関数でインデックス取得
        calc_service = main_service.calculation_service
        swi_index = calc_service.get_data_num(lat, lon, base_info)
        guidance_index = calc_service.get_data_num(lat, lon, guidance_grib2['base_info'])

        print(f"SWIインデックス: {swi_index}")
        print(f"Guidanceインデックス: {guidance_index}")

        # Python 0-based インデックスに変換
        python_swi_index = swi_index - 1
        python_guidance_index = guidance_index - 1

        # 範囲チェック
        if python_swi_index >= len(swi_grib2['swi']):
            print(f"エラー: SWIインデックス{python_swi_index}が範囲外（最大{len(swi_grib2['swi'])}）")
            continue

        # 初期タンク値取得
        swi_raw = swi_grib2['swi'][python_swi_index]
        first_tunk_raw = swi_grib2['first_tunk'][python_swi_index]
        second_tunk_raw = swi_grib2['second_tunk'][python_swi_index]

        swi_initial = swi_raw / 10
        first_tunk = first_tunk_raw / 10
        second_tunk = second_tunk_raw / 10
        third_tunk = swi_initial - first_tunk - second_tunk

        print(f"初期タンク値:")
        print(f"  SWI(total): raw={swi_raw}, value={swi_initial}")
        print(f"  第1タンク: raw={first_tunk_raw}, value={first_tunk}")
        print(f"  第2タンク: raw={second_tunk_raw}, value={second_tunk}")
        print(f"  第3タンク: value={third_tunk} (計算値)")

        # 降水量データ取得（最初の時刻のみテスト）
        if python_guidance_index < len(guidance_grib2['data'][0]['value']):
            rain_value = guidance_grib2['data'][0]['value'][python_guidance_index]
            print(f"降水量(FT=3): {rain_value}")

            # タンクモデル1ステップ実行
            new_first, new_second, new_third = calc_service.calc_tunk_model(
                first_tunk, second_tunk, third_tunk, 3, rain_value
            )

            new_swi = new_first + new_second + new_third

            print(f"タンクモデル計算結果:")
            print(f"  新第1タンク: {new_first}")
            print(f"  新第2タンク: {new_second}")
            print(f"  新第3タンク: {new_third}")
            print(f"  新SWI値: {new_swi}")

            diff = abs(new_swi - expected['swi_ft0'])
            print(f"期待値との差分: {diff:.2f}")

            # 初期値（FT=0）との比較
            diff_initial = abs(swi_initial - expected['swi_ft0'])
            print(f"初期値との差分: {diff_initial:.2f}")

            if diff_initial < diff:
                print("注意: 初期値の方が期待値に近い可能性があります")

if __name__ == "__main__":
    debug_swi_calculation()