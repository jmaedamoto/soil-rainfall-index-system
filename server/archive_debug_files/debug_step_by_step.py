#!/usr/bin/env python3
"""
VBAとPythonの計算を1ステップずつ詳細比較
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

def debug_step_by_step():
    """1ステップずつの詳細比較"""
    print("=== Step by Step Debug ===")
    
    # 座標とデータ
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
    
    # インデックス
    swi_index = calc_service.get_data_num(lat, lon, base_info)
    guidance_index = calc_service.get_data_num(lat, lon, guidance_base_info)
    
    print(f"Indexes: swi_index={swi_index}, guidance_index={guidance_index}")
    
    # 初期値（VBAと完全同一）
    initial_swi_raw = swi_data['swi'][swi_index]
    first_tunk_raw = swi_data['first_tunk'][swi_index]
    second_tunk_raw = swi_data['second_tunk'][swi_index]
    
    # VBAの処理
    swi = initial_swi_raw / 10
    first_tunk = first_tunk_raw / 10
    second_tunk = second_tunk_raw / 10
    third_tunk = swi - first_tunk - second_tunk
    
    print(f"\\nVBA initial values:")
    print(f"  swi = {swi}")
    print(f"  first_tunk = {first_tunk}")
    print(f"  second_tunk = {second_tunk}")
    print(f"  third_tunk = {third_tunk}")
    
    # ガイダンス最初の3ステップを手動実装
    results = []
    results.append({'ft': 0, 'value': swi})  # FT=0
    
    for i in range(3):  # FT3, FT6, FT9
        data_set = guidance_data['data'][i]
        values = data_set.get('value', [])
        ft = data_set.get('ft', (i + 1) * 3)
        
        rain = values[guidance_index] if guidance_index < len(values) else 0
        
        print(f"\\n--- Step {i+1}: FT{ft} ---")
        print(f"rain = {rain}")
        print(f"Input to calc_tunk_model:")
        print(f"  s1 = {first_tunk}")
        print(f"  s2 = {second_tunk}")
        print(f"  s3 = {third_tunk}")
        print(f"  t = 3")
        print(f"  r = {rain}")
        
        # 手動でcalc_tunk_model実装（VBA完全再現）
        s1, s2, s3, t, r = first_tunk, second_tunk, third_tunk, 3, rain
        
        # パラメータ
        l1, l2, l3, l4 = 15.0, 60.0, 15.0, 15.0
        a1, a2, a3, a4 = 0.1, 0.15, 0.05, 0.01
        b1, b2, b3 = 0.12, 0.05, 0.01
        
        # 流出量計算（VBA完全同一）
        q1 = 0
        q2 = 0
        q3 = 0
        
        if s1 > l1:
            q1 = q1 + a1 * (s1 - l1)
        if s1 > l2:
            q1 = q1 + a2 * (s1 - l2)
        
        if s2 > l3:
            q2 = a3 * (s2 - l3)
            
        if s3 > l4:
            q3 = a4 * (s3 - l4)
        
        print(f"  Calculated flows: q1={q1}, q2={q2}, q3={q3}")
        
        # 貯留量更新（VBA完全同一）
        s1_new = (1 - b1 * t) * s1 - q1 * t + r
        s2_new = (1 - b2 * t) * s2 - q2 * t + b1 * s1 * t
        s3_new = (1 - b3 * t) * s3 - q3 * t + b2 * s2 * t
        
        swi_value = s1_new + s2_new + s3_new
        
        print(f"  New tank states: s1_new={s1_new}, s2_new={s2_new}, s3_new={s3_new}")
        print(f"  SWI value = {swi_value}")
        
        results.append({'ft': ft, 'value': swi_value})
        
        # VBAのように更新
        first_tunk = s1_new  # tmp_f
        second_tunk = s2_new  # tmp_s
        third_tunk = s3_new  # tmp_t
    
    # CSVと比較
    csv_file = "data/shiga_swi.csv"
    df = pd.read_csv(csv_file, encoding='shift-jis', header=None, skiprows=1)
    first_row = df.iloc[0]
    
    print(f"\\n=== Manual vs CSV Comparison ===")
    for i, result in enumerate(results[1:4]):  # FT3, FT6, FT9
        ft = result['ft']
        python_val = result['value']
        csv_col = 7 + i  # CSV 7列目=FT3
        csv_val = first_row[csv_col] if csv_col < len(first_row) else 0
        
        diff = abs(csv_val - python_val)
        print(f"FT{ft}: Manual={python_val:.6f}, CSV={csv_val:.6f}, Diff={diff:.6f}")

if __name__ == "__main__":
    debug_step_by_step()