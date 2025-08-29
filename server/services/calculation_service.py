# -*- coding: utf-8 -*-
"""
土壌雨量指数計算サービス
"""
from typing import List, Dict, Any
import logging
from datetime import datetime, timedelta

from models import (
    BaseInfo, SwiTimeSeries, GuidanceTimeSeries, Risk, 
    Mesh, Area, Prefecture
)


logger = logging.getLogger(__name__)


class CalculationService:
    """土壌雨量指数計算サービス"""
    
    # 3段タンクモデルパラメータ (VBAと同じ値)
    L1, L2, L3, L4 = 15.0, 60.0, 15.0, 15.0
    A1, A2, A3, A4 = 0.1, 0.15, 0.05, 0.01
    B1, B2, B3 = 0.12, 0.05, 0.01
    
    def calc_tunk_model(self, s1: float, s2: float, s3: float, r: float, dt: float = 1.0) -> tuple:
        """3段タンクモデル計算（VBAと同じアルゴリズム）"""
        try:
            # 流出量計算
            q1 = self.A1 * max(0, s1 - self.L1) + self.A2 * max(0, s1 - self.L2)
            q2 = self.A3 * max(0, s2 - self.L3)
            q3 = self.A4 * max(0, s3 - self.L4)
            
            # 貯留量更新
            s1_new = (1 - self.B1 * dt) * s1 - q1 * dt + r
            s2_new = (1 - self.B2 * dt) * s2 - q2 * dt + self.B1 * s1 * dt
            s3_new = (1 - self.B3 * dt) * s3 - q3 * dt + self.B2 * s2 * dt
            
            # 負の値を0にクリップ
            s1_new = max(0, s1_new)
            s2_new = max(0, s2_new)
            s3_new = max(0, s3_new)
            
            return s1_new, s2_new, s3_new
            
        except Exception as e:
            logger.error(f"タンクモデル計算エラー: {e}")
            return 0.0, 0.0, 0.0
    
    def calc_swi_timelapse(
        self, 
        mesh: Mesh, 
        swi_grib2: Dict[str, Any], 
        guidance_grib2: Dict[str, Any]
    ) -> List[SwiTimeSeries]:
        """土壌雨量指数時系列計算（元の実装と同じ）"""
        try:
            swi_index = self.get_data_num(mesh.lat, mesh.lon, swi_grib2['base_info'])
            
            if (swi_index >= len(swi_grib2['swi']) or
                swi_index >= len(swi_grib2['first_tunk']) or
                swi_index >= len(swi_grib2['second_tunk'])):
                return []
            
            # 初期値取得
            initial_swi = swi_grib2['swi'][swi_index]
            first_tunk = swi_grib2['first_tunk'][swi_index]  
            second_tunk = swi_grib2['second_tunk'][swi_index]
            
            # NaNや無効値チェック
            if (initial_swi != initial_swi or initial_swi >= 9999 or
                first_tunk != first_tunk or first_tunk >= 9999 or
                second_tunk != second_tunk or second_tunk >= 9999):
                return []
            
            # 初期タンク状態設定（VBAと同じロジック）
            s1 = first_tunk
            s2 = second_tunk
            s3 = initial_swi - first_tunk - second_tunk
            
            result = []
            
            # FT=0の初期値
            result.append(SwiTimeSeries(ft=0, value=initial_swi))
            
            # 予測値計算
            for i, guidance_values in enumerate(guidance_grib2['data']):
                if swi_index < len(guidance_values):
                    rain = guidance_values[swi_index]
                    
                    # NaNや無効値チェック
                    if rain != rain or rain >= 9999:  # NaN check
                        rain = 0.0
                    
                    # タンクモデル計算
                    s1, s2, s3 = self.calc_tunk_model(s1, s2, s3, rain, 1.0)
                    swi_value = s1 + s2 + s3
                    
                    ft = (i + 1) * 3  # 3時間間隔
                    result.append(SwiTimeSeries(ft=ft, value=swi_value))
            
            return result
            
        except Exception as e:
            logger.error(f"SWI時系列計算エラー: {e}")
            return []
    
    def calc_rain_timelapse(
        self, 
        mesh: Mesh, 
        guidance_grib2: Dict[str, Any]
    ) -> List[GuidanceTimeSeries]:
        """降水量時系列計算（元の実装と同じ）"""
        try:
            rain_index = self.get_data_num(mesh.lat, mesh.lon, guidance_grib2['base_info'])
            
            result = []
            
            for i, guidance_values in enumerate(guidance_grib2['data']):
                if rain_index < len(guidance_values):
                    rain = guidance_values[rain_index]
                    
                    # NaNや無効値チェック
                    if rain != rain or rain >= 9999:  # NaN check
                        rain = 0.0
                    
                    ft = (i + 1) * 3  # 3時間間隔
                    result.append(GuidanceTimeSeries(ft=ft, value=rain))
            
            return result
            
        except Exception as e:
            logger.error(f"降水量時系列計算エラー: {e}")
            return []
    
    def calc_risk_timeline(self, area: Area) -> List[Risk]:
        """リスクレベル判定（VBAのcalc_risk_timelineロジック）"""
        try:
            if not area.meshes:
                return []
            
            # 最初のメッシュからFT情報を取得
            first_mesh = area.meshes[0]
            if not first_mesh.swi:
                return []
            
            result = []
            
            for swi_data in first_mesh.swi:
                ft = swi_data.ft
                risk_level = 0
                
                # 各メッシュの最高リスクレベルを計算
                for mesh in area.meshes:
                    # 該当FTのSWI値を取得
                    mesh_swi = None
                    for mesh_swi_data in mesh.swi:
                        if mesh_swi_data.ft == ft:
                            mesh_swi = mesh_swi_data.value
                            break
                    
                    if mesh_swi is not None:
                        # VBAと同じリスクレベル判定
                        mesh_risk = 0
                        if mesh_swi >= mesh.dosyakei_bound:
                            mesh_risk = 3  # 土砂災害
                        elif mesh_swi >= mesh.warning_bound:
                            mesh_risk = 2  # 警報
                        elif mesh_swi >= mesh.advisary_bound:
                            mesh_risk = 1  # 注意報
                        
                        risk_level = max(risk_level, mesh_risk)
                
                result.append(Risk(ft=ft, value=risk_level))
            
            return result
            
        except Exception as e:
            logger.error(f"リスク計算エラー: {e}")
            return []
    
    def get_data_num(self, lat: float, lon: float, base_info: BaseInfo) -> int:
        """緯度経度からデータ番号を計算"""
        try:
            # ミリ度に変換
            lat_milli = int(lat * 1000000)
            lon_milli = int(lon * 1000000)
            
            # グリッドインデックス計算
            x = int((lon_milli - base_info.s_lon) / base_info.d_lon)
            y = int((base_info.e_lat - lat_milli) / base_info.d_lat)
            
            # 範囲チェック
            if x < 0 or x >= base_info.x_num or y < 0 or y >= base_info.y_num:
                return -1
            
            # データ番号計算
            data_num = y * base_info.x_num + x
            
            return data_num if data_num < base_info.grid_num else -1
            
        except Exception as e:
            logger.error(f"データ番号変換エラー: lat={lat}, lon={lon} - {e}")
            return -1
    
    def process_mesh_calculations(
        self,
        mesh: Mesh,
        swi_grib2: Dict[str, Any],
        guidance_grib2: Dict[str, Any]
    ) -> Mesh:
        """メッシュごとの計算処理（元の実装と同じ）"""
        try:
            # SWI時系列計算
            mesh.swi = self.calc_swi_timelapse(mesh, swi_grib2, guidance_grib2)
            
            # 降水量時系列計算
            mesh.rain = self.calc_rain_timelapse(mesh, guidance_grib2)
            
            return mesh
            
        except Exception as e:
            logger.error(f"メッシュ計算エラー: {mesh.code} - {e}")
            # エラーの場合も空のリストを設定
            mesh.swi = []
            mesh.rain = []
            return mesh