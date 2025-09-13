#!/usr/bin/env python3
"""
GRIB2からの初期値読み取りを詳細比較
"""

import sys
import os
sys.path.append('.')

import pandas as pd
from services.grib2_service import Grib2Service
from services.calculation_service import CalculationService
import logging

logging.basicConfig(level=logging.ERROR)

def compare_initial_values():
    """初期値の詳細比較"""
    print("=== Initial Values Comparison ===")
    
    # 座標
    csv_x, csv_y = 2869, 4187
    lat = (csv_y + 0.5) * 30 / 3600
    lon = (csv_x + 0.5) * 45 / 3600 + 100
    
    # GRIB2データ読み込み
    grib2_service = Grib2Service()
    calc_service = CalculationService()
    
    swi_file = "data/Z__C_RJTD_20230602000000_SRF_GPV_Ggis1km_Psw_Aper10min_ANAL_grib2.bin"
    
    base_info, swi_data = grib2_service.unpack_swi_grib2_from_file(swi_file)
    
    # インデックス
    swi_index = calc_service.get_data_num(lat, lon, base_info)
    
    print(f"Coordinate: lat={lat:.10f}, lon={lon:.10f}")
    print(f"SWI index: {swi_index}")
    
    # Pythonでの初期値
    if (swi_index < len(swi_data['swi']) and
        swi_index < len(swi_data['first_tunk']) and
        swi_index < len(swi_data['second_tunk'])):
        
        initial_swi_raw = swi_data['swi'][swi_index]
        first_tunk_raw = swi_data['first_tunk'][swi_index]  
        second_tunk_raw = swi_data['second_tunk'][swi_index]
        
        print(f"\\nPython raw values:")
        print(f"  initial_swi_raw = {initial_swi_raw} (type: {type(initial_swi_raw)})")
        print(f"  first_tunk_raw = {first_tunk_raw} (type: {type(first_tunk_raw)})")
        print(f"  second_tunk_raw = {second_tunk_raw} (type: {type(second_tunk_raw)})")
        
        # VBAと同じ処理（10で割る）
        initial_swi = initial_swi_raw / 10
        first_tunk = first_tunk_raw / 10
        second_tunk = second_tunk_raw / 10
        third_tunk = initial_swi - first_tunk - second_tunk
        
        print(f"\\nPython processed values (÷10):")
        print(f"  initial_swi = {initial_swi:.15f}")
        print(f"  first_tunk = {first_tunk:.15f}")
        print(f"  second_tunk = {second_tunk:.15f}")
        print(f"  third_tunk = {third_tunk:.15f}")
        
        # CSVでのFT0値と比較（これはinitial_swiに相当するはず）
        csv_file = "data/shiga_swi.csv"
        df = pd.read_csv(csv_file, encoding='shift-jis', header=None, skiprows=1)
        first_row = df.iloc[0]
        
        # CSVの6列目が初期値？（推測）
        if len(first_row) > 6:
            csv_initial = first_row[6]  # 6列目をテスト
            print(f"\\nCSV comparison (column 6 as initial?):")
            print(f"  CSV column 6 = {csv_initial:.15f}")
            print(f"  Python initial_swi = {initial_swi:.15f}")
            print(f"  Difference = {abs(csv_initial - initial_swi):.15f}")
        
        # 近隣インデックスの値も確認
        print(f"\\nNeighboring values:")
        for offset in [-2, -1, 0, 1, 2]:
            test_index = swi_index + offset
            if 0 <= test_index < len(swi_data['swi']):
                swi_val = swi_data['swi'][test_index]
                first_val = swi_data['first_tunk'][test_index]
                second_val = swi_data['second_tunk'][test_index]
                print(f"  Index {test_index}: SWI={swi_val}, F={first_val}, S={second_val}")
        
        # 最初のFT3計算を手動実行
        print(f"\\n=== First FT3 calculation ===")
        guidance_file = "data/guid_msm_grib2_20230602000000_rmax00.bin"
        guidance_base_info, guidance_data = grib2_service.unpack_guidance_grib2_from_file(guidance_file)
        
        guidance_index = calc_service.get_data_num(lat, lon, guidance_base_info)
        
        if len(guidance_data['data']) > 0:
            first_guidance = guidance_data['data'][0]
            rain = first_guidance['value'][guidance_index] if guidance_index < len(first_guidance['value']) else 0
            ft = first_guidance['ft']
            
            print(f"First guidance: FT={ft}, rain={rain}")
            
            # 手動でタンクモデル計算
            s1, s2, s3 = first_tunk, second_tunk, third_tunk
            dt = 3
            
            # VBAのパラメータ
            L1, L2, L3, L4 = 15.0, 60.0, 15.0, 15.0
            A1, A2, A3, A4 = 0.1, 0.15, 0.05, 0.01
            B1, B2, B3 = 0.12, 0.05, 0.01
            
            # 流出量計算
            q1 = 0
            if s1 > L1:
                q1 += A1 * (s1 - L1)
            if s1 > L2:
                q1 += A2 * (s1 - L2)
                
            q2 = 0
            if s2 > L3:
                q2 = A3 * (s2 - L3)
                
            q3 = 0
            if s3 > L4:
                q3 = A4 * (s3 - L4)
            
            # 貯留量更新
            s1_new = (1 - B1 * dt) * s1 - q1 * dt + rain
            s2_new = (1 - B2 * dt) * s2 - q2 * dt + B1 * s1 * dt
            s3_new = (1 - B3 * dt) * s3 - q3 * dt + B2 * s2 * dt
            
            swi_ft3 = s1_new + s2_new + s3_new
            
            print(f"Manual FT3 calculation:")
            print(f"  Input: s1={s1}, s2={s2}, s3={s3}, rain={rain}")
            print(f"  Flows: q1={q1:.6f}, q2={q2:.6f}, q3={q3:.6f}")
            print(f"  Output: s1_new={s1_new:.6f}, s2_new={s2_new:.6f}, s3_new={s3_new:.6f}")
            print(f"  FT3 SWI = {swi_ft3:.6f}")
            
            # CSVのFT3値と比較
            csv_ft3 = first_row[7] if len(first_row) > 7 else 0
            print(f"  CSV FT3 = {csv_ft3:.6f}")
            print(f"  Difference = {abs(csv_ft3 - swi_ft3):.6f}")
    else:
        print("Index out of range!")

if __name__ == "__main__":
    compare_initial_values()