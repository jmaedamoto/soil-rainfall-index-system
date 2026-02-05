"""
キャッシュ管理コントローラ

機能:
- キャッシュ一覧取得
- キャッシュ統計情報取得
- キャッシュ削除
- 期限切れキャッシュクリーンアップ
"""

from flask import jsonify, request
import logging

from services.cache_service import get_cache_service

logger = logging.getLogger(__name__)


def get_cache_list():
    """キャッシュ一覧取得"""
    try:
        cache_service = get_cache_service()
        caches = cache_service.list_caches()

        return jsonify({
            "status": "success",
            "cache_count": len(caches),
            "caches": caches
        }), 200

    except Exception as e:
        logger.error(f"キャッシュ一覧取得エラー: {e}")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500


def get_cache_stats():
    """キャッシュ統計情報取得"""
    try:
        cache_service = get_cache_service()
        stats = cache_service.get_cache_stats()

        return jsonify({
            "status": "success",
            "stats": stats
        }), 200

    except Exception as e:
        logger.error(f"キャッシュ統計取得エラー: {e}")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500


def get_cache_metadata(cache_key: str):
    """キャッシュメタデータ取得"""
    try:
        cache_service = get_cache_service()
        metadata = cache_service.get_metadata(cache_key)

        if not metadata:
            return jsonify({
                "status": "error",
                "message": f"Cache not found: {cache_key}"
            }), 404

        return jsonify({
            "status": "success",
            "metadata": metadata
        }), 200

    except Exception as e:
        logger.error(f"メタデータ取得エラー: {e}")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500


def delete_cache(cache_key: str):
    """キャッシュ削除"""
    try:
        cache_service = get_cache_service()

        if not cache_service.exists(cache_key):
            return jsonify({
                "status": "error",
                "message": f"Cache not found: {cache_key}"
            }), 404

        cache_service.invalidate_cache(cache_key)

        return jsonify({
            "status": "success",
            "message": f"Cache deleted: {cache_key}"
        }), 200

    except Exception as e:
        logger.error(f"キャッシュ削除エラー: {e}")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500


def cleanup_expired_caches():
    """期限切れキャッシュクリーンアップ"""
    try:
        cache_service = get_cache_service()
        deleted_count = cache_service.cleanup_expired_caches()

        return jsonify({
            "status": "success",
            "message": f"Expired caches cleaned up: {deleted_count} deleted"
        }), 200

    except Exception as e:
        logger.error(f"クリーンアップエラー: {e}")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500


def check_cache_exists(cache_key: str):
    """キャッシュ存在確認"""
    try:
        cache_service = get_cache_service()
        exists = cache_service.exists(cache_key)

        return jsonify({
            "status": "success",
            "cache_key": cache_key,
            "exists": exists
        }), 200

    except Exception as e:
        logger.error(f"キャッシュ存在確認エラー: {e}")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500
