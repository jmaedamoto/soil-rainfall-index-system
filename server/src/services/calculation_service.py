#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
VBA Module.basの完全再現によるCalculationService
既存のcalculation_service.pyを完全に置き換え
"""

from typing import List, Dict, Any, Tuple, Optional
import logging
from datetime import datetime, timedelta

from models import (
    BaseInfo, SwiTimeSeries, GuidanceTimeSeries, Risk,
    Mesh, Area, Prefecture, SecondarySubdivision
)
from .calculation_aggregation_service import CalculationAggregationService

logger = logging.getLogger(__name__)

class CalculationService:
    """VBA Module.basの完全再現によるCalculationService"""

    # VBA タンクモデルパラメータ (完全同一)
    l1, l2, l3, l4 = 15.0, 60.0, 15.0, 15.0
    a1, a2, a3, a4 = 0.1, 0.15, 0.05, 0.01
    b1, b2, b3 = 0.12, 0.05, 0.01

    def __init__(self):
        self.aggregation_service = CalculationAggregationService()

    @staticmethod
    def normalize_risk_rule(risk_rule: Optional[str]) -> str:
        """危険度ルールを正規化する。"""
        normalized = (risk_rule or "legacy").lower()
        if normalized not in {"legacy", "lead_time_to_level4"}:
            raise ValueError(f"Unsupported risk_rule: {risk_rule}")
        return normalized

    @staticmethod
    def _normalize_rainfall_index(rain_value: float) -> int:
        """1時間雨量から level4_curve 参照用インデックスを作る。"""
        try:
            rainfall_index = int(round(float(rain_value)))
        except (TypeError, ValueError):
            rainfall_index = 0
        return max(0, min(150, rainfall_index))

    def get_level4_threshold(
        self,
        level4_curve,
        rain_value: float,
        fallback_dosyakei_bound: int
    ) -> Optional[int]:
        """1時間雨量に対応するレベル4閾値を取得する。"""
        if level4_curve is None:
            return fallback_dosyakei_bound

        rainfall_index = self._normalize_rainfall_index(rain_value)

        try:
            threshold = int(level4_curve[rainfall_index])
        except (IndexError, TypeError, ValueError):
            return fallback_dosyakei_bound

        if threshold >= 999:
            return None

        return threshold

    def get_data_num(self, lat: float, lon: float, base_info: Any) -> int:
        """
        VBA Function get_data_num の完全再現
        VBA 1-based戻り値をそのまま返す（Python配列アクセス時に-1）
        """
        # VBA: y = Int((base_info.s_lat / 1000000 - lat) / (base_info.d_lat / 1000000)) + 1
        y = int((base_info.s_lat / 1000000 - lat) / (base_info.d_lat / 1000000)) + 1

        # VBA: x = Int((lon - base_info.s_lon / 1000000) / (base_info.d_lon / 1000000)) + 1
        x = int((lon - base_info.s_lon / 1000000) / (base_info.d_lon / 1000000)) + 1

        # VBA: get_data_num = (y - 1) * base_info.x_num + x
        return (y - 1) * base_info.x_num + x

    def get_data_num_from_vba_coordinates(self, vba_x: int, vba_y: int, base_info: Any) -> int:
        """
        VBA座標の処理は通常の緯度経度変換経由で行う
        VBA Module.basの実装と同じ方式に戻す
        """
        # VBA座標をメッシュコードに変換してから緯度経度を取得
        # これはdataServiceでのmeshcode_to_coordinateと同等の処理
        try:
            # VBA座標からメッシュコード様式の座標を復元
            # 通常のget_data_num関数を使用するために緯度経度変換を行う
            lat, lon = self.vba_coordinates_to_latlon(vba_x, vba_y)

            # VBA: get_data_num(lat, lon, base_info)と同じ処理
            return self.get_data_num(lat, lon, base_info)

        except Exception as e:
            logger.error(f"Error in get_data_num_from_vba_coordinates for ({vba_x}, {vba_y}): {e}")
            return 1  # エラー時のデフォルト値

    def vba_coordinates_to_latlon(self, vba_x: int, vba_y: int) -> tuple:
        """
        VBA座標から緯度経度を計算
        メッシュコード変換ロジックに基づく
        """
        try:
            # VBA座標をメッシュコード形式として解釈
            lat = (vba_y + 0.5) * 30 / 3600  # メッシュコード変換式
            lon = (vba_x + 0.5) * 45 / 3600 + 100  # メッシュコード変換式
            return lat, lon
        except Exception:
            return 35.0, 135.0  # デフォルト座標（関西地方中央）

    def calc_tunk_model(self, s1: float, s2: float, s3: float, t: float, r: float) -> Tuple[float, float, float]:
        """
        VBA Sub calc_tunk_model の完全再現
        """
        # VBA: q1 = 0, q2 = 0, q3 = 0
        q1 = q2 = q3 = 0.0

        # VBA: If s1 > l1 Then q1 = q1 + a1 * (s1 - l1)
        if s1 > self.l1:
            q1 = q1 + self.a1 * (s1 - self.l1)

        # VBA: If s1 > l2 Then q1 = q1 + a2 * (s1 - l2)
        if s1 > self.l2:
            q1 = q1 + self.a2 * (s1 - self.l2)

        # VBA: If s2 > l3 Then q2 = a3 * (s2 - l3)
        if s2 > self.l3:
            q2 = self.a3 * (s2 - self.l3)

        # VBA: If s3 > l4 Then q3 = a4 * (s3 - l4)
        if s3 > self.l4:
            q3 = self.a4 * (s3 - self.l4)

        # VBA: s1_new = (1 - b1 * t) * s1 - q1 * t + r
        s1_new = (1 - self.b1 * t) * s1 - q1 * t + r

        # VBA: s2_new = (1 - b2 * t) * s2 - q2 * t + b1 * s1 * t
        s2_new = (1 - self.b2 * t) * s2 - q2 * t + self.b1 * s1 * t

        # VBA: s3_new = (1 - b3 * t) * s3 - q3 * t + b2 * s2 * t
        s3_new = (1 - self.b3 * t) * s3 - q3 * t + self.b2 * s2 * t

        # VBA: If s1_new < 0 Then s1_new = 0
        if s1_new < 0:
            s1_new = 0

        # VBA: If s2_new < 0 Then s2_new = 0
        if s2_new < 0:
            s2_new = 0

        # VBA: If s3_new < 0 Then s3_new = 0
        if s3_new < 0:
            s3_new = 0

        return s1_new, s2_new, s3_new

    def calc_rain_timelapse(self, mesh: Mesh, guidance_grib2: Dict[str, Any], data_key: str = 'data') -> List[GuidanceTimeSeries]:
        """
        降水量時系列計算（1時間雨量・3時間雨量共通）

        Args:
            mesh: メッシュデータ
            guidance_grib2: ガイダンスGRIB2データ
            data_key: 取得するデータのキー ('data', 'data_1h', 'data_3h')
        """
        try:
            # VBA: guidance_index = get_data_num(m.lat, m.lon, guidance_grib2.base_info)
            guidance_index = self.get_data_num(mesh.lat, mesh.lon, guidance_grib2['base_info'])

            # VBA配列は1-based、Pythonは0-basedなので変換
            python_index = guidance_index - 1

            # 指定されたデータキーのデータを取得
            if data_key not in guidance_grib2:
                logger.warning(f"Data key '{data_key}' not found in guidance_grib2")
                return []

            # VBA: ReDim rain_timeseries(UBound(guidance_grib2.data))
            rain_timeseries = []

            # VBA: For i = 1 To UBound(guidance_grib2.data)
            for i in range(len(guidance_grib2[data_key])):  # Python 0-based
                guidance_item = guidance_grib2[data_key][i]

                # VBA: rain_timeseries(i).ft = guidance_grib2.data(i).ft
                # VBA: rain_timeseries(i).value = guidance_grib2.data(i).value(guidance_index)
                if python_index < len(guidance_item['value']):
                    value = guidance_item['value'][python_index]
                    rain_timeseries.append(GuidanceTimeSeries(
                        ft=guidance_item['ft'],
                        value=value
                    ))

            return rain_timeseries

        except Exception as e:
            logger.error(f"Rain calculation error for mesh {mesh.code}: {e}")
            return []

    def calc_hourly_rain(self, rain_3h: List[GuidanceTimeSeries], rain_1h_max: List[GuidanceTimeSeries]) -> List[GuidanceTimeSeries]:
        """
        1時間ごとの雨量を推定

        前提:
        - 3時間の中央の1時間に最大1時間雨量が降る
        - 残りの雨量は前後1時間で半分ずつ分配

        Args:
            rain_3h: 3時間雨量時系列
            rain_1h_max: 3時間内の最大1時間雨量時系列

        Returns:
            1時間ごとの雨量時系列
        """
        try:
            hourly_rain = []

            # 各3時間期間を処理
            for i in range(len(rain_3h)):
                if i >= len(rain_1h_max):
                    break

                r3h = rain_3h[i].value
                r1h_max = rain_1h_max[i].value
                ft_base = rain_3h[i].ft

                # 残りの雨量を計算
                r_rest = max(0, r3h - r1h_max)
                r_half = r_rest / 2.0

                # FT=3の場合: 0-1時, 1-2時, 2-3時
                # 前1時間 (ft_base - 3 → ft_base - 2)
                hourly_rain.append(GuidanceTimeSeries(
                    ft=ft_base - 2,
                    value=r_half
                ))

                # 中央1時間（最大） (ft_base - 2 → ft_base - 1)
                hourly_rain.append(GuidanceTimeSeries(
                    ft=ft_base - 1,
                    value=r1h_max
                ))

                # 後1時間 (ft_base - 1 → ft_base)
                hourly_rain.append(GuidanceTimeSeries(
                    ft=ft_base,
                    value=r_half
                ))

            return hourly_rain

        except Exception as e:
            logger.error(f"Hourly rain calculation error: {e}")
            return []

    def calc_hourly_rain_uniform(
        self,
        rain_3h: List[GuidanceTimeSeries]
    ) -> List[GuidanceTimeSeries]:
        """
        3時間雨量を1時間ごとに均等按分する。
        """
        hourly_rain = []

        for rain_item in rain_3h:
            hourly_value = rain_item.value / 3.0
            ft_base = rain_item.ft
            hourly_rain.append(GuidanceTimeSeries(ft=ft_base - 2, value=hourly_value))
            hourly_rain.append(GuidanceTimeSeries(ft=ft_base - 1, value=hourly_value))
            hourly_rain.append(GuidanceTimeSeries(ft=ft_base, value=hourly_value))

        return hourly_rain

    def calc_swi_hourly(self, initial_swi: float, initial_first_tunk: float,
                        initial_second_tunk: float, initial_third_tunk: float,
                        hourly_rain: List[GuidanceTimeSeries]) -> List[SwiTimeSeries]:
        """
        1時間ごとの土壌雨量指数を計算

        Args:
            initial_swi: 初期SWI値
            initial_first_tunk: 初期第1タンク値
            initial_second_tunk: 初期第2タンク値
            initial_third_tunk: 初期第3タンク値
            hourly_rain: 1時間ごとの雨量時系列

        Returns:
            1時間ごとのSWI時系列
        """
        try:
            swi_hourly = []

            # 初期値（FT=0）
            swi_hourly.append(SwiTimeSeries(ft=0, value=initial_swi))

            # 現在のタンク状態
            current_first_tunk = initial_first_tunk
            current_second_tunk = initial_second_tunk
            current_third_tunk = initial_third_tunk

            # 1時間ごとに計算（dt=1時間）
            for rain_item in hourly_rain:
                # タンクモデル計算（1時間ステップ）
                tmp_f, tmp_s, tmp_t = self.calc_tunk_model(
                    current_first_tunk,
                    current_second_tunk,
                    current_third_tunk,
                    1,  # 1時間
                    rain_item.value
                )

                # SWI = 3つのタンクの合計
                swi_value = tmp_f + tmp_s + tmp_t
                swi_hourly.append(SwiTimeSeries(
                    ft=rain_item.ft,
                    value=swi_value
                ))

                # タンク状態を更新
                current_first_tunk = tmp_f
                current_second_tunk = tmp_s
                current_third_tunk = tmp_t

            return swi_hourly

        except Exception as e:
            logger.error(f"Hourly SWI calculation error: {e}")
            return []

    def calc_hourly_risk(self, swi_hourly: List[SwiTimeSeries],
                         advisary_bound: int, warning_bound: int,
                         dosyakei_bound: int,
                         rain_hourly: Optional[List[GuidanceTimeSeries]] = None,
                         level4_curve=None,
                         risk_rule: str = "legacy") -> List[Risk]:
        """
        1時間ごとの危険度を判定

        Args:
            swi_hourly: 1時間ごとのSWI時系列
            advisary_bound: 注意報基準値
            warning_bound: 警報基準値
            dosyakei_bound: 土砂災害基準値

        Returns:
            1時間ごとのリスク時系列
        """
        try:
            risk_hourly = []
            normalized_risk_rule = self.normalize_risk_rule(risk_rule)
            rain_by_ft = {
                int(rain.ft): float(rain.value)
                for rain in (rain_hourly or [])
            }

            for swi_item in swi_hourly:
                swi_value = swi_item.value
                rain_value = rain_by_ft.get(int(swi_item.ft), 0.0)
                level4_threshold = self.get_level4_threshold(
                    level4_curve,
                    rain_value,
                    dosyakei_bound,
                )

                # リスクレベル判定（政府ガイドライン準拠: レベル0,2,3,4）
                if level4_threshold is not None and swi_value >= level4_threshold:
                    risk = 4  # レベル4: 土砂災害
                elif swi_value >= warning_bound:
                    risk = 3  # レベル3: 警報
                elif swi_value >= advisary_bound:
                    risk = 2  # レベル2: 注意
                else:
                    risk = 0  # レベル0: 正常

                risk_hourly.append(Risk(ft=swi_item.ft, value=risk))

            return self.apply_risk_rule_to_hourly(risk_hourly, normalized_risk_rule)

        except Exception as e:
            logger.error(f"Hourly risk calculation error: {e}")
            return []

    def apply_risk_rule_to_hourly(
        self,
        risk_hourly: List[Risk],
        risk_rule: str = "legacy"
    ) -> List[Risk]:
        """1時間危険度系列へ危険度ルールを適用する。"""
        try:
            normalized_risk_rule = self.normalize_risk_rule(risk_rule)

            if normalized_risk_rule == "legacy" or not risk_hourly:
                return risk_hourly

            adjusted = [Risk(ft=risk.ft, value=risk.value) for risk in risk_hourly]

            first_level4_index = next(
                (index for index, risk in enumerate(adjusted) if risk.value >= 4),
                None,
            )

            if first_level4_index is None:
                return adjusted

            last_level4_index = max(
                index for index, risk in enumerate(adjusted) if risk.value >= 4
            )
            level3_start = max(0, first_level4_index - 3)

            for index in range(level3_start, first_level4_index):
                adjusted[index].value = 3

            for index in range(first_level4_index, last_level4_index + 1):
                adjusted[index].value = 4

            return adjusted

        except Exception as e:
            logger.error(f"Risk rule application error: {e}")
            return []

    def calc_3hour_max_risk_from_hourly(self, risk_hourly: List[Risk]) -> List[Risk]:
        """
        1時間ごとの危険度から3時間ごとの最大危険度を算出

        Args:
            risk_hourly: 1時間ごとのリスク時系列

        Returns:
            3時間ごとの最大リスク時系列
        """
        try:
            risk_3hour_max = []

            if not risk_hourly:
                return risk_3hour_max

            # FT=0の初期値を処理（guidance_data_3hがFT=3から始まる場合、rain_1hourはFT=1から始まるため、
            # swi_hourlyは(0:初期値, 1, 2, 3, ...)となる。FT=0は単独で処理する）
            if risk_hourly[0].ft == 0:
                risk_3hour_max.append(Risk(ft=0, value=risk_hourly[0].value))
                remaining = risk_hourly[1:]
            else:
                remaining = risk_hourly

            # 残りを3つずつグループ化して最大値を取得
            # FT=1,2,3 → FT=3, FT=4,5,6 → FT=6, FT=7,8,9 → FT=9, ...
            for i in range(0, len(remaining), 3):
                group = remaining[i:i+3]
                if not group:
                    continue

                # 最大リスクを計算
                max_risk = max(r.value for r in group)

                # 3時間期間の終了時刻（最後の要素のFT）を代表値とする
                # これにより、FT=1,2,3のグループはFT=3として保存される
                ft_end = group[-1].ft

                risk_3hour_max.append(Risk(ft=ft_end, value=max_risk))

            return risk_3hour_max

        except Exception as e:
            logger.error(f"3-hour max risk calculation error: {e}")
            return []

    def calc_swi_timelapse(self, mesh: Mesh, swi_grib2: Dict[str, Any], guidance_grib2: Dict[str, Any]) -> List[SwiTimeSeries]:
        """
        VBA Function calc_swi_timelapse の完全再現
        """
        try:
            # VBA: swi_index = get_data_num(m.lat, m.lon, swi_grib2.base_info)
            swi_index = self.get_data_num(mesh.lat, mesh.lon, swi_grib2['base_info'])
            guidance_index = self.get_data_num(mesh.lat, mesh.lon, guidance_grib2['base_info'])

            # VBA配列は1-based、Pythonは0-basedなので変換
            python_swi_index = swi_index - 1

            if (python_swi_index >= len(swi_grib2['swi']) or
                python_swi_index >= len(swi_grib2['first_tunk']) or
                python_swi_index >= len(swi_grib2['second_tunk'])):
                return []

            # VBA: swi = swi_grib2.swi(swi_index) / 10
            swi = swi_grib2['swi'][python_swi_index] / 10

            # VBA: first_tunk = swi_grib2.first_tunk(swi_index) / 10
            first_tunk = swi_grib2['first_tunk'][python_swi_index] / 10

            # VBA: second_tunk = swi_grib2.second_tunk(swi_index) / 10
            second_tunk = swi_grib2['second_tunk'][python_swi_index] / 10

            # VBA: third_tunk = swi - first_tunk - second_tunk
            third_tunk = swi - first_tunk - second_tunk

            # guidance_indexは上で既に計算済み
            python_guidance_index = guidance_index - 1
            rain_3hour = []
            for i in range(len(guidance_grib2['data'])):
                guidance_item = guidance_grib2['data'][i]
                if python_guidance_index < len(guidance_item['value']):
                    rain_3hour.append(
                        GuidanceTimeSeries(
                            ft=guidance_item['ft'],
                            value=guidance_item['value'][python_guidance_index],
                        )
                    )

            hourly_rain_uniform = self.calc_hourly_rain_uniform(rain_3hour)
            swi_hourly = self.calc_swi_hourly(
                swi,
                first_tunk,
                second_tunk,
                third_tunk,
                hourly_rain_uniform,
            )

            swi_by_ft = {point.ft: point.value for point in swi_hourly}
            swi_time_series = [SwiTimeSeries(ft=0, value=swi)]
            for rain_item in rain_3hour:
                if rain_item.ft in swi_by_ft:
                    swi_time_series.append(
                        SwiTimeSeries(ft=rain_item.ft, value=swi_by_ft[rain_item.ft])
                    )

            return swi_time_series

        except Exception as e:
            logger.error(f"SWI calculation error for mesh {mesh.code}: {e}")
            return []

    def calc_risk_timeline(self, meshes: List[Mesh], risk_rule: str = "legacy") -> List[Risk]:
        """
        VBA Function calc_risk_timeline の完全再現
        リスクレベル計算
        """
        try:
            # 詳細デバッグログ
            logger.info(f"=== calc_risk_timeline called with {len(meshes) if isinstance(meshes, list) else 'invalid'} meshes ===")

            # 入力データ型の確認
            if not isinstance(meshes, list):
                logger.error(f"Risk calculation error: meshes is not a list, got {type(meshes)}")
                return []

            if not meshes:
                logger.error("Risk calculation error: meshes list is empty")
                return []

            # 最初のメッシュのSWIデータ確認
            first_mesh = meshes[0]
            logger.info(f"First mesh: code={getattr(first_mesh, 'code', 'no code')}, has swi attr: {hasattr(first_mesh, 'swi')}")

            if not hasattr(first_mesh, 'swi') or not first_mesh.swi:
                logger.error(f"Risk calculation error: first mesh has no swi data. Has swi attr: {hasattr(first_mesh, 'swi')}, swi length: {len(first_mesh.swi) if hasattr(first_mesh, 'swi') and first_mesh.swi else 0}")
                return []

            # 時系列の長さを取得
            timeline_length = len(first_mesh.swi)
            logger.info(f"Timeline length: {timeline_length}")
            logger.info(f"First mesh boundaries: advisory={getattr(first_mesh, 'advisary_bound', 'N/A')}, warning={getattr(first_mesh, 'warning_bound', 'N/A')}, dosyakei={getattr(first_mesh, 'dosyakei_bound', 'N/A')}")
            logger.info(f"First 3 SWI values: {[first_mesh.swi[i].value for i in range(min(3, timeline_length))]}")

            normalized_risk_rule = self.normalize_risk_rule(risk_rule)
            risk_timeline = []

            for t in range(timeline_length):
                ft = first_mesh.swi[t].ft
                max_risk = 0

                for mesh in meshes:
                    mesh_risk_3hour_max = getattr(mesh, 'risk_3hour_max', None)
                    if mesh_risk_3hour_max:
                        matching_point = next((point for point in mesh_risk_3hour_max if point.ft == ft), None)
                        if matching_point is not None:
                            max_risk = max(max_risk, matching_point.value)
                            continue

                    if not hasattr(mesh, 'swi') or not mesh.swi:
                        continue

                    if t < len(mesh.swi):
                        swi_value = mesh.swi[t].value

                        # リスクレベル判定（政府ガイドライン準拠: レベル0,2,3,4）
                        if swi_value >= mesh.dosyakei_bound:
                            risk = 4  # レベル4: 土砂災害
                        elif swi_value >= mesh.warning_bound:
                            risk = 3  # レベル3: 警報
                        elif swi_value >= mesh.advisary_bound:
                            risk = 2  # レベル2: 注意
                        else:
                            risk = 0  # レベル0: 正常

                        max_risk = max(max_risk, risk)

                risk_timeline.append(Risk(ft=ft, value=max_risk))

            logger.info(f"Risk timeline calculated: {len(risk_timeline)} entries")
            if risk_timeline:
                logger.info(f"First 3 risk values: {[(r.ft, r.value) for r in risk_timeline[:3]]}")

            return risk_timeline

        except Exception as e:
            logger.error(f"Risk calculation error: {e}")
            logger.error(f"meshes type: {type(meshes)}")
            if isinstance(meshes, list) and meshes:
                logger.error(f"first mesh type: {type(meshes[0])}")
            import traceback
            logger.error(f"Risk calculation traceback: {traceback.format_exc()}")
            return []

    def process_mesh_calculations(
        self,
        mesh: Mesh,
        swi_grib2: Dict[str, Any],
        guidance_grib2: Dict[str, Any],
        risk_rule: str = "legacy"
    ) -> Mesh:
        """
        VBA calc_data の一部処理
        単一メッシュの計算を実行（全雨量・SWI・危険度）
        """
        try:
            # 3時間ごとのSWI計算
            mesh.swi = self.calc_swi_timelapse(mesh, swi_grib2, guidance_grib2)

            # 3時間内の最大1時間雨量の計算
            mesh.rain_1hour_max = self.calc_rain_timelapse(mesh, guidance_grib2, data_key='data_1h')

            # 3時間雨量の計算
            mesh.rain_3hour = self.calc_rain_timelapse(mesh, guidance_grib2, data_key='data_3h')

            # 1時間ごとの雨量を推定
            mesh.rain_1hour = self.calc_hourly_rain(mesh.rain_3hour, mesh.rain_1hour_max)

            # 初期タンク値を取得（GRIB2データから）
            swi_index = self.get_data_num(mesh.lat, mesh.lon, swi_grib2['base_info'])
            python_swi_index = swi_index - 1

            if (python_swi_index < len(swi_grib2['swi']) and
                python_swi_index < len(swi_grib2['first_tunk']) and
                python_swi_index < len(swi_grib2['second_tunk'])):

                initial_swi = swi_grib2['swi'][python_swi_index] / 10
                initial_first_tunk = swi_grib2['first_tunk'][python_swi_index] / 10
                initial_second_tunk = swi_grib2['second_tunk'][python_swi_index] / 10
                initial_third_tunk = initial_swi - initial_first_tunk - initial_second_tunk

                # メッシュ50357712のデバッグログ（計算前）
                if mesh.code == '50357712':
                    logger.info(f"[DEBUG] Mesh {mesh.code} rain_1hour FTs: {[r.ft for r in mesh.rain_1hour[:6]]}")
                    logger.info(f"[DEBUG] Mesh {mesh.code} initial_swi: {initial_swi}, advisary: {mesh.advisary_bound}")

                # 1時間ごとのSWI計算
                mesh.swi_hourly = self.calc_swi_hourly(
                    initial_swi,
                    initial_first_tunk,
                    initial_second_tunk,
                    initial_third_tunk,
                    mesh.rain_1hour
                )

                # メッシュ50357712のデバッグログ（SWI計算後）
                if mesh.code == '50357712':
                    logger.info(f"[DEBUG] Mesh {mesh.code} swi_hourly: {[(s.ft, round(s.value, 1)) for s in mesh.swi_hourly[:6]]}")

                # 1時間ごとの危険度計算
                mesh.risk_hourly = self.calc_hourly_risk(
                    mesh.swi_hourly,
                    mesh.advisary_bound,
                    mesh.warning_bound,
                    mesh.dosyakei_bound,
                    rain_hourly=mesh.rain_1hour,
                    level4_curve=getattr(mesh, 'level4_curve', None),
                    risk_rule=risk_rule,
                )

                # メッシュ50357712のデバッグログ（risk_hourly計算後）
                if mesh.code == '50357712':
                    logger.info(f"[DEBUG] Mesh {mesh.code} risk_hourly: {[(r.ft, r.value) for r in mesh.risk_hourly[:9]]}")

                # 3時間ごとの最大危険度計算（1時間雨量ベース）
                mesh.risk_3hour_max = self.calc_3hour_max_risk_from_hourly(mesh.risk_hourly)

                # メッシュ50357712のデバッグログ（risk_3hour_max計算後）
                if mesh.code == '50357712':
                    logger.info(f"[DEBUG] Mesh {mesh.code} risk_3hour_max: {[(r.ft, r.value) for r in mesh.risk_3hour_max[:5]]}")

            return mesh

        except Exception as e:
            logger.error(f"Mesh calculations error: {e}")
            return mesh

    def recalculate_swi_and_risk(self, mesh: Mesh, risk_rule: str = "legacy") -> Mesh:
        """
        雨量データは既に調整済みという前提で、SWIと危険度のみ再計算

        Args:
            mesh: 調整済み雨量データを持つメッシュ

        Returns:
            再計算されたメッシュ
        """
        try:
            # 既存のSWI初期値を使用（最初のSWI値から逆算）
            if mesh.swi and len(mesh.swi) > 0:
                initial_swi = mesh.swi[0].value

                # タンク値の推定（簡易版：均等分割）
                # より正確にはSWIデータから取得すべきだが、
                # 調整後の再計算では元の初期値を保持していると仮定
                initial_first_tunk = initial_swi * 0.4
                initial_second_tunk = initial_swi * 0.3
                initial_third_tunk = initial_swi * 0.3

                # 1時間ごとのSWI再計算
                mesh.swi_hourly = self.calc_swi_hourly(
                    initial_swi,
                    initial_first_tunk,
                    initial_second_tunk,
                    initial_third_tunk,
                    mesh.rain_1hour
                )

                # 1時間ごとの危険度再計算
                mesh.risk_hourly = self.calc_hourly_risk(
                    mesh.swi_hourly,
                    mesh.advisary_bound,
                    mesh.warning_bound,
                    mesh.dosyakei_bound,
                    rain_hourly=mesh.rain_1hour,
                    level4_curve=getattr(mesh, 'level4_curve', None),
                    risk_rule=risk_rule,
                )

                # 3時間ごとの最大危険度再計算
                mesh.risk_3hour_max = self.calc_3hour_max_risk_from_hourly(mesh.risk_hourly)

                hourly_rain_uniform = self.calc_hourly_rain_uniform(mesh.rain_3hour)
                swi_hourly_uniform = self.calc_swi_hourly(
                    initial_swi,
                    initial_first_tunk,
                    initial_second_tunk,
                    initial_third_tunk,
                    hourly_rain_uniform
                )
                swi_by_ft = {point.ft: point.value for point in swi_hourly_uniform}
                mesh.swi = [SwiTimeSeries(ft=0, value=initial_swi)]
                for rain_point in mesh.rain_3hour:
                    if rain_point.ft in swi_by_ft:
                        mesh.swi.append(
                            SwiTimeSeries(ft=rain_point.ft, value=swi_by_ft[rain_point.ft])
                        )

            return mesh

        except Exception as e:
            logger.error(f"SWI recalculation error: {e}")
            return mesh

    def process_area_calculations(self, areas: List[Area], risk_rule: str = "legacy") -> None:
        """
        VBA calc_data の一部処理
        各エリアのリスク計算を実行
        """
        try:
            for area in areas:
                # VBA: prefectures(i).areas(j).risk_timeline = calc_risk_timeline(prefectures(i).areas(j).meshes)
                area.risk_timeline = self.calc_risk_timeline(area.meshes, risk_rule=risk_rule)

        except Exception as e:
            logger.error(f"Area calculations error: {e}")

    # 既存の互換性のため、古いメソッド名も保持
    def calc_tunk_model_legacy(self, s1: float, s2: float, s3: float, dt: float, r: float) -> Tuple[float, float, float]:
        """既存コードとの互換性のため"""
        return self.calc_tunk_model(s1, s2, s3, dt, r)

    def calc_secondary_subdivision_aggregates(self, subdivision: SecondarySubdivision):
        """
        二次細分内の集約データを計算
        - 最大1時間雨量タイムライン
        - 最大3時間雨量タイムライン
        - 最大リスクタイムライン
        """
        try:
            if not subdivision.areas:
                return

            # 全メッシュを収集
            all_meshes = []
            for area in subdivision.areas:
                all_meshes.extend(area.meshes)

            if not all_meshes:
                return

            # 汎用集約メソッドを使用
            subdivision.rain_1hour_max_timeline = self.aggregation_service.aggregate_timeline(
                all_meshes, 'rain_1hour_max', GuidanceTimeSeries
            )
            subdivision.rain_3hour_timeline = self.aggregation_service.aggregate_timeline(
                all_meshes, 'rain_3hour', GuidanceTimeSeries
            )
            subdivision.risk_timeline = self.aggregation_service.aggregate_area_risk_timeline(
                subdivision.areas
            )

        except Exception as e:
            logger.error(f"二次細分集約エラー ({subdivision.name}): {e}")

    def calc_prefecture_aggregates(self, prefecture: Prefecture):
        """
        府県全体の集約データを計算
        - 最大1時間雨量タイムライン
        - 最大3時間雨量タイムライン
        - 最大リスクタイムライン
        """
        try:
            # 全メッシュを収集
            all_meshes = []
            for area in prefecture.areas:
                all_meshes.extend(area.meshes)

            if not all_meshes:
                return

            # 汎用集約メソッドを使用
            prefecture.prefecture_rain_1hour_max_timeline = self.aggregation_service.aggregate_timeline(
                all_meshes, 'rain_1hour_max', GuidanceTimeSeries
            )
            prefecture.prefecture_rain_3hour_timeline = self.aggregation_service.aggregate_timeline(
                all_meshes, 'rain_3hour', GuidanceTimeSeries
            )
            prefecture.prefecture_risk_timeline = self.aggregation_service.aggregate_area_risk_timeline(
                prefecture.areas
            )

        except Exception as e:
            logger.error(f"府県集約エラー ({prefecture.name}): {e}")
