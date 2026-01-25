"""
キャッシュ管理APIルート

エンドポイント:
- GET  /cache/list - キャッシュ一覧
- GET  /cache/stats - 統計情報
- GET  /cache/<cache_key> - メタデータ取得
- GET  /cache/<cache_key>/exists - 存在確認
- DELETE /cache/<cache_key> - キャッシュ削除
- POST /cache/cleanup - 期限切れクリーンアップ
"""

from flask import Blueprint
from src.api.controllers import cache_controller

# Blueprint作成（プレフィックスはapp.pyで一元管理）
cache_bp = Blueprint('cache', __name__)

# ルート定義
cache_bp.route('/cache/list', methods=['GET'])(
    cache_controller.get_cache_list)

cache_bp.route('/cache/stats', methods=['GET'])(
    cache_controller.get_cache_stats)

cache_bp.route('/cache/<cache_key>', methods=['GET'])(
    cache_controller.get_cache_metadata)

cache_bp.route('/cache/<cache_key>/exists', methods=['GET'])(
    cache_controller.check_cache_exists)

cache_bp.route('/cache/<cache_key>', methods=['DELETE'])(
    cache_controller.delete_cache)

cache_bp.route('/cache/cleanup', methods=['POST'])(
    cache_controller.cleanup_expired_caches)
