#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
インデックス計算のデバッグ - VBAとの完全一致確認
"""

import sys
import os
sys.path.append(os.path.dirname(__file__))

from services.grib2_service import Grib2Service
from services.calculation_service import CalculationService
from services.data_service import DataService

def main():
    print("=== インデックス計算デバッグ ===")
    
    guidance_file = "data/guid_msm_grib2_20230602000000_rmax00.bin"
    
    try:
        # サービス初期化
        grib2_service = Grib2Service()
        calc_service = CalculationService()
        data_service = DataService()
        
        # ガイダンスデータ取得
        base_info, guidance_result = grib2_service.unpack_guidance_grib2_from_file(guidance_file)
        guidance_data = guidance_result['data']
        
        print(f"Guidance base_info:")
        print(f"  grid_num: {base_info.grid_num}")
        print(f"  x_num: {base_info.x_num}, y_num: {base_info.y_num}")
        print(f"  s_lat: {base_info.s_lat}, s_lon: {base_info.s_lon}")
        print(f"  d_lat: {base_info.d_lat}, d_lon: {base_info.d_lon}")
        
        # 滋賀県最初のメッシュ
        prefectures = data_service.prepare_areas()
        shiga = next((p for p in prefectures if p.code == "shiga"), None)
        first_mesh = shiga.areas[0].meshes[0]
        
        print(f"\nFirst mesh:")
        print(f"  code: {first_mesh.code}")
        print(f"  lat: {first_mesh.lat}, lon: {first_mesh.lon}")
        print(f"  x: {first_mesh.x}, y: {first_mesh.y}")
        
        # インデックス計算（0-based変換前）
        lat, lon = first_mesh.lat, first_mesh.lon
        
        # VBAの計算を直接再現
        y_vba = int((base_info.s_lat / 1000000 - lat) / (base_info.d_lat / 1000000)) + 1
        x_vba = int((lon - base_info.s_lon / 1000000) / (base_info.d_lon / 1000000)) + 1
        data_num_vba = (y_vba - 1) * base_info.x_num + x_vba
        
        print(f"\nVBA calculation:")
        print(f"  y_vba: {y_vba}, x_vba: {x_vba}")
        print(f"  data_num_vba (1-based): {data_num_vba}")
        print(f"  data_num_python (0-based): {data_num_vba - 1}")
        
        # Python計算サービスでの結果
        guidance_index = calc_service.get_data_num(lat, lon, base_info)
        print(f"  calc_service result: {guidance_index}")
        
        # 配列境界チェック
        print(f"\n配列境界チェック:")
        print(f"  guidance_data length: {len(guidance_data)}")
        if len(guidance_data) > 0:
            first_data_length = len(guidance_data[0]['value'])
            print(f"  first data value length: {first_data_length}")
            print(f"  guidance_index < length: {guidance_index < first_data_length}")
            
            # 実際のデータ値を確認
            if guidance_index < first_data_length:
                actual_value = guidance_data[0]['value'][guidance_index]
                print(f"  actual value at index {guidance_index}: {actual_value}")
                
                # 隣接インデックスも確認
                if guidance_index + 1 < first_data_length:
                    next_value = guidance_data[0]['value'][guidance_index + 1]
                    print(f"  value at index {guidance_index + 1}: {next_value}")
                if guidance_index > 0:
                    prev_value = guidance_data[0]['value'][guidance_index - 1]
                    print(f"  value at index {guidance_index - 1}: {prev_value}")
        
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()