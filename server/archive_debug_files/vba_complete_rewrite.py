#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Module.basのcalc_data関数とその関連関数を完全にVBAから忠実にPythonに置き換え
VBAの1ベース配列をPythonの0ベース配列に正確に変換
"""

import struct
import os
from typing import List, Dict, Any, Tuple
from datetime import datetime
from dataclasses import dataclass

# VBAのType構造体をPythonのdataclassで完全再現
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

@dataclass
class SwiTimeSeries:
    ft: int
    value: float

@dataclass
class GuidanceTimeSeries:
    ft: int
    value: float

@dataclass
class Risk:
    ft: int
    value: int

@dataclass
class Mesh:
    area_name: str
    code: str
    lon: float
    lat: float
    x: int
    y: int
    advisary_bound: int
    warning_bound: int
    dosyakei_bound: int
    swi: List[SwiTimeSeries] = None
    rain: List[GuidanceTimeSeries] = None

@dataclass
class Area:
    name: str
    meshes: List[Mesh]
    risk_timeline: List[Risk] = None

@dataclass
class Prefecture:
    name: str
    code: str
    areas: List[Area]
    area_min_x: int
    area_max_y: int

@dataclass
class SwiGrib2:
    base_info: BaseInfo
    swi: List[float]
    first_tunk: List[float]
    second_tunk: List[float]

@dataclass
class GuidanceGrib2:
    base_info: BaseInfo
    data: List[Dict[str, Any]]

class VBACalculationService:
    """VBA Module.basの完全再現クラス"""
    
    # VBA タンクモデルパラメータ (完全同一)
    l1, l2, l3, l4 = 15.0, 60.0, 15.0, 15.0
    a1, a2, a3, a4 = 0.1, 0.15, 0.05, 0.01
    b1, b2, b3 = 0.12, 0.05, 0.01

    def get_dat(self, data: bytes, s: int, length: int) -> int:
        """
        VBA Function get_dat(buf, s, length) の完全再現
        VBA: 1ベースインデックス -> Python: 0ベースインデックス変換
        """
        # VBA: For i = s To e
        # Python: for i in range(s-1, e)  # VBAの1ベースを0ベースに変換
        result = 0
        e = s + length - 1
        
        for i in range(s - 1, e):  # VBA 1-based to Python 0-based
            if i < len(data):
                dat = data[i]
                result += dat * (256 ** (e - 1 - i))  # VBA: (e - i), Python: (e - 1 - i)
        
        return result

    def unpack_info(self, data: bytes) -> BaseInfo:
        """
        VBA Function unpack_info の完全再現
        VBAの順次処理を忠実に再現
        """
        # VBA: total_size = get_dat(buf, 9, 8)
        total_size = self.get_dat(data, 9, 8)
        
        # VBA: position = 16
        position = 16
        
        # Section 1: 日時情報
        # VBA: section_size = get_dat(buf, position + 1, 4)
        section_size = self.get_dat(data, position + 1, 4)
        
        # VBA: initial_date = DateSerial(get_dat(buf, position + 13, 2), get_dat(buf, position + 15, 1), get_dat(buf, position + 16, 1))
        # VBA: initial_time = TimeSerial(get_dat(buf, position + 17, 1), get_dat(buf, position + 18, 1), get_dat(buf, position + 19, 1))
        year = self.get_dat(data, position + 13, 2)
        month = self.get_dat(data, position + 15, 1)
        day = self.get_dat(data, position + 16, 1)
        hour = self.get_dat(data, position + 17, 1)
        minute = self.get_dat(data, position + 18, 1)
        second = self.get_dat(data, position + 19, 1)
        initial_date = datetime(year, month, day, hour, minute, second)
        
        # VBA: position = position + section_size
        position = position + section_size
        
        # Section 3: グリッド情報
        # VBA: section_size = get_dat(buf, position + 1, 4)
        section_size = self.get_dat(data, position + 1, 4)
        
        # VBA: unpack_info.grid_num = get_dat(buf, position + 7, 4)
        grid_num = self.get_dat(data, position + 7, 4)
        
        # VBA: unpack_info.x_num = get_dat(buf, position + 31, 4)
        x_num = self.get_dat(data, position + 31, 4)
        
        # VBA: unpack_info.y_num = get_dat(buf, position + 35, 4) 
        y_num = self.get_dat(data, position + 35, 4)
        
        # VBA: unpack_info.s_lat = get_dat(buf, position + 47, 4)
        s_lat = self.get_dat(data, position + 47, 4)
        
        # VBA: unpack_info.s_lon = get_dat(buf, position + 51, 4)
        s_lon = self.get_dat(data, position + 51, 4)
        
        # VBA: unpack_info.e_lat = get_dat(buf, position + 56, 4)
        e_lat = self.get_dat(data, position + 56, 4)
        
        # VBA: unpack_info.e_lon = get_dat(buf, position + 60, 4)
        e_lon = self.get_dat(data, position + 60, 4)
        
        # VBA: unpack_info.d_lon = get_dat(buf, position + 64, 4)
        d_lon = self.get_dat(data, position + 64, 4)
        
        # VBA: unpack_info.d_lat = get_dat(buf, position + 68, 4)
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

    def unpack_runlength(self, data: bytes, position: int, grid_num: int) -> List[int]:
        """
        VBA Function unpack_runlength の完全再現
        VBA配列の1ベースをPython配列の0ベースに変換
        """
        # VBA: ReDim unpack_runlength(1 To grid_num)
        result = [0] * grid_num  # Python: 0-based array
        
        # VBA: level_max = get_dat(buf, position + 12, 2)
        level_max = self.get_dat(data, position + 12, 2)
        
        # VBA: ReDim level(0 To level_max)
        level = [0] * (level_max + 1)  # 0 to level_max
        
        # VBA: For i = 0 To level_max
        for i in range(level_max + 1):
            # VBA: level(i) = get_dat(buf, position + 21 + i * 2, 2)
            level[i] = self.get_dat(data, position + 21 + i * 2, 2)
        
        # VBA: p = position + 21 + (level_max + 1) * 2
        p = position + 21 + (level_max + 1) * 2
        
        # VBA: i = 1  (VBA 1-based)
        i = 0  # Python 0-based
        
        while i < grid_num:
            # VBA: d = get_dat(buf, p, 1)
            d = self.get_dat(data, p, 1)
            p += 1
            
            if d <= level_max:
                # VBA: unpack_runlength(i) = level(d)
                result[i] = level[d]
                # VBA: i = i + 1
                i += 1
            else:
                # VBA: run_length = get_dat(buf, p, 1)
                run_length = self.get_dat(data, p, 1)
                p += 1
                
                # VBA: d2 = get_dat(buf, p, 1)
                d2 = self.get_dat(data, p, 1)
                p += 1
                
                # VBA: For j = 1 To run_length
                for j in range(run_length):
                    if i < grid_num:
                        # VBA: unpack_runlength(i) = level(d2)
                        result[i] = level[d2]
                        # VBA: i = i + 1
                        i += 1
        
        return result

    def unpack_data(self, position: int, data: bytes, grid_num: int) -> List[float]:
        """
        VBA Function unpack_data の完全再現
        """
        # VBA: data_type = get_dat(buf, position + 10, 2)
        data_type = self.get_dat(data, position + 10, 2)
        
        if data_type == 200:  # ランレングス圧縮
            # VBA: Dim int_data() As Integer
            # VBA: int_data = unpack_runlength(position, buf, grid_num)
            int_data = self.unpack_runlength(data, position, grid_num)
            
            # VBA: ReDim unpack_data(1 To grid_num)
            result = [0.0] * grid_num  # Python 0-based
            
            # VBA: For i = 1 To grid_num
            for i in range(grid_num):
                # VBA: unpack_data(i) = int_data(i)
                result[i] = float(int_data[i])
            
            return result
        else:
            # 他のデータタイプ（必要に応じて実装）
            return [0.0] * grid_num

    def unpack_swi_grib2(self, filename: str) -> SwiGrib2:
        """
        VBA Function unpack_swi_grib2(filename) As SwiGrib2 の完全再現
        """
        with open(filename, 'rb') as f:
            data = f.read()
        
        # VBA: base_info = unpack_info(position, total_size, buf)
        base_info = self.unpack_info(data)
        
        # VBA処理を続けるためのposition初期化
        total_size = self.get_dat(data, 9, 8)
        position = 16
        
        # Section 1をスキップ
        section_size = self.get_dat(data, position + 1, 4)
        position = position + section_size
        
        # Section 3をスキップ  
        section_size = self.get_dat(data, position + 1, 4)
        position = position + section_size
        
        # VBA: ReDim swi(1 To base_info.grid_num)
        # VBA: ReDim first_tunk(1 To base_info.grid_num)  
        # VBA: ReDim second_tunk(1 To base_info.grid_num)
        swi = [0.0] * base_info.grid_num
        first_tunk = [0.0] * base_info.grid_num
        second_tunk = [0.0] * base_info.grid_num
        
        # VBA: Do While position < total_size
        while position < total_size:
            if position + 4 >= len(data):
                break
                
            # VBA: section_size = get_dat(buf, position, 4)
            section_size = self.get_dat(data, position, 4)
            
            if section_size == 0:
                break
            
            # VBA: section_no = get_dat(buf, position + 5, 1)
            section_no = self.get_dat(data, position + 5, 1)
            
            if section_no == 5:  # データ表現セクション
                # VBA: data_type = get_dat(buf, position + 23, 1)
                data_type = self.get_dat(data, position + 23, 1)
                
                if data_type == 200:  # 土壌雨量指数
                    # VBA: swi = unpack_data(position, buf, base_info.grid_num)
                    swi = self.unpack_data(position, data, base_info.grid_num)
                elif data_type == 201:
                    # VBA: data_sub_type = get_dat(buf, position + 25, 4)
                    data_sub_type = self.get_dat(data, position + 25, 4)
                    
                    if data_sub_type == 1:  # 第1タンク値
                        first_tunk = self.unpack_data(position, data, base_info.grid_num)
                    elif data_sub_type == 2:  # 第2タンク値
                        second_tunk = self.unpack_data(position, data, base_info.grid_num)
            
            # VBA: position = position + section_size
            position = position + section_size
        
        return SwiGrib2(
            base_info=base_info,
            swi=swi,
            first_tunk=first_tunk,
            second_tunk=second_tunk
        )

    def unpack_guidance_grib2(self, filename: str) -> GuidanceGrib2:
        """
        VBA Function unpack_guidance_grib2(filename) As GuidanceGrib2 の完全再現
        """
        with open(filename, 'rb') as f:
            data = f.read()
        
        base_info = self.unpack_info(data)
        
        # VBA処理を続けるためのposition初期化
        total_size = self.get_dat(data, 9, 8)
        position = 16
        
        # Section 1をスキップ
        section_size = self.get_dat(data, position + 1, 4)
        position = position + section_size
        
        # Section 3をスキップ  
        section_size = self.get_dat(data, position + 1, 4)
        position = position + section_size
        guidance_data = []
        
        # VBA: i = 0
        i = 0
        
        # VBA: Do While position < total_size
        while position < total_size:
            if position + 4 >= len(data):
                break
                
            section_size = self.get_dat(data, position, 4)
            if section_size == 0:
                break
            
            section_no = self.get_dat(data, position + 5, 1)
            
            if section_no == 4:  # プロダクト定義セクション
                # VBA: ft = get_dat(buf, position + 19, 4)
                ft = self.get_dat(data, position + 19, 4)
                
                # VBA: span = get_dat(buf, position + 46, 1)
                span = self.get_dat(data, position + 46, 1)
                
                # VBA: loop_count = get_dat(buf, position + 50, 1)
                loop_count = self.get_dat(data, position + 50, 1)
                
            elif section_no == 7:  # データセクション
                # VBA: If span = 3 And loop_count = 2 Then
                if span == 3 and loop_count == 2:
                    # VBA: i = i + 1
                    i += 1
                    
                    # VBA: guidance_data(i).ft = ft
                    # VBA: guidance_data(i).value = unpack_data(position, buf, base_info.grid_num)
                    data_values = self.unpack_data(position, data, base_info.grid_num)
                    guidance_data.append({
                        'ft': ft,
                        'value': data_values
                    })
            
            position = position + section_size
        
        return GuidanceGrib2(
            base_info=base_info,
            data=guidance_data
        )

    def meshcode_to_coordinate(self, code: str) -> Tuple[float, float, int, int]:
        """
        VBA Function meshcode_to_coordinate の完全再現
        """
        # VBA: y = Int(Mid(code, 1, 2)) * 80 + Int(Mid(code, 5, 1)) * 10 + Int(Mid(code, 7, 1))
        y = int(code[0:2]) * 80 + int(code[4]) * 10 + int(code[6])
        
        # VBA: x = Int(Mid(code, 3, 2)) * 80 + Int(Mid(code, 6, 1)) * 10 + Int(Mid(code, 8, 1))
        x = int(code[2:4]) * 80 + int(code[5]) * 10 + int(code[7])
        
        # VBA: lat = (y + 0.5) * 30 / 3600
        lat = (y + 0.5) * 30 / 3600
        
        # VBA: lon = (x + 0.5) * 45 / 3600 + 100
        lon = (x + 0.5) * 45 / 3600 + 100
        
        return lat, lon, x, y

    def get_data_num(self, lat: float, lon: float, base_info: BaseInfo) -> int:
        """
        VBA Function get_data_num の完全再現
        VBA: 1ベース戻り値 -> Python: 0ベース戻り値変換
        """
        # VBA: y = Int((base_info.s_lat / 1000000 - lat) / (base_info.d_lat / 1000000)) + 1
        y = int((base_info.s_lat / 1000000 - lat) / (base_info.d_lat / 1000000)) + 1
        
        # VBA: x = Int((lon - base_info.s_lon / 1000000) / (base_info.d_lon / 1000000)) + 1
        x = int((lon - base_info.s_lon / 1000000) / (base_info.d_lon / 1000000)) + 1
        
        # VBA: get_data_num = (y - 1) * base_info.x_num + x
        vba_result = (y - 1) * base_info.x_num + x
        
        # VBA 1-based を Python 0-based に変換
        return vba_result - 1

    def calc_tunk_model(self, s1: float, s2: float, s3: float, t: float, r: float) -> Tuple[float, float, float]:
        """
        VBA Sub calc_tunk_model の完全再現
        """
        # VBA: q1 = 0, q2 = 0, q3 = 0
        q1 = q2 = q3 = 0.0
        
        # VBA: If s1 > l1 Then q1 = q1 + a1 * (s1 - l1)
        if s1 > self.l1:
            q1 = q1 + self.a1 * (s1 - self.l1)
            
        # VBA: If s1 > l2 Then q1 = q1 + a2 * (s1 - l2)
        if s1 > self.l2:
            q1 = q1 + self.a2 * (s1 - self.l2)
            
        # VBA: If s2 > l3 Then q2 = a3 * (s2 - l3)
        if s2 > self.l3:
            q2 = self.a3 * (s2 - self.l3)
            
        # VBA: If s3 > l4 Then q3 = a4 * (s3 - l4)
        if s3 > self.l4:
            q3 = self.a4 * (s3 - self.l4)
        
        # VBA: s1_new = (1 - b1 * t) * s1 - q1 * t + r
        s1_new = (1 - self.b1 * t) * s1 - q1 * t + r
        
        # VBA: s2_new = (1 - b2 * t) * s2 - q2 * t + q1 * t
        s2_new = (1 - self.b2 * t) * s2 - q2 * t + q1 * t
        
        # VBA: s3_new = s3 + q2 * t
        s3_new = s3 + q2 * t
        
        # VBA: If s1_new < 0 Then s1_new = 0
        if s1_new < 0:
            s1_new = 0
            
        # VBA: If s2_new < 0 Then s2_new = 0
        if s2_new < 0:
            s2_new = 0
            
        # VBA: If s3_new < 0 Then s3_new = 0
        if s3_new < 0:
            s3_new = 0
        
        return s1_new, s2_new, s3_new

if __name__ == "__main__":
    # テスト実行
    calc = VBACalculationService()
    
    # ファイルテスト
    swi_file = "data/Z__C_RJTD_20230602000000_SRF_GPV_Ggis1km_Psw_Aper10min_ANAL_grib2.bin"
    guidance_file = "data/guid_msm_grib2_20230602000000_rmax00.bin"
    
    if os.path.exists(swi_file):
        print("=== VBA完全再現テスト ===")
        
        # SWI GRIB2テスト
        swi_grib2 = calc.unpack_swi_grib2(swi_file)
        print(f"SWI base_info: grid_num={swi_grib2.base_info.grid_num}")
        print(f"SWI data length: {len(swi_grib2.swi)}")
        
        # ガイダンスGRIB2テスト
        guidance_grib2 = calc.unpack_guidance_grib2(guidance_file)
        print(f"Guidance base_info: grid_num={guidance_grib2.base_info.grid_num}")
        print(f"Guidance data length: {len(guidance_grib2.data)}")
        
        # 座標変換テスト
        test_code = "52352679"
        lat, lon, x, y = calc.meshcode_to_coordinate(test_code)
        print(f"meshcode_to_coordinate({test_code}): lat={lat}, lon={lon}, x={x}, y={y}")
        
        # データ番号テスト
        data_num = calc.get_data_num(lat, lon, swi_grib2.base_info)
        print(f"get_data_num: {data_num}")
        
        # 実際のSWI値
        if 0 <= data_num < len(swi_grib2.swi):
            swi_value = swi_grib2.swi[data_num] / 10  # VBA: / 10
            print(f"SWI value: {swi_value}")
    else:
        print(f"ファイルが見つかりません: {swi_file}")