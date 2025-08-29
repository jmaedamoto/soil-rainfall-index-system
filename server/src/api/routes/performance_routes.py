# -*- coding: utf-8 -*-
"""
パフォーマンス分析APIルート (Blueprint)
"""
from flask import Blueprint
from ..controllers.performance_controller import PerformanceController

# Blueprint作成
performance_bp = Blueprint('performance', __name__)

# コントローラーインスタンス（データディレクトリは後で設定）
performance_controller = None

def init_performance_routes(data_dir: str = "data"):
    """パフォーマンスルートを初期化"""
    global performance_controller
    performance_controller = PerformanceController(data_dir)

@performance_bp.route('/api/test-performance-analysis', methods=['GET'])
def test_performance_analysis():
    """パフォーマンス解析版：各処理の実行時間を詳細計測"""
    return performance_controller.test_performance_analysis()

@performance_bp.route('/api/test-performance-summary', methods=['GET'])
def test_performance_summary():
    """軽量パフォーマンスサマリー"""
    return performance_controller.test_performance_summary()

@performance_bp.route('/api/test-csv-optimization', methods=['GET'])
def test_csv_optimization():
    """CSV最適化効果の比較"""
    return performance_controller.test_csv_optimization()

@performance_bp.route('/api/test-parallel-processing', methods=['GET'])
def test_parallel_processing():
    """並列処理性能の評価"""
    return performance_controller.test_parallel_processing()

@performance_bp.route('/api/test-optimization-analysis', methods=['GET'])
def test_optimization_analysis():
    """最適化分析：最適な処理手法の推奨"""
    return performance_controller.test_optimization_analysis()