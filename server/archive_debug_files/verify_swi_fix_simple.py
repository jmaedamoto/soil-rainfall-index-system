#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SWI修正効果の簡単な検証
特定メッシュでの値を直接確認
"""

import sys
import os
sys.path.append(os.path.dirname(__file__))

from services.grib2_service import Grib2Service
from services.calculation_service import CalculationService
from services.data_service import DataService

def main():
    print("=== SWI修正効果の簡単検証 ===")
    
    try:
        # サービス初期化
        grib2_service = Grib2Service()
        calc_service = CalculationService()
        data_service = DataService()
        
        # データ取得
        swi_file = "data/Z__C_RJTD_20230602000000_SRF_GPV_Ggis1km_Psw_Aper10min_ANAL_grib2.bin"
        guidance_file = "data/guid_msm_grib2_20230602000000_rmax00.bin"
        
        swi_base_info, swi_result = grib2_service.unpack_swi_grib2_from_file(swi_file)
        guidance_base_info, guidance_result = grib2_service.unpack_guidance_grib2_from_file(guidance_file)
        
        # 滋賀県データ準備
        prefectures = data_service.prepare_areas()
        shiga = next((p for p in prefectures if p.code == "shiga"), None)
        first_mesh = shiga.areas[0].meshes[0]
        
        print(f"テスト対象メッシュ: {first_mesh.code} (x:{first_mesh.x}, y:{first_mesh.y})")
        
        # SWI計算
        swi_timeline = calc_service.calc_swi_timelapse(first_mesh, swi_result, guidance_result)
        
        print(f"\nSWI計算結果:")
        if swi_timeline:
            ft0_value = None
            for item in swi_timeline:
                if item.ft == 0:
                    ft0_value = item.value
                    print(f"  FT=0: {item.value}")
                    break
                    
            if ft0_value is not None:
                print(f"\n期待値との比較:")
                print(f"  Python計算結果: {ft0_value}")
                print(f"  期待値（CSV）: 93.0")
                print(f"  差異: {abs(ft0_value - 93.0):.1f}")
                
                if abs(ft0_value - 93.0) < 0.1:
                    print("  ✅ 完全一致！")
                elif abs(ft0_value - 93.0) < 5.0:
                    print("  ⚠️ ほぼ一致")
                else:
                    print("  ❌ 大きな差異あり")
                    
                # Rain計算もテスト
                print(f"\nRain計算結果:")
                rain_timeline = calc_service.calc_rain_timelapse(first_mesh, guidance_result)
                if rain_timeline:
                    for i, item in enumerate(rain_timeline[:3]):
                        print(f"  FT={item.ft}: {item.value}")
        else:
            print("SWI計算結果が空です")
            
        # 期待値を参照CSVから取得
        print(f"\n参照CSV確認:")
        try:
            with open('data/shiga_swi.csv', 'r', encoding='iso-8859-1') as f:
                lines = f.readlines()
            
            # 座標一致する行を検索
            for line in lines[1:6]:  # 最初の空行をスキップ
                parts = line.strip().split(',')
                if (len(parts) >= 4 and parts[1] and parts[2] and 
                    int(parts[1]) == first_mesh.x and int(parts[2]) == first_mesh.y):
                    csv_swi = float(parts[3])
                    print(f"  CSV SWI値: {csv_swi}")
                    break
                    
        except Exception as e:
            print(f"  CSV読み取りエラー: {e}")
            
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()