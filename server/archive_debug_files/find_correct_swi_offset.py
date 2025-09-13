#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
正しいSWIオフセットを特定
期待値93.0に一致するオフセットを検索
"""

import sys
import os
sys.path.append(os.path.dirname(__file__))

from services.grib2_service import Grib2Service
from services.calculation_service import CalculationService
from services.data_service import DataService

def main():
    print("=== 正しいSWIオフセット特定 ===")
    
    try:
        # サービス初期化
        grib2_service = Grib2Service()
        calc_service = CalculationService()
        data_service = DataService()
        
        # データ取得
        swi_file = "data/Z__C_RJTD_20230602000000_SRF_GPV_Ggis1km_Psw_Aper10min_ANAL_grib2.bin"
        swi_base_info, swi_result = grib2_service.unpack_swi_grib2_from_file(swi_file)
        swi_data = swi_result['swi']
        
        # 滋賀県データ準備
        prefectures = data_service.prepare_areas()
        shiga = next((p for p in prefectures if p.code == "shiga"), None)
        first_mesh = shiga.areas[0].meshes[0]  # 座標2869,4187
        
        print(f"テスト対象メッシュ: code={first_mesh.code}, x={first_mesh.x}, y={first_mesh.y}")
        
        # 基本インデックス計算
        base_index = calc_service.get_data_num(first_mesh.lat, first_mesh.lon, swi_base_info)
        print(f"基本インデックス: {base_index}")
        
        # 期待値93.0を検索（SWI CSVから）
        print(f"\n期待値930.0（93.0×10）の検索:")
        target_value = 930.0
        found_offsets = []
        
        # 広範囲で検索
        search_range = 200
        for offset in range(-search_range, search_range + 1):
            test_index = base_index + offset
            if 0 <= test_index < len(swi_data):
                value = swi_data[test_index]
                if abs(value - target_value) < 0.1:
                    found_offsets.append((offset, test_index, value))
                    print(f"  オフセット {offset:+4d}: インデックス {test_index}, 値 {value} (÷10 = {value/10})")
        
        if not found_offsets:
            print("期待値930.0が見つかりませんでした")
            # 近似値を検索
            print(f"\n930.0に近い値を検索:")
            close_values = []
            for offset in range(-search_range, search_range + 1):
                test_index = base_index + offset
                if 0 <= test_index < len(swi_data):
                    value = swi_data[test_index]
                    diff = abs(value - target_value)
                    if diff < 50:  # 930±50の範囲
                        close_values.append((offset, test_index, value, diff))
            
            # 差異でソート
            close_values.sort(key=lambda x: x[3])
            
            print("930.0に最も近い値:")
            for offset, test_index, value, diff in close_values[:10]:
                print(f"  オフセット {offset:+4d}: 値 {value} (差異 {diff:.1f}, ÷10 = {value/10})")
                
        else:
            print(f"\n{len(found_offsets)}個の候補が見つかりました")
            
            # 最適オフセットを選択（最初に見つかったもの）
            best_offset, best_index, best_value = found_offsets[0]
            
            print(f"\n最適オフセット: {best_offset}")
            print(f"修正後のSWI値: {best_value/10}")
            
            # 他のメッシュでも検証
            print(f"\n他のメッシュでの検証:")
            test_meshes = [
                shiga.areas[0].meshes[1],  # 2番目のメッシュ
                shiga.areas[0].meshes[2],  # 3番目のメッシュ
                shiga.areas[0].meshes[3],  # 4番目のメッシュ
            ]
            
            # SWI CSVから期待値を手動設定（headコマンドの結果から）
            expected_values = [90.0, 90.0, 90.0]  # 2-4行目の期待値
            
            for i, mesh in enumerate(test_meshes):
                mesh_index = calc_service.get_data_num(mesh.lat, mesh.lon, swi_base_info)
                corrected_index = mesh_index + best_offset
                
                if 0 <= corrected_index < len(swi_data):
                    corrected_value = swi_data[corrected_index] / 10
                    expected = expected_values[i] if i < len(expected_values) else "N/A"
                    match = abs(corrected_value - expected) < 0.1 if isinstance(expected, float) else False
                    print(f"  メッシュ{i+2}: 修正値={corrected_value}, 期待値={expected}, 一致={match}")
                else:
                    print(f"  メッシュ{i+2}: インデックス範囲外")
            
            # 現在の-49オフセットとの比較
            print(f"\n現在の-49オフセットとの比較:")
            current_offset = -49
            current_value = swi_data[base_index + current_offset] / 10 if 0 <= base_index + current_offset < len(swi_data) else None
            print(f"  -49オフセット値: {current_value}")
            print(f"  新オフセット値: {best_value/10}")
            print(f"  期待値93.0に対する精度改善: {abs(current_value - 93.0):.1f} -> {abs(best_value/10 - 93.0):.1f}")
            
        # 期待値90.0も検索
        print(f"\n期待値900.0（90.0×10）の検索:")
        target_value_90 = 900.0
        found_90_offsets = []
        
        for offset in range(-search_range, search_range + 1):
            test_index = base_index + offset
            if 0 <= test_index < len(swi_data):
                value = swi_data[test_index]
                if abs(value - target_value_90) < 0.1:
                    found_90_offsets.append((offset, test_index, value))
        
        print(f"期待値900.0が見つかった場所: {len(found_90_offsets)}個")
        for offset, test_index, value in found_90_offsets[:5]:
            print(f"  オフセット {offset:+4d}: 値 {value} (÷10 = {value/10})")
            
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()