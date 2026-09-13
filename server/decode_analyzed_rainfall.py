#!/usr/bin/env python3
"""Decode JMA analyzed-rainfall GRIB2 data and export it as CSV."""

from __future__ import annotations

import argparse
import csv
import math
import os
import sys
import tempfile
from pathlib import Path


SERVER_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(SERVER_ROOT / "src"))

from services.grib2_service import Grib2Service  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "気象庁仕様 No.11601 の解析雨量／速報版解析雨量GRIB2をCSVへ変換します。"
        )
    )
    parser.add_argument("grib2_file", type=Path, help="入力GRIB2ファイル")
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        help="出力CSV（省略時は入力ファイルの拡張子を .csv に置換）",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="既存の出力CSVを上書きする",
    )
    return parser.parse_args()


def export_csv(grib2_file: Path, output_file: Path, force: bool = False) -> int:
    if not grib2_file.is_file():
        raise FileNotFoundError(f"入力ファイルが見つかりません: {grib2_file}")
    if output_file.exists() and not force:
        raise FileExistsError(
            f"出力ファイルは既に存在します: {output_file}（上書きは --force）"
        )

    service = Grib2Service()
    base_info, analyzed = service.unpack_analyzed_rainfall_grib2_from_file(
        str(grib2_file)
    )
    rainfall = analyzed["rainfall"]
    if len(rainfall) != base_info.grid_num:
        raise ValueError(
            "展開した格子数がヘッダーと一致しません: "
            f"header={base_info.grid_num}, decoded={len(rainfall)}"
        )
    if base_info.x_num * base_info.y_num != base_info.grid_num:
        raise ValueError(
            "格子形状が資料点数と一致しません: "
            f"x={base_info.x_num}, y={base_info.y_num}, grids={base_info.grid_num}"
        )

    output_file.parent.mkdir(parents=True, exist_ok=True)
    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="",
            prefix=f".{output_file.name}.",
            suffix=".tmp",
            dir=output_file.parent,
            delete=False,
        ) as csv_file:
            temp_path = Path(csv_file.name)
            writer = csv.writer(csv_file, lineterminator="\n")
            writer.writerow(
                ["grid_index", "x", "y", "latitude", "longitude", "rainfall_mm"]
            )

            for grid_index, value in enumerate(rainfall):
                y, x = divmod(grid_index, base_info.x_num)
                latitude = (base_info.s_lat - y * base_info.d_lat) / 1_000_000
                longitude = (base_info.s_lon + x * base_info.d_lon) / 1_000_000
                writer.writerow(
                    [
                        grid_index,
                        x + 1,
                        y + 1,
                        f"{latitude:.6f}",
                        f"{longitude:.6f}",
                        "" if math.isnan(value) else f"{value:g}",
                    ]
                )

        os.replace(temp_path, output_file)
        temp_path = None
    finally:
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)

    print(f"入力: {grib2_file}")
    print(f"出力: {output_file}")
    print(f"基準時刻 (UTC): {base_info.initial_date.isoformat()}")
    print(f"対象時刻 (UTC): {analyzed['valid_time'].isoformat()}")
    print(f"積算時間: {analyzed['accumulation_minutes']}分")
    print(f"格子数: {base_info.x_num} x {base_info.y_num} = {base_info.grid_num}")
    return 0


def main() -> int:
    args = parse_args()
    input_file = args.grib2_file.resolve()
    output_file = (args.output or input_file.with_suffix(".csv")).resolve()
    try:
        return export_csv(input_file, output_file, force=args.force)
    except (OSError, ValueError) as error:
        print(f"エラー: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
