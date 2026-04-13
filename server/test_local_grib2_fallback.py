# -*- coding: utf-8 -*-
"""
ローカルGRIB2フォールバック設定のテスト
"""
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.append(str(PROJECT_ROOT))
sys.path.append(str(PROJECT_ROOT / "src"))

from src.config.config_service import ConfigService
from src.services.main_service import MainService


def test_config_service_reads_local_grib2_fallback(tmp_path):
    config_path = tmp_path / "app_config.yaml"
    config_path.write_text(
        "\n".join(
            [
                "data:",
                '  directory: "data"',
                "  local_grib2_fallback:",
                "    enabled: true",
                '    swi_path: "/tmp/swi.bin"',
                '    guidance_path: "/tmp/guidance.bin"',
            ]
        ),
        encoding="utf-8",
    )

    config_service = ConfigService(str(config_path))

    assert config_service.get_local_grib2_fallback_config() == {
        "enabled": True,
        "swi_path": "/tmp/swi.bin",
        "guidance_path": "/tmp/guidance.bin",
    }


def test_main_service_loads_from_local_fallback_when_enabled(tmp_path):
    swi_file = tmp_path / "swi.bin"
    guidance_file = tmp_path / "guidance.bin"
    swi_file.write_bytes(b"swi-bytes")
    guidance_file.write_bytes(b"guidance-bytes")

    main_service = MainService()
    main_service.config_service.config = {
        "data": {
            "local_grib2_fallback": {
                "enabled": True,
                "swi_path": str(swi_file),
                "guidance_path": str(guidance_file),
            }
        }
    }

    swi_bytes, guidance_bytes = main_service._load_grib2_bytes(
        "https://example.com/swi.bin",
        "https://example.com/guidance.bin",
    )

    assert swi_bytes == b"swi-bytes"
    assert guidance_bytes == b"guidance-bytes"


def test_main_service_downloads_when_local_fallback_disabled():
    main_service = MainService()
    main_service.config_service.config = {
        "data": {
            "local_grib2_fallback": {
                "enabled": False,
                "swi_path": "/tmp/swi.bin",
                "guidance_path": "/tmp/guidance.bin",
            }
        }
    }

    downloads = []

    def fake_download(url):
        downloads.append(url)
        if "swi" in url:
            return b"remote-swi"
        return b"remote-guidance"

    main_service.grib2_service.download_file = fake_download

    swi_bytes, guidance_bytes = main_service._load_grib2_bytes(
        "https://example.com/swi.bin",
        "https://example.com/guidance.bin",
    )

    assert swi_bytes == b"remote-swi"
    assert guidance_bytes == b"remote-guidance"
    assert downloads == [
        "https://example.com/swi.bin",
        "https://example.com/guidance.bin",
    ]
