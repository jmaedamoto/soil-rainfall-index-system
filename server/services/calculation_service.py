#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
VBA Module.basの完全再現によるCalculationService
既存のcalculation_service.pyを完全に置き換え
"""

from typing import List, Dict, Any, Tuple
import logging
from datetime import datetime, timedelta

from models import (
    BaseInfo, SwiTimeSeries, GuidanceTimeSeries, Risk, 
    Mesh, Area, Prefecture
)

logger = logging.getLogger(__name__)

class CalculationService:
    """VBA Module.basの完全再現によるCalculationService"""
    
    # VBA タンクモデルパラメータ (完全同一)
    l1, l2, l3, l4 = 15.0, 60.0, 15.0, 15.0
    a1, a2, a3, a4 = 0.1, 0.15, 0.05, 0.01
    b1, b2, b3 = 0.12, 0.05, 0.01

    def get_data_num(self, lat: float, lon: float, base_info: Any) -> int:
        """
        VBA Function get_data_num の完全再現
        VBA 1-based戻り値をそのまま返す（Python配列アクセス時に-1）
        """
        # VBA: y = Int((base_info.s_lat / 1000000 - lat) / (base_info.d_lat / 1000000)) + 1
        y = int((base_info.s_lat / 1000000 - lat) / (base_info.d_lat / 1000000)) + 1

        # VBA: x = Int((lon - base_info.s_lon / 1000000) / (base_info.d_lon / 1000000)) + 1
        x = int((lon - base_info.s_lon / 1000000) / (base_info.d_lon / 1000000)) + 1

        # VBA: get_data_num = (y - 1) * base_info.x_num + x
        return (y - 1) * base_info.x_num + x

    def get_data_num_from_vba_coordinates(self, vba_x: int, vba_y: int, base_info: Any) -> int:
        """
        VBA座標の処理は通常の緯度経度変換経由で行う
        VBA Module.basの実装と同じ方式に戻す
        """
        # VBA座標をメッシュコードに変換してから緯度経度を取得
        # これはdataServiceでのmeshcode_to_coordinateと同等の処理
        try:
            # VBA座標からメッシュコード様式の座標を復元
            # 通常のget_data_num関数を使用するために緯度経度変換を行う
            lat, lon = self.vba_coordinates_to_latlon(vba_x, vba_y)

            # VBA: get_data_num(lat, lon, base_info)と同じ処理
            return self.get_data_num(lat, lon, base_info)

        except Exception as e:
            logger.error(f"Error in get_data_num_from_vba_coordinates for ({vba_x}, {vba_y}): {e}")
            return 1  # エラー時のデフォルト値

    def vba_coordinates_to_latlon(self, vba_x: int, vba_y: int) -> tuple[float, float]:
        """
        VBA座標から緯度経度を計算
        メッシュコード変換ロジックに基づく
        """
        try:
            # VBA座標をメッシュコード形式として解釈
            lat = (vba_y + 0.5) * 30 / 3600  # メッシュコード変換式
            lon = (vba_x + 0.5) * 45 / 3600 + 100  # メッシュコード変換式
            return lat, lon
        except Exception:
            return 35.0, 135.0  # デフォルト座標（関西地方中央）

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
        
        # VBA: s2_new = (1 - b2 * t) * s2 - q2 * t + b1 * s1 * t
        s2_new = (1 - self.b2 * t) * s2 - q2 * t + self.b1 * s1 * t

        # VBA: s3_new = (1 - b3 * t) * s3 - q3 * t + b2 * s2 * t
        s3_new = (1 - self.b3 * t) * s3 - q3 * t + self.b2 * s2 * t
        
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
        try:
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
            
        except Exception as e:
            logger.error(f"Rain calculation error for mesh {mesh.code}: {e}")
            return []

    def calc_swi_timelapse(self, mesh: Mesh, swi_grib2: Dict[str, Any], guidance_grib2: Dict[str, Any]) -> List[SwiTimeSeries]:
        """
        VBA Function calc_swi_timelapse の完全再現
        """
        try:
            # VBA: swi_index = get_data_num(m.lat, m.lon, swi_grib2.base_info)
            swi_index = self.get_data_num(mesh.lat, mesh.lon, swi_grib2['base_info'])
            guidance_index = self.get_data_num(mesh.lat, mesh.lon, guidance_grib2['base_info'])

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
            
            # guidance_indexは上で既に計算済み
            python_guidance_index = guidance_index - 1
            
            # VBA: ReDim swi_time_siries(UBound(guidance_grib2.data) + 1)
            swi_time_series = []
            
            # VBA: swi_time_siries(1).ft = 0
            # VBA: swi_time_siries(1).value = swi
            swi_time_series.append(SwiTimeSeries(ft=0, value=swi))
            
            # VBA: tmp_f = 0, tmp_s = 0, tmp_t = 0 (VBAでは初期化)
            # しかし実際には初期タンク値が使用される
            current_first_tunk = first_tunk
            current_second_tunk = second_tunk
            current_third_tunk = third_tunk

            # VBA: For i = 1 To UBound(guidance_grib2.data)
            for i in range(len(guidance_grib2['data'])):  # Python 0-based
                guidance_item = guidance_grib2['data'][i]

                if python_guidance_index < len(guidance_item['value']):
                    # VBA: Call calc_tunk_model(first_tunk, second_tunk, third_tunk, 3, guidance_grib2.data(i).value(guidance_index), tmp_f, tmp_s, tmp_t)
                    rain_value = guidance_item['value'][python_guidance_index]
                    tmp_f, tmp_s, tmp_t = self.calc_tunk_model(current_first_tunk, current_second_tunk, current_third_tunk, 3, rain_value)

                    # VBA: swi_time_siries(i + 1).ft = guidance_grib2.data(i).ft
                    # VBA: swi_time_siries(i + 1).value = tmp_f + tmp_s + tmp_t
                    swi_value = tmp_f + tmp_s + tmp_t
                    swi_time_series.append(SwiTimeSeries(
                        ft=guidance_item['ft'],
                        value=swi_value
                    ))

                    # VBA: first_tunk = tmp_f, second_tunk = tmp_s, third_tunk = tmp_t
                    current_first_tunk = tmp_f
                    current_second_tunk = tmp_s
                    current_third_tunk = tmp_t
            
            return swi_time_series
            
        except Exception as e:
            logger.error(f"SWI calculation error for mesh {mesh.code}: {e}")
            return []

    def calc_risk_timeline(self, meshes: List[Mesh]) -> List[Risk]:
        """
        VBA Function calc_risk_timeline の完全再現
        リスクレベル計算
        """
        try:
            # 詳細デバッグログ
            logger.info(f"=== calc_risk_timeline called with {len(meshes) if isinstance(meshes, list) else 'invalid'} meshes ===")

            # 入力データ型の確認
            if not isinstance(meshes, list):
                logger.error(f"Risk calculation error: meshes is not a list, got {type(meshes)}")
                return []

            if not meshes:
                logger.error("Risk calculation error: meshes list is empty")
                return []

            # 最初のメッシュのSWIデータ確認
            first_mesh = meshes[0]
            logger.info(f"First mesh: code={getattr(first_mesh, 'code', 'no code')}, has swi attr: {hasattr(first_mesh, 'swi')}")

            if not hasattr(first_mesh, 'swi') or not first_mesh.swi:
                logger.error(f"Risk calculation error: first mesh has no swi data. Has swi attr: {hasattr(first_mesh, 'swi')}, swi length: {len(first_mesh.swi) if hasattr(first_mesh, 'swi') and first_mesh.swi else 0}")
                return []

            # 時系列の長さを取得
            timeline_length = len(first_mesh.swi)
            logger.info(f"Timeline length: {timeline_length}")
            logger.info(f"First mesh boundaries: advisory={getattr(first_mesh, 'advisary_bound', 'N/A')}, warning={getattr(first_mesh, 'warning_bound', 'N/A')}, dosyakei={getattr(first_mesh, 'dosyakei_bound', 'N/A')}")
            logger.info(f"First 3 SWI values: {[first_mesh.swi[i].value for i in range(min(3, timeline_length))]}")

            risk_timeline = []

            for t in range(timeline_length):
                ft = first_mesh.swi[t].ft
                max_risk = 0

                for mesh in meshes:
                    if not hasattr(mesh, 'swi') or not mesh.swi:
                        continue

                    if t < len(mesh.swi):
                        swi_value = mesh.swi[t].value

                        # VBAリスクレベル判定
                        if swi_value >= mesh.dosyakei_bound:
                            risk = 3  # 土砂災害
                        elif swi_value >= mesh.warning_bound:
                            risk = 2  # 警報
                        elif swi_value >= mesh.advisary_bound:
                            risk = 1  # 注意
                        else:
                            risk = 0  # 正常

                        max_risk = max(max_risk, risk)

                risk_timeline.append(Risk(ft=ft, value=max_risk))

            logger.info(f"Risk timeline calculated: {len(risk_timeline)} entries")
            if risk_timeline:
                logger.info(f"First 3 risk values: {[(r.ft, r.value) for r in risk_timeline[:3]]}")

            return risk_timeline

        except Exception as e:
            logger.error(f"Risk calculation error: {e}")
            logger.error(f"meshes type: {type(meshes)}")
            if isinstance(meshes, list) and meshes:
                logger.error(f"first mesh type: {type(meshes[0])}")
            import traceback
            logger.error(f"Risk calculation traceback: {traceback.format_exc()}")
            return []

    def process_mesh_calculations(self, mesh: Mesh, swi_grib2: Dict[str, Any], guidance_grib2: Dict[str, Any]) -> Mesh:
        """
        VBA calc_data の一部処理
        単一メッシュの計算を実行
        """
        try:
            # VBA: prefectures(i).areas(j).meshes(k).swi = calc_swi_timelapse(...)
            mesh.swi = self.calc_swi_timelapse(mesh, swi_grib2, guidance_grib2)

            # VBA: prefectures(i).areas(j).meshes(k).rain = calc_rain_timelapse(...)
            mesh.rain = self.calc_rain_timelapse(mesh, guidance_grib2)

            return mesh

        except Exception as e:
            logger.error(f"Mesh calculations error: {e}")
            return mesh

    def process_area_calculations(self, areas: List[Area]) -> None:
        """
        VBA calc_data の一部処理
        各エリアのリスク計算を実行
        """
        try:
            for area in areas:
                # VBA: prefectures(i).areas(j).risk_timeline = calc_risk_timeline(prefectures(i).areas(j).meshes)
                area.risk_timeline = self.calc_risk_timeline(area.meshes)
                
        except Exception as e:
            logger.error(f"Area calculations error: {e}")

    # 既存の互換性のため、古いメソッド名も保持
    def calc_tunk_model_legacy(self, s1: float, s2: float, s3: float, dt: float, r: float) -> Tuple[float, float, float]:
        """既存コードとの互換性のため"""
        return self.calc_tunk_model(s1, s2, s3, dt, r)