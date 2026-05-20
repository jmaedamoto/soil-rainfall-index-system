# -*- coding: utf-8 -*-
"""
メインAPIコントローラー
"""
from flask import request, jsonify
from datetime import datetime, timedelta
import logging
import os
import sys
import time
import uuid

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

    @staticmethod
    def _build_available_prefecture_details(prefectures: dict) -> list:
        """府県コードと名称の一覧を返す"""
        details = []
        for code, prefecture in prefectures.items():
            if isinstance(prefecture, dict):
                name = prefecture.get("name", code)
            else:
                name = getattr(prefecture, "name", code)
            details.append({
                "code": code,
                "name": name,
            })
        return details

    @staticmethod
    def _extract_available_times(prefectures: dict) -> list:
        """先頭メッシュから利用可能なFT一覧を抽出する"""
        if not prefectures:
            return []

        first_pref = next(iter(prefectures.values()))
        if not first_pref.get("areas") or not first_pref["areas"][0].get("meshes"):
            return []

        first_mesh = first_pref["areas"][0]["meshes"][0]
        return sorted(set(
            [point["ft"] for point in first_mesh.get("risk_3hour_max_timeline", [])] +
            [point["ft"] for point in first_mesh.get("risk_hourly_timeline", [])]
        ))

    @staticmethod
    def _extract_cache_sample(result: dict) -> dict:
        """キャッシュ内容比較用に先頭府県・先頭エリア・先頭メッシュの要約を返す"""
        prefectures = result.get("prefectures") or {}
        if not prefectures:
            return {"prefecture_count": 0}

        pref_code, prefecture = next(iter(prefectures.items()))
        areas = prefecture.get("areas") or []
        if not areas:
            return {
                "prefecture_count": len(prefectures),
                "pref_code": pref_code,
                "area_count": 0,
            }

        area = areas[0]
        meshes = area.get("meshes") or []
        if not meshes:
            return {
                "prefecture_count": len(prefectures),
                "pref_code": pref_code,
                "area_name": area.get("name"),
                "mesh_count": 0,
                "area_risk_timeline": area.get("risk_timeline", [])[:3],
            }

        mesh = meshes[0]
        return {
            "prefecture_count": len(prefectures),
            "pref_code": pref_code,
            "area_name": area.get("name"),
            "mesh_count": len(meshes),
            "mesh_code": mesh.get("code"),
            "mesh_swi_timeline": mesh.get("swi_timeline", [])[:3],
            "mesh_risk_3hour_max_timeline": mesh.get("risk_3hour_max_timeline", [])[:3],
            "mesh_risk_hourly_timeline": mesh.get("risk_hourly_timeline", [])[:6],
            "area_risk_timeline": area.get("risk_timeline", [])[:3],
            "prefecture_risk_timeline": prefecture.get("prefecture_risk_timeline", [])[:3],
        }

    def _build_lightweight_session_response(
        self,
        session_id: str,
        prefectures: dict,
        swi_initial,
        guidance_initial,
        guidance_type: str,
        risk_rule: str,
        swi_url: str,
        guidance_url: str,
    ):
        """軽量セッションレスポンスを組み立てる"""
        return jsonify({
            "status": "success",
            "session_id": session_id,
            "swi_initial_time": swi_initial.isoformat() + 'Z',
            "guidance_initial_time": guidance_initial.isoformat() + 'Z',
            "guidance_type": guidance_type,
            "risk_rule": risk_rule,
            "available_prefectures": list(prefectures.keys()),
            "available_prefecture_details": self._build_available_prefecture_details(
                prefectures
            ),
            "available_times": self._extract_available_times(prefectures),
            "used_urls": {
                "swi_url": swi_url,
                "swi_initial_time": swi_initial.isoformat() + 'Z',
                "guidance_url": guidance_url,
                "guidance_initial_time": guidance_initial.isoformat() + 'Z',
                "guidance_type": guidance_type,
                "risk_rule": risk_rule,
            }
        })

    def _build_cached_response(
        self,
        cached_result: dict,
        swi_initial,
        guidance_initial,
        guidance_type: str,
        risk_rule: str,
        cache_key: str,
        swi_url: str,
        guidance_url: str,
    ):
        """キャッシュ済み結果から返却レスポンスを組み立てる"""
        sample = self._extract_cache_sample(cached_result)
        logger.info(
            "キャッシュ返却内容サンプル: cache_key=%s sample=%s",
            cache_key,
            sample,
        )

        if self.session_service:
            session_id = self.session_service.create_session(
                cached_result['prefectures'],
                swi_initial.isoformat(),
                guidance_initial.isoformat(),
                datetime.now().isoformat(),
                guidance_type,
                risk_rule,
                cache_key,
            )
            return self._build_lightweight_session_response(
                session_id,
                cached_result['prefectures'],
                swi_initial,
                guidance_initial,
                guidance_type,
                risk_rule,
                swi_url,
                guidance_url,
            )

        cached_result["status"] = "success"
        cached_result["guidance_type"] = guidance_type
        cached_result["risk_rule"] = risk_rule
        cached_result["used_urls"] = {
            "swi_url": swi_url,
            "swi_initial_time": swi_initial.isoformat() + 'Z',
            "guidance_url": guidance_url,
            "guidance_initial_time": guidance_initial.isoformat() + 'Z',
            "guidance_type": guidance_type,
            "risk_rule": risk_rule,
        }
        return jsonify(cached_result)

    @staticmethod
    def _build_request_trace_context() -> dict:
        """本番追跡用のリクエストコンテキストを作成する"""
        forwarded_for = request.headers.get('X-Forwarded-For')
        remote_addr = forwarded_for.split(',')[0].strip() if forwarded_for else request.remote_addr
        return {
            "request_id": uuid.uuid4().hex[:12],
            "pid": os.getpid(),
            "remote_addr": remote_addr or "unknown",
            "user_agent": request.headers.get('User-Agent', 'unknown'),
        }

    @staticmethod
    def _trace_prefix(trace_context: dict) -> str:
        """追跡ログ用プレフィックスを返す"""
        return (
            f"[request_id={trace_context['request_id']} "
            f"pid={trace_context['pid']} remote={trace_context['remote_addr']}]"
        )
    
    def data_check(self):
        """データファイル確認エンドポイント"""
        try:
            required_files = []
            
            # 必要なファイルリスト
            prefecture_definitions = self.main_service.data_service.get_prefecture_definitions()
            for pref in prefecture_definitions:
                pref_code = pref["code"]
                required_files.extend([
                    f"dosha_{pref_code}.csv",
                    f"dosyakei_{pref_code}.csv"
                ])
            
            # ファイル存在確認
            file_status = {}
            prefectures_file = os.path.join(self.data_dir, "prefectures.csv")
            file_status["prefectures.csv"] = os.path.exists(prefectures_file)
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
            guidance_type = "msm"
            guidance_url = self.config_service.build_guidance_url(initial_time, guidance_type)

            result["used_urls"] = {
                "swi_url": swi_url,
                "guidance_url": guidance_url,
                "guidance_type": guidance_type
            }
            result["guidance_type"] = guidance_type
            
            return jsonify(result)
            
        except Exception as e:
            logger.error(f"本番テスト処理エラー: {e}")
            error_urls = {}
            if 'initial_time' in locals():
                error_urls = {
                    "swi_url": self.config_service.build_swi_url(initial_time),
                    "guidance_url": self.config_service.build_guidance_url(initial_time, "msm"),
                    "guidance_type": "msm"
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
            request_started_at = time.perf_counter()
            trace_context = self._build_request_trace_context()
            trace_prefix = self._trace_prefix(trace_context)
            logger.info(f"{trace_prefix} 本番処理リクエスト受信")

            data = request.get_json()
            if not data:
                logger.warning(f"{trace_prefix} リクエストデータなし")
                return jsonify({
                    "status": "error",
                    "message": "リクエストデータが必要です"
                }), 400

            # SWI初期時刻取得
            swi_initial_str = data.get('swi_initial')
            if not swi_initial_str:
                logger.warning(f"{trace_prefix} swi_initial パラメータ不足")
                return jsonify({
                    "status": "error",
                    "message": "swi_initialパラメータが必要です"
                }), 400

            # ガイダンス初期時刻取得
            guidance_initial_str = data.get('guidance_initial')
            if not guidance_initial_str:
                logger.warning(f"{trace_prefix} guidance_initial パラメータ不足")
                return jsonify({
                    "status": "error",
                    "message": "guidance_initialパラメータが必要です"
                }), 400

            try:
                guidance_type = self.config_service.normalize_guidance_type(
                    data.get('guidance_type', 'msm')
                )
                risk_rule = self.main_service.calculation_service.normalize_risk_rule(
                    data.get('risk_rule', 'legacy')
                )
            except ValueError as e:
                logger.warning(f"{trace_prefix} guidance_type/risk_rule 検証エラー: {e}")
                return jsonify({
                    "status": "error",
                    "message": str(e)
                }), 400

            # ISO8601形式の日時パース
            try:
                swi_initial = datetime.fromisoformat(swi_initial_str.replace('Z', '+00:00'))
                swi_initial = swi_initial.replace(tzinfo=None)
            except ValueError as e:
                logger.warning(f"{trace_prefix} swi_initial パースエラー: {e}")
                return jsonify({
                    "status": "error",
                    "message": f"swi_initial日時形式エラー: {e}"
                }), 400

            try:
                guidance_initial = datetime.fromisoformat(guidance_initial_str.replace('Z', '+00:00'))
                guidance_initial = guidance_initial.replace(tzinfo=None)
            except ValueError as e:
                logger.warning(f"{trace_prefix} guidance_initial パースエラー: {e}")
                return jsonify({
                    "status": "error",
                    "message": f"guidance_initial日時形式エラー: {e}"
                }), 400

            try:
                self.config_service.validate_guidance_initial_time(
                    guidance_initial,
                    guidance_type
                )
            except ValueError as e:
                logger.warning(f"{trace_prefix} guidance_initial 制約エラー: {e}")
                return jsonify({
                    "status": "error",
                    "message": str(e)
                }), 400

            logger.info(
                f"{trace_prefix} 本番処理開始: SWI初期時刻={swi_initial}, "
                f"ガイダンス初期時刻={guidance_initial}, guidance_type={guidance_type}, "
                f"risk_rule={risk_rule}"
            )

            # 設定ファイルからURL構築
            swi_url = self.config_service.build_swi_url(swi_initial)
            guidance_url = self.config_service.build_guidance_url(guidance_initial, guidance_type)

            # キャッシュキー生成
            cache_key = self.cache_service.generate_cache_key(
                swi_initial.isoformat(),
                guidance_initial.isoformat(),
                guidance_type,
                risk_rule,
            )
            logger.info(f"{trace_prefix} キャッシュキー算出: {cache_key}")

            # 先にキャッシュを確認し、ヒット時はGRIB2取得前に即返却する
            cached_result = self.cache_service.get_cached_result(cache_key)
            if cached_result:
                elapsed = time.perf_counter() - request_started_at
                logger.info(
                    f"{trace_prefix} キャッシュ即時返却: {cache_key} "
                    f"(elapsed={elapsed:.2f}s)"
                )
                return self._build_cached_response(
                    cached_result,
                    swi_initial,
                    guidance_initial,
                    guidance_type,
                    risk_rule,
                    cache_key,
                    swi_url,
                    guidance_url,
                )

            cache_write_in_progress = self.cache_service.is_cache_write_in_progress(cache_key)
            cache_materializing = self.cache_service.is_cache_materializing(cache_key)
            calculation_in_progress = self.cache_service.is_calculation_in_progress(cache_key)
            if cache_write_in_progress or cache_materializing or calculation_in_progress:
                wait_started_at = time.perf_counter()
                logger.info(
                    "%s キャッシュ作成中のため完了待機: %s, calculating=%s, tmp=%s, materializing=%s",
                    trace_prefix,
                    cache_key,
                    calculation_in_progress,
                    cache_write_in_progress,
                    cache_materializing,
                )

                if self.cache_service.wait_for_cache_materialization(cache_key, timeout_seconds=300.0):
                    cached_result = self.cache_service.get_cached_result(cache_key)
                    if cached_result:
                        wait_elapsed = time.perf_counter() - wait_started_at
                        total_elapsed = time.perf_counter() - request_started_at
                        logger.info(
                            f"{trace_prefix} キャッシュ確定後返却: {cache_key} "
                            f"(wait_elapsed={wait_elapsed:.2f}s total_elapsed={total_elapsed:.2f}s)"
                        )
                        return self._build_cached_response(
                            cached_result,
                            swi_initial,
                            guidance_initial,
                            guidance_type,
                            risk_rule,
                            cache_key,
                            swi_url,
                            guidance_url,
                        )

                wait_elapsed = time.perf_counter() - wait_started_at
                logger.warning(
                    f"{trace_prefix} キャッシュ作成待機タイムアウト: {cache_key} "
                    f"(wait_elapsed={wait_elapsed:.2f}s)"
                )

            # ========================================
            # 重複計算防止: ロック機構
            # ========================================

            # 計算ロック取得を試みる
            lock_acquired = self.cache_service.acquire_calculation_lock(cache_key)
            if not lock_acquired:
                wait_started_at = time.perf_counter()
                logger.info(
                    f"{trace_prefix} 別リクエストが計算を開始したため待機に切り替え: {cache_key}"
                )
                if self.cache_service.wait_for_cache_materialization(cache_key, timeout_seconds=300.0):
                    cached_result = self.cache_service.get_cached_result(cache_key)
                    if cached_result:
                        wait_elapsed = time.perf_counter() - wait_started_at
                        total_elapsed = time.perf_counter() - request_started_at
                        logger.info(
                            f"{trace_prefix} ロック取得失敗後にキャッシュ返却: {cache_key} "
                            f"(wait_elapsed={wait_elapsed:.2f}s total_elapsed={total_elapsed:.2f}s)"
                        )
                        return self._build_cached_response(
                            cached_result,
                            swi_initial,
                            guidance_initial,
                            guidance_type,
                            risk_rule,
                            cache_key,
                            swi_url,
                            guidance_url,
                        )

                wait_elapsed = time.perf_counter() - wait_started_at
                logger.error(
                    f"{trace_prefix} 計算ロック取得失敗後もキャッシュ未確定: {cache_key} "
                    f"(wait_elapsed={wait_elapsed:.2f}s)"
                )
                return jsonify({
                    "status": "error",
                    "message": "同一条件の計算が進行中ですが、結果の取得に失敗しました。しばらくして再試行してください。"
                }), 503

            try:
                on_cache_saved = None
                if lock_acquired:
                    logger.info(f"{trace_prefix} 計算ロック取得後に計算開始: {cache_key}")
                    def on_cache_saved(success: bool) -> None:
                        if success:
                            logger.info(
                                f"{trace_prefix} 非同期キャッシュ保存完了によりロック解放: {cache_key}"
                            )
                        else:
                            logger.warning(
                                f"{trace_prefix} 非同期キャッシュ保存失敗によりロック解放: {cache_key}"
                            )
                        self.cache_service.release_calculation_lock(cache_key)

                # メイン処理実行（個別URLを使用、use_cache=True でキャッシュ有効）
                calculation_started_at = time.perf_counter()
                result = self.main_service.main_process_from_separate_urls(
                    swi_url,
                    guidance_url,
                    guidance_type=guidance_type,
                    risk_rule=risk_rule,
                    use_cache=True,
                    async_cache_save=True,
                    on_cache_saved=on_cache_saved,
                )
                calculation_elapsed = time.perf_counter() - calculation_started_at
                logger.info(
                    f"{trace_prefix} 計算処理完了: {cache_key} "
                    f"(calculation_elapsed={calculation_elapsed:.2f}s)"
                )

                # セッションサービスが有効な場合、セッション作成して軽量レスポンスを返す
                if self.session_service:
                    # ベースセッション作成
                    session_id = self.session_service.create_session(
                        result['prefectures'],
                        swi_initial.isoformat(),
                        guidance_initial.isoformat(),
                        datetime.now().isoformat(),
                        guidance_type,
                        risk_rule,
                        cache_key,
                    )
                    total_elapsed = time.perf_counter() - request_started_at
                    logger.info(
                        f"{trace_prefix} 軽量セッションレスポンス返却: session_id={session_id} "
                        f"cache_key={cache_key} total_elapsed={total_elapsed:.2f}s"
                    )

                    return self._build_lightweight_session_response(
                        session_id,
                        result['prefectures'],
                        swi_initial,
                        guidance_initial,
                        guidance_type,
                        risk_rule,
                        swi_url,
                        guidance_url,
                    )

                # セッションサービスが無効な場合、従来通り全データを返す
                if lock_acquired:
                    # セッションを使わない経路ではレスポンス前にロックを解放してよい
                    self.cache_service.release_calculation_lock(cache_key)
                    logger.info(f"{trace_prefix} セッション未使用経路のため計算ロック解放: {cache_key}")

                result["status"] = "success"

                # 使用したURLとキャッシュ情報も返却
                result["used_urls"] = {
                    "swi_url": swi_url,
                    "swi_initial_time": swi_initial.isoformat() + 'Z',
                    "guidance_url": guidance_url,
                    "guidance_initial_time": guidance_initial.isoformat() + 'Z',
                    "guidance_type": guidance_type
                }
                result["guidance_type"] = guidance_type
                result["risk_rule"] = risk_rule
                total_elapsed = time.perf_counter() - request_started_at
                logger.info(
                    f"{trace_prefix} フルレスポンス返却: {cache_key} total_elapsed={total_elapsed:.2f}s"
                )

                return jsonify(result)

            except Exception as e:
                # エラー時はロックを解放
                if lock_acquired:
                    self.cache_service.release_calculation_lock(cache_key)
                    logger.info(f"{trace_prefix} 例外発生のため計算ロック解放: {cache_key}")
                raise

        except Exception as e:
            elapsed = time.perf_counter() - request_started_at if 'request_started_at' in locals() else 0.0
            logger.exception(f"{trace_prefix if 'trace_prefix' in locals() else ''} 本番処理エラー: {e} (elapsed={elapsed:.2f}s)")
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
                    datetime.now().isoformat(),
                    'msm',
                    'legacy'
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
                    "guidance_type": "msm",
                    "risk_rule": "legacy",
                    "available_prefectures": available_prefs,
                    "available_prefecture_details": self._build_available_prefecture_details(
                        result['prefectures']
                    ),
                    "available_times": available_times,
                    "used_urls": {
                        "swi_url": f"file://{swi_file}",
                        "swi_initial_time": swi_initial_time,
                        "guidance_url": f"file://{guidance_file}",
                        "guidance_initial_time": guidance_initial_time,
                        "guidance_type": "msm",
                        "risk_rule": "legacy"
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
