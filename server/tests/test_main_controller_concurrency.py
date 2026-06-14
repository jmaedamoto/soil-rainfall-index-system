import os
import sys
from types import SimpleNamespace
from unittest.mock import Mock

from flask import Flask

SERVER_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if SERVER_ROOT not in sys.path:
    sys.path.insert(0, SERVER_ROOT)

from src.api.controllers.main_controller import MainController


def _build_controller():
    controller = MainController.__new__(MainController)
    controller.session_service = None
    controller.data_dir = "data"
    controller.config_service = SimpleNamespace(
        normalize_guidance_type=lambda value: value or "msm",
        validate_guidance_initial_time=lambda initial, guidance_type: None,
        build_swi_url=lambda initial: f"swi://{initial.isoformat()}",
        build_guidance_url=lambda initial, guidance_type: (
            f"{guidance_type}://{initial.isoformat()}"
        ),
    )
    controller.main_service = SimpleNamespace(
        calculation_service=SimpleNamespace(
            normalize_risk_rule=lambda value: value or "legacy"
        ),
        main_process_from_separate_urls=Mock(),
    )
    controller.cache_service = SimpleNamespace(
        generate_cache_key=lambda *args: "cache-key",
        get_cached_result=Mock(return_value=None),
        is_cache_write_in_progress=Mock(return_value=False),
        is_cache_materializing=Mock(return_value=False),
        is_calculation_in_progress=Mock(return_value=False),
        wait_for_cache_materialization=Mock(return_value=False),
        acquire_calculation_lock=Mock(return_value=False),
        acquire_calculation_slot=Mock(return_value=True),
        release_calculation_lock=Mock(),
        release_calculation_slot=Mock(),
    )
    return controller


def test_lock_failure_waits_for_cache_instead_of_recomputing():
    app = Flask(__name__)
    controller = _build_controller()
    controller.cache_service.wait_for_cache_materialization.return_value = True
    controller.cache_service.get_cached_result.side_effect = [
        None,
        {"prefectures": {"28": {"name": "兵庫県", "areas": [{"meshes": []}]}}},
    ]

    with app.test_request_context(
        json={
            "swi_initial": "2026-05-20T00:00:00Z",
            "guidance_initial": "2026-05-20T00:00:00Z",
            "guidance_type": "msm",
            "risk_rule": "legacy",
        }
    ):
        response = controller.production_soil_rainfall_index_with_urls()

    assert response.status_code == 200
    assert response.get_json()["status"] == "success"
    controller.main_service.main_process_from_separate_urls.assert_not_called()


def test_lock_failure_returns_202_when_cache_never_materializes():
    app = Flask(__name__)
    controller = _build_controller()

    with app.test_request_context(
        json={
            "swi_initial": "2026-05-20T00:00:00Z",
            "guidance_initial": "2026-05-20T00:00:00Z",
            "guidance_type": "msm",
            "risk_rule": "legacy",
        }
    ):
        response = controller.production_soil_rainfall_index_with_urls()

    assert response.status_code == 202
    assert response.headers["Retry-After"] == "2"
    assert response.get_json()["status"] == "calculating"
    controller.main_service.main_process_from_separate_urls.assert_not_called()


def test_busy_calculation_slot_releases_key_lock_and_returns_202():
    app = Flask(__name__)
    controller = _build_controller()
    controller.cache_service.acquire_calculation_lock.return_value = True
    controller.cache_service.acquire_calculation_slot.return_value = False

    with app.test_request_context(
        json={
            "swi_initial": "2026-05-20T00:00:00Z",
            "guidance_initial": "2026-05-20T00:00:00Z",
            "guidance_type": "msm",
            "risk_rule": "legacy",
            "region": "shikoku",
        }
    ):
        response = controller.production_soil_rainfall_index_with_urls()

    assert response.status_code == 202
    assert response.get_json()["status"] == "calculating"
    controller.cache_service.release_calculation_lock.assert_called_once_with("cache-key")
    controller.main_service.main_process_from_separate_urls.assert_not_called()
