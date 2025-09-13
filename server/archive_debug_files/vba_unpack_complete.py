#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
VBA unpack_data と unpack_runlength の完全再現
"""

import struct
import os
from typing import List, Dict, Any, Tuple
from datetime import datetime
from dataclasses import dataclass

# 前回のBaseInfoクラスなどをコピー
@dataclass
class BaseInfo:
    initial_date: datetime
    grid_num: int
    x_num: int
    y_num: int
    s_lat: int
    s_lon: int
    e_lat: int
    e_lon: int
    d_lat: int
    d_lon: int

class VBACompleteUnpack:
    """VBAのunpack関数群の完全再現"""
    
    def get_dat(self, data: bytes, s: int, length: int) -> int:
        """VBA get_dat の完全再現"""
        result = 0
        e = s + length - 1
        
        for i in range(s - 1, e):  # VBA 1-based to Python 0-based
            if i < len(data):
                dat = data[i]
                result += dat * (256 ** (e - 1 - i))
        
        return result
    
    def unpack_info(self, data: bytes) -> BaseInfo:
        """VBA unpack_info の完全再現"""
        total_size = self.get_dat(data, 9, 8)
        position = 16
        
        # Section 1: 日時情報
        section_size = self.get_dat(data, position + 1, 4)
        year = self.get_dat(data, position + 13, 2)
        month = self.get_dat(data, position + 15, 1)
        day = self.get_dat(data, position + 16, 1)
        hour = self.get_dat(data, position + 17, 1)
        minute = self.get_dat(data, position + 18, 1)
        second = self.get_dat(data, position + 19, 1)
        initial_date = datetime(year, month, day, hour, minute, second)
        position = position + section_size
        
        # Section 3: グリッド情報
        section_size = self.get_dat(data, position + 1, 4)
        grid_num = self.get_dat(data, position + 7, 4)
        x_num = self.get_dat(data, position + 31, 4)
        y_num = self.get_dat(data, position + 35, 4)
        s_lat = self.get_dat(data, position + 47, 4)
        s_lon = self.get_dat(data, position + 51, 4)
        e_lat = self.get_dat(data, position + 56, 4)
        e_lon = self.get_dat(data, position + 60, 4)
        d_lon = self.get_dat(data, position + 64, 4)
        d_lat = self.get_dat(data, position + 68, 4)
        
        return BaseInfo(
            initial_date=initial_date,
            grid_num=grid_num,
            x_num=x_num,
            y_num=y_num,
            s_lat=s_lat,
            s_lon=s_lon,
            e_lat=e_lat,
            e_lon=e_lon,
            d_lat=d_lat,
            d_lon=d_lon
        )
        
    def unpack_runlength(self, bit_num: int, level_num: int, level_max: int, 
                        grid_num: int, level: List[int], data: bytes, 
                        s_position: int, e_position: int) -> List[int]:
        """
        VBA Function unpack_runlength の完全再現
        """
        # VBA: lngu = 2 ^ bit_num - 1 - level_max
        lngu = (2 ** bit_num) - 1 - level_max
        
        # VBA: ReDim data(grid_num)
        result = [0] * grid_num  # Python 0-based, VBA 1-based
        
        # VBA: d_index = 1
        d_index = 0  # Python 0-based
        
        # VBA: p = s_position
        p = s_position
        
        # VBA: Do While p < e_position
        while p < e_position:
            if p + bit_num // 8 > len(data):
                break
                
            # VBA: d = get_dat(buf, p, bit_num / 8)
            d = self.get_dat(data, p, bit_num // 8)
            p = p + bit_num // 8
            
            # VBA: If d > level_num Then
            if d > level_num:
                print(f"Error: d={d} > level_num={level_num}")
                break
            
            if p + bit_num // 8 > len(data):
                break
                
            # VBA: dd = get_dat(buf, p, bit_num / 8)
            dd = self.get_dat(data, p, bit_num // 8)
            
            # VBA: If dd <= level_max Then
            if dd <= level_max:
                # VBA: data(d_index) = level(d)
                if d_index < grid_num and d < len(level):
                    result[d_index] = level[d]
                # VBA: d_index = d_index + 1
                d_index = d_index + 1
            else:
                # VBA: nlength = 0
                nlength = 0
                # VBA: p2 = 1
                p2 = 1
                
                # VBA: Do While p <= e_position And dd > level_max
                while p <= e_position and dd > level_max:
                    # VBA: nlength = nlength + ((lngu ^ (p2 - 1)) * (dd - level_max - 1))
                    nlength = nlength + ((lngu ** (p2 - 1)) * (dd - level_max - 1))
                    p = p + bit_num // 8
                    
                    if p + bit_num // 8 > len(data):
                        break
                        
                    dd = self.get_dat(data, p, bit_num // 8)
                    p2 = p2 + 1
                
                # VBA: For i = 1 To nlength + 1
                for i in range(nlength + 1):
                    if d_index < grid_num and d < len(level):
                        # VBA: data(d_index) = level(d)
                        result[d_index] = level[d]
                        # VBA: d_index = d_index + 1
                        d_index = d_index + 1
            
            p = p + bit_num // 8
        
        return result
    
    def unpack_data(self, position: int, data: bytes, grid_num: int) -> List[float]:
        """
        VBA Function unpack_data の完全再現
        """
        # Section 5: データ表現セクション
        # VBA: section_size = get_dat(buf, position + 1, 4)
        section_size = self.get_dat(data, position + 1, 4)
        
        # VBA: bit_num = get_dat(buf, position + 12, 1)
        bit_num = self.get_dat(data, position + 12, 1)
        
        # VBA: level_max = get_dat(buf, position + 13, 2)
        level_max = self.get_dat(data, position + 13, 2)
        
        # VBA: level_num = get_dat(buf, position + 15, 2)
        level_num = self.get_dat(data, position + 15, 2)
        
        # VBA: ReDim level(level_num)
        level = [0] * (level_num + 1)  # VBA 0 to level_num
        
        # VBA: fct = get_dat(buf, position + 17, 1)
        fct = self.get_dat(data, position + 17, 1)
        
        # VBA: For i = 1 To level_max
        for i in range(1, level_max + 1):
            # VBA: level(i) = get_dat(buf, position + 16 + 2 * i, 2)
            level[i] = self.get_dat(data, position + 16 + 2 * i, 2)
            
            # VBA: If level(i) >= 65536 / 2 Then level(i) = level(i) - 65536 / 2
            if level[i] >= 65536 // 2:
                level[i] = level[i] - 65536 // 2
        
        # VBA: position = position + section_size
        position = position + section_size
        
        # Section 6: ビットマップセクション (スキップ)
        # VBA: section_size = get_dat(buf, position + 1, 4)
        section_size = self.get_dat(data, position + 1, 4)
        position = position + section_size
        
        # Section 7: データセクション
        # VBA: section_size = get_dat(buf, position + 1, 4)
        section_size = self.get_dat(data, position + 1, 4)
        
        # VBA: unpack_data = unpack_runlength(bit_num, level_num, level_max, grid_num, level, buf, position + 6, position + section_size)
        s_position = position + 6
        e_position = position + section_size
        
        int_data = self.unpack_runlength(bit_num, level_num, level_max, grid_num, level, data, s_position, e_position)
        
        # VBA配列をfloatに変換
        result = [float(val) for val in int_data]
        
        return result

def test_unpack():
    """完全な展開テスト"""
    calc = VBACompleteUnpack()
    
    swi_file = "data/Z__C_RJTD_20230602000000_SRF_GPV_Ggis1km_Psw_Aper10min_ANAL_grib2.bin"
    
    if not os.path.exists(swi_file):
        print(f"ファイルが見つかりません: {swi_file}")
        return
    
    with open(swi_file, 'rb') as f:
        data = f.read()
    
    print(f"=== VBA完全展開テスト ===")
    print(f"ファイルサイズ: {len(data)} bytes")
    
    # Base info
    base_info = calc.unpack_info(data)
    print(f"Grid_num: {base_info.grid_num}")
    print(f"X_num: {base_info.x_num}, Y_num: {base_info.y_num}")
    print(f"S_lat: {base_info.s_lat}, S_lon: {base_info.s_lon}")
    
    # Section探索
    total_size = calc.get_dat(data, 9, 8)
    position = 16
    
    # Section 1をスキップ
    section_size = calc.get_dat(data, position + 1, 4)
    position = position + section_size
    
    # Section 3をスキップ  
    section_size = calc.get_dat(data, position + 1, 4)
    position = position + section_size
    
    # データセクションを探索
    swi_data = None
    first_tunk_data = None
    second_tunk_data = None
    section_count = 0
    
    try:
        while position < total_size and section_count < 50:  # 無限ループ防止
            if position + 4 >= len(data):
                print(f"Position {position} exceeds data length {len(data)}")
                break
                
            section_size = calc.get_dat(data, position, 4)
            if section_size == 0:
                print("Section size is 0, breaking")
                break
            
            if position + 5 >= len(data):
                break
                
            section_no = calc.get_dat(data, position + 5, 1)
            section_count += 1
            print(f"Section {section_count}: No.{section_no}, Length: {section_size}, Position: {position}")
            
            if section_no == 5:  # データ表現セクション
                if position + 23 < len(data):
                    data_type = calc.get_dat(data, position + 23, 1)
                    print(f"  Data type: {data_type}")
                    
                    try:
                        if data_type == 200:  # 土壌雨量指数
                            print("  SWI data found, unpacking...")
                            swi_data = calc.unpack_data(position, data, base_info.grid_num)
                            print(f"  SWI data length: {len(swi_data)}")
                            
                            if len(swi_data) > 0:
                                # テスト座標での値確認
                                test_code = "52352679"
                                lat = (4187 + 0.5) * 30 / 3600
                                lon = (2869 + 0.5) * 45 / 3600 + 100
                                
                                # VBA get_data_num計算
                                y = int((base_info.s_lat / 1000000 - lat) / (base_info.d_lat / 1000000)) + 1
                                x = int((lon - base_info.s_lon / 1000000) / (base_info.d_lon / 1000000)) + 1
                                data_num = (y - 1) * base_info.x_num + x
                                python_index = data_num - 1  # VBA 1-based to Python 0-based
                                
                                print(f"  Test coordinates: lat={lat}, lon={lon}")
                                print(f"  VBA data_num: {data_num}, Python index: {python_index}")
                                
                                if 0 <= python_index < len(swi_data):
                                    swi_value = swi_data[python_index] / 10  # VBA: /10
                                    print(f"  SWI value: {swi_value}")
                                else:
                                    print(f"  Index out of range: {python_index}")
                                    
                        elif data_type == 201:
                            if position + 25 < len(data):
                                data_sub_type = calc.get_dat(data, position + 25, 4)
                                if data_sub_type == 1:
                                    print("  First tank data found")
                                elif data_sub_type == 2:
                                    print("  Second tank data found")
                    except Exception as e:
                        print(f"  Error in data unpacking: {e}")
            
            position = position + section_size
            
    except Exception as e:
        print(f"Error in section parsing: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_unpack()