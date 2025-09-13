#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SWI座標計算のVBA完全再現
70.0の期待値を見つけるため座標変換を詳細分析
"""

import sys
import os
sys.path.append(os.path.dirname(__file__))

from services.grib2_service import Grib2Service
from services.data_service import DataService

def meshcode_to_coordinate_vba(code):
    """VBA meshcode_to_coordinate関数の完全再現"""
    y = int(code[0:2]) * 80 + int(code[4]) * 10 + int(code[6])
    x = int(code[2:4]) * 80 + int(code[5]) * 10 + int(code[7])
    lat = (y + 0.5) * 30 / 3600
    lon = (x + 0.5) * 45 / 3600 + 100
    return lat, lon, x, y

def get_data_num_vba(lat, lon, base_info):
    """VBA get_data_num関数の完全再現"""
    y = int((base_info.s_lat / 1000000 - lat) / (base_info.d_lat / 1000000)) + 1
    x = int((lon - base_info.s_lon / 1000000) / (base_info.d_lon / 1000000)) + 1
    data_num = (y - 1) * base_info.x_num + x
    return data_num, x, y

def main():
    print("=== SWI座標計算VBA完全再現 ===")
    
    try:
        # サービス初期化
        grib2_service = Grib2Service()
        data_service = DataService()
        
        # SWIデータ取得
        swi_file = "data/Z__C_RJTD_20230602000000_SRF_GPV_Ggis1km_Psw_Aper10min_ANAL_grib2.bin"
        swi_base_info, swi_result = grib2_service.unpack_swi_grib2_from_file(swi_file)
        swi_data = swi_result['swi']
        
        print(f"SWI base info: grid_num={swi_base_info.grid_num}, x_num={swi_base_info.x_num}, y_num={swi_base_info.y_num}")
        print(f"SWI data length: {len(swi_data)}")
        
        # 滋賀県データ準備
        prefectures = data_service.prepare_areas()
        shiga = next((p for p in prefectures if p.code == "shiga"), None)
        first_mesh = shiga.areas[0].meshes[0]
        
        print(f"\nFirst mesh: code={first_mesh.code}")
        print(f"Python: lat={first_mesh.lat}, lon={first_mesh.lon}, x={first_mesh.x}, y={first_mesh.y}")
        
        # VBA座標変換
        lat_vba, lon_vba, x_vba, y_vba = meshcode_to_coordinate_vba(first_mesh.code)
        print(f"VBA: lat={lat_vba}, lon={lon_vba}, x={x_vba}, y={y_vba}")
        
        # 座標差異確認
        lat_diff = abs(lat_vba - first_mesh.lat)
        lon_diff = abs(lon_vba - first_mesh.lon)
        print(f"座標差異: lat_diff={lat_diff}, lon_diff={lon_diff}")
        
        if lat_diff > 1e-10 or lon_diff > 1e-10:
            print("警告: VBAとPythonの座標に差異があります")
        
        # VBA get_data_num計算
        data_num_vba, x_calc_vba, y_calc_vba = get_data_num_vba(lat_vba, lon_vba, swi_base_info)
        
        print(f"\nVBA get_data_num:")
        print(f"  y_calc={y_calc_vba}, x_calc={x_calc_vba}")
        print(f"  data_num={data_num_vba}")
        
        # Python get_data_num計算（現在の実装）
        from services.calculation_service import CalculationService
        calc_service = CalculationService()
        data_num_python = calc_service.get_data_num(first_mesh.lat, first_mesh.lon, swi_base_info)
        
        print(f"Python get_data_num: {data_num_python}")
        print(f"差異: {data_num_vba - data_num_python}")
        
        # VBAインデックスでのSWI値（1-basedから0-basedに変換）
        vba_index = data_num_vba - 1
        if 0 <= vba_index < len(swi_data):
            vba_swi_value = swi_data[vba_index]
            print(f"\nVBA index {vba_index}でのSWI値: {vba_swi_value} (÷10 = {vba_swi_value/10})")
        
        # Pythonインデックスでの値
        python_index = data_num_python
        if 0 <= python_index < len(swi_data):
            python_swi_value = swi_data[python_index]
            print(f"Python index {python_index}でのSWI値: {python_swi_value} (÷10 = {python_swi_value/10})")
        
        # 期待値700.0を検索
        print(f"\n期待値700.0の検索:")
        target_value = 700.0
        found_indices = []
        
        # 広範囲で検索
        search_center = min(vba_index, python_index)
        search_range = 100
        
        for offset in range(-search_range, search_range + 1):
            test_index = search_center + offset
            if 0 <= test_index < len(swi_data):
                value = swi_data[test_index]
                if abs(value - target_value) < 0.1:
                    found_indices.append((test_index, offset, value))
        
        if found_indices:
            print(f"Found {len(found_indices)} indices with value 700.0:")
            for idx, offset, value in found_indices[:5]:  # 最初の5件を表示
                print(f"  Index {idx} (offset {offset:+d}): {value}")
                
                # このインデックスから逆算してVBA座標を計算
                # data_num = index + 1 (1-based)
                # (y-1) * x_num + x = data_num
                data_num_reverse = idx + 1
                y_reverse = ((data_num_reverse - 1) // swi_base_info.x_num) + 1
                x_reverse = ((data_num_reverse - 1) % swi_base_info.x_num) + 1
                
                print(f"    逆算VBA座標: y={y_reverse}, x={x_reverse}")
                print(f"    期待VBA座標: y={y_calc_vba}, x={x_calc_vba}")
                print(f"    差異: dy={y_reverse - y_calc_vba}, dx={x_reverse - x_calc_vba}")
                
            # 最も近いインデックスを特定
            best_idx, best_offset, best_value = found_indices[0]
            correction_offset = best_offset
            
            print(f"\n修正オフセット候補: {correction_offset}")
            print(f"修正後のSWI値: {best_value/10}")
            
        else:
            print("期待値700.0が見つかりませんでした")
            
            # 周辺値を詳細確認
            print("\n周辺値詳細確認:")
            for offset in range(-20, 21):
                test_index = vba_index + offset
                if 0 <= test_index < len(swi_data):
                    value = swi_data[test_index]
                    note = ""
                    if abs(value - 700.0) < 20:  # 700に近い値
                        note = " <- 700に近い"
                    if offset == 0:
                        note += " <- VBA位置"
                    print(f"  Index {test_index} (offset {offset:+2d}): {value:6.1f}{note}")
        
        # CSVファイルで期待値を再確認
        print(f"\n参照CSV確認:")
        try:
            with open('data/shiga_swi.csv', 'r', encoding='utf-8') as f:
                first_line = f.readline().strip()
            
            parts = first_line.split(',')
            if len(parts) > 3:
                csv_x = int(parts[1])
                csv_y = int(parts[2])
                csv_swi_value = float(parts[3]) if parts[3] else None
                
                print(f"CSV: x={csv_x}, y={csv_y}, SWI={csv_swi_value}")
                print(f"VBA: x={x_vba}, y={y_vba}")
                print(f"座標一致: x={csv_x == x_vba}, y={csv_y == y_vba}")
                
                if csv_swi_value and abs(csv_swi_value - 70.0) < 0.1:
                    print("CSV期待値70.0を確認")
        except Exception as e:
            print(f"CSV読み取りエラー: {e}")
            
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()