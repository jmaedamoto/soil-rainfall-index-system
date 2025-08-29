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
from api.routes.test_routes import test_bp, init_test_routes  
from api.routes.performance_routes import performance_bp, init_performance_routes

def create_app(data_dir: str = "data"):
    """Flaskアプリケーション作成ファクトリー"""
    app = Flask(__name__)
    CORS(app)
    
    # ルート初期化
    init_main_routes(data_dir)
    init_test_routes(data_dir)
    init_performance_routes(data_dir)
    
    # Blueprint登録
    app.register_blueprint(main_bp)
    app.register_blueprint(test_bp)
    app.register_blueprint(performance_bp)
    
    return app

# アプリケーション作成
app = create_app()

# ログ設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

if __name__ == '__main__':
    logger.info("土壌雨量指数計算API起動 - Blueprint-based Routing Architecture")
    logger.info("アーキテクチャ: STEP 4B完了 - Blueprint分離")
    logger.info("利用可能エンドポイント:")
    logger.info("  メインAPI (main_bp):")
    logger.info("    GET  /")
    logger.info("    GET  /api/health")
    logger.info("    GET  /api/data-check")
    logger.info("    POST /api/soil-rainfall-index")
    logger.info("    GET  /api/production-soil-rainfall-index")
    logger.info("  テストAPI (test_bp):")
    logger.info("    GET  /api/test-bin-data")
    logger.info("    GET  /api/test-grib2-analysis")
    logger.info("    GET  /api/test-soil-rainfall-index")
    logger.info("    GET  /api/test-single-prefecture")
    logger.info("    GET  /api/test-full-soil-rainfall-index")
    logger.info("    GET  /api/test-full-parallel-soil-rainfall-index")
    logger.info("  パフォーマンスAPI (performance_bp):")
    logger.info("    GET  /api/test-performance-analysis")
    logger.info("    GET  /api/test-performance-summary")
    logger.info("    GET  /api/test-csv-optimization")
    logger.info("    GET  /api/test-parallel-processing")
    logger.info("    GET  /api/test-optimization-analysis")
    
    app.run(debug=True, host='0.0.0.0', port=5000)