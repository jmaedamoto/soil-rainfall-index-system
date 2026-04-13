# -*- coding: utf-8 -*-
"""
土壌雨量指数計算システム API層
リファクタリング済み: Blueprint-based Routing Architecture
"""
from flask import Flask
from flask_cors import CORS
import logging
import os
import sys

# プロジェクトルートをパスに追加
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.append(project_root)
sys.path.append(os.path.join(project_root, 'src'))

# Blueprintルートのインポート
from api.routes.main_routes import main_bp, init_main_routes
from api.routes.cache_routes import cache_bp
from api.routes.rainfall_routes import rainfall_bp
from api.routes.session_routes import create_session_blueprint
from api.routes.test_routes import test_bp, init_test_routes
from api.controllers.session_controller import SessionController

# ============================================================
# API設定（エンドポイントプレフィックスの一元管理）
# ============================================================
# Apache 側で '/dosya/api' にマウントするため、Flask 側の既定プレフィックスは空
# 別環境で必要な場合のみ SOIL_RAINFALL_API_PREFIX で上書きする
API_PREFIX = os.environ.get('SOIL_RAINFALL_API_PREFIX', '')
# ============================================================

def create_app(data_dir: str = "data"):
    """Flaskアプリケーション作成ファクトリー"""
    app = Flask(__name__)
    CORS(app)

    # ルート初期化
    init_main_routes(data_dir)

    # セッションBlueprint作成と登録
    # main_routes.pyで作成されたsession_serviceを使用
    from api.routes.main_routes import session_service

    if session_service:
        session_controller = SessionController(session_service)
        session_bp = create_session_blueprint(session_controller)
        app.register_blueprint(session_bp, url_prefix=API_PREFIX)

        # テストルートも初期化（session_serviceを渡す）
        init_test_routes(data_dir, session_service)

    # Blueprint登録（全て同じプレフィックスを適用）
    app.register_blueprint(main_bp, url_prefix=API_PREFIX)
    app.register_blueprint(cache_bp, url_prefix=API_PREFIX)
    app.register_blueprint(rainfall_bp, url_prefix=API_PREFIX)
    app.register_blueprint(test_bp, url_prefix=API_PREFIX)

    return app

# アプリケーション作成
app = create_app()

# ログ設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

if __name__ == '__main__':
    logger.info("土壌雨量指数計算API起動 - 本番運用版")
    logger.info(f"APIプレフィックス: '{API_PREFIX}'")
    logger.info("利用可能エンドポイント:")
    logger.info("  メインAPI (main_bp):")
    logger.info(f"    GET  /dosya/api{API_PREFIX}/")
    logger.info(f"    GET  /dosya/api{API_PREFIX}/health")
    logger.info(f"    GET  /dosya/api{API_PREFIX}/data-check")
    logger.info(f"    POST /dosya/api{API_PREFIX}/soil-rainfall-index")
    logger.info(f"    GET  /dosya/api{API_PREFIX}/production-soil-rainfall-index")
    logger.info(f"    POST /dosya/api{API_PREFIX}/production-soil-rainfall-index-with-urls")
    logger.info(f"    POST /dosya/api{API_PREFIX}/test-session-with-local-bins")
    logger.info("  キャッシュAPI (cache_bp):")
    logger.info(f"    GET    /dosya/api{API_PREFIX}/cache/list")
    logger.info(f"    GET    /dosya/api{API_PREFIX}/cache/stats")
    logger.info(f"    GET    /dosya/api{API_PREFIX}/cache/<cache_key>")
    logger.info(f"    GET    /dosya/api{API_PREFIX}/cache/<cache_key>/exists")
    logger.info(f"    DELETE /dosya/api{API_PREFIX}/cache/<cache_key>")
    logger.info(f"    POST   /dosya/api{API_PREFIX}/cache/cleanup")
    logger.info("  雨量調整API (rainfall_bp):")
    logger.info(f"    GET    /dosya/api{API_PREFIX}/rainfall-forecast")
    logger.info(f"    POST   /dosya/api{API_PREFIX}/rainfall-adjustment")
    logger.info("  セッション管理API (session_bp):")
    logger.info(f"    GET    /dosya/api{API_PREFIX}/session/<session_id>")
    logger.info(f"    GET    /dosya/api{API_PREFIX}/session/<session_id>/prefecture/<prefecture_code>")
    logger.info(f"    GET    /dosya/api{API_PREFIX}/session/<session_id>/risk-at-time?ft=<ft>")
    logger.info(f"    GET    /dosya/api{API_PREFIX}/session/<session_id>/mesh/<mesh_code>")
    logger.info(f"    GET    /dosya/api{API_PREFIX}/session/<session_id>/rainfall-data")
    logger.info(f"    POST   /dosya/api{API_PREFIX}/session/<session_id>/recalculate")
    logger.info(f"    DELETE /dosya/api{API_PREFIX}/session/<session_id>")
    logger.info(f"    GET    /dosya/api{API_PREFIX}/sessions")
    logger.info(f"    GET    /dosya/api{API_PREFIX}/sessions/stats")
    logger.info(f"    POST   /dosya/api{API_PREFIX}/sessions/cleanup")
    logger.info("  テストAPI (test_bp):")
    logger.info(f"    GET    /dosya/api{API_PREFIX}/test-bin-data")
    logger.info(f"    GET    /dosya/api{API_PREFIX}/test-grib2-analysis")
    logger.info(f"    GET    /dosya/api{API_PREFIX}/test-soil-rainfall-index")
    logger.info(f"    GET    /dosya/api{API_PREFIX}/test-single-prefecture")
    logger.info(f"    GET    /dosya/api{API_PREFIX}/test-full-soil-rainfall-index")
    logger.info(f"    GET    /dosya/api{API_PREFIX}/test-full-parallel-soil-rainfall-index")

    app.run(debug=True, host='0.0.0.0', port=5000)
