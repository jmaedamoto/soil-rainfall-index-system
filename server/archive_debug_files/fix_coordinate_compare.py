#!/usr/bin/env python3
"""
VBA座標計算に合わせた修正版比較テスト
"""

import sys
import os
sys.path.append('.')

import pandas as pd
from services.grib2_service import Grib2Service
import logging

# ログレベルを設定
logging.basicConfig(level=logging.ERROR, format='%(levelname)s: %(message)s')

def vba_get_data_num(lat, lon, base_info):
    """VBA互換の座標計算"""
    y = int((base_info.s_lat / 1000000 - lat) / (base_info.d_lat / 1000000)) + 1
    x = int((lon - base_info.s_lon / 1000000) / (base_info.d_lon / 1000000)) + 1
    return (y - 1) * base_info.x_num + x

def compare_coordinate_calculation():
    """座標計算の比較"""
    print("=== Coordinate Calculation Comparison ===")
    
    # CSV読み込み
    csv_file = "data/shiga_swi.csv"
    df = pd.read_csv(csv_file, encoding='shift-jis', header=None, skiprows=1)
    
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
    
    # VBA式でデータ番号計算
    swi_index_vba = vba_get_data_num(lat, lon, base_info)
    swi_index_python = swi_index_vba - 1  # Python用に0ベースに変換
    
    print(f"VBA data_num: {swi_index_vba} (1-based)")
    print(f"Python index: {swi_index_python} (0-based)")
    
    if 0 <= swi_index_python < len(swi_data['swi']):
        # 生の値を取得
        python_swi_raw = swi_data['swi'][swi_index_python]
        python_first_tunk_raw = swi_data['first_tunk'][swi_index_python]
        python_second_tunk_raw = swi_data['second_tunk'][swi_index_python]
        
        print(f"\\nRaw GRIB2 values:")
        print(f"  SWI (raw): {python_swi_raw}")
        print(f"  First tank (raw): {python_first_tunk_raw}")
        print(f"  Second tank (raw): {python_second_tunk_raw}")
        
        # VBAでは10で割る
        python_swi = python_swi_raw / 10
        python_first_tunk = python_first_tunk_raw / 10
        python_second_tunk = python_second_tunk_raw / 10
        python_third_tunk = python_swi - python_first_tunk - python_second_tunk
        
        print(f"\\nVBA-style values (/10):")
        print(f"  SWI: {python_swi}")
        print(f"  First tank: {python_first_tunk}")
        print(f"  Second tank: {python_second_tunk}")
        print(f"  Third tank: {python_third_tunk}")
        print(f"  Sum: {python_first_tunk + python_second_tunk + python_third_tunk}")
        
        print(f"\\nComparison with CSV:")
        print(f"  CSV SWI: {csv_initial_swi}")
        print(f"  Python SWI: {python_swi}")
        print(f"  Difference: {abs(python_swi - csv_initial_swi)}")
        
        if abs(python_swi - csv_initial_swi) < 0.01:
            print("✓ MATCH!")
            return True
        else:
            print("✗ MISMATCH")
            return False
    else:
        print(f"Index {swi_index_python} out of range (0-{len(swi_data['swi'])-1})")
        return False

if __name__ == "__main__":
    compare_coordinate_calculation()