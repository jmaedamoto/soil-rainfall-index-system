#!/usr/bin/env python3
"""Standalone JMA analyzed/rapid analyzed rainfall GRIB2 decoder.

This module only uses the Python standard library. It supports the GRIB2 local
templates documented in JMA specification No.11601 (4.50008, 5.200, 7.200).
"""

from __future__ import annotations

import argparse
import csv
import math
import os
import sys
import tempfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterator, Optional, Sequence, Union


__version__ = "1.0.0"


@dataclass(frozen=True)
class GridInfo:
    reference_time: datetime
    point_count: int
    width: int
    height: int
    first_latitude_microdegrees: int
    first_longitude_microdegrees: int
    last_latitude_microdegrees: int
    last_longitude_microdegrees: int
    latitude_increment_microdegrees: int
    longitude_increment_microdegrees: int

    def coordinates(self, index: int) -> tuple[float, float]:
        """Return the latitude/longitude of a zero-based decoded value."""
        if not 0 <= index < self.point_count:
            raise IndexError(f"grid index out of range: {index}")
        row, column = divmod(index, self.width)
        latitude = (
            self.first_latitude_microdegrees
            - row * self.latitude_increment_microdegrees
        ) / 1_000_000
        longitude = (
            self.first_longitude_microdegrees
            + column * self.longitude_increment_microdegrees
        ) / 1_000_000
        return latitude, longitude


@dataclass(frozen=True)
class AnalyzedRainfall:
    grid: GridInfo
    valid_time: datetime
    accumulation_minutes: int
    level_values: tuple[float, ...]
    used_level_max: int
    bits_per_value: int
    packed_values: bytes

    def iter_values(self) -> Iterator[float]:
        """Yield rainfall values in grid scan order; missing values are NaN."""
        max_value_code = self.used_level_max
        run_base = (1 << self.bits_per_value) - 1 - max_value_code
        if run_base <= 0:
            raise ValueError(f"invalid run-length base: {run_base}")

        position = 0
        emitted = 0
        packed = self.packed_values
        while position < len(packed) and emitted < self.grid.point_count:
            value_code = packed[position]
            position += 1
            if value_code > max_value_code:
                raise ValueError(
                    f"run-length code found where a level was expected: {value_code}"
                )
            value = math.nan if value_code == 0 else self.level_values[value_code]

            run_length = 1
            multiplier = 1
            while position < len(packed) and packed[position] > max_value_code:
                run_code = packed[position]
                position += 1
                run_length += (run_code - (max_value_code + 1)) * multiplier
                multiplier *= run_base

            if emitted + run_length > self.grid.point_count:
                raise ValueError(
                    "decoded run exceeds the number of grid points: "
                    f"decoded={emitted}, run={run_length}, expected={self.grid.point_count}"
                )
            for _ in range(run_length):
                yield value
            emitted += run_length

        if emitted != self.grid.point_count:
            raise ValueError(
                "decoded grid count does not match the header: "
                f"decoded={emitted}, expected={self.grid.point_count}"
            )

    def values(self) -> list[float]:
        """Materialize all rainfall values. Prefer iter_values() for large data."""
        return list(self.iter_values())


def _uint(data: bytes, offset: int, size: int) -> int:
    end = offset + size
    if offset < 0 or end > len(data):
        raise ValueError(f"unexpected end of GRIB2 data at byte {offset + 1}")
    return int.from_bytes(data[offset:end], "big")


def _section(data: bytes, offset: int, expected_number: int) -> tuple[int, int]:
    size = _uint(data, offset, 4)
    number = _uint(data, offset + 4, 1)
    if number != expected_number:
        raise ValueError(
            f"expected section {expected_number} at byte {offset + 1}, found {number}"
        )
    if size < 5 or offset + size > len(data):
        raise ValueError(f"invalid section {number} size: {size}")
    return size, offset + size


def _datetime(data: bytes, offset: int) -> datetime:
    try:
        return datetime(
            _uint(data, offset, 2),
            _uint(data, offset + 2, 1),
            _uint(data, offset + 3, 1),
            _uint(data, offset + 4, 1),
            _uint(data, offset + 5, 1),
            _uint(data, offset + 6, 1),
        )
    except ValueError as error:
        raise ValueError(f"invalid GRIB2 date/time at byte {offset + 1}: {error}") from error


def decode(data: bytes) -> AnalyzedRainfall:
    """Decode bytes containing JMA analyzed or rapid analyzed rainfall GRIB2."""
    if len(data) < 20 or data[:4] != b"GRIB" or data[7] != 2:
        raise ValueError("input is not GRIB edition 2 data")
    total_size = _uint(data, 8, 8)
    if total_size != len(data):
        raise ValueError(
            f"GRIB2 length mismatch: header={total_size}, actual={len(data)}"
        )
    if data[-4:] != b"7777":
        raise ValueError("GRIB2 end section (7777) is missing")

    position = 16
    section1_size, position = _section(data, position, 1)
    if section1_size < 21:
        raise ValueError(f"identification section is too short: {section1_size}")
    reference_time = _datetime(data, 16 + 12)

    section3_start = position
    section3_size, position = _section(data, position, 3)
    if section3_size < 72:
        raise ValueError(f"grid definition section is too short: {section3_size}")
    if _uint(data, section3_start + 12, 2) != 0:
        raise ValueError("only latitude/longitude grid template 3.0 is supported")
    if _uint(data, section3_start + 71, 1) != 0:
        raise ValueError("only scanning mode 0x00 is supported")

    grid = GridInfo(
        reference_time=reference_time,
        point_count=_uint(data, section3_start + 6, 4),
        width=_uint(data, section3_start + 30, 4),
        height=_uint(data, section3_start + 34, 4),
        first_latitude_microdegrees=_uint(data, section3_start + 46, 4),
        first_longitude_microdegrees=_uint(data, section3_start + 50, 4),
        last_latitude_microdegrees=_uint(data, section3_start + 55, 4),
        last_longitude_microdegrees=_uint(data, section3_start + 59, 4),
        longitude_increment_microdegrees=_uint(data, section3_start + 63, 4),
        latitude_increment_microdegrees=_uint(data, section3_start + 67, 4),
    )
    if grid.width * grid.height != grid.point_count:
        raise ValueError(
            "grid dimensions do not match point count: "
            f"{grid.width}x{grid.height}!={grid.point_count}"
        )

    section4_start = position
    section4_size, position = _section(data, position, 4)
    if section4_size < 82:
        raise ValueError(f"product definition section is too short: {section4_size}")
    template4 = _uint(data, section4_start + 7, 2)
    if template4 != 50008:
        raise ValueError(f"unsupported product definition template: 4.{template4}")
    category = _uint(data, section4_start + 9, 1)
    parameter = _uint(data, section4_start + 10, 1)
    if (category, parameter) != (1, 200):
        raise ValueError(
            f"product is not analyzed rainfall: category={category}, parameter={parameter}"
        )
    valid_time = _datetime(data, section4_start + 34)
    accumulation_unit = _uint(data, section4_start + 48, 1)
    if accumulation_unit != 0:
        raise ValueError(f"unsupported accumulation time unit: {accumulation_unit}")
    accumulation_minutes = _uint(data, section4_start + 49, 4)

    section5_start = position
    section5_size, position = _section(data, position, 5)
    template5 = _uint(data, section5_start + 9, 2)
    if template5 != 200:
        raise ValueError(f"unsupported data representation template: 5.{template5}")
    represented_points = _uint(data, section5_start + 5, 4)
    if represented_points != grid.point_count:
        raise ValueError(
            f"represented point count mismatch: {represented_points}!={grid.point_count}"
        )
    bits_per_value = _uint(data, section5_start + 11, 1)
    if bits_per_value != 8:
        raise ValueError(f"only 8-bit run-length data is supported: {bits_per_value}")
    used_level_max = _uint(data, section5_start + 12, 2)
    level_count = _uint(data, section5_start + 14, 2)
    scale_factor = _uint(data, section5_start + 16, 1)
    expected_section5_size = 17 + 2 * level_count
    if section5_size < expected_section5_size or used_level_max > level_count:
        raise ValueError("invalid representative-level table")
    levels = [math.nan]
    for level_index in range(1, level_count + 1):
        raw_value = _uint(data, section5_start + 15 + 2 * level_index, 2)
        levels.append(raw_value * (10.0 ** -scale_factor))

    section6_start = position
    _, position = _section(data, position, 6)
    bitmap_indicator = _uint(data, section6_start + 5, 1)
    if bitmap_indicator != 255:
        raise ValueError(f"bitmap data is unsupported: indicator={bitmap_indicator}")

    section7_start = position
    section7_size, position = _section(data, position, 7)
    if position != total_size - 4:
        raise ValueError("unexpected data exists between section 7 and section 8")

    return AnalyzedRainfall(
        grid=grid,
        valid_time=valid_time,
        accumulation_minutes=accumulation_minutes,
        level_values=tuple(levels),
        used_level_max=used_level_max,
        bits_per_value=bits_per_value,
        packed_values=data[section7_start + 5 : section7_start + section7_size],
    )


def decode_file(path: Union[Path, str]) -> AnalyzedRainfall:
    """Read and decode a GRIB2 file."""
    return decode(Path(path).read_bytes())


def export_csv(
    analyzed: AnalyzedRainfall,
    output_path: Union[Path, str],
    *,
    force: bool = False,
    omit_missing: bool = False,
) -> int:
    """Export decoded grid values to CSV and return the number of data rows."""
    destination = Path(output_path)
    if destination.exists() and not force:
        raise FileExistsError(f"output already exists: {destination} (use --force)")
    destination.parent.mkdir(parents=True, exist_ok=True)

    temporary: Optional[Path] = None
    row_count = 0
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="",
            prefix=f".{destination.name}.",
            suffix=".tmp",
            dir=destination.parent,
            delete=False,
        ) as stream:
            temporary = Path(stream.name)
            writer = csv.writer(stream, lineterminator="\n")
            writer.writerow(
                ["grid_index", "x", "y", "latitude", "longitude", "rainfall_mm"]
            )
            for index, value in enumerate(analyzed.iter_values()):
                if omit_missing and math.isnan(value):
                    continue
                row, column = divmod(index, analyzed.grid.width)
                latitude, longitude = analyzed.grid.coordinates(index)
                writer.writerow(
                    [
                        index,
                        column + 1,
                        row + 1,
                        f"{latitude:.6f}",
                        f"{longitude:.6f}",
                        "" if math.isnan(value) else f"{value:g}",
                    ]
                )
                row_count += 1
        os.replace(temporary, destination)
        temporary = None
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    return row_count


def _arguments(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="JMA analyzed/rapid analyzed rainfall GRIB2 to CSV converter"
    )
    parser.add_argument("grib2_file", type=Path, help="input GRIB2 file")
    parser.add_argument("-o", "--output", type=Path, help="output CSV path")
    parser.add_argument("--force", action="store_true", help="overwrite output CSV")
    parser.add_argument(
        "--omit-missing", action="store_true", help="do not write missing grid points"
    )
    parser.add_argument("--version", action="version", version=__version__)
    return parser.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = _arguments(argv)
    source = args.grib2_file.resolve()
    destination = (args.output or source.with_suffix(".csv")).resolve()
    try:
        analyzed = decode_file(source)
        rows = export_csv(
            analyzed,
            destination,
            force=args.force,
            omit_missing=args.omit_missing,
        )
    except (OSError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1

    print(f"input: {source}")
    print(f"output: {destination}")
    print(f"reference time (UTC): {analyzed.grid.reference_time.isoformat()}")
    print(f"valid time (UTC): {analyzed.valid_time.isoformat()}")
    print(f"accumulation: {analyzed.accumulation_minutes} minutes")
    print(
        f"grid: {analyzed.grid.width} x {analyzed.grid.height} "
        f"= {analyzed.grid.point_count} points"
    )
    print(f"CSV data rows: {rows}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
