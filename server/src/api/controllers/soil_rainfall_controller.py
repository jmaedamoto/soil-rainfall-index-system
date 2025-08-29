# -*- coding: utf-8 -*-
"""
土壌雨量指数APIコントローラー
"""
from flask import request, jsonify
from typing import Dict, Any, Tuple
import logging
import os
from datetime import datetime

from services import MainService

logger = logging.getLogger(__name__)


class SoilRainfallController:
    """土壌雨量指数APIコントローラー"""
    
    def __init__(self):
        self.main_service = MainService()
    
    def test_full_soil_rainfall_index(self) -> Tuple[Dict[str, Any], int]:
        """テスト用：binファイルを使って全メッシュのmain_processと同じ形式のJSONを返す（API層使用）"""
        try:
            data_dir = "data"
            
            # binファイルのパス
            swi_file = os.path.join(data_dir, "Z__C_RJTD_20250101000000_SRF_GPV_Ggis1km_Psw_Aper10min_ANAL_grib2.bin")
            guidance_file = os.path.join(data_dir, "guid_msm_grib2_20250101000000_rmax00.bin")
            
            # ファイル存在確認
            if not os.path.exists(swi_file):
                return {
                    "status": "error",
                    "error": "SWI binファイルが見つかりません",
                    "timestamp": datetime.now().isoformat()
                }, 500
                
            if not os.path.exists(guidance_file):
                return {
                    "status": "error",
                    "error": "ガイダンス binファイルが見つかりません",
                    "timestamp": datetime.now().isoformat()
                }, 500
            
            # MainServiceを使用してメイン処理実行
            logger.info("API層：サービス層でメイン処理実行中...")
            result = self.main_service.main_process_from_files(swi_file, guidance_file)
            
            logger.info("API層：サービス層でのメイン処理完了")
            return result, 200
            
        except Exception as e:
            logger.error(f"API層：フル土壌雨量指数計算エラー: {e}")
            return {
                "status": "error",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }, 500
    
    def health_check(self) -> Tuple[Dict[str, Any], int]:
        """ヘルスチェックエンドポイント"""
        return {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "service": "soil-rainfall-index-api",
            "version": "step3-api-layer"
        }, 200
    
    def data_check(self) -> Tuple[Dict[str, Any], int]:
        """データファイル確認エンドポイント"""
        try:
            data_dir = "data"
            
            # CSVファイル確認
            csv_files = []
            prefectures = ['shiga', 'kyoto', 'osaka', 'hyogo', 'nara', 'wakayama']
            
            for pref in prefectures:
                dosha_file = os.path.join(data_dir, f"dosha_{pref}.csv")
                dosyakei_file = os.path.join(data_dir, f"dosyakei_{pref}.csv")
                
                csv_files.append({
                    "prefecture": pref,
                    "dosha_file": {
                        "path": dosha_file,
                        "exists": os.path.exists(dosha_file)
                    },
                    "dosyakei_file": {
                        "path": dosyakei_file,
                        "exists": os.path.exists(dosyakei_file)
                    }
                })
            
            # GRIB2ファイル確認
            swi_file = os.path.join(data_dir, "Z__C_RJTD_20250101000000_SRF_GPV_Ggis1km_Psw_Aper10min_ANAL_grib2.bin")
            guidance_file = os.path.join(data_dir, "guid_msm_grib2_20250101000000_rmax00.bin")
            
            return {
                "status": "success",
                "timestamp": datetime.now().isoformat(),
                "data_files": {
                    "csv_files": csv_files,
                    "grib2_files": {
                        "swi_file": {
                            "path": swi_file,
                            "exists": os.path.exists(swi_file)
                        },
                        "guidance_file": {
                            "path": guidance_file,
                            "exists": os.path.exists(guidance_file)
                        }
                    }
                }
            }, 200
            
        except Exception as e:
            logger.error(f"API層：データチェックエラー: {e}")
            return {
                "status": "error",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }, 500