#!/usr/bin/env python3
"""
CSVの座標とPython計算の座標を正確にマッチング
"""

import sys
import os
sys.path.append('.')

import pandas as pd
from services.grib2_service import Grib2Service
from services.calculation_service import CalculationService
from models import Mesh
import logging

logging.basicConfig(level=logging.ERROR)

def debug_csv_exact_match():
    """CSVの正確な行とPython計算をマッチング"""
    print("=== CSV Exact Match Debug ===")
    
    # CSV読み込み
    csv_file = "data/shiga_swi.csv"
    df = pd.read_csv(csv_file, encoding='shift-jis', header=None, skiprows=1)
    
    print("CSV file contents (first 5 rows):")
    for i in range(min(5, len(df))):
        row = df.iloc[i]
        area_name = row[0] if pd.notna(row[0]) else "N/A"
        x = int(row[1]) if pd.notna(row[1]) else 0
        y = int(row[2]) if pd.notna(row[2]) else 0
        
        # SWI時系列値（7列目以降）
        swi_values = []
        for j in range(7, min(13, len(row))):
            if pd.notna(row[j]):
                swi_values.append(f"{row[j]:.6f}")
            else:
                swi_values.append("N/A")
        
        print(f"  Row {i}: {area_name} X={x} Y={y} SWI=[{', '.join(swi_values)}]")
    
    # 座標(2869, 4187)の行を探す
    target_x, target_y = 2869, 4187
    matching_rows = []
    
    for i, row in df.iterrows():
        if int(row[1]) == target_x and int(row[2]) == target_y:
            matching_rows.append((i, row))
    
    print(f"\\nRows matching coordinates X={target_x}, Y={target_y}: {len(matching_rows)}")
    
    if matching_rows:
        row_index, row = matching_rows[0]  # 最初のマッチ行を使用
        
        print(f"Using row {row_index}:")
        area_name = row[0]
        print(f"  Area: {area_name}")
        print(f"  Coordinates: X={int(row[1])}, Y={int(row[2])}")
        
        # CSV値を抽出
        csv_swi_values = []
        for j in range(7, 13):  # FT3, FT6, FT9, FT12, FT15, FT18
            if j < len(row) and pd.notna(row[j]):
                csv_swi_values.append(row[j])
            else:
                csv_swi_values.append(None)
        
        print(f"  CSV SWI values: {csv_swi_values}")
        
        # Pythonで同じ座標を計算
        lat = (target_y + 0.5) * 30 / 3600
        lon = (target_x + 0.5) * 45 / 3600 + 100
        
        print(f"\\nPython calculation for same coordinates:")
        print(f"  lat={lat:.10f}, lon={lon:.10f}")
        
        # GRIB2データとPython計算
        grib2_service = Grib2Service()
        calc_service = CalculationService()
        
        swi_file = "data/Z__C_RJTD_20230602000000_SRF_GPV_Ggis1km_Psw_Aper10min_ANAL_grib2.bin"
        guidance_file = "data/guid_msm_grib2_20230602000000_rmax00.bin"
        
        base_info, swi_data = grib2_service.unpack_swi_grib2_from_file(swi_file)
        guidance_base_info, guidance_data = grib2_service.unpack_guidance_grib2_from_file(guidance_file)
        
        mesh = Mesh(
            area_name=str(area_name),
            code="",
            lat=lat,
            lon=lon,
            x=target_x,
            y=target_y,
            advisary_bound=100,
            warning_bound=150,
            dosyakei_bound=200,
            swi=[],
            rain=[]
        )
        
        swi_timeline = calc_service.calc_swi_timelapse(mesh, swi_data, guidance_data)
        
        # FT3以降の値を抽出
        python_swi_values = {}
        for t in swi_timeline:
            if t.ft >= 3:  # FT3以降のみ
                python_swi_values[t.ft] = t.value
        
        print(f"  Python SWI timeline: {[(ft, f'{val:.6f}') for ft, val in list(python_swi_values.items())[:6]]}")
        
        # 詳細比較
        print(f"\\nDetailed comparison:")
        expected_fts = [3, 6, 9, 12, 15, 18]
        for i, ft in enumerate(expected_fts):
            if i < len(csv_swi_values) and csv_swi_values[i] is not None:
                csv_val = csv_swi_values[i]
                python_val = python_swi_values.get(ft, 0.0)
                diff = abs(csv_val - python_val)
                
                print(f"  FT{ft}: CSV={csv_val:.6f}, Python={python_val:.6f}, Diff={diff:.6f}")
    else:
        print(f"No matching rows found for coordinates X={target_x}, Y={target_y}")

if __name__ == "__main__":
    debug_csv_exact_match()