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
from services.cache_service import get_cache_service
from src.config.config_service import ConfigService


logger = logging.getLogger(__name__)


class MainController:
    """メインAPIコントローラー"""

    def __init__(self, data_dir: str = "data", session_service=None):
        self.main_service = MainService(data_dir)
        self.cache_service = get_cache_service()
        self.config_service = ConfigService()
        self.session_service = session_service
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
                # 自動時刻設定（UTC現在時刻の3時間前、6時間区切り）
                now = datetime.utcnow()
                hours_ago = now - timedelta(hours=3)
                # 6時間区切りに調整（0, 6, 12, 18時）
                hour = (hours_ago.hour // 6) * 6
                initial_time = hours_ago.replace(hour=hour, minute=0, second=0, microsecond=0)
            
            logger.info(f"本番テスト実行: 初期時刻={initial_time}")
            
            # メイン処理実行
            result = self.main_service.main_process_from_urls(initial_time)
            result["status"] = "success"

            # 使用したURLも返却（デバッグ用）
            swi_url = self.config_service.build_swi_url(initial_time)
            guidance_url = self.config_service.build_guidance_url(initial_time)

            result["used_urls"] = {
                "swi_url": swi_url,
                "guidance_url": guidance_url
            }
            
            return jsonify(result)
            
        except Exception as e:
            logger.error(f"本番テスト処理エラー: {e}")
            error_urls = {}
            if 'initial_time' in locals():
                error_urls = {
                    "swi_url": self.config_service.build_swi_url(initial_time),
                    "guidance_url": self.config_service.build_guidance_url(initial_time)
                }
            return jsonify({
                "status": "error",
                "message": str(e),
                "used_urls": error_urls if error_urls else {"swi_url": "N/A", "guidance_url": "N/A"}
            }), 500

    def production_soil_rainfall_index_with_urls(self):
        """本番テスト用エンドポイント（SWIとガイダンスの初期時刻を個別指定）"""
        try:
            data = request.get_json()
            if not data:
                return jsonify({
                    "status": "error",
                    "message": "リクエストデータが必要です"
                }), 400

            # SWI初期時刻取得
            swi_initial_str = data.get('swi_initial')
            if not swi_initial_str:
                return jsonify({
                    "status": "error",
                    "message": "swi_initialパラメータが必要です"
                }), 400

            # ガイダンス初期時刻取得
            guidance_initial_str = data.get('guidance_initial')
            if not guidance_initial_str:
                return jsonify({
                    "status": "error",
                    "message": "guidance_initialパラメータが必要です"
                }), 400

            # ISO8601形式の日時パース
            try:
                swi_initial = datetime.fromisoformat(swi_initial_str.replace('Z', '+00:00'))
                swi_initial = swi_initial.replace(tzinfo=None)
            except ValueError as e:
                return jsonify({
                    "status": "error",
                    "message": f"swi_initial日時形式エラー: {e}"
                }), 400

            try:
                guidance_initial = datetime.fromisoformat(guidance_initial_str.replace('Z', '+00:00'))
                guidance_initial = guidance_initial.replace(tzinfo=None)
            except ValueError as e:
                return jsonify({
                    "status": "error",
                    "message": f"guidance_initial日時形式エラー: {e}"
                }), 400

            logger.info(f"本番テスト実行: SWI初期時刻={swi_initial}, ガイダンス初期時刻={guidance_initial}")

            # 設定ファイルからURL構築
            swi_url = self.config_service.build_swi_url(swi_initial)
            guidance_url = self.config_service.build_guidance_url(guidance_initial)

            # キャッシュキー生成
            cache_key = self.cache_service.generate_cache_key(
                swi_initial.isoformat(),
                guidance_initial.isoformat()
            )

            # キャッシュ存在確認
            cache_exists = self.cache_service.exists(cache_key)
            cache_metadata = None
            if cache_exists:
                cache_metadata = self.cache_service.get_metadata(cache_key)

            # メイン処理実行（個別URLを使用、use_cache=True でキャッシュ有効）
            result = self.main_service.main_process_from_separate_urls(
                swi_url, guidance_url, use_cache=True)

            # セッションサービスが有効な場合、セッション作成して軽量レスポンスを返す
            if self.session_service:
                # セッション作成
                session_id = self.session_service.create_session(
                    result['prefectures'],
                    swi_initial.isoformat(),
                    guidance_initial.isoformat(),
                    datetime.now().isoformat()
                )

                # 利用可能な時刻を抽出（最初のメッシュから）
                available_times = []
                first_pref = next(iter(result['prefectures'].values()))
                if first_pref.areas and first_pref.areas[0].meshes:
                    first_mesh = first_pref.areas[0].meshes[0]
                    available_times = sorted(set(
                        [point.ft for point in first_mesh.risk_3hour_max_timeline] +
                        [point.ft for point in first_mesh.risk_hourly_timeline]
                    ))

                # 軽量レスポンスを返す
                return jsonify({
                    "status": "success",
                    "session_id": session_id,
                    "swi_initial_time": swi_initial.isoformat(),
                    "guidance_initial_time": guidance_initial.isoformat(),
                    "available_prefectures": list(result['prefectures'].keys()),
                    "available_times": available_times,
                    "cache_info": {
                        "cache_key": cache_key,
                        "cache_hit": cache_exists,
                        "cache_metadata": cache_metadata
                    },
                    "used_urls": {
                        "swi_url": swi_url,
                        "swi_initial_time": swi_initial.isoformat(),
                        "guidance_url": guidance_url,
                        "guidance_initial_time": guidance_initial.isoformat()
                    }
                })

            # セッションサービスが無効な場合、従来通り全データを返す
            result["status"] = "success"

            # 使用したURLとキャッシュ情報も返却
            result["used_urls"] = {
                "swi_url": swi_url,
                "swi_initial_time": swi_initial.isoformat(),
                "guidance_url": guidance_url,
                "guidance_initial_time": guidance_initial.isoformat()
            }

            result["cache_info"] = {
                "cache_key": cache_key,
                "cache_hit": cache_exists,
                "cache_metadata": cache_metadata
            }

            return jsonify(result)

        except Exception as e:
            logger.error(f"本番テスト処理エラー: {e}")
            return jsonify({
                "status": "error",
                "message": str(e)
            }), 500