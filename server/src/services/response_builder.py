# -*- coding: utf-8 -*-
"""
レスポンス構築サービス
main_service.pyから重複するレスポンス構築ロジックを抽出
"""
from typing import Dict, Any, List
from datetime import datetime
from models import Prefecture


class ResponseBuilder:
    """APIレスポンスを構築するヘルパークラス"""

    @staticmethod
    def _build_max_timeline_from_meshes(
        meshes,
        timeline_key: str
    ) -> List[Dict[str, Any]]:
        """メッシュ群からFTごとの最大値タイムラインを構築する"""
        max_by_ft: Dict[int, float] = {}

        for mesh in meshes:
            for point in mesh.get(timeline_key, []):
                ft = int(point["ft"])
                value = float(point["value"])
                if ft not in max_by_ft or value > max_by_ft[ft]:
                    max_by_ft[ft] = value

        return [
            {"ft": ft, "value": value}
            for ft, value in sorted(max_by_ft.items())
        ]

    @staticmethod
    def _build_row_metrics_from_meshes(meshes) -> Dict[str, Any]:
        """タイムライン表で使う集約値を構築する"""
        return {
            "swi_timeline": ResponseBuilder._build_max_timeline_from_meshes(
                meshes, "swi_timeline"
            ),
            "rain_3hour_timeline": ResponseBuilder._build_max_timeline_from_meshes(
                meshes, "rain_timeline"
            ),
        }

    @staticmethod
    def build_prefecture_response(prefectures: List[Prefecture],
                                  initial_time: datetime) -> Dict[str, Any]:
        """
        Prefecture オブジェクトのリストから完全なAPIレスポンスを構築

        Args:
            prefectures: Prefecture オブジェクトのリスト
            initial_time: 初期時刻

        Returns:
            APIレスポンス辞書
        """
        result = {
            "calculation_time": datetime.utcnow().isoformat(),
            "initial_time": initial_time.isoformat(),
            "prefectures": {}
        }

        for prefecture in prefectures:
            result["prefectures"][prefecture.code] = ResponseBuilder._build_prefecture_dict(prefecture)

        return result

    @staticmethod
    def _build_prefecture_dict(prefecture: Prefecture) -> Dict[str, Any]:
        """
        単一の Prefecture オブジェクトから辞書を構築

        Args:
            prefecture: Prefecture オブジェクト

        Returns:
            府県データの辞書
        """
        pref_data = {
            "name": prefecture.name,
            "code": prefecture.code,
            "areas": [],
            "secondary_subdivisions": [],
            "prefecture_rain_1hour_max_timeline": ResponseBuilder._build_guidance_timeline(
                prefecture.prefecture_rain_1hour_max_timeline
            ),
            "prefecture_rain_3hour_timeline": ResponseBuilder._build_guidance_timeline(
                prefecture.prefecture_rain_3hour_timeline
            ),
            "prefecture_risk_timeline": ResponseBuilder._build_risk_timeline(
                prefecture.prefecture_risk_timeline
            ),
        }

        # 二次細分データ
        for subdivision in prefecture.secondary_subdivisions:
            subdivision_meshes = [
                ResponseBuilder._build_mesh_dict(mesh)
                for area in subdivision.areas
                for mesh in area.meshes
            ]
            subdiv_data = {
                "name": subdivision.name,
                "area_names": [area.name for area in subdivision.areas],
                "rain_1hour_max_timeline": ResponseBuilder._build_guidance_timeline(
                    subdivision.rain_1hour_max_timeline
                ),
                "rain_3hour_timeline": ResponseBuilder._build_guidance_timeline(
                    subdivision.rain_3hour_timeline
                ),
                "risk_timeline": ResponseBuilder._build_risk_timeline(
                    subdivision.risk_timeline
                ),
                **ResponseBuilder._build_row_metrics_from_meshes(subdivision_meshes),
            }
            pref_data["secondary_subdivisions"].append(subdiv_data)

        # エリア（市町村）データ
        for area in prefecture.areas:
            area_meshes = [ResponseBuilder._build_mesh_dict(mesh) for mesh in area.meshes]
            area_data = {
                "name": area.name,
                "secondary_subdivision_name": area.secondary_subdivision_name,
                "meshes": area_meshes,
                "risk_timeline": ResponseBuilder._build_risk_timeline(
                    area.risk_timeline,
                    include_rainfall_to_level4=True,
                ),
                **ResponseBuilder._build_row_metrics_from_meshes(area_meshes),
            }

            pref_data["areas"].append(area_data)

        pref_data.update(
            ResponseBuilder._build_row_metrics_from_meshes(
                [
                    mesh
                    for area in pref_data["areas"]
                    for mesh in area["meshes"]
                ]
            )
        )

        return pref_data

    @staticmethod
    def _build_mesh_dict(mesh) -> Dict[str, Any]:
        """
        Mesh オブジェクトから辞書を構築

        Args:
            mesh: Mesh オブジェクト

        Returns:
            メッシュデータの辞書
        """
        return {
            "code": mesh.code,
            "lat": float(mesh.lat),
            "lon": float(mesh.lon),
            "x": int(mesh.x),
            "y": int(mesh.y),
            "swi_timeline": ResponseBuilder._build_swi_timeline(mesh.swi),
            "swi_hourly_timeline": ResponseBuilder._build_swi_timeline(mesh.swi_hourly),
            "rain_1hour_timeline": ResponseBuilder._build_guidance_timeline(mesh.rain_1hour),
            "rain_1hour_max_timeline": ResponseBuilder._build_guidance_timeline(mesh.rain_1hour_max),
            "rain_timeline": ResponseBuilder._build_guidance_timeline(mesh.rain_3hour),
            "risk_hourly_timeline": ResponseBuilder._build_risk_timeline(mesh.risk_hourly),
            "risk_3hour_max_timeline": ResponseBuilder._build_risk_timeline(mesh.risk_3hour_max)
        }

    @staticmethod
    def _build_swi_timeline(swi_data) -> List[Dict[str, Any]]:
        """SWIタイムラインを辞書リストに変換"""
        return [
            {"ft": s.ft, "value": float(s.value)}
            for s in swi_data
        ]

    @staticmethod
    def _build_guidance_timeline(guidance_data) -> List[Dict[str, Any]]:
        """ガイダンスタイムラインを辞書リストに変換"""
        return [
            {"ft": r.ft, "value": float(r.value)}
            for r in guidance_data
        ]

    @staticmethod
    def _build_risk_timeline(
        risk_data,
        include_rainfall_to_level4: bool = False,
    ) -> List[Dict[str, Any]]:
        """リスクタイムラインを辞書リストに変換"""
        timeline = []
        for r in risk_data:
            point = {"ft": r.ft, "value": r.value}
            if include_rainfall_to_level4:
                point["rainfall_to_level4_1h_mm"] = getattr(
                    r,
                    "rainfall_to_level4_1h_mm",
                    None,
                )
            timeline.append(point)
        return timeline
