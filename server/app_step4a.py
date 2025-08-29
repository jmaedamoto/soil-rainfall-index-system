# -*- coding: utf-8 -*-
"""
土壌雨量指数計算システム API層
リファクタリング済み: コントローラ層分離アーキテクチャ
"""
from flask import Flask, request, jsonify
from flask_cors import CORS
import logging
import os
import sys

# プロジェクトルートをパスに追加
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.append(project_root)
sys.path.append(os.path.join(project_root, 'src'))

# コントローラーのインポート
from api.controllers.main_controller import MainController
from api.controllers.test_controller import TestController
from api.controllers.performance_controller import PerformanceController

app = Flask(__name__)
CORS(app)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# コントローラーインスタンス
main_controller = MainController(data_dir="data")
test_controller = TestController(data_dir="data")
performance_controller = PerformanceController(data_dir="data")

# =============================================================================
# メインAPIエンドポイント（main_controller）
# =============================================================================

@app.route('/', methods=['GET'])
def root():
    """ルートエンドポイント"""
    return main_controller.root()

@app.route('/api/health', methods=['GET'])
def health_check():
    """ヘルスチェックエンドポイント"""
    return main_controller.health_check()

@app.route('/api/data-check', methods=['GET'])
def data_check():
    """データファイル確認エンドポイント"""
    return main_controller.data_check()

@app.route('/api/soil-rainfall-index', methods=['POST'])
def soil_rainfall_index():
    """メイン処理エンドポイント（URL ベース）"""
    return main_controller.soil_rainfall_index()

@app.route('/api/production-soil-rainfall-index', methods=['GET'])
def production_soil_rainfall_index():
    """本番テスト用エンドポイント（GET メソッド）"""
    return main_controller.production_soil_rainfall_index()

# =============================================================================
# テストAPIエンドポイント（test_controller）
# =============================================================================

@app.route('/api/test-bin-data', methods=['GET'])
def test_bin_data():
    """binファイルデータテスト"""
    return test_controller.test_bin_data()

@app.route('/api/test-grib2-analysis', methods=['GET'])
def test_grib2_analysis():
    """GRIB2解析テスト"""
    return test_controller.test_grib2_analysis()

@app.route('/api/test-soil-rainfall-index', methods=['GET'])
def test_soil_rainfall_index():
    """土壌雨量指数計算テスト（簡易版）"""
    return test_controller.test_soil_rainfall_index()

@app.route('/api/test-single-prefecture', methods=['GET'])
def test_single_prefecture():
    """単一府県テスト"""
    return test_controller.test_single_prefecture()

@app.route('/api/test-full-soil-rainfall-index', methods=['GET'])
def test_full_soil_rainfall_index():
    """テスト用：binファイルを使って全メッシュのmain_processと同じ形式のJSONを返す（元の実装と同じ戻り値形式）"""
    return test_controller.test_full_soil_rainfall_index()

@app.route('/api/test-full-parallel-soil-rainfall-index', methods=['GET'])  
def test_full_parallel_soil_rainfall_index():
    """並列処理版（実際は最適化されたシーケンシャル処理）"""
    return test_controller.test_full_parallel_soil_rainfall_index()

# =============================================================================
# パフォーマンス分析エンドポイント（performance_controller）
# =============================================================================

@app.route('/api/test-performance-analysis', methods=['GET'])
def test_performance_analysis():
    """パフォーマンス解析版：各処理の実行時間を詳細計測"""
    return performance_controller.test_performance_analysis()

@app.route('/api/test-performance-summary', methods=['GET'])
def test_performance_summary():
    """軽量パフォーマンスサマリー"""
    return performance_controller.test_performance_summary()

@app.route('/api/test-csv-optimization', methods=['GET'])
def test_csv_optimization():
    """CSV最適化効果の比較"""
    return performance_controller.test_csv_optimization()

@app.route('/api/test-parallel-processing', methods=['GET'])
def test_parallel_processing():
    """並列処理性能の評価"""
    return performance_controller.test_parallel_processing()

@app.route('/api/test-optimization-analysis', methods=['GET'])
def test_optimization_analysis():
    """最適化分析：最適な処理手法の推奨"""
    return performance_controller.test_optimization_analysis()


if __name__ == '__main__':
    logger.info("土壌雨量指数計算API起動 - コントローラ層分離完了版")
    logger.info("アーキテクチャ: STEP 4A完了 - API層コントローラ分離")
    logger.info("利用可能エンドポイント:")
    logger.info("  GET  /")
    logger.info("  GET  /api/health")
    logger.info("  GET  /api/data-check")  
    logger.info("  POST /api/soil-rainfall-index")
    logger.info("  GET  /api/production-soil-rainfall-index")
    logger.info("  GET  /api/test-bin-data")
    logger.info("  GET  /api/test-grib2-analysis")
    logger.info("  GET  /api/test-soil-rainfall-index")
    logger.info("  GET  /api/test-single-prefecture")
    logger.info("  GET  /api/test-full-soil-rainfall-index")
    logger.info("  GET  /api/test-performance-analysis")
    logger.info("  GET  /api/test-performance-summary")
    logger.info("  GET  /api/test-csv-optimization")
    logger.info("  GET  /api/test-parallel-processing")
    logger.info("  GET  /api/test-full-parallel-soil-rainfall-index")
    logger.info("  GET  /api/test-optimization-analysis")
    
    app.run(debug=True, host='0.0.0.0', port=5000)