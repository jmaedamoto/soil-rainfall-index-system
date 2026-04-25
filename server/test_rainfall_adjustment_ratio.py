# -*- coding: utf-8 -*-
"""
雨量調整の比率補正ロジックの回帰テスト
"""
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.append(str(PROJECT_ROOT))
sys.path.append(str(PROJECT_ROOT / "src"))

from src.services.rainfall_adjustment_service import RainfallAdjustmentService


def test_calculate_mesh_ratios_from_session_uses_area_max_values():
    service = RainfallAdjustmentService()

    prefectures = {
        "28": {
            "name": "兵庫県",
            "areas": [
                {
                    "name": "神戸市",
                    "meshes": [
                        {
                            "code": "mesh-1",
                            "rain_timeline": [{"ft": 3, "value": 5.0}, {"ft": 6, "value": 10.0}],
                        },
                        {
                            "code": "mesh-2",
                            "rain_timeline": [{"ft": 3, "value": 10.0}, {"ft": 6, "value": 20.0}],
                        },
                    ],
                }
            ],
        }
    }

    adjustments = {
        "兵庫県_神戸市": {3: 20.0, 6: 10.0},
    }

    mesh_ratios = service.calculate_mesh_ratios_from_session(prefectures, adjustments)
    adjusted = service.build_adjusted_mesh_rainfall_from_session(prefectures, mesh_ratios)

    assert mesh_ratios["mesh-1"][3] == 2.0
    assert mesh_ratios["mesh-2"][6] == 0.5
    assert adjusted["mesh-1"] == [(3, 10.0), (6, 5.0)]
    assert adjusted["mesh-2"] == [(3, 20.0), (6, 10.0)]


def test_calculate_mesh_ratios_from_session_keeps_zero_original_values_unchanged():
    service = RainfallAdjustmentService()

    prefectures = {
        "28": {
            "name": "兵庫県",
            "areas": [
                {
                    "name": "西宮市",
                    "meshes": [
                        {
                            "code": "mesh-3",
                            "rain_timeline": [{"ft": 3, "value": 0.0}, {"ft": 6, "value": 0.0}],
                        }
                    ],
                }
            ],
        }
    }

    adjustments = {
        "兵庫県_西宮市": {3: 12.0},
    }

    mesh_ratios = service.calculate_mesh_ratios_from_session(prefectures, adjustments)
    adjusted = service.build_adjusted_mesh_rainfall_from_session(prefectures, mesh_ratios)

    assert mesh_ratios["mesh-3"][3] == 1.0
    assert adjusted["mesh-3"] == [(3, 0.0), (6, 0.0)]


def test_calculate_mesh_ratios_from_session_uses_max_ratio_for_shared_mesh_codes():
    service = RainfallAdjustmentService()

    prefectures = {
        "28": {
            "name": "兵庫県",
            "areas": [
                {
                    "name": "A市",
                    "meshes": [
                        {
                            "code": "shared-mesh",
                            "rain_timeline": [{"ft": 3, "value": 10.0}],
                        }
                    ],
                },
                {
                    "name": "B市",
                    "meshes": [
                        {
                            "code": "shared-mesh",
                            "rain_timeline": [{"ft": 3, "value": 10.0}],
                        }
                    ],
                },
            ],
        }
    }

    adjustments = {
        "兵庫県_A市": {3: 20.0},
        "兵庫県_B市": {3: 15.0},
    }

    mesh_ratios = service.calculate_mesh_ratios_from_session(prefectures, adjustments)

    assert mesh_ratios["shared-mesh"][3] == 2.0


def test_build_filled_mesh_rainfall_from_session_overwrites_target_area_values():
    service = RainfallAdjustmentService()

    prefectures = {
        "28": {
            "name": "兵庫県",
            "areas": [
                {
                    "name": "神戸市",
                    "meshes": [
                        {
                            "code": "mesh-1",
                            "rain_timeline": [{"ft": 3, "value": 5.0}, {"ft": 6, "value": 10.0}],
                        }
                    ],
                }
            ],
        }
    }

    adjustments = {
        "兵庫県_神戸市": {3: 20.0},
    }

    adjusted = service.build_filled_mesh_rainfall_from_session(prefectures, adjustments)

    assert adjusted["mesh-1"] == [(3, 20.0), (6, 10.0)]


def test_build_filled_mesh_rainfall_from_session_uses_max_value_for_shared_mesh_codes():
    service = RainfallAdjustmentService()

    prefectures = {
        "28": {
            "name": "兵庫県",
            "areas": [
                {
                    "name": "A市",
                    "meshes": [
                        {
                            "code": "shared-mesh",
                            "rain_timeline": [{"ft": 3, "value": 5.0}],
                        }
                    ],
                },
                {
                    "name": "B市",
                    "meshes": [
                        {
                            "code": "shared-mesh",
                            "rain_timeline": [{"ft": 3, "value": 5.0}],
                        }
                    ],
                },
            ],
        }
    }

    adjustments = {
        "兵庫県_A市": {3: 10.0},
        "兵庫県_B市": {3: 20.0},
    }

    adjusted = service.build_filled_mesh_rainfall_from_session(prefectures, adjustments)

    assert adjusted["shared-mesh"] == [(3, 20.0)]
