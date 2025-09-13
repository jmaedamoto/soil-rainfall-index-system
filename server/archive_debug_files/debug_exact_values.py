#!/usr/bin/env python3
"""
VBAとPythonの値を完全一致させるため、各ステップの値を詳細に出力
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

def debug_exact_values():
    """各ステップの値を詳細出力"""
    print("=== Exact Values Debug ===")
    
    # テストデータ（座標2869, 4187）
    csv_x, csv_y = 2869, 4187
    lat = (csv_y + 0.5) * 30 / 3600
    lon = (csv_x + 0.5) * 45 / 3600 + 100
    
    print(f"Test coordinates: X={csv_x}, Y={csv_y}")
    print(f"Converted: lat={lat:.10f}, lon={lon:.10f}")
    
    # GRIB2データ読み込み
    grib2_service = Grib2Service()
    calc_service = CalculationService()
    
    swi_file = "data/Z__C_RJTD_20230602000000_SRF_GPV_Ggis1km_Psw_Aper10min_ANAL_grib2.bin"
    guidance_file = "data/guid_msm_grib2_20230602000000_rmax00.bin"
    
    base_info, swi_data = grib2_service.unpack_swi_grib2_from_file(swi_file)
    guidance_base_info, guidance_data = grib2_service.unpack_guidance_grib2_from_file(guidance_file)
    
    # インデックス計算
    swi_index = calc_service.get_data_num(lat, lon, base_info)
    guidance_index = calc_service.get_data_num(lat, lon, guidance_base_info)
    
    print(f"\\nIndex mapping:")
    print(f"  swi_index = {swi_index}")
    print(f"  guidance_index = {guidance_index}")
    
    # 生の初期値
    initial_swi_raw = swi_data['swi'][swi_index]
    first_tunk_raw = swi_data['first_tunk'][swi_index]
    second_tunk_raw = swi_data['second_tunk'][swi_index]
    
    print(f"\\nRaw initial values:")
    print(f"  initial_swi_raw = {initial_swi_raw} (exact: {repr(initial_swi_raw)})")
    print(f"  first_tunk_raw = {first_tunk_raw} (exact: {repr(first_tunk_raw)})")
    print(f"  second_tunk_raw = {second_tunk_raw} (exact: {repr(second_tunk_raw)})")
    
    # 10で割った値
    initial_swi = initial_swi_raw / 10
    first_tunk = first_tunk_raw / 10
    second_tunk = second_tunk_raw / 10
    third_tunk = initial_swi - first_tunk - second_tunk
    
    print(f"\\nProcessed initial values (/10):")
    print(f"  initial_swi = {initial_swi} (exact: {repr(initial_swi)})")
    print(f"  first_tunk = {first_tunk} (exact: {repr(first_tunk)})")
    print(f"  second_tunk = {second_tunk} (exact: {repr(second_tunk)})")
    print(f"  third_tunk = {third_tunk} (exact: {repr(third_tunk)})")
    
    # 初期タンク状態
    current_s1 = first_tunk
    current_s2 = second_tunk  
    current_s3 = third_tunk
    
    print(f"\\nInitial tank states:")
    print(f"  current_s1 = {current_s1} (exact: {repr(current_s1)})")
    print(f"  current_s2 = {current_s2} (exact: {repr(current_s2)})")
    print(f"  current_s3 = {current_s3} (exact: {repr(current_s3)})")
    
    # 最初の数ステップの詳細
    print(f"\\nStep-by-step calculation:")
    
    for i, data_set in enumerate(guidance_data['data'][:5]):
        values = data_set.get('value', [])
        ft = data_set.get('ft', (i + 1) * 3)
        
        if guidance_index < len(values):
            rain = values[guidance_index]
            
            print(f"\\n--- FT{ft} ---")
            print(f"rain = {rain} (exact: {repr(rain)})")
            print(f"Input to calc_tunk_model: s1={current_s1}, s2={current_s2}, s3={current_s3}, dt=3.0, r={rain}")
            
            # タンクモデル計算
            tmp_f, tmp_s, tmp_t = calc_service.calc_tunk_model(current_s1, current_s2, current_s3, 3.0, rain)
            swi_value = tmp_f + tmp_s + tmp_t
            
            print(f"Output from calc_tunk_model: tmp_f={tmp_f}, tmp_s={tmp_s}, tmp_t={tmp_t}")
            print(f"swi_value = {swi_value} (exact: {repr(swi_value)})")
            
            # 状態更新
            current_s1 = tmp_f
            current_s2 = tmp_s
            current_s3 = tmp_t
    
    # CSVとの比較
    csv_file = "data/shiga_swi.csv"
    df = pd.read_csv(csv_file, encoding='shift-jis', header=None, skiprows=1)
    first_row = df.iloc[0]
    
    print(f"\\nCSV comparison:")
    for i in range(6):
        col_index = 7 + i
        if col_index < len(first_row):
            csv_val = first_row[col_index]
            print(f"  Column {col_index}: {csv_val} (exact: {repr(csv_val)})")

if __name__ == "__main__":
    debug_exact_values()