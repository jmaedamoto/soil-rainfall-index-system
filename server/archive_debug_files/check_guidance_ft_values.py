#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GRIB2ガイダンスデータのFT値を詳細確認
"""

import sys
import os
sys.path.append(os.path.dirname(__file__))

from services.grib2_service import Grib2Service

def main():
    print("=== GRIB2ガイダンスデータのFT値確認 ===")
    
    grib2_service = Grib2Service()
    guidance_file = "data/guid_msm_grib2_20230602000000_rmax00.bin"
    
    guidance_base_info, guidance_result = grib2_service.unpack_guidance_grib2_from_file(guidance_file)
    
    print(f"ガイダンスデータ数: {len(guidance_result['data'])}")
    
    print("\\n--- 全FT値の確認 ---")
    for i, item in enumerate(guidance_result['data']):
        ft = item['ft']
        value_count = len(item['value'])
        print(f"データ{i+1}: FT={ft}, 値の数={value_count}")
        
        # 座標(2869, 4187)の値も確認
        guidance_index = 133918  # デバッグで確認済み
        python_index = guidance_index - 1
        
        if python_index < value_count:
            value_at_target = item['value'][python_index]
            print(f"  座標(2869, 4187)の値: {value_at_target}")

if __name__ == "__main__":
    main()