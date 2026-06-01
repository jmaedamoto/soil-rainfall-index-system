import os
import sys
from types import SimpleNamespace
from unittest.mock import Mock

from flask import Flask

SERVER_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if SERVER_ROOT not in sys.path:
    sys.path.insert(0, SERVER_ROOT)

from src.api.controllers.main_controller import MainController


def _build_controller(cache_save_result=True, session_service=None):
    controller = MainController.__new__(MainController)
    controller.session_service = session_service
    controller.data_dir = "data"
    controller.config_service = SimpleNamespace(
        normalize_guidance_type=lambda value: value or "msm",
        validate_guidance_initial_time=lambda initial, guidance_type: None,
        build_swi_url=lambda initial: f"swi://{initial.isoformat()}",
        build_guidance_url=lambda initial, guidance_type: (
            f"{guidance_type}://{initial.isoformat()}"
        ),
    )
    result = {
        "prefectures": {
            "shiga": {
                "name": "滋賀県",
                "areas": [],
            }
        }
    }
    controller.main_service = SimpleNamespace(
        calculation_service=SimpleNamespace(
            normalize_risk_rule=lambda value: value or "legacy"
        ),
        data_service=SimpleNamespace(
            prepare_areas=Mock(return_value=[]),
        ),
        main_process_from_separate_urls=Mock(return_value=result),
    )
    controller.cache_service = SimpleNamespace(
        generate_cache_key=Mock(return_value="cache-key"),
        get_cached_result=Mock(return_value=None),
        is_cache_write_in_progress=Mock(return_value=False),
        is_cache_materializing=Mock(return_value=False),
        is_calculation_in_progress=Mock(return_value=False),
        wait_for_cache_materialization=Mock(return_value=False),
        acquire_calculation_lock=Mock(return_value=True),
        set_cached_result=Mock(return_value=cache_save_result),
        release_calculation_lock=Mock(),
    )
    return controller, result


def _request_payload():
    return {
        "swi_initial": "2026-05-20T00:00:00Z",
        "guidance_initial": "2026-05-20T00:00:00Z",
        "guidance_type": "msm",
        "risk_rule": "legacy",
        "region": "kinki",
    }


def test_calculation_owner_saves_region_cache_before_returning_session():
    app = Flask(__name__)
    session_service = SimpleNamespace(create_session=Mock(return_value="session-1"))
    controller, result = _build_controller(session_service=session_service)

    with app.test_request_context(json=_request_payload()):
        response = controller.production_soil_rainfall_index_with_urls()

    assert response.status_code == 200
    assert response.get_json()["session_id"] == "session-1"
    controller.main_service.main_process_from_separate_urls.assert_called_once_with(
        "swi://2026-05-20T00:00:00",
        "msm://2026-05-20T00:00:00",
        guidance_type="msm",
        risk_rule="legacy",
        use_cache=False,
        async_cache_save=False,
    )
    controller.cache_service.set_cached_result.assert_called_once_with(
        "cache-key",
        result,
        "2026-05-20T00:00:00",
        "2026-05-20T00:00:00",
        "msm",
        "legacy",
    )
    controller.cache_service.release_calculation_lock.assert_called_once_with("cache-key")
    session_service.create_session.assert_called_once()


def test_cache_save_failure_releases_lock_and_returns_500():
    app = Flask(__name__)
    session_service = SimpleNamespace(create_session=Mock(return_value="session-1"))
    controller, _ = _build_controller(
        cache_save_result=False,
        session_service=session_service,
    )

    with app.test_request_context(json=_request_payload()):
        response, status_code = controller.production_soil_rainfall_index_with_urls()

    assert status_code == 500
    assert response.get_json()["status"] == "error"
    controller.cache_service.release_calculation_lock.assert_called_once_with("cache-key")
    session_service.create_session.assert_not_called()
