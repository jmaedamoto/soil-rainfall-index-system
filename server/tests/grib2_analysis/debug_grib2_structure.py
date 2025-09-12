#!/usr/bin/env python3
"""
GRIB2ファイル構造の詳細デバッグ
VBA処理との完全一致を目指す
"""

from services.grib2_service import Grib2Service
import struct

def debug_grib2_binary_structure():
    """GRIB2バイナリ構造の詳細デバッグ"""
    print("=== GRIB2バイナリ構造デバッグ ===")
    
    grib2_service = Grib2Service()
    swi_file = "data/Z__C_RJTD_20230602000000_SRF_GPV_Ggis1km_Psw_Aper10min_ANAL_grib2.bin"
    
    try:
        with open(swi_file, 'rb') as f:
            data = f.read()
        
        print(f"ファイルサイズ: {len(data)} バイト")
        
        # セクション0: 指示
        total_size = grib2_service.get_dat(data, 8, 8)
        print(f"総サイズ: {total_size}")
        
        position = 16  # セクション1開始位置
        
        # セクション1: 識別セクション
        section_size = grib2_service.get_dat(data, position, 4)
        print(f"\nセクション1サイズ: {section_size}")
        
        # 初期時刻情報
        year = grib2_service.get_dat(data, position + 12, 2)
        month = grib2_service.get_dat(data, position + 14, 1)
        day = grib2_service.get_dat(data, position + 15, 1)
        hour = grib2_service.get_dat(data, position + 16, 1)
        print(f"初期時刻: {year}-{month:02d}-{day:02d} {hour:02d}:00:00")
        
        position += section_size
        
        # セクション3: グリッド定義
        section_size = grib2_service.get_dat(data, position, 4)
        print(f"\nセクション3サイズ: {section_size}")
        
        grid_num = grib2_service.get_dat(data, position + 6, 4)
        x_num = grib2_service.get_dat(data, position + 30, 4)
        y_num = grib2_service.get_dat(data, position + 34, 4)
        print(f"グリッド数: {grid_num}, X軸: {x_num}, Y軸: {y_num}")
        
        position += section_size
        
        # データ種別を調査するためのループ
        data_count = 0
        while position < len(data) - 4 and data_count < 3:
            # セクション4: プロダクト定義
            section_size = grib2_service.get_dat(data, position, 4)
            data_type = grib2_service.get_dat(data, position + 22, 1)
            data_sub_type = grib2_service.get_dat(data, position + 24, 4)
            
            print(f"\nデータ{data_count + 1}:")
            print(f"  セクション4サイズ: {section_size}")
            print(f"  データタイプ: {data_type}")
            print(f"  データサブタイプ: {data_sub_type}")
            
            position += section_size
            
            # セクション5: データ表現
            section_size = grib2_service.get_dat(data, position, 4)
            print(f"  セクション5サイズ: {section_size}")
            
            if data_type == 200:  # 土壌雨量指数
                bit_num = grib2_service.get_dat(data, position + 11, 1)
                level_max = grib2_service.get_dat(data, position + 12, 2)
                level_num = grib2_service.get_dat(data, position + 14, 2)
                
                print(f"  bit_num: {bit_num}")
                print(f"  level_max: {level_max}")
                print(f"  level_num: {level_num}")
                
                # レベル値をデバッグ
                print("  レベル値 (最初の10個):")
                for i in range(1, min(11, level_max + 1)):
                    if position + 15 + 2 * i < len(data):
                        val = grib2_service.get_dat(data, position + 15 + 2 * i, 2)
                        if val >= 65536 // 2:
                            val = int(val - 65536 // 2)
                        print(f"    level[{i}] = {val}")
                
                position += section_size
                
                # セクション6: ビットマップ（スキップ）
                section_size = grib2_service.get_dat(data, position, 4)
                position += section_size
                
                # セクション7: データセクションを詳細調査
                section_size = grib2_service.get_dat(data, position, 4)
                print(f"  セクション7サイズ: {section_size}")
                
                # 最初の数バイトのランレングスデータを調査
                s_position = position + 5
                byte_size = bit_num // 8
                print(f"  バイトサイズ: {byte_size}")
                print("  最初の10個のd/dd値:")
                
                p = s_position
                for j in range(10):
                    if p + 2 * byte_size <= len(data):
                        d = grib2_service.get_dat(data, p, byte_size)
                        p += byte_size
                        dd = grib2_service.get_dat(data, p, byte_size)
                        p += byte_size
                        
                        print(f"    {j}: d={d}, dd={dd} (d > level_num: {d > level_num})")
                    else:
                        break
                
                position += section_size
                break
            else:
                position += section_size
                # セクション6,7をスキップ
                section_size = grib2_service.get_dat(data, position, 4)
                position += section_size
                section_size = grib2_service.get_dat(data, position, 4)
                position += section_size
            
            data_count += 1
            
    except Exception as e:
        print(f"エラー: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_grib2_binary_structure()