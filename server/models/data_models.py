# -*- coding: utf-8 -*-
"""
データモデル定義
土壌雨量指数計算システムで使用するすべてのデータクラス
"""
from dataclasses import dataclass
from typing import List, Optional
from datetime import datetime


@dataclass
class BaseInfo:
    """GRIB2ファイルの基本情報"""
    initial_date: datetime
    grid_num: int
    x_num: int
    y_num: int
    s_lat: int  # ミリ度
    s_lon: int  # ミリ度
    e_lat: int  # ミリ度
    e_lon: int  # ミリ度
    d_lat: int  # ミリ度
    d_lon: int  # ミリ度


@dataclass
class SwiTimeSeries:
    """土壌雨量指数時系列データ"""
    ft: int  # 予測時間（時間）
    value: float  # SWI値


@dataclass
class GuidanceTimeSeries:
    """ガイダンス時系列データ（降水量）"""
    ft: int  # 予測時間（時間）  
    value: float  # 降水量値


@dataclass
class Risk:
    """リスクレベル情報"""
    ft: int  # 予測時間（時間）
    value: int  # リスクレベル（0-3）


@dataclass
class Mesh:
    """メッシュデータ"""
    area_name: str
    code: str  # メッシュコード
    lat: float
    lon: float
    x: int  # グリッドX座標
    y: int  # グリッドY座標
    advisary_bound: int  # 注意報基準値
    warning_bound: int   # 警報基準値
    dosyakei_bound: int  # 土砂災害基準値
    swi: List[SwiTimeSeries]  # 3時間ごとのSWI
    swi_hourly: List[SwiTimeSeries]  # 1時間ごとのSWI
    rain_1hour: List[GuidanceTimeSeries]  # 1時間ごとの雨量（推定）
    rain_1hour_max: List[GuidanceTimeSeries]  # 3時間内の最大1時間雨量
    rain_3hour: List[GuidanceTimeSeries]  # 3時間ごとの合計雨量
    risk_hourly: List[Risk]  # 1時間ごとの危険度
    risk_3hour_max: List[Risk]  # 3時間ごとの最大危険度（1時間雨量ベース）
    vba_x: Optional[int] = None  # VBA X座標（GRIB2データアクセス用）
    vba_y: Optional[int] = None  # VBA Y座標（GRIB2データアクセス用）


@dataclass
class Area:
    """地域データ"""
    name: str
    meshes: List[Mesh]


@dataclass
class Prefecture:
    """都道府県データ"""
    name: str
    code: str
    areas: List[Area]
    area_min_x: int
    area_max_y: int


# 都道府県マスターデータ
PREFECTURES_MASTER = {
    'shiga': '滋賀県',
    'kyoto': '京都府', 
    'osaka': '大阪府',
    'hyogo': '兵庫県',
    'nara': '奈良県',
    'wakayama': '和歌山県'
}