# -*- coding: utf-8 -*-
"""
セッション管理APIコントローラー
"""
from flask import jsonify, request
from datetime import datetime
import logging
import os
import sys
from typing import Any, Dict, List

# プロジェクトルートをパスに追加
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(project_root)

from services.session_service import SessionService
from services.rainfall_adjustment_service import RainfallAdjustmentService
from services.calculation_service_numpy import CalculationServiceNumpy

logger = logging.getLogger(__name__)


class SessionController:
    """セッション管理APIコントローラー"""

    def __init__(self, session_service: SessionService):
        self.session_service = session_service
        self.rainfall_adjustment_service = RainfallAdjustmentService()

    @staticmethod
    def _trace_prefix(session_id: str) -> str:
        forwarded_for = request.headers.get('X-Forwarded-For')
        remote_addr = forwarded_for.split(',')[0].strip() if forwarded_for else request.remote_addr
        return f"[session_id={session_id} pid={os.getpid()} remote={remote_addr or 'unknown'}]"

    @staticmethod
    def _build_max_timeline_from_meshes(
        meshes: List[Dict[str, Any]],
        timeline_key: str
    ) -> List[Dict[str, float]]:
        max_by_ft: Dict[int, float] = {}

        for mesh in meshes:
            for point in mesh.get(timeline_key, []):
                ft = int(point["ft"])
                value = float(point["value"])
                if ft not in max_by_ft or value > max_by_ft[ft]:
                    max_by_ft[ft] = value

        return [
            {"ft": ft, "value": value}
            for ft, value in sorted(max_by_ft.items())
        ]

    @staticmethod
    def _build_row_metrics_from_meshes(meshes: List[Dict[str, Any]]) -> Dict[str, Any]:
        positive_thresholds = [
            int(mesh.get("dosyakei_bound", 0))
            for mesh in meshes
            if int(mesh.get("dosyakei_bound", 0)) > 0
        ]

        return {
            "level4_threshold": min(positive_thresholds, default=0),
            "swi_timeline": SessionController._build_max_timeline_from_meshes(
                meshes, "swi_timeline"
            ),
            "rain_3hour_timeline": SessionController._build_max_timeline_from_meshes(
                meshes, "rain_timeline"
            ),
        }

    @staticmethod
    def _collect_subdivision_meshes(
        prefecture: Dict[str, Any],
        area_names: List[str]
    ) -> List[Dict[str, Any]]:
        area_name_set = set(area_names)
        meshes: List[Dict[str, Any]] = []

        for area in prefecture.get("areas", []):
            if area.get("name") in area_name_set:
                meshes.extend(area.get("meshes", []))

        return meshes

    def get_session_info(self, session_id: str):
        """
        セッション情報取得

        GET /session/<session_id>
        """
        try:
            trace_prefix = self._trace_prefix(session_id)
            logger.info(f"{trace_prefix} セッション情報取得開始")
            info = self.session_service.get_session_info(session_id)

            if info is None:
                logger.warning(f"{trace_prefix} セッション情報取得失敗: session not found")
                return jsonify({
                    "status": "error",
                    "error": "Session not found or expired",
                    "session_id": session_id
                }), 404

            logger.info(
                f"{trace_prefix} セッション情報取得成功: "
                f"prefecture_count={info.get('prefecture_count')} "
                f"guidance_type={info.get('guidance_type')} risk_rule={info.get('risk_rule')}"
            )
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
            trace_prefix = self._trace_prefix(session_id)
            logger.info(f"{trace_prefix} 府県データ取得開始: prefecture_code={prefecture_code}")
            prefecture = self.session_service.get_prefecture(
                session_id,
                prefecture_code
            )

            if prefecture is None:
                logger.warning(
                    f"{trace_prefix} 府県データ取得失敗: prefecture_code={prefecture_code}"
                )
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
                "risk_rule": self.session_service.get_session(session_id).get("risk_rule", "legacy"),
                "areas": [
                    {
                        "name": area["name"],
                        "secondary_subdivision_name": area["secondary_subdivision_name"],
                        "risk_timeline": area["risk_timeline"],
                        **self._build_row_metrics_from_meshes(area.get("meshes", [])),
                    }
                    for area in prefecture["areas"]
                ],
                "secondary_subdivisions": [
                    {
                        "name": subdiv["name"],
                        "area_names": subdiv.get("area_names", []),
                        "risk_timeline": subdiv.get("risk_timeline", []),
                        **self._build_row_metrics_from_meshes(
                            self._collect_subdivision_meshes(
                                prefecture,
                                subdiv.get("area_names", []),
                            )
                        ),
                    }
                    for subdiv in prefecture.get("secondary_subdivisions", [])
                ],
                "prefecture_risk_timeline": prefecture.get("prefecture_risk_timeline", []),
                **self._build_row_metrics_from_meshes(
                    [
                        mesh
                        for area in prefecture.get("areas", [])
                        for mesh in area.get("meshes", [])
                    ]
                ),
            }

            # デバッグ: レスポンスデータの確認
            logger.info(
                f"{trace_prefix} 府県データ取得成功: prefecture_code={prefecture_code} "
                f"areas={len(response_data['areas'])} "
                f"secondary_subdivisions={len(response_data['secondary_subdivisions'])} "
                f"prefecture_risk_timeline_length={len(response_data['prefecture_risk_timeline'])}"
            )
            if response_data['areas']:
                first_area = response_data['areas'][0]
                logger.info(
                    f"{trace_prefix} First area: {first_area['name']}, "
                    f"risk_timeline length: {len(first_area.get('risk_timeline', []))}"
                )
                if first_area.get('risk_timeline'):
                    logger.info(f"{trace_prefix} First risk point: {first_area['risk_timeline'][0]}")

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
            trace_prefix = self._trace_prefix(session_id)
            ft = request.args.get('ft', type=int)
            if ft is None:
                logger.warning(f"{trace_prefix} 時刻別リスク取得失敗: ft パラメータ不足")
                return jsonify({
                    "status": "error",
                    "error": "Parameter 'ft' is required"
                }), 400

            # include_coords パラメータ（デフォルトtrue、後方互換性のため）
            include_coords_str = request.args.get('include_coords', 'true').lower()
            include_coords = include_coords_str == 'true'
            logger.info(
                f"{trace_prefix} 時刻別リスク取得開始: ft={ft} include_coords={include_coords}"
            )

            session = self.session_service.get_session(session_id)
            if session is None:
                logger.warning(f"{trace_prefix} 時刻別リスク取得失敗: session not found")
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
                            logger.info(
                                f"{trace_prefix} [get_risk_at_time] FT={ft}, Mesh={mesh['code']}, "
                                f"Risk={risk_value}, Timeline={mesh['risk_3hour_max_timeline'][:3]}"
                            )
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

            logger.info(
                f"{trace_prefix} 時刻別リスク取得成功: ft={ft} "
                f"mesh_count={len(mesh_risks)} coords_included={include_coords}"
            )

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
            area_rainfall_24hour, subdivision_rainfall_24hour = \
                self.rainfall_adjustment_service.aggregate_rainfall_24hour_from_session(prefectures)

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
                "subdivision_rainfall": subdivision_rainfall,
                "area_rainfall_24hour": area_rainfall_24hour,
                "subdivision_rainfall_24hour": subdivision_rainfall_24hour,
                "guidance_type": session.get('guidance_type', 'msm'),
                "risk_rule": session.get('risk_rule', 'legacy'),
                "input_mode": session.get('input_mode', '3hour'),
                "adjustment_mode": session.get('adjustment_mode', 'ratio_3hour')
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
                "adjustment_mode": "ratio_3hour",  # 省略時は ratio_3hour
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

            aggregate_adjustments_raw = data.get('aggregate_adjustments', {})
            aggregate_adjustments = {}
            for area_key, timeline in aggregate_adjustments_raw.items():
                aggregate_adjustments[area_key] = {
                    point['ft']: point['value'] for point in timeline
                }

            input_mode = data.get('input_mode', '3hour')
            adjustment_mode = data.get('adjustment_mode', 'ratio_3hour')
            session_guidance_type = (session.get('guidance_type', 'msm') or 'msm').lower()
            session_risk_rule = CalculationServiceNumpy.normalize_risk_rule(
                session.get('risk_rule', 'legacy')
            )
            requested_guidance_type = data.get('guidance_type')
            requested_risk_rule = data.get('risk_rule')
            guidance_type = session_guidance_type
            risk_rule = session_risk_rule

            if requested_guidance_type is not None:
                normalized_requested_guidance_type = requested_guidance_type.lower()
                if normalized_requested_guidance_type not in {'msm', 'gsm'}:
                    return jsonify({
                        "status": "error",
                        "error": f"Unsupported guidance_type: {requested_guidance_type}",
                        "session_id": session_id
                    }), 400
                if normalized_requested_guidance_type != session_guidance_type:
                    return jsonify({
                        "status": "error",
                        "error": (
                            "guidance_type does not match the session. "
                            f"session={session_guidance_type}, request={normalized_requested_guidance_type}"
                        ),
                        "session_id": session_id
                    }), 400

            if requested_risk_rule is not None:
                try:
                    normalized_requested_risk_rule = CalculationServiceNumpy.normalize_risk_rule(
                        requested_risk_rule
                    )
                except ValueError:
                    return jsonify({
                        "status": "error",
                        "error": f"Unsupported risk_rule: {requested_risk_rule}",
                        "session_id": session_id
                    }), 400
                if normalized_requested_risk_rule != session_risk_rule:
                    return jsonify({
                        "status": "error",
                        "error": (
                            "risk_rule does not match the session. "
                            f"session={session_risk_rule}, request={normalized_requested_risk_rule}"
                        ),
                        "session_id": session_id
                    }), 400

            if input_mode not in {'3hour', '24hour'}:
                return jsonify({
                    "status": "error",
                    "error": f"Unsupported input_mode: {input_mode}",
                    "session_id": session_id
                }), 400

            allowed_adjustment_modes = {
                '3hour': {'ratio_3hour', 'fill_3hour'},
                '24hour': {
                    'fill_24hour_uniform',
                    'ratio_24hour_uniform',
                    'fill_24hour_peak_mesh',
                    'ratio_24hour_peak_mesh',
                },
            }
            if adjustment_mode not in allowed_adjustment_modes[input_mode]:
                return jsonify({
                    "status": "error",
                    "error": f"Unsupported adjustment_mode: {adjustment_mode}",
                    "session_id": session_id
                }), 400

            logger.info(
                "調整対象領域数: 3hour=%s件, 24hour=%s件, input_mode=%s, adjustment_mode=%s, guidance_type=%s, risk_rule=%s",
                len(adjustments),
                len(aggregate_adjustments),
                input_mode,
                adjustment_mode,
                guidance_type,
                risk_rule,
            )

            # NumPyベクトル化版サービス（高速）
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

            expanded_aggregate_adjustments = dict(aggregate_adjustments)
            for subdiv_key, subdiv_rain in list(aggregate_adjustments.items()):
                if subdiv_key in subdiv_to_areas:
                    info = subdiv_to_areas[subdiv_key]
                    for area_name in info['area_names']:
                        area_key = f"{info['pref_name']}_{area_name}"
                        if area_key not in expanded_aggregate_adjustments:
                            expanded_aggregate_adjustments[area_key] = subdiv_rain
                            logger.info(f"二次細分 {subdiv_key} → 市町村 {area_key} に24時間調整を展開")

            if input_mode == '24hour':
                if adjustment_mode == 'fill_24hour_uniform':
                    adjusted_mesh_rainfall = self.rainfall_adjustment_service.build_fill_24hour_uniform_from_session(
                        existing_prefectures_dict,
                        expanded_aggregate_adjustments
                    )
                elif adjustment_mode == 'ratio_24hour_uniform':
                    adjusted_mesh_rainfall = self.rainfall_adjustment_service.build_ratio_24hour_uniform_from_session(
                        existing_prefectures_dict,
                        expanded_aggregate_adjustments
                    )
                elif adjustment_mode == 'fill_24hour_peak_mesh':
                    adjusted_mesh_rainfall = self.rainfall_adjustment_service.build_fill_24hour_peak_mesh_from_session(
                        existing_prefectures_dict,
                        expanded_aggregate_adjustments
                    )
                else:
                    adjusted_mesh_rainfall = self.rainfall_adjustment_service.build_ratio_24hour_peak_mesh_from_session(
                        existing_prefectures_dict,
                        expanded_aggregate_adjustments
                    )
            elif adjustment_mode == 'fill_3hour':
                adjusted_mesh_rainfall = self.rainfall_adjustment_service.build_filled_mesh_rainfall_from_session(
                    existing_prefectures_dict,
                    expanded_adjustments
                )
            else:
                mesh_ratios = self.rainfall_adjustment_service.calculate_mesh_ratios_from_session(
                    existing_prefectures_dict,
                    expanded_adjustments
                )
                adjusted_mesh_rainfall = self.rainfall_adjustment_service.build_adjusted_mesh_rainfall_from_session(
                    existing_prefectures_dict,
                    mesh_ratios
                )

            # Step 1: 調整対象メッシュのデータを収集
            import time
            collect_start = time.time()

            for pref_code, pref_dict in existing_prefectures_dict.items():
                for area_dict in pref_dict['areas']:
                    for mesh_dict in area_dict['meshes']:
                        mesh_code = mesh_dict['code']
                        new_rain_timeline = adjusted_mesh_rainfall.get(mesh_code)
                        if not new_rain_timeline:
                            continue

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
                            'rain_3hour': new_rain_timeline,
                            'original_rain_3hour': [
                                (int(point['ft']), float(point['value']))
                                for point in mesh_dict.get('rain_timeline', [])
                            ],
                            'rain_1hour_max': [
                                (int(point['ft']), float(point['value']))
                                for point in mesh_dict.get('rain_1hour_max_timeline', [])
                            ],
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
                numpy_results = calculation_service_numpy.recalculate_meshes_vectorized(
                    mesh_data_list,
                    risk_rule=risk_rule,
                )

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
                adjustments=aggregate_adjustments_raw if input_mode == '24hour' else adjustments_raw,
                recalculated_meshes=recalculated_meshes,
                input_mode=input_mode,
                adjustment_mode=adjustment_mode
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
                "guidance_type": guidance_type,
                "risk_rule": risk_rule,
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
