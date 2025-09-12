#!/usr/bin/env python3
"""
VBAとPythonの完全一致比較
実際のランレングス展開をVBAロジックで完全再現
"""

from services.grib2_service import Grib2Service

def debug_exact_vba_matching():
    """VBAとの完全一致を目指すデバッグ"""
    print("=== VBA完全一致比較デバッグ ===")
    
    grib2_service = Grib2Service()
    swi_file = "data/Z__C_RJTD_20230602000000_SRF_GPV_Ggis1km_Psw_Aper10min_ANAL_grib2.bin"
    
    try:
        # 手動でVBAと同じ順序でセクション解析
        with open(swi_file, 'rb') as f:
            data = f.read()
        
        print(f"ファイルサイズ: {len(data)} bytes")
        
        # VBA順序での解析
        position = 0
        
        # セクション0: 指示部
        if data[position:position+4] != b'GRIB':
            print("ERROR: GRIBヘッダーが見つかりません")
            return
        
        total_size = grib2_service.get_dat(data, position + 8, 4)
        print(f"総サイズ: {total_size}")
        position = 16
        
        # セクション1: 識別セクション
        section_size = grib2_service.get_dat(data, position, 4)
        print(f"セクション1サイズ: {section_size}")
        
        # 時刻情報
        year = grib2_service.get_dat(data, position + 12, 2)
        month = grib2_service.get_dat(data, position + 14, 1)
        day = grib2_service.get_dat(data, position + 15, 1)
        hour = grib2_service.get_dat(data, position + 16, 1)
        print(f"時刻: {year}-{month:02d}-{day:02d} {hour:02d}:00:00")
        
        position += section_size
        
        # セクション2はスキップ（存在しない場合もある）
        next_section = grib2_service.get_dat(data, position + 4, 1)
        if next_section == 2:
            section_size = grib2_service.get_dat(data, position, 4)
            print(f"セクション2サイズ: {section_size} (スキップ)")
            position += section_size
        
        # セクション3: グリッド定義
        section_size = grib2_service.get_dat(data, position, 4)
        section_num = grib2_service.get_dat(data, position + 4, 1)
        print(f"セクション{section_num}サイズ: {section_size}")
        
        if section_num != 3:
            print(f"ERROR: 期待セクション3、実際は{section_num}")
            return
        
        grid_num = grib2_service.get_dat(data, position + 6, 4)
        x_num = grib2_service.get_dat(data, position + 30, 4)
        y_num = grib2_service.get_dat(data, position + 34, 4)
        print(f"グリッド: {grid_num}, X={x_num}, Y={y_num}")
        
        position += section_size
        
        # セクション4: プロダクト定義
        section_size = grib2_service.get_dat(data, position, 4)
        section_num = grib2_service.get_dat(data, position + 4, 1)
        data_type = grib2_service.get_dat(data, position + 22, 1)
        print(f"セクション{section_num}サイズ: {section_size}, データタイプ: {data_type}")
        
        if data_type != 200:
            print(f"ERROR: 期待データタイプ200、実際は{data_type}")
            return
        
        position += section_size
        
        # セクション5: データ表現
        section_size = grib2_service.get_dat(data, position, 4)
        section_num = grib2_service.get_dat(data, position + 4, 1)
        print(f"セクション{section_num}サイズ: {section_size}")
        
        bit_num = grib2_service.get_dat(data, position + 11, 1)
        level_max = grib2_service.get_dat(data, position + 12, 2)
        level_num = grib2_service.get_dat(data, position + 14, 2)
        print(f"bit_num={bit_num}, level_max={level_max}, level_num={level_num}")
        
        # レベル配列を正確に読み取り
        level = []
        for i in range(1, level_max + 1):
            val = grib2_service.get_dat(data, position + 15 + 2 * i, 2)
            if val >= 32768:  # 符号付き16bit
                val = val - 65536
            level.append(val)
        
        print(f"レベル配列例: level[1]={level[0]}, level[14]={level[13]} (期待値700)")
        
        position += section_size
        
        # セクション6: ビットマップ
        section_size = grib2_service.get_dat(data, position, 4)
        section_num = grib2_service.get_dat(data, position + 4, 1)
        print(f"セクション{section_num}サイズ: {section_size} (ビットマップ)")
        position += section_size
        
        # セクション7: データセクション
        section_size = grib2_service.get_dat(data, position, 4)
        section_num = grib2_service.get_dat(data, position + 4, 1)
        print(f"セクション{section_num}サイズ: {section_size} (データ)")
        
        # ランレングス展開の最初の数バイトを詳細チェック
        byte_size = bit_num // 8
        s_position = position + 5
        e_position = position + section_size
        
        print(f"\nランレングス展開テスト:")
        print(f"  開始位置: {s_position}, 終了位置: {e_position}")
        print(f"  byte_size: {byte_size}")
        
        p = s_position
        for i in range(10):
            if p + 2 * byte_size > len(data):
                break
            
            d = grib2_service.get_dat(data, p, byte_size)
            p += byte_size
            dd = grib2_service.get_dat(data, p, byte_size)
            p += byte_size
            
            print(f"  {i}: d={d}, dd={dd}, d>level_num:{d>level_num}")
            
            if d > level_num:
                print(f"    ERROR detected at position {i}")
                print(f"    Raw bytes at d position: {data[p-2*byte_size:p-byte_size].hex()}")
                print(f"    Raw bytes at dd position: {data[p-byte_size:p].hex()}")
                break
        
    except Exception as e:
        print(f"エラー: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_exact_vba_matching()
