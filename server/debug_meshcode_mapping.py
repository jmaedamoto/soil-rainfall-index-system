#!/usr/bin/env python3
"""
メッシュコードと GRIB2 グリッドの正確なマッピング検証
VBAのmeshcode_to_coordinate + get_data_num ロジックの再現
"""

import pandas as pd
from services.grib2_service import Grib2Service

def meshcode_to_coordinate(x, y):
    """VBAのmeshcode_to_coordinate関数を再現
    
    Args:
        x, y: CSV の X,Y 座標（メッシュコード座標系）
    
    Returns:
        (lat, lon): 緯度経度座標
    """
    # VBA: lat = (y + 0.5) * 30 / 3600
    # VBA: lon = (x + 0.5) * 45 / 3600 + 100
    lat = (y + 0.5) * 30 / 3600
    lon = (x + 0.5) * 45 / 3600 + 100
    return lat, lon

def get_data_num(lat, lon, base_info):
    """VBAのget_data_num関数を再現
    
    Args:
        lat, lon: 緯度経度
        base_info: GRIB2メタデータ
    
    Returns:
        grid_index: GRIB2グリッドインデックス (1ベース)
    """
    # VBA: y = Int((base_info.s_lat / 1000000 - lat) / (base_info.d_lat / 1000000)) + 1
    # VBA: x = Int((lon - base_info.s_lon / 1000000) / (base_info.d_lon / 1000000)) + 1
    # VBA: get_data_num = (y - 1) * base_info.x_num + x
    
    y = int((base_info.s_lat / 1000000 - lat) / (base_info.d_lat / 1000000)) + 1
    x = int((lon - base_info.s_lon / 1000000) / (base_info.d_lon / 1000000)) + 1
    grid_index = (y - 1) * base_info.x_num + x
    
    return grid_index, x, y

def debug_correct_mapping():
    """正確なメッシュコード→GRIB2マッピングの検証"""
    
    # GRIB2データ解析
    grib2_service = Grib2Service()
    
    print("=== GRIB2 guidance データ解析 ===")
    base_info, guidance_data = grib2_service.unpack_guidance_grib2_from_file('data/guid_msm_grib2_20230602000000_rmax00.bin')
    
    print(f"base_info.s_lat: {base_info.s_lat} ({base_info.s_lat / 1000000:.6f})")
    print(f"base_info.s_lon: {base_info.s_lon} ({base_info.s_lon / 1000000:.6f})")
    print(f"base_info.d_lat: {base_info.d_lat} ({base_info.d_lat / 1000000:.6f})")
    print(f"base_info.d_lon: {base_info.d_lon} ({base_info.d_lon / 1000000:.6f})")
    print(f"base_info.x_num: {base_info.x_num}")
    print(f"base_info.y_num: {base_info.y_num}")
    print(f"base_info.grid_num: {base_info.grid_num}")
    
    if len(guidance_data['data']) > 0:
        first_dataset = guidance_data['data'][0]  # ft=3のデータ
        print(f"第1データセット要素数: {len(first_dataset)}")
        
        # 一意値の統計
        unique_values = {}
        for val in first_dataset:
            unique_values[val] = unique_values.get(val, 0) + 1
        
        print(f"一意値数: {len(unique_values)}")
        sorted_values = sorted(unique_values.items(), key=lambda x: x[1], reverse=True)[:10]
        print(f"上位10個の値: {sorted_values}")
    
    # CSV比較データ読み込み
    print(f"\n=== 正確なメッシュコード→GRIB2マッピング ===")
    try:
        df = pd.read_csv('data/shiga_rain.csv', encoding='shift_jis', header=None)
        print(f"CSV形状: {df.shape}")
        
        # 最初の5行のデータを正確に検証
        print(f"\n詳細マッピング検証:")
        for i in range(1, min(6, df.shape[0])):  # 1行目はスキップ
            area_name = df.iloc[i, 0]
            mesh_x = df.iloc[i, 1]  # メッシュコード X座標
            mesh_y = df.iloc[i, 2]  # メッシュコード Y座標
            rain_values = df.iloc[i, 3:8].values  # 雨量時系列
            
            # メッシュコード → 緯度経度変換 (VBAロジック)
            lat, lon = meshcode_to_coordinate(mesh_x, mesh_y)
            
            # 緯度経度 → GRIB2グリッドインデックス変換 (VBAロジック)
            grid_index, grib_x, grib_y = get_data_num(lat, lon, base_info)
            
            print(f"\n行{i+1}: エリア={area_name}")
            print(f"  メッシュコード座標: X={mesh_x}, Y={mesh_y}")
            print(f"  緯度経度変換: lat={lat:.6f}, lon={lon:.6f}")
            print(f"  GRIB2グリッド座標: x={grib_x}, y={grib_y}")
            print(f"  GRIB2インデックス: {grid_index}")
            print(f"  CSV雨量値[3:8]: {rain_values}")
            
            # GRIB2データから対応する値を取得 (0ベースインデックス)
            if 1 <= grid_index <= len(first_dataset):
                grib2_value = first_dataset[grid_index - 1]  # 1ベース → 0ベース
                csv_first_rain = rain_values[0] if len(rain_values) > 0 else 0
                print(f"  GRIB2値(ft=3): {grib2_value}")
                print(f"  CSV値(4列目): {csv_first_rain}")
                print(f"  一致: {'○' if abs(grib2_value - csv_first_rain) < 0.01 else '×'}")
                
                if abs(grib2_value - csv_first_rain) >= 0.01:
                    print(f"  差分: {abs(grib2_value - csv_first_rain):.6f}")
            else:
                print(f"  GRIB2値: インデックス範囲外 ({grid_index} > {len(first_dataset)})")
        
        # より多くのデータポイントで統計的検証
        print(f"\n=== 統計的検証（最初の50行） ===")
        matches = 0
        total_checked = 0
        
        for i in range(1, min(51, df.shape[0])):
            mesh_x = df.iloc[i, 1]
            mesh_y = df.iloc[i, 2]
            rain_value = df.iloc[i, 3] if len(df.iloc[i, :]) > 3 else 0
            
            lat, lon = meshcode_to_coordinate(mesh_x, mesh_y)
            grid_index, grib_x, grib_y = get_data_num(lat, lon, base_info)
            
            if 1 <= grid_index <= len(first_dataset):
                grib2_value = first_dataset[grid_index - 1]
                total_checked += 1
                if abs(grib2_value - rain_value) < 0.01:
                    matches += 1
        
        print(f"検証済み点数: {total_checked}")
        print(f"完全一致数: {matches}")
        print(f"一致率: {matches/total_checked*100:.1f}%" if total_checked > 0 else "N/A")
                
    except Exception as e:
        print(f"CSV読み込みエラー: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("正確なメッシュコード→GRIB2マッピング検証開始")
    debug_correct_mapping()