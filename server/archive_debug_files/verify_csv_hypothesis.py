#!/usr/bin/env python3
"""
CSV構造の仮説検証
7列目 = FT=3, 8列目 = FT=6 仮説をテスト
"""

import sys
import os
sys.path.append('.')

import pandas as pd
from services.grib2_service import Grib2Service
from services.calculation_service import CalculationService
from models import Mesh

def verify_csv_hypothesis():
    """CSV構造仮説の検証"""
    print("=== CSV Structure Hypothesis Verification ===")
    print("Hypothesis: CSV column 7 = FT3, column 8 = FT6, etc.")
    
    # テストデータ
    csv_x, csv_y = 2869, 4187
    lat = (csv_y + 0.5) * 30 / 3600
    lon = (csv_x + 0.5) * 45 / 3600 + 100
    
    # GRIB2データ読み込み
    grib2_service = Grib2Service()
    calc_service = CalculationService()
    
    swi_file = "data/Z__C_RJTD_20230602000000_SRF_GPV_Ggis1km_Psw_Aper10min_ANAL_grib2.bin"
    guidance_file = "data/guid_msm_grib2_20230602000000_rmax00.bin"
    
    base_info, swi_data = grib2_service.unpack_swi_grib2_from_file(swi_file)
    guidance_base_info, guidance_data = grib2_service.unpack_guidance_grib2_from_file(guidance_file)
    
    # Python計算実行
    mesh = Mesh(
        area_name="test",
        code="",
        lat=lat,
        lon=lon,
        x=csv_x,
        y=csv_y,
        advisary_bound=100,
        warning_bound=150,
        dosyakei_bound=200,
        swi=[],
        rain=[]
    )
    
    swi_timeline = calc_service.calc_swi_timelapse(mesh, swi_data, guidance_data)
    
    # CSV読み込み
    csv_file = "data/shiga_swi.csv"
    df = pd.read_csv(csv_file, encoding='shift-jis', header=None, skiprows=1)
    first_row = df.iloc[0]
    
    print(f"\\nPython timeline:")
    ft_to_value = {}
    for t in swi_timeline:
        ft_to_value[t.ft] = t.value
        print(f"  FT{t.ft}: {t.value:.6f}")
    
    print(f"\\nCSV values (columns 7-12):")
    csv_values = []
    for i in range(6):  # 7列目から12列目
        col_index = 7 + i
        if col_index < len(first_row):
            val = first_row[col_index]
            csv_values.append(val)
            print(f"  Column {col_index}: {val}")
    
    print(f"\\n=== Hypothesis Testing ===")
    
    # 仮説1: 7列目=FT0, 8列目=FT3, ...
    print("\\nHypothesis 1: CSV column 7=FT0, 8=FT3, 9=FT6, ...")
    hypotheses = [
        (7, 0),
        (8, 3), 
        (9, 6),
        (10, 9),
        (11, 12),
        (12, 15)
    ]
    
    total_diff_h1 = 0
    for col, ft in hypotheses:
        if col < len(first_row) and ft in ft_to_value:
            csv_val = first_row[col]
            python_val = ft_to_value[ft]
            diff = abs(csv_val - python_val)
            total_diff_h1 += diff
            print(f"  Col{col} vs FT{ft}: CSV={csv_val:.2f}, Python={python_val:.2f}, Diff={diff:.2f}")
    
    # 仮説2: 7列目=FT3, 8列目=FT6, ... (FT0が省略されている)
    print("\\nHypothesis 2: CSV column 7=FT3, 8=FT6, 9=FT9, ... (FT0 omitted)")
    hypotheses_2 = [
        (7, 3),
        (8, 6), 
        (9, 9),
        (10, 12),
        (11, 15),
        (12, 18)
    ]
    
    total_diff_h2 = 0
    for col, ft in hypotheses_2:
        if col < len(first_row) and ft in ft_to_value:
            csv_val = first_row[col]
            python_val = ft_to_value[ft]
            diff = abs(csv_val - python_val)
            total_diff_h2 += diff
            print(f"  Col{col} vs FT{ft}: CSV={csv_val:.2f}, Python={python_val:.2f}, Diff={diff:.2f}")
    
    print(f"\\n=== Hypothesis Comparison ===")
    print(f"Hypothesis 1 total difference: {total_diff_h1:.2f}")
    print(f"Hypothesis 2 total difference: {total_diff_h2:.2f}")
    
    if total_diff_h1 < total_diff_h2:
        print("→ Hypothesis 1 (7col=FT0) is better")
        return 1
    else:
        print("→ Hypothesis 2 (7col=FT3) is better")
        return 2

if __name__ == "__main__":
    verify_csv_hypothesis()