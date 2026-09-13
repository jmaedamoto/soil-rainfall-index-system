"""Example integration: inspect rainfall without exporting a full CSV."""

import argparse
import math

from analyzed_rainfall_decoder import decode_file


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("grib2_file", help="Input analyzed-rainfall GRIB2 file")
    args = parser.parse_args()
    analyzed = decode_file(args.grib2_file)
    print(f"Valid time (UTC): {analyzed.valid_time.isoformat()}")
    print(f"Accumulation: {analyzed.accumulation_minutes} minutes")
    print(f"Grid: {analyzed.grid.width} x {analyzed.grid.height}")

    valid_count = 0
    maximum = None
    for index, rainfall_mm in enumerate(analyzed.iter_values()):
        if math.isnan(rainfall_mm):
            continue
        if valid_count < 5:
            latitude, longitude = analyzed.grid.coordinates(index)
            print(f"{latitude:.6f}, {longitude:.6f}: {rainfall_mm:g} mm")
        valid_count += 1
        maximum = rainfall_mm if maximum is None else max(maximum, rainfall_mm)
    print(f"Valid points: {valid_count}")
    print(f"Maximum rainfall (mm): {maximum}")


if __name__ == "__main__":
    main()
