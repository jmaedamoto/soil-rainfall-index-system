# -*- coding: utf-8 -*-
"""
メイン処理サービス
"""
from typing import Dict, Any, Tuple, Optional, Callable
import logging
from datetime import datetime, timedelta
import time
import os

from models import Prefecture
from .grib2_service import Grib2Service
from .data_service import DataService
from .calculation_service import CalculationService
from .cache_service import get_cache_service
from .response_builder import ResponseBuilder
from config.config_service import ConfigService


logger = logging.getLogger(__name__)


class MainService:
    """メイン処理サービス"""

    def __init__(self, data_dir: str = "data"):
        self.grib2_service = Grib2Service()
        self.data_service = DataService(data_dir)
        self.calculation_service = CalculationService()
        self.cache_service = get_cache_service()
        self.config_service = ConfigService()

    def main_process_from_files(self, swi_file: str, guidance_file: str) -> Dict[str, Any]:
        """ファイルベースのメイン処理（テスト用）"""
        try:
            start_time = time.time()
            base_info, swi_grib2, guidance_grib2 = self._parse_grib2_from_files(
                swi_file, guidance_file
            )
            result, total_meshes = self._run_calculation_pipeline(
                swi_grib2, guidance_grib2, base_info.initial_date
            )

            total_time = time.time() - start_time
            result["status"] = "success"
            result["note"] = "フル版: ローカルbinファイルからの実データ（全メッシュ処理）"

            logger.info(f"総処理時間: {total_time:.2f}秒")
            logger.info(f"処理速度: {total_meshes/total_time:.0f} meshes/second")

            return result

        except Exception as e:
            logger.error(f"メイン処理エラー: {e}")
            raise

    def main_process_from_urls(self, initial_time: datetime) -> Dict[str, Any]:
        """URL ベースのメイン処理"""
        try:
            # 設定ファイルからURL構築
            swi_url = self.config_service.build_swi_url(initial_time)
            guidance_url = self.config_service.build_guidance_url(initial_time, "msm")
            base_info, swi_grib2, guidance_grib2 = self._parse_grib2_from_urls(
                swi_url, guidance_url
            )
            result, _ = self._run_calculation_pipeline(
                swi_grib2, guidance_grib2, initial_time
            )
            return result

        except Exception as e:
            logger.error(f"URL ベースメイン処理エラー: {e}")
            raise

    def main_process_from_separate_urls(
        self,
        swi_url: str,
        guidance_url: str,
        guidance_type: str = "msm",
        risk_rule: str = "legacy",
        use_cache: bool = True,
        async_cache_save: bool = True,
        on_cache_saved: Optional[Callable[[bool], None]] = None,
    ) -> Dict[str, Any]:
        """
        個別URLベースのメイン処理（SWIとガイダンスのURLを個別指定）

        Args:
            swi_url: SWI GRIB2データURL
            guidance_url: ガイダンスGRIB2データURL
            use_cache: キャッシュ使用フラグ（デフォルト: True）

        Returns:
            処理結果JSON
        """
        try:
            base_info, swi_grib2, guidance_base_info, guidance_grib2 = (
                self._parse_separate_grib2_from_urls(swi_url, guidance_url)
            )

            # SWI初期時刻を使用
            swi_initial_time = base_info.initial_date
            guidance_initial_time = guidance_base_info.initial_date

            logger.info(f"SWI初期時刻: {swi_initial_time}")
            logger.info(f"ガイダンス初期時刻: {guidance_initial_time}")

            # キャッシュキー生成
            normalized_guidance_type = self.config_service.normalize_guidance_type(guidance_type)
            normalized_risk_rule = self.calculation_service.normalize_risk_rule(risk_rule)
            cache_key = self.cache_service.generate_cache_key(
                swi_initial_time.isoformat(),
                guidance_initial_time.isoformat(),
                normalized_guidance_type,
                normalized_risk_rule,
            )

            # キャッシュチェック
            if use_cache:
                cached_result = self.cache_service.get_cached_result(cache_key)
                if cached_result:
                    logger.info(f"キャッシュヒット: {cache_key}")
                    return cached_result

            logger.info(f"キャッシュミス: {cache_key} - 計算を実行")

            # SWI初期時刻以降のガイダンスデータのみを使用
            guidance_grib2_filtered = self._filter_guidance_data(
                guidance_grib2, swi_initial_time, guidance_initial_time
            )

            # 計算処理実行
            result, _ = self._run_calculation_pipeline(
                swi_grib2, guidance_grib2_filtered, swi_initial_time, normalized_risk_rule
            )

            # キャッシュ保存はレスポンスをブロックしないよう非同期で実行
            if use_cache:
                if async_cache_save:
                    self.cache_service.set_cached_result_async(
                        cache_key,
                        result,
                        swi_initial_time.isoformat(),
                        guidance_initial_time.isoformat(),
                        normalized_guidance_type,
                        normalized_risk_rule,
                        on_cache_saved,
                    )
                else:
                    self.cache_service.set_cached_result(
                        cache_key,
                        result,
                        swi_initial_time.isoformat(),
                        guidance_initial_time.isoformat(),
                        normalized_guidance_type,
                        normalized_risk_rule,
                    )

            return result

        except Exception as e:
            logger.error(f"個別URLベースメイン処理エラー: {e}")
            raise

    def _parse_grib2_from_files(self, swi_file: str, guidance_file: str):
        """ローカルファイルからGRIB2を解析する"""
        logger.info("GRIB2ファイル解析開始")
        grib2_start = time.time()

        base_info, swi_grib2 = self.grib2_service.unpack_swi_grib2_from_file(swi_file)
        _, guidance_grib2 = self.grib2_service.unpack_guidance_grib2_from_file(guidance_file)

        self._log_grib2_parse_summary(
            base_info.initial_date,
            swi_grib2,
            guidance_grib2,
            time.time() - grib2_start,
        )
        return base_info, swi_grib2, guidance_grib2

    def _parse_grib2_from_urls(self, swi_url: str, guidance_url: str):
        """同一初期時刻のURLからGRIB2を取得して解析する"""
        swi_data_bytes, guidance_data_bytes = self._load_grib2_bytes(
            swi_url, guidance_url
        )
        base_info, swi_grib2 = self.grib2_service.unpack_swi_grib2(swi_data_bytes)
        _, guidance_grib2 = self.grib2_service.unpack_guidance_grib2(guidance_data_bytes)
        return base_info, swi_grib2, guidance_grib2

    def _parse_separate_grib2_from_urls(self, swi_url: str, guidance_url: str):
        """個別URLからGRIB2を取得して解析する"""
        swi_data_bytes, guidance_data_bytes = self._load_grib2_bytes(
            swi_url, guidance_url
        )
        base_info, swi_grib2 = self.grib2_service.unpack_swi_grib2(swi_data_bytes)
        guidance_base_info, guidance_grib2 = self.grib2_service.unpack_guidance_grib2(
            guidance_data_bytes
        )
        return base_info, swi_grib2, guidance_base_info, guidance_grib2

    def _log_grib2_parse_summary(
        self,
        initial_time: datetime,
        swi_grib2: Dict[str, Any],
        guidance_grib2: Dict[str, Any],
        elapsed_seconds: float,
    ) -> None:
        """GRIB2解析結果の要約を出力する"""
        logger.info(f"GRIB2解析完了: {elapsed_seconds:.2f}秒")
        logger.info(f"初期時刻: {initial_time}")
        logger.info(f"SWIデータ数: {len(swi_grib2['swi'])}")
        logger.info(f"ガイダンスデータ数: {len(guidance_grib2['data'])}")

    def _run_calculation_pipeline(
        self,
        swi_grib2: Dict[str, Any],
        guidance_grib2: Dict[str, Any],
        initial_time: datetime,
        risk_rule: str = "legacy",
    ) -> Tuple[Dict[str, Any], int]:
        """地域データ準備からレスポンス構築までの計算パイプライン"""
        prefectures = self._prepare_prefectures()
        total_meshes = self._calculate_meshes(prefectures, swi_grib2, guidance_grib2, risk_rule)
        self._aggregate_risk_timelines(prefectures, risk_rule)
        result = ResponseBuilder.build_prefecture_response(prefectures, initial_time)
        return result, total_meshes

    def _prepare_prefectures(self):
        """地域データを構築する"""
        logger.info("地域データ構築開始")
        area_start = time.time()
        prefectures = self.data_service.prepare_areas()
        logger.info(f"地域データ構築完了: {time.time() - area_start:.2f}秒")
        return prefectures

    def _calculate_meshes(
        self,
        prefectures,
        swi_grib2: Dict[str, Any],
        guidance_grib2: Dict[str, Any],
        risk_rule: str = "legacy",
    ) -> int:
        """メッシュ単位の計算を実行する"""
        logger.info("メッシュ計算処理開始")
        calc_start = time.time()
        total_meshes = 0

        for prefecture in prefectures:
            for area in prefecture.areas:
                for mesh in area.meshes:
                    self.calculation_service.process_mesh_calculations(
                        mesh, swi_grib2, guidance_grib2, risk_rule=risk_rule
                    )
                    total_meshes += 1

        logger.info(
            f"メッシュ計算完了: {time.time() - calc_start:.2f}秒 ({total_meshes}メッシュ)"
        )
        return total_meshes

    def _aggregate_risk_timelines(self, prefectures, risk_rule: str = "legacy") -> None:
        """エリア・二次細分・府県単位の集約を実行する"""
        logger.info("リスクタイムライン計算開始")
        risk_start = time.time()

        for prefecture in prefectures:
            for area in prefecture.areas:
                area.risk_timeline = self.calculation_service.calc_risk_timeline(
                    area.meshes, risk_rule=risk_rule
                )

            for subdivision in prefecture.secondary_subdivisions:
                self.calculation_service.calc_secondary_subdivision_aggregates(subdivision)

            self.calculation_service.calc_prefecture_aggregates(prefecture)

        logger.info(
            f"リスクタイムライン・集約計算完了: {time.time() - risk_start:.2f}秒"
        )

    def _load_grib2_bytes(self, swi_url: str, guidance_url: str) -> Tuple[bytes, bytes]:
        """GRIB2データを設定に従って取得する"""
        fallback_config = self.config_service.get_local_grib2_fallback_config()

        if fallback_config["enabled"]:
            fallback_swi_path = fallback_config["swi_path"]
            fallback_guidance_path = fallback_config["guidance_path"]

            if fallback_swi_path and fallback_guidance_path:
                if os.path.exists(fallback_swi_path) and os.path.exists(fallback_guidance_path):
                    logger.info(f"ローカルGRIB2フォールバック使用: {fallback_swi_path}")
                    logger.info(f"ローカルGRIB2フォールバック使用: {fallback_guidance_path}")
                    with open(fallback_swi_path, 'rb') as f:
                        swi_data_bytes = f.read()
                    with open(fallback_guidance_path, 'rb') as f:
                        guidance_data_bytes = f.read()
                    return swi_data_bytes, guidance_data_bytes

                logger.warning("ローカルGRIB2フォールバックが有効ですが、指定ファイルが見つかりません")

        logger.info(f"SWI URL: {swi_url}")
        logger.info(f"Guidance URL: {guidance_url}")

        swi_data_bytes = self.grib2_service.download_file(swi_url)
        if not swi_data_bytes:
            raise Exception(f"SWIファイル取得失敗: {swi_url}")

        guidance_data_bytes = self.grib2_service.download_file(guidance_url)
        if not guidance_data_bytes:
            raise Exception(f"ガイダンスファイル取得失敗: {guidance_url}")

        return swi_data_bytes, guidance_data_bytes

    def _filter_guidance_data(self, guidance_grib2: Dict[str, Any],
                              swi_initial_time: datetime,
                              guidance_initial_time: datetime) -> Dict[str, Any]:
        """
        SWI初期時刻以降のガイダンスデータのみを抽出

        Args:
            guidance_grib2: ガイダンスGRIB2データ
            swi_initial_time: SWI初期時刻
            guidance_initial_time: ガイダンス初期時刻

        Returns:
            フィルタリングされたガイダンスデータ
        """
        # 時刻差を計算（時間単位）
        time_diff_hours = (swi_initial_time - guidance_initial_time).total_seconds() / 3600

        logger.info(f"時刻差: {time_diff_hours}時間 (SWI - ガイダンス)")

        # SWI初期時刻がガイダンス初期時刻と同じかそれ以前の場合、全データを使用
        if time_diff_hours <= 0:
            logger.info("SWI初期時刻 <= ガイダンス初期時刻のため、全ガイダンスデータを使用")
            return guidance_grib2

        # フィルタリング処理
        filtered_grib2 = {
            'base_info': guidance_grib2['base_info']
        }

        # 各データキーに対してフィルタリング
        for key in ['data', 'data_1h', 'data_3h']:
            if key not in guidance_grib2:
                continue

            filtered_data = []
            for item in guidance_grib2[key]:
                # ガイダンスデータの実際の時刻を計算
                # item['ft']は初期時刻からの予測時間（時間単位）
                data_time = guidance_initial_time + timedelta(hours=item['ft'])

                # SWI初期時刻以降のデータのみを使用
                if data_time >= swi_initial_time:
                    # FTをSWI初期時刻からの相対時間に再計算
                    new_ft = int((data_time - swi_initial_time).total_seconds() / 3600)
                    filtered_item = {
                        'ft': new_ft,
                        'value': item['value']
                    }
                    filtered_data.append(filtered_item)
                    logger.debug(f"ガイダンスデータ使用: 元FT={item['ft']}, 新FT={new_ft}, 時刻={data_time}")
                else:
                    logger.debug(f"ガイダンスデータ除外: FT={item['ft']}, 時刻={data_time} (SWI初期時刻より前)")

            filtered_grib2[key] = filtered_data
            logger.info(f"{key}: {len(guidance_grib2[key])}件 → {len(filtered_data)}件に絞り込み")

        return filtered_grib2
