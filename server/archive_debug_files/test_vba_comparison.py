#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
VBAのModule.basと完全一致するかを検証するテスト
"""

import sys
import os
sys.path.append(os.path.dirname(__file__))

from services.grib2_service import Grib2Service
from services.calculation_service import CalculationService
from services.data_service import DataService

def main():
    print("=== VBAのModule.basとの完全一致テスト ===")
    
    # 正確に同じGRIB2ファイルを使用
    swi_file = "data/Z__C_RJTD_20230602000000_SRF_GPV_Ggis1km_Psw_Aper10min_ANAL_grib2.bin"
    guidance_file = "data/guid_msm_grib2_20230602000000_rmax00.bin"
    
    print(f"SWIファイル: {swi_file}")
    print(f"ガイダンスファイル: {guidance_file}")
    
    try:
        # サービス初期化
        grib2_service = Grib2Service()
        calc_service = CalculationService()
        data_service = DataService()
        
        # GRIB2ファイル解析
        print("\n1. GRIB2ファイル解析...")
        base_info, swi_data = grib2_service.unpack_swi_grib2_from_file(swi_file)
        print(f"SWI grid_num: {base_info.grid_num}")
        
        base_info_guidance, guidance_data = grib2_service.unpack_guidance_grib2_from_file(guidance_file)
        print(f"Guidance data count: {len(guidance_data)}")
        
        # CSVデータ構築
        print("\n2. CSVデータ構築...")
        prefectures = data_service.prepare_areas()
        shiga = None
        for pref in prefectures:
            if pref.code == "shiga":
                shiga = pref
                break
        
        if not shiga:
            print("ERROR: 滋賀県データが見つかりません")
            return
            
        print(f"滋賀県メッシュ数: {len([m for a in shiga.areas for m in a.meshes])}")
        
        # 最初のメッシュでテスト（VBAと同じデータ）
        first_area = shiga.areas[0]
        first_mesh = first_area.meshes[0]
        
        print(f"\n3. 最初のメッシュ詳細:")
        print(f"  地域名: {first_area.name}")
        print(f"  メッシュコード: {first_mesh.code}")
        print(f"  X座標: {first_mesh.x}")
        print(f"  Y座標: {first_mesh.y}")
        print(f"  緯度: {first_mesh.lat}")
        print(f"  経度: {first_mesh.lon}")
        print(f"  注意報境界: {first_mesh.advisary_bound}")
        print(f"  警報境界: {first_mesh.warning_bound}")
        print(f"  土砂災害境界: {first_mesh.dosyakei_bound}")
        
        # VBAの期待値と比較
        print(f"\n4. 期待値との比較:")
        print(f"  期待: 地域名=大津市內, X=2869, Y=4187")
        print(f"  実際: 地域名={first_area.name}, X={first_mesh.x}, Y={first_mesh.y}")
        
        # SWI時系列計算
        print(f"\n5. SWI時系列計算テスト...")
        swi_grib2 = {
            'base_info': base_info,
            'swi': swi_data['swi'],
            'first_tunk': swi_data['first_tunk'],
            'second_tunk': swi_data['second_tunk']
        }
        
        guidance_grib2 = {
            'base_info': base_info_guidance,
            'data': guidance_data
        }
        
        swi_timeline = calc_service.calc_swi_timelapse(first_mesh, swi_grib2, guidance_grib2)
        print(f"  SWIタイムライン長: {len(swi_timeline)}")
        
        if swi_timeline:
            print(f"  SWI FT=0: 期待70.0 → 実際{swi_timeline[0].value}")
            print(f"  SWI最初の3つ:")
            for i, s in enumerate(swi_timeline[:3]):
                print(f"    FT={s.ft}: {s.value}")
        
        # 雨量時系列計算
        print(f"\n6. 雨量時系列計算テスト...")
        rain_timeline = calc_service.calc_rain_timelapse(first_mesh, guidance_grib2)
        print(f"  雨量タイムライン長: {len(rain_timeline)}")
        
        if rain_timeline:
            # VBAでは最初の雨量データはFT=3
            print(f"  Rain FT=3: 期待50 → 実際{rain_timeline[0].value if len(rain_timeline) > 0 else 'なし'}")
            print(f"  Rain最初の3つ:")
            for i, r in enumerate(rain_timeline[:3]):
                print(f"    FT={r.ft}: {r.value}")
        else:
            print("  WARNING: 雨量データが空です")
            print("  guidance_grib2構造を確認:")
            print(f"    keys: {list(guidance_grib2.keys())}")
            if 'data' in guidance_grib2 and len(guidance_grib2['data']) > 0:
                print(f"    first data keys: {list(guidance_grib2['data'][0].keys())}")
                if 'value' in guidance_grib2['data'][0]:
                    print(f"    value array length: {len(guidance_grib2['data'][0]['value'])}")
        
        print(f"\n=== テスト完了 ===")
        
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()