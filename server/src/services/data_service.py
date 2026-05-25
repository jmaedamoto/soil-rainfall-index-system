# -*- coding: utf-8 -*-
"""
データ処理サービス
"""
from typing import List, Dict, Any, Optional, Tuple
import pandas as pd
import numpy as np
import logging
import os
import time
import csv
from collections import defaultdict, OrderedDict

from models import Prefecture, Area, Mesh, SecondarySubdivision, PREFECTURES_MASTER


logger = logging.getLogger(__name__)


class DataService:
    """データ処理サービス"""

    def __init__(self, data_dir: str = "data"):
        self.data_dir = data_dir
        self.cache = {}
        self.cache_timestamp = None
        self.cache_ttl = 300  # 5分キャッシュ
        self.level4_curve_cache: Dict[str, Optional[Dict[str, Dict[str, Any]]]] = {}
        self.global_level4_curve_lookup: Optional[Dict[str, np.ndarray]] = None
        self.global_mesh_static_info_lookup: Optional[Dict[str, Dict[str, Any]]] = None

    def get_prefecture_definitions(self) -> List[Dict[str, Any]]:
        """府県定義一覧を取得する"""
        prefectures_file = os.path.join(self.data_dir, "prefectures.csv")
        fallback_definitions = [
            {
                "code": code,
                "name": name,
                "sort_order": (index + 1) * 10,
                "enabled": True,
            }
            for index, (code, name) in enumerate(PREFECTURES_MASTER.items())
        ]

        if not os.path.exists(prefectures_file):
            logger.warning(
                f"Prefecture master not found: {prefectures_file}. "
                "Falling back to built-in prefecture list."
            )
            return fallback_definitions

        definitions: List[Dict[str, Any]] = []
        try:
            with open(prefectures_file, "r", encoding="utf-8-sig", newline="") as csv_file:
                reader = csv.DictReader(csv_file)
                for row in reader:
                    code = (row.get("prefecture_code") or "").strip()
                    name = (row.get("prefecture_name") or "").strip()
                    if not code or not name:
                        logger.warning(f"Skipping prefecture row with missing code/name: {row}")
                        continue

                    sort_order_raw = (row.get("sort_order") or "").strip()
                    try:
                        sort_order = int(sort_order_raw) if sort_order_raw else 9999
                    except ValueError:
                        logger.warning(
                            f"Invalid sort_order for prefecture {code}: {sort_order_raw}. "
                            "Using fallback order."
                        )
                        sort_order = 9999

                    enabled_raw = (row.get("enabled") or "1").strip().lower()
                    enabled = enabled_raw in ("1", "true", "yes", "on")
                    if not enabled:
                        continue

                    definitions.append({
                        "code": code,
                        "name": name,
                        "sort_order": sort_order,
                        "enabled": enabled,
                    })
        except Exception as e:
            logger.error(f"Error loading prefecture master {prefectures_file}: {e}")
            return fallback_definitions

        if not definitions:
            logger.warning(
                f"No enabled prefectures found in {prefectures_file}. "
                "Falling back to built-in prefecture list."
            )
            return fallback_definitions

        definitions.sort(key=lambda item: (item["sort_order"], item["code"]))
        return definitions

    def meshcode_to_coordinate(self, code: str) -> Tuple[float, float]:
        """メッシュコードから緯度経度を計算（単一メッシュ用）"""
        try:
            if len(str(code)) >= 8:
                code_str = str(code)
                y = (int(code_str[:2]) * 80 +
                     int(code_str[4]) * 10 +
                     int(code_str[6]))
                x = (int(code_str[2:4]) * 80 +
                     int(code_str[5]) * 10 +
                     int(code_str[7]))
                lat = (y + 0.5) * 30 / 3600
                lon = (x + 0.5) * 45 / 3600 + 100
                return lat, lon
        except Exception:
            pass
        return 35.0, 135.0  # デフォルト座標

    def meshcode_to_coordinate_vectorized(self, mesh_codes: List[str]) -> List[Tuple[float, float]]:
        """メッシュコードから緯度経度を計算（ベクトル化版）"""
        coords = []
        for code in mesh_codes:
            try:
                if len(str(code)) >= 8:
                    code_str = str(code)
                    y = (int(code_str[:2]) * 80 +
                         int(code_str[4]) * 10 +
                         int(code_str[6]))
                    x = (int(code_str[2:4]) * 80 +
                         int(code_str[5]) * 10 +
                         int(code_str[7]))
                    lat = (y + 0.5) * 30 / 3600
                    lon = (x + 0.5) * 45 / 3600 + 100
                    coords.append((lat, lon))
                else:
                    coords.append((35.0, 135.0))
            except Exception:
                coords.append((35.0, 135.0))
        return coords

    def meshcode_to_index(self, code: str) -> Tuple[int, int]:
        """メッシュコードからインデックスを計算（単一メッシュ用）"""
        try:
            if len(str(code)) >= 8:
                code_str = str(code)
                y = (int(code_str[:2]) * 80 +
                     int(code_str[4]) * 10 +
                     int(code_str[6]))
                x = (int(code_str[2:4]) * 80 +
                     int(code_str[5]) * 10 +
                     int(code_str[7]))
                return x, y
        except Exception:
            pass
        return 0, 0

    def meshcode_to_index_vectorized(self, mesh_codes: List[str]) -> List[Tuple[int, int]]:
        """メッシュコードからインデックスを計算（ベクトル化版）"""
        indices = []
        for code in mesh_codes:
            try:
                if len(str(code)) >= 8:
                    code_str = str(code)
                    y = (int(code_str[:2]) * 80 +
                         int(code_str[4]) * 10 +
                         int(code_str[6]))
                    x = (int(code_str[2:4]) * 80 +
                         int(code_str[5]) * 10 +
                         int(code_str[7]))
                    indices.append((x, y))
                else:
                    indices.append((0, 0))
            except Exception:
                indices.append((0, 0))
        return indices

    def parse_boundary_value(self, value) -> int:
        """境界値をパース"""
        if (pd.isna(value) or
                str(value).strip() == "|" or
                str(value).strip() == "−" or
                str(value).strip() == ""):
            return 9999
        try:
            return int(float(str(value).strip()))
        except ValueError:
            return 9999

    def _load_level4_curve_lookup(self, prefecture_code: str) -> Optional[Dict[str, Dict[str, Any]]]:
        """2_2 CSVを読み込み、メッシュコードごとの辞書と数値配列を構築する。"""
        if prefecture_code in self.level4_curve_cache:
            return self.level4_curve_cache[prefecture_code]

        level4_file = os.path.join(self.data_dir, f"2_2_{prefecture_code}.csv")
        if not os.path.exists(level4_file):
            logger.warning(f"Level4 curve file not found: {level4_file}")
            self.level4_curve_cache[prefecture_code] = None
            return None

        try:
            level4_data = pd.read_csv(level4_file, encoding='shift_jis', header=1, dtype=str)
            mesh_column = '格子番号'
            if mesh_column not in level4_data.columns:
                raise ValueError(f"Missing required column: {mesh_column}")

            curve_columns = list(level4_data.columns[3:])
            if len(curve_columns) != 151:
                raise ValueError(
                    f"Unexpected level4 curve column count: {len(curve_columns)} "
                    f"(expected 151)"
                )

            curve_frame = (
                level4_data[curve_columns]
                .replace({'|': np.nan, '−': np.nan, '': np.nan})
                .apply(lambda column: pd.to_numeric(column, errors='coerce'))
                .fillna(999)
                .astype(np.int32)
            )

            mesh_codes = level4_data[mesh_column].astype(str).str.strip().tolist()
            lookup = {
                mesh_code: {
                    'dosyakei_bound': int(curve_values[0]) if int(curve_values[0]) < 999 else 999,
                    'level4_curve': curve_values.copy(),
                }
                for mesh_code, curve_values in zip(mesh_codes, curve_frame.to_numpy(copy=True))
            }

            self.level4_curve_cache[prefecture_code] = lookup
            logger.info(f"Loaded {level4_file}: {len(lookup)} rows")
            return lookup
        except Exception as e:
            logger.error(f"Error loading {level4_file}: {e}")
            self.level4_curve_cache[prefecture_code] = None
            return None

    def _validate_level4_join(
        self,
        prefecture_code: str,
        dosha_data: pd.DataFrame,
        level4_lookup: Optional[Dict[str, Dict[str, Any]]]
    ) -> None:
        """dosha と 2_2 の結合前提を検証する。"""
        if level4_lookup is None:
            logger.warning(f"{prefecture_code}: skip level4 join validation because 2_2 data is unavailable")
            return

        dosha_mesh_codes = dosha_data.iloc[:, 2].astype(str).str.strip()
        dosha_mesh_set = set(dosha_mesh_codes.tolist())
        level4_mesh_set = set(level4_lookup.keys())

        if len(dosha_mesh_codes) != len(level4_lookup):
            logger.warning(
                f"{prefecture_code}: dosha rows={len(dosha_mesh_codes)} "
                f"but 2_2 rows={len(level4_lookup)}"
            )

        missing_in_level4 = sorted(dosha_mesh_set - level4_mesh_set)
        extra_in_level4 = sorted(level4_mesh_set - dosha_mesh_set)

        if missing_in_level4:
            logger.warning(
                f"{prefecture_code}: missing {len(missing_in_level4)} mesh codes in 2_2 "
                f"(examples: {missing_in_level4[:5]})"
            )
        if extra_in_level4:
            logger.warning(
                f"{prefecture_code}: extra {len(extra_in_level4)} mesh codes in 2_2 "
                f"(examples: {extra_in_level4[:5]})"
            )

        missing_curve_rows = [
            mesh_code
            for mesh_code, payload in level4_lookup.items()
            if payload['level4_curve'].shape[0] != 151
        ]
        if missing_curve_rows:
            logger.warning(
                f"{prefecture_code}: invalid curve length rows detected "
                f"(examples: {missing_curve_rows[:5]})"
            )

    def _ensure_global_level4_curve_lookup(self) -> Dict[str, np.ndarray]:
        """全府県横断の mesh_code -> level4_curve lookup を初期化する。"""
        if self.global_level4_curve_lookup is not None:
            return self.global_level4_curve_lookup

        global_lookup: Dict[str, np.ndarray] = {}
        for pref in self.get_prefecture_definitions():
            pref_code = pref["code"]
            pref_lookup = self._load_level4_curve_lookup(pref_code)
            if pref_lookup is None:
                continue
            for mesh_code, payload in pref_lookup.items():
                global_lookup[mesh_code] = payload['level4_curve']

        self.global_level4_curve_lookup = global_lookup
        return global_lookup

    def get_level4_curve_by_mesh_code(self, mesh_code: str) -> Optional[np.ndarray]:
        """メッシュコードに対応するレベル4カーブを返す。"""
        lookup = self._ensure_global_level4_curve_lookup()
        curve = lookup.get(str(mesh_code).strip())
        if curve is None:
            return None
        return curve.copy()

    def get_mesh_static_info_by_mesh_code(self, mesh_code: str) -> Optional[Dict[str, Any]]:
        """メッシュコードに対応する静的メッシュ情報を返す。"""
        if self.global_mesh_static_info_lookup is None:
            self.global_mesh_static_info_lookup = {}
            prefectures = self.prepare_areas()
            for prefecture in prefectures:
                for area in prefecture.areas:
                    for mesh in area.meshes:
                        self.global_mesh_static_info_lookup[mesh.code] = {
                            "mesh_code": mesh.code,
                            "advisary_bound": mesh.advisary_bound,
                            "warning_bound": mesh.warning_bound,
                            "dosyakei_bound": mesh.dosyakei_bound,
                            "level4_curve": None if mesh.level4_curve is None else mesh.level4_curve.copy(),
                        }

        payload = self.global_mesh_static_info_lookup.get(str(mesh_code).strip())
        if payload is None:
            return None
        copied_payload = dict(payload)
        if copied_payload["level4_curve"] is not None:
            copied_payload["level4_curve"] = copied_payload["level4_curve"].copy()
        return copied_payload

    def load_csv_data(self, prefecture_code: str) -> Tuple[Optional[pd.DataFrame], Optional[Dict[str, Dict[str, Any]]], Optional[pd.DataFrame]]:
        """CSVデータ読み込み（dosha, 2_2, VBA SWI data）"""
        dosha_file = os.path.join(self.data_dir, f"dosha_{prefecture_code}.csv")
        dosha_data = None
        if os.path.exists(dosha_file):
            try:
                dosha_data = pd.read_csv(dosha_file, encoding='shift_jis', skiprows=1)
                logger.info(f"Loaded {dosha_file}: {len(dosha_data)} rows")
            except Exception as e:
                logger.error(f"Error loading {dosha_file}: {e}")

        level4_curve_lookup = self._load_level4_curve_lookup(prefecture_code)
        if dosha_data is not None:
            self._validate_level4_join(prefecture_code, dosha_data, level4_curve_lookup)

        # VBA SWI CSVファイル読み込み（VBA X,Y座標のため）
        vba_swi_file = os.path.join(self.data_dir, f"{prefecture_code}_swi.csv")
        vba_swi_data = None
        if os.path.exists(vba_swi_file):
            try:
                vba_swi_data = pd.read_csv(vba_swi_file, encoding='shift_jis', skiprows=1)
                logger.info(f"Loaded {vba_swi_file}: {len(vba_swi_data)} rows")
            except Exception as e:
                logger.error(f"Error loading {vba_swi_file}: {e}")

        return dosha_data, level4_curve_lookup, vba_swi_data

    def prepare_areas(self) -> List[Prefecture]:
        """地域データ構築（最適化版）"""
        # キャッシュチェック
        current_time = time.time()
        if (self.cache_timestamp and
            current_time - self.cache_timestamp < self.cache_ttl and
            'prefectures' in self.cache):
            logger.info("キャッシュからデータを取得")
            return self.cache['prefectures']

        logger.info("CSVファイルからデータを構築中...")
        start_time = time.time()

        # 全てのCSVデータを事前読み込み
        csv_loading_start = time.time()
        all_dosha_data = {}
        all_level4_curve_lookup = {}
        all_vba_swi_data = {}

        prefecture_definitions = self.get_prefecture_definitions()

        for pref in prefecture_definitions:
            pref_code = pref["code"]
            dosha_data, level4_curve_lookup, vba_swi_data = self.load_csv_data(pref_code)
            if dosha_data is not None:
                all_dosha_data[pref_code] = dosha_data
            if level4_curve_lookup is not None:
                all_level4_curve_lookup[pref_code] = level4_curve_lookup
            if vba_swi_data is not None:
                all_vba_swi_data[pref_code] = vba_swi_data

        csv_loading_time = time.time() - csv_loading_start
        logger.info(f"CSV読み込み時間: {csv_loading_time:.2f}秒")

        # メッシュ処理
        mesh_processing_start = time.time()
        prefectures = []

        for pref in prefecture_definitions:
            pref_code = pref["code"]
            pref_name = pref["name"]
            if pref_code not in all_dosha_data:
                logger.warning(f"Skipping {pref_code}: no dosha data")
                continue

            dosha_data = all_dosha_data[pref_code]
            level4_curve_lookup = all_level4_curve_lookup.get(pref_code)
            vba_swi_data = all_vba_swi_data.get(pref_code)

            # pandas vectorized operations を使用
            # 第1列: 二次細分名、第2列: 市町村名、第3列: メッシュコード
            subdivision_names = dosha_data.iloc[:, 0].astype(str).str.strip().values
            area_names = dosha_data.iloc[:, 1].astype(str).str.strip().values
            mesh_codes = dosha_data.iloc[:, 2].astype(str).values
            advisary_bounds = dosha_data.iloc[:, 3].apply(self.parse_boundary_value).values
            warning_bounds = dosha_data.iloc[:, 4].apply(self.parse_boundary_value).values

            # 座標計算をベクトル化（最適化: 一括処理）
            coords = self.meshcode_to_coordinate_vectorized(mesh_codes.tolist())
            indices = self.meshcode_to_index_vectorized(mesh_codes.tolist())

            if level4_curve_lookup is not None:
                level4_payloads = [level4_curve_lookup.get(str(code)) for code in mesh_codes]
                dosyakei_bounds = [
                    payload['dosyakei_bound'] if payload is not None else 999
                    for payload in level4_payloads
                ]
                level4_curves = [
                    payload['level4_curve'].copy() if payload is not None else None
                    for payload in level4_payloads
                ]
            else:
                dosyakei_bounds = [999] * len(mesh_codes)
                level4_curves = [None] * len(mesh_codes)

            # VBA X,Y座標のルックアップテーブル作成（最適化: iterrows()→ベクトル演算）
            vba_coordinates_lookup = {}
            if vba_swi_data is not None:
                try:
                    # 列をベクトル化して処理
                    area_names_vba = vba_swi_data.iloc[:, 0].astype(str).str.strip()
                    vba_x_values = pd.to_numeric(vba_swi_data.iloc[:, 1], errors='coerce').fillna(0).astype(int)
                    vba_y_values = pd.to_numeric(vba_swi_data.iloc[:, 2], errors='coerce').fillna(0).astype(int)

                    # 境界値を処理
                    def parse_vba_bound(val):
                        if pd.isna(val) or str(val).strip() == '':
                            return 9999
                        try:
                            return int(val)
                        except:
                            return 9999

                    advisary_vba = vba_swi_data.iloc[:, 3].apply(parse_vba_bound)
                    warning_vba = vba_swi_data.iloc[:, 4].apply(parse_vba_bound)
                    dosyakei_vba = vba_swi_data.iloc[:, 5].apply(parse_vba_bound)

                    # ディクショナリ構築
                    for i in range(len(vba_swi_data)):
                        key = f"{area_names_vba.iloc[i]}_{advisary_vba.iloc[i]}_{warning_vba.iloc[i]}_{dosyakei_vba.iloc[i]}"
                        vba_coordinates_lookup[key] = {
                            'vba_x': vba_x_values.iloc[i],
                            'vba_y': vba_y_values.iloc[i]
                        }
                except Exception as e:
                    logger.warning(f"VBA座標ルックアップテーブル作成エラー: {e}")

            # メッシュオブジェクト一括作成（最適化: zip使用で効率化）
            # OrderedDictを使用してCSV出現順を保持
            meshes = []
            area_dict = OrderedDict()
            subdivision_dict = OrderedDict()  # 二次細分用

            # zip()を使った効率的なイテレーション
            for code, subdivision_name, area_name, coord, idx, adv, warn, dosa, level4_curve in zip(
                mesh_codes, subdivision_names, area_names, coords, indices,
                advisary_bounds, warning_bounds, dosyakei_bounds, level4_curves
            ):
                try:
                    lat, lon = coord
                    x, y = idx

                    # VBA X,Y座標をルックアップ
                    vba_x = None
                    vba_y = None
                    lookup_key = f"{area_name}_{int(adv)}_{int(warn)}_{dosa}"
                    if lookup_key in vba_coordinates_lookup:
                        vba_coords = vba_coordinates_lookup[lookup_key]
                        vba_x = vba_coords['vba_x']
                        vba_y = vba_coords['vba_y']

                    mesh = Mesh(
                        area_name=area_name,
                        code=code,
                        lat=lat,
                        lon=lon,
                        x=x,
                        y=y,
                        advisary_bound=int(adv),
                        warning_bound=int(warn),
                        dosyakei_bound=dosa,
                        swi=[],
                        swi_hourly=[],
                        rain_1hour=[],
                        rain_1hour_max=[],
                        rain_3hour=[],
                        risk_hourly=[],
                        risk_3hour_max=[],
                        level4_curve=level4_curve,
                        vba_x=vba_x,
                        vba_y=vba_y
                    )

                    meshes.append(mesh)

                    # エリア別に分類（CSV出現順を保持）
                    if area_name not in area_dict:
                        area = Area(
                            name=area_name,
                            meshes=[],
                            secondary_subdivision_name=subdivision_name
                        )
                        area_dict[area_name] = area

                    area_dict[area_name].meshes.append(mesh)

                except Exception as e:
                    logger.warning(f"Error creating mesh: {e}")
                    continue

            # 二次細分構造を構築（CSV出現順を保持）
            for area in area_dict.values():
                subdiv_name = area.secondary_subdivision_name
                if subdiv_name not in subdivision_dict:
                    subdivision = SecondarySubdivision(name=subdiv_name)
                    subdivision_dict[subdiv_name] = subdivision

                subdivision_dict[subdiv_name].areas.append(area)

            # 座標範囲を高速計算
            area_min_x = 0
            area_max_y = 0
            if meshes:
                all_x = [mesh.x for mesh in meshes]
                all_y = [mesh.y for mesh in meshes]
                area_min_x = min(all_x)
                area_max_y = max(all_y)

            # Prefecture dataclass instance creation
            prefecture = Prefecture(
                name=pref_name,
                code=pref_code,
                areas=list(area_dict.values()),
                area_min_x=area_min_x,
                area_max_y=area_max_y,
                secondary_subdivisions=list(subdivision_dict.values())
            )

            prefectures.append(prefecture)
            logger.info(f"Prepared {pref_code}: {len(prefecture.secondary_subdivisions)} subdivisions, "
                       f"{len(prefecture.areas)} areas, {len(meshes)} meshes")

        mesh_processing_time = time.time() - mesh_processing_start
        total_time = time.time() - start_time

        total_meshes = sum(
            len(area.meshes)
            for pref in prefectures
            for area in pref.areas
        )

        logger.info(f"データ構築完了:")
        logger.info(f"  CSV読み込み時間: {csv_loading_time:.2f}秒")
        logger.info(f"  メッシュ処理時間: {mesh_processing_time:.2f}秒")
        logger.info(f"  総時間: {total_time:.2f}秒")
        logger.info(f"  総メッシュ数: {total_meshes}")
        logger.info(f"  処理速度: {total_meshes/total_time:.0f} meshes/second")

        # キャッシュに保存
        self.cache['prefectures'] = prefectures
        self.cache_timestamp = current_time

        return prefectures
