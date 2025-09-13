#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
座標計算の詳細検証 - VBAとPythonの差異調査
"""

import sys
import os
sys.path.append(os.path.dirname(__file__))

from services.grib2_service import Grib2Service
from services.calculation_service import CalculationService

def main():
    print("=== 座標計算詳細検証 ===")
    
    # CSV期待値を読み込み
    swi_expected = {}
    with open('data/shiga_swi.csv', 'r', encoding='shift_jis') as f:
        lines = f.readlines()
    
    for line in lines[:5]:  # 最初の5行をテスト
        parts = line.strip().split(',')
        if len(parts) >= 4 and parts[1] and parts[2] and parts[3]:
            try:
                x = int(parts[1])
                y = int(parts[2])
                swi_value = float(parts[3])
                swi_expected[(x, y)] = swi_value
                print(f"期待値: ({x}, {y}) → SWI={swi_value}")
            except:
                continue
    
    # SWIファイル読み込み
    grib2_service = Grib2Service()
    calculation_service = CalculationService()
    swi_file = "data/Z__C_RJTD_20230602000000_SRF_GPV_Ggis1km_Psw_Aper10min_ANAL_grib2.bin"
    
    base_info, swi_result = grib2_service.unpack_swi_grib2_from_file(swi_file)
    
    print(f"\nbase_info詳細:")
    print(f"  grid_num: {base_info.grid_num}")
    print(f"  x_num: {base_info.x_num}, y_num: {base_info.y_num}")
    print(f"  s_lat: {base_info.s_lat}, s_lon: {base_info.s_lon}")
    print(f"  d_lat: {base_info.d_lat}, d_lon: {base_info.d_lon}")
    
    print(f"\n=== 各座標での詳細計算 ===")
    
    for (x, y), expected_swi in swi_expected.items():
        # メッシュコードから緯度経度変換（VBAロジック）
        lat, lon = calculation_service.meshcode_to_coordinate(f"{x:04d}{y:04d}")
        
        print(f"\n座標 ({x}, {y})")
        print(f"  期待SWI: {expected_swi}")
        print(f"  緯度経度: {lat}, {lon}")
        
        # get_data_num計算
        data_num = calculation_service.get_data_num(lat, lon, base_info)
        python_index = data_num - 1
        
        print(f"  VBA data_num: {data_num}")
        print(f"  Python index: {python_index}")
        
        # 実際のSWI値
        if python_index < len(swi_result['swi']):
            raw_swi = swi_result['swi'][python_index]
            actual_swi = raw_swi / 10
            print(f"  生SWI: {raw_swi}")
            print(f"  実際SWI: {actual_swi}")
            print(f"  差異: {abs(actual_swi - expected_swi)}")
            
            if abs(actual_swi - expected_swi) > 0.1:
                print(f"  ★ 大きな差異: {actual_swi} vs {expected_swi}")
                
                # 周辺インデックスの値も確認
                for offset in [-2, -1, 0, 1, 2]:
                    check_index = python_index + offset
                    if 0 <= check_index < len(swi_result['swi']):
                        check_raw = swi_result['swi'][check_index]
                        check_swi = check_raw / 10
                        print(f"    index[{check_index}]: {check_swi}")
                        if abs(check_swi - expected_swi) < 0.1:
                            print(f"    → 一致発見！ offset={offset}")
        else:
            print(f"  ERROR: インデックス範囲外")

if __name__ == "__main__":
    main()