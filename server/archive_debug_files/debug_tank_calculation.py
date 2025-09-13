#!/usr/bin/env python3
"""
タンクモデル計算のデバッグ
VBAと完全に同じ計算を実行
"""

import sys
import os
sys.path.append('.')

import pandas as pd
from services.grib2_service import Grib2Service

def debug_tank_calculation():
    """タンクモデル計算の詳細デバッグ"""
    print("=== Tank Model Calculation Debug ===")
    
    def vba_get_data_num(lat, lon, base_info):
        y = int((base_info.s_lat / 1000000 - lat) / (base_info.d_lat / 1000000)) + 1
        x = int((lon - base_info.s_lon / 1000000) / (base_info.d_lon / 1000000)) + 1
        return (y - 1) * base_info.x_num + x

    def vba_calc_tunk_model(s1, s2, s3, t, r):
        """VBA calc_tunk_model の完全再現"""
        # 流出限界(mm)
        l1, l2, l3, l4 = 15, 60, 15, 15
        
        # 流出係数(1/hr)
        a1, a2, a3, a4 = 0.1, 0.15, 0.05, 0.01
        
        # 浸透係数(1/hr)
        b1, b2, b3 = 0.12, 0.05, 0.01
        
        # 流出量(mm/hr)
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
            
        # 貯留量(mm)
        s1_new = (1 - b1 * t) * s1 - q1 * t + r
        s2_new = (1 - b2 * t) * s2 - q2 * t + b1 * s1 * t
        s3_new = (1 - b3 * t) * s3 - q3 * t + b2 * s2 * t
        
        return s1_new, s2_new, s3_new

    # CSV読み込み
    df = pd.read_csv('data/shiga_swi.csv', encoding='shift-jis', header=None, skiprows=1)
    first_row = df.iloc[0]
    csv_x, csv_y = int(first_row[1]), int(first_row[2])
    csv_timeseries_ft0 = first_row[7]  # 7列目が初期値
    
    print(f"CSV First mesh: X={csv_x}, Y={csv_y}")
    print(f"CSV Timeseries FT0: {csv_timeseries_ft0}")
    
    # 座標変換
    lat = (csv_y + 0.5) * 30 / 3600
    lon = (csv_x + 0.5) * 45 / 3600 + 100
    
    # GRIB2読み込み
    grib2_service = Grib2Service()
    swi_file = 'data/Z__C_RJTD_20230602000000_SRF_GPV_Ggis1km_Psw_Aper10min_ANAL_grib2.bin'
    guidance_file = 'data/guid_msm_grib2_20230602000000_rmax00.bin'
    
    base_info, swi_data = grib2_service.unpack_swi_grib2_from_file(swi_file)
    guidance_base_info, guidance_data = grib2_service.unpack_guidance_grib2_from_file(guidance_file)
    
    # データ取得
    swi_index = vba_get_data_num(lat, lon, base_info) - 1  # Python 0-based
    guidance_index = vba_get_data_num(lat, lon, guidance_base_info) - 1
    
    print(f"\\nGRIB2 Index: {swi_index}")
    
    # 初期値（VBAと同じ）
    swi = swi_data['swi'][swi_index] / 10
    first_tunk = swi_data['first_tunk'][swi_index] / 10  
    second_tunk = swi_data['second_tunk'][swi_index] / 10
    third_tunk = swi - first_tunk - second_tunk
    
    print(f"Initial values:")
    print(f"  swi: {swi}")
    print(f"  first_tunk: {first_tunk}")
    print(f"  second_tunk: {second_tunk}")
    print(f"  third_tunk: {third_tunk}")
    print(f"  sum: {first_tunk + second_tunk + third_tunk}")
    
    # VBAスタイルの時系列計算
    swi_time_series = []
    
    # FT=0 (初期値)
    swi_time_series.append({'ft': 0, 'value': swi})
    print(f"\\nTime series calculation:")
    print(f"  FT=0: {swi}")
    
    # 予測計算
    tmp_f, tmp_s, tmp_t = first_tunk, second_tunk, third_tunk
    
    for i, guidance_values in enumerate(guidance_data['data']):
        if guidance_index < len(guidance_values):
            rain = guidance_values[guidance_index]
            
            # タンクモデル計算
            tmp_f, tmp_s, tmp_t = vba_calc_tunk_model(tmp_f, tmp_s, tmp_t, 3, rain)  # t=3時間
            swi_value = tmp_f + tmp_s + tmp_t
            
            ft = (i + 1) * 3
            swi_time_series.append({'ft': ft, 'value': swi_value})
            
            print(f"  FT={ft}: {swi_value} (rain={rain})")
            
            if len(swi_time_series) >= 3:  # 最初の3つだけ
                break
    
    print(f"\\nComparison:")
    print(f"  Python FT=0: {swi_time_series[0]['value']}")
    print(f"  CSV FT=0 (7th col): {csv_timeseries_ft0}")
    print(f"  Difference: {csv_timeseries_ft0 - swi_time_series[0]['value']}")

if __name__ == "__main__":
    debug_tank_calculation()