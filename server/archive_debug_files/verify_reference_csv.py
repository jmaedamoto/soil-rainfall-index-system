#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
参照CSVファイルの実際の座標とVBA動作を徹底検証
"""

import sys
import os
sys.path.append(os.path.dirname(__file__))

from services.grib2_service import Grib2Service
from services.calculation_service import CalculationService
from services.data_service import DataService

def meshcode_to_coordinate_vba(code):
    '''VBA meshcode_to_coordinate関数の完全再現'''
    y = int(code[0:2]) * 80 + int(code[4]) * 10 + int(code[6])
    x = int(code[2:4]) * 80 + int(code[5]) * 10 + int(code[7])
    lat = (y + 0.5) * 30 / 3600
    lon = (x + 0.5) * 45 / 3600 + 100
    return lat, lon, x, y

def main():
    print("=== 参照CSV徹底検証 ===")
    
    try:
        # 参照CSVの詳細解析
        print("1. 参照CSVファイル解析")
        with open('data/shiga_rain.csv', 'r', encoding='iso-8859-1') as f:
            first_line = f.readline().strip()
        
        parts = first_line.split(',')
        csv_area_name = parts[0]
        csv_x = int(parts[1])
        csv_y = int(parts[2])
        csv_rain_values = [float(v) for v in parts[3:9]]
        
        print(f"CSV data:")
        print(f"  Area: {csv_area_name}")
        print(f"  X: {csv_x}, Y: {csv_y}")
        print(f"  Rain values: {csv_rain_values}")
        
        # Pythonメッシュデータ
        print("\n2. Pythonメッシュデータ")
        data_service = DataService()
        prefectures = data_service.prepare_areas()
        shiga = next((p for p in prefectures if p.code == "shiga"), None)
        first_mesh = shiga.areas[0].meshes[0]
        
        print(f"Python mesh:")
        print(f"  Area: {shiga.areas[0].name}")
        print(f"  Code: {first_mesh.code}")
        print(f"  X: {first_mesh.x}, Y: {first_mesh.y}")
        print(f"  Lat: {first_mesh.lat}, Lon: {first_mesh.lon}")
        
        # VBA座標計算
        print("\n3. VBA座標変換")
        lat_vba, lon_vba, x_vba, y_vba = meshcode_to_coordinate_vba(first_mesh.code)
        print(f"VBA calculation:")
        print(f"  Code: {first_mesh.code}")
        print(f"  X: {x_vba}, Y: {y_vba}")
        print(f"  Lat: {lat_vba}, Lon: {lon_vba}")
        
        # 座標一致確認
        print("\n4. 座標一致確認")
        x_match = (csv_x == first_mesh.x == x_vba)
        y_match = (csv_y == first_mesh.y == y_vba)
        print(f"X coordinate match: CSV={csv_x}, Python={first_mesh.x}, VBA={x_vba} -> {x_match}")
        print(f"Y coordinate match: CSV={csv_y}, Python={first_mesh.y}, VBA={y_vba} -> {y_match}")
        
        if x_match and y_match:
            print("✓ All coordinates match perfectly!")
        else:
            print("✗ Coordinate mismatch detected!")
        
        # GRIB2データでの実際の計算
        print("\n5. GRIB2データ計算")
        grib2_service = Grib2Service()
        calc_service = CalculationService()
        
        guidance_file = "data/guid_msm_grib2_20230602000000_rmax00.bin"
        base_info, guidance_result = grib2_service.unpack_guidance_grib2_from_file(guidance_file)
        guidance_data = guidance_result['data']
        
        # VBAと完全に同じ計算
        print(f"Base info:")
        print(f"  s_lat: {base_info.s_lat}, s_lon: {base_info.s_lon}")
        print(f"  d_lat: {base_info.d_lat}, d_lon: {base_info.d_lon}")
        print(f"  x_num: {base_info.x_num}, y_num: {base_info.y_num}")
        
        # メッシュ座標でのインデックス計算
        mesh_lat, mesh_lon = first_mesh.lat, first_mesh.lon
        
        # VBAのget_data_num完全再現
        y_calc = int((base_info.s_lat / 1000000 - mesh_lat) / (base_info.d_lat / 1000000)) + 1
        x_calc = int((mesh_lon - base_info.s_lon / 1000000) / (base_info.d_lon / 1000000)) + 1
        data_num = (y_calc - 1) * base_info.x_num + x_calc
        
        print(f"VBA index calculation:")
        print(f"  y_calc: {y_calc}, x_calc: {x_calc}")
        print(f"  data_num: {data_num}")
        
        # 複数のインデックスで値を確認
        print(f"\n6. データ値確認")
        first_guidance = guidance_data[0]
        data_length = len(first_guidance['value'])
        
        print(f"Guidance data length: {data_length}")
        print(f"FT: {first_guidance['ft']}")
        
        # 周辺インデックスの値
        test_indices = [data_num - 5, data_num - 1, data_num, data_num + 1, data_num + 5]
        for idx in test_indices:
            if 0 <= idx < data_length:
                value = first_guidance['value'][idx]
                note = ""
                if value in csv_rain_values:
                    note = f" <- CSV value! (expected at position {csv_rain_values.index(value)})"
                print(f"  Index {idx}: {value}{note}")
        
        # 期待値50を探す
        print(f"\n7. 期待値50の位置検索")
        target_value = 50.0
        for idx in range(max(0, data_num - 20), min(data_length, data_num + 20)):
            value = first_guidance['value'][idx]
            if abs(value - target_value) < 0.1:
                print(f"Found target value {target_value} at index {idx}")
                offset = idx - data_num
                print(f"Offset from calculated index: {offset}")
                
                # このオフセットが全値で一致するかテスト
                print(f"Testing offset for all rain values:")
                for i, expected_rain in enumerate(csv_rain_values):
                    if i < len(guidance_data):
                        test_idx = data_num + offset
                        if 0 <= test_idx < len(guidance_data[i]['value']):
                            actual_value = guidance_data[i]['value'][test_idx]
                            match = abs(actual_value - expected_rain) < 0.1
                            print(f"  FT={guidance_data[i]['ft']}: expected={expected_rain}, actual={actual_value}, match={match}")
                break
        
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()