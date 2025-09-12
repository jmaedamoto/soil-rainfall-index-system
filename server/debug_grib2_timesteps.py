#!/usr/bin/env python3
"""
GRIB2ガイダンスデータの全時刻を詳細解析
CSV参照データとの完全一致を確認
"""

import pandas as pd
from services.grib2_service import Grib2Service

def meshcode_to_coordinate(x, y):
    """メッシュコード座標 → 緯度経度変換"""
    lat = (y + 0.5) * 30 / 3600
    lon = (x + 0.5) * 45 / 3600 + 100
    return lat, lon

def get_data_num(lat, lon, base_info):
    """緯度経度 → GRIB2グリッドインデックス変換"""
    y = int((base_info.s_lat / 1000000 - lat) / (base_info.d_lat / 1000000)) + 1
    x = int((lon - base_info.s_lon / 1000000) / (base_info.d_lon / 1000000)) + 1
    grid_index = (y - 1) * base_info.x_num + x
    return grid_index, x, y

def debug_all_timesteps():
    """全時刻のGRIB2データを解析してCSVと比較"""
    
    grib2_service = Grib2Service()
    
    # GRIB2データ解析
    print("=== GRIB2 guidance 全データ解析 ===")
    base_info, guidance_data = grib2_service.unpack_guidance_grib2_from_file('data/guid_msm_grib2_20230602000000_rmax00.bin')
    
    print(f"base_info詳細:")
    print(f"  s_lat: {base_info.s_lat / 1000000:.6f}")
    print(f"  s_lon: {base_info.s_lon / 1000000:.6f}")
    print(f"  d_lat: {base_info.d_lat / 1000000:.6f}")
    print(f"  d_lon: {base_info.d_lon / 1000000:.6f}")
    print(f"  x_num: {base_info.x_num}, y_num: {base_info.y_num}")
    print(f"  grid_num: {base_info.grid_num}")
    
    print(f"\\nガイダンスデータセット数: {len(guidance_data['data'])}")
    print(f"各データセット要素数:")
    for i, dataset in enumerate(guidance_data['data']):
        print(f"  データセット{i}: {len(dataset)}要素")
    
    # CSV比較データ読み込み
    try:
        df = pd.read_csv('data/shiga_rain.csv', encoding='shift_jis', header=None)
        print(f"\\nCSV形状: {df.shape}")
        
        # テスト用座標を準備
        test_indices = [1, 2, 3, 4, 5]  # 1行目は0ベースで
        test_coords = []
        for i in test_indices:
            if i < df.shape[0]:
                mesh_x = df.iloc[i, 1]
                mesh_y = df.iloc[i, 2] 
                csv_rain_series = df.iloc[i, 3:].values  # 全雨量時系列
                
                lat, lon = meshcode_to_coordinate(mesh_x, mesh_y)
                grid_index, grib_x, grib_y = get_data_num(lat, lon, base_info)
                
                test_coords.append({
                    'csv_row': i,
                    'mesh_x': mesh_x,
                    'mesh_y': mesh_y,
                    'lat': lat,
                    'lon': lon,
                    'grid_index': grid_index,
                    'csv_rain': csv_rain_series
                })
        
        print(f"\\n=== 全データセットとの比較検証 ===")
        
        # 各データセットと比較
        for dataset_idx, dataset in enumerate(guidance_data['data']):
            print(f"\\nデータセット{dataset_idx}:")
            
            # 各テスト座標での値を確認
            matches = 0
            total = 0
            
            for coord in test_coords:
                grid_index = coord['grid_index']
                csv_rain = coord['csv_rain']
                
                if 1 <= grid_index <= len(dataset):
                    grib2_value = dataset[grid_index - 1]  # 0ベース変換
                    total += 1
                    
                    # CSV時系列の各時刻と比較
                    best_match_idx = -1
                    best_match_diff = float('inf')
                    
                    for t_idx, csv_val in enumerate(csv_rain[:15]):  # 最初の15時刻
                        diff = abs(grib2_value - csv_val)
                        if diff < best_match_diff:
                            best_match_diff = diff
                            best_match_idx = t_idx
                    
                    if dataset_idx == 0:  # 最初のデータセットで詳細表示
                        print(f"  座標({coord['mesh_x']}, {coord['mesh_y']}):")
                        print(f"    GRIB2値: {grib2_value}")
                        print(f"    CSV時系列: {csv_rain[:8]}")
                        print(f"    最適一致: t={best_match_idx}, diff={best_match_diff:.1f}")
                    
                    # 完全一致チェック（誤差0.1未満）
                    if best_match_diff < 0.1:
                        matches += 1
            
            print(f"  一致数/総数: {matches}/{total}")
            print(f"  一致率: {matches/total*100:.1f}%" if total > 0 else "N/A")
            
            # データセットの統計
            unique_values = {}
            for val in dataset:
                rounded_val = round(val, 1)
                unique_values[rounded_val] = unique_values.get(rounded_val, 0) + 1
            
            sorted_values = sorted(unique_values.items(), key=lambda x: x[1], reverse=True)[:8]
            print(f"  上位値: {sorted_values}")
        
        # CSV時系列の統計
        print(f"\\n=== CSV雨量時系列統計 ===")
        all_csv_values = []
        for i in test_indices:
            if i < df.shape[0]:
                rain_series = df.iloc[i, 3:13].values  # 10個の時刻
                all_csv_values.extend(rain_series)
        
        csv_unique = {}
        for val in all_csv_values:
            csv_unique[val] = csv_unique.get(val, 0) + 1
        
        csv_sorted = sorted(csv_unique.items(), key=lambda x: x[1], reverse=True)[:10]
        print(f"CSV上位値: {csv_sorted}")
        
    except Exception as e:
        print(f"CSV読み込みエラー: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("GRIB2ガイダンス全時刻データの詳細解析開始")
    debug_all_timesteps()