# -*- coding: utf-8 -*-
"""
セッション管理APIルート
"""
from flask import Blueprint

def create_session_blueprint(session_controller):
    """
    セッション管理APIのBlueprintを作成

    Args:
        session_controller: SessionControllerインスタンス

    Returns:
        Blueprint: セッション管理API Blueprint
    """
    session_bp = Blueprint('session_bp', __name__)

    # セッション情報取得
    @session_bp.route('/session/<session_id>', methods=['GET'])
    def get_session_info(session_id):
        return session_controller.get_session_info(session_id)

    # 府県データ取得
    @session_bp.route('/session/<session_id>/prefecture/<prefecture_code>', methods=['GET'])
    def get_prefecture_data(session_id, prefecture_code):
        return session_controller.get_prefecture_data(session_id, prefecture_code)

    # 指定時刻の全メッシュリスク値取得
    @session_bp.route('/session/<session_id>/risk-at-time', methods=['GET'])
    def get_risk_at_time(session_id):
        return session_controller.get_risk_at_time(session_id)

    # メッシュ詳細データ取得
    @session_bp.route('/session/<session_id>/mesh/<mesh_code>', methods=['GET'])
    def get_mesh_detail(session_id, mesh_code):
        return session_controller.get_mesh_detail(session_id, mesh_code)

    # セッション削除
    @session_bp.route('/session/<session_id>', methods=['DELETE'])
    def delete_session(session_id):
        return session_controller.delete_session(session_id)

    # セッション一覧取得（デバッグ用）
    @session_bp.route('/sessions', methods=['GET'])
    def list_sessions():
        return session_controller.list_sessions()

    # セッション統計情報取得
    @session_bp.route('/sessions/stats', methods=['GET'])
    def get_session_stats():
        return session_controller.get_session_stats()

    # 期限切れセッションクリーンアップ
    @session_bp.route('/sessions/cleanup', methods=['POST'])
    def cleanup_sessions():
        return session_controller.cleanup_sessions()

    return session_bp
