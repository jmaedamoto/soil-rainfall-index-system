#!/usr/bin/env python3
"""
GRIB2のft（予報時刻）とCSV時系列の完全対応検証
VBAのft値に基づく正確なマッピング
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

def debug_ft_mapping():
    """ft値に基づくCSVマッピング検証"""
    
    grib2_service = Grib2Service()
    
    # GRIB2データ解析（ft値も取得）
    base_info, guidance_data = grib2_service.unpack_guidance_grib2_from_file('data/guid_msm_grib2_20230602000000_rmax00.bin')
    
    print(f"GRIB2データセット数: {len(guidance_data['data'])}")
    print(f"ft値リスト: {guidance_data.get('ft_values', 'N/A')}")
    
    # ft値が無い場合は、直接VBAロジックで計算する必要がある
    # ここでは既知の結果から推定
    
    # CSV比較データ読み込み
    try:
        df = pd.read_csv('data/shiga_rain.csv', encoding='shift_jis', header=None)
        
        # テスト座標 (前回確認した座標)
        test_row = 1
        mesh_x = df.iloc[test_row, 1]
        mesh_y = df.iloc[test_row, 2]
        csv_rain_series = df.iloc[test_row, 3:].values
        
        lat, lon = meshcode_to_coordinate(mesh_x, mesh_y)
        grid_index, grib_x, grib_y = get_data_num(lat, lon, base_info)
        
        print(f"\\nテスト座標: ({mesh_x}, {mesh_y})")
        print(f"GRIB2インデックス: {grid_index}")
        
        # 判明している完全一致を使用してft値を推定
        known_matches = [
            (5, 12, "Dataset 5 matches t=12h"),  # Dataset 5 = t=12h
            (0, 15, "Dataset 0 matches t=15h"),  # Dataset 0 = t=15h
        ]
        
        print(f"\\n=== 判明している完全一致 ===")
        for dataset_idx, csv_time_h, desc in known_matches:
            dataset = guidance_data['data'][dataset_idx]
            grib2_value = dataset[grid_index - 1]
            csv_idx = csv_time_h // 3  # 3時間間隔
            csv_value = csv_rain_series[csv_idx]
            
            print(f"{desc}:")
            print(f"  GRIB2値: {grib2_value}")
            print(f"  CSV値: {csv_value} (t={csv_time_h}h, 列{csv_idx + 3})")
            print(f"  完全一致: {'○' if abs(grib2_value - csv_value) < 0.01 else '×'}")
        
        # より多くのデータセットでft値を推定
        print(f"\\n=== ft値推定（他のデータセット） ===")
        for dataset_idx in range(len(guidance_data['data'])):
            dataset = guidance_data['data'][dataset_idx]
            grib2_value = dataset[grid_index - 1]
            
            # CSV時系列の中で最も近い値を探索
            best_csv_idx = None
            best_diff = float('inf')
            
            for csv_idx, csv_val in enumerate(csv_rain_series):
                diff = abs(grib2_value - csv_val)
                if diff < best_diff:
                    best_diff = diff
                    best_csv_idx = csv_idx
            
            csv_time_h = best_csv_idx * 3
            
            if best_diff < 0.01:
                print(f"Dataset{dataset_idx:2d}: GRIB2={grib2_value:4.1f} → CSV t={csv_time_h:2d}h (差{best_diff:.6f}) ★完全一致")
            elif best_diff < 1.0:
                print(f"Dataset{dataset_idx:2d}: GRIB2={grib2_value:4.1f} → CSV t={csv_time_h:2d}h (差{best_diff:.3f})")
        
        # GRIB2のft値を直接計算（VBAロジック再現）
        print(f"\\n=== VBA ft値計算の再現 ===")
        try:
            with open('data/guid_msm_grib2_20230602000000_rmax00.bin', 'rb') as f:
                data = f.read()
            
            position = 0
            # ヘッダー情報をスキップ
            base_info_py, position, total_size = grib2_service.unpack_info(data, position)
            
            loop_count = 1
            prev_ft = 0
            dataset_ft_map = {}  # dataset_index -> ft_value
            dataset_count = 0
            
            while position < total_size - 4 and dataset_count < 30:
                # セクション4解析
                section_size = grib2_service.get_dat(data, position, 4)
                span = grib2_service.get_dat(data, position + 49, 4)
                ft = grib2_service.get_dat(data, position + 18, 4) + span
                
                if prev_ft > ft:
                    loop_count += 1
                
                position += section_size
                
                # 条件チェック
                if span == 3 and loop_count == 2:
                    dataset_ft_map[dataset_count] = ft
                    print(f"Dataset{dataset_count:2d}: ft={ft:3d} (span={span}, loop_count={loop_count})")
                    dataset_count += 1
                    
                    # データセクションをスキップ
                    position = grib2_service._skip_data_section(data, position)
                else:
                    # 条件に合わない場合もスキップ
                    position = grib2_service._skip_data_section(data, position)
                
                prev_ft = ft
            
            print(f"\\n=== ft値マッピング確認 ===")
            for dataset_idx in range(min(10, len(guidance_data['data']))):
                ft_value = dataset_ft_map.get(dataset_idx, 'N/A')
                dataset = guidance_data['data'][dataset_idx]
                grib2_value = dataset[grid_index - 1]
                
                if ft_value != 'N/A':
                    csv_idx = ft_value // 3
                    if csv_idx < len(csv_rain_series):
                        csv_value = csv_rain_series[csv_idx]
                        diff = abs(grib2_value - csv_value)
                        match_status = "★完全一致" if diff < 0.01 else f"差{diff:.3f}"
                        print(f"Dataset{dataset_idx:2d}: ft={ft_value:3d} → CSV t={ft_value:2d}h(列{csv_idx+3}) GRIB2={grib2_value} CSV={csv_value} {match_status}")
                    
        except Exception as e:
            print(f"ft値計算エラー: {e}")
            
    except Exception as e:
        print(f"CSV読み込みエラー: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("ft値に基づくCSVマッピング検証開始")
    debug_ft_mapping()