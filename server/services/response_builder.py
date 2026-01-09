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
            )
        }

        # 二次細分データ
        for subdivision in prefecture.secondary_subdivisions:
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
                )
            }
            pref_data["secondary_subdivisions"].append(subdiv_data)

        # エリア（市町村）データ
        for area in prefecture.areas:
            area_data = {
                "name": area.name,
                "secondary_subdivision_name": area.secondary_subdivision_name,
                "meshes": [],
                "risk_timeline": ResponseBuilder._build_risk_timeline(area.risk_timeline)
            }

            for mesh in area.meshes:
                mesh_data = ResponseBuilder._build_mesh_dict(mesh)
                area_data["meshes"].append(mesh_data)

            pref_data["areas"].append(area_data)

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
            "advisary_bound": int(mesh.advisary_bound),
            "warning_bound": int(mesh.warning_bound),
            "dosyakei_bound": int(mesh.dosyakei_bound),
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
    def _build_risk_timeline(risk_data) -> List[Dict[str, Any]]:
        """リスクタイムラインを辞書リストに変換"""
        return [
            {"ft": r.ft, "value": r.value}
            for r in risk_data
        ]
