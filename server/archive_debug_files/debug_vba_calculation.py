#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
VBA計算過程の詳細デバッグ
calc_rain_timelapse と calc_swi_timelapse の逐行比較
"""

import sys
import os
sys.path.append(os.path.dirname(__file__))

from services.grib2_service import Grib2Service
from services.data_service import DataService
from services.calculation_service import CalculationService

def debug_rain_calculation():
    """Rain計算の詳細デバッグ"""
    print("=== Rain計算詳細デバッグ ===")
    
    # サービス初期化
    grib2_service = Grib2Service()
    data_service = DataService()
    calc_service = CalculationService()
    
    # データ読み込み
    guidance_file = "data/guid_msm_grib2_20230602000000_rmax00.bin"
    guidance_base_info, guidance_result = grib2_service.unpack_guidance_grib2_from_file(guidance_file)
    
    # 滋賀県の最初のメッシュ
    prefectures = data_service.prepare_areas()
    shiga = next((p for p in prefectures if p.code == "shiga"), None)
    first_mesh = shiga.areas[0].meshes[0]
    
    print(f"テストメッシュ: {first_mesh.code}")
    print(f"座標: lat={first_mesh.lat}, lon={first_mesh.lon}")
    print(f"x={first_mesh.x}, y={first_mesh.y}")
    
    # VBA get_data_num の完全再現
    print("\n--- get_data_num計算 ---")
    base_info = guidance_result['base_info']
    print(f"base_info.s_lat={base_info.s_lat}, base_info.d_lat={base_info.d_lat}")
    print(f"base_info.s_lon={base_info.s_lon}, base_info.d_lon={base_info.d_lon}")
    print(f"base_info.x_num={base_info.x_num}")
    
    # VBA: y = Int((base_info.s_lat / 1000000 - lat) / (base_info.d_lat / 1000000)) + 1
    y_calc = (base_info.s_lat / 1000000 - first_mesh.lat) / (base_info.d_lat / 1000000)
    y = int(y_calc) + 1
    print(f"VBA y計算: ({base_info.s_lat}/1000000 - {first_mesh.lat}) / ({base_info.d_lat}/1000000) = {y_calc}")
    print(f"VBA y = Int({y_calc}) + 1 = {y}")
    
    # VBA: x = Int((lon - base_info.s_lon / 1000000) / (base_info.d_lon / 1000000)) + 1
    x_calc = (first_mesh.lon - base_info.s_lon / 1000000) / (base_info.d_lon / 1000000)
    x = int(x_calc) + 1
    print(f"VBA x計算: ({first_mesh.lon} - {base_info.s_lon}/1000000) / ({base_info.d_lon}/1000000) = {x_calc}")
    print(f"VBA x = Int({x_calc}) + 1 = {x}")
    
    # VBA: get_data_num = (y - 1) * base_info.x_num + x
    guidance_index = (y - 1) * base_info.x_num + x
    print(f"VBA guidance_index = ({y} - 1) * {base_info.x_num} + {x} = {guidance_index}")
    
    # Python配列アクセス用（0-based）
    python_index = guidance_index - 1
    print(f"Python index = {guidance_index} - 1 = {python_index}")
    
    print("\n--- Rain値抽出 ---")
    for i, guidance_item in enumerate(guidance_result['data'][:6]):
        ft = guidance_item['ft']
        if python_index < len(guidance_item['value']):
            rain_value = guidance_item['value'][python_index]
            print(f"FT={ft}: guidance_item['value'][{python_index}] = {rain_value}")
        else:
            print(f"FT={ft}: インデックス範囲外")
    
    # 期待値との比較
    print("\n--- 期待値比較 ---")
    expected_rain = [50, 26, 19, 28, 8, 3]  # CSV期待値
    rain_timeline = calc_service.calc_rain_timelapse(first_mesh, guidance_result)
    
    for i, (timeline_item, expected) in enumerate(zip(rain_timeline[:6], expected_rain)):
        actual = timeline_item.value
        diff = actual - expected
        print(f"FT={timeline_item.ft}: Python={actual}, 期待値={expected}, 差異={diff}")

def debug_swi_calculation():
    """SWI計算の詳細デバッグ"""
    print("\n\n=== SWI計算詳細デバッグ ===")
    
    # サービス初期化
    grib2_service = Grib2Service()
    data_service = DataService()
    calc_service = CalculationService()
    
    # データ読み込み
    swi_file = "data/Z__C_RJTD_20230602000000_SRF_GPV_Ggis1km_Psw_Aper10min_ANAL_grib2.bin"
    guidance_file = "data/guid_msm_grib2_20230602000000_rmax00.bin"
    
    swi_base_info, swi_result = grib2_service.unpack_swi_grib2_from_file(swi_file)
    guidance_base_info, guidance_result = grib2_service.unpack_guidance_grib2_from_file(guidance_file)
    
    # 滋賀県の最初のメッシュ
    prefectures = data_service.prepare_areas()
    shiga = next((p for p in prefectures if p.code == "shiga"), None)
    first_mesh = shiga.areas[0].meshes[0]
    
    print(f"テストメッシュ: {first_mesh.code}")
    
    # VBA get_data_num for SWI data
    print("\n--- SWI get_data_num計算 ---")
    swi_base_info = swi_result['base_info']
    
    y_calc = (swi_base_info.s_lat / 1000000 - first_mesh.lat) / (swi_base_info.d_lat / 1000000)
    y = int(y_calc) + 1
    x_calc = (first_mesh.lon - swi_base_info.s_lon / 1000000) / (swi_base_info.d_lon / 1000000)
    x = int(x_calc) + 1
    swi_index = (y - 1) * swi_base_info.x_num + x
    python_swi_index = swi_index - 1
    
    print(f"SWI index = {swi_index}, Python index = {python_swi_index}")
    
    # VBA SWI初期値取得
    print("\n--- SWI初期値取得 ---")
    if python_swi_index < len(swi_result['swi']):
        # VBA: swi = swi_grib2.swi(swi_index) / 10
        swi_raw = swi_result['swi'][python_swi_index]
        swi = swi_raw / 10
        print(f"VBA swi = swi_grib2.swi({swi_index}) / 10 = {swi_raw} / 10 = {swi}")
        
        # VBA: first_tunk = swi_grib2.first_tunk(swi_index) / 10
        first_tunk_raw = swi_result['first_tunk'][python_swi_index]
        first_tunk = first_tunk_raw / 10
        print(f"VBA first_tunk = {first_tunk_raw} / 10 = {first_tunk}")
        
        # VBA: second_tunk = swi_grib2.second_tunk(swi_index) / 10
        second_tunk_raw = swi_result['second_tunk'][python_swi_index]
        second_tunk = second_tunk_raw / 10
        print(f"VBA second_tunk = {second_tunk_raw} / 10 = {second_tunk}")
        
        # VBA: third_tunk = swi - first_tunk - second_tunk
        third_tunk = swi - first_tunk - second_tunk
        print(f"VBA third_tunk = {swi} - {first_tunk} - {second_tunk} = {third_tunk}")
        
        print(f"\n初期タンク状態:")
        print(f"  第1タンク: {first_tunk}")
        print(f"  第2タンク: {second_tunk}")
        print(f"  第3タンク: {third_tunk}")
        print(f"  合計SWI: {first_tunk + second_tunk + third_tunk} (期待値: {swi})")
        
        # タンクモデル計算のテスト
        print("\n--- タンクモデル計算テスト ---")
        print("VBAパラメータ:")
        print(f"  l1={calc_service.l1}, l2={calc_service.l2}, l3={calc_service.l3}, l4={calc_service.l4}")
        print(f"  a1={calc_service.a1}, a2={calc_service.a2}, a3={calc_service.a3}, a4={calc_service.a4}")
        print(f"  b1={calc_service.b1}, b2={calc_service.b2}, b3={calc_service.b3}")
        
        # 期待値比較
        print("\n--- 期待値比較 ---")
        swi_timeline = calc_service.calc_swi_timelapse(first_mesh, swi_result, guidance_result)
        if swi_timeline:
            ft0_swi = swi_timeline[0].value
            expected_swi = 93.0  # CSV期待値
            diff = abs(ft0_swi - expected_swi)
            print(f"FT=0: Python={ft0_swi}, 期待値={expected_swi}, 差異={diff}")
            
            # 初期値が正確かどうか確認
            print(f"初期SWI計算確認: {first_tunk} + {second_tunk} + {third_tunk} = {first_tunk + second_tunk + third_tunk}")

def main():
    debug_rain_calculation()
    debug_swi_calculation()

if __name__ == "__main__":
    main()