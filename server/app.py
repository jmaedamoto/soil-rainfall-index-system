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
from api.controllers.session_controller import SessionController

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
        app.register_blueprint(session_bp, url_prefix='/api')

    # Blueprint登録
    app.register_blueprint(main_bp)
    app.register_blueprint(cache_bp)
    app.register_blueprint(rainfall_bp)

    return app

# アプリケーション作成
app = create_app()

# ログ設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

if __name__ == '__main__':
    logger.info("土壌雨量指数計算API起動 - 本番運用版")
    logger.info("利用可能エンドポイント:")
    logger.info("  メインAPI (main_bp):")
    logger.info("    GET  /")
    logger.info("    GET  /api/health")
    logger.info("    GET  /api/data-check")
    logger.info("    POST /api/soil-rainfall-index")
    logger.info("    GET  /api/production-soil-rainfall-index")
    logger.info("    POST /api/production-soil-rainfall-index-with-urls")
    logger.info("    POST /api/test-session-with-local-bins")
    logger.info("  キャッシュAPI (cache_bp):")
    logger.info("    GET    /api/cache/list")
    logger.info("    GET    /api/cache/stats")
    logger.info("    GET    /api/cache/<cache_key>")
    logger.info("    GET    /api/cache/<cache_key>/exists")
    logger.info("    DELETE /api/cache/<cache_key>")
    logger.info("    POST   /api/cache/cleanup")
    logger.info("  雨量調整API (rainfall_bp):")
    logger.info("    GET    /api/rainfall-forecast")
    logger.info("    POST   /api/rainfall-adjustment")
    logger.info("  セッション管理API (session_bp):")
    logger.info("    GET    /api/session/<session_id>")
    logger.info("    GET    /api/session/<session_id>/prefecture/<prefecture_code>")
    logger.info("    GET    /api/session/<session_id>/risk-at-time?ft=<ft>")
    logger.info("    GET    /api/session/<session_id>/mesh/<mesh_code>")
    logger.info("    GET    /api/session/<session_id>/rainfall-data")
    logger.info("    POST   /api/session/<session_id>/recalculate")
    logger.info("    DELETE /api/session/<session_id>")
    logger.info("    GET    /api/sessions")
    logger.info("    GET    /api/sessions/stats")
    logger.info("    POST   /api/sessions/cleanup")

    app.run(debug=True, host='0.0.0.0', port=5000)