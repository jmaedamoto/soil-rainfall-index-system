# -*- coding: utf-8 -*-
"""
土壌雨量指数APIルーティング
"""
from flask import Blueprint, jsonify
import logging

from src.api.controllers import SoilRainfallController

logger = logging.getLogger(__name__)

# Blueprint作成
soil_rainfall_bp = Blueprint('soil_rainfall', __name__)

# コントローラーインスタンス
controller = SoilRainfallController()


@soil_rainfall_bp.route('/api/test-full-soil-rainfall-index', methods=['GET'])
def test_full_soil_rainfall_index():
    """テスト用：binファイルを使って全メッシュのmain_processと同じ形式のJSONを返す（API層使用）"""
    result, status_code = controller.test_full_soil_rainfall_index()
    return jsonify(result), status_code


@soil_rainfall_bp.route('/api/health', methods=['GET'])
def health():
    """ヘルスチェック"""
    result, status_code = controller.health_check()
    return jsonify(result), status_code


@soil_rainfall_bp.route('/api/data-check', methods=['GET'])
def data_check():
    """データファイル確認"""
    result, status_code = controller.data_check()
    return jsonify(result), status_code