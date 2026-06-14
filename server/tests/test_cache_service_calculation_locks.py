import json
import os
import socket
import sys
from datetime import datetime

SERVER_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if SERVER_ROOT not in sys.path:
    sys.path.insert(0, SERVER_ROOT)

from src.services.cache_service import CacheService


def test_dead_process_calculation_lock_is_recovered(tmp_path, monkeypatch):
    service = CacheService(cache_dir=str(tmp_path))
    lock_path = service._get_lock_path("cache-key")
    lock_path.write_text(
        json.dumps({
            "cache_key": "cache-key",
            "started_at": datetime.now().isoformat(),
            "pid": 99999999,
            "hostname": socket.gethostname(),
            "token": "dead-owner",
        }),
        encoding="utf-8",
    )
    monkeypatch.setattr(service, "_process_is_alive", lambda pid: False)

    assert service.acquire_calculation_lock("cache-key")
    lock_data = json.loads(lock_path.read_text(encoding="utf-8"))
    assert lock_data["pid"] == os.getpid()

    service.release_calculation_lock("cache-key")
    assert not lock_path.exists()


def test_legacy_lock_without_owner_metadata_is_recovered(tmp_path):
    service = CacheService(cache_dir=str(tmp_path))
    lock_path = service._get_lock_path("legacy-cache")
    lock_path.write_text(
        json.dumps({
            "cache_key": "legacy-cache",
            "started_at": datetime.now().isoformat(),
        }),
        encoding="utf-8",
    )

    assert service.acquire_calculation_lock("legacy-cache")
    service.release_calculation_lock("legacy-cache")
    assert not lock_path.exists()


def test_only_one_global_calculation_slot_can_be_owned(tmp_path):
    first = CacheService(cache_dir=str(tmp_path))
    second = CacheService(cache_dir=str(tmp_path))

    assert first.acquire_calculation_slot("first-cache")
    assert not second.acquire_calculation_slot("second-cache")

    second.release_calculation_slot()
    assert first._get_calculation_slot_path().exists()

    first.release_calculation_slot()
    assert not first._get_calculation_slot_path().exists()
