#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ガイダンス解析のシンプルテスト - VBAとの完全一致確認
"""

import sys
import os
sys.path.append(os.path.dirname(__file__))

from services.grib2_service import Grib2Service
from services.calculation_service import CalculationService
from services.data_service import DataService

def main():
    print("=== ガイダンス解析シンプルテスト ===")
    
    guidance_file = "data/guid_msm_grib2_20230602000000_rmax00.bin"
    
    try:
        grib2_service = Grib2Service()
        
        # ガイダンス解析
        base_info, guidance_result = grib2_service.unpack_guidance_grib2_from_file(guidance_file)
        guidance_data = guidance_result['data']
        
        print(f"ガイダンスデータ数: {len(guidance_data)}")
        print(f"期待値: 26個")
        
        if len(guidance_data) == 26:
            print("✅ VBA期待値と一致")
            
            # FT値確認
            ft_values = [item['ft'] for item in guidance_data]
            expected_fts = list(range(3, 79, 3))  # 3,6,9,...,78
            
            if ft_values == expected_fts:
                print("✅ FT値も完全一致")
                
                # 最初のメッシュでテスト
                data_service = DataService()
                calc_service = CalculationService()
                
                # 滋賀県データ構築
                prefectures = data_service.prepare_areas()
                shiga = next((p for p in prefectures if p.code == "shiga"), None)
                
                if shiga and shiga.areas:
                    first_mesh = shiga.areas[0].meshes[0]
                    print(f"テストメッシュ: X={first_mesh.x}, Y={first_mesh.y}")
                    
                    # 雨量時系列計算
                    rain_timeline = calc_service.calc_rain_timelapse(first_mesh, guidance_result)
                    print(f"雨量タイムライン長: {len(rain_timeline)}")
                    
                    if len(rain_timeline) == 26:
                        print("✅ 雨量時系列も26個で正常")
                        print(f"Rain FT=3: {rain_timeline[0].value}")
                        print(f"期待値: 50")
                        
                        if rain_timeline[0].value == 50:
                            print("🎉 完全なVBA一致を実現!")
                        else:
                            print(f"❌ 値が不一致: 実際{rain_timeline[0].value} vs 期待50")
                    else:
                        print(f"❌ 雨量タイムライン長が不正: {len(rain_timeline)}")
                else:
                    print("❌ 滋賀県データ取得失敗")
            else:
                print(f"❌ FT値不一致: 実際{ft_values[:5]}... vs 期待{expected_fts[:5]}...")
        else:
            print(f"❌ データ数不一致: 実際{len(guidance_data)} vs 期待26")
        
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()