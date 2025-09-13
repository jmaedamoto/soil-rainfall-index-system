#!/usr/bin/env python3
"""
Simple SWI comparison test
"""

import sys
import os
sys.path.append('.')

import pandas as pd
from services.grib2_service import Grib2Service
import logging

# ログレベルを設定
logging.basicConfig(level=logging.ERROR, format='%(levelname)s: %(message)s')

def simple_swi_compare():
    """簡単なSWI比較"""
    print("=== Simple SWI Comparison ===")
    
    # CSV読み込み
    csv_file = "data/shiga_swi.csv"
    df = pd.read_csv(csv_file, encoding='shift-jis', header=None, skiprows=1)
    print(f"CSV data: {len(df)} meshes")
    
    # 最初の行を取得
    first_row = df.iloc[0]
    csv_x, csv_y = int(first_row[1]), int(first_row[2])
    csv_initial_swi = first_row[6]
    
    print(f"First mesh: X={csv_x}, Y={csv_y}")
    print(f"CSV initial SWI: {csv_initial_swi}")
    
    # 座標変換（VBAと同じ）
    lat = (csv_y + 0.5) * 30 / 3600
    lon = (csv_x + 0.5) * 45 / 3600 + 100
    print(f"Converted: lat={lat:.6f}, lon={lon:.6f}")
    
    # GRIB2サービス初期化
    grib2_service = Grib2Service()
    
    # SWI GRIB2ファイル読み込み
    swi_file = "data/Z__C_RJTD_20230602000000_SRF_GPV_Ggis1km_Psw_Aper10min_ANAL_grib2.bin"
    print("Loading SWI GRIB2...")
    base_info, swi_data = grib2_service.unpack_swi_grib2_from_file(swi_file)
    
    # データ番号取得
    swi_index = grib2_service.get_data_num(lat, lon, base_info)
    print(f"Data index: {swi_index}")
    
    if swi_index < len(swi_data['swi']):
        # Python処理での初期SWI値
        python_swi_raw = swi_data['swi'][swi_index]
        python_swi_divided = python_swi_raw / 10  # VBAでは10で割る
        
        print(f"Python SWI (raw): {python_swi_raw}")
        print(f"Python SWI (/10): {python_swi_divided}")
        print(f"CSV SWI: {csv_initial_swi}")
        print(f"Difference: {abs(python_swi_divided - csv_initial_swi)}")
        
        if abs(python_swi_divided - csv_initial_swi) < 0.01:
            print("Match!")
        else:
            print("Mismatch - needs correction")
            
        # タンク値も確認
        first_tunk_raw = swi_data['first_tunk'][swi_index]
        second_tunk_raw = swi_data['second_tunk'][swi_index]
        
        first_tunk = first_tunk_raw / 10
        second_tunk = second_tunk_raw / 10
        third_tunk = python_swi_divided - first_tunk - second_tunk
        
        print(f"Tank values:")
        print(f"  First tank: {first_tunk}")
        print(f"  Second tank: {second_tunk}")
        print(f"  Third tank: {third_tunk}")
        print(f"  Sum: {first_tunk + second_tunk + third_tunk}")
    else:
        print("Index out of range")

if __name__ == "__main__":
    simple_swi_compare()