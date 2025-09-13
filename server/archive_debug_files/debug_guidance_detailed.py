#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ガイダンスGRIB2解析の詳細デバッグ - VBAとの完全一致を確認
"""

import sys
import os
sys.path.append(os.path.dirname(__file__))

from services.grib2_service import Grib2Service

def main():
    print("=== ガイダンスGRIB2解析詳細デバッグ ===")
    
    guidance_file = "data/guid_msm_grib2_20230602000000_rmax00.bin"
    print(f"ファイル: {guidance_file}")
    
    try:
        grib2_service = Grib2Service()
        
        # VBAの期待値: 26個のガイダンスデータ
        print("\nVBAの期待値: 26個のガイダンスデータ")
        print("条件: span=3 AND loop_count=2 の時のみデータを取得")
        
        base_info, guidance_result = grib2_service.unpack_guidance_grib2_from_file(guidance_file)
        guidance_data = guidance_result['data']
        
        print(f"\n解析結果:")
        print(f"  取得できたデータ数: {len(guidance_data)}")
        print(f"  base_info.grid_num: {base_info.grid_num}")
        
        if len(guidance_data) > 0:
            print(f"\n最初のデータ:")
            first_data = guidance_data[0]
            print(f"  FT: {first_data['ft']}")
            print(f"  value配列長: {len(first_data['value'])}")
            print(f"  最初の値: {first_data['value'][:5] if len(first_data['value']) >= 5 else first_data['value']}")
            
            print(f"\n全FTリスト:")
            for i, data_item in enumerate(guidance_data):
                print(f"  {i+1}: FT={data_item['ft']}")
        
        # VBAとの比較: 期待値は FT=3,6,9,...,78 の26個
        expected_fts = list(range(3, 79, 3))  # 3,6,9,...,78
        print(f"\n期待されるFT値 ({len(expected_fts)}個): {expected_fts}")
        
        actual_fts = [item['ft'] for item in guidance_data]
        print(f"実際のFT値 ({len(actual_fts)}個): {actual_fts}")
        
        if len(actual_fts) != len(expected_fts):
            print(f"\n❌ ERROR: データ数が一致しません")
            print(f"  期待: {len(expected_fts)}個")
            print(f"  実際: {len(actual_fts)}個")
            print(f"  不足: {len(expected_fts) - len(actual_fts)}個")
            
            missing_fts = set(expected_fts) - set(actual_fts)
            if missing_fts:
                print(f"  欠落しているFT: {sorted(missing_fts)}")
        else:
            print(f"\n✅ データ数は正しい")
            
            if actual_fts == expected_fts:
                print(f"✅ FT値も完全一致")
            else:
                print(f"❌ FT値が一致しません")
                print(f"  違い: {set(expected_fts) ^ set(actual_fts)}")
        
        print(f"\n=== デバッグ完了 ===")
        
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()