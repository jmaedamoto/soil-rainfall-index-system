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
from collections import defaultdict

from models import Prefecture, Area, Mesh, PREFECTURES_MASTER


logger = logging.getLogger(__name__)


class DataService:
    """データ処理サービス"""
    
    def __init__(self, data_dir: str = "data"):
        self.data_dir = data_dir
        self.cache = {}
        self.cache_timestamp = None
        self.cache_ttl = 300  # 5分キャッシュ
    
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
                str(value).strip() == ""):
            return 9999
        try:
            return int(float(str(value).strip()))
        except ValueError:
            return 9999
    
    def get_dosyakei_bound(self, dosyakei_data: pd.DataFrame, meshcode: str) -> int:
        """土砂災害境界値を取得"""
        try:
            # LEVEL3_00列から境界値を取得（修正済み）
            row = dosyakei_data[dosyakei_data['GRIDNO'].astype(str) == meshcode]
            if row.empty:
                return 999
            
            level_00 = row['LEVEL3_00'].iloc[0]
            if pd.isna(level_00) or level_00 >= 999:
                return 999
            
            return int(level_00)
            
        except Exception as e:
            logger.error(f"土砂災害境界値取得エラー: {meshcode} - {e}")
            return 999
    
    def load_csv_data(self, prefecture_code: str) -> Tuple[Optional[pd.DataFrame], Optional[pd.DataFrame], Optional[pd.DataFrame]]:
        """CSVデータ読み込み（dosha, dosyakei, VBA SWI data）"""
        dosha_file = os.path.join(self.data_dir, f"dosha_{prefecture_code}.csv")
        dosha_data = None
        if os.path.exists(dosha_file):
            try:
                dosha_data = pd.read_csv(dosha_file, encoding='shift_jis', skiprows=1)
                logger.info(f"Loaded {dosha_file}: {len(dosha_data)} rows")
            except Exception as e:
                logger.error(f"Error loading {dosha_file}: {e}")

        dosyakei_file = os.path.join(self.data_dir, f"dosyakei_{prefecture_code}.csv")
        dosyakei_data = None
        if os.path.exists(dosyakei_file):
            try:
                dosyakei_data = pd.read_csv(dosyakei_file, encoding='shift_jis')
                logger.info(f"Loaded {dosyakei_file}: {len(dosyakei_data)} rows")
            except Exception as e:
                logger.error(f"Error loading {dosyakei_file}: {e}")

        # VBA SWI CSVファイル読み込み（VBA X,Y座標のため）
        vba_swi_file = os.path.join(self.data_dir, f"{prefecture_code}_swi.csv")
        vba_swi_data = None
        if os.path.exists(vba_swi_file):
            try:
                vba_swi_data = pd.read_csv(vba_swi_file, encoding='shift_jis', skiprows=1)
                logger.info(f"Loaded {vba_swi_file}: {len(vba_swi_data)} rows")
            except Exception as e:
                logger.error(f"Error loading {vba_swi_file}: {e}")

        return dosha_data, dosyakei_data, vba_swi_data
    
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
        all_dosyakei_data = {}
        all_vba_swi_data = {}

        for pref_code in PREFECTURES_MASTER.keys():
            dosha_data, dosyakei_data, vba_swi_data = self.load_csv_data(pref_code)
            if dosha_data is not None:
                all_dosha_data[pref_code] = dosha_data
            if dosyakei_data is not None:
                all_dosyakei_data[pref_code] = dosyakei_data
            if vba_swi_data is not None:
                all_vba_swi_data[pref_code] = vba_swi_data
        
        csv_loading_time = time.time() - csv_loading_start
        logger.info(f"CSV読み込み時間: {csv_loading_time:.2f}秒")
        
        # メッシュ処理
        mesh_processing_start = time.time()
        prefectures = []
        
        for pref_code, pref_name in PREFECTURES_MASTER.items():
            if pref_code not in all_dosha_data:
                logger.warning(f"Skipping {pref_code}: no dosha data")
                continue
            
            dosha_data = all_dosha_data[pref_code]
            dosyakei_data = all_dosyakei_data.get(pref_code)
            vba_swi_data = all_vba_swi_data.get(pref_code)
            
            # pandas vectorized operations を使用
            mesh_codes = dosha_data.iloc[:, 2].astype(str).values
            area_names = dosha_data.iloc[:, 1].astype(str).values
            advisary_bounds = dosha_data.iloc[:, 3].apply(self.parse_boundary_value).values
            warning_bounds = dosha_data.iloc[:, 4].apply(self.parse_boundary_value).values
            
            # 座標計算をベクトル化（最適化: 一括処理）
            coords = self.meshcode_to_coordinate_vectorized(mesh_codes.tolist())
            indices = self.meshcode_to_index_vectorized(mesh_codes.tolist())
            
            # dosyakei境界値を一括取得（最適化: O(n²)→O(n)）
            if dosyakei_data is not None:
                # ディクショナリルックアップテーブル作成（pandasベクトル演算）
                dosyakei_data_filtered = dosyakei_data[['GRIDNO', 'LEVEL3_00']].copy()
                dosyakei_data_filtered['GRIDNO'] = dosyakei_data_filtered['GRIDNO'].astype(str)
                dosyakei_data_filtered['LEVEL3_00_processed'] = dosyakei_data_filtered['LEVEL3_00'].apply(
                    lambda x: 999 if (pd.isna(x) or x >= 999) else int(x)
                )
                dosyakei_lookup = dict(zip(
                    dosyakei_data_filtered['GRIDNO'],
                    dosyakei_data_filtered['LEVEL3_00_processed']
                ))

                # O(1)ルックアップで一括取得
                dosyakei_bounds = [dosyakei_lookup.get(str(code), 999) for code in mesh_codes]
            else:
                dosyakei_bounds = [999] * len(mesh_codes)

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
            meshes = []
            area_dict = {}

            # zip()を使った効率的なイテレーション
            for code, area_name, coord, idx, adv, warn, dosa in zip(
                mesh_codes, area_names, coords, indices,
                advisary_bounds, warning_bounds, dosyakei_bounds
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
                        vba_x=vba_x,
                        vba_y=vba_y
                    )

                    meshes.append(mesh)

                    # エリア別に分類
                    if area_name not in area_dict:
                        area = Area(name=area_name, meshes=[])
                        area_dict[area_name] = area
                    
                    area_dict[area_name].meshes.append(mesh)
                    
                except Exception as e:
                    logger.warning(f"Error creating mesh {i}: {e}")
                    continue
            
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
                area_max_y=area_max_y
            )
            
            prefectures.append(prefecture)
            logger.info(f"Prepared {pref_code}: {len(prefecture.areas)} areas, {len(meshes)} meshes")
        
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