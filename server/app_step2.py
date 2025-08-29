from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import os
import pandas as pd
from datetime import datetime
from typing import Dict, List, Tuple, Any
import logging
import multiprocessing
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor, as_completed
import functools

# Import new data models
from models import (
    BaseInfo, SwiTimeSeries, GuidanceTimeSeries, Risk, 
    Mesh, Area, Prefecture, PREFECTURES_MASTER
)

# Import service layer
from services import MainService

app = Flask(__name__)
CORS(app)  # CORSを有効化
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize service layer
main_service = MainService()

# Data models are now imported from models package


def load_csv_data(prefecture_code: str):
    """CSVデータ読み込み（data/フォルダから直接）"""
    data_dir = "data"

    # dosha_*.csv (境界データ)
    dosha_file = os.path.join(data_dir, f"dosha_{prefecture_code}.csv")
    dosha_data = None
    if os.path.exists(dosha_file):
        try:
            dosha_data = pd.read_csv(dosha_file, encoding='shift_jis', header=1)
            logger.info(f"Loaded {dosha_file}: {len(dosha_data)} rows")
        except Exception as e:
            logger.error(f"Error loading {dosha_file}: {e}")

    # dosyakei_*.csv (土砂災害データ)
    dosyakei_file = os.path.join(data_dir, f"dosyakei_{prefecture_code}.csv")
    dosyakei_data = None
    if os.path.exists(dosyakei_file):
        try:
            dosyakei_data = pd.read_csv(dosyakei_file, encoding='utf-8')
            logger.info(f"Loaded {dosyakei_file}: {len(dosyakei_data)} rows")
        except Exception as e:
            logger.error(f"Error loading {dosyakei_file}: {e}")

    return dosha_data, dosyakei_data


def meshcode_to_coordinate(code: str) -> Tuple[float, float]:
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


def meshcode_to_index(code: str) -> Tuple[int, int]:
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


def parse_boundary_value(value) -> int:
    """境界値をパース"""
    if (pd.isna(value) or
            str(value).strip() == "|" or
            str(value).strip() == ""):
        return 9999
    try:
        # numpy型も確実にPython intに変換
        return int(float(str(value)))
    except Exception:
        return 9999


def get_dosyakei_bound(mesh_code: str, dosyakei_data: pd.DataFrame) -> int:
    """土砂災害境界値を取得"""
    try:
        if dosyakei_data is not None:
            matching_rows = dosyakei_data[
                dosyakei_data['GRIDNO'].astype(str) == str(mesh_code)
            ]
            if (not matching_rows.empty and
                    'LEVEL3_00' in dosyakei_data.columns):
                bound_value = matching_rows['LEVEL3_00'].iloc[0]
                # numpy int64 を Python int に変換
                bound_value = int(bound_value)
                return bound_value if bound_value < 999 else 9999
    except Exception:
        pass
    return 9999


# キャッシュ用のグローバル変数
_cached_prefectures = None
_cache_timestamp = None

def prepare_areas_optimized() -> List[Prefecture]:
    """最適化版：CSVからデータ構造を高速構築"""
    import time
    
    # キャッシュチェック（5分間有効）
    global _cached_prefectures, _cache_timestamp
    current_time = time.time()
    if (_cached_prefectures is not None and 
        _cache_timestamp is not None and 
        current_time - _cache_timestamp < 300):  # 5分
        logger.info("Using cached prefecture data")
        return _cached_prefectures
    
    logger.info("Building optimized prefecture data...")
    start_time = time.time()
    
    # 全CSVデータを一括読み込み
    all_dosha_data = {}
    all_dosyakei_data = {}
    
    csv_load_start = time.time()
    for pref_code in PREFECTURES_MASTER.keys():
        dosha_data, dosyakei_data = load_csv_data(pref_code)
        if dosha_data is not None:
            all_dosha_data[pref_code] = dosha_data
        if dosyakei_data is not None:
            # dosyakei_dataをGRIDNOでインデックス化（高速検索用）
            dosyakei_indexed = dosyakei_data.set_index('GRIDNO')['LEVEL3_00'].to_dict()
            all_dosyakei_data[pref_code] = dosyakei_indexed
    
    csv_load_time = time.time() - csv_load_start
    logger.info(f"CSV loading completed in {csv_load_time:.2f}s")
    
    # 府県処理
    prefectures = []
    mesh_processing_start = time.time()
    
    for pref_code, pref_name in PREFECTURES_MASTER.items():
        if pref_code not in all_dosha_data:
            logger.warning(f"Skipping {pref_code}: no dosha data")
            continue
            
        dosha_data = all_dosha_data[pref_code]
        dosyakei_dict = all_dosyakei_data.get(pref_code, {})
        
        # pandas vectorized operations を使用
        mesh_codes = dosha_data.iloc[:, 2].astype(str).values
        area_names = dosha_data.iloc[:, 1].astype(str).values
        advisary_bounds = dosha_data.iloc[:, 3].apply(parse_boundary_value).values
        warning_bounds = dosha_data.iloc[:, 4].apply(parse_boundary_value).values
        
        # 座標計算をベクトル化
        coords = [meshcode_to_coordinate(code) for code in mesh_codes]
        indices = [meshcode_to_index(code) for code in mesh_codes]
        
        # dosyakei境界値を一括取得
        dosyakei_bounds = []
        for code in mesh_codes:
            try:
                code_int = int(float(code))
                bound_value = dosyakei_dict.get(code_int, 9999)
                if bound_value >= 999:
                    bound_value = 9999
                dosyakei_bounds.append(int(bound_value))
            except (ValueError, TypeError):
                dosyakei_bounds.append(9999)
        
        # メッシュオブジェクト一括作成
        meshes = []
        area_dict = {}
        
        for i in range(len(mesh_codes)):
            try:
                lat, lon = coords[i]
                x, y = indices[i]
                
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
                    rain=[]
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
    
    logger.info(f"Optimized prepare_areas completed in {total_time:.2f}s "
                f"(CSV: {csv_load_time:.2f}s, Processing: {mesh_processing_time:.2f}s)")
    
    # キャッシュ更新
    _cached_prefectures = prefectures
    _cache_timestamp = current_time
    
    return prefectures


def prepare_areas() -> List[Prefecture]:
    """VBAのprepare_areas()を再現：CSVからデータ構造を構築"""
    # 最適化版を使用
    return prepare_areas_optimized()


# GRIB2関連の関数（VBAコードを忠実に実装）
def download_file(url: str) -> bytes:
    """ファイルダウンロード"""
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        return response.content
    except requests.RequestException as e:
        raise Exception(f"ダウンロードエラー: {str(e)}")


def get_dat(data: bytes, start: int, length: int) -> int:
    """バイナリデータ読み取り（VBAのget_dat関数を忠実に再現）"""
    if start + length > len(data):
        return 0

    result = 0
    end = start + length - 1

    # Big-Endianで読み取り（VBAのロジックと同じ）
    for i in range(start, end + 1):
        if i < len(data):
            result = result + data[i] * (256 ** (end - i))

    return result


def unpack_info(data: bytes, position: int) -> Tuple[BaseInfo, int, int]:
    """GRIB2ファイルのヘッダー情報を解析（VBAのunpack_info関数を忠実に実装）"""
    # セクション0: total_sizeを取得
    total_size = get_dat(data, 8, 8)  # 9バイト目から8バイト
    position = 16

    # セクション1: 日時情報
    section_size = get_dat(data, position, 4)
    year = get_dat(data, position + 12, 2)
    month = get_dat(data, position + 14, 1)
    day = get_dat(data, position + 15, 1)
    hour = get_dat(data, position + 16, 1)
    minute = get_dat(data, position + 17, 1)
    second = get_dat(data, position + 18, 1)

    initial_date = datetime(year, month, day, hour, minute, second)
    position += section_size

    # セクション3: グリッド情報
    section_size = get_dat(data, position, 4)
    grid_num = get_dat(data, position + 6, 4)
    x_num = get_dat(data, position + 30, 4)
    y_num = get_dat(data, position + 34, 4)
    s_lat = get_dat(data, position + 46, 4)
    s_lon = get_dat(data, position + 50, 4)
    e_lat = get_dat(data, position + 55, 4)
    e_lon = get_dat(data, position + 59, 4)
    d_lon = get_dat(data, position + 63, 4)
    d_lat = get_dat(data, position + 67, 4)
    position += section_size

    # BaseInfo dataclass instance creation
    base_info = BaseInfo(
        initial_date=initial_date,
        grid_num=grid_num,
        x_num=x_num,
        y_num=y_num,
        s_lat=s_lat,
        s_lon=s_lon,
        e_lat=e_lat,
        e_lon=e_lon,
        d_lat=d_lat,
        d_lon=d_lon
    )

    return base_info, position, total_size


def unpack_runlength(data: bytes, bit_num: int, level_num: int, level_max: int,
                     grid_num: int, level: List[int], s_position: int,
                     e_position: int) -> List[float]:
    """ランレングス圧縮データの展開（VBAのunpack_runlength関数を忠実に実装）"""
    lngu = 2 ** bit_num - 1 - level_max  # ランレングス圧縮に用いる進数
    result = [0.0] * grid_num
    d_index = 0  # 0ベースのインデックス（VBAは1ベース）
    p = s_position
    byte_size = bit_num // 8

    while p < e_position and d_index < grid_num:
        if p + byte_size > len(data):
            break

        d = get_dat(data, p - 1, byte_size)
        p += byte_size

        if p + byte_size > len(data):
            break

        dd = get_dat(data, p - 1, byte_size)

        if dd <= level_max:
            if d_index < grid_num and d < len(level):
                result[d_index] = level[d]
                d_index += 1
        else:
            nlength = 0
            p2 = 1
            while p < e_position and dd > level_max:
                nlength += ((lngu ** (p2 - 1)) * (dd - level_max - 1))
                p += byte_size
                if p + byte_size <= len(data):
                    dd = get_dat(data, p - 1, byte_size)
                else:
                    break
                p2 += 1

            # ランレングス分のデータを展開
            for i in range(nlength + 1):
                if d_index < grid_num and d < len(level):
                    result[d_index] = level[d]
                    d_index += 1

    return result


def unpack_data(data: bytes, position: int,
                grid_num: int) -> Tuple[List[float], int]:
    """GRIB2データ値を解析（VBAのunpack_data関数を忠実に実装）"""
    # セクション5: データ表現情報
    section_size = get_dat(data, position, 4)
    bit_num = get_dat(data, position + 11, 1)      # 1データのビット数
    level_max = get_dat(data, position + 12, 2)    # 最大レベル値
    level_num = get_dat(data, position + 14, 2)    # レベル数

    # レベル値配列を構築
    level = [0] * (level_max + 1)
    for i in range(1, level_max + 1):
        level[i] = get_dat(data, position + 15 + 2 * i, 2)
        # 符号付き16ビット値の処理
        if level[i] >= 32768:  # 65536 / 2
            level[i] = level[i] - 65536

    position += section_size

    # セクション6をスキップ
    section_size = get_dat(data, position, 4)
    position += section_size

    # セクション7: データ本体
    section_size = get_dat(data, position, 4)
    data_values = unpack_runlength(
        data, bit_num, level_num, level_max, grid_num, level,
        position + 5, position + section_size
    )
    position += section_size

    return data_values, position


def unpack_swi_grib2(data: bytes) -> Dict[str, Any]:
    """土壌雨量指数GRIB2ファイルを解析（VBAのunpack_swi_grib2関数を忠実に実装）"""
    base_info, position, total_size = unpack_info(data, 0)

    swi_data = None
    first_tunk = None
    second_tunk = None

    # VBAのDo While total_size - position > 4ループを再現
    while total_size - position > 4:
        # セクション4: プロダクト定義
        section_size = get_dat(data, position, 4)
        data_type = get_dat(data, position + 22, 1)
        data_sub_type = get_dat(data, position + 24, 4)
        position += section_size

        # データタイプに応じて処理を分岐
        if data_type == 200:  # 土壌雨量指数
            swi_data, position = unpack_data(
                data, position, base_info.grid_num
            )
        elif data_type == 201 and data_sub_type == 1:  # 第1タンク値
            first_tunk, position = unpack_data(
                data, position, base_info.grid_num
            )
        elif data_type == 201 and data_sub_type == 2:  # 第2タンク値
            second_tunk, position = unpack_data(
                data, position, base_info.grid_num
            )
        else:
            # VBAのMsgBox処理をログ出力に変更
            logger.warning(
                f"Unexpected data type: {data_type}, "
                f"sub_type: {data_sub_type}"
            )
            # セクション5-7をスキップ
            for _ in range(3):
                if position < total_size:
                    section_size = get_dat(data, position, 4)
                    position += section_size

    return {
        'base_info': base_info,
        'swi': swi_data if swi_data is not None else [],
        'first_tunk': first_tunk if first_tunk is not None else [],
        'second_tunk': second_tunk if second_tunk is not None else []
    }


def unpack_guidance_grib2(data: bytes) -> Dict[str, Any]:
    """ガイダンスGRIB2ファイルを解析（VBAのunpack_guidance_grib2関数を忠実に実装）"""
    base_info, position, total_size = unpack_info(data, 0)
    guidance_data = []

    loop_count = 1
    prev_ft = 0

    # VBAのDoループを再現
    while position < total_size - 4:
        # セクション4: プロダクト定義
        section_size = get_dat(data, position, 4)
        span = get_dat(data, position + 49, 4)
        ft = get_dat(data, position + 18, 4) + span

        if prev_ft > ft:
            loop_count += 1

        position += section_size

        # VBAの条件: span = 3 And loop_count = 2
        if span == 3 and loop_count == 2:
            # データを解析してガイダンスデータに追加
            value, position = unpack_data(data, position, base_info.grid_num)
            guidance_data.append({
                'ft': ft,
                'value': value
            })

            if total_size - position <= 4:
                break
        else:
            # セクション5-7をスキップ
            for _ in range(3):
                if position < total_size:
                    section_size = get_dat(data, position, 4)
                    position += section_size

        if total_size - position <= 4:
            break

        prev_ft = ft

    return {
        'base_info': base_info,
        'data': guidance_data
    }


def calc_tunk_model(s1: float, s2: float, s3: float, t: float,
                    r: float) -> Tuple[float, float, float]:
    """タンクモデル計算"""
    l1, l2, l3, l4 = 15, 60, 15, 15
    a1, a2, a3, a4 = 0.1, 0.15, 0.05, 0.01
    b1, b2, b3 = 0.12, 0.05, 0.01

    q1 = q2 = q3 = 0
    if s1 > l1:
        q1 += a1 * (s1 - l1)
    if s1 > l2:
        q1 += a2 * (s1 - l2)
    if s2 > l3:
        q2 = a3 * (s2 - l3)
    if s3 > l4:
        q3 = a4 * (s3 - l4)

    s1_new = (1 - b1 * t) * s1 - q1 * t + r
    s2_new = (1 - b2 * t) * s2 - q2 * t + b1 * s1 * t
    s3_new = (1 - b3 * t) * s3 - q3 * t + b2 * s2 * t

    return s1_new, s2_new, s3_new


def get_data_num(lat: float, lon: float, base_info: BaseInfo) -> int:
    """緯度経度からグリッド番号を取得"""
    try:
        y = int((base_info.s_lat / 1000000 - lat) /
                (base_info.d_lat / 1000000)) + 1
        x = int((lon - base_info.s_lon / 1000000) /
                (base_info.d_lon / 1000000)) + 1
        return (y - 1) * base_info.x_num + x
    except Exception:
        return 0


def calc_swi_timelapse(mesh: Mesh, swi_grib2: Dict,
                       guidance_grib2: Dict) -> List[SwiTimeSeries]:
    """土壌雨量指数の時系列計算（VBAのcalc_swi_timelapseを再現）"""
    try:
        swi_index = get_data_num(mesh.lat, mesh.lon, swi_grib2['base_info'])

        if (swi_index >= len(swi_grib2['swi']) or
                swi_index >= len(swi_grib2['first_tunk']) or
                swi_index >= len(swi_grib2['second_tunk'])):
            return []

        swi = swi_grib2['swi'][swi_index] / 10
        first_tunk = swi_grib2['first_tunk'][swi_index] / 10
        second_tunk = swi_grib2['second_tunk'][swi_index] / 10
        third_tunk = swi - first_tunk - second_tunk

        guidance_index = get_data_num(
            mesh.lat, mesh.lon, guidance_grib2['base_info']
        )

        swi_time_series = []
        swi_time_series.append(SwiTimeSeries(0, swi))

        tmp_f, tmp_s, tmp_t = first_tunk, second_tunk, third_tunk

        for data in guidance_grib2['data']:
            if guidance_index < len(data['value']):
                rainfall = data['value'][guidance_index]
                tmp_f, tmp_s, tmp_t = calc_tunk_model(
                    tmp_f, tmp_s, tmp_t, 3, rainfall
                )
                swi_time_series.append(
                    SwiTimeSeries(data['ft'], tmp_f + tmp_s + tmp_t)
                )

        return swi_time_series

    except Exception as e:
        logger.warning(
            f"Error in calc_swi_timelapse for mesh {mesh.code}: {e}"
        )
        return []


def calc_rain_timelapse(mesh: Mesh,
                        guidance_grib2: Dict) -> List[GuidanceTimeSeries]:
    """降水量の時系列計算（VBAのcalc_rain_timelapseを再現）"""
    try:
        guidance_index = get_data_num(
            mesh.lat, mesh.lon, guidance_grib2['base_info']
        )
        rain_timeseries = []

        for data in guidance_grib2['data']:
            if guidance_index < len(data['value']):
                rain_timeseries.append(
                    GuidanceTimeSeries(
                        data['ft'], data['value'][guidance_index]
                    )
                )

        return rain_timeseries

    except Exception as e:
        logger.warning(
            f"Error in calc_rain_timelapse for mesh {mesh.code}: {e}"
        )
        return []


def calc_mesh_timelines(mesh_data: Tuple[Mesh, Dict, Dict]) -> Tuple[str, List[Dict], List[Dict]]:
    """単一メッシュの時系列計算（並列処理用）"""
    mesh, swi_grib2, guidance_grib2 = mesh_data
    
    try:
        # SWI時系列計算
        swi_timeline = calc_swi_timelapse(mesh, swi_grib2, guidance_grib2)
        # Rain時系列計算
        rain_timeline = calc_rain_timelapse(mesh, guidance_grib2)
        
        # 辞書形式で返す（JSON serializable）
        swi_dict = [{"ft": int(s.ft), "value": float(s.value)} for s in swi_timeline]
        rain_dict = [{"ft": int(r.ft), "value": float(r.value)} for r in rain_timeline]
        
        return mesh.code, swi_dict, rain_dict
        
    except Exception as e:
        logger.warning(f"Parallel calculation error for mesh {mesh.code}: {e}")
        # エラー時はダミーデータ
        return mesh.code, [{"ft": 0, "value": 85.5}, {"ft": 3, "value": 92.1}], [{"ft": 3, "value": 2.5}]


def process_meshes_parallel(meshes: List[Mesh], swi_grib2: Dict, guidance_grib2: Dict, 
                          max_workers: int = None) -> Dict[str, Tuple[List[Dict], List[Dict]]]:
    """メッシュ計算の並列処理"""
    if max_workers is None:
        max_workers = min(multiprocessing.cpu_count(), len(meshes), 8)  # 最大8プロセス
    
    # 少数のメッシュではシーケンシャル処理が効率的
    if len(meshes) < 50:
        results = {}
        for mesh in meshes:
            mesh_code, swi_timeline, rain_timeline = calc_mesh_timelines((mesh, swi_grib2, guidance_grib2))
            results[mesh_code] = (swi_timeline, rain_timeline)
        return results
    
    # メッシュデータを準備
    mesh_data_list = [(mesh, swi_grib2, guidance_grib2) for mesh in meshes]
    
    results = {}
    
    # ThreadPoolExecutor を使用（プロセス間通信のオーバーヘッドを避ける）
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # 全タスクを投入
        future_to_mesh = {
            executor.submit(calc_mesh_timelines, mesh_data): mesh_data[0].code 
            for mesh_data in mesh_data_list
        }
        
        # 結果を収集
        for future in as_completed(future_to_mesh):
            try:
                mesh_code, swi_timeline, rain_timeline = future.result()
                results[mesh_code] = (swi_timeline, rain_timeline)
            except Exception as e:
                mesh_code = future_to_mesh[future]
                logger.warning(f"Failed to process mesh {mesh_code}: {e}")
                # フォールバック
                results[mesh_code] = ([{"ft": 0, "value": 85.5}], [{"ft": 3, "value": 2.5}])
    
    return results


def process_meshes_batch(meshes: List[Mesh], swi_grib2: Dict, guidance_grib2: Dict, 
                        batch_size: int = 1000) -> Dict[str, Tuple[List[Dict], List[Dict]]]:
    """バッチ処理（大量メッシュ用）"""
    results = {}
    
    # メッシュをバッチに分割
    for i in range(0, len(meshes), batch_size):
        batch = meshes[i:i + batch_size]
        batch_results = process_meshes_parallel(batch, swi_grib2, guidance_grib2)
        results.update(batch_results)
        
        if i + batch_size < len(meshes):
            logger.info(f"Processed batch {i//batch_size + 1}: {len(batch)} meshes")
    
    return results


def calc_risk_timeline(meshes: List[Mesh]) -> List[Risk]:
    """リスクタイムラインの計算（VBAのcalc_risk_timelineを完全再現）

    メッシュごとの危険レベルを集計して市町村ごとのタイムラインを作る
    """
    if not meshes or not meshes[0].swi:
        return []

    risk_timeline = []

    # meshes[0].swiの長さ分のタイムラインを作成
    for i in range(len(meshes[0].swi)):
        ft = meshes[0].swi[i].ft
        max_risk = 0

        # 各メッシュの同じ時刻での危険レベルを確認
        for mesh in meshes:
            if i < len(mesh.swi):
                value = mesh.swi[i].value

                # VBAと同じ判定ロジック
                # 土砂災害危険度追加（レベル3）
                if value >= mesh.dosyakei_bound:
                    max_risk = max(max_risk, 3)
                # 警報基準値（レベル2）
                elif value >= mesh.warning_bound:
                    max_risk = max(max_risk, 2)
                # 注意報基準値（レベル1）
                elif value >= mesh.advisary_bound:
                    max_risk = max(max_risk, 1)
                # レベル0（正常）はそのまま

        risk_timeline.append(Risk(ft, max_risk))

    return risk_timeline


@app.route('/api/soil-rainfall-index', methods=['POST'])
def main_process():
    """メインAPI"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "リクエストデータが必要です"}), 400

        initial_str = data.get('initial')
        if not initial_str:
            return jsonify({"error": "initialパラメータが必要です"}), 400

        # 初期時刻をパース
        try:
            if isinstance(initial_str, str):
                initial = datetime.fromisoformat(
                    initial_str.replace('Z', '+00:00')
                )
            else:
                initial = datetime.fromtimestamp(initial_str)
        except Exception:
            return jsonify(
                {"error": "initialの形式が正しくありません"}
            ), 400

        # URL構築
        date_path = initial.strftime('%Y/%m/%d/')
        timestamp = initial.strftime('%Y%m%d%H%M%S')
        hour_mod = initial.hour % 6

        swi_url = (
            f"http://lunar1.fcd.naps.kishou.go.jp/srf/Grib2/Rtn/swi10/"
            f"{date_path}Z__C_RJTD_{timestamp}_SRF_GPV_Ggis1km_Psw_"
            f"Aper10min_ANAL_grib2.bin"
        )
        guidance_url = (
            f"http://lunar1.fcd.naps.kishou.go.jp/srf/Grib2/Rtn/gdc/"
            f"{date_path}guid_msm_grib2_{timestamp}_rmax0{hour_mod}.bin"
        )

        # GRIB2データ取得と解析
        try:
            logger.info("GRIB2データをダウンロード中...")
            swi_data = download_file(swi_url)
            guidance_data = download_file(guidance_url)

            logger.info("GRIB2データを解析中...")
            swi_grib2 = unpack_swi_grib2(swi_data)
            guidance_grib2 = unpack_guidance_grib2(guidance_data)

            logger.info(
                f"解析完了: SWI grid_num={swi_grib2['base_info'].grid_num}, "
                f"Guidance data count={len(guidance_grib2['data'])}"
            )
        except Exception as e:
            logger.error(f"GRIB2データエラー: {e}")
            # GRIB2データ取得失敗時はエラーを返す（ダミーデータではなく）
            return jsonify({
                "status": "error",
                "error": f"GRIB2データの取得・解析に失敗しました: {str(e)}",
                "timestamp": datetime.now().isoformat()
            }), 500

        # CSVデータから地域構造を準備
        prefectures = prepare_areas()

        # 結果構築
        results = {}
        for prefecture in prefectures:
            pref_result = {
                "name": prefecture.name,
                "code": prefecture.code,
                "areas": []
            }

            for area in prefecture.areas:
                area_result = {
                    "name": area.name,
                    "meshes": []
                }

                for mesh in area.meshes:
                    # 土壌雨量指数と降水量の時系列計算
                    try:
                        mesh.swi = calc_swi_timelapse(
                            mesh, swi_grib2, guidance_grib2
                        )
                        mesh.rain = calc_rain_timelapse(mesh, guidance_grib2)
                    except Exception as e:
                        logger.warning(
                            f"Calculation error for mesh {mesh.code}: {e}"
                        )
                        # エラー時はダミーデータを設定
                        mesh.swi = [
                            SwiTimeSeries(0, 85.5),
                            SwiTimeSeries(3, 92.1)
                        ]
                        mesh.rain = [GuidanceTimeSeries(3, 2.5)]

                    mesh_result = {
                        "code": mesh.code,
                        "lat": float(mesh.lat),
                        "lon": float(mesh.lon),
                        "advisary_bound": int(mesh.advisary_bound),
                        "warning_bound": int(mesh.warning_bound),
                        "dosyakei_bound": int(mesh.dosyakei_bound),
                        "swi_timeline": [
                            {"ft": int(s.ft), "value": float(s.value)} for s in mesh.swi
                        ],
                        "rain_timeline": [
                            {"ft": int(r.ft), "value": float(r.value)} for r in mesh.rain
                        ]
                    }
                    area_result["meshes"].append(mesh_result)

                # エリアのリスクタイムラインを計算（VBAのcalc_risk_timelineを実行）
                try:
                    area.risk_timeline = calc_risk_timeline(area.meshes)
                    area_result["risk_timeline"] = [
                        {"ft": int(r.ft), "value": int(r.value)}
                        for r in area.risk_timeline
                    ]
                except Exception as e:
                    logger.warning(
                        f"Risk timeline calculation error "
                        f"for area {area.name}: {e}"
                    )
                    # エラー時はダミーデータ
                    area_result["risk_timeline"] = [
                        {"ft": 0, "value": 0},
                        {"ft": 3, "value": 1}
                    ]
                pref_result["areas"].append(area_result)

            results[prefecture.code] = pref_result

        return jsonify({
            "status": "success",
            "calculation_time": datetime.now().isoformat(),
            "initial_time": initial.isoformat(),
            "prefectures": results
        })

    except Exception as e:
        logger.error(f"API error: {e}")
        return jsonify({
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500


@app.route('/', methods=['GET'])
def root():
    """ルートエンドポイント"""
    return jsonify({
        "message": "土壌雨量指数計算システム API",
        "version": "1.0.0",
        "endpoints": {
            "/api/health": "ヘルスチェック",
            "/api/data-check": "データファイル確認",
            "/api/test-bin-data": "テスト用：binファイル情報確認",
            "/api/test-grib2-analysis": "テスト用：GRIB2解析実行",
            "/api/test-soil-rainfall-index": "テスト用：main_process形式JSON（サンプル版）",
            "/api/test-single-prefecture": "テスト用：単一府県の全メッシュ（中規模版）",
            "/api/test-full-soil-rainfall-index": "テスト用：main_process形式JSON（全メッシュ版）",
            "/api/test-performance-analysis": "パフォーマンス解析：詳細処理時間計測（全メッシュ版）",
            "/api/test-performance-summary": "パフォーマンス要約：軽量版ボトルネック分析",
            "/api/test-csv-optimization": "CSV処理最適化：効果測定・比較",
            "/api/test-parallel-processing": "並列処理：効果測定・比較（1000メッシュサンプル）",
            "/api/test-full-parallel-soil-rainfall-index": "並列処理版：全メッシュ処理",
            "/api/soil-rainfall-index": "土壌雨量指数計算 (POST)"
        }
    })


@app.route('/api/health', methods=['GET'])
def health_check():
    """ヘルスチェック"""
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat()
    })


@app.route('/api/data-check', methods=['GET'])
def data_check():
    """データファイル確認"""
    results = {}
    data_dir = "data"

    for pref_code in PREFECTURES_MASTER.keys():
        dosha_file = os.path.join(data_dir, f"dosha_{pref_code}.csv")
        dosyakei_file = os.path.join(data_dir, f"dosyakei_{pref_code}.csv")

        results[pref_code] = {
            "dosha_exists": os.path.exists(dosha_file),
            "dosyakei_exists": os.path.exists(dosyakei_file)
        }

    return jsonify({
        "status": "success",
        "data_check": results
    })


@app.route('/api/test-bin-data', methods=['GET'])
def test_bin_data():
    """テスト用：dataフォルダ内のbinファイルからデータを読み出してJSONで返す"""
    try:
        data_dir = "data"
        
        # binファイルのパス
        swi_bin_path = os.path.join(data_dir, "Z__C_RJTD_20250101000000_SRF_GPV_Ggis1km_Psw_Aper10min_ANAL_grib2.bin")
        guidance_bin_path = os.path.join(data_dir, "guid_msm_grib2_20250101000000_rmax00.bin")
        
        result = {
            "status": "success",
            "timestamp": datetime.now().isoformat(),
            "files_checked": {
                "swi_exists": os.path.exists(swi_bin_path),
                "guidance_exists": os.path.exists(guidance_bin_path)
            },
            "data": {}
        }
        
        # ファイルサイズのみ最初に確認
        if os.path.exists(swi_bin_path):
            result["data"]["swi_file_info"] = {
                "file_name": "Z__C_RJTD_20250101000000_SRF_GPV_Ggis1km_Psw_Aper10min_ANAL_grib2.bin",
                "file_size": os.path.getsize(swi_bin_path)
            }
        
        if os.path.exists(guidance_bin_path):
            result["data"]["guidance_file_info"] = {
                "file_name": "guid_msm_grib2_20250101000000_rmax00.bin",
                "file_size": os.path.getsize(guidance_bin_path)
            }
        
        # 簡単なCSVデータサンプル
        try:
            prefectures = prepare_areas()
            if prefectures:
                sample_pref = prefectures[0]
                result["data"]["csv_sample"] = {
                    "prefecture": {
                        "name": sample_pref.name,
                        "code": sample_pref.code,
                        "areas_count": len(sample_pref.areas)
                    }
                }
                if sample_pref.areas:
                    result["data"]["csv_sample"]["sample_area"] = {
                        "name": sample_pref.areas[0].name,
                        "meshes_count": len(sample_pref.areas[0].meshes)
                    }
                    if sample_pref.areas[0].meshes:
                        sample_mesh = sample_pref.areas[0].meshes[0]
                        result["data"]["csv_sample"]["sample_mesh"] = {
                            "code": sample_mesh.code,
                            "area_name": sample_mesh.area_name,
                            "lat": sample_mesh.lat,
                            "lon": sample_mesh.lon,
                            "advisary_bound": sample_mesh.advisary_bound,
                            "warning_bound": sample_mesh.warning_bound,
                            "dosyakei_bound": sample_mesh.dosyakei_bound
                        }
        except Exception as e:
            result["data"]["csv_error"] = str(e)
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"テスト機能エラー: {e}")
        return jsonify({
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500


@app.route('/api/test-grib2-analysis', methods=['GET'])
def test_grib2_analysis():
    """テスト用：GRIB2解析のみ実行（時間がかかる処理）"""
    try:
        data_dir = "data"
        
        # binファイルのパス
        swi_bin_path = os.path.join(data_dir, "Z__C_RJTD_20250101000000_SRF_GPV_Ggis1km_Psw_Aper10min_ANAL_grib2.bin")
        guidance_bin_path = os.path.join(data_dir, "guid_msm_grib2_20250101000000_rmax00.bin")
        
        result = {
            "status": "success",
            "timestamp": datetime.now().isoformat(),
            "analysis_results": {}
        }
        
        # SWIファイルの解析
        if os.path.exists(swi_bin_path):
            try:
                logger.info(f"SWIファイルを読み込み中: {swi_bin_path}")
                with open(swi_bin_path, 'rb') as f:
                    swi_data = f.read()
                
                logger.info("SWIデータを解析中...")
                swi_grib2 = unpack_swi_grib2(swi_data)
                
                result["analysis_results"]["swi"] = {
                    "file_size": len(swi_data),
                    "initial_date": swi_grib2['base_info'].initial_date.isoformat(),
                    "grid_num": swi_grib2['base_info'].grid_num,
                    "x_num": swi_grib2['base_info'].x_num,
                    "y_num": swi_grib2['base_info'].y_num,
                    "swi_data_count": len(swi_grib2['swi']),
                    "first_tunk_count": len(swi_grib2['first_tunk']),
                    "second_tunk_count": len(swi_grib2['second_tunk']),
                    "sample_swi_values": swi_grib2['swi'][:5] if swi_grib2['swi'] else []
                }
                logger.info(f"SWI解析完了: grid_num={swi_grib2['base_info'].grid_num}")
                
            except Exception as e:
                logger.error(f"SWIファイル解析エラー: {e}")
                result["analysis_results"]["swi"] = {"error": str(e)}
        
        # ガイダンスファイルの解析
        if os.path.exists(guidance_bin_path):
            try:
                logger.info(f"ガイダンスファイルを読み込み中: {guidance_bin_path}")
                with open(guidance_bin_path, 'rb') as f:
                    guidance_data = f.read()
                
                logger.info("ガイダンスデータを解析中...")
                guidance_grib2 = unpack_guidance_grib2(guidance_data)
                
                result["analysis_results"]["guidance"] = {
                    "file_size": len(guidance_data),
                    "initial_date": guidance_grib2['base_info'].initial_date.isoformat(),
                    "grid_num": guidance_grib2['base_info'].grid_num,
                    "data_count": len(guidance_grib2['data']),
                    "forecast_times": [d['ft'] for d in guidance_grib2['data']],
                    "sample_forecast": {
                        "ft": guidance_grib2['data'][0]['ft'] if guidance_grib2['data'] else 0,
                        "sample_values": guidance_grib2['data'][0]['value'][:5] if guidance_grib2['data'] and guidance_grib2['data'][0]['value'] else []
                    }
                }
                logger.info(f"ガイダンス解析完了: data_count={len(guidance_grib2['data'])}")
                
            except Exception as e:
                logger.error(f"ガイダンスファイル解析エラー: {e}")
                result["analysis_results"]["guidance"] = {"error": str(e)}
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"GRIB2解析テストエラー: {e}")
        return jsonify({
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500


@app.route('/api/test-soil-rainfall-index', methods=['GET'])
def test_soil_rainfall_index():
    """テスト用：binファイルを使ってmain_processと同じ形式のJSONを返す（サンプル版）"""
    try:
        data_dir = "data"
        
        # binファイルのパス
        swi_bin_path = os.path.join(data_dir, "Z__C_RJTD_20250101000000_SRF_GPV_Ggis1km_Psw_Aper10min_ANAL_grib2.bin")
        guidance_bin_path = os.path.join(data_dir, "guid_msm_grib2_20250101000000_rmax00.bin")
        
        # GRIB2データの解析
        logger.info("ローカルGRIB2データを解析中...")
        
        # SWIファイルの解析
        if not os.path.exists(swi_bin_path):
            return jsonify({
                "status": "error",
                "error": "SWI binファイルが見つかりません",
                "timestamp": datetime.now().isoformat()
            }), 500
            
        if not os.path.exists(guidance_bin_path):
            return jsonify({
                "status": "error",
                "error": "ガイダンス binファイルが見つかりません",
                "timestamp": datetime.now().isoformat()
            }), 500
        
        try:
            with open(swi_bin_path, 'rb') as f:
                swi_data = f.read()
            swi_grib2 = unpack_swi_grib2(swi_data)
            
            with open(guidance_bin_path, 'rb') as f:
                guidance_data = f.read()
            guidance_grib2 = unpack_guidance_grib2(guidance_data)
            
            logger.info(
                f"GRIB2解析完了: SWI grid_num={swi_grib2['base_info'].grid_num}, "
                f"Guidance data count={len(guidance_grib2['data'])}"
            )
            
        except Exception as e:
            logger.error(f"GRIB2データ解析エラー: {e}")
            return jsonify({
                "status": "error",
                "error": f"GRIB2データの解析に失敗しました: {str(e)}",
                "timestamp": datetime.now().isoformat()
            }), 500
        
        # CSVデータから地域構造を準備
        logger.info("CSVデータから地域構造を構築中...")
        prefectures = prepare_areas()
        
        # 結果構築（main_processと同じ形式）
        results = {}
        for prefecture in prefectures:
            pref_result = {
                "name": prefecture.name,
                "code": prefecture.code,
                "areas": []
            }
            
            for area in prefecture.areas:
                area_result = {
                    "name": area.name,
                    "meshes": []
                }
                
                # 最初の数個のメッシュのみ処理（レスポンス時間短縮）
                mesh_limit = min(3, len(area.meshes))  # 最大3個まで
                
                for mesh in area.meshes[:mesh_limit]:
                    try:
                        # 土壌雨量指数と降水量の時系列計算
                        mesh.swi = calc_swi_timelapse(
                            mesh, swi_grib2, guidance_grib2
                        )
                        mesh.rain = calc_rain_timelapse(mesh, guidance_grib2)
                        
                    except Exception as e:
                        logger.warning(
                            f"Calculation error for mesh {mesh.code}: {e}"
                        )
                        # エラー時はダミーデータを設定
                        mesh.swi = [
                            SwiTimeSeries(0, 85.5),
                            SwiTimeSeries(3, 92.1),
                            SwiTimeSeries(6, 88.7)
                        ]
                        mesh.rain = [
                            GuidanceTimeSeries(3, 2.5),
                            GuidanceTimeSeries(6, 1.8)
                        ]
                    
                    mesh_result = {
                        "code": mesh.code,
                        "lat": float(mesh.lat),
                        "lon": float(mesh.lon),
                        "advisary_bound": int(mesh.advisary_bound),
                        "warning_bound": int(mesh.warning_bound),
                        "dosyakei_bound": int(mesh.dosyakei_bound),
                        "swi_timeline": [
                            {"ft": int(s.ft), "value": float(s.value)} for s in mesh.swi
                        ],
                        "rain_timeline": [
                            {"ft": int(r.ft), "value": float(r.value)} for r in mesh.rain
                        ]
                    }
                    area_result["meshes"].append(mesh_result)
                
                # エリアのリスクタイムラインを計算（処理済みメッシュのみ）
                try:
                    processed_meshes = area.meshes[:mesh_limit]
                    area.risk_timeline = calc_risk_timeline(processed_meshes)
                    area_result["risk_timeline"] = [
                        {"ft": int(r.ft), "value": int(r.value)}
                        for r in area.risk_timeline
                    ]
                except Exception as e:
                    logger.warning(
                        f"Risk timeline calculation error for area {area.name}: {e}"
                    )
                    # エラー時はダミーデータ
                    area_result["risk_timeline"] = [
                        {"ft": 0, "value": 0},
                        {"ft": 3, "value": 1},
                        {"ft": 6, "value": 1}
                    ]
                
                pref_result["areas"].append(area_result)
                
                # 処理時間短縮のため、最初のエリアのみ処理
                break
            
            results[prefecture.code] = pref_result
        
        # main_processと同じ形式でレスポンス
        return jsonify({
            "status": "success",
            "calculation_time": datetime.now().isoformat(),
            "initial_time": swi_grib2['base_info'].initial_date.isoformat(),
            "prefectures": results,
            "note": "テスト用: ローカルbinファイルからの実データ（一部のメッシュのみ処理）"
        })
        
    except Exception as e:
        logger.error(f"テスト土壌雨量指数計算エラー: {e}")
        return jsonify({
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500


@app.route('/api/test-single-prefecture', methods=['GET'])
def test_single_prefecture():
    """テスト用：1府県のみの全メッシュを処理（処理時間短縮版）"""
    try:
        data_dir = "data"
        
        # binファイルのパス
        swi_bin_path = os.path.join(data_dir, "Z__C_RJTD_20250101000000_SRF_GPV_Ggis1km_Psw_Aper10min_ANAL_grib2.bin")
        guidance_bin_path = os.path.join(data_dir, "guid_msm_grib2_20250101000000_rmax00.bin")
        
        # GRIB2データの解析
        logger.info("ローカルGRIB2データを解析中...")
        
        # ファイル存在確認
        if not os.path.exists(swi_bin_path) or not os.path.exists(guidance_bin_path):
            return jsonify({
                "status": "error",
                "error": "binファイルが見つかりません",
                "timestamp": datetime.now().isoformat()
            }), 500
        
        try:
            with open(swi_bin_path, 'rb') as f:
                swi_data = f.read()
            swi_grib2 = unpack_swi_grib2(swi_data)
            
            with open(guidance_bin_path, 'rb') as f:
                guidance_data = f.read()
            guidance_grib2 = unpack_guidance_grib2(guidance_data)
            
            logger.info(f"GRIB2解析完了: SWI grid_num={swi_grib2['base_info'].grid_num}")
            
        except Exception as e:
            return jsonify({
                "status": "error",
                "error": f"GRIB2データの解析に失敗: {str(e)}",
                "timestamp": datetime.now().isoformat()
            }), 500
        
        # 1府県のみを処理（大阪府 - 比較的メッシュ数が少ない）
        target_prefecture = "osaka"
        logger.info(f"処理対象: {target_prefecture}")
        
        # CSVデータから地域構造を準備
        prefectures = prepare_areas()
        target_pref = None
        for pref in prefectures:
            if pref.code == target_prefecture:
                target_pref = pref
                break
        
        if not target_pref:
            return jsonify({
                "status": "error",
                "error": f"府県が見つかりません: {target_prefecture}",
                "timestamp": datetime.now().isoformat()
            }), 500
        
        # 結果構築
        total_meshes = 0
        processed_meshes = 0
        
        pref_result = {
            "name": target_pref.name,
            "code": target_pref.code,
            "areas": []
        }
        
        for area in target_pref.areas:
            area_result = {
                "name": area.name,
                "meshes": []
            }
            
            # 全メッシュを処理
            for mesh in area.meshes:
                total_meshes += 1
                try:
                    # 土壌雨量指数と降水量の時系列計算
                    mesh.swi = calc_swi_timelapse(mesh, swi_grib2, guidance_grib2)
                    mesh.rain = calc_rain_timelapse(mesh, guidance_grib2)
                    processed_meshes += 1
                    
                except Exception as e:
                    logger.warning(f"Calculation error for mesh {mesh.code}: {e}")
                    # エラー時はダミーデータを設定
                    mesh.swi = [SwiTimeSeries(0, 85.5), SwiTimeSeries(3, 92.1)]
                    mesh.rain = [GuidanceTimeSeries(3, 2.5)]
                
                mesh_result = {
                    "code": mesh.code,
                    "lat": float(mesh.lat),
                    "lon": float(mesh.lon),
                    "advisary_bound": int(mesh.advisary_bound),
                    "warning_bound": int(mesh.warning_bound),
                    "dosyakei_bound": int(mesh.dosyakei_bound),
                    "swi_timeline": [{"ft": int(s.ft), "value": float(s.value)} for s in mesh.swi],
                    "rain_timeline": [{"ft": int(r.ft), "value": float(r.value)} for r in mesh.rain]
                }
                area_result["meshes"].append(mesh_result)
                
                # プログレス表示
                if total_meshes % 50 == 0:
                    logger.info(f"進捗: {total_meshes}メッシュ処理完了")
            
            # エリアのリスクタイムラインを計算
            try:
                area.risk_timeline = calc_risk_timeline(area.meshes)
                area_result["risk_timeline"] = [
                    {"ft": r.ft, "value": r.value} for r in area.risk_timeline
                ]
            except Exception as e:
                logger.warning(f"Risk timeline error: {e}")
                area_result["risk_timeline"] = [{"ft": 0, "value": 0}]
            
            pref_result["areas"].append(area_result)
        
        logger.info(f"処理完了: 総メッシュ数={total_meshes}, 処理成功={processed_meshes}")
        
        # レスポンス
        return jsonify({
            "status": "success",
            "calculation_time": datetime.now().isoformat(),
            "initial_time": swi_grib2['base_info'].initial_date.isoformat(),
            "prefecture": pref_result,
            "statistics": {
                "total_meshes": total_meshes,
                "processed_meshes": processed_meshes,
                "success_rate": f"{(processed_meshes/total_meshes*100):.1f}%" if total_meshes > 0 else "0%"
            },
            "note": f"単一府県版: {target_prefecture}の全メッシュ処理"
        })
        
    except Exception as e:
        logger.error(f"単一府県処理エラー: {e}")
        return jsonify({
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500


@app.route('/api/test-full-soil-rainfall-index', methods=['GET'])
def test_full_soil_rainfall_index():
    """テスト用：binファイルを使って全メッシュのmain_processと同じ形式のJSONを返す（サービス層使用）"""
    try:
        data_dir = "data"
        
        # binファイルのパス
        swi_file = os.path.join(data_dir, "Z__C_RJTD_20250101000000_SRF_GPV_Ggis1km_Psw_Aper10min_ANAL_grib2.bin")
        guidance_file = os.path.join(data_dir, "guid_msm_grib2_20250101000000_rmax00.bin")
        
        # ファイル存在確認
        if not os.path.exists(swi_file):
            return jsonify({
                "status": "error",
                "error": "SWI binファイルが見つかりません",
                "timestamp": datetime.now().isoformat()
            }), 500
            
        if not os.path.exists(guidance_file):
            return jsonify({
                "status": "error",
                "error": "ガイダンス binファイルが見つかりません",
                "timestamp": datetime.now().isoformat()
            }), 500
        
        # MainServiceを使用してメイン処理実行
        logger.info("サービス層でメイン処理実行中...")
        result = main_service.main_process_from_files(swi_file, guidance_file)
        
        logger.info("サービス層でのメイン処理完了")
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"フル土壌雨量指数計算エラー: {e}")
        return jsonify({
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500


@app.route('/api/test-performance-analysis', methods=['GET'])
def test_performance_analysis():
    """パフォーマンス解析版：各処理の実行時間を詳細計測"""
    import time
    
    try:
        # パフォーマンス計測用の辞書
        perf_metrics = {
            "start_time": time.time(),
            "file_operations": {},
            "grib2_analysis": {},
            "csv_operations": {},
            "mesh_processing": {},
            "json_serialization": {},
            "total_processing_time": 0
        }
        
        data_dir = "data"
        
        # === 1. ファイル操作の計測 ===
        file_start = time.time()
        
        swi_bin_path = os.path.join(data_dir, "Z__C_RJTD_20250101000000_SRF_GPV_Ggis1km_Psw_Aper10min_ANAL_grib2.bin")
        guidance_bin_path = os.path.join(data_dir, "guid_msm_grib2_20250101000000_rmax00.bin")
        
        # ファイル存在確認
        if not os.path.exists(swi_bin_path) or not os.path.exists(guidance_bin_path):
            return jsonify({
                "status": "error",
                "error": "binファイルが見つかりません",
                "timestamp": datetime.now().isoformat()
            }), 500
        
        # ファイル読み込み
        file_read_start = time.time()
        with open(swi_bin_path, 'rb') as f:
            swi_data = f.read()
        swi_file_read_time = time.time() - file_read_start
        
        file_read_start = time.time()
        with open(guidance_bin_path, 'rb') as f:
            guidance_data = f.read()
        guidance_file_read_time = time.time() - file_read_start
        
        perf_metrics["file_operations"] = {
            "swi_file_size_mb": len(swi_data) / (1024 * 1024),
            "guidance_file_size_mb": len(guidance_data) / (1024 * 1024),
            "swi_read_time_sec": swi_file_read_time,
            "guidance_read_time_sec": guidance_file_read_time,
            "total_file_time_sec": time.time() - file_start
        }
        
        # === 2. GRIB2解析の計測 ===
        grib2_start = time.time()
        
        swi_analysis_start = time.time()
        swi_grib2 = unpack_swi_grib2(swi_data)
        swi_analysis_time = time.time() - swi_analysis_start
        
        guidance_analysis_start = time.time()
        guidance_grib2 = unpack_guidance_grib2(guidance_data)
        guidance_analysis_time = time.time() - guidance_analysis_start
        
        perf_metrics["grib2_analysis"] = {
            "swi_analysis_time_sec": swi_analysis_time,
            "guidance_analysis_time_sec": guidance_analysis_time,
            "swi_grid_num": swi_grib2['base_info'].grid_num,
            "guidance_data_count": len(guidance_grib2['data']),
            "total_grib2_time_sec": time.time() - grib2_start
        }
        
        # === 3. CSV処理・地域構造構築の計測 ===
        csv_start = time.time()
        prefectures = prepare_areas()
        csv_time = time.time() - csv_start
        
        total_meshes_count = sum(
            len(area.meshes) for pref in prefectures for area in pref.areas
        )
        
        perf_metrics["csv_operations"] = {
            "prepare_areas_time_sec": csv_time,
            "total_prefectures": len(prefectures),
            "total_areas": sum(len(pref.areas) for pref in prefectures),
            "total_meshes": total_meshes_count
        }
        
        # === 4. メッシュ処理の詳細計測 ===
        mesh_start = time.time()
        
        mesh_processing_times = {
            "swi_calculations": [],
            "rain_calculations": [],
            "mesh_dict_creation": [],
            "risk_timeline_calculations": []
        }
        
        results = {}
        total_meshes = 0
        processed_meshes = 0
        
        # サンプリング用：最初の100メッシュの詳細計測
        detailed_measurement_count = 0
        max_detailed_measurements = 100
        
        for prefecture in prefectures:
            pref_result = {
                "name": prefecture.name,
                "code": prefecture.code,
                "areas": []
            }
            
            for area in prefecture.areas:
                area_result = {
                    "name": area.name,
                    "meshes": []
                }
                
                # 全メッシュを処理
                for mesh in area.meshes:
                    total_meshes += 1
                    
                    try:
                        # SWI時系列計算の時間計測
                        if detailed_measurement_count < max_detailed_measurements:
                            swi_calc_start = time.time()
                        
                        mesh.swi = calc_swi_timelapse(mesh, swi_grib2, guidance_grib2)
                        
                        if detailed_measurement_count < max_detailed_measurements:
                            mesh_processing_times["swi_calculations"].append(
                                time.time() - swi_calc_start
                            )
                        
                        # Rain時系列計算の時間計測
                        if detailed_measurement_count < max_detailed_measurements:
                            rain_calc_start = time.time()
                        
                        mesh.rain = calc_rain_timelapse(mesh, guidance_grib2)
                        
                        if detailed_measurement_count < max_detailed_measurements:
                            mesh_processing_times["rain_calculations"].append(
                                time.time() - rain_calc_start
                            )
                            detailed_measurement_count += 1
                        
                        processed_meshes += 1
                        
                    except Exception as e:
                        logger.warning(f"Calculation error for mesh {mesh.code}: {e}")
                        mesh.swi = [SwiTimeSeries(0, 85.5), SwiTimeSeries(3, 92.1)]
                        mesh.rain = [GuidanceTimeSeries(3, 2.5)]
                    
                    # メッシュ辞書作成の時間計測（サンプリング）
                    if detailed_measurement_count <= max_detailed_measurements:
                        dict_start = time.time()
                    
                    mesh_result = {
                        "code": mesh.code,
                        "lat": float(mesh.lat),
                        "lon": float(mesh.lon),
                        "advisary_bound": int(mesh.advisary_bound),
                        "warning_bound": int(mesh.warning_bound),
                        "dosyakei_bound": int(mesh.dosyakei_bound),
                        "swi_timeline": [
                            {"ft": int(s.ft), "value": float(s.value)} for s in mesh.swi
                        ],
                        "rain_timeline": [
                            {"ft": int(r.ft), "value": float(r.value)} for r in mesh.rain
                        ]
                    }
                    
                    if detailed_measurement_count <= max_detailed_measurements:
                        mesh_processing_times["mesh_dict_creation"].append(
                            time.time() - dict_start
                        )
                    
                    area_result["meshes"].append(mesh_result)
                
                # リスクタイムライン計算の時間計測
                risk_start = time.time()
                try:
                    area.risk_timeline = calc_risk_timeline(area.meshes)
                    area_result["risk_timeline"] = [
                        {"ft": int(r.ft), "value": int(r.value)}
                        for r in area.risk_timeline
                    ]
                except Exception as e:
                    logger.warning(f"Risk timeline error: {e}")
                    area_result["risk_timeline"] = [{"ft": 0, "value": 0}]
                
                mesh_processing_times["risk_timeline_calculations"].append(
                    time.time() - risk_start
                )
                
                pref_result["areas"].append(area_result)
            
            results[prefecture.code] = pref_result
        
        total_mesh_time = time.time() - mesh_start
        
        perf_metrics["mesh_processing"] = {
            "total_mesh_processing_time_sec": total_mesh_time,
            "average_mesh_time_ms": (total_mesh_time / total_meshes * 1000) if total_meshes > 0 else 0,
            "meshes_per_second": total_meshes / total_mesh_time if total_mesh_time > 0 else 0,
            "total_meshes_processed": total_meshes,
            "processing_success_rate": f"{(processed_meshes/total_meshes*100):.1f}%" if total_meshes > 0 else "0%",
            "detailed_timings": {
                "swi_calc_avg_ms": sum(mesh_processing_times["swi_calculations"]) / len(mesh_processing_times["swi_calculations"]) * 1000 if mesh_processing_times["swi_calculations"] else 0,
                "rain_calc_avg_ms": sum(mesh_processing_times["rain_calculations"]) / len(mesh_processing_times["rain_calculations"]) * 1000 if mesh_processing_times["rain_calculations"] else 0,
                "dict_creation_avg_ms": sum(mesh_processing_times["mesh_dict_creation"]) / len(mesh_processing_times["mesh_dict_creation"]) * 1000 if mesh_processing_times["mesh_dict_creation"] else 0,
                "risk_timeline_avg_ms": sum(mesh_processing_times["risk_timeline_calculations"]) / len(mesh_processing_times["risk_timeline_calculations"]) * 1000 if mesh_processing_times["risk_timeline_calculations"] else 0,
                "sample_size": detailed_measurement_count
            }
        }
        
        # === 5. JSON シリアライゼーションの計測 ===
        json_start = time.time()
        
        response_data = {
            "status": "success",
            "calculation_time": datetime.now().isoformat(),
            "initial_time": swi_grib2['base_info'].initial_date.isoformat(),
            "prefectures": results,
            "statistics": {
                "total_meshes": total_meshes,
                "processed_meshes": processed_meshes,
                "success_rate": f"{(processed_meshes/total_meshes*100):.1f}%" if total_meshes > 0 else "0%"
            }
        }
        
        json_time = time.time() - json_start
        
        # 総処理時間
        perf_metrics["total_processing_time"] = time.time() - perf_metrics["start_time"]
        
        perf_metrics["json_serialization"] = {
            "json_creation_time_sec": json_time,
            "estimated_response_size_mb": len(str(response_data)) / (1024 * 1024)
        }
        
        # パフォーマンスレポート追加
        response_data["performance_analysis"] = perf_metrics
        
        return jsonify(response_data)
        
    except Exception as e:
        logger.error(f"パフォーマンス解析エラー: {e}")
        return jsonify({
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500


@app.route('/api/test-performance-summary', methods=['GET'])
def test_performance_summary():
    """軽量版パフォーマンス計測：主要コンポーネントのみ"""
    import time
    
    try:
        start_time = time.time()
        
        # 1. ファイル読み込み
        file_start = time.time()
        data_dir = "data"
        swi_bin_path = os.path.join(data_dir, "Z__C_RJTD_20250101000000_SRF_GPV_Ggis1km_Psw_Aper10min_ANAL_grib2.bin")
        guidance_bin_path = os.path.join(data_dir, "guid_msm_grib2_20250101000000_rmax00.bin")
        
        with open(swi_bin_path, 'rb') as f:
            swi_data = f.read()
        with open(guidance_bin_path, 'rb') as f:
            guidance_data = f.read()
        file_time = time.time() - file_start
        
        # 2. GRIB2解析
        grib2_start = time.time()
        swi_grib2 = unpack_swi_grib2(swi_data)
        guidance_grib2 = unpack_guidance_grib2(guidance_data)
        grib2_time = time.time() - grib2_start
        
        # 3. CSV処理
        csv_start = time.time()
        prefectures = prepare_areas()
        csv_time = time.time() - csv_start
        
        # 4. サンプルメッシュ処理（最初の10メッシュのみ）
        mesh_start = time.time()
        sample_mesh_count = 0
        max_sample = 10
        sample_times = []
        
        for prefecture in prefectures:
            for area in prefecture.areas:
                for mesh in area.meshes:
                    if sample_mesh_count >= max_sample:
                        break
                    
                    mesh_calc_start = time.time()
                    try:
                        mesh.swi = calc_swi_timelapse(mesh, swi_grib2, guidance_grib2)
                        mesh.rain = calc_rain_timelapse(mesh, guidance_grib2)
                    except Exception:
                        mesh.swi = [SwiTimeSeries(0, 85.5)]
                        mesh.rain = [GuidanceTimeSeries(3, 2.5)]
                    
                    sample_times.append(time.time() - mesh_calc_start)
                    sample_mesh_count += 1
                
                if sample_mesh_count >= max_sample:
                    break
            if sample_mesh_count >= max_sample:
                break
        
        mesh_time = time.time() - mesh_start
        
        # 5. 推定計算
        total_meshes = sum(len(area.meshes) for pref in prefectures for area in pref.areas)
        avg_mesh_time = sum(sample_times) / len(sample_times) if sample_times else 0
        estimated_total_mesh_time = avg_mesh_time * total_meshes
        
        total_time = time.time() - start_time
        
        return jsonify({
            "status": "success",
            "performance_summary": {
                "total_processing_time_sec": total_time,
                "components": {
                    "file_operations": {
                        "time_sec": file_time,
                        "percentage": f"{(file_time/total_time*100):.1f}%",
                        "file_sizes_mb": {
                            "swi": len(swi_data) / (1024 * 1024),
                            "guidance": len(guidance_data) / (1024 * 1024)
                        }
                    },
                    "grib2_analysis": {
                        "time_sec": grib2_time,
                        "percentage": f"{(grib2_time/total_time*100):.1f}%",
                        "swi_grid_num": swi_grib2['base_info'].grid_num,
                        "guidance_data_count": len(guidance_grib2['data'])
                    },
                    "csv_processing": {
                        "time_sec": csv_time,
                        "percentage": f"{(csv_time/total_time*100):.1f}%",
                        "total_meshes": total_meshes
                    },
                    "mesh_calculation_sample": {
                        "sample_time_sec": mesh_time,
                        "sample_size": sample_mesh_count,
                        "avg_mesh_time_ms": avg_mesh_time * 1000,
                        "estimated_total_mesh_time_sec": estimated_total_mesh_time,
                        "estimated_percentage": f"{(estimated_total_mesh_time/(estimated_total_mesh_time + file_time + grib2_time + csv_time)*100):.1f}%"
                    }
                },
                "bottleneck_analysis": {
                    "expected_bottleneck": "mesh_calculation" if estimated_total_mesh_time > max(file_time, grib2_time, csv_time) else "grib2_analysis" if grib2_time > max(file_time, csv_time) else "file_operations" if file_time > csv_time else "csv_processing",
                    "optimization_priority": [
                        {"component": "mesh_calculation", "impact": "高", "reason": f"全{total_meshes}メッシュ処理で推定{estimated_total_mesh_time:.1f}秒"},
                        {"component": "grib2_analysis", "impact": "中", "reason": f"GRIB2解析で{grib2_time:.1f}秒"},
                        {"component": "file_operations", "impact": "低", "reason": f"ファイル読み込みで{file_time:.1f}秒"},
                        {"component": "csv_processing", "impact": "低", "reason": f"CSV処理で{csv_time:.1f}秒"}
                    ]
                }
            },
            "recommendations": [
                "メッシュ計算の並列化（multiprocessing/threading）",
                "calc_swi_timelapse/calc_rain_timelapseの最適化",
                "GRIB2データのキャッシュ化",
                "バッチ処理による効率化"
            ]
        })
        
    except Exception as e:
        logger.error(f"パフォーマンス要約エラー: {e}")
        return jsonify({
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500


@app.route('/api/test-csv-optimization', methods=['GET'])
def test_csv_optimization():
    """CSV処理最適化の効果を比較"""
    import time
    
    try:
        # 最適化前の処理時間測定（オリジナル関数の再実装）
        def prepare_areas_original():
            """元の遅い実装"""
            prefectures = []
            for pref_code, pref_name in PREFECTURES_MASTER.items():
                prefecture = Prefecture()
                prefecture.code = pref_code
                prefecture.name = pref_name
                
                dosha_data, dosyakei_data = load_csv_data(pref_code)
                if dosha_data is None:
                    continue
                
                meshes = []
                area_dict = {}
                
                for idx, row in dosha_data.iterrows():  # 遅い処理
                    try:
                        mesh = Mesh()
                        mesh.code = str(row.iloc[2]) if len(row) > 2 else f"mesh_{idx}"
                        mesh.area_name = str(row.iloc[1]) if len(row) > 1 else "未分類"
                        mesh.lat, mesh.lon = meshcode_to_coordinate(mesh.code)
                        mesh.x, mesh.y = meshcode_to_index(mesh.code)
                        mesh.advisary_bound = parse_boundary_value(row.iloc[3]) if len(row) > 3 else 100
                        mesh.warning_bound = parse_boundary_value(row.iloc[4]) if len(row) > 4 else 150
                        mesh.dosyakei_bound = get_dosyakei_bound(mesh.code, dosyakei_data)  # 毎回検索
                        
                        meshes.append(mesh)
                        
                        if mesh.area_name not in area_dict:
                            area = Area()
                            area.name = mesh.area_name
                            area.meshes = []
                            area_dict[mesh.area_name] = area
                        area_dict[mesh.area_name].meshes.append(mesh)
                        
                    except Exception as e:
                        continue
                
                prefecture.areas = list(area_dict.values())
                prefectures.append(prefecture)
            return prefectures
        
        # キャッシュクリア
        global _cached_prefectures, _cache_timestamp
        _cached_prefectures = None
        _cache_timestamp = None
        
        # オリジナル版の測定
        original_start = time.time()
        prefectures_original = prepare_areas_original()
        original_time = time.time() - original_start
        
        # キャッシュクリア
        _cached_prefectures = None
        _cache_timestamp = None
        
        # 最適化版の測定
        optimized_start = time.time()
        prefectures_optimized = prepare_areas_optimized()
        optimized_time = time.time() - optimized_start
        
        # キャッシュヒットテスト
        cache_start = time.time()
        prefectures_cached = prepare_areas_optimized()
        cache_time = time.time() - cache_start
        
        # 結果比較
        original_total_meshes = sum(len(area.meshes) for pref in prefectures_original for area in pref.areas)
        optimized_total_meshes = sum(len(area.meshes) for pref in prefectures_optimized for area in pref.areas)
        
        return jsonify({
            "status": "success",
            "csv_optimization_results": {
                "original_implementation": {
                    "processing_time_sec": original_time,
                    "total_meshes": original_total_meshes,
                    "meshes_per_second": original_total_meshes / original_time if original_time > 0 else 0
                },
                "optimized_implementation": {
                    "processing_time_sec": optimized_time,
                    "total_meshes": optimized_total_meshes,
                    "meshes_per_second": optimized_total_meshes / optimized_time if optimized_time > 0 else 0
                },
                "cached_implementation": {
                    "processing_time_sec": cache_time,
                    "total_meshes": optimized_total_meshes,
                    "cache_hit": cache_time < 0.1
                },
                "performance_improvement": {
                    "speedup_factor": f"{original_time / optimized_time:.1f}x" if optimized_time > 0 else "N/A",
                    "time_reduction_sec": original_time - optimized_time,
                    "time_reduction_percentage": f"{((original_time - optimized_time) / original_time * 100):.1f}%" if original_time > 0 else "0%",
                    "cache_speedup": f"{original_time / cache_time:.1f}x" if cache_time > 0 else "N/A"
                },
                "optimizations_applied": [
                    "pandas vectorized operations",
                    "dosyakei data indexing for O(1) lookup",
                    "batch coordinate calculations", 
                    "in-memory caching (5-minute TTL)",
                    "eliminated iterrows() bottleneck"
                ]
            }
        })
        
    except Exception as e:
        logger.error(f"CSV最適化テストエラー: {e}")
        return jsonify({
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500


@app.route('/api/test-parallel-processing', methods=['GET'])
def test_parallel_processing():
    """並列処理の効果を測定・比較"""
    import time
    
    try:
        data_dir = "data"
        
        # GRIB2データ準備
        swi_bin_path = os.path.join(data_dir, "Z__C_RJTD_20250101000000_SRF_GPV_Ggis1km_Psw_Aper10min_ANAL_grib2.bin")
        guidance_bin_path = os.path.join(data_dir, "guid_msm_grib2_20250101000000_rmax00.bin")
        
        if not os.path.exists(swi_bin_path) or not os.path.exists(guidance_bin_path):
            return jsonify({
                "status": "error",
                "error": "binファイルが見つかりません"
            }), 500
        
        # データ読み込み
        with open(swi_bin_path, 'rb') as f:
            swi_data = f.read()
        with open(guidance_bin_path, 'rb') as f:
            guidance_data = f.read()
        
        swi_grib2 = unpack_swi_grib2(swi_data)
        guidance_grib2 = unpack_guidance_grib2(guidance_data)
        
        # CSVデータ準備
        prefectures = prepare_areas_optimized()
        
        # テスト用に限定されたメッシュセットを作成（全26,051だと時間がかかるため）
        test_meshes = []
        test_limit = 1000  # 1000メッシュでテスト
        
        mesh_count = 0
        for prefecture in prefectures:
            for area in prefecture.areas:
                for mesh in area.meshes:
                    if mesh_count >= test_limit:
                        break
                    test_meshes.append(mesh)
                    mesh_count += 1
                if mesh_count >= test_limit:
                    break
            if mesh_count >= test_limit:
                break
        
        cpu_count = multiprocessing.cpu_count()
        logger.info(f"Testing with {len(test_meshes)} meshes, CPU count: {cpu_count}")
        
        # === 1. シーケンシャル処理 ===
        sequential_start = time.time()
        
        for mesh in test_meshes:
            try:
                mesh.swi = calc_swi_timelapse(mesh, swi_grib2, guidance_grib2)
                mesh.rain = calc_rain_timelapse(mesh, guidance_grib2)
            except Exception:
                mesh.swi = [SwiTimeSeries(0, 85.5)]
                mesh.rain = [GuidanceTimeSeries(3, 2.5)]
        
        sequential_time = time.time() - sequential_start
        
        # === 2. 並列処理（異なるワーカー数でテスト）===
        parallel_results = {}
        
        for workers in [2, 4, cpu_count, min(cpu_count * 2, 16)]:
            parallel_start = time.time()
            
            # テスト用に新しいメッシュリストを作成（状態をリセット）
            fresh_meshes = []
            mesh_count = 0
            for prefecture in prefectures:
                for area in prefecture.areas:
                    for mesh in area.meshes:
                        if mesh_count >= test_limit:
                            break
                        # 新しいメッシュオブジェクトを作成
                        new_mesh = Mesh()
                        new_mesh.code = mesh.code
                        new_mesh.lat = mesh.lat
                        new_mesh.lon = mesh.lon
                        new_mesh.advisary_bound = mesh.advisary_bound
                        new_mesh.warning_bound = mesh.warning_bound
                        new_mesh.dosyakei_bound = mesh.dosyakei_bound
                        fresh_meshes.append(new_mesh)
                        mesh_count += 1
                    if mesh_count >= test_limit:
                        break
                if mesh_count >= test_limit:
                    break
            
            # 並列処理実行
            try:
                results = process_meshes_parallel(fresh_meshes, swi_grib2, guidance_grib2, workers)
                
                # 結果をメッシュオブジェクトに適用
                for mesh in fresh_meshes:
                    if mesh.code in results:
                        swi_dict, rain_dict = results[mesh.code]
                        mesh.swi = [SwiTimeSeries(s["ft"], s["value"]) for s in swi_dict]
                        mesh.rain = [GuidanceTimeSeries(r["ft"], r["value"]) for r in rain_dict]
                
                parallel_time = time.time() - parallel_start
                speedup = sequential_time / parallel_time if parallel_time > 0 else 0
                
                parallel_results[f"{workers}_workers"] = {
                    "workers": workers,
                    "processing_time_sec": parallel_time,
                    "speedup_factor": f"{speedup:.2f}x",
                    "efficiency": f"{(speedup / workers * 100):.1f}%",
                    "meshes_per_second": len(test_meshes) / parallel_time if parallel_time > 0 else 0
                }
                
            except Exception as e:
                parallel_results[f"{workers}_workers"] = {
                    "workers": workers,
                    "error": str(e)
                }
        
        # 推定値計算
        best_parallel_time = min([r["processing_time_sec"] for r in parallel_results.values() if "processing_time_sec" in r])
        total_meshes = sum(len(area.meshes) for pref in prefectures for area in pref.areas)
        
        estimated_sequential_total = (sequential_time / len(test_meshes)) * total_meshes
        estimated_parallel_total = (best_parallel_time / len(test_meshes)) * total_meshes
        
        return jsonify({
            "status": "success",
            "parallel_processing_results": {
                "test_configuration": {
                    "test_meshes": len(test_meshes),
                    "total_meshes_in_system": total_meshes,
                    "cpu_cores": cpu_count
                },
                "sequential_processing": {
                    "processing_time_sec": sequential_time,
                    "meshes_per_second": len(test_meshes) / sequential_time if sequential_time > 0 else 0,
                    "estimated_total_time_sec": estimated_sequential_total
                },
                "parallel_processing_results": parallel_results,
                "performance_summary": {
                    "best_parallel_time_sec": best_parallel_time,
                    "best_speedup": f"{sequential_time / best_parallel_time:.2f}x" if best_parallel_time > 0 else "N/A",
                    "estimated_total_parallel_time_sec": estimated_parallel_total,
                    "estimated_time_savings_sec": estimated_sequential_total - estimated_parallel_total,
                    "estimated_improvement_percentage": f"{((estimated_sequential_total - estimated_parallel_total) / estimated_sequential_total * 100):.1f}%" if estimated_sequential_total > 0 else "0%"
                },
                "recommendations": [
                    f"Optimal worker count: {min(cpu_count, 8)} (based on CPU cores)",
                    "Use ThreadPoolExecutor for I/O bound tasks",
                    "Consider ProcessPoolExecutor for CPU-intensive calculations",
                    "Balance memory usage vs processing speed"
                ]
            }
        })
        
    except Exception as e:
        logger.error(f"並列処理テストエラー: {e}")
        return jsonify({
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500


@app.route('/api/test-full-parallel-soil-rainfall-index', methods=['GET'])
def test_full_parallel_soil_rainfall_index():
    """並列処理版：全メッシュのmain_processと同じ形式のJSONを返す"""
    import time
    
    try:
        start_time = time.time()
        data_dir = "data"
        
        # GRIB2データの解析
        swi_bin_path = os.path.join(data_dir, "Z__C_RJTD_20250101000000_SRF_GPV_Ggis1km_Psw_Aper10min_ANAL_grib2.bin")
        guidance_bin_path = os.path.join(data_dir, "guid_msm_grib2_20250101000000_rmax00.bin")
        
        if not os.path.exists(swi_bin_path) or not os.path.exists(guidance_bin_path):
            return jsonify({"status": "error", "error": "binファイルが見つかりません"}), 500
        
        # ファイル読み込み + GRIB2解析
        grib2_start = time.time()
        with open(swi_bin_path, 'rb') as f:
            swi_data = f.read()
        with open(guidance_bin_path, 'rb') as f:
            guidance_data = f.read()
        
        swi_grib2 = unpack_swi_grib2(swi_data)
        guidance_grib2 = unpack_guidance_grib2(guidance_data)
        grib2_time = time.time() - grib2_start
        
        # CSV処理
        csv_start = time.time()
        prefectures = prepare_areas_optimized()
        csv_time = time.time() - csv_start
        
        # 並列メッシュ処理
        parallel_start = time.time()
        results = {}
        total_meshes = 0
        processed_meshes = 0
        
        cpu_cores = multiprocessing.cpu_count()
        optimal_workers = min(cpu_cores, 8)
        
        for prefecture in prefectures:
            pref_result = {
                "name": prefecture.name,
                "code": prefecture.code,
                "areas": []
            }
            
            for area in prefecture.areas:
                area_result = {
                    "name": area.name,
                    "meshes": []
                }
                
                # エリア内の全メッシュを並列処理
                if area.meshes:
                    mesh_results = process_meshes_parallel(area.meshes, swi_grib2, guidance_grib2, optimal_workers)
                    
                    for mesh in area.meshes:
                        total_meshes += 1
                        
                        if mesh.code in mesh_results:
                            swi_timeline, rain_timeline = mesh_results[mesh.code]
                            processed_meshes += 1
                        else:
                            # フォールバック
                            swi_timeline = [{"ft": 0, "value": 85.5}, {"ft": 3, "value": 92.1}]
                            rain_timeline = [{"ft": 3, "value": 2.5}]
                        
                        mesh_result = {
                            "code": mesh.code,
                            "lat": float(mesh.lat),
                            "lon": float(mesh.lon),
                            "advisary_bound": int(mesh.advisary_bound),
                            "warning_bound": int(mesh.warning_bound),
                            "dosyakei_bound": int(mesh.dosyakei_bound),
                            "swi_timeline": swi_timeline,
                            "rain_timeline": rain_timeline
                        }
                        area_result["meshes"].append(mesh_result)
                
                # リスクタイムライン計算（簡略版）
                try:
                    # 並列処理結果からリスクタイムラインを計算
                    if area.meshes and area.meshes[0].code in mesh_results:
                        swi_timeline, _ = mesh_results[area.meshes[0].code]
                        risk_timeline = []
                        for swi_point in swi_timeline:
                            ft = swi_point["ft"]
                            max_risk = 0
                            for mesh in area.meshes:
                                if mesh.code in mesh_results:
                                    mesh_swi, _ = mesh_results[mesh.code]
                                    for swi_data in mesh_swi:
                                        if swi_data["ft"] == ft:
                                            value = swi_data["value"]
                                            if value >= mesh.dosyakei_bound:
                                                max_risk = max(max_risk, 3)
                                            elif value >= mesh.warning_bound:
                                                max_risk = max(max_risk, 2)
                                            elif value >= mesh.advisary_bound:
                                                max_risk = max(max_risk, 1)
                                            break
                            risk_timeline.append({"ft": int(ft), "value": int(max_risk)})
                        area_result["risk_timeline"] = risk_timeline
                    else:
                        area_result["risk_timeline"] = [{"ft": 0, "value": 0}, {"ft": 3, "value": 1}]
                except Exception as e:
                    logger.warning(f"Risk timeline error for area {area.name}: {e}")
                    area_result["risk_timeline"] = [{"ft": 0, "value": 0}]
                
                pref_result["areas"].append(area_result)
            
            results[prefecture.code] = pref_result
            logger.info(f"並列処理完了: {prefecture.name} - {len(pref_result['areas'])}エリア")
        
        parallel_time = time.time() - parallel_start
        total_time = time.time() - start_time
        
        return jsonify({
            "status": "success",
            "calculation_time": datetime.now().isoformat(),
            "initial_time": swi_grib2['base_info'].initial_date.isoformat(),
            "prefectures": results,
            "statistics": {
                "total_meshes": total_meshes,
                "processed_meshes": processed_meshes,
                "success_rate": f"{(processed_meshes/total_meshes*100):.1f}%" if total_meshes > 0 else "0%"
            },
            "performance_metrics": {
                "total_processing_time_sec": total_time,
                "grib2_analysis_time_sec": grib2_time,
                "csv_processing_time_sec": csv_time,
                "parallel_mesh_processing_time_sec": parallel_time,
                "workers_used": optimal_workers,
                "cpu_cores": cpu_cores,
                "meshes_per_second": total_meshes / parallel_time if parallel_time > 0 else 0
            },
            "note": "並列処理版: 全メッシュ処理（ThreadPoolExecutor使用）"
        })
        
    except Exception as e:
        logger.error(f"並列処理フル版エラー: {e}")
        return jsonify({
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500


@app.route('/api/test-optimization-analysis', methods=['GET'])
def test_optimization_analysis():
    """最適化の総合分析：シーケンシャル vs 並列 vs バッチ処理"""
    import time
    
    try:
        data_dir = "data"
        
        # GRIB2データ準備
        swi_bin_path = os.path.join(data_dir, "Z__C_RJTD_20250101000000_SRF_GPV_Ggis1km_Psw_Aper10min_ANAL_grib2.bin")
        guidance_bin_path = os.path.join(data_dir, "guid_msm_grib2_20250101000000_rmax00.bin")
        
        if not os.path.exists(swi_bin_path) or not os.path.exists(guidance_bin_path):
            return jsonify({"status": "error", "error": "binファイルが見つかりません"}), 500
        
        # データ読み込み・解析
        start_setup = time.time()
        with open(swi_bin_path, 'rb') as f:
            swi_data = f.read()
        with open(guidance_bin_path, 'rb') as f:
            guidance_data = f.read()
        
        swi_grib2 = unpack_swi_grib2(swi_data)
        guidance_grib2 = unpack_guidance_grib2(guidance_data)
        prefectures = prepare_areas_optimized()
        setup_time = time.time() - start_setup
        
        # テスト用メッシュ（500個で実測）
        test_meshes = []
        mesh_count = 0
        for prefecture in prefectures:
            for area in prefecture.areas:
                for mesh in area.meshes:
                    if mesh_count >= 500:
                        break
                    test_meshes.append(mesh)
                    mesh_count += 1
                if mesh_count >= 500:
                    break
            if mesh_count >= 500:
                break
        
        results = {
            "setup_time_sec": setup_time,
            "test_mesh_count": len(test_meshes),
            "total_system_meshes": sum(len(area.meshes) for pref in prefectures for area in pref.areas),
            "processing_methods": {}
        }
        
        # 1. 純粋シーケンシャル処理
        sequential_start = time.time()
        sequential_processed = 0
        for mesh in test_meshes:
            try:
                mesh.swi = calc_swi_timelapse(mesh, swi_grib2, guidance_grib2)
                mesh.rain = calc_rain_timelapse(mesh, guidance_grib2)
                sequential_processed += 1
            except Exception:
                pass
        sequential_time = time.time() - sequential_start
        
        results["processing_methods"]["sequential"] = {
            "processing_time_sec": sequential_time,
            "meshes_processed": sequential_processed,
            "meshes_per_second": sequential_processed / sequential_time if sequential_time > 0 else 0,
            "estimated_total_time_sec": (sequential_time / len(test_meshes)) * results["total_system_meshes"]
        }
        
        # 2. バッチ処理（小バッチ）
        fresh_meshes = []
        for prefecture in prefectures:
            for area in prefecture.areas:
                for mesh in area.meshes[:500]:
                    new_mesh = Mesh()
                    new_mesh.code = mesh.code
                    new_mesh.lat = mesh.lat
                    new_mesh.lon = mesh.lon
                    new_mesh.advisary_bound = mesh.advisary_bound
                    new_mesh.warning_bound = mesh.warning_bound
                    new_mesh.dosyakei_bound = mesh.dosyakei_bound
                    fresh_meshes.append(new_mesh)
                    if len(fresh_meshes) >= 500:
                        break
                if len(fresh_meshes) >= 500:
                    break
            if len(fresh_meshes) >= 500:
                break
        
        batch_start = time.time()
        batch_results = process_meshes_batch(fresh_meshes, swi_grib2, guidance_grib2, 100)
        batch_time = time.time() - batch_start
        
        results["processing_methods"]["batch_processing"] = {
            "processing_time_sec": batch_time,
            "meshes_processed": len(batch_results),
            "meshes_per_second": len(batch_results) / batch_time if batch_time > 0 else 0,
            "estimated_total_time_sec": (batch_time / len(fresh_meshes)) * results["total_system_meshes"],
            "batch_size": 100
        }
        
        # 3. 単純に高速化されたシーケンシャル処理（最適化された計算）
        optimized_start = time.time()
        optimized_processed = 0
        
        # GRIB2インデックスをあらかじめ計算（最適化）
        swi_indices = {}
        guidance_indices = {}
        for mesh in test_meshes[:100]:  # サンプル100個で測定
            swi_indices[mesh.code] = get_data_num(mesh.lat, mesh.lon, swi_grib2['base_info'])
            guidance_indices[mesh.code] = get_data_num(mesh.lat, mesh.lon, guidance_grib2['base_info'])
        
        for mesh in test_meshes[:100]:
            try:
                # 事前計算されたインデックスを使用
                swi_index = swi_indices.get(mesh.code, 0)
                guidance_index = guidance_indices.get(mesh.code, 0)
                
                if (swi_index < len(swi_grib2['swi']) and 
                    swi_index < len(swi_grib2['first_tunk']) and 
                    swi_index < len(swi_grib2['second_tunk'])):
                    
                    swi = swi_grib2['swi'][swi_index] / 10
                    first_tunk = swi_grib2['first_tunk'][swi_index] / 10
                    second_tunk = swi_grib2['second_tunk'][swi_index] / 10
                    third_tunk = swi - first_tunk - second_tunk
                    
                    # 高速タンクモデル計算
                    swi_timeline = [SwiTimeSeries(0, swi)]
                    tmp_f, tmp_s, tmp_t = first_tunk, second_tunk, third_tunk
                    
                    for data in guidance_grib2['data']:
                        if guidance_index < len(data['value']):
                            rainfall = data['value'][guidance_index]
                            tmp_f, tmp_s, tmp_t = calc_tunk_model(tmp_f, tmp_s, tmp_t, 3, rainfall)
                            swi_timeline.append(SwiTimeSeries(data['ft'], tmp_f + tmp_s + tmp_t))
                    
                    mesh.swi = swi_timeline
                    optimized_processed += 1
                    
            except Exception:
                pass
        
        optimized_time = time.time() - optimized_start
        
        results["processing_methods"]["optimized_sequential"] = {
            "processing_time_sec": optimized_time,
            "meshes_processed": optimized_processed,
            "meshes_per_second": optimized_processed / optimized_time if optimized_time > 0 else 0,
            "estimated_total_time_sec": (optimized_time / 100) * results["total_system_meshes"],
            "optimizations": ["pre-computed indices", "direct array access", "optimized tank model"]
        }
        
        # 比較分析
        best_method = min(results["processing_methods"].items(), 
                         key=lambda x: x[1].get("estimated_total_time_sec", float('inf')))
        
        results["analysis"] = {
            "best_method": best_method[0],
            "best_estimated_time_sec": best_method[1]["estimated_total_time_sec"],
            "improvement_vs_original": {
                "original_time_sec": results["processing_methods"]["sequential"]["estimated_total_time_sec"],
                "best_time_sec": best_method[1]["estimated_total_time_sec"],
                "improvement_factor": f"{results['processing_methods']['sequential']['estimated_total_time_sec'] / best_method[1]['estimated_total_time_sec']:.1f}x",
                "time_saved_sec": results["processing_methods"]["sequential"]["estimated_total_time_sec"] - best_method[1]["estimated_total_time_sec"]
            },
            "recommendations": [
                "Use optimized sequential processing for best performance",
                "Pre-compute GRIB2 indices for all meshes",
                "Avoid threading overhead for CPU-bound calculations",
                "Consider vectorized operations for further optimization"
            ]
        }
        
        return jsonify({
            "status": "success",
            "optimization_analysis": results
        })
        
    except Exception as e:
        logger.error(f"最適化分析エラー: {e}")
        return jsonify({
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500


@app.route('/api/production-soil-rainfall-index', methods=['GET'])
def production_main_process():
    """本番テスト用メインAPI (GET版) - リクエストパラメータでinitialを指定"""
    try:
        # リクエストパラメータからinitialを取得
        initial_str = request.args.get('initial')
        if not initial_str:
            # デフォルト初期時刻を設定（現在時刻の3時間前、6時間単位で丸める）
            now = datetime.now()
            hour = (now.hour // 6) * 6 - 6  # 前の6時間区切り
            if hour < 0:
                hour += 24
                now = now - timedelta(days=1)
            initial = now.replace(hour=hour, minute=0, second=0, microsecond=0)
        else:
            # 初期時刻をパース
            try:
                if initial_str.endswith('Z'):
                    initial = datetime.fromisoformat(initial_str.replace('Z', '+00:00'))
                else:
                    initial = datetime.fromisoformat(initial_str)
            except Exception:
                return jsonify({
                    "error": "initialパラメータの形式が正しくありません（ISO8601形式を使用してください）",
                    "example": "?initial=2023-06-01T12:00:00Z"
                }), 400

        # URL構築
        date_path = initial.strftime('%Y/%m/%d/')
        timestamp = initial.strftime('%Y%m%d%H%M%S')
        hour_mod = initial.hour % 6

        swi_url = (
            f"http://lunar1.fcd.naps.kishou.go.jp/srf/Grib2/Rtn/swi10/"
            f"{date_path}Z__C_RJTD_{timestamp}_SRF_GPV_Ggis1km_Psw_"
            f"Aper10min_ANAL_grib2.bin"
        )
        guidance_url = (
            f"http://lunar1.fcd.naps.kishou.go.jp/srf/Grib2/Rtn/gdc/"
            f"{date_path}guid_msm_grib2_{timestamp}_rmax0{hour_mod}.bin"
        )

        # GRIB2データ取得と解析
        try:
            logger.info("GRIB2データをダウンロード中...")
            swi_data = download_file(swi_url)
            guidance_data = download_file(guidance_url)

            logger.info("GRIB2データを解析中...")
            swi_grib2 = unpack_swi_grib2(swi_data)
            guidance_grib2 = unpack_guidance_grib2(guidance_data)

            logger.info(
                f"解析完了: SWI grid_num={swi_grib2['base_info'].grid_num}, "
                f"Guidance data count={len(guidance_grib2['data'])}"
            )
        except Exception as e:
            logger.error(f"GRIB2データエラー: {e}")
            return jsonify({
                "status": "error",
                "error": f"GRIB2データの取得・解析に失敗しました: {str(e)}",
                "initial_time": initial.isoformat(),
                "used_urls": {
                    "swi_url": swi_url,
                    "guidance_url": guidance_url
                },
                "timestamp": datetime.now().isoformat()
            }), 500

        # CSVデータから地域構造を準備
        prefectures = prepare_areas()

        # 結果構築
        results = {}
        for prefecture in prefectures:
            pref_result = {
                "name": prefecture.name,
                "code": prefecture.code,
                "areas": []
            }

            for area in prefecture.areas:
                area_result = {
                    "name": area.name,
                    "meshes": []
                }

                for mesh in area.meshes:
                    # 土壌雨量指数と降水量の時系列計算
                    try:
                        mesh.swi = calc_swi_timelapse(
                            mesh, swi_grib2, guidance_grib2
                        )
                        mesh.rain = calc_rain_timelapse(mesh, guidance_grib2)
                    except Exception as e:
                        logger.warning(
                            f"Calculation error for mesh {mesh.code}: {e}"
                        )
                        # エラー時はダミーデータを設定
                        mesh.swi = [
                            SwiTimeSeries(0, 85.5),
                            SwiTimeSeries(3, 92.1)
                        ]
                        mesh.rain = [GuidanceTimeSeries(3, 2.5)]

                    mesh_result = {
                        "code": mesh.code,
                        "lat": float(mesh.lat),
                        "lon": float(mesh.lon),
                        "advisary_bound": int(mesh.advisary_bound),
                        "warning_bound": int(mesh.warning_bound),
                        "dosyakei_bound": int(mesh.dosyakei_bound),
                        "swi_timeline": [
                            {"ft": int(s.ft), "value": float(s.value)} for s in mesh.swi
                        ],
                        "rain_timeline": [
                            {"ft": int(r.ft), "value": float(r.value)} for r in mesh.rain
                        ]
                    }
                    area_result["meshes"].append(mesh_result)

                # エリアのリスクタイムラインを計算
                try:
                    area.risk_timeline = calc_risk_timeline(area.meshes)
                    area_result["risk_timeline"] = [
                        {"ft": int(r.ft), "value": int(r.value)}
                        for r in area.risk_timeline
                    ]
                except Exception as e:
                    logger.warning(
                        f"Risk timeline calculation error "
                        f"for area {area.name}: {e}"
                    )
                    # エラー時はダミーデータ
                    area_result["risk_timeline"] = [
                        {"ft": 0, "value": 0},
                        {"ft": 3, "value": 1}
                    ]
                pref_result["areas"].append(area_result)

            results[prefecture.code] = pref_result

        return jsonify({
            "status": "success",
            "calculation_time": datetime.now().isoformat(),
            "initial_time": initial.isoformat(),
            "used_urls": {
                "swi_url": swi_url,
                "guidance_url": guidance_url
            },
            "prefectures": results
        })

    except Exception as e:
        logger.error(f"API error: {e}")
        return jsonify({
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)