#!/usr/bin/env python3
"""
GRIB2解析のデバッグ版
VBAの条件を詳しく確認する
"""

import os
import struct
import pandas as pd
from services.grib2_service import Grib2Service


def debug_guidance_analysis():
    """guidance GRIB2ファイルの条件分析"""
    
    grib2_service = Grib2Service()
    
    # データファイル読み込み
    filepath = 'data/guid_msm_grib2_20230602000000_rmax00.bin'
    with open(filepath, 'rb') as f:
        data = f.read()
    
    print(f"ファイルサイズ: {len(data)} bytes")
    
    # ヘッダー情報取得
    base_info, position, total_size = grib2_service.unpack_info(data, 0)
    print(f"初期時刻: {base_info.initial_date}")
    print(f"総サイズ: {total_size}")
    print(f"グリッド数: {base_info.grid_num}")
    
    guidance_data = []
    loop_count = 1
    prev_ft = 0
    dataset_count = 0
    extracted_count = 0
    
    print("\n=== セクション解析開始 ===")
    
    # VBAのDoループを再現
    while position < total_size - 4:
        dataset_count += 1
        
        # セクション4: プロダクト定義
        section_size = grib2_service.get_dat(data, position, 4)
        span = grib2_service.get_dat(data, position + 49, 4)
        ft = grib2_service.get_dat(data, position + 18, 4) + span
        
        print(f"Dataset {dataset_count}: span={span}, ft={ft}, loop_count={loop_count}, prev_ft={prev_ft}")
        
        if prev_ft > ft:
            loop_count += 1
            print(f"  -> loop_count増加: {loop_count}")
        
        position += section_size
        
        # VBAの条件: span = 3 And loop_count = 2
        if span == 3 and loop_count == 2:
            print(f"  -> 条件一致！データを抽出")
            extracted_count += 1
            try:
                data_values, position = grib2_service._unpack_data_section(data, position, base_info.grid_num)
                guidance_data.append(data_values)
                print(f"     データ要素数: {len(data_values)}")
                print(f"     最初の5要素: {data_values[:5]}")
            except Exception as e:
                print(f"     データ抽出エラー: {e}")
                position = grib2_service._skip_data_section(data, position)
        else:
            print(f"  -> 条件不一致、スキップ")
            # 条件に合わない場合はスキップ
            position = grib2_service._skip_data_section(data, position)
        
        prev_ft = ft
        
        if dataset_count >= 30:  # 最初の30個のみ表示
            break
    
    print(f"\n=== 解析完了 ===")
    print(f"総データセット数: {dataset_count}")
    print(f"抽出されたデータセット数: {extracted_count}")
    print(f"guidance_data長さ: {len(guidance_data)}")


def compare_with_csv():
    """CSVデータと比較"""
    print("\n=== CSV比較データ ===")
    try:
        df = pd.read_csv('data/shiga_rain.csv', encoding='shift_jis', header=None)
        print(f"CSV形状: {df.shape}")
        # 4列目以降が雨量時系列（3列目までがArea名、X、Y座標）
        rain_data = df.iloc[0, 3:].values  # 最初の行の雨量データ
        print(f"最初の行の雨量データ: {rain_data}")
        print(f"データ範囲: min={rain_data.min()}, max={rain_data.max()}")
        
    except Exception as e:
        print(f"CSV読み込みエラー: {e}")


if __name__ == "__main__":
    print("GRIB2解析デバッグ開始")
    debug_guidance_analysis()
    compare_with_csv()