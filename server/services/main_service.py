# -*- coding: utf-8 -*-
"""
メイン処理サービス
"""
from typing import Dict, List, Any
import logging
from datetime import datetime
import time

from models import Prefecture
from .grib2_service import Grib2Service
from .data_service import DataService
from .calculation_service import CalculationService


logger = logging.getLogger(__name__)


class MainService:
    """メイン処理サービス"""
    
    def __init__(self, data_dir: str = "data"):
        self.grib2_service = Grib2Service()
        self.data_service = DataService(data_dir)
        self.calculation_service = CalculationService()
    
    def main_process_from_files(self, swi_file: str, guidance_file: str) -> Dict[str, Any]:
        """ファイルベースのメイン処理（テスト用）"""
        try:
            start_time = time.time()
            logger.info("GRIB2ファイル解析開始")
            
            # GRIB2データ解析
            grib2_start = time.time()
            base_info, swi_grib2 = self.grib2_service.unpack_swi_grib2_from_file(swi_file)
            _, guidance_grib2 = self.grib2_service.unpack_guidance_grib2_from_file(guidance_file)
            grib2_time = time.time() - grib2_start
            
            logger.info(f"GRIB2解析完了: {grib2_time:.2f}秒")
            logger.info(f"初期時刻: {base_info.initial_date}")
            logger.info(f"SWIデータ数: {len(swi_grib2['swi'])}")
            logger.info(f"ガイダンスデータ数: {len(guidance_grib2['data'])}")
            
            # 地域データ構築
            logger.info("地域データ構築開始")
            area_start = time.time()
            prefectures = self.data_service.prepare_areas()
            area_time = time.time() - area_start
            
            logger.info(f"地域データ構築完了: {area_time:.2f}秒")
            
            # メッシュ計算処理
            logger.info("メッシュ計算処理開始")
            calc_start = time.time()
            
            total_meshes = 0
            for prefecture in prefectures:
                for area in prefecture.areas:
                    # 個別メッシュごとに計算を実行
                    for i, mesh in enumerate(area.meshes):
                        area.meshes[i] = self.calculation_service.process_mesh_calculations(
                            mesh, swi_grib2, guidance_grib2
                        )
                    total_meshes += len(area.meshes)
            
            calc_time = time.time() - calc_start
            logger.info(f"メッシュ計算完了: {calc_time:.2f}秒 ({total_meshes}メッシュ)")
            
            # リスクタイムライン計算
            logger.info("リスクタイムライン計算開始")
            risk_start = time.time()
            
            for prefecture in prefectures:
                for area in prefecture.areas:
                    area.risk_timeline = self.calculation_service.calc_risk_timeline(area.meshes)
            
            risk_time = time.time() - risk_start
            logger.info(f"リスクタイムライン計算完了: {risk_time:.2f}秒")
            
            # 結果構築
            total_time = time.time() - start_time
            
            result = {
                "status": "success",
                "calculation_time": datetime.now().isoformat(),
                "initial_time": base_info.initial_date.isoformat(),
                "note": "フル版: ローカルbinファイルからの実データ（全メッシュ処理）",
                "prefectures": {}
            }
            
            # データ構造を辞書形式に変換
            for prefecture in prefectures:
                pref_data = {
                    "name": prefecture.name,
                    "code": prefecture.code,
                    "areas": []
                }
                
                for area in prefecture.areas:
                    area_data = {
                        "name": area.name,
                        "meshes": [],
                        "risk_timeline": [
                            {"ft": risk.ft, "value": risk.value} 
                            for risk in area.risk_timeline
                        ]
                    }
                    
                    for mesh in area.meshes:
                        mesh_data = {
                            "code": mesh.code,
                            "lat": float(mesh.lat),
                            "lon": float(mesh.lon),
                            "x": int(mesh.x),
                            "y": int(mesh.y),
                            "advisary_bound": int(mesh.advisary_bound),
                            "warning_bound": int(mesh.warning_bound),
                            "dosyakei_bound": int(mesh.dosyakei_bound),
                            "swi_timeline": [
                                {"ft": s.ft, "value": float(s.value)} 
                                for s in mesh.swi
                            ],
                            "rain_timeline": [
                                {"ft": r.ft, "value": float(r.value)} 
                                for r in mesh.rain
                            ]
                        }
                        area_data["meshes"].append(mesh_data)
                    
                    pref_data["areas"].append(area_data)
                
                result["prefectures"][prefecture.code] = pref_data
            
            logger.info(f"総処理時間: {total_time:.2f}秒")
            logger.info(f"処理速度: {total_meshes/total_time:.0f} meshes/second")
            
            return result
            
        except Exception as e:
            logger.error(f"メイン処理エラー: {e}")
            raise
    
    def main_process_from_urls(self, initial_time: datetime) -> Dict[str, Any]:
        """URL ベースのメイン処理"""
        try:
            # URL 構築
            swi_url = f"http://lunar1.fcd.naps.kishou.go.jp/srf/Grib2/Rtn/swi10/{initial_time.strftime('%Y/%m/%d')}/Z__C_RJTD_{initial_time.strftime('%Y%m%d%H%M%S')}_SRF_GPV_Ggis1km_Psw_Aper10min_ANAL_grib2.bin"
            guidance_url = f"http://lunar1.fcd.naps.kishou.go.jp/srf/Grib2/Rtn/gdc/{initial_time.strftime('%Y/%m/%d')}/guid_msm_grib2_{initial_time.strftime('%Y%m%d%H%M%S')}_rmax00.bin"
            
            logger.info(f"SWI URL: {swi_url}")
            logger.info(f"Guidance URL: {guidance_url}")
            
            # GRIB2データダウンロード・解析
            swi_data_bytes = self.grib2_service.download_file(swi_url)
            if not swi_data_bytes:
                raise Exception(f"SWIファイルダウンロード失敗: {swi_url}")
            
            guidance_data_bytes = self.grib2_service.download_file(guidance_url)
            if not guidance_data_bytes:
                raise Exception(f"ガイダンスファイルダウンロード失敗: {guidance_url}")
            
            # データ解析
            base_info, swi_grib2 = self.grib2_service.unpack_swi_grib2(swi_data_bytes)
            _, guidance_grib2 = self.grib2_service.unpack_guidance_grib2(guidance_data_bytes)
            
            # 残りの処理はファイル版と同じ
            return self._process_data(base_info, swi_grib2, guidance_grib2, initial_time)
            
        except Exception as e:
            logger.error(f"URL ベースメイン処理エラー: {e}")
            raise
    
    def _process_data(self, base_info, swi_grib2, guidance_grib2, initial_time: datetime) -> Dict[str, Any]:
        """共通データ処理部分"""
        try:
            # 地域データ構築
            prefectures = self.data_service.prepare_areas()
            
            # メッシュ計算処理
            total_meshes = 0
            for prefecture in prefectures:
                for area in prefecture.areas:
                    for mesh in area.meshes:
                        self.calculation_service.process_mesh_calculations(
                            mesh, swi_grib2, guidance_grib2
                        )
                        total_meshes += 1
            
            # リスクタイムライン計算
            for prefecture in prefectures:
                for area in prefecture.areas:
                    area.risk_timeline = self.calculation_service.calc_risk_timeline(area.meshes)
            
            # 結果構築
            result = {
                "calculation_time": datetime.now().isoformat(),
                "initial_time": initial_time.isoformat(),
                "prefectures": {}
            }
            
            # データ変換は main_process_from_files と同じロジック
            for prefecture in prefectures:
                pref_data = {
                    "name": prefecture.name,
                    "code": prefecture.code,
                    "areas": []
                }
                
                for area in prefecture.areas:
                    area_data = {
                        "name": area.name,
                        "meshes": [],
                        "risk_timeline": [
                            {"ft": risk.ft, "value": risk.value} 
                            for risk in area.risk_timeline
                        ]
                    }
                    
                    for mesh in area.meshes:
                        mesh_data = {
                            "code": mesh.code,
                            "lat": float(mesh.lat),
                            "lon": float(mesh.lon),
                            "x": int(mesh.x),
                            "y": int(mesh.y),
                            "advisary_bound": int(mesh.advisary_bound),
                            "warning_bound": int(mesh.warning_bound),
                            "dosyakei_bound": int(mesh.dosyakei_bound),
                            "swi_timeline": [
                                {"ft": s.ft, "value": float(s.value)} 
                                for s in mesh.swi
                            ],
                            "rain_timeline": [
                                {"ft": r.ft, "value": float(r.value)} 
                                for r in mesh.rain
                            ]
                        }
                        area_data["meshes"].append(mesh_data)
                    
                    pref_data["areas"].append(area_data)
                
                result["prefectures"][prefecture.code] = pref_data
            
            return result
            
        except Exception as e:
            logger.error(f"データ処理エラー: {e}")
            raise