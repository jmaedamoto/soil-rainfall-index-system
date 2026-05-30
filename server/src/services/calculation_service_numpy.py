#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NumPyベクトル化によるCalculationService

全メッシュを一括で計算することで、Pythonループのオーバーヘッドを削減
"""

import numpy as np
from typing import List, Dict, Any, Tuple, Optional
import logging

logger = logging.getLogger(__name__)


class CalculationServiceNumpy:
    """NumPyベクトル化版 CalculationService"""

    # VBA タンクモデルパラメータ (完全同一)
    L1, L2, L3, L4 = 15.0, 60.0, 15.0, 15.0
    A1, A2, A3, A4 = 0.1, 0.15, 0.05, 0.01
    B1, B2, B3 = 0.12, 0.05, 0.01

    @staticmethod
    def normalize_risk_rule(risk_rule: Optional[str]) -> str:
        normalized = (risk_rule or "legacy").lower()
        if normalized not in {"legacy", "lead_time_to_level4"}:
            raise ValueError(f"Unsupported risk_rule: {risk_rule}")
        return normalized

    def calc_tank_model_vectorized(
        self,
        s1: np.ndarray,
        s2: np.ndarray,
        s3: np.ndarray,
        t: float,
        r: np.ndarray
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        ベクトル化されたタンクモデル計算

        Args:
            s1: 第1タンク貯留量 (n_meshes,)
            s2: 第2タンク貯留量 (n_meshes,)
            s3: 第3タンク貯留量 (n_meshes,)
            t: 時間ステップ（時間）
            r: 降雨量 (n_meshes,)

        Returns:
            (s1_new, s2_new, s3_new): 更新後のタンク貯留量
        """
        # 流出量の計算（ベクトル化）
        q1 = self.A1 * np.maximum(0, s1 - self.L1) + self.A2 * np.maximum(0, s1 - self.L2)
        q2 = self.A3 * np.maximum(0, s2 - self.L3)
        q3 = self.A4 * np.maximum(0, s3 - self.L4)

        # 新しいタンク状態の計算
        s1_new = (1 - self.B1 * t) * s1 - q1 * t + r
        s2_new = (1 - self.B2 * t) * s2 - q2 * t + self.B1 * s1 * t
        s3_new = (1 - self.B3 * t) * s3 - q3 * t + self.B2 * s2 * t

        # 負の値をゼロにクリップ
        s1_new = np.maximum(0, s1_new)
        s2_new = np.maximum(0, s2_new)
        s3_new = np.maximum(0, s3_new)

        return s1_new, s2_new, s3_new

    def calc_swi_hourly_vectorized(
        self,
        initial_swi: np.ndarray,
        initial_s1: np.ndarray,
        initial_s2: np.ndarray,
        initial_s3: np.ndarray,
        hourly_rain: np.ndarray
    ) -> np.ndarray:
        """
        全メッシュの1時間ごとSWI計算をベクトル化

        Args:
            initial_swi: 初期SWI (n_meshes,)
            initial_s1: 初期第1タンク (n_meshes,)
            initial_s2: 初期第2タンク (n_meshes,)
            initial_s3: 初期第3タンク (n_meshes,)
            hourly_rain: 1時間ごと雨量 (n_times, n_meshes)

        Returns:
            swi_hourly: SWI時系列 (n_times+1, n_meshes) - FT=0を含む
        """
        n_times, n_meshes = hourly_rain.shape

        # 結果配列を事前確保
        swi_hourly = np.zeros((n_times + 1, n_meshes), dtype=np.float64)
        swi_hourly[0] = initial_swi  # FT=0

        # 現在のタンク状態
        s1 = initial_s1.copy()
        s2 = initial_s2.copy()
        s3 = initial_s3.copy()

        # 時系列ループ（メッシュ方向はベクトル化）
        for t_idx in range(n_times):
            rain = hourly_rain[t_idx]
            s1, s2, s3 = self.calc_tank_model_vectorized(s1, s2, s3, 1.0, rain)
            swi_hourly[t_idx + 1] = s1 + s2 + s3

        return swi_hourly

    def calc_hourly_risk_vectorized(
        self,
        swi_hourly: np.ndarray,
        rain_hourly: np.ndarray,
        advisory_bounds: np.ndarray,
        warning_bounds: np.ndarray,
        dosyakei_bounds: np.ndarray,
        level4_curves: Optional[np.ndarray] = None,
        risk_rule: str = "legacy"
    ) -> np.ndarray:
        """
        全メッシュの危険度をベクトル化計算

        Args:
            swi_hourly: SWI時系列 (n_times, n_meshes)
            rain_hourly: 1時間雨量時系列 (n_times-1, n_meshes)
            advisory_bounds: 注意報基準値 (n_meshes,)
            warning_bounds: 警報基準値 (n_meshes,)
            dosyakei_bounds: 土砂災害基準値 (n_meshes,)

        Returns:
            risk_hourly: リスク時系列 (n_times, n_meshes)
        """
        _, n_meshes = swi_hourly.shape
        normalized_risk_rule = self.normalize_risk_rule(risk_rule)

        # 閾値を整数にキャスト（元のコードと同じ処理）
        advisory = np.floor(advisory_bounds).astype(np.int32).reshape(1, -1)
        warning = np.floor(warning_bounds).astype(np.int32).reshape(1, -1)
        dosyakei = np.floor(dosyakei_bounds).astype(np.int32).reshape(1, -1)
        level4_thresholds, level4_valid = self.build_level4_thresholds_vectorized(
            rain_hourly,
            dosyakei,
            level4_curves,
        )

        # ベクトル化された条件判定（高い閾値から判定）
        conditions = [
            level4_valid & (swi_hourly >= level4_thresholds),  # レベル4
            swi_hourly >= warning,    # レベル3
            swi_hourly >= advisory,   # レベル2
        ]
        choices = [4, 3, 2]

        risk = np.select(conditions, choices, default=0).astype(np.int32)

        return self.apply_risk_rule_vectorized(risk, normalized_risk_rule)

    def build_level4_thresholds_vectorized(
        self,
        rain_hourly: np.ndarray,
        dosyakei_bounds: np.ndarray,
        level4_curves: Optional[np.ndarray] = None,
    ) -> Tuple[np.ndarray, np.ndarray]:
        """1時間雨量ごとのレベル4閾値をメッシュ単位で展開する。"""
        _, n_meshes = dosyakei_bounds.shape

        rain_with_ft0 = np.vstack([
            np.zeros((1, n_meshes), dtype=np.float64),
            rain_hourly,
        ])
        rain_indices = np.clip(
            np.rint(rain_with_ft0).astype(np.int32),
            0,
            150,
        )

        if level4_curves is None:
            thresholds = np.broadcast_to(dosyakei_bounds, rain_indices.shape)
            valid = thresholds < 999
            return thresholds, valid

        safe_curves = np.array(level4_curves, dtype=np.int32, copy=True)
        has_curve = np.any(safe_curves >= 0, axis=1).reshape(1, -1)
        safe_curves = np.where(safe_curves >= 0, safe_curves, 999)
        curve_thresholds = np.take_along_axis(
            safe_curves[np.newaxis, :, :],
            rain_indices[:, :, np.newaxis],
            axis=2,
        ).squeeze(axis=2)

        fallback_thresholds = np.broadcast_to(dosyakei_bounds, rain_indices.shape)
        thresholds = np.where(has_curve, curve_thresholds, fallback_thresholds)
        valid = np.where(has_curve, curve_thresholds < 999, fallback_thresholds < 999)
        return thresholds, valid

    def apply_risk_rule_vectorized(
        self,
        risk_hourly: np.ndarray,
        risk_rule: str = "legacy"
    ) -> np.ndarray:
        normalized_risk_rule = self.normalize_risk_rule(risk_rule)
        if normalized_risk_rule == "legacy" or risk_hourly.size == 0:
            return risk_hourly

        adjusted = risk_hourly.copy()
        n_times, n_meshes = adjusted.shape

        for mesh_index in range(n_meshes):
            level4_indices = np.where(adjusted[:, mesh_index] >= 4)[0]
            if len(level4_indices) == 0:
                continue

            first_level4_index = int(level4_indices[0])
            last_level4_index = int(level4_indices[-1])
            level3_start = max(0, first_level4_index - 3)

            if level3_start < first_level4_index:
                adjusted[level3_start:first_level4_index, mesh_index] = 3

            adjusted[first_level4_index:last_level4_index + 1, mesh_index] = 4

        return adjusted

    def calc_3hour_max_risk_vectorized(self, risk_hourly: np.ndarray) -> np.ndarray:
        """
        1時間リスクから3時間最大リスクをベクトル化計算

        Args:
            risk_hourly: 1時間リスク (n_times, n_meshes) - FT=0を含む

        Returns:
            risk_3hour: 3時間最大リスク (n_3hour_periods+1, n_meshes) - FT=0を含む
        """
        n_times, n_meshes = risk_hourly.shape

        # FT=0は単独で処理
        result = [risk_hourly[0]]  # FT=0

        # 残り（FT=1から）を3つずつグループ化
        remaining = risk_hourly[1:]
        n_remaining = remaining.shape[0]
        n_groups = (n_remaining + 2) // 3  # 切り上げ

        for i in range(n_groups):
            start_idx = i * 3
            end_idx = min(start_idx + 3, n_remaining)
            group = remaining[start_idx:end_idx]
            max_risk = np.max(group, axis=0)
            result.append(max_risk)

        return np.array(result)

    def calc_hourly_rain_vectorized(
        self,
        rain_3h: np.ndarray,
        rain_1h_max: np.ndarray
    ) -> np.ndarray:
        """
        3時間雨量と最大1時間雨量から1時間ごと雨量を推定（ベクトル化）

        Args:
            rain_3h: 3時間雨量 (n_periods, n_meshes)
            rain_1h_max: 最大1時間雨量 (n_periods, n_meshes)

        Returns:
            rain_1hour: 1時間ごと雨量 (n_periods*3, n_meshes)
        """
        n_periods, n_meshes = rain_3h.shape

        # 結果配列
        rain_1hour = np.zeros((n_periods * 3, n_meshes), dtype=np.float64)

        # 残りの雨量
        r_rest = np.maximum(0, rain_3h - rain_1h_max)
        r_half = r_rest / 2.0

        # 3時間期間ごとに展開
        for i in range(n_periods):
            rain_1hour[i * 3] = r_half[i]      # 前1時間
            rain_1hour[i * 3 + 1] = rain_1h_max[i]  # 中央1時間（最大）
            rain_1hour[i * 3 + 2] = r_half[i]  # 後1時間

        return rain_1hour

    def calc_hourly_rain_uniform_vectorized(self, rain_3h: np.ndarray) -> np.ndarray:
        """
        3時間雨量を1時間ごとに均等按分する。
        """
        n_periods, n_meshes = rain_3h.shape
        rain_1hour = np.zeros((n_periods * 3, n_meshes), dtype=np.float64)

        for i in range(n_periods):
            hourly_value = rain_3h[i] / 3.0
            rain_1hour[i * 3] = hourly_value
            rain_1hour[i * 3 + 1] = hourly_value
            rain_1hour[i * 3 + 2] = hourly_value

        return rain_1hour

    def process_all_meshes_vectorized(
        self,
        mesh_data: Dict[str, np.ndarray],
        guidance_rain_3h: np.ndarray,
        guidance_rain_1h_max: np.ndarray
    ) -> Dict[str, np.ndarray]:
        """
        全メッシュの計算を一括実行

        Args:
            mesh_data: メッシュデータ
                - initial_swi: 初期SWI (n_meshes,)
                - initial_s1: 初期第1タンク (n_meshes,)
                - initial_s2: 初期第2タンク (n_meshes,)
                - initial_s3: 初期第3タンク (n_meshes,)
                - advisory_bounds: 注意報基準値 (n_meshes,)
                - warning_bounds: 警報基準値 (n_meshes,)
                - dosyakei_bounds: 土砂災害基準値 (n_meshes,)
            guidance_rain_3h: 3時間雨量予測 (n_periods, n_meshes)
            guidance_rain_1h_max: 最大1時間雨量予測 (n_periods, n_meshes)

        Returns:
            results: 計算結果
                - swi_hourly: 1時間SWI (n_times+1, n_meshes)
                - risk_hourly: 1時間リスク (n_times+1, n_meshes)
                - risk_3hour: 3時間最大リスク (n_3hour+1, n_meshes)
        """
        # 1時間ごと雨量を推定
        rain_1hour = self.calc_hourly_rain_vectorized(
            guidance_rain_3h,
            guidance_rain_1h_max
        )

        # 1時間ごとSWI計算
        swi_hourly = self.calc_swi_hourly_vectorized(
            mesh_data['initial_swi'],
            mesh_data['initial_s1'],
            mesh_data['initial_s2'],
            mesh_data['initial_s3'],
            rain_1hour
        )

        # 1時間ごとリスク計算
        risk_hourly = self.calc_hourly_risk_vectorized(
            swi_hourly,
            rain_1hour,
            mesh_data['advisory_bounds'],
            mesh_data['warning_bounds'],
            mesh_data['dosyakei_bounds'],
            mesh_data.get('level4_curves'),
        )

        # 3時間最大リスク計算
        risk_3hour = self.calc_3hour_max_risk_vectorized(risk_hourly)

        return {
            'rain_1hour': rain_1hour,
            'swi_hourly': swi_hourly,
            'risk_hourly': risk_hourly,
            'risk_3hour': risk_3hour
        }

    def recalculate_meshes_vectorized(
        self,
        mesh_data_list: list,
        risk_rule: str = "legacy"
    ) -> dict:
        """
        複数メッシュの雨量調整後の再計算を一括実行

        Args:
            mesh_data_list: メッシュデータのリスト
                各要素は {
                    'mesh_code': str,
                    'initial_swi': float,
                    'advisory_bound': int,
                    'warning_bound': int,
                    'dosyakei_bound': int,
                    'rain_3hour': list of (ft, value)
                }

        Returns:
            results: {mesh_code: {swi_timeline, risk_3hour_max_timeline, risk_hourly_timeline}}
        """
        if not mesh_data_list:
            return {}

        n_meshes = len(mesh_data_list)

        # 3時間雨量のFT一覧を取得（最初のメッシュから）
        first_rain = mesh_data_list[0]['rain_3hour']
        n_periods = len(first_rain)
        ft_list = [r[0] for r in first_rain]

        # 配列に変換
        initial_swi = np.array([m['initial_swi'] for m in mesh_data_list])
        # タンク値の推定（簡易版：均等分割）
        initial_s1 = initial_swi * 0.4
        initial_s2 = initial_swi * 0.3
        initial_s3 = initial_swi * 0.3

        advisory_bounds = np.array([m['advisory_bound'] for m in mesh_data_list])
        warning_bounds = np.array([m['warning_bound'] for m in mesh_data_list])
        dosyakei_bounds = np.array([m['dosyakei_bound'] for m in mesh_data_list])
        level4_curves = np.full((n_meshes, 151), -1, dtype=np.int32)
        for i, mesh in enumerate(mesh_data_list):
            curve = mesh.get('level4_curve')
            if curve is None:
                continue
            if len(curve) != 151:
                logger.warning(
                    "Invalid level4_curve length for mesh %s: %s",
                    mesh.get('mesh_code'),
                    len(curve),
                )
                continue
            level4_curves[i] = np.array(curve, dtype=np.int32)

        # 3時間雨量を配列化
        rain_3h = np.zeros((n_periods, n_meshes), dtype=np.float64)
        rain_1h_max = np.zeros((n_periods, n_meshes), dtype=np.float64)
        for i, mesh in enumerate(mesh_data_list):
            original_3h_by_ft = {
                int(ft): float(value)
                for ft, value in mesh.get('original_rain_3hour', mesh['rain_3hour'])
            }
            max_1h_by_ft = {
                int(ft): float(value)
                for ft, value in mesh.get('rain_1hour_max', [])
            }
            for j, (ft, value) in enumerate(mesh['rain_3hour']):
                rain_3h[j, i] = value
                original_1h_max = max_1h_by_ft.get(int(ft), 0.0)
                original_3h = original_3h_by_ft.get(int(ft), 0.0)

                if value <= 0:
                    adjusted_1h_max = 0.0
                elif original_1h_max > 0 and original_3h > 0:
                    adjusted_1h_max = min(value, original_1h_max * (value / original_3h))
                else:
                    adjusted_1h_max = value / 3.0

                rain_1h_max[j, i] = max(0.0, min(value, adjusted_1h_max))

        # 1時間雨量を推定（元の1時間最大雨量の形状を可能な限り維持）
        rain_1hour = self.calc_hourly_rain_vectorized(rain_3h, rain_1h_max)

        # 1時間ごとSWI計算
        swi_hourly = self.calc_swi_hourly_vectorized(
            initial_swi, initial_s1, initial_s2, initial_s3, rain_1hour
        )

        # 1時間ごとリスク計算
        risk_hourly = self.calc_hourly_risk_vectorized(
            swi_hourly,
            rain_1hour,
            advisory_bounds,
            warning_bounds,
            dosyakei_bounds,
            level4_curves=level4_curves,
            risk_rule=risk_rule,
        )

        # 3時間最大リスク計算
        risk_3hour = self.calc_3hour_max_risk_vectorized(risk_hourly)

        # 3時間SWIは、3時間雨量を1時間ごとに均等按分して1時間ステップで計算した終点値を使う
        rain_1hour_uniform = self.calc_hourly_rain_uniform_vectorized(rain_3h)
        swi_hourly_uniform = self.calc_swi_hourly_vectorized(
            initial_swi, initial_s1, initial_s2, initial_s3, rain_1hour_uniform
        )

        # 結果を辞書形式に変換
        results = {}
        for i, mesh in enumerate(mesh_data_list):
            mesh_code = mesh['mesh_code']

            # SWIタイムライン (FT=0を含む)
            swi_timeline = [{'ft': 0, 'value': float(swi_hourly_uniform[0, i])}]
            for j, ft in enumerate(ft_list):
                hourly_index = (j + 1) * 3
                swi_timeline.append({'ft': ft, 'value': float(swi_hourly_uniform[hourly_index, i])})

            # 3時間最大リスクタイムライン
            risk_3h_timeline = []
            for j in range(risk_3hour.shape[0]):
                ft = 0 if j == 0 else ft_list[min(j - 1, len(ft_list) - 1)]
                if j > 0:
                    ft = ft_list[j - 1] if j <= len(ft_list) else ft_list[-1]
                risk_3h_timeline.append({'ft': j * 3 if j > 0 else 0, 'value': int(risk_3hour[j, i])})

            # 正しいFT値で再構築
            risk_3h_timeline = [{'ft': 0, 'value': int(risk_3hour[0, i])}]
            for j, ft in enumerate(ft_list):
                if j + 1 < risk_3hour.shape[0]:
                    risk_3h_timeline.append({'ft': ft, 'value': int(risk_3hour[j + 1, i])})

            # 1時間リスクタイムライン
            risk_hourly_timeline = []
            for j in range(risk_hourly.shape[0]):
                risk_hourly_timeline.append({'ft': j, 'value': int(risk_hourly[j, i])})

            rain_1hour_timeline = [
                {'ft': j + 1, 'value': float(rain_1hour[j, i])}
                for j in range(rain_1hour.shape[0])
            ]
            swi_hourly_timeline = [
                {'ft': j, 'value': float(swi_hourly[j, i])}
                for j in range(swi_hourly.shape[0])
            ]
            rain_1hour_max_timeline = [
                {'ft': ft, 'value': float(rain_1h_max[j, i])}
                for j, ft in enumerate(ft_list)
            ]

            results[mesh_code] = {
                'rain_1hour_timeline': rain_1hour_timeline,
                'rain_1hour_max_timeline': rain_1hour_max_timeline,
                'swi_timeline': swi_timeline,
                'swi_hourly_timeline': swi_hourly_timeline,
                'risk_3hour_max_timeline': risk_3h_timeline,
                'risk_hourly_timeline': risk_hourly_timeline
            }

        return results
