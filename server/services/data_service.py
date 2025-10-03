# -*- coding: utf-8 -*-
"""
データ処理サービス
"""
from typing import List, Dict, Any, Optional, Tuple
import pandas as pd
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
        """メッシュコードから緯度経度を計算"""
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
    
    def meshcode_to_index(self, code: str) -> Tuple[int, int]:
        """メッシュコードからインデックスを計算"""
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
            
            # 座標計算をベクトル化
            coords = [self.meshcode_to_coordinate(code) for code in mesh_codes]
            indices = [self.meshcode_to_index(code) for code in mesh_codes]
            
            # dosyakei境界値を一括取得
            dosyakei_bounds = []
            for code in mesh_codes:
                if dosyakei_data is not None:
                    bound = self.get_dosyakei_bound(dosyakei_data, code)
                else:
                    bound = 999
                dosyakei_bounds.append(bound)

            # VBA X,Y座標のルックアップテーブル作成
            vba_coordinates_lookup = {}
            if vba_swi_data is not None:
                for idx, row in vba_swi_data.iterrows():
                    try:
                        area_name = str(row.iloc[0]).strip()
                        vba_x = int(row.iloc[1])
                        vba_y = int(row.iloc[2])
                        advisary = int(row.iloc[3]) if str(row.iloc[3]).strip() != '' else 9999
                        warning = int(row.iloc[4]) if str(row.iloc[4]).strip() != '' else 9999
                        dosyakei = int(row.iloc[5]) if str(row.iloc[5]).strip() != '' else 9999

                        # 一意なキーを作成（エリア名 + 境界値の組み合わせ）
                        key = f"{area_name}_{advisary}_{warning}_{dosyakei}"
                        vba_coordinates_lookup[key] = {
                            'vba_x': vba_x,
                            'vba_y': vba_y
                        }
                    except (ValueError, IndexError):
                        continue
            
            # メッシュオブジェクト一括作成
            meshes = []
            area_dict = {}
            
            for i in range(len(mesh_codes)):
                try:
                    lat, lon = coords[i]
                    x, y = indices[i]

                    # VBA X,Y座標をルックアップ
                    vba_x = None
                    vba_y = None
                    lookup_key = f"{area_names[i]}_{int(advisary_bounds[i])}_{int(warning_bounds[i])}_{dosyakei_bounds[i]}"
                    if lookup_key in vba_coordinates_lookup:
                        vba_coords = vba_coordinates_lookup[lookup_key]
                        vba_x = vba_coords['vba_x']
                        vba_y = vba_coords['vba_y']

                    mesh = Mesh(
                        area_name=area_names[i],
                        code=mesh_codes[i],
                        lat=lat,
                        lon=lon,
                        x=x,
                        y=y,
                        advisary_bound=int(advisary_bounds[i]),
                        warning_bound=int(warning_bounds[i]),
                        dosyakei_bound=dosyakei_bounds[i],
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
                    area_name = mesh.area_name
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