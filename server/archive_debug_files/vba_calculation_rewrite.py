#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
VBA calc_swi_timelapse と calc_rain_timelapse の完全再現
既存のCalculationServiceを完全に置き換え
"""

from typing import List, Dict, Any, Tuple
from models.data_models import SwiTimeSeries, GuidanceTimeSeries, Mesh

class VBACalculationRewrite:
    """VBA Module.bas の calc_swi_timelapse と calc_rain_timelapse を完全再現"""
    
    # VBA タンクモデルパラメータ (完全同一)
    l1, l2, l3, l4 = 15.0, 60.0, 15.0, 15.0
    a1, a2, a3, a4 = 0.1, 0.15, 0.05, 0.01
    b1, b2, b3 = 0.12, 0.05, 0.01

    def get_data_num(self, lat: float, lon: float, base_info: Any) -> int:
        """
        VBA Function get_data_num の完全再現
        VBA 1-based戻り値をそのまま返す
        """
        # VBA: y = Int((base_info.s_lat / 1000000 - lat) / (base_info.d_lat / 1000000)) + 1
        y = int((base_info.s_lat / 1000000 - lat) / (base_info.d_lat / 1000000)) + 1
        
        # VBA: x = Int((lon - base_info.s_lon / 1000000) / (base_info.d_lon / 1000000)) + 1
        x = int((lon - base_info.s_lon / 1000000) / (base_info.d_lon / 1000000)) + 1
        
        # VBA: get_data_num = (y - 1) * base_info.x_num + x
        return (y - 1) * base_info.x_num + x

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

    def calc_rain_timelapse(self, mesh: Mesh, guidance_grib2: Dict[str, Any]) -> List[GuidanceTimeSeries]:
        """
        VBA Function calc_rain_timelapse の完全再現
        """
        # VBA: guidance_index = get_data_num(m.lat, m.lon, guidance_grib2.base_info)
        guidance_index = self.get_data_num(mesh.lat, mesh.lon, guidance_grib2['base_info'])
        
        # VBA配列は1-based、Pythonは0-basedなので変換
        python_index = guidance_index - 1
        
        # VBA: ReDim rain_timeseries(UBound(guidance_grib2.data))
        rain_timeseries = []
        
        # VBA: For i = 1 To UBound(guidance_grib2.data)
        for i in range(len(guidance_grib2['data'])):  # Python 0-based
            guidance_item = guidance_grib2['data'][i]
            
            # VBA: rain_timeseries(i).ft = guidance_grib2.data(i).ft
            # VBA: rain_timeseries(i).value = guidance_grib2.data(i).value(guidance_index)
            if python_index < len(guidance_item['value']):
                value = guidance_item['value'][python_index]
                rain_timeseries.append(GuidanceTimeSeries(
                    ft=guidance_item['ft'],
                    value=value
                ))
        
        return rain_timeseries

    def calc_swi_timelapse(self, mesh: Mesh, swi_grib2: Dict[str, Any], guidance_grib2: Dict[str, Any]) -> List[SwiTimeSeries]:
        """
        VBA Function calc_swi_timelapse の完全再現
        """
        # VBA: swi_index = get_data_num(m.lat, m.lon, swi_grib2.base_info)
        swi_index = self.get_data_num(mesh.lat, mesh.lon, swi_grib2['base_info'])
        
        # VBA配列は1-based、Pythonは0-basedなので変換
        python_swi_index = swi_index - 1
        
        if (python_swi_index >= len(swi_grib2['swi']) or
            python_swi_index >= len(swi_grib2['first_tunk']) or
            python_swi_index >= len(swi_grib2['second_tunk'])):
            return []
        
        # VBA: swi = swi_grib2.swi(swi_index) / 10
        swi = swi_grib2['swi'][python_swi_index] / 10
        
        # VBA: first_tunk = swi_grib2.first_tunk(swi_index) / 10
        first_tunk = swi_grib2['first_tunk'][python_swi_index] / 10
        
        # VBA: second_tunk = swi_grib2.second_tunk(swi_index) / 10
        second_tunk = swi_grib2['second_tunk'][python_swi_index] / 10
        
        # VBA: third_tunk = swi - first_tunk - second_tunk
        third_tunk = swi - first_tunk - second_tunk
        
        # VBA: guidance_index = get_data_num(m.lat, m.lon, guidance_grib2.base_info)
        guidance_index = self.get_data_num(mesh.lat, mesh.lon, guidance_grib2['base_info'])
        python_guidance_index = guidance_index - 1
        
        # VBA: ReDim swi_time_siries(UBound(guidance_grib2.data) + 1)
        swi_time_series = []
        
        # VBA: swi_time_siries(1).ft = 0
        # VBA: swi_time_siries(1).value = swi
        swi_time_series.append(SwiTimeSeries(ft=0, value=swi))
        
        # VBA: tmp_f = 0, tmp_s = 0, tmp_t = 0
        tmp_f = first_tunk
        tmp_s = second_tunk  
        tmp_t = third_tunk
        
        # VBA: For i = 1 To UBound(guidance_grib2.data)
        for i in range(len(guidance_grib2['data'])):  # Python 0-based
            guidance_item = guidance_grib2['data'][i]
            
            if python_guidance_index < len(guidance_item['value']):
                # VBA: Call calc_tunk_model(first_tunk, second_tunk, third_tunk, 3, guidance_grib2.data(i).value(guidance_index), tmp_f, tmp_s, tmp_t)
                rain_value = guidance_item['value'][python_guidance_index]
                tmp_f, tmp_s, tmp_t = self.calc_tunk_model(tmp_f, tmp_s, tmp_t, 3, rain_value)
                
                # VBA: swi_time_siries(i + 1).ft = guidance_grib2.data(i).ft
                # VBA: swi_time_siries(i + 1).value = tmp_f + tmp_s + tmp_t
                swi_value = tmp_f + tmp_s + tmp_t
                swi_time_series.append(SwiTimeSeries(
                    ft=guidance_item['ft'],
                    value=swi_value
                ))
        
        return swi_time_series

def test_vba_calculation():
    """VBA計算の完全テスト"""
    import sys
    import os
    sys.path.append(os.path.dirname(__file__))
    
    from services.grib2_service import Grib2Service
    from services.data_service import DataService
    
    print("=== VBA計算完全再現テスト ===")
    
    try:
        # サービス初期化
        grib2_service = Grib2Service()
        data_service = DataService()
        vba_calc = VBACalculationRewrite()
        
        # データ取得
        swi_file = "data/Z__C_RJTD_20230602000000_SRF_GPV_Ggis1km_Psw_Aper10min_ANAL_grib2.bin"
        guidance_file = "data/guid_msm_grib2_20230602000000_rmax00.bin"
        
        swi_base_info, swi_result = grib2_service.unpack_swi_grib2_from_file(swi_file)
        guidance_base_info, guidance_result = grib2_service.unpack_guidance_grib2_from_file(guidance_file)
        
        print(f"SWI data length: {len(swi_result['swi'])}")
        print(f"Guidance data count: {len(guidance_result['data'])}")
        
        # 滋賀県データ準備
        prefectures = data_service.prepare_areas()
        shiga = next((p for p in prefectures if p.code == "shiga"), None)
        first_mesh = shiga.areas[0].meshes[0]
        
        print(f"Test mesh: {first_mesh.code} (x:{first_mesh.x}, y:{first_mesh.y})")
        
        # VBA完全再現計算
        print("\n=== Rain計算 ===")
        rain_timeline = vba_calc.calc_rain_timelapse(first_mesh, guidance_result)
        
        for i, item in enumerate(rain_timeline[:6]):
            print(f"FT={item.ft}: {item.value}")
        
        print("\n=== SWI計算 ===")
        swi_timeline = vba_calc.calc_swi_timelapse(first_mesh, swi_result, guidance_result)
        
        for i, item in enumerate(swi_timeline[:6]):
            print(f"FT={item.ft}: {item.value}")
        
        # 期待値と比較
        print("\n=== 期待値比較 ===")
        expected_rain = [50, 26, 19, 28, 8, 3]  # CSV期待値
        expected_swi = 93.0  # CSV期待値
        
        print("Rain比較:")
        for i, (actual, expected) in enumerate(zip(rain_timeline[:6], expected_rain)):
            match = "✓" if abs(actual.value - expected) < 0.1 else "✗"
            print(f"  FT={actual.ft}: {actual.value} vs {expected} {match}")
        
        if len(swi_timeline) > 0:
            ft0_swi = swi_timeline[0].value
            swi_match = "✓" if abs(ft0_swi - expected_swi) < 0.1 else "✗"
            print(f"SWI比較:")
            print(f"  FT=0: {ft0_swi} vs {expected_swi} {swi_match}")
        
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_vba_calculation()