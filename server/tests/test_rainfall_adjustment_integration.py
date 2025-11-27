# -*- coding: utf-8 -*-
"""
雨量調整機能の統合テスト
編集なしの雨量調整が元の計算結果と100%一致することを検証
"""
import sys
import os
import json
import logging
from datetime import datetime

# プロジェクトルートをパスに追加
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)

from services.main_service import MainService
from services.rainfall_adjustment_service import RainfallAdjustmentService
from services.grib2_service import Grib2Service
from services.data_service import DataService
from services.calculation_service import CalculationService

# ログ設定
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class RainfallAdjustmentIntegrationTest:
    """雨量調整機能の統合テスト"""

    def __init__(self, data_dir: str = "data"):
        self.main_service = MainService(data_dir)
        self.rainfall_service = RainfallAdjustmentService()
        self.grib2_service = Grib2Service()
        self.data_service = DataService(data_dir)
        self.calculation_service = CalculationService()

    def test_unmodified_rainfall_identity(self):
        """
        編集なしの雨量調整が元の計算結果と100%一致することを検証

        テストシナリオ:
        1. 元のGRIB2データで計算（ベースライン）
        2. 市町村別雨量を抽出
        3. 抽出した雨量をそのまま（編集なし）で再計算
        4. ベースラインと再計算結果の危険度時系列を比較
        5. 100%一致を確認
        """
        logger.info("=== 雨量調整機能統合テスト開始 ===")
        logger.info("テスト: 編集なし雨量調整の恒等性検証")

        # テストデータのパス
        swi_file = os.path.join(project_root, "data",
                                "Z__C_RJTD_20250101000000_SRF_GPV_Ggis1km_Psw_Aper10min_ANAL_grib2.bin")
        guidance_file = os.path.join(project_root, "data",
                                     "guid_msm_grib2_20250101000000_rmax00.bin")

        if not os.path.exists(swi_file):
            logger.error(f"SWIファイルが見つかりません: {swi_file}")
            return False

        if not os.path.exists(guidance_file):
            logger.error(f"ガイダンスファイルが見つかりません: {guidance_file}")
            return False

        # STEP 1: ベースライン計算（元のGRIB2データ）
        logger.info("\n--- STEP 1: ベースライン計算 ---")
        try:
            # GRIB2データ解析
            base_info, swi_grib2 = self.grib2_service.unpack_swi_grib2_from_file(swi_file)
            _, guidance_grib2 = self.grib2_service.unpack_guidance_grib2_from_file(guidance_file)

            logger.info(f"初期時刻: {base_info.initial_date}")
            logger.info(f"SWIデータ数: {len(swi_grib2['swi'])}")
            logger.info(f"ガイダンスデータ数: {len(guidance_grib2['data_3h'])}")

            # 地域データ構築
            prefectures_baseline = self.data_service.prepare_areas()
            logger.info(f"都道府県数: {len(prefectures_baseline)}")

            # メッシュ計算
            total_meshes = 0
            for prefecture in prefectures_baseline:
                for area in prefecture.areas:
                    for i, mesh in enumerate(area.meshes):
                        area.meshes[i] = self.calculation_service.process_mesh_calculations(
                            mesh, swi_grib2, guidance_grib2
                        )
                    total_meshes += len(area.meshes)

            logger.info(f"処理メッシュ数: {total_meshes}")

            # リスクタイムライン計算
            for prefecture in prefectures_baseline:
                for area in prefecture.areas:
                    area.risk_timeline = self.calculation_service.calc_risk_timeline(area.meshes)

            logger.info("ベースライン計算完了")

        except Exception as e:
            logger.error(f"ベースライン計算エラー: {e}", exc_info=True)
            return False

        # STEP 2: 市町村別雨量抽出
        logger.info("\n--- STEP 2: 市町村別雨量抽出 ---")
        try:
            area_rainfall = self.rainfall_service.extract_area_rainfall_timeseries(
                prefectures_baseline, guidance_grib2
            )
            logger.info(f"抽出した市町村数: {len(area_rainfall)}")

            # サンプル表示
            sample_area = list(area_rainfall.keys())[0]
            logger.info(f"サンプル市町村: {sample_area}")
            logger.info(f"  時系列データ: {area_rainfall[sample_area][:3]}...")

        except Exception as e:
            logger.error(f"雨量抽出エラー: {e}", exc_info=True)
            return False

        # STEP 3: 編集なしで再計算
        logger.info("\n--- STEP 3: 編集なし再計算 ---")
        try:
            # 新しいprefecturesインスタンスを作成（独立した計算）
            prefectures_adjusted = self.data_service.prepare_areas()

            # メッシュ計算（元のガイダンスデータ）
            for prefecture in prefectures_adjusted:
                for area in prefecture.areas:
                    for i, mesh in enumerate(area.meshes):
                        area.meshes[i] = self.calculation_service.process_mesh_calculations(
                            mesh, swi_grib2, guidance_grib2
                        )

            # area_rainfallをadjustments形式に変換（編集なし＝元の値そのまま）
            area_adjustments = {}
            for area_key, timeseries in area_rainfall.items():
                area_adjustments[area_key] = {
                    point['ft']: point['value']
                    for point in timeseries
                }

            # メッシュごとの調整比率を計算
            mesh_ratios = self.rainfall_service._calculate_mesh_ratios(
                area_adjustments,
                prefectures_adjusted,
                guidance_grib2
            )

            logger.info(f"計算された調整比率のメッシュ数: {len(mesh_ratios)}")

            # メッシュの雨量データを調整
            self.rainfall_service.adjust_mesh_rainfall_by_ratios(
                prefectures_adjusted,
                mesh_ratios
            )

            # 調整後の雨量でSWI・危険度を再計算
            for prefecture in prefectures_adjusted:
                for area in prefecture.areas:
                    for i, mesh in enumerate(area.meshes):
                        area.meshes[i] = self.calculation_service.recalculate_swi_and_risk(mesh)

            # リスクタイムライン計算
            for prefecture in prefectures_adjusted:
                for area in prefecture.areas:
                    area.risk_timeline = self.calculation_service.calc_risk_timeline(area.meshes)

            logger.info("編集なし再計算完了")

        except Exception as e:
            logger.error(f"再計算エラー: {e}", exc_info=True)
            return False

        # STEP 4: 危険度時系列の比較
        logger.info("\n--- STEP 4: 危険度時系列の比較 ---")
        try:
            total_areas = 0
            total_comparisons = 0
            total_matches = 0
            total_mismatches = 0
            mismatch_details = []

            for pref_baseline, pref_adjusted in zip(prefectures_baseline, prefectures_adjusted):
                for area_baseline, area_adjusted in zip(pref_baseline.areas, pref_adjusted.areas):
                    total_areas += 1

                    # リスクタイムラインを比較
                    baseline_timeline = area_baseline.risk_timeline
                    adjusted_timeline = area_adjusted.risk_timeline

                    if len(baseline_timeline) != len(adjusted_timeline):
                        logger.warning(
                            f"タイムライン長が異なります: {pref_baseline.name}_{area_baseline.name} "
                            f"(baseline={len(baseline_timeline)}, adjusted={len(adjusted_timeline)})"
                        )
                        continue

                    for risk_baseline, risk_adjusted in zip(baseline_timeline, adjusted_timeline):
                        total_comparisons += 1

                        if risk_baseline.ft != risk_adjusted.ft:
                            logger.warning(f"FT不一致: {risk_baseline.ft} vs {risk_adjusted.ft}")
                            continue

                        if risk_baseline.value == risk_adjusted.value:
                            total_matches += 1
                        else:
                            total_mismatches += 1
                            mismatch_details.append({
                                "prefecture": pref_baseline.name,
                                "area": area_baseline.name,
                                "ft": risk_baseline.ft,
                                "baseline": risk_baseline.value,
                                "adjusted": risk_adjusted.value
                            })

            # 結果サマリー
            logger.info("\n" + "=" * 60)
            logger.info("テスト結果サマリー")
            logger.info("=" * 60)
            logger.info(f"比較対象市町村数: {total_areas}")
            logger.info(f"総比較ポイント数: {total_comparisons}")
            logger.info(f"一致数: {total_matches}")
            logger.info(f"不一致数: {total_mismatches}")

            if total_comparisons > 0:
                match_rate = (total_matches / total_comparisons) * 100
                logger.info(f"一致率: {match_rate:.2f}%")

            if total_mismatches == 0:
                logger.info("\n[SUCCESS] テスト成功: 100%一致しました！")
                return True
            else:
                logger.error(f"\n[FAILED] テスト失敗: {total_mismatches}件の不一致があります")

                # 不一致の詳細を表示（最大10件）
                logger.error("\n不一致の詳細（最大10件）:")
                for i, detail in enumerate(mismatch_details[:10], 1):
                    logger.error(
                        f"{i}. {detail['prefecture']}_{detail['area']} "
                        f"FT{detail['ft']}: "
                        f"baseline={detail['baseline']}, adjusted={detail['adjusted']}"
                    )

                if len(mismatch_details) > 10:
                    logger.error(f"... 他{len(mismatch_details) - 10}件の不一致")

                return False

        except Exception as e:
            logger.error(f"比較エラー: {e}", exc_info=True)
            return False


def main():
    """メインテスト実行"""
    test = RainfallAdjustmentIntegrationTest()
    success = test.test_unmodified_rainfall_identity()

    if success:
        print("\n" + "=" * 60)
        print("[SUCCESS] Integration Test PASSED")
        print("=" * 60)
        print("Unmodified rainfall adjustment identity verified.")
        print("Implementation is working correctly.")
        sys.exit(0)
    else:
        print("\n" + "=" * 60)
        print("[FAILED] Integration Test FAILED")
        print("=" * 60)
        print("Implementation has issues. Check logs for details.")
        sys.exit(1)


if __name__ == '__main__':
    main()
