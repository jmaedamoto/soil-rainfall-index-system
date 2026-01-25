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

        GET /session/<session_id>/risk-at-time?ft=<ft>
        """
        try:
            ft = request.args.get('ft', type=int)
            if ft is None:
                return jsonify({
                    "status": "error",
                    "error": "Parameter 'ft' is required"
                }), 400

            session = self.session_service.get_session(session_id)
            if session is None:
                return jsonify({
                    "status": "error",
                    "error": "Session not found or expired",
                    "session_id": session_id
                }), 404

            # 全府県の全メッシュからリスク値と座標を抽出（辞書形式）
            mesh_risks = {}
            mesh_coords = {}
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

                        # メッシュ50357712の詳細ログ
                        if mesh['code'] == '50357712':
                            logger.info(f"[get_risk_at_time] ★特定メッシュ★ FT={ft}, Mesh={mesh['code']}, Risk={risk_value}, Timeline={mesh['risk_3hour_max_timeline'][:5]}")

                        mesh_risks[mesh["code"]] = risk_value
                        mesh_coords[mesh["code"]] = {
                            "lat": mesh["lat"],
                            "lon": mesh["lon"]
                        }

            return jsonify({
                "status": "success",
                "ft": ft,
                "mesh_risks": mesh_risks,
                "mesh_coords": mesh_coords
            })

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
        雨量調整後の再計算（セッションベース・最適化版）

        POST /session/<session_id>/recalculate

        Request Body:
            {
                "adjustments": {"府県名_市町村名": [{"ft": 0, "value": 10.5}, ...]},
                "swi_initial": "2025-01-01T00:00:00Z",  # 使用されない（互換性のため残す）
                "guidance_initial": "2025-01-01T00:00:00Z",  # 使用されない
                "data_source": "test"  # 使用されない
            }

        Returns:
            - セッションを更新（調整対象メッシュのみ）
            - 初期時刻のメッシュリスクのみ返す（軽量レスポンス）

        最適化:
            - GRIB2解析をスキップ（セッションの既存データを使用）
            - 調整対象メッシュのみ処理
            - 辞書形式のまま処理（Prefectureオブジェクト変換なし）
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

            logger.info(f"Session {session_id}: 雨量調整再計算開始")

            # セッションから既存の辞書形式データを取得
            existing_prefectures_dict = session['prefectures']

            # adjustmentsを配列形式から辞書形式に変換
            adjustments_raw = data['adjustments']
            adjustments = {}
            for area_key, timeline in adjustments_raw.items():
                adjustments[area_key] = {
                    point['ft']: point['value'] for point in timeline
                }

            logger.info(f"調整対象市町村数: {len(adjustments)}件")

            # サービス初期化（SWI再計算のみ使用）
            from services.calculation_service import CalculationService
            from models import Mesh, SwiTimeSeries, Risk
            calculation_service = CalculationService()

            # 調整対象メッシュを特定
            adjusted_mesh_count = 0
            adjusted_area_set = set()

            # 各府県・市町村・メッシュを走査して雨量調整を適用
            for pref_code, pref_dict in existing_prefectures_dict.items():
                for area_dict in pref_dict['areas']:
                    area_key = f"{pref_dict['name']}_{area_dict['name']}"

                    if area_key in adjustments:
                        adjusted_area_set.add(area_key)
                        adjusted_rain = adjustments[area_key]

                        # この市町村の全メッシュを処理
                        for mesh_dict in area_dict['meshes']:
                            # 雨量timelineを調整
                            mesh_dict['rain_timeline'] = [
                                {"ft": ft, "value": adjusted_rain[ft]}
                                for ft in sorted(adjusted_rain.keys())
                            ]

                            # 調整された3時間雨量から1時間雨量を推定
                            rain_1hour_estimated = []
                            for rain_point in mesh_dict['rain_timeline']:
                                ft_3h = rain_point['ft']
                                rain_3h = rain_point['value']
                                rain_1h_avg = rain_3h / 3.0

                                for hour_offset in range(3):
                                    ft_1h = ft_3h - 3 + hour_offset + 1
                                    if ft_1h >= 0:
                                        rain_1hour_estimated.append(
                                            SwiTimeSeries(ft=ft_1h, value=rain_1h_avg)
                                        )

                            # 一時的なMeshオブジェクトを作成してSWI・リスクを再計算
                            temp_mesh = Mesh(
                                area_name=area_dict['name'],
                                code=mesh_dict['code'],
                                lon=mesh_dict['lon'],
                                lat=mesh_dict['lat'],
                                x=0, y=0,
                                advisary_bound=mesh_dict['advisary_bound'],
                                warning_bound=mesh_dict['warning_bound'],
                                dosyakei_bound=mesh_dict['dosyakei_bound'],
                                swi=[
                                    SwiTimeSeries(ft=p['ft'], value=p['value'])
                                    for p in mesh_dict.get('swi_timeline', [])
                                ],
                                swi_hourly=[],
                                rain_1hour=rain_1hour_estimated,
                                rain_1hour_max=[],
                                rain_3hour=[
                                    SwiTimeSeries(ft=p['ft'], value=p['value'])
                                    for p in mesh_dict['rain_timeline']
                                ],
                                risk_hourly=[],
                                risk_3hour_max=[]
                            )

                            # SWI・リスク再計算
                            calculation_service.recalculate_swi_and_risk(temp_mesh)

                            # 結果を辞書に戻す
                            mesh_dict['swi_timeline'] = [
                                {"ft": s.ft, "value": s.value} for s in temp_mesh.swi
                            ]
                            mesh_dict['risk_3hour_max_timeline'] = [
                                {"ft": r.ft, "value": r.value} for r in temp_mesh.risk_3hour_max
                            ]

                            adjusted_mesh_count += 1

            logger.info(f"調整メッシュ数: {adjusted_mesh_count}件")

            # 調整された市町村のリスクタイムラインを再集計
            for pref_code, pref_dict in existing_prefectures_dict.items():
                for area_dict in pref_dict['areas']:
                    area_key = f"{pref_dict['name']}_{area_dict['name']}"

                    if area_key in adjusted_area_set:
                        # この市町村の全メッシュからリスクタイムラインを集計
                        area_dict['risk_timeline'] = self._aggregate_area_risk_timeline(
                            area_dict['meshes']
                        )

            # 調整された市町村を含む二次細分の集約を更新
            for pref_code, pref_dict in existing_prefectures_dict.items():
                for subdiv_dict in pref_dict.get('secondary_subdivisions', []):
                    # この二次細分に調整された市町村が含まれるか確認
                    subdiv_areas = subdiv_dict.get('area_names', [])
                    if subdiv_areas and any(f"{pref_dict['name']}_{area_name}" in adjusted_area_set for area_name in subdiv_areas):
                        # 二次細分のリスクタイムラインを再集計
                        subdiv_dict['risk_timeline'] = self._aggregate_subdivision_risk_timeline(
                            pref_dict, subdiv_areas
                        )

                # 府県全体のリスクタイムラインを更新
                if any(area_key.startswith(pref_dict['name']) for area_key in adjusted_area_set):
                    pref_dict['prefecture_risk_timeline'] = self._aggregate_prefecture_risk_timeline(
                        pref_dict
                    )

            # セッションを更新
            self.session_service.sessions[session_id]["prefectures"] = existing_prefectures_dict
            self.session_service.sessions[session_id]["adjusted"] = True

            logger.info(f"Session {session_id}: セッション更新完了")

            # 軽量レスポンス: 初期時刻（FT=0）のメッシュリスクと座標を返す
            mesh_risks = {}
            mesh_coords = {}
            for pref_code, pref_dict in existing_prefectures_dict.items():
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
                "session_id": session_id,
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
