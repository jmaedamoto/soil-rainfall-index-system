# -*- coding: utf-8 -*-
"""
雨量調整APIコントローラー
"""
from flask import request, jsonify
from datetime import datetime
import logging
import os
import sys

# プロジェクトルートをパスに追加
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(project_root)

from services.main_service import MainService
from services.rainfall_adjustment_service import RainfallAdjustmentService
from services.grib2_service import Grib2Service
from services.data_service import DataService
from services.calculation_service import CalculationService
from services.cache_service import get_cache_service


logger = logging.getLogger(__name__)


class RainfallController:
    """雨量調整APIコントローラー"""

    def __init__(self, data_dir: str = "data"):
        self.main_service = MainService(data_dir)
        self.rainfall_service = RainfallAdjustmentService()
        self.grib2_service = Grib2Service()
        self.data_service = DataService(data_dir)
        self.calculation_service = CalculationService()
        self.cache_service = get_cache_service()
        self.data_dir = data_dir

    def get_rainfall_forecast(self):
        """
        市町村ごとの雨量予想時系列を取得

        Query Parameters:
            swi_initial: SWI初期時刻（ISO8601形式）
            guidance_initial: ガイダンス初期時刻（ISO8601形式）

        Returns:
            {
                "status": "success",
                "swi_initial_time": "2025-10-28T12:00:00",
                "guidance_initial_time": "2025-10-28T12:00:00",
                "area_rainfall": {
                    "滋賀県_大津市": [
                        {"ft": 0, "value": 5.2},
                        {"ft": 3, "value": 12.5},
                        ...
                    ],
                    ...
                }
            }
        """
        try:
            # パラメータ取得
            swi_initial_str = request.args.get('swi_initial')
            guidance_initial_str = request.args.get('guidance_initial')

            if not swi_initial_str or not guidance_initial_str:
                return jsonify({
                    "status": "error",
                    "message": "swi_initialとguidance_initialパラメータが必要です"
                }), 400

            # 日時パース
            try:
                swi_initial = datetime.fromisoformat(swi_initial_str.replace('Z', '+00:00'))
                swi_initial = swi_initial.replace(tzinfo=None)
            except ValueError as e:
                return jsonify({
                    "status": "error",
                    "message": f"swi_initial日時形式エラー: {e}"
                }), 400

            try:
                guidance_initial = datetime.fromisoformat(guidance_initial_str.replace('Z', '+00:00'))
                guidance_initial = guidance_initial.replace(tzinfo=None)
            except ValueError as e:
                return jsonify({
                    "status": "error",
                    "message": f"guidance_initial日時形式エラー: {e}"
                }), 400

            logger.info(f"雨量予想取得: SWI={swi_initial}, ガイダンス={guidance_initial}")

            # テストデータ判定（2023-06-02はテストデータ）
            is_test_data = (
                swi_initial.year == 2023 and
                swi_initial.month == 6 and
                swi_initial.day == 2 and
                swi_initial.hour == 0
            )

            if is_test_data:
                # ローカルテストデータを使用
                logger.info("テストデータモード: ローカルbinファイルを使用します")
                import os

                swi_filename = "Z__C_RJTD_20230602000000_SRF_GPV_Ggis1km_Psw_Aper10min_ANAL_grib2.bin"
                guidance_filename = "guid_msm_grib2_20230602000000_rmax00.bin"

                swi_path = os.path.join("data", swi_filename)
                guidance_path = os.path.join("data", guidance_filename)

                if not os.path.exists(swi_path):
                    raise Exception(f"テストデータファイルが見つかりません: {swi_path}")
                if not os.path.exists(guidance_path):
                    raise Exception(f"テストデータファイルが見つかりません: {guidance_path}")

                with open(swi_path, 'rb') as f:
                    swi_data_bytes = f.read()
                with open(guidance_path, 'rb') as f:
                    guidance_data_bytes = f.read()

                logger.info(f"ローカルファイル読み込み完了: {swi_filename}, {guidance_filename}")
            else:
                # 本番データをダウンロード
                logger.info("本番データモード: 気象庁サーバーからダウンロードします")
                from src.config.config_service import ConfigService
                config_service = ConfigService()

                swi_url = config_service.build_swi_url(swi_initial)
                guidance_url = config_service.build_guidance_url(guidance_initial)

                logger.info(f"SWI URL: {swi_url}")
                logger.info(f"Guidance URL: {guidance_url}")

                # データダウンロード
                swi_data_bytes = self.grib2_service.download_file(swi_url)
                if not swi_data_bytes:
                    raise Exception(f"SWIファイルダウンロード失敗: {swi_url}")

                guidance_data_bytes = self.grib2_service.download_file(guidance_url)
                if not guidance_data_bytes:
                    raise Exception(f"ガイダンスファイルダウンロード失敗: {guidance_url}")

            # GRIB2解析
            base_info, swi_grib2 = self.grib2_service.unpack_swi_grib2(swi_data_bytes)
            _, guidance_grib2 = self.grib2_service.unpack_guidance_grib2(guidance_data_bytes)

            # SWI初期時刻でガイダンスデータをフィルタリング
            guidance_grib2 = self.main_service._filter_guidance_data(
                guidance_grib2, swi_initial, guidance_initial
            )

            # 地域データ構築
            prefectures = self.data_service.prepare_areas()

            # メッシュ計算（雨量データの取得のため）
            for prefecture in prefectures:
                for area in prefecture.areas:
                    for i, mesh in enumerate(area.meshes):
                        area.meshes[i] = self.calculation_service.process_mesh_calculations(
                            mesh, swi_grib2, guidance_grib2
                        )

            # 市町村別雨量時系列を抽出
            area_rainfall = self.rainfall_service.extract_area_rainfall_timeseries(
                prefectures, guidance_grib2
            )

            # 二次細分別雨量時系列を抽出
            subdivision_rainfall = self.rainfall_service.extract_subdivision_rainfall_timeseries(
                prefectures, guidance_grib2
            )

            return jsonify({
                "status": "success",
                "swi_initial_time": swi_initial.isoformat(),
                "guidance_initial_time": guidance_initial.isoformat(),
                "area_rainfall": area_rainfall,
                "subdivision_rainfall": subdivision_rainfall
            })

        except Exception as e:
            logger.error(f"雨量予想取得エラー: {e}", exc_info=True)
            return jsonify({
                "status": "error",
                "message": str(e)
            }), 500

    def calculate_with_adjusted_rainfall(self):
        """
        調整後雨量でSWI・危険度を再計算

        Request Body:
            {
                "swi_initial": "2025-10-28T12:00:00Z",
                "guidance_initial": "2025-10-28T12:00:00Z",
                "area_adjustments": {
                    "滋賀県_大津市": {
                        "0": 10.0,   # ft: 調整後雨量
                        "3": 15.0,
                        ...
                    },
                    ...
                }
            }

        Returns:
            CalculationResult（既存と同じ形式）
        """
        try:
            # デバッグ: Content-Typeを確認
            logger.info(f"Content-Type: {request.content_type}")
            logger.info(f"Request data (raw): {request.data[:200]}")  # 最初の200バイトのみ

            data = request.get_json(force=True)  # force=Trueで強制的にJSONとしてパース
            if not data:
                return jsonify({
                    "status": "error",
                    "message": "リクエストデータが必要です"
                }), 400

            # パラメータ取得
            swi_initial_str = data.get('swi_initial')
            guidance_initial_str = data.get('guidance_initial')
            area_adjustments = data.get('area_adjustments', {})

            if not swi_initial_str or not guidance_initial_str:
                return jsonify({
                    "status": "error",
                    "message": "swi_initialとguidance_initialが必要です"
                }), 400

            # 日時パース
            try:
                swi_initial = datetime.fromisoformat(swi_initial_str.replace('Z', '+00:00'))
                swi_initial = swi_initial.replace(tzinfo=None)
            except ValueError as e:
                return jsonify({
                    "status": "error",
                    "message": f"swi_initial日時形式エラー: {e}"
                }), 400

            try:
                guidance_initial = datetime.fromisoformat(guidance_initial_str.replace('Z', '+00:00'))
                guidance_initial = guidance_initial.replace(tzinfo=None)
            except ValueError as e:
                return jsonify({
                    "status": "error",
                    "message": f"guidance_initial日時形式エラー: {e}"
                }), 400

            # area_adjustmentsのキーを整数に変換
            converted_adjustments = {}
            for area_key, adjustments in area_adjustments.items():
                converted_adjustments[area_key] = {
                    int(ft): float(value)
                    for ft, value in adjustments.items()
                }

            logger.info(f"雨量調整再計算: SWI={swi_initial}, ガイダンス={guidance_initial}")
            logger.info(f"調整対象市町村数: {len(converted_adjustments)}")

            # テストデータ判定（2023-06-02はテストデータ）
            is_test_data = (
                swi_initial.year == 2023 and
                swi_initial.month == 6 and
                swi_initial.day == 2 and
                swi_initial.hour == 0
            )

            if is_test_data:
                # ローカルテストデータを使用
                logger.info("テストデータモード: ローカルbinファイルを使用します")
                import os

                swi_filename = "Z__C_RJTD_20230602000000_SRF_GPV_Ggis1km_Psw_Aper10min_ANAL_grib2.bin"
                guidance_filename = "guid_msm_grib2_20230602000000_rmax00.bin"

                swi_path = os.path.join("data", swi_filename)
                guidance_path = os.path.join("data", guidance_filename)

                if not os.path.exists(swi_path):
                    raise Exception(f"テストデータファイルが見つかりません: {swi_path}")
                if not os.path.exists(guidance_path):
                    raise Exception(f"テストデータファイルが見つかりません: {guidance_path}")

                with open(swi_path, 'rb') as f:
                    swi_data_bytes = f.read()
                with open(guidance_path, 'rb') as f:
                    guidance_data_bytes = f.read()

                logger.info(f"ローカルファイル読み込み完了: {swi_filename}, {guidance_filename}")
            else:
                # 本番データをダウンロード
                logger.info("本番データモード: 気象庁サーバーからダウンロードします")
                from src.config.config_service import ConfigService
                config_service = ConfigService()

                swi_url = config_service.build_swi_url(swi_initial)
                guidance_url = config_service.build_guidance_url(guidance_initial)

                logger.info(f"SWI URL: {swi_url}")
                logger.info(f"Guidance URL: {guidance_url}")

                # データダウンロード
                swi_data_bytes = self.grib2_service.download_file(swi_url)
                if not swi_data_bytes:
                    raise Exception(f"SWIファイルダウンロード失敗: {swi_url}")

                guidance_data_bytes = self.grib2_service.download_file(guidance_url)
                if not guidance_data_bytes:
                    raise Exception(f"ガイダンスファイルダウンロード失敗: {guidance_url}")

            # GRIB2解析
            base_info, swi_grib2 = self.grib2_service.unpack_swi_grib2(swi_data_bytes)
            _, guidance_grib2 = self.grib2_service.unpack_guidance_grib2(guidance_data_bytes)

            # ガイダンスデータフィルタリング
            guidance_grib2 = self.main_service._filter_guidance_data(
                guidance_grib2, swi_initial, guidance_initial
            )

            # 地域データ構築
            prefectures = self.data_service.prepare_areas()

            # 調整対象の市町村/二次細分キーセットを作成
            adjusted_area_keys = set(converted_adjustments.keys())
            logger.info(f"調整対象市町村/二次細分: {len(adjusted_area_keys)}件")

            # 調整対象メッシュコードを収集（市町村別と二次細分別の両方に対応）
            adjusted_mesh_codes = set()
            adjusted_municipality_keys = set()  # 市町村キーを保存

            for prefecture in prefectures:
                # 市町村別の調整を確認
                for area in prefecture.areas:
                    area_key = f"{prefecture.name}_{area.name}"
                    if area_key in adjusted_area_keys:
                        adjusted_municipality_keys.add(area_key)
                        for mesh in area.meshes:
                            adjusted_mesh_codes.add(mesh.code)

                # 二次細分別の調整を確認
                for subdivision in prefecture.secondary_subdivisions:
                    subdiv_key = f"{prefecture.name}_{subdivision.name}"
                    if subdiv_key in adjusted_area_keys:
                        # この二次細分に所属する全市町村を追加
                        for area in subdivision.areas:
                            area_key = f"{prefecture.name}_{area.name}"
                            adjusted_municipality_keys.add(area_key)
                            for mesh in area.meshes:
                                adjusted_mesh_codes.add(mesh.code)

            logger.info(f"調整対象メッシュ数: {len(adjusted_mesh_codes)}件（全{sum(len(a.meshes) for p in prefectures for a in p.areas)}件中）")
            logger.info(f"調整対象市町村数: {len(adjusted_municipality_keys)}件")

            # 調整対象メッシュのみ計算（元の雨量データ）
            calculated_count = 0
            for prefecture in prefectures:
                for area in prefecture.areas:
                    for i, mesh in enumerate(area.meshes):
                        if mesh.code in adjusted_mesh_codes:
                            area.meshes[i] = self.calculation_service.process_mesh_calculations(
                                mesh, swi_grib2, guidance_grib2
                            )
                            calculated_count += 1

            logger.info(f"初期計算完了: {calculated_count}メッシュ")

            # メッシュごとの調整比率を計算
            mesh_ratios = self.rainfall_service._calculate_mesh_ratios(
                converted_adjustments,
                prefectures,
                guidance_grib2
            )

            # メッシュの雨量データを調整
            self.rainfall_service.adjust_mesh_rainfall_by_ratios(
                prefectures,
                mesh_ratios
            )

            # 調整後の雨量でSWI・危険度を再計算（調整対象メッシュのみ）
            recalculated_count = 0
            for prefecture in prefectures:
                for area in prefecture.areas:
                    for i, mesh in enumerate(area.meshes):
                        if mesh.code in adjusted_mesh_codes:
                            # 雨量は既に調整済みなので、SWIと危険度のみ再計算
                            area.meshes[i] = self.calculation_service.recalculate_swi_and_risk(
                                mesh
                            )
                            recalculated_count += 1

            logger.info(f"再計算完了: {recalculated_count}メッシュ")

            # リスクタイムライン計算（調整対象市町村のみ）
            risk_calculated_count = 0
            for prefecture in prefectures:
                for area in prefecture.areas:
                    area_key = f"{prefecture.name}_{area.name}"
                    if area_key in adjusted_municipality_keys:
                        area.risk_timeline = self.calculation_service.calc_risk_timeline(area.meshes)
                        risk_calculated_count += 1

            logger.info(f"リスクタイムライン計算完了: {risk_calculated_count}市町村")
            logger.info(f"調整対象キー（最初の5件）: {list(adjusted_area_keys)[:5]}")
            logger.info(f"調整対象市町村キー（最初の5件）: {list(adjusted_municipality_keys)[:5]}")

            # 結果構築（既存のmain_serviceと同じ形式）
            result = {
                "status": "success",
                "calculation_time": datetime.utcnow().isoformat(),
                "initial_time": swi_initial.isoformat(),
                "swi_initial_time": swi_initial.isoformat(),
                "guid_initial_time": guidance_initial.isoformat(),
                "adjusted": True,  # 調整済みフラグ
                "prefectures": {}
            }

            # データ構造を辞書形式に変換（調整対象市町村のみ）
            for prefecture in prefectures:
                pref_data = {
                    "name": prefecture.name,
                    "code": prefecture.code,
                    "areas": []
                }

                for area in prefecture.areas:
                    area_key = f"{prefecture.name}_{area.name}"
                    # 調整対象市町村のみ出力
                    if area_key not in adjusted_municipality_keys:
                        continue

                    area_data = {
                        "name": area.name,
                        "meshes": [],
                        "risk_timeline": [
                            {"ft": r.ft, "value": r.value}
                            for r in area.risk_timeline
                        ]
                    }

                    for mesh in area.meshes:
                        # 調整対象メッシュのみ出力
                        if mesh.code not in adjusted_mesh_codes:
                            continue

                        mesh_data = {
                            "code": mesh.code,
                            "lat": mesh.lat,
                            "lon": mesh.lon,
                            "advisary_bound": mesh.advisary_bound,
                            "warning_bound": mesh.warning_bound,
                            "dosyakei_bound": mesh.dosyakei_bound,
                            "swi_timeline": [
                                {"ft": s.ft, "value": s.value}
                                for s in mesh.swi
                            ],
                            "rain_timeline": [
                                {"ft": r.ft, "value": r.value}
                                for r in mesh.rain_3hour
                            ],
                            "risk_3hour_max_timeline": [
                                {"ft": r.ft, "value": r.value}
                                for r in mesh.risk_3hour_max
                            ]
                        }
                        area_data["meshes"].append(mesh_data)

                    # メッシュが存在する市町村のみ追加
                    if area_data["meshes"]:
                        pref_data["areas"].append(area_data)

                # 市町村が存在する府県のみ追加
                if pref_data["areas"]:
                    result["prefectures"][prefecture.code] = pref_data

            logger.info(f"レスポンス府県数: {len(result['prefectures'])}")
            logger.info(f"レスポンス府県コード: {list(result['prefectures'].keys())}")

            return jsonify(result)

        except Exception as e:
            logger.error(f"雨量調整再計算エラー: {e}", exc_info=True)
            return jsonify({
                "status": "error",
                "message": str(e)
            }), 500
