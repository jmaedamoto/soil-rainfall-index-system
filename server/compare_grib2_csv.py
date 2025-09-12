#!/usr/bin/env python3
"""
GRIB2とCSVの詳細比較
"""

import pandas as pd
from services.grib2_service import Grib2Service

def compare_grib2_csv():
    """GRIB2データとCSVデータの詳細比較"""
    
    # GRIB2データ解析
    grib2_service = Grib2Service()
    base_info, guidance_data = grib2_service.unpack_guidance_grib2_from_file('data/guid_msm_grib2_20230602000000_rmax00.bin')
    
    print("=== GRIB2データ分析 ===")
    print(f"データセット数: {len(guidance_data['data'])}")
    
    if len(guidance_data['data']) > 0:
        first_dataset = guidance_data['data'][0]
        print(f"最初のデータセット要素数: {len(first_dataset)}")
        
        # 値の分布確認
        unique_values = {}
        for val in first_dataset:
            unique_values[val] = unique_values.get(val, 0) + 1
        
        print("値の分布 (上位10個):")
        sorted_values = sorted(unique_values.items(), key=lambda x: x[1], reverse=True)
        for val, count in sorted_values[:10]:
            print(f"  {val}: {count}回")
    
    # CSVデータ分析
    print("\n=== CSV比較データ ===")
    try:
        df = pd.read_csv('data/shiga_rain.csv', encoding='shift_jis', header=None)
        print(f"CSV形状: {df.shape}")
        
        # 4列目以降が雨量時系列（3列目までがArea名、X、Y座標）
        rain_data = df.iloc[:, 3:].values.flatten()  # 全雨量データを1次元に
        
        # 値の分布確認
        unique_csv_values = {}
        for val in rain_data:
            unique_csv_values[val] = unique_csv_values.get(val, 0) + 1
        
        print("CSV雨量値の分布 (上位10個):")
        sorted_csv_values = sorted(unique_csv_values.items(), key=lambda x: x[1], reverse=True)
        for val, count in sorted_csv_values[:10]:
            print(f"  {val}: {count}回")
        
        print(f"\nCSV雨量データ統計:")
        print(f"  最小値: {rain_data.min()}")
        print(f"  最大値: {rain_data.max()}")
        print(f"  平均値: {rain_data.mean():.2f}")
        print(f"  非ゼロ値の数: {(rain_data > 0).sum()}")
        print(f"  総データ数: {len(rain_data)}")
        
        # 座標情報も確認
        print(f"\n座標情報 (最初の5行):")
        for i in range(min(5, df.shape[0])):
            area_name = df.iloc[i, 0]
            x_coord = df.iloc[i, 1] 
            y_coord = df.iloc[i, 2]
            rain_values = df.iloc[i, 3:8].values  # 最初の5つの雨量値
            print(f"  {area_name}, X={x_coord}, Y={y_coord}, 雨量={rain_values}")
            
    except Exception as e:
        print(f"CSV読み込みエラー: {e}")
    
    # グリッド数の比較
    print(f"\n=== グリッド数比較 ===")
    print(f"GRIB2グリッド数: {base_info.grid_num}")
    if len(guidance_data['data']) > 0:
        print(f"GRIB2実データ要素数: {len(guidance_data['data'][0])}")
    print(f"CSV行数: {df.shape[0] if 'df' in locals() else 'N/A'}")

if __name__ == "__main__":
    print("GRIB2とCSVの詳細比較開始")
    compare_grib2_csv()