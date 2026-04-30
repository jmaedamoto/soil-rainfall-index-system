from __future__ import annotations

import json
import os
import sys
from copy import deepcopy
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SERVER_DIR = ROOT / "server"
OUTPUT_DIR = ROOT / "client" / "docs" / "manual-fixtures"

sys.path.insert(0, str(SERVER_DIR))

from app import create_app  # noqa: E402


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> None:
    os.environ.setdefault("SOIL_RAINFALL_ROUTE_PROFILE", "all")
    app = create_app(str(SERVER_DIR / "data"))

    with app.test_client() as client:
      session_resp = client.post("/test-session-with-local-bins")
      if session_resp.status_code != 200:
          raise SystemExit(f"fixture session creation failed: {session_resp.status_code} {session_resp.get_data(as_text=True)}")

      session_data = session_resp.get_json()
      if not session_data or session_data.get("status") != "success":
          raise SystemExit(f"fixture session creation failed: {session_data}")

      session_id = session_data["session_id"]
      first_pref = session_data["available_prefectures"][0]
      first_ft = session_data["available_times"][0]

      prefecture_resp = client.get(f"/session/{session_id}/prefecture/{first_pref}")
      risk_resp = client.get(f"/session/{session_id}/risk-at-time?ft={first_ft}&include_coords=true")
      rainfall_resp = client.get(f"/session/{session_id}/rainfall-data")

      prefecture_data = prefecture_resp.get_json()
      risk_data = risk_resp.get_json()
      rainfall_data = rainfall_resp.get_json()

      if not prefecture_data or prefecture_data.get("status") != "success":
          raise SystemExit(f"prefecture fixture failed: {prefecture_data}")
      if not risk_data or risk_data.get("status") != "success":
          raise SystemExit(f"risk fixture failed: {risk_data}")
      if not rainfall_data or rainfall_data.get("status") != "success":
          raise SystemExit(f"rainfall fixture failed: {rainfall_data}")

      adjusted_session = deepcopy(session_data)
      adjusted_session["session_id"] = "mock-adjusted-session"

      adjusted_risk = deepcopy(risk_data)
      adjusted_risk["mesh_risks"] = {
          mesh_code: min(4, risk + 1) if isinstance(risk, int) else risk
          for mesh_code, risk in adjusted_risk["mesh_risks"].items()
      }

      sample_area_key = next(iter(rainfall_data["area_rainfall"].keys()))
      sample_series = rainfall_data["area_rainfall"][sample_area_key]
      sample_series_24h = rainfall_data["area_rainfall_24hour"][sample_area_key]

      meta = {
          "session_id": session_id,
          "adjusted_session_id": adjusted_session["session_id"],
          "first_prefecture": first_pref,
          "first_ft": first_ft,
          "sample_area_key": sample_area_key,
          "sample_area_ft": sample_series[0]["ft"],
          "sample_area_24h_ft": sample_series_24h[0]["ft"],
      }

      write_json(OUTPUT_DIR / "meta.json", meta)
      write_json(OUTPUT_DIR / "session-info.json", session_data)
      write_json(OUTPUT_DIR / "session-info-adjusted.json", adjusted_session)
      write_json(OUTPUT_DIR / "prefecture-data.json", prefecture_data)
      write_json(OUTPUT_DIR / "risk-at-time.json", risk_data)
      write_json(OUTPUT_DIR / "risk-at-time-adjusted.json", adjusted_risk)
      write_json(OUTPUT_DIR / "rainfall-data.json", rainfall_data)


if __name__ == "__main__":
    main()
