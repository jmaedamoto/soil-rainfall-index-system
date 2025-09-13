#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SWI GRIB2デコード処理の詳細トレース
特定座標での値生成過程をVBAと比較
"""

import sys
import os
sys.path.append(os.path.dirname(__file__))

from services.grib2_service import Grib2Service
from services.calculation_service import CalculationService

def main():
    print("=== SWI GRIB2デコード詳細トレース ===")
    
    grib2_service = Grib2Service()
    calculation_service = CalculationService()
    
    # SWIファイル読み込み
    swi_file = "data/Z__C_RJTD_20230602000000_SRF_GPV_Ggis1km_Psw_Aper10min_ANAL_grib2.bin"
    
    with open(swi_file, 'rb') as f:
        data = f.read()
    
    print(f"SWIファイルサイズ: {len(data)} bytes")
    
    # base_info取得
    base_info, position, total_size = grib2_service.unpack_info(data, 0)
    print(f"base_info grid_num: {base_info.grid_num}")
    
    # テスト座標
    test_lat = 35.0041666666667
    test_lon = 135.868055555556
    target_index = calculation_service.get_data_num(test_lat, test_lon, base_info)
    python_target_index = target_index - 1
    
    print(f"ターゲット座標: lat={test_lat}, lon={test_lon}")
    print(f"VBA target_index: {target_index}, Python index: {python_target_index}")
    
    # VBA処理を正確にトレース
    swi_data = None
    section_count = 0
    
    while total_size - position > 4:
        section_count += 1
        print(f"\n--- セクション {section_count} ---")
        
        # セクション4: プロダクト定義
        section_size = grib2_service.get_dat(data, position, 4)
        data_type = grib2_service.get_dat(data, position + 22, 1)
        data_sub_type = grib2_service.get_dat(data, position + 24, 4)
        
        print(f"section_size: {section_size}")
        print(f"data_type: {data_type}")
        print(f"data_sub_type: {data_sub_type}")
        
        position += section_size
        
        if data_type == 200:  # SWIデータ
            print("★ SWIデータ処理開始")
            
            # セクション5: データ表現
            section5_size = grib2_service.get_dat(data, position, 4)
            bit_num = grib2_service.get_dat(data, position + 11, 1)
            level_max = grib2_service.get_dat(data, position + 12, 2)
            level_num = grib2_service.get_dat(data, position + 14, 2)
            
            print(f"セクション5サイズ: {section5_size}")
            print(f"bit_num: {bit_num}")
            print(f"level_max: {level_max}")
            print(f"level_num: {level_num}")
            
            # VBA level配列構築を詳細トレース
            level = [0] * (level_num + 1)
            for i in range(1, level_max + 1):
                val = grib2_service.get_dat(data, position + 15 + 2 * i, 2)
                if val >= 65536 / 2:
                    val = val - 65536 / 2
                level[i] = int(val)
            
            print(f"level配列構築: max={level_max}, 実配列長={len(level)}")
            if len(level) > 15:
                print(f"level[13]={level[13]} level[14]={level[14]}")
            
            position += section5_size
            
            # セクション6: ビットマップ（スキップ）
            section6_size = grib2_service.get_dat(data, position, 4)
            position += section6_size
            
            # セクション7: データ
            section7_size = grib2_service.get_dat(data, position, 4)
            
            print(f"セクション7サイズ: {section7_size}")
            print(f"ランレングス処理開始: target_index={python_target_index}")
            
            # ランレングス展開（ターゲット位置での詳細トレース）
            swi_data = grib2_service.unpack_runlength(
                data, bit_num, level_num, level_max, base_info.grid_num, 
                level, position + 6, position + section7_size
            )
            
            if python_target_index < len(swi_data):
                target_value = swi_data[python_target_index]
                print(f"★ ターゲット位置の値: {target_value}")
                print(f"期待値: 930.0")
                print(f"差異: {abs(target_value - 930.0)}")
            
            # 最初のSWIデータのみ処理してブレーク（VBA準拠）
            break
            
        else:
            # その他のセクションをスキップ
            for _ in range(3):  # セクション5,6,7をスキップ
                section_size = grib2_service.get_dat(data, position, 4)
                position += section_size
                
    print(f"\n処理完了: {section_count}セクション処理")

if __name__ == "__main__":
    main()