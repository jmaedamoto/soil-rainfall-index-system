#!/usr/bin/env python3
"""
フル計算テスト - CSV結果との完全一致を目指す
"""

import sys
import os
sys.path.append('.')

import pandas as pd
from services.grib2_service import Grib2Service
from services.calculation_service import CalculationService
from models import Mesh
import logging

# ログレベルを設定
logging.basicConfig(level=logging.ERROR)

def test_full_calculation():
    """フル計算テスト"""
    print("=== Full Calculation Test ===")
    
    # CSVファイル読み込み
    csv_file = "data/shiga_swi.csv"
    df = pd.read_csv(csv_file, encoding='shift-jis', header=None, skiprows=1)
    
    # サービス初期化
    grib2_service = Grib2Service()
    calc_service = CalculationService()
    
    # GRIB2ファイル読み込み
    swi_file = "data/Z__C_RJTD_20230602000000_SRF_GPV_Ggis1km_Psw_Aper10min_ANAL_grib2.bin"
    guidance_file = "data/guid_msm_grib2_20230602000000_rmax00.bin"
    
    print("Loading GRIB2 files...")
    base_info, swi_data = grib2_service.unpack_swi_grib2_from_file(swi_file)
    guidance_base_info, guidance_data = grib2_service.unpack_guidance_grib2_from_file(guidance_file)
    
    print(f"SWI data: {len(swi_data['swi'])} values")
    print(f"Guidance data: {len(guidance_data['data'])} time series")
    
    # 最初の3メッシュでテスト
    matches = 0
    mismatches = 0
    
    for i in range(min(3, len(df))):
        row = df.iloc[i]
        area_name = row[0]
        csv_x, csv_y = int(row[1]), int(row[2])
        
        # 座標変換
        lat = (csv_y + 0.5) * 30 / 3600
        lon = (csv_x + 0.5) * 45 / 3600 + 100
        
        print(f"\\nMesh {i+1}: {area_name} (X={csv_x}, Y={csv_y})")
        print(f"  Coordinates: lat={lat:.6f}, lon={lon:.6f}")
        
        try:
            # Meshオブジェクト作成
            mesh = Mesh(
                area_name=str(area_name),
                code="",
                lat=lat,
                lon=lon,
                x=csv_x,
                y=csv_y,
                advisary_bound=int(row[3]) if pd.notna(row[3]) else 0,
                warning_bound=int(row[4]) if pd.notna(row[4]) else 0,
                dosyakei_bound=int(row[5]) if pd.notna(row[5]) else 0,
                swi=[],
                rain=[]
            )
            
            # Python計算実行
            swi_timeline = calc_service.calc_swi_timelapse(mesh, swi_data, guidance_data)
            
            if swi_timeline:
                print(f"  Python calculation successful: {len(swi_timeline)} time points")
                
                # CSVとの比較（CSV 7列目=FT3, 8列目=FT6, ...）
                csv_values = []
                python_values = []
                
                # PythonのFT3以降の値とCSVを比較 (FT0はスキップ)
                python_ft_values = {t.ft: t.value for t in swi_timeline}
                
                for j, expected_ft in enumerate([3, 6, 9, 12, 15]):  # CSVの7列目からの対応FT
                    csv_col = 7 + j
                    if csv_col < len(row) and expected_ft in python_ft_values:
                        csv_val = row[csv_col] if pd.notna(row[csv_col]) else 0.0
                        python_val = python_ft_values[expected_ft]
                        
                        csv_values.append(csv_val)
                        python_values.append(python_val)
                        
                        print(f"    FT{expected_ft}: CSV={csv_val:.2f}, Python={python_val:.2f}, Diff={abs(csv_val-python_val):.2f}")
                        
                        if abs(csv_val - python_val) < 0.01:
                            matches += 1
                        else:
                            mismatches += 1
                
                # 全体の傾向を確認
                if csv_values and python_values:
                    csv_avg = sum(csv_values) / len(csv_values)
                    python_avg = sum(python_values) / len(python_values)
                    print(f"  Average: CSV={csv_avg:.2f}, Python={python_avg:.2f}")
            else:
                print(f"  Python calculation failed")
                mismatches += 5  # 5個の時系列ポイントがすべて失敗
                
        except Exception as e:
            print(f"  Error: {e}")
            mismatches += 5
    
    print(f"\\n=== Results ===")
    print(f"Matches: {matches}")
    print(f"Mismatches: {mismatches}")
    if matches + mismatches > 0:
        accuracy = matches / (matches + mismatches) * 100
        print(f"Accuracy: {accuracy:.1f}%")
        
        if accuracy > 95:
            print("Excellent match!")
        elif accuracy > 80:
            print("Good match, minor adjustments needed")
        else:
            print("Significant differences, major corrections needed")
    
    return matches, mismatches

if __name__ == "__main__":
    test_full_calculation()