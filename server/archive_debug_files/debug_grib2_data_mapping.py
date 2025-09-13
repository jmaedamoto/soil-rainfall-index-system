#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GRIB2データマッピングの詳細デバッグ
VBAの配列アクセスパターンを解析
"""

import sys
import os
sys.path.append(os.path.dirname(__file__))

from services.grib2_service import Grib2Service
from services.calculation_service import CalculationService
from services.data_service import DataService

def main():
    print("=== GRIB2データマッピングデバッグ ===")
    
    guidance_file = "data/guid_msm_grib2_20230602000000_rmax00.bin"
    
    try:
        # サービス初期化
        grib2_service = Grib2Service()
        calc_service = CalculationService()
        data_service = DataService()
        
        # ガイダンスデータ取得
        base_info, guidance_result = grib2_service.unpack_guidance_grib2_from_file(guidance_file)
        guidance_data = guidance_result['data']
        
        # 滋賀県最初のメッシュ
        prefectures = data_service.prepare_areas()
        shiga = next((p for p in prefectures if p.code == "shiga"), None)
        first_mesh = shiga.areas[0].meshes[0]
        
        print(f"メッシュ情報:")
        print(f"  code: {first_mesh.code}")
        print(f"  lat: {first_mesh.lat}, lon: {first_mesh.lon}")
        print(f"  x: {first_mesh.x}, y: {first_mesh.y}")
        
        # 複数のインデックス計算方法をテスト
        lat, lon = first_mesh.lat, first_mesh.lon
        
        # 方法1: 現在のPython実装（1-based戻り値）
        guidance_index_current = calc_service.get_data_num(lat, lon, base_info)
        
        # 方法2: VBA実装から0-based変換なし
        y_vba = int((base_info.s_lat / 1000000 - lat) / (base_info.d_lat / 1000000)) + 1
        x_vba = int((lon - base_info.s_lon / 1000000) / (base_info.d_lon / 1000000)) + 1
        data_num_vba_1based = (y_vba - 1) * base_info.x_num + x_vba
        data_num_vba_0based = data_num_vba_1based - 1
        
        print(f"\nインデックス計算:")
        print(f"  VBA intermediate: y={y_vba}, x={x_vba}")
        print(f"  VBA 1-based: {data_num_vba_1based}")
        print(f"  VBA 0-based: {data_num_vba_0based}")
        print(f"  Current Python: {guidance_index_current}")
        
        # データ配列の境界
        first_data_length = len(guidance_data[0]['value'])
        print(f"\nデータ配列情報:")
        print(f"  base_info.grid_num: {base_info.grid_num}")
        print(f"  first_data_length: {first_data_length}")
        print(f"  match: {base_info.grid_num == first_data_length}")
        
        # 複数のインデックスでの値を確認
        print(f"\n様々なインデックスでの値:")
        
        test_indices = [
            data_num_vba_0based - 2,
            data_num_vba_0based - 1,
            data_num_vba_0based,
            data_num_vba_0based + 1,
            data_num_vba_0based + 2,
            guidance_index_current - 1,
            guidance_index_current,
            guidance_index_current + 1
        ]
        
        for idx in sorted(set(test_indices)):
            if 0 <= idx < first_data_length:
                value = guidance_data[0]['value'][idx]
                label = ""
                if idx == data_num_vba_0based:
                    label += " [VBA 0-based]"
                if idx == guidance_index_current:
                    label += " [Current Python]"
                print(f"  Index {idx}: {value}{label}")
        
        # 期待値50に最も近い値を探す
        print(f"\n期待値50に最も近い値を検索:")
        target_value = 50
        min_diff = float('inf')
        best_index = -1
        
        for idx in range(max(0, guidance_index_current - 10), 
                        min(first_data_length, guidance_index_current + 10)):
            value = guidance_data[0]['value'][idx]
            diff = abs(value - target_value)
            if diff < min_diff:
                min_diff = diff
                best_index = idx
            if value == target_value:
                print(f"  EXACT MATCH! Index {idx}: {value}")
        
        if best_index >= 0:
            best_value = guidance_data[0]['value'][best_index]
            print(f"  Best match: Index {best_index}: {best_value} (diff: {min_diff})")
            
            # このインデックスを得るためのVBA計算逆算
            # data_num = best_index + 1 (1-basedの場合)
            # (y-1) * x_num + x = data_num
            if base_info.x_num > 0:
                data_num_1based = best_index + 1
                y_calc = ((data_num_1based - 1) // base_info.x_num) + 1
                x_calc = ((data_num_1based - 1) % base_info.x_num) + 1
                
                print(f"  Reverse calculation for exact match:")
                print(f"    Required 1-based data_num: {data_num_1based}")
                print(f"    Required VBA coordinates: y={y_calc}, x={x_calc}")
                print(f"    Current VBA coordinates: y={y_vba}, x={x_vba}")
                print(f"    Difference: dy={y_calc - y_vba}, dx={x_calc - x_vba}")
        
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()