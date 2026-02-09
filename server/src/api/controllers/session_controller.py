# -*- coding: utf-8 -*-
"""
セッション管理APIコントローラー
"""
from flask import jsonify, request
from datetime import datetime
import logging
import os
import sys

# プロジェクトルートをパスに追加
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(project_root)

from services.session_service import SessionService

logger = logging.getLogger(__name__)


class SessionController:
    """セッション管理APIコントローラー"""

    def __init__(self, session_service: SessionService):
        self.session_service = session_service

    def get_session_info(self, session_id: str):
        """
        セッション情報取得

        GET /session/<session_id>
        """
        try:
            info = self.session_service.get_session_info(session_id)

            if info is None:
                return jsonify({
                    "status": "error",
                    "error": "Session not found or expired",
                    "session_id": session_id
                }), 404

            return jsonify({
                "status": "success",
                "session": info
            })

        except Exception as e:
            logger.error(f"Session info error: {e}")
            return jsonify({
                "status": "error",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }), 500

    def get_prefecture_data(self, session_id: str, prefecture_code: str):
        """
        府県データ取得（危険度時系列のみ）

        GET /session/<session_id>/prefecture/<prefecture_code>

        Returns:
            - 府県名、コード
            - エリア別危険度時系列
            - 二次細分別危険度時系列
            - 府県全体危険度時系列
        """
        try:
            prefecture = self.session_service.get_prefecture(
                session_id,
                prefecture_code
            )

            if prefecture is None:
                return jsonify({
                    "status": "error",
                    "error": "Session or prefecture not found",
                    "session_id": session_id,
                    "prefecture_code": prefecture_code
                }), 404

            # 危険度時系列のみを抽出（prefectureは辞書形式）
            response_data = {
                "name": prefecture["name"],
                "code": prefecture["code"],
                "areas": [
                    {
                        "name": area["name"],
                        "secondary_subdivision_name": area["secondary_subdivision_name"],
                        "risk_timeline": area["risk_timeline"]
                    }
                    for area in prefecture["areas"]
                ],
                "secondary_subdivisions": [
                    {
                        "name": subdiv["name"],
                        "area_names": subdiv.get("area_names", []),
                        "risk_timeline": subdiv.get("risk_timeline", [])
                    }
                    for subdiv in prefecture.get("secondary_subdivisions", [])
                ],
                "prefecture_risk_timeline": prefecture.get("prefecture_risk_timeline", [])
            }

            # デバッグ: レスポンスデータの確認
            logger.info(f"Prefecture {prefecture_code}: {len(response_data['areas'])} areas")
            if response_data['areas']:
                first_area = response_data['areas'][0]
                logger.info(f"First area: {first_area['name']}, risk_timeline length: {len(first_area.get('risk_timeline', []))}")
                if first_area.get('risk_timeline'):
                    logger.info(f"First risk point: {first_area['risk_timeline'][0]}")

            return jsonify({
                "status": "success",
                "prefecture": response_data
            })

        except Exception as e:
            logger.error(f"Prefecture data error: {e}")
            return jsonify({
                "status": "error",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }), 500

    def get_risk_at_time(self, session_id: str):
        """
        指定時刻の全メッシュリスク値取得

        GET /session/<session_id>/risk-at-time?ft=<ft>&include_coords=<true|false>

        Parameters:
            ft: 予報時刻（必須）
            include_coords: 座標を含めるか（省略時true、初回のみtrueで2回目以降はfalse推奨）
        """
        try:
            ft = request.args.get('ft', type=int)
            if ft is None:
                return jsonify({
                    "status": "error",
                    "error": "Parameter 'ft' is required"
                }), 400

            # include_coords パラメータ（デフォルトtrue、後方互換性のため）
            include_coords_str = request.args.get('include_coords', 'true').lower()
            include_coords = include_coords_str == 'true'

            session = self.session_service.get_session(session_id)
            if session is None:
                return jsonify({
                    "status": "error",
                    "error": "Session not found or expired",
                    "session_id": session_id
                }), 404

            # 全府県の全メッシュからリスク値を抽出（辞書形式）
            mesh_risks = {}
            mesh_coords = {} if include_coords else None
            prefectures = session['prefectures']

            sample_count = 0
            for pref_code, prefecture in prefectures.items():
                for area in prefecture["areas"]:
                    for mesh in area["meshes"]:
                        # 指定されたFTのリスク値を取得
                        risk_value = 0
                        for risk_point in mesh["risk_3hour_max_timeline"]:
                            if risk_point["ft"] == ft:
                                risk_value = risk_point["value"]
                                break

                        # 最初の3メッシュのデータをログ出力
                        if sample_count < 3:
                            logger.info(f"[get_risk_at_time] FT={ft}, Mesh={mesh['code']}, Risk={risk_value}, Timeline={mesh['risk_3hour_max_timeline'][:3]}")
                            sample_count += 1

                        mesh_risks[mesh["code"]] = risk_value

                        # 座標は必要な場合のみ収集
                        if include_coords:
                            mesh_coords[mesh["code"]] = {
                                "lat": mesh["lat"],
                                "lon": mesh["lon"]
                            }

            response_data = {
                "status": "success",
                "ft": ft,
                "mesh_risks": mesh_risks
            }

            # 座標は要求された場合のみ含める
            if include_coords:
                response_data["mesh_coords"] = mesh_coords

            return jsonify(response_data)

        except Exception as e:
            logger.error(f"Risk at time error: {e}")
            return jsonify({
                "status": "error",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }), 500

    def get_mesh_detail(self, session_id: str, mesh_code: str):
        """
        メッシュ詳細データ取得

        GET /session/<session_id>/mesh/<mesh_code>
        """
        try:
            session = self.session_service.get_session(session_id)
            if session is None:
                return jsonify({
                    "status": "error",
                    "error": "Session not found or expired",
                    "session_id": session_id
                }), 404

            # 全府県からメッシュを検索（辞書形式）
            prefectures = session['prefectures']
            target_mesh = None

            for pref_code, prefecture in prefectures.items():
                for area in prefecture["areas"]:
                    for mesh in area["meshes"]:
                        if mesh["code"] == mesh_code:
                            target_mesh = mesh
                            break
                    if target_mesh:
                        break
                if target_mesh:
                    break

            if target_mesh is None:
                return jsonify({
                    "status": "error",
                    "error": "Mesh not found",
                    "mesh_code": mesh_code
                }), 404

            # 既に辞書形式なのでそのまま使用
            mesh_dict = target_mesh

            return jsonify({
                "status": "success",
                "mesh": mesh_dict
            })

        except Exception as e:
            logger.error(f"Mesh detail error: {e}")
            return jsonify({
                "status": "error",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }), 500

    def delete_session(self, session_id: str):
        """
        セッション削除

        DELETE /session/<session_id>
        """
        try:
            success = self.session_service.delete_session(session_id)

            if not success:
                return jsonify({
                    "status": "error",
                    "error": "Session not found",
                    "session_id": session_id
                }), 404

            return jsonify({
                "status": "success",
                "message": "Session deleted",
                "session_id": session_id
            })

        except Exception as e:
            logger.error(f"Session delete error: {e}")
            return jsonify({
                "status": "error",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }), 500

    def list_sessions(self):
        """
        セッション一覧取得（デバッグ用）

        GET /sessions
        """
        try:
            sessions = self.session_service.list_sessions()

            return jsonify({
                "status": "success",
                "sessions": sessions,
                "count": len(sessions)
            })

        except Exception as e:
            logger.error(f"Session list error: {e}")
            return jsonify({
                "status": "error",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }), 500

    def get_session_stats(self):
        """
        セッション統計情報取得

        GET /sessions/stats
        """
        try:
            stats = self.session_service.get_stats()

            return jsonify({
                "status": "success",
                "stats": stats
            })

        except Exception as e:
            logger.error(f"Session stats error: {e}")
            return jsonify({
                "status": "error",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }), 500

    def cleanup_sessions(self):
        """
        期限切れセッションクリーンアップ

        POST /sessions/cleanup
        """
        try:
            deleted_count = self.session_service.cleanup_expired_sessions()

            return jsonify({
                "status": "success",
                "message": f"Cleaned up {deleted_count} expired sessions",
                "deleted_count": deleted_count
            })

        except Exception as e:
            logger.error(f"Session cleanup error: {e}")
            return jsonify({
                "status": "error",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }), 500

    def get_rainfall_data(self, session_id: str):
        """
        雨量調整用の雨量データ取得

        GET /session/<session_id>/rainfall-data

        Returns:
            - 市町村別雨量タイムライン
            - 二次細分別雨量タイムライン
        """
        try:
            session = self.session_service.get_session(session_id)
            if session is None:
                return jsonify({
                    "status": "error",
                    "error": "Session not found or expired",
                    "session_id": session_id
                }), 404

            # 雨量データを抽出
            prefectures = session['prefectures']
            area_rainfall = {}
            subdivision_rainfall = {}

            for pref_code, prefecture in prefectures.items():
                pref_name = prefecture["name"]

                # 市町村別雨量
                for area in prefecture["areas"]:
                    area_key = f"{pref_name}_{area['name']}"

                    # 市町村内の全メッシュから雨量タイムラインを集約
                    if area["meshes"]:
                        ft_set = set()
                        for mesh in area["meshes"]:
                            if mesh.get("rain_timeline"):
                                for point in mesh["rain_timeline"]:
                                    ft_set.add(point["ft"])

                        timeline = []
                        for ft in sorted(ft_set):
                            max_value = max(
                                (point["value"] for mesh in area["meshes"]
                                 if mesh.get("rain_timeline")
                                 for point in mesh["rain_timeline"]
                                 if point["ft"] == ft),
                                default=0.0
                            )
                            timeline.append({"ft": ft, "value": max_value})

                        area_rainfall[area_key] = timeline

                # 二次細分別雨量
                for subdiv in prefecture.get("secondary_subdivisions", []):
                    subdiv_key = f"{pref_name}_{subdiv['name']}"

                    # 二次細分内の全メッシュから雨量タイムラインを集約
                    all_meshes = []
                    for area_name in subdiv.get("area_names", []):
                        area = next((a for a in prefecture["areas"] if a["name"] == area_name), None)
                        if area:
                            all_meshes.extend(area["meshes"])

                    if all_meshes:
                        ft_set = set()
                        for mesh in all_meshes:
                            if mesh.get("rain_timeline"):
                                for point in mesh["rain_timeline"]:
                                    ft_set.add(point["ft"])

                        timeline = []
                        for ft in sorted(ft_set):
                            max_value = max(
                                (point["value"] for mesh in all_meshes
                                 if mesh.get("rain_timeline")
                                 for point in mesh["rain_timeline"]
                                 if point["ft"] == ft),
                                default=0.0
                            )
                            timeline.append({"ft": ft, "value": max_value})

                        subdivision_rainfall[subdiv_key] = timeline

            return jsonify({
                "status": "success",
                "area_rainfall": area_rainfall,
                "subdivision_rainfall": subdivision_rainfall
            })

        except Exception as e:
            logger.error(f"Rainfall data error: {e}")
            return jsonify({
                "status": "error",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }), 500

    def recalculate_with_adjusted_rainfall(self, session_id: str):
        """
        雨量調整後の再計算（フォークセッション方式）

        POST /session/<session_id>/recalculate

        Request Body:
            {
                "adjustments": {"府県名_市町村名": [{"ft": 0, "value": 10.5}, ...]},
                "swi_initial": "2025-01-01T00:00:00Z",  # 使用されない（互換性のため残す）
                "guidance_initial": "2025-01-01T00:00:00Z",  # 使用されない
                "data_source": "test"  # 使用されない
            }

        Returns:
            - 新しいフォークセッションを作成（ベースセッションは変更しない）
            - 初期時刻のメッシュリスクのみ返す（軽量レスポンス）

        フォークセッション方式:
            - ベースセッション（計算結果）は複数ユーザーで共有可能
            - 雨量編集時はフォークセッション（差分のみ）を作成
            - 各ユーザーの編集は独立し、相互に干渉しない
        """
        try:
            # セッション取得
            session = self.session_service.get_session(session_id)
            if session is None:
                return jsonify({
                    "status": "error",
                    "error": "Session not found or expired",
                    "session_id": session_id
                }), 404

            # リクエストボディ取得
            data = request.get_json()
            if not data or 'adjustments' not in data:
                return jsonify({
                    "status": "error",
                    "error": "Missing 'adjustments' in request body"
                }), 400

            logger.info(f"Session {session_id}: 雨量調整再計算開始（フォーク方式）")

            # ベースセッションIDを特定
            if session.get('is_fork'):
                base_session_id = session.get('base_session_id')
                logger.info(f"フォークセッションからの再編集: base={base_session_id}")
            else:
                base_session_id = session_id
                logger.info(f"ベースセッションからの初回編集: base={base_session_id}")

            # セッションからprefecturesを取得（フォークの場合はマージ済み）
            existing_prefectures_dict = session['prefectures']

            # adjustmentsを配列形式から辞書形式に変換
            adjustments_raw = data['adjustments']
            adjustments = {}
            for area_key, timeline in adjustments_raw.items():
                adjustments[area_key] = {
                    point['ft']: point['value'] for point in timeline
                }

            logger.info(f"調整対象市町村数: {len(adjustments)}件")

            # NumPyベクトル化版サービス（高速）
            from services.calculation_service_numpy import CalculationServiceNumpy
            calculation_service_numpy = CalculationServiceNumpy()

            # 再計算済みメッシュを保存する辞書
            recalculated_meshes = {}
            adjusted_mesh_count = 0

            # NumPy一括計算用のデータリスト
            mesh_data_list = []
            mesh_code_to_rain = {}  # mesh_code -> 調整済み雨量

            # 二次細分名 → 市町村名リストのマッピングを構築
            subdiv_to_areas = {}
            for pref_code, pref_dict in existing_prefectures_dict.items():
                pref_name = pref_dict['name']
                for subdiv in pref_dict.get('secondary_subdivisions', []):
                    subdiv_key = f"{pref_name}_{subdiv['name']}"
                    subdiv_to_areas[subdiv_key] = {
                        'pref_name': pref_name,
                        'area_names': subdiv.get('area_names', [])
                    }

            # 二次細分キーの調整を市町村キーに展開
            expanded_adjustments = dict(adjustments)
            for subdiv_key, subdiv_rain in list(adjustments.items()):
                if subdiv_key in subdiv_to_areas:
                    info = subdiv_to_areas[subdiv_key]
                    for area_name in info['area_names']:
                        area_key = f"{info['pref_name']}_{area_name}"
                        if area_key not in expanded_adjustments:
                            expanded_adjustments[area_key] = subdiv_rain
                            logger.info(f"二次細分 {subdiv_key} → 市町村 {area_key} に展開")

            # Step 1: 調整対象メッシュのデータを収集
            import time
            collect_start = time.time()

            for pref_code, pref_dict in existing_prefectures_dict.items():
                for area_dict in pref_dict['areas']:
                    area_key = f"{pref_dict['name']}_{area_dict['name']}"

                    if area_key in expanded_adjustments:
                        adjusted_rain = expanded_adjustments[area_key]

                        # 雨量timelineを調整
                        new_rain_timeline = [
                            (ft, adjusted_rain[ft])
                            for ft in sorted(adjusted_rain.keys())
                        ]

                        # この市町村の全メッシュを処理
                        for mesh_dict in area_dict['meshes']:
                            mesh_code = mesh_dict['code']

                            # 初期SWI値を取得
                            swi_timeline = mesh_dict.get('swi_timeline', [])
                            initial_swi = swi_timeline[0]['value'] if swi_timeline else 100.0

                            # NumPy一括計算用のデータを収集
                            mesh_data_list.append({
                                'mesh_code': mesh_code,
                                'initial_swi': initial_swi,
                                'advisory_bound': mesh_dict['advisary_bound'],
                                'warning_bound': mesh_dict['warning_bound'],
                                'dosyakei_bound': mesh_dict['dosyakei_bound'],
                                'rain_3hour': new_rain_timeline
                            })
                            mesh_code_to_rain[mesh_code] = [
                                {"ft": ft, "value": value}
                                for ft, value in new_rain_timeline
                            ]
                            adjusted_mesh_count += 1

            collect_time = time.time() - collect_start
            logger.info(f"データ収集: {adjusted_mesh_count}メッシュ, {collect_time:.3f}秒")

            # Step 2: NumPy一括計算
            calc_start = time.time()
            if mesh_data_list:
                numpy_results = calculation_service_numpy.recalculate_meshes_vectorized(mesh_data_list)

                # 結果をrecalculated_meshesに格納
                for mesh_code, result in numpy_results.items():
                    recalculated_meshes[mesh_code] = {
                        'rain_timeline': mesh_code_to_rain[mesh_code],
                        'swi_timeline': result['swi_timeline'],
                        'risk_3hour_max_timeline': result['risk_3hour_max_timeline'],
                        'risk_hourly_timeline': result['risk_hourly_timeline']
                    }

            calc_time = time.time() - calc_start
            logger.info(f"NumPy一括計算: {adjusted_mesh_count}メッシュ, {calc_time:.3f}秒")

            # フォークセッションを作成
            fork_session_id = self.session_service.create_fork_session(
                base_session_id=base_session_id,
                adjustments=adjustments_raw,  # 元の形式で保存
                recalculated_meshes=recalculated_meshes
            )

            if fork_session_id is None:
                return jsonify({
                    "status": "error",
                    "error": "Failed to create fork session",
                    "session_id": session_id
                }), 500

            logger.info(f"フォークセッション作成完了: {fork_session_id}")

            # 軽量レスポンス: 初期時刻（FT=0）のメッシュリスクと座標を返す
            # フォークセッションから取得（マージ済み）
            fork_session = self.session_service.get_session(fork_session_id)
            merged_prefectures = fork_session['prefectures']

            mesh_risks = {}
            mesh_coords = {}
            for pref_code, pref_dict in merged_prefectures.items():
                for area_dict in pref_dict["areas"]:
                    for mesh_dict in area_dict["meshes"]:
                        risk_timeline = mesh_dict.get("risk_3hour_max_timeline", [])
                        risk_point = next((r for r in risk_timeline if r["ft"] == 0), None)
                        if risk_point:
                            mesh_risks[mesh_dict["code"]] = risk_point["value"]
                        else:
                            mesh_risks[mesh_dict["code"]] = 0

                        # メッシュ座標も追加（地図表示に必要）
                        mesh_coords[mesh_dict["code"]] = {
                            "lat": mesh_dict["lat"],
                            "lon": mesh_dict["lon"]
                        }

            return jsonify({
                "status": "success",
                "session_id": fork_session_id,  # 新しいフォークセッションID
                "base_session_id": base_session_id,
                "is_fork": True,
                "adjusted": True,
                "ft": 0,
                "mesh_risks": mesh_risks,
                "mesh_coords": mesh_coords,
                "recalculated_meshes": adjusted_mesh_count
            })

        except Exception as e:
            logger.error(f"Session recalculation error: {e}", exc_info=True)
            return jsonify({
                "status": "error",
                "error": str(e),
                "session_id": session_id
            }), 500


    def _aggregate_area_risk_timeline(self, meshes_dict_list):
        """
        市町村のリスクタイムラインを集計（辞書形式）

        Args:
            meshes_dict_list: メッシュ辞書のリスト

        Returns:
            [{"ft": 0, "value": 3}, ...] 形式のリスクタイムライン
        """
        # FTごとの最大リスク値を集計
        ft_max_risk = {}

        for mesh_dict in meshes_dict_list:
            for risk_point in mesh_dict.get('risk_3hour_max_timeline', []):
                ft = risk_point['ft']
                value = risk_point['value']
                if ft not in ft_max_risk or value > ft_max_risk[ft]:
                    ft_max_risk[ft] = value

        # ソートして返す
        return [{"ft": ft, "value": ft_max_risk[ft]} for ft in sorted(ft_max_risk.keys())]

    def _aggregate_subdivision_risk_timeline(self, pref_dict, area_names):
        """
        二次細分のリスクタイムラインを集計（辞書形式）

        Args:
            pref_dict: 府県辞書
            area_names: この二次細分に属する市町村名リスト

        Returns:
            [{"ft": 0, "value": 3}, ...] 形式のリスクタイムライン
        """
        ft_max_risk = {}

        for area_dict in pref_dict['areas']:
            if area_dict['name'] in area_names:
                for mesh_dict in area_dict['meshes']:
                    for risk_point in mesh_dict.get('risk_3hour_max_timeline', []):
                        ft = risk_point['ft']
                        value = risk_point['value']
                        if ft not in ft_max_risk or value > ft_max_risk[ft]:
                            ft_max_risk[ft] = value

        return [{"ft": ft, "value": ft_max_risk[ft]} for ft in sorted(ft_max_risk.keys())]

    def _aggregate_prefecture_risk_timeline(self, pref_dict):
        """
        府県全体のリスクタイムラインを集計（辞書形式）

        Args:
            pref_dict: 府県辞書

        Returns:
            [{"ft": 0, "value": 3}, ...] 形式のリスクタイムライン
        """
        ft_max_risk = {}

        for area_dict in pref_dict['areas']:
            for mesh_dict in area_dict['meshes']:
                for risk_point in mesh_dict.get('risk_3hour_max_timeline', []):
                    ft = risk_point['ft']
                    value = risk_point['value']
                    if ft not in ft_max_risk or value > ft_max_risk[ft]:
                        ft_max_risk[ft] = value

        return [{"ft": ft, "value": ft_max_risk[ft]} for ft in sorted(ft_max_risk.keys())]
