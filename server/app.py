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
from api.routes.main_routes import (
    init_main_routes,
    main_development_bp,
    main_production_bp,
)
from api.routes.cache_routes import cache_bp
from api.routes.rainfall_routes import rainfall_bp
from api.routes.session_routes import (
    create_development_session_blueprint,
    create_production_session_blueprint,
)
from api.controllers.session_controller import SessionController
from config.config_service import ConfigService

# ============================================================
# API設定（エンドポイントプレフィックスの一元管理）
# ============================================================
# Apache 側で '/dosya/api' にマウントするため、Flask 側の既定プレフィックスは空
# 別環境で必要な場合のみ SOIL_RAINFALL_API_PREFIX で上書きする
API_PREFIX = os.environ.get('SOIL_RAINFALL_API_PREFIX', '')
# ============================================================


def _register_development_blueprints(app: Flask, data_dir: str, session_controller: SessionController):
    """開発・検証向けBlueprintを登録"""
    app.register_blueprint(main_development_bp, url_prefix=API_PREFIX)
    app.register_blueprint(
        create_development_session_blueprint(session_controller),
        url_prefix=API_PREFIX,
    )
    app.register_blueprint(cache_bp, url_prefix=API_PREFIX)
    app.register_blueprint(rainfall_bp, url_prefix=API_PREFIX)


def _log_registered_endpoint_sets(route_profile: str):
    """登録するエンドポイント群をログ出力"""
    logger.info("利用可能エンドポイント:")
    logger.info("  本番API:")
    logger.info(f"    POST /dosya/api{API_PREFIX}/production-soil-rainfall-index-with-urls")
    logger.info(f"    GET  /dosya/api{API_PREFIX}/session/<session_id>/prefecture/<prefecture_code>")
    logger.info(f"    GET  /dosya/api{API_PREFIX}/session/<session_id>/risk-at-time?ft=<ft>")
    logger.info(f"    GET  /dosya/api{API_PREFIX}/session/<session_id>/rainfall-data")
    logger.info(f"    POST /dosya/api{API_PREFIX}/session/<session_id>/recalculate")

    if route_profile != "production":
        logger.info("  開発・検証API:")
        logger.info(f"    GET  /dosya/api{API_PREFIX}/")
        logger.info(f"    GET  /dosya/api{API_PREFIX}/health")
        logger.info(f"    GET  /dosya/api{API_PREFIX}/data-check")
        logger.info(f"    POST /dosya/api{API_PREFIX}/soil-rainfall-index")
        logger.info(f"    GET  /dosya/api{API_PREFIX}/production-soil-rainfall-index")
        logger.info(f"    POST /dosya/api{API_PREFIX}/test-session-with-local-bins")
        logger.info(f"    GET  /dosya/api{API_PREFIX}/session/<session_id>")
        logger.info(f"    GET  /dosya/api{API_PREFIX}/session/<session_id>/mesh/<mesh_code>")
        logger.info(f"    DELETE /dosya/api{API_PREFIX}/session/<session_id>")
        logger.info(f"    GET  /dosya/api{API_PREFIX}/sessions")
        logger.info(f"    GET  /dosya/api{API_PREFIX}/sessions/stats")
        logger.info(f"    POST /dosya/api{API_PREFIX}/sessions/cleanup")
        logger.info(f"    GET  /dosya/api{API_PREFIX}/cache/list")
        logger.info(f"    GET  /dosya/api{API_PREFIX}/cache/stats")
        logger.info(f"    GET  /dosya/api{API_PREFIX}/cache/<cache_key>")
        logger.info(f"    GET  /dosya/api{API_PREFIX}/cache/<cache_key>/exists")
        logger.info(f"    DELETE /dosya/api{API_PREFIX}/cache/<cache_key>")
        logger.info(f"    POST /dosya/api{API_PREFIX}/cache/cleanup")
        logger.info(f"    GET  /dosya/api{API_PREFIX}/rainfall-forecast")
        logger.info(f"    POST /dosya/api{API_PREFIX}/rainfall-adjustment")


def create_app(data_dir: str = "data"):
    """Flaskアプリケーション作成ファクトリー"""
    app = Flask(__name__)
    CORS(app)
    config_service = ConfigService()
    route_profile = config_service.get_api_route_profile()

    # ルート初期化
    init_main_routes(data_dir)

    # セッションBlueprint作成と登録
    # main_routes.pyで作成されたsession_serviceを使用
    from api.routes.main_routes import session_service

    if session_service:
        session_controller = SessionController(session_service)
        app.register_blueprint(
            create_production_session_blueprint(session_controller),
            url_prefix=API_PREFIX,
        )

        if route_profile != "production":
            _register_development_blueprints(app, data_dir, session_controller)

    # 本番向けBlueprintは常に登録
    app.register_blueprint(main_production_bp, url_prefix=API_PREFIX)

    return app

# アプリケーション作成
app = create_app()

# ログ設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

if __name__ == '__main__':
    logger.info("土壌雨量指数計算API起動 - 本番運用版")
    route_profile = ConfigService().get_api_route_profile()
    logger.info(f"APIプレフィックス: '{API_PREFIX}'")
    logger.info(f"APIルートプロファイル: '{route_profile}'")
    _log_registered_endpoint_sets(route_profile)

    app.run(debug=True, host='0.0.0.0', port=5000)
