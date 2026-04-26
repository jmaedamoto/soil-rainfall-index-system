# -*- coding: utf-8 -*-
"""
危険度ルール切替の回帰テスト
"""
from pathlib import Path
import sys

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.append(str(PROJECT_ROOT))
sys.path.append(str(PROJECT_ROOT / "src"))

from src.models.data_models import Risk, SwiTimeSeries
from src.services.calculation_service import CalculationService
from src.services.calculation_service_numpy import CalculationServiceNumpy


def test_apply_risk_rule_to_hourly_promotes_lead_times_before_level4():
    service = CalculationService()
    risk_hourly = [
        Risk(ft=0, value=0),
        Risk(ft=1, value=0),
        Risk(ft=2, value=0),
        Risk(ft=3, value=1),
        Risk(ft=4, value=0),
        Risk(ft=5, value=0),
        Risk(ft=6, value=4),
        Risk(ft=7, value=4),
    ]

    adjusted = service.apply_risk_rule_to_hourly(
        risk_hourly,
        "lead_time_to_level4",
    )

    assert [(point.ft, point.value) for point in adjusted] == [
        (0, 2),
        (1, 2),
        (2, 2),
        (3, 2),
        (4, 3),
        (5, 3),
        (6, 4),
        (7, 4),
    ]


def test_calc_hourly_risk_keeps_legacy_rule_by_default():
    service = CalculationService()
    swi_hourly = [
        SwiTimeSeries(ft=0, value=10),
        SwiTimeSeries(ft=1, value=20),
        SwiTimeSeries(ft=2, value=35),
        SwiTimeSeries(ft=3, value=80),
    ]

    risk_hourly = service.calc_hourly_risk(
        swi_hourly,
        advisary_bound=15,
        warning_bound=30,
        dosyakei_bound=70,
    )

    assert [(point.ft, point.value) for point in risk_hourly] == [
        (0, 0),
        (1, 2),
        (2, 3),
        (3, 4),
    ]


def test_apply_risk_rule_vectorized_matches_scalar_behavior():
    service = CalculationServiceNumpy()
    risk_hourly = np.array([
        [0, 0],
        [0, 1],
        [0, 0],
        [1, 0],
        [0, 0],
        [0, 0],
        [4, 4],
    ], dtype=np.int32)

    adjusted = service.apply_risk_rule_vectorized(
        risk_hourly,
        "lead_time_to_level4",
    )

    assert adjusted[:, 0].tolist() == [2, 2, 2, 2, 3, 3, 4]
    assert adjusted[:, 1].tolist() == [2, 2, 2, 2, 3, 3, 4]
