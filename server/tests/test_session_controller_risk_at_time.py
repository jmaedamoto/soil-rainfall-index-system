import os
import sys
from types import SimpleNamespace

from flask import Flask

SERVER_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if SERVER_ROOT not in sys.path:
    sys.path.insert(0, SERVER_ROOT)

from src.api.controllers.session_controller import SessionController


def _build_controller(session):
    controller = SessionController.__new__(SessionController)
    controller.session_service = SimpleNamespace(get_session=lambda session_id: session)
    return controller


def test_get_risk_at_time_returns_503_when_requested_ft_is_missing():
    app = Flask(__name__)
    session = {
        "prefectures": {
            "28": {
                "areas": [
                    {
                        "meshes": [
                            {
                                "code": "mesh-1",
                                "lat": 35.0,
                                "lon": 135.0,
                                "risk_3hour_max_timeline": [],
                            }
                        ]
                    }
                ]
            }
        }
    }
    controller = _build_controller(session)

    with app.test_request_context("/session/test/risk-at-time?ft=0&include_coords=false"):
        response, status_code = controller.get_risk_at_time("test-session")

    assert status_code == 503
    body = response.get_json()
    assert body["status"] == "error"
    assert body["ft"] == 0
    assert body["missing_mesh_count"] == 1
    assert body["mesh_count"] == 1


def test_get_risk_at_time_returns_mesh_risks_when_requested_ft_exists():
    app = Flask(__name__)
    session = {
        "prefectures": {
            "28": {
                "areas": [
                    {
                        "meshes": [
                            {
                                "code": "mesh-1",
                                "lat": 35.0,
                                "lon": 135.0,
                                "risk_3hour_max_timeline": [
                                    {"ft": 0, "value": 2},
                                    {"ft": 3, "value": 1},
                                ],
                            }
                        ]
                    }
                ]
            }
        }
    }
    controller = _build_controller(session)

    with app.test_request_context("/session/test/risk-at-time?ft=0&include_coords=false"):
        response = controller.get_risk_at_time("test-session")

    assert response.status_code == 200
    body = response.get_json()
    assert body["status"] == "success"
    assert body["ft"] == 0
    assert body["mesh_risks"] == {"mesh-1": 2}
    assert body["mesh_coords"] == {"mesh-1": {"lat": 35.0, "lon": 135.0}}
