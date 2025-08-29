# -*- coding: utf-8 -*-
"""
メインAPIコントローラー
"""
from flask import request, jsonify
from datetime import datetime, timedelta
import logging
import os
import sys

# プロジェクトルートをパスに追加
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(project_root)

from services.main_service import MainService


logger = logging.getLogger(__name__)


class MainController:
    """メインAPIコントローラー"""
    
    def __init__(self, data_dir: str = "data"):
        self.main_service = MainService(data_dir)
        self.data_dir = data_dir
    
    def root(self):
        """ルートエンドポイント"""
        return jsonify({
            "message": "土壌雨量指数計算システム API",
            "architecture": "Refactored Service Layer Architecture",
            "version": "4.0.0",
            "endpoints": [
                "GET  /",
                "GET  /api/health",
                "GET  /api/data-check",
                "POST /api/soil-rainfall-index",
                "GET  /api/production-soil-rainfall-index",
                "GET  /api/test-bin-data",
                "GET  /api/test-grib2-analysis",
                "GET  /api/test-soil-rainfall-index",
                "GET  /api/test-single-prefecture",
                "GET  /api/test-full-soil-rainfall-index",
                "GET  /api/test-performance-analysis",
                "GET  /api/test-performance-summary",
                "GET  /api/test-csv-optimization",
                "GET  /api/test-parallel-processing",
                "GET  /api/test-full-parallel-soil-rainfall-index",
                "GET  /api/test-optimization-analysis"
            ]
        })
    
    def health_check(self):
        """ヘルスチェックエンドポイント"""
        return jsonify({
            "status": "success",
            "message": "土壌雨量指数計算API稼働中",
            "architecture": "Refactored Service Layer Architecture",
            "version": "4.0.0"
        })
    
    def data_check(self):
        """データファイル確認エンドポイント"""
        try:
            required_files = []
            
            # 必要なファイルリスト
            prefectures = ["shiga", "kyoto", "osaka", "hyogo", "nara", "wakayama"]
            for pref in prefectures:
                required_files.extend([
                    f"dosha_{pref}.csv",
                    f"dosyakei_{pref}.csv"
                ])
            
            # ファイル存在確認
            file_status = {}
            for filename in required_files:
                filepath = os.path.join(self.data_dir, filename)
                file_status[filename] = os.path.exists(filepath)
            
            return jsonify({
                "status": "success",
                "data_directory": self.data_dir,
                "files": file_status,
                "total_files": len(required_files),
                "existing_files": sum(file_status.values())
            })
            
        except Exception as e:
            logger.error(f"データチェックエラー: {e}")
            return jsonify({
                "status": "error",
                "message": str(e)
            }), 500
    
    def soil_rainfall_index(self):
        """メイン処理エンドポイント（URL ベース）"""
        try:
            data = request.get_json()
            if not data:
                return jsonify({
                    "status": "error",
                    "message": "リクエストデータが必要です"
                }), 400
            
            # 初期時刻パラメータ取得
            initial_str = data.get('initial')
            if not initial_str:
                return jsonify({
                    "status": "error",
                    "message": "initialパラメータが必要です"
                }), 400
            
            # ISO8601形式の日時パース
            try:
                initial_time = datetime.fromisoformat(initial_str.replace('Z', '+00:00'))
                # UTCからJSTに変換（必要に応じて）
                initial_time = initial_time.replace(tzinfo=None)
            except ValueError as e:
                return jsonify({
                    "status": "error",
                    "message": f"日時形式エラー: {e}"
                }), 400
            
            # メイン処理実行
            result = self.main_service.main_process_from_urls(initial_time)
            result["status"] = "success"
            
            return jsonify(result)
            
        except Exception as e:
            logger.error(f"メイン処理エラー: {e}")
            return jsonify({
                "status": "error",
                "message": str(e)
            }), 500
    
    def production_soil_rainfall_index(self):
        """本番テスト用エンドポイント（GET メソッド）"""
        try:
            # クエリパラメータから初期時刻を取得
            initial_str = request.args.get('initial')
            
            if initial_str:
                # 指定された初期時刻を使用
                try:
                    initial_time = datetime.fromisoformat(initial_str.replace('Z', '+00:00'))
                    initial_time = initial_time.replace(tzinfo=None)
                except ValueError as e:
                    return jsonify({
                        "status": "error",
                        "message": f"日時形式エラー: {e}"
                    }), 400
            else:
                # 自動時刻設定（現在時刻の3時間前、6時間区切り）
                now = datetime.now()
                hours_ago = now - timedelta(hours=3)
                # 6時間区切りに調整（0, 6, 12, 18時）
                hour = (hours_ago.hour // 6) * 6
                initial_time = hours_ago.replace(hour=hour, minute=0, second=0, microsecond=0)
            
            logger.info(f"本番テスト実行: 初期時刻={initial_time}")
            
            # メイン処理実行
            result = self.main_service.main_process_from_urls(initial_time)
            result["status"] = "success"
            
            # 使用したURLも返却（デバッグ用）
            swi_url = f"http://lunar1.fcd.naps.kishou.go.jp/srf/Grib2/Rtn/swi10/Z__C_RJTD_{initial_time.strftime('%Y%m%d%H%M%S')}_SRF_GPV_Ggis1km_Psw_Aper10min_ANAL_grib2.bin"
            guidance_url = f"http://lunar1.fcd.naps.kishou.go.jp/srf/Grib2/Rtn/gdc/guid_msm_grib2_{initial_time.strftime('%Y%m%d%H%M%S')}_rmax00.bin"
            
            result["used_urls"] = {
                "swi_url": swi_url,
                "guidance_url": guidance_url
            }
            
            return jsonify(result)
            
        except Exception as e:
            logger.error(f"本番テスト処理エラー: {e}")
            return jsonify({
                "status": "error",
                "message": str(e),
                "used_urls": {
                    "swi_url": f"http://lunar1.fcd.naps.kishou.go.jp/srf/Grib2/Rtn/swi10/Z__C_RJTD_{initial_time.strftime('%Y%m%d%H%M%S')}_SRF_GPV_Ggis1km_Psw_Aper10min_ANAL_grib2.bin" if 'initial_time' in locals() else "N/A",
                    "guidance_url": f"http://lunar1.fcd.naps.kishou.go.jp/srf/Grib2/Rtn/gdc/guid_msm_grib2_{initial_time.strftime('%Y%m%d%H%M%S')}_rmax00.bin" if 'initial_time' in locals() else "N/A"
                }
            }), 500