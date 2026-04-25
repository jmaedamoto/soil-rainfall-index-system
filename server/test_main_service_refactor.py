# -*- coding: utf-8 -*-
"""
MainService のリファクタリング回帰テスト
"""
from pathlib import Path
import sys
from types import SimpleNamespace

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.append(str(PROJECT_ROOT))
sys.path.append(str(PROJECT_ROOT / "src"))

from src.models.data_models import Risk, GuidanceTimeSeries
from src.services.calculation_aggregation_service import CalculationAggregationService
from src.services.main_service import MainService


def test_filter_guidance_data_rebases_forecast_times():
    main_service = MainService()

    guidance_grib2 = {
        "base_info": {},
        "data": [
            {"ft": 0, "value": [10]},
            {"ft": 3, "value": [20]},
            {"ft": 6, "value": [30]},
        ],
        "data_1h": [
            {"ft": 0, "value": [1]},
            {"ft": 3, "value": [2]},
            {"ft": 6, "value": [3]},
        ],
        "data_3h": [
            {"ft": 0, "value": [11]},
            {"ft": 3, "value": [22]},
            {"ft": 6, "value": [33]},
        ],
    }

    guidance_initial = __import__("datetime").datetime(2026, 1, 1, 0, 0, 0)
    swi_initial = __import__("datetime").datetime(2026, 1, 1, 3, 0, 0)

    filtered = main_service._filter_guidance_data(
        guidance_grib2,
        swi_initial,
        guidance_initial,
    )

    assert [item["ft"] for item in filtered["data"]] == [0, 3]
    assert [item["value"] for item in filtered["data"]] == [[20], [30]]
    assert [item["ft"] for item in filtered["data_1h"]] == [0, 3]
    assert [item["ft"] for item in filtered["data_3h"]] == [0, 3]


def test_calculation_aggregation_service_aggregates_max_values():
    aggregation_service = CalculationAggregationService()

    mesh1 = SimpleNamespace()
    mesh1.rain_3hour = [GuidanceTimeSeries(ft=0, value=10), GuidanceTimeSeries(ft=3, value=20)]
    mesh2 = SimpleNamespace()
    mesh2.rain_3hour = [GuidanceTimeSeries(ft=0, value=30), GuidanceTimeSeries(ft=3, value=5)]

    aggregated = aggregation_service.aggregate_timeline([mesh1, mesh2], "rain_3hour", GuidanceTimeSeries)

    assert [(point.ft, point.value) for point in aggregated] == [(0, 30), (3, 20)]


def test_calculation_aggregation_service_aggregates_area_risks():
    aggregation_service = CalculationAggregationService()

    area1 = SimpleNamespace()
    area1.risk_timeline = [Risk(ft=0, value=2), Risk(ft=3, value=1)]
    area2 = SimpleNamespace()
    area2.risk_timeline = [Risk(ft=0, value=0), Risk(ft=3, value=4)]

    aggregated = aggregation_service.aggregate_area_risk_timeline([area1, area2])

    assert [(point.ft, point.value) for point in aggregated] == [(0, 2), (3, 4)]


def test_main_process_from_separate_urls_saves_cache_asynchronously(monkeypatch):
    main_service = MainService()

    swi_initial = __import__("datetime").datetime(2026, 4, 24, 0, 0, 0)
    guidance_initial = __import__("datetime").datetime(2026, 4, 24, 0, 0, 0)
    expected_result = {"prefectures": {"28": {"areas": []}}}

    monkeypatch.setattr(
        main_service,
        "_parse_separate_grib2_from_urls",
        lambda swi_url, guidance_url: (
            SimpleNamespace(initial_date=swi_initial),
            {"swi": []},
            SimpleNamespace(initial_date=guidance_initial),
            {"base_info": {}, "data": [], "data_1h": [], "data_3h": []},
        ),
    )
    monkeypatch.setattr(main_service, "_filter_guidance_data", lambda guidance, *_: guidance)
    monkeypatch.setattr(main_service, "_run_calculation_pipeline", lambda *args: (expected_result, 0))
    monkeypatch.setattr(main_service.cache_service, "get_cached_result", lambda cache_key: None)

    async_calls = []
    monkeypatch.setattr(
        main_service.cache_service,
        "set_cached_result_async",
        lambda cache_key, result, swi_initial_str, guidance_initial_str: async_calls.append(
            (cache_key, result, swi_initial_str, guidance_initial_str)
        ),
    )

    result = main_service.main_process_from_separate_urls(
        "https://example.com/swi.bin",
        "https://example.com/guid.bin",
        use_cache=True,
    )

    assert result == expected_result
    assert len(async_calls) == 1
    assert async_calls[0][1] == expected_result
