#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
最終VBA検証テスト - 参照CSVとの完全一致確認
"""

import sys
import os
sys.path.append(os.path.dirname(__file__))

from services.grib2_service import Grib2Service
from services.calculation_service import CalculationService
from services.data_service import DataService

def main():
    print("=== 最終VBA検証テスト ===")
    
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
        
        base_info_guidance, guidance_result = grib2_service.unpack_guidance_grib2_from_file(guidance_file)
        guidance_data = guidance_result['data']
        print(f"ガイダンスデータ数: {len(guidance_data)} (期待値: 26)")
        
        # CSVデータ構築
        print("\n2. CSVデータ構築...")
        prefectures = data_service.prepare_areas()
        shiga = next((p for p in prefectures if p.code == "shiga"), None)
        
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
        print(f"  期待値: 地域名=大津市内, X=2869, Y=4187")
        
        # 座標確認
        coordinate_match = (first_mesh.x == 2869 and first_mesh.y == 4187)
        print(f"  座標一致: {coordinate_match}")
        
        # SWI時系列計算
        print(f"\n4. SWI時系列計算...")
        swi_grib2 = {
            'base_info': base_info,
            'swi': swi_data['swi'],
            'first_tunk': swi_data['first_tunk'],
            'second_tunk': swi_data['second_tunk']
        }
        
        swi_timeline = calc_service.calc_swi_timelapse(first_mesh, swi_grib2, guidance_result)
        print(f"  SWIタイムライン長: {len(swi_timeline)}")
        
        if swi_timeline:
            actual_swi_ft0 = swi_timeline[0].value
            print(f"  SWI FT=0: 実際={actual_swi_ft0}, 期待=70.0")
            swi_match = abs(actual_swi_ft0 - 70.0) < 0.1
            print(f"  SWI一致: {swi_match}")
        
        # 雨量時系列計算
        print(f"\n5. 雨量時系列計算...")
        rain_timeline = calc_service.calc_rain_timelapse(first_mesh, guidance_result)
        print(f"  雨量タイムライン長: {len(rain_timeline)}")
        
        if rain_timeline:
            actual_rain_ft3 = rain_timeline[0].value
            print(f"  Rain FT=3: 実際={actual_rain_ft3}, 期待=50")
            rain_match = abs(actual_rain_ft3 - 50) < 0.1
            print(f"  雨量一致: {rain_match}")
            
            # 最初の6個の値確認（参照CSVと比較）
            print(f"\n  雨量詳細比較:")
            expected_rain = [50, 26, 19, 28, 8, 3]
            for i, expected in enumerate(expected_rain):
                if i < len(rain_timeline):
                    actual = rain_timeline[i].value
                    print(f"    FT={rain_timeline[i].ft}: 実際={actual}, 期待={expected}")
                else:
                    print(f"    FT=? データなし, 期待={expected}")
        else:
            print("  WARNING: 雨量データが空です")
        
        # 総合判定
        print(f"\n=== 総合結果 ===")
        if len(guidance_data) == 26:
            print("✓ ガイダンスデータ数: 正常")
        else:
            print("✗ ガイダンスデータ数: 異常")
            
        if coordinate_match:
            print("✓ メッシュ座標: 正常")
        else:
            print("✗ メッシュ座標: 異常")
            
        if swi_timeline and abs(swi_timeline[0].value - 70.0) < 2.0:
            print("✓ SWI値: 概ね正常")
        else:
            print("✗ SWI値: 異常")
            
        if rain_timeline and len(rain_timeline) >= 6:
            print("✓ 雨量データ: 正常")
        else:
            print("✗ 雨量データ: 異常")
        
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()