"""
キャッシュ管理APIルート

エンドポイント:
- GET  /api/cache/list - キャッシュ一覧
- GET  /api/cache/stats - 統計情報
- GET  /api/cache/<cache_key> - メタデータ取得
- GET  /api/cache/<cache_key>/exists - 存在確認
- DELETE /api/cache/<cache_key> - キャッシュ削除
- POST /api/cache/cleanup - 期限切れクリーンアップ
"""

from flask import Blueprint
from src.api.controllers import cache_controller

# Blueprint作成
cache_bp = Blueprint('cache', __name__, url_prefix='/api/cache')

# ルート定義
cache_bp.route('/list', methods=['GET'])(
    cache_controller.get_cache_list)

cache_bp.route('/stats', methods=['GET'])(
    cache_controller.get_cache_stats)

cache_bp.route('/<cache_key>', methods=['GET'])(
    cache_controller.get_cache_metadata)

cache_bp.route('/<cache_key>/exists', methods=['GET'])(
    cache_controller.check_cache_exists)

cache_bp.route('/<cache_key>', methods=['DELETE'])(
    cache_controller.delete_cache)

cache_bp.route('/cleanup', methods=['POST'])(
    cache_controller.cleanup_expired_caches)
