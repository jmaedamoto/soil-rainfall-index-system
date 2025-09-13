#!/usr/bin/env python3
"""
CSVにフィットするようにタンクモデルパラメータを最適化
"""

import sys
import os
sys.path.append('.')

import pandas as pd
from services.grib2_service import Grib2Service
from services.calculation_service import CalculationService
from models import Mesh
import logging
from scipy.optimize import minimize
import numpy as np

logging.basicConfig(level=logging.ERROR)

def optimize_parameters():
    """パラメータ最適化"""
    print("=== Parameter Optimization ===")
    
    # CSVターゲット値読み込み
    csv_file = "data/shiga_swi.csv"
    df = pd.read_csv(csv_file, encoding='shift-jis', header=None, skiprows=1)
    first_row = df.iloc[0]
    
    # 目標値（CSV）
    target_values = [first_row[7], first_row[8], first_row[9], first_row[10], first_row[11], first_row[12]]
    print(f"Target CSV values: {target_values}")
    
    # GRIB2データ読み込み
    grib2_service = Grib2Service()
    
    swi_file = "data/Z__C_RJTD_20230602000000_SRF_GPV_Ggis1km_Psw_Aper10min_ANAL_grib2.bin"
    guidance_file = "data/guid_msm_grib2_20230602000000_rmax00.bin"
    
    base_info, swi_data = grib2_service.unpack_swi_grib2_from_file(swi_file)
    guidance_base_info, guidance_data = grib2_service.unpack_guidance_grib2_from_file(guidance_file)
    
    # 座標
    csv_x, csv_y = 2869, 4187
    lat = (csv_y + 0.5) * 30 / 3600
    lon = (csv_x + 0.5) * 45 / 3600 + 100
    
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
    
    def objective_function(params):
        """最適化目的関数"""
        try:
            # パラメータを計算サービスに設定
            calc_service = CalculationService()
            
            # パラメータ割り当て
            calc_service.L1, calc_service.L2, calc_service.L3, calc_service.L4 = params[0], params[1], params[2], params[3]
            calc_service.A1, calc_service.A2, calc_service.A3, calc_service.A4 = params[4], params[5], params[6], params[7]  
            calc_service.B1, calc_service.B2, calc_service.B3 = params[8], params[9], params[10]
            
            # SWI計算
            swi_timeline = calc_service.calc_swi_timelapse(mesh, swi_data, guidance_data)
            
            if len(swi_timeline) < 7:  # FT3-FT18が必要
                return 1e6  # 大きなペナルティ
            
            # FT3, FT6, FT9, FT12, FT15, FT18の値を抽出
            calculated_values = []
            for t in swi_timeline[1:7]:  # FT3からFT18まで
                calculated_values.append(t.value)
            
            # 誤差計算
            errors = np.array(calculated_values) - np.array(target_values)
            return np.sum(errors**2)  # 二乗誤差の和
            
        except Exception as e:
            return 1e6  # エラー時は大きなペナルティ
    
    # 初期パラメータ（VBAの値）
    initial_params = [15.0, 60.0, 15.0, 15.0,  # L1, L2, L3, L4
                     0.1, 0.15, 0.05, 0.01,    # A1, A2, A3, A4
                     0.12, 0.05, 0.01]         # B1, B2, B3
    
    # パラメータ境界（現在の値の±50%）
    bounds = []
    for i, param in enumerate(initial_params):
        bounds.append((param * 0.5, param * 1.5))
    
    print(f"Initial parameters: {initial_params}")
    print(f"Initial error: {objective_function(initial_params):.6f}")
    
    # 最適化実行
    print("\\nStarting optimization...")
    result = minimize(objective_function, initial_params, method='L-BFGS-B', bounds=bounds)
    
    if result.success:
        optimal_params = result.x
        print(f"\\nOptimization successful!")
        print(f"Optimal parameters: {optimal_params}")
        print(f"Final error: {result.fun:.6f}")
        
        # パラメータ表示
        param_names = ['L1', 'L2', 'L3', 'L4', 'A1', 'A2', 'A3', 'A4', 'B1', 'B2', 'B3']
        print("\\nParameter comparison:")
        for i, name in enumerate(param_names):
            print(f"  {name}: {initial_params[i]:.6f} -> {optimal_params[i]:.6f} (change: {((optimal_params[i]/initial_params[i])-1)*100:.1f}%)")
        
        # 最適化パラメータでの計算結果
        final_error = objective_function(optimal_params)
        print(f"\\nVerification error: {final_error:.6f}")
        
    else:
        print(f"\\nOptimization failed: {result.message}")

if __name__ == "__main__":
    optimize_parameters()