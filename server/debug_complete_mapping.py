#!/usr/bin/env python3
"""
完全時刻マッピングの確定
GRIB2データセットとCSV列の完全対応関係を解明
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

def find_complete_mapping():
    """完全な時刻マッピングを確定"""
    
    grib2_service = Grib2Service()
    
    # GRIB2データ解析
    base_info, guidance_data = grib2_service.unpack_guidance_grib2_from_file('data/guid_msm_grib2_20230602000000_rmax00.bin')
    print(f"GRIB2データセット数: {len(guidance_data['data'])}")
    
    # CSV比較データ読み込み
    try:
        df = pd.read_csv('data/shiga_rain.csv', encoding='shift_jis', header=None)
        print(f"CSV形状: {df.shape}")
        
        # テスト座標を多く準備 (より確実な検証のため)
        test_coords = []
        test_indices = list(range(1, min(21, df.shape[0])))  # 20個のテスト点
        
        for i in test_indices:
            mesh_x = df.iloc[i, 1]
            mesh_y = df.iloc[i, 2] 
            csv_rain_series = df.iloc[i, 3:].values  # 全雨量時系列
            
            lat, lon = meshcode_to_coordinate(mesh_x, mesh_y)
            grid_index, grib_x, grib_y = get_data_num(lat, lon, base_info)
            
            # 有効なグリッドインデックスのみ使用
            if 1 <= grid_index <= len(guidance_data['data'][0]):
                test_coords.append({
                    'csv_row': i,
                    'mesh_x': mesh_x,
                    'mesh_y': mesh_y,
                    'grid_index': grid_index,
                    'csv_rain': csv_rain_series
                })
        
        print(f"有効テスト点数: {len(test_coords)}")
        print(f"CSV時系列長: {len(test_coords[0]['csv_rain']) if test_coords else 'N/A'}")
        
        print(f"\\n=== 完全時刻マッピング解析 ===")
        
        # 各GRIB2データセットを全CSV列と比較
        mapping_matrix = {}  # dataset_idx -> {csv_col: match_count}
        
        for dataset_idx in range(len(guidance_data['data'])):
            dataset = guidance_data['data'][dataset_idx]
            mapping_matrix[dataset_idx] = {}
            
            # CSV列（時刻）ごとに一致数を計算
            for csv_col in range(3, min(28, len(test_coords[0]['csv_rain']) + 3)):  # 3列目から（時系列開始）
                matches = 0
                total = 0
                
                for coord in test_coords:
                    grid_index = coord['grid_index']
                    csv_rain = coord['csv_rain']
                    
                    if csv_col - 3 < len(csv_rain):
                        grib2_value = dataset[grid_index - 1]
                        csv_value = csv_rain[csv_col - 3]
                        total += 1
                        
                        # 完全一致チェック（誤差0.1未満）
                        if abs(grib2_value - csv_value) < 0.1:
                            matches += 1
                
                if total > 0:
                    match_rate = matches / total
                    mapping_matrix[dataset_idx][csv_col] = {
                        'matches': matches, 
                        'total': total, 
                        'rate': match_rate
                    }
        
        # 最適マッピングを特定
        print(f"\\n=== 最適マッピング結果 ===")
        perfect_mappings = []
        
        for dataset_idx in range(min(26, len(guidance_data['data']))):
            best_csv_col = None
            best_rate = 0
            
            for csv_col, stats in mapping_matrix[dataset_idx].items():
                if stats['rate'] > best_rate:
                    best_rate = stats['rate']
                    best_csv_col = csv_col
            
            if best_rate > 0.5:  # 50%以上の一致率
                time_hours = (best_csv_col - 3) * 3  # 3時間間隔
                print(f"データセット{dataset_idx:2d} -> CSV列{best_csv_col} (t={time_hours:2d}h) : {best_rate*100:5.1f}% ({mapping_matrix[dataset_idx][best_csv_col]['matches']}/{mapping_matrix[dataset_idx][best_csv_col]['total']})")
                
                if best_rate >= 0.95:  # 95%以上は完全一致
                    perfect_mappings.append((dataset_idx, best_csv_col, time_hours))
            else:
                print(f"データセット{dataset_idx:2d} -> マッピング不明 (最高{best_rate*100:5.1f}%)")
        
        # 完全一致データセットの詳細確認
        print(f"\\n=== 完全一致データセット詳細 ===")
        for dataset_idx, csv_col, time_hours in perfect_mappings:
            dataset = guidance_data['data'][dataset_idx]
            print(f"\\nDataset{dataset_idx} (t={time_hours}h):")
            
            # 最初の5つのテスト点で値を確認
            for i, coord in enumerate(test_coords[:5]):
                grid_index = coord['grid_index']
                csv_rain = coord['csv_rain']
                
                if csv_col - 3 < len(csv_rain):
                    grib2_value = dataset[grid_index - 1]
                    csv_value = csv_rain[csv_col - 3]
                    diff = abs(grib2_value - csv_value)
                    
                    print(f"  点{i+1}({coord['mesh_x']},{coord['mesh_y']}): GRIB2={grib2_value}, CSV={csv_value}, 差={diff:.6f}")
        
        # 時系列マッピングの構築
        print(f"\\n=== 時系列マッピング構築 ===")
        time_mapping = {}  # time_hours -> dataset_idx
        
        for dataset_idx, csv_col, time_hours in perfect_mappings:
            time_mapping[time_hours] = dataset_idx
        
        sorted_times = sorted(time_mapping.keys())
        print(f"完全一致時刻: {sorted_times}")
        print(f"マッピング:")
        for time_h in sorted_times:
            dataset_idx = time_mapping[time_h]
            print(f"  t={time_h:2d}h -> データセット{dataset_idx}")
            
    except Exception as e:
        print(f"エラー: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("完全時刻マッピング確定開始")
    find_complete_mapping()