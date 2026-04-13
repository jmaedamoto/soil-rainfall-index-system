#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
計算結果の集約処理
"""

from typing import List

from models import Area, Mesh, Risk


class CalculationAggregationService:
    """時系列の集約処理を担当するサービス"""

    def aggregate_timeline(self, meshes: List[Mesh], attribute_name: str, model_class):
        """メッシュの時系列をFTごとの最大値で集約する"""
        ft_set = set()
        for mesh in meshes:
            timeline = getattr(mesh, attribute_name, [])
            for point in timeline:
                ft_set.add(point.ft)

        aggregated_timeline = []
        for ft in sorted(ft_set):
            max_value = max(
                (
                    point.value
                    for mesh in meshes
                    for point in getattr(mesh, attribute_name, [])
                    if point.ft == ft
                ),
                default=0.0,
            )
            aggregated_timeline.append(model_class(ft=ft, value=max_value))

        return aggregated_timeline

    def aggregate_area_risk_timeline(self, areas: List[Area]) -> List[Risk]:
        """エリア単位のリスク時系列をFTごとの最大値で集約する"""
        ft_set = set()
        for area in areas:
            for point in area.risk_timeline:
                ft_set.add(point.ft)

        aggregated_risk = []
        for ft in sorted(ft_set):
            max_risk = max(
                (
                    point.value
                    for area in areas
                    for point in area.risk_timeline
                    if point.ft == ft
                ),
                default=0,
            )
            aggregated_risk.append(Risk(ft=ft, value=max_risk))

        return aggregated_risk
