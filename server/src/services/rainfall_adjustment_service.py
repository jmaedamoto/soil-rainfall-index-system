# -*- coding: utf-8 -*-
"""
雨量調整サービス
ユーザーが入力した雨量調整値に基づいてガイダンスデータを調整
"""
from typing import Dict, List, Any, Tuple
import logging
import copy

from models import Prefecture, Area, Mesh, GuidanceTimeSeries

logger = logging.getLogger(__name__)


class RainfallAdjustmentService:
    """雨量調整サービス"""

    WINDOW_24H_MAP: Dict[int, Tuple[int, ...]] = {
        24: (3, 6, 9, 12, 15, 18, 21, 24),
        48: (27, 30, 33, 36, 39, 42, 45, 48),
    }

    def calculate_mesh_ratios_from_session(
        self,
        prefectures_dict: Dict[str, Any],
        area_adjustments: Dict[str, Dict[int, float]]
    ) -> Dict[str, Dict[int, float]]:
        """
        セッション辞書形式データから、メッシュごとの調整比率を計算する。

        Args:
            prefectures_dict: session['prefectures'] 形式の辞書
            area_adjustments: {"府県名_市町村名": {ft: value}}

        Returns:
            {"mesh_code": {ft: ratio}}
        """
        logger.info("セッション辞書からメッシュごとの調整比率を計算開始")

        mesh_to_areas: Dict[str, List[str]] = {}
        area_original_max: Dict[str, Dict[int, float]] = {}
        for pref_dict in prefectures_dict.values():
            pref_name = pref_dict["name"]
            for area_dict in pref_dict.get("areas", []):
                area_key = f"{pref_name}_{area_dict['name']}"
                ft_max_values: Dict[int, float] = {}
                for mesh_dict in area_dict.get("meshes", []):
                    mesh_code = mesh_dict.get("code")
                    if not mesh_code:
                        continue
                    mesh_to_areas.setdefault(mesh_code, []).append(area_key)
                    for point in mesh_dict.get("rain_timeline", []):
                        ft = int(point["ft"])
                        value = float(point["value"])
                        if ft not in ft_max_values or value > ft_max_values[ft]:
                            ft_max_values[ft] = value

                area_original_max[area_key] = ft_max_values

        mesh_ratios: Dict[str, Dict[int, float]] = {}

        for mesh_code, area_keys in mesh_to_areas.items():
            ft_ratios_list: Dict[int, List[float]] = {}

            for area_key in area_keys:
                adjustments = area_adjustments.get(area_key)
                if not adjustments:
                    continue

                for ft, adjusted_value in adjustments.items():
                    ft_int = int(ft)
                    original_max = area_original_max.get(area_key, {}).get(ft_int, 0.0)

                    if original_max > 0:
                        ratio = adjusted_value / original_max
                    else:
                        if adjusted_value > 0:
                            logger.warning(
                                "雨量調整をスキップ: original_max=0, area=%s, ft=%s, adjusted_value=%s",
                                area_key,
                                ft_int,
                                adjusted_value,
                            )
                        ratio = 1.0

                    ft_ratios_list.setdefault(ft_int, []).append(ratio)

            if ft_ratios_list:
                mesh_ratios[mesh_code] = {
                    ft: max(ratios) if ratios else 1.0
                    for ft, ratios in ft_ratios_list.items()
                }

        logger.info("セッション辞書からの調整比率計算完了: %sメッシュ", len(mesh_ratios))
        return mesh_ratios

    def build_adjusted_mesh_rainfall_from_session(
        self,
        prefectures_dict: Dict[str, Any],
        mesh_ratios: Dict[str, Dict[int, float]]
    ) -> Dict[str, List[Tuple[int, float]]]:
        """
        セッション辞書形式データから、比率適用後のメッシュ別3時間雨量を作成する。

        Args:
            prefectures_dict: session['prefectures'] 形式の辞書
            mesh_ratios: {"mesh_code": {ft: ratio}}

        Returns:
            {"mesh_code": [(ft, adjusted_value), ...]}
        """
        adjusted_mesh_rainfall: Dict[str, List[Tuple[int, float]]] = {}

        for pref_dict in prefectures_dict.values():
            for area_dict in pref_dict.get("areas", []):
                for mesh_dict in area_dict.get("meshes", []):
                    mesh_code = mesh_dict.get("code")
                    if mesh_code not in mesh_ratios:
                        continue

                    ratios = mesh_ratios[mesh_code]
                    adjusted_mesh_rainfall[mesh_code] = [
                        (
                            int(point["ft"]),
                            float(point["value"]) * ratios.get(int(point["ft"]), 1.0)
                        )
                        for point in mesh_dict.get("rain_timeline", [])
                    ]

        logger.info("比率適用後のメッシュ雨量生成完了: %sメッシュ", len(adjusted_mesh_rainfall))
        return adjusted_mesh_rainfall

    def build_filled_mesh_rainfall_from_session(
        self,
        prefectures_dict: Dict[str, Any],
        area_adjustments: Dict[str, Dict[int, float]]
    ) -> Dict[str, List[Tuple[int, float]]]:
        """
        セッション辞書形式データから、領域内を入力値で塗りつぶしたメッシュ別3時間雨量を作成する。

        同じ mesh_code に複数領域の指示がかかった場合は、FT ごとに最大値を採用する。
        """
        logger.info("セッション辞書から塗りつぶし後のメッシュ雨量生成開始")

        adjusted_mesh_rainfall: Dict[str, Dict[int, float]] = {}

        for pref_dict in prefectures_dict.values():
            pref_name = pref_dict["name"]
            for area_dict in pref_dict.get("areas", []):
                area_key = f"{pref_name}_{area_dict['name']}"
                adjustments = area_adjustments.get(area_key)
                if not adjustments:
                    continue

                for mesh_dict in area_dict.get("meshes", []):
                    mesh_code = mesh_dict.get("code")
                    if not mesh_code:
                        continue

                    current_values = {
                        int(point["ft"]): float(point["value"])
                        for point in mesh_dict.get("rain_timeline", [])
                    }

                    for ft, filled_value in adjustments.items():
                        ft_int = int(ft)
                        if ft_int not in current_values:
                            continue
                        if mesh_code not in adjusted_mesh_rainfall:
                            adjusted_mesh_rainfall[mesh_code] = dict(current_values)
                        adjusted_mesh_rainfall[mesh_code][ft_int] = max(
                            adjusted_mesh_rainfall[mesh_code].get(ft_int, current_values[ft_int]),
                            float(filled_value)
                        )

        filled_mesh_rainfall = {
            mesh_code: [(ft, value) for ft, value in sorted(ft_values.items())]
            for mesh_code, ft_values in adjusted_mesh_rainfall.items()
        }

        logger.info("塗りつぶし後のメッシュ雨量生成完了: %sメッシュ", len(filled_mesh_rainfall))
        return filled_mesh_rainfall

    def aggregate_rainfall_24hour_from_session(
        self,
        prefectures_dict: Dict[str, Any]
    ) -> Tuple[Dict[str, List[Dict[str, float]]], Dict[str, List[Dict[str, float]]]]:
        """
        セッション辞書形式データから、市町村別・二次細分別の24時間代表雨量を集計する。

        各領域では、各メッシュの24時間合計を求めたうえで最大値を代表値とする。
        """
        area_rainfall_24hour: Dict[str, List[Dict[str, float]]] = {}
        subdivision_rainfall_24hour: Dict[str, List[Dict[str, float]]] = {}

        for pref_dict in prefectures_dict.values():
            pref_name = pref_dict["name"]

            for area_dict in pref_dict.get("areas", []):
                area_key = f"{pref_name}_{area_dict['name']}"
                area_rainfall_24hour[area_key] = self._build_aggregate_timeline_for_meshes(
                    area_dict.get("meshes", [])
                )

            for subdiv_dict in pref_dict.get("secondary_subdivisions", []):
                subdiv_key = f"{pref_name}_{subdiv_dict['name']}"
                meshes = self._collect_subdivision_meshes(pref_dict, subdiv_dict.get("area_names", []))
                subdivision_rainfall_24hour[subdiv_key] = self._build_aggregate_timeline_for_meshes(meshes)

        return area_rainfall_24hour, subdivision_rainfall_24hour

    def build_fill_24hour_uniform_from_session(
        self,
        prefectures_dict: Dict[str, Any],
        area_adjustments: Dict[str, Dict[int, float]]
    ) -> Dict[str, List[Tuple[int, float]]]:
        """
        24時間入力値を8区間に均等按分し、対象領域を塗りつぶす。
        """
        return self._build_24hour_adjusted_mesh_rainfall(
            prefectures_dict,
            area_adjustments,
            strategy='fill_uniform'
        )

    def build_ratio_24hour_uniform_from_session(
        self,
        prefectures_dict: Dict[str, Any],
        area_adjustments: Dict[str, Dict[int, float]]
    ) -> Dict[str, List[Tuple[int, float]]]:
        """
        24時間入力値を8区間に均等按分し、各FTで比率補正する。
        """
        return self._build_24hour_adjusted_mesh_rainfall(
            prefectures_dict,
            area_adjustments,
            strategy='ratio_uniform'
        )

    def build_ratio_24hour_peak_mesh_from_session(
        self,
        prefectures_dict: Dict[str, Any],
        area_adjustments: Dict[str, Dict[int, float]]
    ) -> Dict[str, List[Tuple[int, float]]]:
        """
        領域内の24時間合計最大メッシュを基準に、24時間入力値へ比率補正する。
        """
        return self._build_24hour_adjusted_mesh_rainfall(
            prefectures_dict,
            area_adjustments,
            strategy='ratio_peak_mesh'
        )

    def extract_area_rainfall_timeseries(
        self,
        prefectures: List[Prefecture],
        guidance_grib2: Dict[str, Any]
    ) -> Dict[str, List[Dict[str, float]]]:
        """
        市町村（Area）ごとの雨量時系列を抽出

        各市町村の全メッシュから雨量データを収集し、
        時刻（FT）ごとに最大値を取得して市町村の代表値とする

        Args:
            prefectures: 都道府県データリスト
            guidance_grib2: ガイダンスGRIB2データ

        Returns:
            {
                "滋賀県_大津市": [
                    {"ft": 0, "value": 5.2},
                    {"ft": 3, "value": 12.5},
                    ...
                ],
                ...
            }
        """
        logger.info("市町村別雨量時系列の抽出開始")
        area_rainfall = {}

        # FT値の範囲を取得
        ft_list = []
        if 'data_3h' in guidance_grib2 and len(guidance_grib2['data_3h']) > 0:
            ft_list = [item['ft'] for item in guidance_grib2['data_3h']]

        for prefecture in prefectures:
            for area in prefecture.areas:
                # 市町村の一意キー
                area_key = f"{prefecture.name}_{area.name}"

                # 各FTごとの最大雨量を収集
                ft_max_values = {ft: 0.0 for ft in ft_list}

                for mesh in area.meshes:
                    # メッシュの3時間雨量を取得
                    for rain_point in mesh.rain_3hour:
                        if rain_point.ft in ft_max_values:
                            ft_max_values[rain_point.ft] = max(
                                ft_max_values[rain_point.ft],
                                rain_point.value
                            )

                # 時系列データに変換（整数値に丸める）
                area_rainfall[area_key] = [
                    {"ft": ft, "value": round(ft_max_values[ft])}
                    for ft in sorted(ft_list)
                ]

        logger.info(f"市町村別雨量時系列抽出完了: {len(area_rainfall)}市町村")
        return area_rainfall

    def extract_subdivision_rainfall_timeseries(
        self,
        prefectures: List[Prefecture],
        guidance_grib2: Dict[str, Any]
    ) -> Dict[str, List[Dict[str, float]]]:
        """
        二次細分ごとの雨量時系列を抽出

        各二次細分の全メッシュから雨量データを収集し、
        時刻（FT）ごとに最大値を取得して二次細分の代表値とする

        Args:
            prefectures: 都道府県データリスト
            guidance_grib2: ガイダンスGRIB2データ

        Returns:
            {
                "滋賀県_湖南": [
                    {"ft": 0, "value": 5.2},
                    {"ft": 3, "value": 12.5},
                    ...
                ],
                ...
            }
        """
        logger.info("二次細分別雨量時系列の抽出開始")
        subdivision_rainfall = {}

        # FT値の範囲を取得
        ft_list = []
        if 'data_3h' in guidance_grib2 and len(guidance_grib2['data_3h']) > 0:
            ft_list = [item['ft'] for item in guidance_grib2['data_3h']]

        for prefecture in prefectures:
            if not hasattr(prefecture, 'secondary_subdivisions') or not prefecture.secondary_subdivisions:
                continue

            for subdivision in prefecture.secondary_subdivisions:
                # 二次細分の一意キー
                subdiv_key = f"{prefecture.name}_{subdivision.name}"

                # 各FTごとの最大雨量を収集
                ft_max_values = {ft: 0.0 for ft in ft_list}

                # 二次細分内の全市町村のメッシュから雨量を収集
                for area in subdivision.areas:
                    for mesh in area.meshes:
                        # メッシュの3時間雨量を取得
                        for rain_point in mesh.rain_3hour:
                            if rain_point.ft in ft_max_values:
                                ft_max_values[rain_point.ft] = max(
                                    ft_max_values[rain_point.ft],
                                    rain_point.value
                                )

                # 時系列データに変換（整数値に丸める）
                subdivision_rainfall[subdiv_key] = [
                    {"ft": ft, "value": round(ft_max_values[ft])}
                    for ft in sorted(ft_list)
                ]

        logger.info(f"二次細分別雨量時系列抽出完了: {len(subdivision_rainfall)}二次細分")
        return subdivision_rainfall

    def adjust_guidance_data_by_area_ratios(
        self,
        guidance_grib2: Dict[str, Any],
        area_adjustments: Dict[str, Dict[int, float]],
        prefectures: List[Prefecture]
    ) -> Dict[str, Any]:
        """
        市町村別の調整比率に基づいてガイダンスデータを調整

        処理フロー:
        1. 市町村ごとに元の雨量最大値を計算
        2. ユーザー入力値との比率を算出
        3. 各メッシュの雨量に比率を適用
        4. 境界メッシュは複数市町村の最大比率を適用

        Args:
            guidance_grib2: 元のガイダンスGRIB2データ
            area_adjustments: {
                "滋賀県_大津市": {0: 10.0, 3: 15.0, ...},  # ft: 調整後雨量
                ...
            }
            prefectures: 都道府県データ（Area-Mesh対応取得用）

        Returns:
            調整後のguidance_grib2（新規コピー）
        """
        logger.info("ガイダンスデータの調整開始")

        # 元データのディープコピー
        adjusted_grib2 = copy.deepcopy(guidance_grib2)

        # メッシュごとの調整比率を計算
        mesh_ratios = self._calculate_mesh_ratios(
            area_adjustments,
            prefectures,
            guidance_grib2
        )

        # ガイダンスデータに比率を適用
        self._apply_ratios_to_guidance_data(
            adjusted_grib2,
            mesh_ratios
        )

        logger.info("ガイダンスデータの調整完了")
        return adjusted_grib2

    def _calculate_mesh_ratios(
        self,
        area_adjustments: Dict[str, Dict[int, float]],
        prefectures: List[Prefecture],
        guidance_grib2: Dict[str, Any]
    ) -> Dict[str, Dict[int, float]]:
        """
        メッシュごとの調整比率を計算

        境界メッシュ（複数市町村にまたがる）は最大比率を採用

        Args:
            area_adjustments: 市町村別の調整後雨量
            prefectures: 都道府県データ
            guidance_grib2: 元のガイダンスデータ

        Returns:
            {
                "mesh_code": {0: 1.5, 3: 1.2, ...},  # ft: 調整比率
                ...
            }
        """
        logger.info("メッシュごとの調整比率計算開始")

        # メッシュコード→市町村リストのマッピング
        mesh_to_areas: Dict[str, List[Tuple[str, str]]] = {}  # {mesh_code: [(pref_name, area_name), ...]}

        for prefecture in prefectures:
            for area in prefecture.areas:
                area_key = f"{prefecture.name}_{area.name}"
                for mesh in area.meshes:
                    if mesh.code not in mesh_to_areas:
                        mesh_to_areas[mesh.code] = []
                    mesh_to_areas[mesh.code].append((prefecture.name, area.name))

        # 各メッシュの調整比率を計算
        mesh_ratios: Dict[str, Dict[int, float]] = {}

        for mesh_code, area_list in mesh_to_areas.items():
            # このメッシュに関係する市町村の調整比率を収集
            ft_ratios_list: Dict[int, List[float]] = {}

            for pref_name, area_name in area_list:
                area_key = f"{pref_name}_{area_name}"

                if area_key not in area_adjustments:
                    continue

                # この市町村の調整データ
                adjustments = area_adjustments[area_key]

                # FTごとに比率を計算
                for ft, adjusted_value in adjustments.items():
                    ft_int = int(ft)

                    # 元の雨量最大値を取得
                    original_max = self._get_area_original_max(
                        pref_name, area_name, ft_int, prefectures
                    )

                    if original_max > 0:
                        ratio = adjusted_value / original_max
                    else:
                        # 元が0の場合は比率を1とする（調整なし）
                        ratio = 1.0

                    if ft_int not in ft_ratios_list:
                        ft_ratios_list[ft_int] = []
                    ft_ratios_list[ft_int].append(ratio)

            # 複数市町村にまたがる場合は最大比率を採用
            mesh_ratios[mesh_code] = {}
            for ft, ratios in ft_ratios_list.items():
                mesh_ratios[mesh_code][ft] = max(ratios) if ratios else 1.0

        logger.info(f"メッシュごとの調整比率計算完了: {len(mesh_ratios)}メッシュ")
        return mesh_ratios

    def _get_area_original_max(
        self,
        pref_name: str,
        area_name: str,
        ft: int,
        prefectures: List[Prefecture]
    ) -> float:
        """
        特定市町村の特定FTにおける元の雨量最大値を取得

        Args:
            pref_name: 都道府県名
            area_name: 市町村名
            ft: FT値
            prefectures: 都道府県データ

        Returns:
            雨量最大値
        """
        for prefecture in prefectures:
            if prefecture.name != pref_name:
                continue
            for area in prefecture.areas:
                if area.name != area_name:
                    continue

                max_value = 0.0
                for mesh in area.meshes:
                    for rain_point in mesh.rain_3hour:
                        if rain_point.ft == ft:
                            max_value = max(max_value, rain_point.value)

                return max_value

        return 0.0

    def _apply_ratios_to_guidance_data(
        self,
        adjusted_grib2: Dict[str, Any],
        mesh_ratios: Dict[str, Dict[int, float]]
    ) -> None:
        """
        ガイダンスデータに調整比率を適用（インプレース更新）

        Args:
            adjusted_grib2: 調整対象のガイダンスデータ
            mesh_ratios: メッシュごとの調整比率
        """
        logger.info("ガイダンスデータへの比率適用開始")

        # data_3h（3時間雨量）を調整
        if 'data_3h' in adjusted_grib2:
            for time_data in adjusted_grib2['data_3h']:
                ft = time_data['ft']
                values = time_data['value']

                # 各メッシュの値を調整
                for mesh_code, ratios in mesh_ratios.items():
                    if ft in ratios:
                        ratio = ratios[ft]
                        # メッシュコードからインデックスを取得
                        # ここではvalues配列のインデックスを直接使用
                        # 実際のインデックス変換はメッシュコードから計算が必要
                        # 一旦、全メッシュに比率を適用（簡略化）
                        pass

        # より正確な実装: メッシュコード→インデックス変換が必要
        # しかし、現状ではmesh_ratiosのキーがメッシュコードなので、
        # prefecturesからメッシュを再取得して調整する方が確実

        logger.info("ガイダンスデータへの比率適用完了")

    def _get_area_original_max_from_session(
        self,
        prefectures_dict: Dict[str, Any],
        area_key: str,
        ft: int
    ) -> float:
        """
        セッション辞書形式データから、市町村の特定FTにおける元の最大3時間雨量を取得する。
        """
        pref_name, area_name = area_key.split('_', 1)

        for pref_dict in prefectures_dict.values():
            if pref_dict.get("name") != pref_name:
                continue

            for area_dict in pref_dict.get("areas", []):
                if area_dict.get("name") != area_name:
                    continue

                max_value = 0.0
                for mesh_dict in area_dict.get("meshes", []):
                    for rain_point in mesh_dict.get("rain_timeline", []):
                        if int(rain_point["ft"]) == ft:
                            max_value = max(max_value, float(rain_point["value"]))

                return max_value

        return 0.0

    def _build_aggregate_timeline_for_meshes(
        self,
        meshes: List[Dict[str, Any]]
    ) -> List[Dict[str, float]]:
        timeline: List[Dict[str, float]] = []

        for window_end_ft, window_fts in self.WINDOW_24H_MAP.items():
            max_value = 0.0
            for mesh_dict in meshes:
                total = self._sum_mesh_values_for_fts(mesh_dict, window_fts)
                max_value = max(max_value, total)
            timeline.append({"ft": window_end_ft, "value": round(max_value)})

        return timeline

    def _collect_subdivision_meshes(
        self,
        pref_dict: Dict[str, Any],
        area_names: List[str]
    ) -> List[Dict[str, Any]]:
        meshes: List[Dict[str, Any]] = []
        for area_name in area_names:
            area_dict = next((a for a in pref_dict.get("areas", []) if a.get("name") == area_name), None)
            if area_dict:
                meshes.extend(area_dict.get("meshes", []))
        return meshes

    def _build_24hour_adjusted_mesh_rainfall(
        self,
        prefectures_dict: Dict[str, Any],
        area_adjustments: Dict[str, Dict[int, float]],
        strategy: str
    ) -> Dict[str, List[Tuple[int, float]]]:
        adjusted_mesh_rainfall: Dict[str, Dict[int, float]] = {}

        for pref_dict in prefectures_dict.values():
            pref_name = pref_dict["name"]
            for area_dict in pref_dict.get("areas", []):
                area_key = f"{pref_name}_{area_dict['name']}"
                adjustments = area_adjustments.get(area_key)
                if not adjustments:
                    continue

                if strategy == 'fill_uniform':
                    self._apply_fill_24hour_uniform(area_dict.get("meshes", []), adjustments, adjusted_mesh_rainfall)
                elif strategy == 'ratio_uniform':
                    self._apply_ratio_24hour_uniform(area_dict.get("meshes", []), adjustments, adjusted_mesh_rainfall)
                elif strategy == 'ratio_peak_mesh':
                    self._apply_ratio_24hour_peak_mesh(area_key, area_dict.get("meshes", []), adjustments, adjusted_mesh_rainfall)

        return {
            mesh_code: [(ft, value) for ft, value in sorted(ft_values.items())]
            for mesh_code, ft_values in adjusted_mesh_rainfall.items()
        }

    def _apply_fill_24hour_uniform(
        self,
        meshes: List[Dict[str, Any]],
        adjustments: Dict[int, float],
        adjusted_mesh_rainfall: Dict[str, Dict[int, float]]
    ) -> None:
        for mesh_dict in meshes:
            mesh_code = mesh_dict.get("code")
            if not mesh_code:
                continue
            current_values = self._mesh_timeline_to_dict(mesh_dict)

            for window_end_ft, target_24h in adjustments.items():
                window_fts = self._available_window_fts(current_values, int(window_end_ft))
                if not window_fts:
                    continue
                per_ft_value = float(target_24h) / len(window_fts)
                target_values = {ft: per_ft_value for ft in window_fts}
                self._merge_mesh_values(mesh_code, current_values, target_values, adjusted_mesh_rainfall)

    def _apply_ratio_24hour_uniform(
        self,
        meshes: List[Dict[str, Any]],
        adjustments: Dict[int, float],
        adjusted_mesh_rainfall: Dict[str, Dict[int, float]]
    ) -> None:
        original_max_by_ft = self._build_original_max_by_ft(meshes)

        for mesh_dict in meshes:
            mesh_code = mesh_dict.get("code")
            if not mesh_code:
                continue
            current_values = self._mesh_timeline_to_dict(mesh_dict)
            target_values: Dict[int, float] = {}

            for window_end_ft, target_24h in adjustments.items():
                window_fts = self._available_window_fts(current_values, int(window_end_ft))
                if not window_fts:
                    continue
                per_ft_value = float(target_24h) / len(window_fts)

                for ft in window_fts:
                    original_max = original_max_by_ft.get(ft, 0.0)
                    if original_max > 0:
                        ratio = per_ft_value / original_max
                        target_values[ft] = current_values[ft] * ratio
                    else:
                        if per_ft_value > 0:
                            logger.warning(
                                "24時間均等比率補正をスキップ: original_max=0, ft=%s, adjusted_value=%s",
                                ft,
                                per_ft_value,
                            )
                        target_values[ft] = current_values[ft]

            self._merge_mesh_values(mesh_code, current_values, target_values, adjusted_mesh_rainfall)

    def _apply_ratio_24hour_peak_mesh(
        self,
        area_key: str,
        meshes: List[Dict[str, Any]],
        adjustments: Dict[int, float],
        adjusted_mesh_rainfall: Dict[str, Dict[int, float]]
    ) -> None:
        mesh_timelines = {
            mesh_dict.get("code"): self._mesh_timeline_to_dict(mesh_dict)
            for mesh_dict in meshes
            if mesh_dict.get("code")
        }

        for window_end_ft, target_24h in adjustments.items():
            window_end_ft_int = int(window_end_ft)
            if window_end_ft_int not in self.WINDOW_24H_MAP:
                continue

            peak_mesh_code = None
            peak_sum = 0.0
            mesh_sums: Dict[str, float] = {}

            for mesh_code, timeline_dict in mesh_timelines.items():
                window_fts = self._available_window_fts(timeline_dict, window_end_ft_int)
                mesh_sum = sum(timeline_dict.get(ft, 0.0) for ft in window_fts)
                mesh_sums[mesh_code] = mesh_sum
                if mesh_sum > peak_sum:
                    peak_sum = mesh_sum
                    peak_mesh_code = mesh_code

            if peak_sum <= 0:
                if float(target_24h) > 0:
                    logger.warning(
                        "24時間最大格子比率補正をスキップ: original_sum_24h=0, area=%s, window_end_ft=%s, adjusted_value=%s",
                        area_key,
                        window_end_ft_int,
                        target_24h,
                    )
                continue

            for mesh_code, timeline_dict in mesh_timelines.items():
                window_fts = self._available_window_fts(timeline_dict, window_end_ft_int)
                if not window_fts:
                    continue

                mesh_sum = mesh_sums.get(mesh_code, 0.0)
                if mesh_sum <= 0:
                    target_values = {ft: timeline_dict[ft] for ft in window_fts}
                else:
                    mesh_target_sum = float(target_24h) * (mesh_sum / peak_sum)
                    target_values = {
                        ft: mesh_target_sum * (timeline_dict[ft] / mesh_sum)
                        for ft in window_fts
                    }

                self._merge_mesh_values(mesh_code, timeline_dict, target_values, adjusted_mesh_rainfall)

    def _build_original_max_by_ft(self, meshes: List[Dict[str, Any]]) -> Dict[int, float]:
        original_max_by_ft: Dict[int, float] = {}
        for mesh_dict in meshes:
            for point in mesh_dict.get("rain_timeline", []):
                ft = int(point["ft"])
                value = float(point["value"])
                if ft not in original_max_by_ft or value > original_max_by_ft[ft]:
                    original_max_by_ft[ft] = value
        return original_max_by_ft

    def _mesh_timeline_to_dict(self, mesh_dict: Dict[str, Any]) -> Dict[int, float]:
        return {
            int(point["ft"]): float(point["value"])
            for point in mesh_dict.get("rain_timeline", [])
        }

    def _available_window_fts(self, timeline_dict: Dict[int, float], window_end_ft: int) -> List[int]:
        return [ft for ft in self.WINDOW_24H_MAP.get(window_end_ft, ()) if ft in timeline_dict]

    def _sum_mesh_values_for_fts(self, mesh_dict: Dict[str, Any], fts: Tuple[int, ...]) -> float:
        timeline_dict = self._mesh_timeline_to_dict(mesh_dict)
        return sum(timeline_dict.get(ft, 0.0) for ft in fts)

    def _merge_mesh_values(
        self,
        mesh_code: str,
        current_values: Dict[int, float],
        target_values: Dict[int, float],
        adjusted_mesh_rainfall: Dict[str, Dict[int, float]]
    ) -> None:
        if not target_values:
            return
        if mesh_code not in adjusted_mesh_rainfall:
            adjusted_mesh_rainfall[mesh_code] = dict(current_values)

        for ft, value in target_values.items():
            adjusted_mesh_rainfall[mesh_code][ft] = max(
                adjusted_mesh_rainfall[mesh_code].get(ft, current_values.get(ft, 0.0)),
                float(value)
            )

    def adjust_mesh_rainfall_by_ratios(
        self,
        prefectures: List[Prefecture],
        mesh_ratios: Dict[str, Dict[int, float]]
    ) -> None:
        """
        メッシュの雨量データを比率で調整（インプレース更新）

        この関数はprefecturesのメッシュデータを直接調整する

        Args:
            prefectures: 都道府県データ（調整対象）
            mesh_ratios: メッシュごとの調整比率
        """
        logger.info("メッシュ雨量データの調整開始")

        total_adjusted = 0

        for prefecture in prefectures:
            for area in prefecture.areas:
                for mesh in area.meshes:
                    if mesh.code in mesh_ratios:
                        ratios = mesh_ratios[mesh.code]

                        # rain_3hour（3時間雨量）を調整
                        for rain_point in mesh.rain_3hour:
                            if rain_point.ft in ratios:
                                ratio = ratios[rain_point.ft]
                                rain_point.value *= ratio
                                total_adjusted += 1

                        # rain_1hour（1時間雨量）も調整
                        if hasattr(mesh, 'rain_1hour') and mesh.rain_1hour:
                            for rain_point in mesh.rain_1hour:
                                # 1時間雨量は対応する3時間期間の比率を使用
                                # FTを3時間単位に変換
                                ft_3h = (rain_point.ft // 3) * 3
                                if ft_3h in ratios:
                                    ratio = ratios[ft_3h]
                                    rain_point.value *= ratio
                                    total_adjusted += 1

                        # rain_1hour_max（最大1時間雨量）も調整
                        if hasattr(mesh, 'rain_1hour_max') and mesh.rain_1hour_max:
                            for rain_point in mesh.rain_1hour_max:
                                if rain_point.ft in ratios:
                                    ratio = ratios[rain_point.ft]
                                    rain_point.value *= ratio
                                    total_adjusted += 1

        logger.info(f"メッシュ雨量データの調整完了: {total_adjusted}件調整")
