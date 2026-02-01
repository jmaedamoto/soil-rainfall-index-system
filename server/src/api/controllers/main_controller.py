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
from config.config_service import ConfigService


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
            "endpoints": {
                "main": [
                    "GET  /",
                    "GET  /health",
                    "GET  /data-check",
                    "POST /soil-rainfall-index",
                    "GET  /production-soil-rainfall-index",
                    "POST /production-soil-rainfall-index-with-urls",
                    "POST /test-session-with-local-bins"
                ],
                "cache": [
                    "GET    /cache/list",
                    "GET    /cache/stats",
                    "GET    /cache/<cache_key>",
                    "GET    /cache/<cache_key>/exists",
                    "DELETE /cache/<cache_key>",
                    "POST   /cache/cleanup"
                ],
                "rainfall": [
                    "GET  /rainfall-forecast",
                    "POST /rainfall-adjustment"
                ],
                "session": [
                    "GET    /session/<session_id>",
                    "GET    /session/<session_id>/prefecture/<prefecture_code>",
                    "GET    /session/<session_id>/risk-at-time?ft=<ft>",
                    "GET    /session/<session_id>/mesh/<mesh_code>",
                    "GET    /session/<session_id>/rainfall-data",
                    "POST   /session/<session_id>/recalculate",
                    "DELETE /session/<session_id>",
                    "GET    /sessions",
                    "GET    /sessions/stats",
                    "POST   /sessions/cleanup"
                ],
                "test": [
                    "GET  /test-bin-data",
                    "GET  /test-grib2-analysis",
                    "GET  /test-soil-rainfall-index",
                    "GET  /test-single-prefecture",
                    "GET  /test-full-soil-rainfall-index",
                    "GET  /test-full-parallel-soil-rainfall-index"
                ]
            }
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
        """
        本番用エンドポイント（SWIとガイダンスの初期時刻を個別指定）

        重複計算防止機能:
        - 同じ条件のリクエストが既に計算中の場合、待機して完了を待つ
        - 計算完了後のベースセッションIDを共有して返す
        """
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

            logger.info(f"本番処理開始: SWI初期時刻={swi_initial}, ガイダンス初期時刻={guidance_initial}")

            # 設定ファイルからURL構築
            swi_url = self.config_service.build_swi_url(swi_initial)
            guidance_url = self.config_service.build_guidance_url(guidance_initial)

            # キャッシュキー生成
            cache_key = self.cache_service.generate_cache_key(
                swi_initial.isoformat(),
                guidance_initial.isoformat()
            )

            # ========================================
            # 重複計算防止: ロック機構
            # ========================================

            # 既に計算中かチェック
            if self.cache_service.is_calculation_in_progress(cache_key):
                logger.info(f"計算中検出、待機開始: {cache_key}")

                # 計算完了を待機（最大5分）
                success, base_session_id = self.cache_service.wait_for_calculation(
                    cache_key, timeout_seconds=300, poll_interval=2.0
                )

                if success and base_session_id and self.session_service:
                    # ベースセッションが存在するか確認
                    session = self.session_service.get_session(base_session_id)
                    if session:
                        logger.info(f"既存セッション再利用: {base_session_id}")

                        # 利用可能な時刻を抽出
                        available_times = []
                        first_pref = next(iter(session['prefectures'].values()))
                        if first_pref['areas'] and first_pref['areas'][0]['meshes']:
                            first_mesh = first_pref['areas'][0]['meshes'][0]
                            available_times = sorted(set(
                                [point['ft'] for point in first_mesh.get('risk_3hour_max_timeline', [])] +
                                [point['ft'] for point in first_mesh.get('risk_hourly_timeline', [])]
                            ))

                        return jsonify({
                            "status": "success",
                            "session_id": base_session_id,
                            "swi_initial_time": swi_initial.isoformat() + 'Z',
                            "guidance_initial_time": guidance_initial.isoformat() + 'Z',
                            "available_prefectures": list(session['prefectures'].keys()),
                            "available_times": available_times,
                            "cache_info": {
                                "cache_key": cache_key,
                                "cache_hit": True,
                                "waited_for_calculation": True
                            },
                            "used_urls": {
                                "swi_url": swi_url,
                                "swi_initial_time": swi_initial.isoformat() + 'Z',
                                "guidance_url": guidance_url,
                                "guidance_initial_time": guidance_initial.isoformat() + 'Z'
                            }
                        })

                # 待機失敗（タイムアウトまたはセッション不在）→ 自分で計算を試みる
                logger.warning(f"待機失敗、自身で計算を試みます: {cache_key}")

            # 計算ロック取得を試みる
            lock_acquired = self.cache_service.acquire_calculation_lock(cache_key)
            session_id = None

            try:
                # キャッシュ存在確認
                cache_exists = self.cache_service.exists(cache_key)
                cache_metadata = None
                if cache_exists:
                    cache_metadata = self.cache_service.get_metadata(cache_key)

                # ローカルフォールバックパス（開発環境用、本番ではファイルが存在しないため無効）
                fallback_swi = os.path.join(self.data_dir,
                    "Z__C_RJTD_20230602000000_SRF_GPV_Ggis1km_Psw_Aper10min_ANAL_grib2.bin")
                fallback_guidance = os.path.join(self.data_dir,
                    "guid_msm_grib2_20230602000000_rmax00.bin")

                # メイン処理実行（個別URLを使用、use_cache=True でキャッシュ有効）
                result = self.main_service.main_process_from_separate_urls(
                    swi_url, guidance_url, use_cache=True,
                    fallback_swi_path=fallback_swi if os.path.exists(fallback_swi) else None,
                    fallback_guidance_path=fallback_guidance if os.path.exists(fallback_guidance) else None
                )

                # セッションサービスが有効な場合、セッション作成して軽量レスポンスを返す
                if self.session_service:
                    # ベースセッション作成
                    session_id = self.session_service.create_session(
                        result['prefectures'],
                        swi_initial.isoformat(),
                        guidance_initial.isoformat(),
                        datetime.now().isoformat()
                    )

                    # ロック解放時にベースセッションIDを保存
                    if lock_acquired:
                        self.cache_service.release_calculation_lock(cache_key, session_id)

                    # 利用可能な時刻を抽出（最初のメッシュから）
                    available_times = []
                    first_pref = next(iter(result['prefectures'].values()))
                    if first_pref['areas'] and first_pref['areas'][0]['meshes']:
                        first_mesh = first_pref['areas'][0]['meshes'][0]
                        available_times = sorted(set(
                            [point['ft'] for point in first_mesh['risk_3hour_max_timeline']] +
                            [point['ft'] for point in first_mesh['risk_hourly_timeline']]
                        ))

                    # 軽量レスポンスを返す
                    available_prefs = list(result['prefectures'].keys())

                    return jsonify({
                        "status": "success",
                        "session_id": session_id,
                        "swi_initial_time": swi_initial.isoformat() + 'Z',
                        "guidance_initial_time": guidance_initial.isoformat() + 'Z',
                        "available_prefectures": available_prefs,
                        "available_times": available_times,
                        "cache_info": {
                            "cache_key": cache_key,
                            "cache_hit": cache_exists,
                            "cache_metadata": cache_metadata
                        },
                        "used_urls": {
                            "swi_url": swi_url,
                            "swi_initial_time": swi_initial.isoformat() + 'Z',
                            "guidance_url": guidance_url,
                            "guidance_initial_time": guidance_initial.isoformat() + 'Z'
                        }
                    })

                # セッションサービスが無効な場合、従来通り全データを返す
                if lock_acquired:
                    self.cache_service.release_calculation_lock(cache_key)

                result["status"] = "success"

                # 使用したURLとキャッシュ情報も返却
                result["used_urls"] = {
                    "swi_url": swi_url,
                    "swi_initial_time": swi_initial.isoformat() + 'Z',
                    "guidance_url": guidance_url,
                    "guidance_initial_time": guidance_initial.isoformat() + 'Z'
                }

                result["cache_info"] = {
                    "cache_key": cache_key,
                    "cache_hit": cache_exists,
                    "cache_metadata": cache_metadata
                }

                return jsonify(result)

            except Exception as e:
                # エラー時はロックを解放
                if lock_acquired:
                    self.cache_service.release_calculation_lock(cache_key)
                raise

        except Exception as e:
            logger.error(f"本番処理エラー: {e}")
            return jsonify({
                "status": "error",
                "message": str(e)
            }), 500

    def test_session_with_local_bins(self):
        """開発環境用: ローカルbinファイルでセッションベースAPIをテスト"""
        try:
            # テスト用binファイルパス
            swi_file = os.path.join(self.data_dir,
                                    "Z__C_RJTD_20230602000000_SRF_GPV_Ggis1km_Psw_Aper10min_ANAL_grib2.bin")
            guidance_file = os.path.join(self.data_dir,
                                         "guid_msm_grib2_20230602000000_rmax00.bin")

            # ファイル存在確認
            if not os.path.exists(swi_file):
                return jsonify({
                    "status": "error",
                    "message": f"SWIテストファイルが見つかりません: {swi_file}"
                }), 404

            if not os.path.exists(guidance_file):
                return jsonify({
                    "status": "error",
                    "message": f"ガイダンステストファイルが見つかりません: {guidance_file}"
                }), 404

            logger.info(f"テスト用binファイルでセッション作成開始")
            logger.info(f"  SWI: {swi_file}")
            logger.info(f"  ガイダンス: {guidance_file}")

            # ファイルベースでメイン処理実行
            result = self.main_service.main_process_from_files(swi_file, guidance_file)

            # セッションサービスが有効な場合、セッション作成
            if self.session_service:
                # テストデータの初期時刻を使用
                swi_initial_time = result.get('initial_time', '2023-06-02T00:00:00')
                guidance_initial_time = swi_initial_time  # 同じ時刻

                # セッション作成
                session_id = self.session_service.create_session(
                    result['prefectures'],
                    swi_initial_time,
                    guidance_initial_time,
                    datetime.now().isoformat()
                )

                # 利用可能な時刻を抽出
                available_times = []
                first_pref = next(iter(result['prefectures'].values()))
                if first_pref['areas'] and first_pref['areas'][0]['meshes']:
                    first_mesh = first_pref['areas'][0]['meshes'][0]
                    available_times = sorted(set(
                        [point['ft'] for point in first_mesh['risk_3hour_max_timeline']] +
                        [point['ft'] for point in first_mesh['risk_hourly_timeline']]
                    ))

                # 軽量レスポンスを返す
                available_prefs = list(result['prefectures'].keys())

                return jsonify({
                    "status": "success",
                    "session_id": session_id,
                    "swi_initial_time": swi_initial_time + 'Z' if not swi_initial_time.endswith('Z') else swi_initial_time,
                    "guidance_initial_time": guidance_initial_time + 'Z' if not guidance_initial_time.endswith('Z') else guidance_initial_time,
                    "available_prefectures": available_prefs,
                    "available_times": available_times,
                    "cache_info": None,  # テストモードではキャッシュなし
                    "used_urls": {
                        "swi_url": f"file://{swi_file}",
                        "swi_initial_time": swi_initial_time,
                        "guidance_url": f"file://{guidance_file}",
                        "guidance_initial_time": guidance_initial_time
                    }
                })

            # セッションサービスが無効な場合、全データを返す
            result["status"] = "success"
            return jsonify(result)

        except Exception as e:
            logger.error(f"テストセッション処理エラー: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({
                "status": "error",
                "message": str(e)
            }), 500