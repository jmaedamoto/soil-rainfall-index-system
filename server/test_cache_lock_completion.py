# -*- coding: utf-8 -*-
"""
計算ロック解放状態の回帰テスト
"""
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.append(str(PROJECT_ROOT))
sys.path.append(str(PROJECT_ROOT / "src"))

from src.services.cache_service import CacheService


def test_completed_lock_is_removed_on_release(tmp_path):
    cache_service = CacheService(cache_dir=str(tmp_path))
    cache_key = "swi_20260413060000_guid_20260413060000"

    assert cache_service.acquire_calculation_lock(cache_key) is True
    cache_service.release_calculation_lock(cache_key, "session-123")

    assert cache_service.get_base_session_id(cache_key) is None
    assert cache_service.is_calculation_in_progress(cache_key) is False


def test_failed_lock_is_removed_on_release(tmp_path):
    cache_service = CacheService(cache_dir=str(tmp_path))
    cache_key = "swi_20260413090000_guid_20260413090000"

    assert cache_service.acquire_calculation_lock(cache_key) is True
    cache_service.release_calculation_lock(cache_key)

    assert cache_service.is_calculation_in_progress(cache_key) is False
    assert cache_service.get_base_session_id(cache_key) is None
