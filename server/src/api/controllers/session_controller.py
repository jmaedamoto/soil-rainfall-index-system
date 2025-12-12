# -*- coding: utf-8 -*-
"""
セッション管理APIコントローラー
"""
from flask import jsonify, request
from datetime import datetime
from dataclasses import asdict
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

        GET /api/session/<session_id>
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
        府県データ取得

        GET /api/session/<session_id>/prefecture/<prefecture_code>
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

            # Prefectureオブジェクトを辞書に変換
            prefecture_dict = asdict(prefecture)

            return jsonify({
                "status": "success",
                "prefecture": prefecture_dict
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

        GET /api/session/<session_id>/risk-at-time?ft=<ft>
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

            # 全府県の全メッシュからリスク値を抽出
            mesh_risks = {}
            prefectures = session['prefectures']

            for pref_code, prefecture in prefectures.items():
                for area in prefecture.areas:
                    for mesh in area.meshes:
                        # 指定されたFTのリスク値を取得
                        risk_value = 0
                        for risk_point in mesh.risk_3hour_max_timeline:
                            if risk_point.ft == ft:
                                risk_value = risk_point.value
                                break

                        mesh_risks[mesh.code] = risk_value

            return jsonify({
                "status": "success",
                "ft": ft,
                "mesh_risks": mesh_risks
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

        GET /api/session/<session_id>/mesh/<mesh_code>
        """
        try:
            session = self.session_service.get_session(session_id)
            if session is None:
                return jsonify({
                    "status": "error",
                    "error": "Session not found or expired",
                    "session_id": session_id
                }), 404

            # 全府県からメッシュを検索
            prefectures = session['prefectures']
            target_mesh = None

            for pref_code, prefecture in prefectures.items():
                for area in prefecture.areas:
                    for mesh in area.meshes:
                        if mesh.code == mesh_code:
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

            # Meshオブジェクトを辞書に変換
            mesh_dict = asdict(target_mesh)

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

        DELETE /api/session/<session_id>
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

        GET /api/sessions
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

        GET /api/sessions/stats
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

        POST /api/sessions/cleanup
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
