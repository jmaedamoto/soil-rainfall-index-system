import os
import sys

SERVER_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if SERVER_ROOT not in sys.path:
    sys.path.insert(0, SERVER_ROOT)
SRC_ROOT = os.path.join(SERVER_ROOT, "src")
if SRC_ROOT not in sys.path:
    sys.path.insert(0, SRC_ROOT)

from src.services.rainfall_adjustment_service import RainfallAdjustmentService


def test_area_max_fill_uses_each_ft_area_max_for_all_meshes():
    service = RainfallAdjustmentService()
    prefectures = {
        "shiga": {
            "name": "滋賀県",
            "areas": [
                {
                    "name": "大津市",
                    "meshes": [
                        {
                            "code": "mesh-1",
                            "rain_timeline": [
                                {"ft": 0, "value": 1.0},
                                {"ft": 3, "value": 8.0},
                            ],
                        },
                        {
                            "code": "mesh-2",
                            "rain_timeline": [
                                {"ft": 0, "value": 5.0},
                                {"ft": 3, "value": 2.0},
                            ],
                        },
                    ],
                }
            ],
        }
    }

    adjusted = service.build_area_max_filled_mesh_rainfall_from_session(
        prefectures,
        {"滋賀県_大津市": {0: 0.0, 3: 0.0}},
    )

    assert adjusted == {
        "mesh-1": [(0, 5.0), (3, 8.0)],
        "mesh-2": [(0, 5.0), (3, 8.0)],
    }


def test_area_max_fill_uses_max_value_for_overlapping_meshes():
    service = RainfallAdjustmentService()
    prefectures = {
        "shiga": {
            "name": "滋賀県",
            "areas": [
                {
                    "name": "大津市",
                    "meshes": [
                        {
                            "code": "shared",
                            "rain_timeline": [
                                {"ft": 0, "value": 1.0},
                                {"ft": 3, "value": 4.0},
                            ],
                        },
                        {
                            "code": "otsu-max",
                            "rain_timeline": [
                                {"ft": 0, "value": 6.0},
                                {"ft": 3, "value": 2.0},
                            ],
                        },
                    ],
                },
                {
                    "name": "草津市",
                    "meshes": [
                        {
                            "code": "shared",
                            "rain_timeline": [
                                {"ft": 0, "value": 1.0},
                                {"ft": 3, "value": 4.0},
                            ],
                        },
                        {
                            "code": "kusatsu-max",
                            "rain_timeline": [
                                {"ft": 0, "value": 3.0},
                                {"ft": 3, "value": 9.0},
                            ],
                        },
                    ],
                },
            ],
        }
    }

    adjusted = service.build_area_max_filled_mesh_rainfall_from_session(
        prefectures,
        {
            "滋賀県_大津市": {0: 0.0, 3: 0.0},
            "滋賀県_草津市": {0: 0.0, 3: 0.0},
        },
    )

    assert adjusted["shared"] == [(0, 6.0), (3, 9.0)]
