#!/usr/bin/env python3
"""
VBAとPythonの厳密な比較デバッグ
同じファイル、同じ位置での値の完全一致検証
"""

import pandas as pd
from services.grib2_service import Grib2Service

def debug_vba_python_exact():
    """VBA実装との厳密な値比較"""
    
    grib2_service = Grib2Service()
    
    # ファイル読み込み
    file_path = 'data/guid_msm_grib2_20230602000000_rmax00.bin'
    
    with open(file_path, 'rb') as f:
        data = f.read()
    
    print(f"ファイルサイズ: {len(data)} bytes")
    
    # ヘッダー解析
    base_info, position, total_size = grib2_service.unpack_info(data, 0)
    
    print(f"base_info詳細:")
    print(f"  s_lat: {base_info.s_lat} ({base_info.s_lat / 1000000:.6f})")
    print(f"  s_lon: {base_info.s_lon} ({base_info.s_lon / 1000000:.6f})")  
    print(f"  d_lat: {base_info.d_lat} ({base_info.d_lat / 1000000:.6f})")
    print(f"  d_lon: {base_info.d_lon} ({base_info.d_lon / 1000000:.6f})")
    print(f"  x_num: {base_info.x_num}, y_num: {base_info.y_num}")
    print(f"  grid_num: {base_info.grid_num}")
    print(f"  initial position after header: {position}")
    print(f"  total_size: {total_size}")
    
    # ループ変数初期化
    loop_count = 1
    prev_ft = 0
    dataset_count = 0
    debug_count = 0
    
    print(f"\\n=== VBA Doループの厳密な再現 ===")
    
    while position < total_size - 4 and debug_count < 50:
        debug_count += 1
        
        print(f"\\nLoop {debug_count}:")
        print(f"  position: {position}")
        
        # セクション4解析 - VBAと同じ読み取り位置
        # VBA: get_dat(buf, position + 1, 4) → 1ベース
        # Python: get_dat(data, position, 4) → 0ベース
        
        # VBA position+1 の位置をPythonで読む
        section_size = grib2_service.get_dat(data, position, 4)
        print(f"  section_size: {section_size} (position+0)")
        
        # VBA position+50 → Python position+49
        span = grib2_service.get_dat(data, position + 49, 4)
        print(f"  span: {span} (position+49)")
        
        # VBA position+19 → Python position+18
        ft_base = grib2_service.get_dat(data, position + 18, 4)
        ft = ft_base + span
        print(f"  ft_base: {ft_base}, ft: {ft} (position+18)")
        
        # loop_count判定
        if prev_ft > ft:
            loop_count += 1
            print(f"  -> loop_count updated: {loop_count}")
        
        print(f"  prev_ft: {prev_ft}, current ft: {ft}")
        print(f"  span: {span}, loop_count: {loop_count}")
        
        # position更新
        position += section_size
        print(f"  position after section4: {position}")
        
        # 条件判定
        if span == 3 and loop_count == 2:
            print(f"  ★ 条件一致！データを抽出")
            dataset_count += 1
            
            try:
                # データ抽出の詳細ログ
                print(f"    データ抽出開始 position: {position}")
                
                # _unpack_data_sectionの詳細実行
                data_values, new_position = grib2_service._unpack_data_section(data, position, base_info.grid_num)
                
                print(f"    抽出データ要素数: {len(data_values)}")
                print(f"    最初の10要素: {data_values[:10]}")
                print(f"    最後の10要素: {data_values[-10:]}")
                print(f"    position after extraction: {new_position}")
                
                # CSVとの比較（既知の座標で）
                print(f"\\n    CSV比較（座標2869,4188）:")
                df = pd.read_csv('data/shiga_rain.csv', encoding='shift_jis', header=None)
                test_row = 1
                mesh_x = df.iloc[test_row, 1]
                mesh_y = df.iloc[test_row, 2]
                csv_rain_series = df.iloc[test_row, 3:].values
                
                # 座標変換
                lat = (mesh_y + 0.5) * 30 / 3600
                lon = (mesh_x + 0.5) * 45 / 3600 + 100
                y = int((base_info.s_lat / 1000000 - lat) / (base_info.d_lat / 1000000)) + 1
                x = int((lon - base_info.s_lon / 1000000) / (base_info.d_lon / 1000000)) + 1
                grid_index = (y - 1) * base_info.x_num + x
                
                if 1 <= grid_index <= len(data_values):
                    grib2_value = data_values[grid_index - 1]
                    print(f"    Dataset{dataset_count}: ft={ft}")
                    print(f"    GRIB2値: {grib2_value}")
                    print(f"    CSV時系列: {csv_rain_series[:8]}")
                    
                    # 全CSV値との比較
                    best_csv_idx = None
                    best_diff = float('inf')
                    for csv_idx, csv_val in enumerate(csv_rain_series):
                        diff = abs(grib2_value - csv_val)
                        if diff < best_diff:
                            best_diff = diff
                            best_csv_idx = csv_idx
                    
                    csv_time_h = best_csv_idx * 3
                    match_status = "完全一致" if best_diff < 0.01 else f"最接近(差{best_diff:.3f})"
                    print(f"    CSV最適一致: t={csv_time_h}h, 値{csv_rain_series[best_csv_idx]}, {match_status}")
                
                position = new_position
                
            except Exception as e:
                print(f"    データ抽出エラー: {e}")
                position = grib2_service._skip_data_section(data, position)
                
        else:
            print(f"  条件不一致 → スキップ")
            position = grib2_service._skip_data_section(data, position)
        
        prev_ft = ft
        
        if total_size - position <= 4:
            print(f"  ファイル終端到達")
            break
    
    print(f"\\n=== 解析完了 ===")
    print(f"デバッグループ数: {debug_count}")  
    print(f"データセット数: {dataset_count}")

if __name__ == "__main__":
    print("VBAとPythonの厳密な比較デバッグ開始")
    debug_vba_python_exact()