#!/usr/bin/env python3
"""
level配列の詳細デバッグ
"""

from services.grib2_service import Grib2Service

def debug_level_array():
    """level配列の構築過程をデバッグ"""
    
    grib2_service = Grib2Service()
    
    # データファイル読み込み
    filepath = 'data/guid_msm_grib2_20230602000000_rmax00.bin'
    with open(filepath, 'rb') as f:
        data = f.read()
    
    print(f"ファイルサイズ: {len(data)} bytes")
    
    # ヘッダー情報取得
    base_info, position, total_size = grib2_service.unpack_info(data, 0)
    
    guidance_data = []
    loop_count = 1
    prev_ft = 0
    dataset_count = 0
    
    print("\n=== level配列構築デバッグ ===")
    
    while position < total_size - 4 and dataset_count < 30:
        dataset_count += 1
        
        # セクション4: プロダクト定義
        section_size = grib2_service.get_dat(data, position, 4)
        span = grib2_service.get_dat(data, position + 49, 4)
        ft = grib2_service.get_dat(data, position + 18, 4) + span
        
        if prev_ft > ft:
            loop_count += 1
        
        position += section_size
        
        # VBAの条件: span = 3 And loop_count = 2
        if span == 3 and loop_count == 2:
            print(f"\nDataset {dataset_count}: 条件一致！")
            
            # セクション5詳細解析（VBA位置確認）
            section_size = grib2_service.get_dat(data, position, 4)
            print(f"  VBA位置確認:")
            print(f"    position+11: bit_num = {grib2_service.get_dat(data, position + 11, 1)}")
            print(f"    position+12: level_max = {grib2_service.get_dat(data, position + 12, 2)}")  
            print(f"    position+13: level_max_alt = {grib2_service.get_dat(data, position + 13, 2)}")
            print(f"    position+14: level_num = {grib2_service.get_dat(data, position + 14, 2)}")
            print(f"    position+15: level_num_alt = {grib2_service.get_dat(data, position + 15, 2)}")
            
            # VBA: position + 12 (1ベース) = position + 11 (0ベース)
            bit_num = grib2_service.get_dat(data, position + 11, 1)    
            level_max = grib2_service.get_dat(data, position + 12, 2)  
            level_num = grib2_service.get_dat(data, position + 14, 2)
            
            print(f"  セクション5サイズ: {section_size}")
            print(f"  bit_num: {bit_num}")
            print(f"  level_max: {level_max}")
            print(f"  level_num: {level_num}")
            
            # level配列を構築
            level = [0] * (level_num + 1)  # VBAの1ベース配列に対応
            print(f"  level配列構築開始 (サイズ: {len(level)})")
            
            for i in range(1, min(level_max + 1, 11)):  # 最初の10個だけ表示
                val = grib2_service.get_dat(data, position + 15 + 2 * i, 2)
                if val >= 65536 / 2:
                    val = int(val - 65536 / 2)
                level[i] = val
                print(f"    level[{i}] = {val} (読み取り位置: {position + 15 + 2 * i})")
            
            if level_max > 10:
                print(f"    ... (残り{level_max - 10}個)")
            
            break
        else:
            # 条件に合わない場合はスキップ
            position = grib2_service._skip_data_section(data, position)
        
        prev_ft = ft


if __name__ == "__main__":
    print("level配列構築デバッグ開始")
    debug_level_array()