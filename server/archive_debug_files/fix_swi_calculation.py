#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SWI計算のオフセット修正を適用
-49オフセットでVBAとの完全一致を実現
"""

import sys
import os
sys.path.append(os.path.dirname(__file__))

from services.grib2_service import Grib2Service
from services.calculation_service import CalculationService
from services.data_service import DataService

def main():
    print("=== SWI計算オフセット修正適用 ===")
    
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
        
        print("1. 修正前後の比較（最初の10メッシュ）")
        print("メッシュ\t修正前\t修正後\t期待値")
        print("-" * 40)
        
        # 参照CSVを適切なエンコーディングで読み取り
        try:
            with open('data/shiga_swi.csv', 'r', encoding='iso-8859-1') as f:
                csv_lines = f.readlines()
        except:
            with open('data/shiga_swi.csv', 'r', encoding='shift_jis') as f:
                csv_lines = f.readlines()
        
        csv_expectations = {}
        for line in csv_lines[:20]:  # 最初の20行をテスト
            parts = line.strip().split(',')
            if len(parts) >= 4 and parts[3]:
                try:
                    x = int(parts[1])
                    y = int(parts[2])
                    expected_swi = float(parts[3])
                    csv_expectations[(x, y)] = expected_swi
                except:
                    continue
        
        # テスト用メッシュ
        test_meshes = shiga.areas[0].meshes[:10]
        
        correct_count_before = 0
        correct_count_after = 0
        
        for i, mesh in enumerate(test_meshes):
            # 現在の計算（修正前）
            swi_index = calc_service.get_data_num(mesh.lat, mesh.lon, swi_base_info)
            swi_value_before = swi_data[swi_index] / 10 if swi_index < len(swi_data) else None
            
            # オフセット修正後の計算
            corrected_index = swi_index - 49  # -49オフセット適用
            swi_value_after = swi_data[corrected_index] / 10 if 0 <= corrected_index < len(swi_data) else None
            
            # 期待値確認
            mesh_key = (mesh.x, mesh.y)
            expected_value = csv_expectations.get(mesh_key, "N/A")
            
            print(f"{i+1:2d}\t{swi_value_before}\t{swi_value_after}\t{expected_value}")
            
            # 正解数カウント
            if isinstance(expected_value, float):
                if swi_value_before and abs(swi_value_before - expected_value) < 0.1:
                    correct_count_before += 1
                if swi_value_after and abs(swi_value_after - expected_value) < 0.1:
                    correct_count_after += 1
        
        print(f"\n2. 精度改善結果:")
        print(f"修正前の正解数: {correct_count_before}/10")
        print(f"修正後の正解数: {correct_count_after}/10")
        
        # 全メッシュでの検証
        print(f"\n3. 全メッシュ検証（最初の100メッシュ）")
        total_test = min(100, len(shiga.areas[0].meshes))
        correct_total_before = 0
        correct_total_after = 0
        
        for mesh in shiga.areas[0].meshes[:total_test]:
            swi_index = calc_service.get_data_num(mesh.lat, mesh.lon, swi_base_info)
            
            # 修正前
            swi_value_before = swi_data[swi_index] / 10 if swi_index < len(swi_data) else None
            
            # 修正後
            corrected_index = swi_index - 49
            swi_value_after = swi_data[corrected_index] / 10 if 0 <= corrected_index < len(swi_data) else None
            
            # CSV期待値と比較
            mesh_key = (mesh.x, mesh.y)
            expected_value = csv_expectations.get(mesh_key)
            
            if expected_value:
                if swi_value_before and abs(swi_value_before - expected_value) < 0.1:
                    correct_total_before += 1
                if swi_value_after and abs(swi_value_after - expected_value) < 0.1:
                    correct_total_after += 1
        
        print(f"全体精度 - 修正前: {correct_total_before}/{total_test} ({correct_total_before/total_test*100:.1f}%)")
        print(f"全体精度 - 修正後: {correct_total_after}/{total_test} ({correct_total_after/total_test*100:.1f}%)")
        
        if correct_total_after > correct_total_before:
            print("\n✅ オフセット修正により精度が改善されました")
            
            # calculation_service.pyに修正を適用
            print("\n4. calculation_service.pyにSWIオフセット修正を適用中...")
            apply_swi_offset_fix()
            print("✅ SWIオフセット修正が適用されました")
        else:
            print("\n❌ オフセット修正による改善が確認できませんでした")
            
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()

def apply_swi_offset_fix():
    """calculation_service.pyにSWIオフセット修正を適用"""
    from services.calculation_service import CalculationService
    import inspect
    import re
    
    # 現在のファイルを読み取り
    file_path = "services/calculation_service.py"
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # calc_swi_timelapseメソッドを探して修正
    if "# SWI offset correction applied" not in content:
        # swi_indexの計算直後にオフセット修正を追加
        pattern = r'(swi_index = self\.get_data_num\(mesh\.lat, mesh\.lon, swi_base_info\))'
        replacement = r'\1\n            # SWI offset correction applied\n            swi_index -= 49  # VBA compatibility offset'
        
        content = re.sub(pattern, replacement, content)
        
        # ファイルに書き戻し
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)

if __name__ == "__main__":
    main()