#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SWI計算の詳細デバッグ - VBAとの完全一致を実現
FT=0で66.0 vs 70.0の差異原因を特定
"""

import sys
import os
sys.path.append(os.path.dirname(__file__))

from services.grib2_service import Grib2Service
from services.calculation_service import CalculationService
from services.data_service import DataService

def main():
    print("=== SWI計算詳細デバッグ ===")
    
    try:
        # サービス初期化
        grib2_service = Grib2Service()
        calc_service = CalculationService()
        data_service = DataService()
        
        # データ取得
        swi_file = "data/Z__C_RJTD_20230602000000_SRF_GPV_Ggis1km_Psw_Aper10min_ANAL_grib2.bin"
        guidance_file = "data/guid_msm_grib2_20230602000000_rmax00.bin"
        
        print("1. GRIB2データ解析")
        swi_base_info, swi_result = grib2_service.unpack_swi_grib2_from_file(swi_file)
        guidance_base_info, guidance_result = grib2_service.unpack_guidance_grib2_from_file(guidance_file)
        
        print(f"SWI base info: grid_num={swi_base_info.grid_num}, x_num={swi_base_info.x_num}, y_num={swi_base_info.y_num}")
        print(f"Guidance base info: grid_num={guidance_base_info.grid_num}, x_num={guidance_base_info.x_num}, y_num={guidance_base_info.y_num}")
        
        # 滋賀県データ準備
        print("\n2. 滋賀県データ準備")
        prefectures = data_service.prepare_areas()
        shiga = next((p for p in prefectures if p.code == "shiga"), None)
        first_mesh = shiga.areas[0].meshes[0]
        
        print(f"First mesh: code={first_mesh.code}, lat={first_mesh.lat}, lon={first_mesh.lon}")
        print(f"x={first_mesh.x}, y={first_mesh.y}")
        
        # インデックス計算
        print("\n3. インデックス計算比較")
        lat, lon = first_mesh.lat, first_mesh.lon
        
        # SWIインデックス（高解像度）
        swi_index = calc_service.get_data_num(lat, lon, swi_base_info)
        print(f"SWI index: {swi_index}")
        
        # Guidanceインデックス（低解像度）
        guidance_index = calc_service.get_data_num(lat, lon, guidance_base_info)
        print(f"Guidance index: {guidance_index}")
        
        # 実際のSWI値を確認
        print("\n4. SWI実際値確認")
        swi_data = swi_result['data']
        if swi_index < len(swi_data):
            swi_value = swi_data[swi_index]
            print(f"Current SWI value at index {swi_index}: {swi_value}")
        else:
            print(f"ERROR: SWI index {swi_index} out of range (max: {len(swi_data)})")
        
        # 周辺インデックスの値も確認
        print("\n5. SWI周辺値確認")
        for offset in [-10, -5, -2, -1, 0, 1, 2, 5, 10]:
            test_index = swi_index + offset
            if 0 <= test_index < len(swi_data):
                value = swi_data[test_index]
                note = " <- Current" if offset == 0 else ""
                if abs(value - 70.0) < 0.1:
                    note += " <- Expected Value 70.0!"
                print(f"  Index {test_index} (offset {offset:+d}): {value}{note}")
        
        # 70.0に近い値を検索
        print("\n6. 期待値70.0の検索")
        target_value = 70.0
        found_indices = []
        search_range = 50
        
        for offset in range(-search_range, search_range + 1):
            test_index = swi_index + offset
            if 0 <= test_index < len(swi_data):
                value = swi_data[test_index]
                if abs(value - target_value) < 0.1:
                    found_indices.append((test_index, offset, value))
                    print(f"Found target value {value} at index {test_index} (offset: {offset:+d})")
        
        if found_indices:
            # 最初に見つかったインデックスでオフセット修正をテスト
            best_index, best_offset, best_value = found_indices[0]
            print(f"\n7. オフセット修正テスト (offset: {best_offset})")
            
            # 修正されたSWI計算をテスト
            corrected_swi_value = swi_data[best_index]
            print(f"Corrected SWI value: {corrected_swi_value}")
            
            # この修正が他のメッシュにも適用可能かテスト
            print("\n8. 他メッシュでの検証")
            test_meshes = shiga.areas[0].meshes[:5]  # 最初の5メッシュをテスト
            
            for i, mesh in enumerate(test_meshes):
                mesh_swi_index = calc_service.get_data_num(mesh.lat, mesh.lon, swi_base_info)
                corrected_index = mesh_swi_index + best_offset
                
                if 0 <= corrected_index < len(swi_data):
                    original_value = swi_data[mesh_swi_index] if mesh_swi_index < len(swi_data) else None
                    corrected_value = swi_data[corrected_index]
                    print(f"  Mesh {i}: original={original_value}, corrected={corrected_value}")
                else:
                    print(f"  Mesh {i}: corrected index {corrected_index} out of range")
        
        else:
            print("Target value 70.0 not found in search range")
            
        # VBA座標変換との比較
        print("\n9. VBA座標変換比較")
        
        # VBAのmeshcode_to_coordinate実装
        def meshcode_to_coordinate_vba(code):
            y = int(code[0:2]) * 80 + int(code[4]) * 10 + int(code[6])
            x = int(code[2:4]) * 80 + int(code[5]) * 10 + int(code[7])
            lat = (y + 0.5) * 30 / 3600
            lon = (x + 0.5) * 45 / 3600 + 100
            return lat, lon, x, y
        
        lat_vba, lon_vba, x_vba, y_vba = meshcode_to_coordinate_vba(first_mesh.code)
        print(f"VBA coordinate: lat={lat_vba}, lon={lon_vba}, x={x_vba}, y={y_vba}")
        print(f"Python coordinate: lat={first_mesh.lat}, lon={first_mesh.lon}, x={first_mesh.x}, y={first_mesh.y}")
        
        # VBAのget_data_num実装
        y_calc = int((swi_base_info.s_lat / 1000000 - lat_vba) / (swi_base_info.d_lat / 1000000)) + 1
        x_calc = int((lon_vba - swi_base_info.s_lon / 1000000) / (swi_base_info.d_lon / 1000000)) + 1
        data_num_vba = (y_calc - 1) * swi_base_info.x_num + x_calc
        
        print(f"VBA get_data_num: y={y_calc}, x={x_calc}, data_num={data_num_vba}")
        print(f"Python get_data_num: data_num={swi_index}")
        print(f"Difference: {data_num_vba - swi_index}")
        
        # VBA座標でのSWI値
        if 0 <= data_num_vba - 1 < len(swi_data):  # VBAは1-based, Pythonは0-based
            vba_swi_value = swi_data[data_num_vba - 1]
            print(f"SWI value at VBA index {data_num_vba - 1}: {vba_swi_value}")
        
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()