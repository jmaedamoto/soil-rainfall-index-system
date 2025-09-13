#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SWI値の詳細デバッグ - VBAとの差異原因調査
"""

import sys
import os
sys.path.append(os.path.dirname(__file__))

from services.main_service import MainService

def main():
    print("=== SWI値詳細デバッグ ===")
    
    # 期待値読み込み
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
    
    print(f"SWI期待値: {len(swi_expected)}件")
    
    # MainServiceでテスト
    main_service = MainService()
    swi_file = "data/Z__C_RJTD_20230602000000_SRF_GPV_Ggis1km_Psw_Aper10min_ANAL_grib2.bin"
    guidance_file = "data/guid_msm_grib2_20230602000000_rmax00.bin"
    
    print("\nメイン処理実行中...")
    result = main_service.main_process_from_files(swi_file, guidance_file)
    
    if result and result.get('status') == 'success':
        shiga_data = result['prefectures'].get('shiga')
        if shiga_data:
            first_area = shiga_data['areas'][0]
            first_mesh = first_area['meshes'][0]  # 最初のメッシュのみ
            
            mesh_key = (first_mesh['x'], first_mesh['y'])
            expected_swi = swi_expected.get(mesh_key)
            
            print(f"\n=== 詳細SWI値比較 ===")
            print(f"メッシュ: {first_mesh['code']} ({first_mesh['x']}, {first_mesh['y']})")
            print(f"CSV期待値: {expected_swi}")
            
            if 'swi_timeline' in first_mesh:
                swi_timeline = first_mesh['swi_timeline']
                if swi_timeline:
                    ft0_swi = swi_timeline[0]['value']
                    print(f"Python FT=0値: {ft0_swi}")
                    print(f"差異: {abs(ft0_swi - expected_swi) if expected_swi else 'N/A'}")
                    
                    print(f"\n=== SWI時系列詳細 ===")
                    for i, item in enumerate(swi_timeline[:3]):
                        print(f"  FT={item['ft']}: {item['value']}")
                else:
                    print("SWI時系列データなし")
            else:
                print("SWI時系列キーなし")
                
    else:
        print("メイン処理失敗")

if __name__ == "__main__":
    main()