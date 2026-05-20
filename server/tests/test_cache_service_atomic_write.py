import os
import sys

SERVER_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if SERVER_ROOT not in sys.path:
    sys.path.insert(0, SERVER_ROOT)
SRC_ROOT = os.path.join(SERVER_ROOT, "src")
if SRC_ROOT not in sys.path:
    sys.path.insert(0, SRC_ROOT)

from src.services.cache_service import CacheService


def test_set_cached_result_can_be_read_back_immediately(tmp_path):
    service = CacheService(cache_dir=str(tmp_path))
    cache_key = "test-cache"
    payload = {
        "prefectures": {
            "shiga": {
                "areas": [
                    {
                        "meshes": [
                            {
                                "code": "mesh-1",
                                "risk_3hour_max_timeline": [
                                    {"ft": 0, "value": 2},
                                    {"ft": 3, "value": 4},
                                ],
                            }
                        ]
                    }
                ]
            }
        }
    }

    assert service.set_cached_result(
        cache_key,
        payload,
        "2026-05-20T03:00:00",
        "2026-05-20T03:00:00",
        "msm",
        "legacy",
    )

    cached = service.get_cached_result(cache_key)
    assert cached == payload
