#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SWI生データ値の直接確認 - VBA vs Python読み取り値の比較
"""

import sys
import os
sys.path.append(os.path.dirname(__file__))

from services.grib2_service import Grib2Service
from services.calculation_service import CalculationService

def main():
    print("=== SWI生データ値直接確認 ===")
    
    # ファイル読み込み
    grib2_service = Grib2Service()
    calculation_service = CalculationService()
    swi_file = "data/Z__C_RJTD_20230602000000_SRF_GPV_Ggis1km_Psw_Aper10min_ANAL_grib2.bin"
    
    print("SWIファイル解析中...")
    base_info, swi_result = grib2_service.unpack_swi_grib2_from_file(swi_file)
    
    print(f"base_info grid_num: {base_info.grid_num}")
    print(f"SWI配列長: {len(swi_result['swi'])}")
    print(f"First tunk配列長: {len(swi_result['first_tunk'])}")
    print(f"Second tunk配列長: {len(swi_result['second_tunk'])}")
    
    # テストメッシュの座標: (2869, 4187)
    test_lat = 35.0041666666667
    test_lon = 135.868055555556
    
    print(f"\nテスト座標: lat={test_lat}, lon={test_lon}")
    
    # get_data_num計算
    swi_index = calculation_service.get_data_num(test_lat, test_lon, base_info)
    python_swi_index = swi_index - 1  # VBA 1-based -> Python 0-based
    
    print(f"VBA swi_index: {swi_index}")
    print(f"Python swi_index: {python_swi_index}")
    
    if python_swi_index < len(swi_result['swi']):
        # 生データ値（/10前）
        raw_swi = swi_result['swi'][python_swi_index]
        raw_first = swi_result['first_tunk'][python_swi_index]
        raw_second = swi_result['second_tunk'][python_swi_index]
        
        print(f"\n=== 生データ値（/10前） ===")
        print(f"Raw SWI: {raw_swi}")
        print(f"Raw First tunk: {raw_first}")
        print(f"Raw Second tunk: {raw_second}")
        
        # VBA処理（/10後）
        swi = raw_swi / 10
        first_tunk = raw_first / 10
        second_tunk = raw_second / 10
        third_tunk = swi - first_tunk - second_tunk
        
        print(f"\n=== VBA処理（/10後） ===")
        print(f"SWI: {swi}")
        print(f"First tunk: {first_tunk}")
        print(f"Second tunk: {second_tunk}")
        print(f"Third tunk: {third_tunk}")
        
        # CSV期待値
        swi_expected = {}
        with open('data/shiga_swi.csv', 'r', encoding='shift_jis') as f:
            lines = f.readlines()
        
        for line in lines:
            parts = line.strip().split(',')
            if len(parts) >= 4 and parts[1] and parts[2] and parts[3]:
                try:
                    x = int(parts[1])
                    y = int(parts[2])
                    swi_value = float(parts[3])
                    swi_expected[(x, y)] = swi_value
                except:
                    continue
        
        expected_swi = swi_expected.get((2869, 4187))
        print(f"\n=== CSV期待値との比較 ===")
        print(f"CSV期待値: {expected_swi}")
        print(f"Python SWI: {swi}")
        print(f"差異: {abs(swi - expected_swi) if expected_swi else 'N/A'}")
        
        if expected_swi and abs(swi - expected_swi) > 0.1:
            print(f"★ 差異発見: 生データレベルでVBAと差異があります")
            print(f"  期待される生データ値: {expected_swi * 10}")
            print(f"  実際の生データ値: {raw_swi}")
        else:
            print("OK: SWI生データは正常です")
    else:
        print(f"ERROR: インデックス範囲外 {python_swi_index} >= {len(swi_result['swi'])}")

if __name__ == "__main__":
    main()