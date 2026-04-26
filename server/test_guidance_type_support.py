# -*- coding: utf-8 -*-
"""
guidance_type 対応の回帰テスト
"""
from datetime import datetime
from pathlib import Path
import sys

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.append(str(PROJECT_ROOT))
sys.path.append(str(PROJECT_ROOT / "src"))

from src.config.config_service import ConfigService
from src.services.cache_service import CacheService


def test_build_guidance_url_supports_msm_and_gsm():
    config = ConfigService()
    msm_time = datetime(2025, 10, 28, 15, 0, 0)
    gsm_time = datetime(2025, 10, 28, 18, 0, 0)

    msm_url = config.build_guidance_url(msm_time, "msm")
    gsm_url = config.build_guidance_url(gsm_time, "gsm")

    assert msm_url.endswith("guid_msm_grib2_20251028150000_rmax03.bin")
    assert gsm_url.endswith("guid_gsm_grib2_20251028180000_rmax.bin")


def test_gsm_guidance_url_rejects_non_6hour_initial_time():
    config = ConfigService()

    with pytest.raises(ValueError, match="Invalid guidance_initial for gsm"):
        config.build_guidance_url(datetime(2026, 4, 26, 3, 0, 0), "gsm")


def test_generate_cache_key_includes_guidance_type():
    msm_key = CacheService.generate_cache_key(
        "2025-01-01T00:00:00",
        "2025-01-01T06:00:00",
        "msm",
    )
    gsm_key = CacheService.generate_cache_key(
        "2025-01-01T00:00:00",
        "2025-01-01T06:00:00",
        "gsm",
    )

    assert msm_key == "swi_20250101000000_guid_msm_20250101060000"
    assert gsm_key == "swi_20250101000000_guid_gsm_20250101060000"
    assert msm_key != gsm_key
