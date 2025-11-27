# -*- coding: utf-8 -*-
"""
雨量調整機能の機能テスト
雨量増加・減少が危険度に正しく反映されることを検証
"""
import sys
import os
import logging

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


class RainfallAdjustmentFunctionalTest:
    """雨量調整機能の機能テスト"""

    def __init__(self, data_dir: str = "data"):
        self.main_service = MainService(data_dir)
        self.rainfall_service = RainfallAdjustmentService()
        self.grib2_service = Grib2Service()
        self.data_service = DataService(data_dir)
        self.calculation_service = CalculationService()

    def test_rainfall_increase_raises_risk(self):
        """
        雨量増加テスト: 雨量を2倍にすると危険度が上がることを検証
        """
        logger.info("=== 雨量増加テスト開始 ===")

        # テストデータのパス
        swi_file = os.path.join(project_root, "data",
                                "Z__C_RJTD_20250101000000_SRF_GPV_Ggis1km_Psw_Aper10min_ANAL_grib2.bin")
        guidance_file = os.path.join(project_root, "data",
                                     "guid_msm_grib2_20250101000000_rmax00.bin")

        if not os.path.exists(swi_file) or not os.path.exists(guidance_file):
            logger.error("テストファイルが見つかりません")
            return False

        try:
            # GRIB2データ解析
            base_info, swi_grib2 = self.grib2_service.unpack_swi_grib2_from_file(swi_file)
            _, guidance_grib2 = self.grib2_service.unpack_guidance_grib2_from_file(guidance_file)

            # 地域データ構築
            prefectures = self.data_service.prepare_areas()

            # ベースライン計算
            for prefecture in prefectures:
                for area in prefecture.areas:
                    for i, mesh in enumerate(area.meshes):
                        area.meshes[i] = self.calculation_service.process_mesh_calculations(
                            mesh, swi_grib2, guidance_grib2
                        )

            for prefecture in prefectures:
                for area in prefecture.areas:
                    area.risk_timeline = self.calculation_service.calc_risk_timeline(area.meshes)

            # ベースラインの危険度を記録
            baseline_risks = {}
            for prefecture in prefectures:
                for area in prefecture.areas:
                    area_key = f"{prefecture.name}_{area.name}"
                    baseline_risks[area_key] = [r.value for r in area.risk_timeline]

            # 雨量を抽出
            area_rainfall = self.rainfall_service.extract_area_rainfall_timeseries(
                prefectures, guidance_grib2
            )

            # 雨量を2倍に増加（最初の市町村のみ）
            test_area = list(area_rainfall.keys())[0]
            logger.info(f"テスト対象市町村: {test_area}")

            area_adjustments = {}
            for area_key, timeseries in area_rainfall.items():
                if area_key == test_area:
                    # 2倍に増加
                    area_adjustments[area_key] = {
                        point['ft']: point['value'] * 2.0
                        for point in timeseries
                    }
                    logger.info(f"  元の雨量（FT0）: {timeseries[0]['value']:.1f}mm")
                    logger.info(f"  調整後雨量（FT0）: {timeseries[0]['value'] * 2.0:.1f}mm")
                else:
                    # その他は変更なし
                    area_adjustments[area_key] = {
                        point['ft']: point['value']
                        for point in timeseries
                    }

            # 新しいprefecturesインスタンスを作成
            prefectures_adjusted = self.data_service.prepare_areas()

            # メッシュ計算
            for prefecture in prefectures_adjusted:
                for area in prefecture.areas:
                    for i, mesh in enumerate(area.meshes):
                        area.meshes[i] = self.calculation_service.process_mesh_calculations(
                            mesh, swi_grib2, guidance_grib2
                        )

            # 調整比率を計算・適用
            mesh_ratios = self.rainfall_service._calculate_mesh_ratios(
                area_adjustments,
                prefectures_adjusted,
                guidance_grib2
            )

            self.rainfall_service.adjust_mesh_rainfall_by_ratios(
                prefectures_adjusted,
                mesh_ratios
            )

            # 再計算
            for prefecture in prefectures_adjusted:
                for area in prefecture.areas:
                    for i, mesh in enumerate(area.meshes):
                        area.meshes[i] = self.calculation_service.recalculate_swi_and_risk(mesh)

            for prefecture in prefectures_adjusted:
                for area in prefecture.areas:
                    area.risk_timeline = self.calculation_service.calc_risk_timeline(area.meshes)

            # 調整後の危険度を記録
            adjusted_risks = {}
            for prefecture in prefectures_adjusted:
                for area in prefecture.areas:
                    area_key = f"{prefecture.name}_{area.name}"
                    adjusted_risks[area_key] = [r.value for r in area.risk_timeline]

            # 検証: テスト対象市町村の危険度が上がった（または同じ）ことを確認
            baseline_max = max(baseline_risks[test_area])
            adjusted_max = max(adjusted_risks[test_area])

            logger.info(f"\n検証結果:")
            logger.info(f"  ベースライン最大危険度: {baseline_max}")
            logger.info(f"  調整後最大危険度: {adjusted_max}")

            if adjusted_max >= baseline_max:
                logger.info(f"[SUCCESS] 雨量増加テスト成功: 危険度が上昇または維持されました")
                return True
            else:
                logger.error(f"[FAILED] 雨量増加テスト失敗: 危険度が低下しました")
                return False

        except Exception as e:
            logger.error(f"雨量増加テストエラー: {e}", exc_info=True)
            return False

    def test_rainfall_decrease_lowers_risk(self):
        """
        雨量減少テスト: 雨量を半分にすると危険度が下がることを検証
        """
        logger.info("\n=== 雨量減少テスト開始 ===")

        # テストデータのパス
        swi_file = os.path.join(project_root, "data",
                                "Z__C_RJTD_20250101000000_SRF_GPV_Ggis1km_Psw_Aper10min_ANAL_grib2.bin")
        guidance_file = os.path.join(project_root, "data",
                                     "guid_msm_grib2_20250101000000_rmax00.bin")

        if not os.path.exists(swi_file) or not os.path.exists(guidance_file):
            logger.error("テストファイルが見つかりません")
            return False

        try:
            # GRIB2データ解析
            base_info, swi_grib2 = self.grib2_service.unpack_swi_grib2_from_file(swi_file)
            _, guidance_grib2 = self.grib2_service.unpack_guidance_grib2_from_file(guidance_file)

            # 地域データ構築
            prefectures = self.data_service.prepare_areas()

            # ベースライン計算
            for prefecture in prefectures:
                for area in prefecture.areas:
                    for i, mesh in enumerate(area.meshes):
                        area.meshes[i] = self.calculation_service.process_mesh_calculations(
                            mesh, swi_grib2, guidance_grib2
                        )

            for prefecture in prefectures:
                for area in prefecture.areas:
                    area.risk_timeline = self.calculation_service.calc_risk_timeline(area.meshes)

            # ベースラインの危険度を記録
            baseline_risks = {}
            for prefecture in prefectures:
                for area in prefecture.areas:
                    area_key = f"{prefecture.name}_{area.name}"
                    baseline_risks[area_key] = [r.value for r in area.risk_timeline]

            # 雨量を抽出
            area_rainfall = self.rainfall_service.extract_area_rainfall_timeseries(
                prefectures, guidance_grib2
            )

            # 雨量を半分に減少（最初の市町村のみ）
            test_area = list(area_rainfall.keys())[0]
            logger.info(f"テスト対象市町村: {test_area}")

            area_adjustments = {}
            for area_key, timeseries in area_rainfall.items():
                if area_key == test_area:
                    # 半分に減少
                    area_adjustments[area_key] = {
                        point['ft']: point['value'] * 0.5
                        for point in timeseries
                    }
                    logger.info(f"  元の雨量（FT0）: {timeseries[0]['value']:.1f}mm")
                    logger.info(f"  調整後雨量（FT0）: {timeseries[0]['value'] * 0.5:.1f}mm")
                else:
                    # その他は変更なし
                    area_adjustments[area_key] = {
                        point['ft']: point['value']
                        for point in timeseries
                    }

            # 新しいprefecturesインスタンスを作成
            prefectures_adjusted = self.data_service.prepare_areas()

            # メッシュ計算
            for prefecture in prefectures_adjusted:
                for area in prefecture.areas:
                    for i, mesh in enumerate(area.meshes):
                        area.meshes[i] = self.calculation_service.process_mesh_calculations(
                            mesh, swi_grib2, guidance_grib2
                        )

            # 調整比率を計算・適用
            mesh_ratios = self.rainfall_service._calculate_mesh_ratios(
                area_adjustments,
                prefectures_adjusted,
                guidance_grib2
            )

            self.rainfall_service.adjust_mesh_rainfall_by_ratios(
                prefectures_adjusted,
                mesh_ratios
            )

            # 再計算
            for prefecture in prefectures_adjusted:
                for area in prefecture.areas:
                    for i, mesh in enumerate(area.meshes):
                        area.meshes[i] = self.calculation_service.recalculate_swi_and_risk(mesh)

            for prefecture in prefectures_adjusted:
                for area in prefecture.areas:
                    area.risk_timeline = self.calculation_service.calc_risk_timeline(area.meshes)

            # 調整後の危険度を記録
            adjusted_risks = {}
            for prefecture in prefectures_adjusted:
                for area in prefecture.areas:
                    area_key = f"{prefecture.name}_{area.name}"
                    adjusted_risks[area_key] = [r.value for r in area.risk_timeline]

            # 検証: テスト対象市町村の危険度が下がった（または同じ）ことを確認
            baseline_max = max(baseline_risks[test_area])
            adjusted_max = max(adjusted_risks[test_area])

            logger.info(f"\n検証結果:")
            logger.info(f"  ベースライン最大危険度: {baseline_max}")
            logger.info(f"  調整後最大危険度: {adjusted_max}")

            if adjusted_max <= baseline_max:
                logger.info(f"[SUCCESS] 雨量減少テスト成功: 危険度が低下または維持されました")
                return True
            else:
                logger.error(f"[FAILED] 雨量減少テスト失敗: 危険度が上昇しました")
                return False

        except Exception as e:
            logger.error(f"雨量減少テストエラー: {e}", exc_info=True)
            return False


def main():
    """メインテスト実行"""
    test = RainfallAdjustmentFunctionalTest()

    # 雨量増加テスト
    increase_success = test.test_rainfall_increase_raises_risk()

    # 雨量減少テスト
    decrease_success = test.test_rainfall_decrease_lowers_risk()

    # 結果サマリー
    print("\n" + "=" * 60)
    print("Functional Test Summary")
    print("=" * 60)
    print(f"Rainfall Increase Test: {'PASSED' if increase_success else 'FAILED'}")
    print(f"Rainfall Decrease Test: {'PASSED' if decrease_success else 'FAILED'}")
    print("=" * 60)

    if increase_success and decrease_success:
        print("\n[SUCCESS] All functional tests passed")
        sys.exit(0)
    else:
        print("\n[FAILED] Some functional tests failed")
        sys.exit(1)


if __name__ == '__main__':
    main()
