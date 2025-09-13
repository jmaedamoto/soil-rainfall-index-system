#!/usr/bin/env python3
"""
座標変換の詳細分析と丸め処理の影響調査
"""

import sys
import os
sys.path.append('.')

from services.grib2_service import Grib2Service
from services.calculation_service import CalculationService
import logging

logging.basicConfig(level=logging.ERROR)

def debug_coordinate_rounding():
    """座標変換と丸め処理の詳細分析"""
    print("=== Coordinate Rounding Analysis ===")
    
    # 座標
    csv_x, csv_y = 2869, 4187
    lat = (csv_y + 0.5) * 30 / 3600
    lon = (csv_x + 0.5) * 45 / 3600 + 100
    
    print(f"Input: X={csv_x}, Y={csv_y}")
    print(f"Lat/Lon: lat={lat:.15f}, lon={lon:.15f}")
    
    # GRIB2データ読み込み
    grib2_service = Grib2Service()
    swi_file = "data/Z__C_RJTD_20230602000000_SRF_GPV_Ggis1km_Psw_Aper10min_ANAL_grib2.bin"
    base_info, swi_data = grib2_service.unpack_swi_grib2_from_file(swi_file)
    
    print(f"\\nBase info:")
    print(f"  s_lat = {base_info.s_lat} / 1000000 = {base_info.s_lat / 1000000:.15f}")
    print(f"  s_lon = {base_info.s_lon} / 1000000 = {base_info.s_lon / 1000000:.15f}")
    print(f"  d_lat = {base_info.d_lat} / 1000000 = {base_info.d_lat / 1000000:.15f}")
    print(f"  d_lon = {base_info.d_lon} / 1000000 = {base_info.d_lon / 1000000:.15f}")
    print(f"  x_num = {base_info.x_num}, y_num = {base_info.y_num}")
    
    # VBAの座標変換を詳細実装
    y_calc = (base_info.s_lat / 1000000 - lat) / (base_info.d_lat / 1000000)
    x_calc = (lon - base_info.s_lon / 1000000) / (base_info.d_lon / 1000000)
    
    print(f"\\nCalculation details:")
    print(f"  y_calc = ({base_info.s_lat / 1000000:.15f} - {lat:.15f}) / {base_info.d_lat / 1000000:.15f}")
    print(f"         = {y_calc:.15f}")
    print(f"  x_calc = ({lon:.15f} - {base_info.s_lon / 1000000:.15f}) / {base_info.d_lon / 1000000:.15f}")
    print(f"         = {x_calc:.15f}")
    
    # 異なる丸め方法をテスト
    methods = [
        ("int()", int(y_calc), int(x_calc)),
        ("floor()", int(y_calc), int(x_calc)),  # int()と同じ
        ("round()", round(y_calc), round(x_calc)),
        ("ceil()", int(y_calc) + 1, int(x_calc) + 1)
    ]
    
    print(f"\\nDifferent rounding methods:")
    for method_name, y_rounded, x_rounded in methods:
        # VBAの1ベース座標
        y_vba = y_rounded + 1
        x_vba = x_rounded + 1
        
        # データ番号計算
        vba_data_num = (y_vba - 1) * base_info.x_num + x_vba
        python_index = vba_data_num - 1
        
        print(f"  {method_name:8}: y={y_vba:4d}, x={x_vba:4d} -> data_num={vba_data_num:7d}, index={python_index:7d}")
        
        # 該当インデックスのSWI値を確認
        if 0 <= python_index < len(swi_data['swi']):
            swi_raw = swi_data['swi'][python_index]
            swi_processed = swi_raw / 10
            print(f"            SWI raw={swi_raw:.1f}, processed={swi_processed:.1f}")
        else:
            print(f"            Index out of range")
    
    # 現在使用しているインデックス
    calc_service = CalculationService()
    current_index = calc_service.get_data_num(lat, lon, base_info)
    print(f"\\nCurrent service index: {current_index}")
    
    # CSVとの初期値比較
    import pandas as pd
    csv_file = "data/shiga_swi.csv"
    df = pd.read_csv(csv_file, encoding='shift-jis', header=None, skiprows=1)
    first_row = df.iloc[0]
    csv_initial = first_row[6] if len(first_row) > 6 else 0  # 6列目
    
    print(f"\\nCSV initial (column 6): {csv_initial}")
    
    # どのインデックスがCSVの初期値70.0に最も近いかを確認
    print(f"\\nFinding closest match to CSV initial value {csv_initial}:")
    min_diff = float('inf')
    best_index = -1
    
    for offset in range(-10, 11):  # ±10インデックス範囲で探索
        test_index = current_index + offset
        if 0 <= test_index < len(swi_data['swi']):
            swi_raw = swi_data['swi'][test_index]
            swi_processed = swi_raw / 10
            diff = abs(swi_processed - csv_initial)
            
            if diff < min_diff:
                min_diff = diff
                best_index = test_index
            
            if diff <= 0.1:  # 0.1以下の差なら表示
                print(f"  Index {test_index}: SWI={swi_processed:.1f}, diff={diff:.3f}")
    
    print(f"\\nBest match: Index {best_index}, diff={min_diff:.3f}")

if __name__ == "__main__":
    debug_coordinate_rounding()