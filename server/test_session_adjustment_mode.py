# -*- coding: utf-8 -*-
"""
セッションの調整方式保持に関する回帰テスト
"""
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.append(str(PROJECT_ROOT))
sys.path.append(str(PROJECT_ROOT / "src"))

from src.services.session_service import SessionService


def test_fork_session_keeps_adjustment_mode_and_input_mode():
    service = SessionService()

    prefectures = {
        "28": {
            "name": "兵庫県",
            "code": "28",
            "areas": [],
            "secondary_subdivisions": [],
            "prefecture_risk_timeline": [],
        }
    }

    base_session_id = service.create_session(
        prefectures=prefectures,
        swi_initial_time="2026-04-25T00:00:00Z",
        guidance_initial_time="2026-04-25T00:00:00Z",
        calculation_time="2026-04-25T00:00:01Z",
    )

    fork_session_id = service.create_fork_session(
        base_session_id=base_session_id,
        adjustments={"兵庫県_神戸市": [{"ft": 3, "value": 10}]},
        recalculated_meshes={},
        input_mode="24hour",
        adjustment_mode="fill_3hour",
    )

    session = service.get_session(fork_session_id)
    info = service.get_session_info(fork_session_id)

    assert session["input_mode"] == "24hour"
    assert session["adjustment_mode"] == "fill_3hour"
    assert info["input_mode"] == "24hour"
    assert info["adjustment_mode"] == "fill_3hour"
