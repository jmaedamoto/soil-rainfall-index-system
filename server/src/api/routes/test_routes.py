# -*- coding: utf-8 -*-
"""
テストAPIルート (Blueprint)
"""
from flask import Blueprint
from ..controllers.test_controller import TestController

# Blueprint作成
test_bp = Blueprint('test', __name__)

# コントローラーインスタンス（データディレクトリは後で設定）
test_controller = None

def init_test_routes(data_dir: str = "data"):
    """テストルートを初期化"""
    global test_controller
    test_controller = TestController(data_dir)

@test_bp.route('/api/test-bin-data', methods=['GET'])
def test_bin_data():
    """binファイルデータテスト"""
    return test_controller.test_bin_data()

@test_bp.route('/api/test-grib2-analysis', methods=['GET'])
def test_grib2_analysis():
    """GRIB2解析テスト"""
    return test_controller.test_grib2_analysis()

@test_bp.route('/api/test-soil-rainfall-index', methods=['GET'])
def test_soil_rainfall_index():
    """土壌雨量指数計算テスト（簡易版）"""
    return test_controller.test_soil_rainfall_index()

@test_bp.route('/api/test-single-prefecture', methods=['GET'])
def test_single_prefecture():
    """単一府県テスト"""
    return test_controller.test_single_prefecture()

@test_bp.route('/api/test-full-soil-rainfall-index', methods=['GET'])
def test_full_soil_rainfall_index():
    """テスト用：binファイルを使って全メッシュのmain_processと同じ形式のJSONを返す（元の実装と同じ戻り値形式）"""
    return test_controller.test_full_soil_rainfall_index()

@test_bp.route('/api/test-full-parallel-soil-rainfall-index', methods=['GET'])  
def test_full_parallel_soil_rainfall_index():
    """並列処理版（実際は最適化されたシーケンシャル処理）"""
    return test_controller.test_full_parallel_soil_rainfall_index()