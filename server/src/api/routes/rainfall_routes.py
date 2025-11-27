# -*- coding: utf-8 -*-
"""
雨量調整API Blueprintルート
"""
from flask import Blueprint
from src.api.controllers.rainfall_controller import RainfallController

# Blueprint作成
rainfall_bp = Blueprint('rainfall', __name__)

# コントローラーインスタンス
rainfall_controller = RainfallController()


@rainfall_bp.route('/api/rainfall-forecast', methods=['GET'])
def get_rainfall_forecast():
    """市町村ごとの雨量予想時系列を取得"""
    return rainfall_controller.get_rainfall_forecast()


@rainfall_bp.route('/api/rainfall-adjustment', methods=['POST'])
def calculate_with_adjusted_rainfall():
    """調整後雨量でSWI・危険度を再計算"""
    return rainfall_controller.calculate_with_adjusted_rainfall()
