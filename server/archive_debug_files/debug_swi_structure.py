#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SWI GRIB2ファイル構造の詳細分析
dataキーが存在しない原因を特定
"""

import sys
import os
sys.path.append(os.path.dirname(__file__))

from services.grib2_service import Grib2Service

def main():
    print("=== SWI GRIB2ファイル構造分析 ===")
    
    try:
        grib2_service = Grib2Service()
        swi_file = "data/Z__C_RJTD_20230602000000_SRF_GPV_Ggis1km_Psw_Aper10min_ANAL_grib2.bin"
        
        print("1. SWI GRIB2ファイル解析")
        swi_base_info, swi_result = grib2_service.unpack_swi_grib2_from_file(swi_file)
        
        print(f"Base info: {swi_base_info}")
        print(f"Result keys: {list(swi_result.keys())}")
        print(f"Result type: {type(swi_result)}")
        
        # swi_resultの詳細構造を確認
        for key, value in swi_result.items():
            print(f"\nKey: {key}")
            print(f"  Type: {type(value)}")
            if isinstance(value, list):
                print(f"  Length: {len(value)}")
                if len(value) > 0:
                    print(f"  First item type: {type(value[0])}")
                    print(f"  First item: {value[0]}")
            elif hasattr(value, '__len__'):
                try:
                    print(f"  Length: {len(value)}")
                except:
                    print(f"  Value: {value}")
            else:
                print(f"  Value: {value}")
        
        # VBAのコードを参考にSWIデータアクセス方法を確認
        print("\n2. VBA Module.basのunpack_swi_grib2を参考に分析")
        print("VBA: swi_data(i) = get_dat(binData, p, 2) / 10")
        print("VBA: Return (initial_time, swi_data)")
        
        # swi_resultから適切なデータを抽出
        if 'swi_data' in swi_result:
            swi_data = swi_result['swi_data']
            print(f"\nFound 'swi_data' key: length={len(swi_data)}")
            print(f"First 10 values: {swi_data[:10] if len(swi_data) >= 10 else swi_data}")
        elif 'data' in swi_result:
            print(f"\nFound 'data' key")
            swi_data = swi_result['data']
        else:
            print("\nNo 'swi_data' or 'data' key found")
            # 可能性のあるキーを確認
            for key, value in swi_result.items():
                if isinstance(value, list) and len(value) > 1000:  # 大きな配列データ
                    print(f"Potential data array: key='{key}', length={len(value)}")
                    swi_data = value
                    break
        
        if 'swi_data' in locals():
            # 特定のインデックスでの値を確認
            print(f"\n3. インデックス4025750での値確認")
            test_index = 4025750
            if test_index < len(swi_data):
                value = swi_data[test_index]
                print(f"Value at index {test_index}: {value}")
                
                # 周辺値も確認
                print("周辺値:")
                for offset in [-2, -1, 0, 1, 2]:
                    idx = test_index + offset
                    if 0 <= idx < len(swi_data):
                        val = swi_data[idx]
                        note = " <- Current" if offset == 0 else ""
                        if abs(val - 70.0) < 0.1:
                            note += " <- Target!"
                        print(f"  Index {idx}: {val}{note}")
            else:
                print(f"Index {test_index} out of range (max: {len(swi_data)})")
        
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()