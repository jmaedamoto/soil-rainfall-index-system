# -*- coding: utf-8 -*-
"""
メインAPIルート (Blueprint)
"""
from flask import Blueprint
from ..controllers.main_controller import MainController

# Blueprint作成
main_bp = Blueprint('main', __name__)

# コントローラーインスタンス（データディレクトリは後で設定）
main_controller = None

def init_main_routes(data_dir: str = "data"):
    """メインルートを初期化"""
    global main_controller
    main_controller = MainController(data_dir)

@main_bp.route('/', methods=['GET'])
def root():
    """ルートエンドポイント"""
    return main_controller.root()

@main_bp.route('/api/health', methods=['GET'])
def health_check():
    """ヘルスチェックエンドポイント"""
    return main_controller.health_check()

@main_bp.route('/api/data-check', methods=['GET'])
def data_check():
    """データファイル確認エンドポイント"""
    return main_controller.data_check()

@main_bp.route('/api/soil-rainfall-index', methods=['POST'])
def soil_rainfall_index():
    """メイン処理エンドポイント（URL ベース）"""
    return main_controller.soil_rainfall_index()

@main_bp.route('/api/production-soil-rainfall-index', methods=['GET'])
def production_soil_rainfall_index():
    """本番テスト用エンドポイント（GET メソッド）"""
    return main_controller.production_soil_rainfall_index()