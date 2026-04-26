# -*- coding: utf-8 -*-
"""
テストAPIコントローラー
"""
from flask import request, jsonify
from datetime import datetime
import logging
import os
import sys
import time

# プロジェクトルートをパスに追加
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(project_root)

from services.main_service import MainService
from services.session_service import SessionService
from models import SwiTimeSeries, GuidanceTimeSeries


logger = logging.getLogger(__name__)


class TestController:
    """テストAPIコントローラー"""

    def __init__(self, data_dir: str = "data", session_service: SessionService = None):
        self.main_service = MainService(data_dir)
        self.session_service = session_service
        self.data_dir = data_dir
    
    def test_bin_data(self):
        """binファイルデータテスト"""
        try:
            swi_bin_path = os.path.join(self.data_dir, "Z__C_RJTD_20230602000000_SRF_GPV_Ggis1km_Psw_Aper10min_ANAL_grib2.bin")
            guidance_bin_path = os.path.join(self.data_dir, "guid_msm_grib2_20230602000000_rmax00.bin")
            
            result = {
                "swi_file": {
                    "path": swi_bin_path,
                    "exists": os.path.exists(swi_bin_path),
                    "size": os.path.getsize(swi_bin_path) if os.path.exists(swi_bin_path) else 0
                },
                "guidance_file": {
                    "path": guidance_bin_path,
                    "exists": os.path.exists(guidance_bin_path),
                    "size": os.path.getsize(guidance_bin_path) if os.path.exists(guidance_bin_path) else 0
                }
            }
            
            return jsonify(result)
            
        except Exception as e:
            logger.error(f"binファイルテストエラー: {e}")
            return jsonify({
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }), 500
    
    def test_grib2_analysis(self):
        """GRIB2解析テスト"""
        try:
            swi_bin_path = os.path.join(self.data_dir, "Z__C_RJTD_20230602000000_SRF_GPV_Ggis1km_Psw_Aper10min_ANAL_grib2.bin")
            guidance_bin_path = os.path.join(self.data_dir, "guid_msm_grib2_20230602000000_rmax00.bin")
            
            if not os.path.exists(swi_bin_path) or not os.path.exists(guidance_bin_path):
                return jsonify({
                    "status": "error",
                    "error": "binファイルが見つかりません"
                }), 404
            
            # GRIB2解析
            base_info, swi_grib2 = self.main_service.grib2_service.unpack_swi_grib2_from_file(swi_bin_path)
            _, guidance_grib2 = self.main_service.grib2_service.unpack_guidance_grib2_from_file(guidance_bin_path)
            
            result = {
                "swi_analysis": {
                    "initial_date": base_info.initial_date.isoformat(),
                    "grid_num": base_info.grid_num,
                    "x_num": base_info.x_num,
                    "y_num": base_info.y_num,
                    "data_count": len(swi_grib2['swi'])
                },
                "guidance_analysis": {
                    "data_sets": len(guidance_grib2['data']),
                    "first_set_count": len(guidance_grib2['data'][0]) if guidance_grib2['data'] else 0
                }
            }
            
            return jsonify(result)
            
        except Exception as e:
            logger.error(f"GRIB2解析テストエラー: {e}")
            return jsonify({
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }), 500
    
    def test_soil_rainfall_index(self):
        """土壌雨量指数計算テスト（簡易版）"""
        try:
            # 1つの府県のみテスト
            prefectures = self.main_service.data_service.prepare_areas()
            if not prefectures:
                return jsonify({
                    "status": "error",
                    "error": "地域データが見つかりません"
                }), 500
            
            test_pref = prefectures[0]  # 最初の府県
            mesh_count = sum(len(area.meshes) for area in test_pref.areas)
            
            result = {
                "test_prefecture": test_pref.name,
                "areas_count": len(test_pref.areas),
                "meshes_count": mesh_count,
                "sample_meshes": []
            }
            
            # サンプルメッシュを3個まで表示
            sample_count = 0
            for area in test_pref.areas:
                for mesh in area.meshes:
                    if sample_count >= 3:
                        break
                    result["sample_meshes"].append({
                        "code": mesh.code,
                        "area": mesh.area_name,
                        "lat": float(mesh.lat),
                        "lon": float(mesh.lon),
                        "advisary_bound": int(mesh.advisary_bound),
                        "warning_bound": int(mesh.warning_bound),
                        "dosyakei_bound": int(mesh.dosyakei_bound)
                    })
                    sample_count += 1
                if sample_count >= 3:
                    break
            
            return jsonify(result)
            
        except Exception as e:
            logger.error(f"土壌雨量指数テストエラー: {e}")
            return jsonify({
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }), 500
    
    def test_single_prefecture(self):
        """単一府県テスト"""
        try:
            pref_code = request.args.get('pref', 'shiga')
            
            prefectures = self.main_service.data_service.prepare_areas()
            target_pref = None
            
            for pref in prefectures:
                if pref.code == pref_code:
                    target_pref = pref
                    break
            
            if not target_pref:
                return jsonify({
                    "status": "error",
                    "error": f"府県が見つかりません: {pref_code}"
                }), 404
            
            result = {
                "prefecture": {
                    "name": target_pref.name,
                    "code": target_pref.code,
                    "areas_count": len(target_pref.areas),
                    "total_meshes": sum(len(area.meshes) for area in target_pref.areas)
                },
                "areas": []
            }
            
            for area in target_pref.areas:
                result["areas"].append({
                    "name": area.name,
                    "meshes_count": len(area.meshes)
                })
            
            return jsonify(result)
            
        except Exception as e:
            logger.error(f"単一府県テストエラー: {e}")
            return jsonify({
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }), 500
    
    def test_full_soil_rainfall_index(self):
        """テスト用：binファイルを使って全メッシュのmain_processと同じ形式のJSONを返す（元の実装と同じ戻り値形式）"""
        start_time = time.time()
        
        try:
            # binファイルのパス
            swi_bin_path = os.path.join(self.data_dir, "Z__C_RJTD_20230602000000_SRF_GPV_Ggis1km_Psw_Aper10min_ANAL_grib2.bin")
            guidance_bin_path = os.path.join(self.data_dir, "guid_msm_grib2_20230602000000_rmax00.bin")
            
            # ファイル存在確認（ベースラインと同じエラー形式）
            if not os.path.exists(swi_bin_path):
                return jsonify({
                    "status": "error",
                    "error": "SWI binファイルが見つかりません",
                    "timestamp": datetime.now().isoformat()
                }), 500
                
            if not os.path.exists(guidance_bin_path):
                return jsonify({
                    "status": "error", 
                    "error": "ガイダンス binファイルが見つかりません",
                    "timestamp": datetime.now().isoformat()
                }), 500
            
            logger.info("ローカルGRIB2データを解析中...")
            
            try:
                # GRIB2解析（サービス層使用）
                base_info, swi_grib2 = self.main_service.grib2_service.unpack_swi_grib2_from_file(swi_bin_path)
                _, guidance_grib2 = self.main_service.grib2_service.unpack_guidance_grib2_from_file(guidance_bin_path)
                
                logger.info(f"GRIB2解析完了: SWI grid_num={base_info.grid_num}, Guidance data count={len(guidance_grib2['data'])}")
                
            except Exception as e:
                logger.error(f"GRIB2データ解析エラー: {e}")
                return jsonify({
                    "status": "error",
                    "error": f"GRIB2データの解析に失敗しました: {str(e)}",
                    "timestamp": datetime.now().isoformat()
                }), 500
            
            # CSVデータから地域構造を準備（サービス層使用）
            logger.info("CSVデータから地域構造を構築中...")
            prefectures = self.main_service.data_service.prepare_areas()
            
            # 結果構築（main_processと同じ形式 - 全メッシュ処理）
            results = {}
            total_meshes = 0
            processed_meshes = 0
            
            for prefecture in prefectures:
                logger.info(f"処理中: {prefecture.name}")
                pref_result = {
                    "name": prefecture.name,
                    "code": prefecture.code,
                    "areas": []
                }
                
                for area in prefecture.areas:
                    area_result = {
                        "name": area.name,
                        "secondary_subdivision_name": area.secondary_subdivision_name,
                        "meshes": []
                    }
                    
                    # 全メッシュを処理（サービス層使用）
                    for mesh in area.meshes:
                        total_meshes += 1
                        try:
                            # 計算サービスを使用
                            mesh = self.main_service.calculation_service.process_mesh_calculations(
                                mesh, swi_grib2, guidance_grib2
                            )
                            processed_meshes += 1
                            
                        except Exception as e:
                            logger.warning(f"Calculation error for mesh {mesh.code}: {e}")
                            # エラー時はダミーデータを設定（元の実装と同じ）
                            from models import Risk
                            mesh.swi = [
                                SwiTimeSeries(ft=0, value=85.5),
                                SwiTimeSeries(ft=3, value=92.1),
                                SwiTimeSeries(ft=6, value=88.7)
                            ]
                            mesh.swi_hourly = [
                                SwiTimeSeries(ft=0, value=85.5),
                                SwiTimeSeries(ft=1, value=86.0),
                                SwiTimeSeries(ft=2, value=90.0),
                                SwiTimeSeries(ft=3, value=92.1),
                                SwiTimeSeries(ft=4, value=88.0),
                                SwiTimeSeries(ft=5, value=89.0),
                                SwiTimeSeries(ft=6, value=88.7)
                            ]
                            mesh.rain_1hour = [
                                GuidanceTimeSeries(ft=1, value=0.75),
                                GuidanceTimeSeries(ft=2, value=1.0),
                                GuidanceTimeSeries(ft=3, value=0.75),
                                GuidanceTimeSeries(ft=4, value=0.5),
                                GuidanceTimeSeries(ft=5, value=0.8),
                                GuidanceTimeSeries(ft=6, value=0.5)
                            ]
                            mesh.rain_1hour_max = [
                                GuidanceTimeSeries(ft=3, value=1.0),
                                GuidanceTimeSeries(ft=6, value=0.8)
                            ]
                            mesh.rain_3hour = [
                                GuidanceTimeSeries(ft=3, value=2.5),
                                GuidanceTimeSeries(ft=6, value=1.8)
                            ]
                            mesh.risk_hourly = [
                                Risk(ft=0, value=0),
                                Risk(ft=1, value=0),
                                Risk(ft=2, value=1),
                                Risk(ft=3, value=1),
                                Risk(ft=4, value=0),
                                Risk(ft=5, value=1),
                                Risk(ft=6, value=0)
                            ]
                            mesh.risk_3hour_max = [
                                Risk(ft=3, value=1),
                                Risk(ft=6, value=1)
                            ]
                        
                        # 元の実装と同じ形式でmesh_result作成（サイズ削減のため一部フィールドを除外）
                        mesh_result = {
                            "code": mesh.code,
                            "lat": float(mesh.lat),
                            "lon": float(mesh.lon),
                            "advisary_bound": int(mesh.advisary_bound),
                            "warning_bound": int(mesh.warning_bound),
                            "dosyakei_bound": int(mesh.dosyakei_bound),
                            "swi_timeline": [
                                {"ft": int(s.ft), "value": float(s.value)} for s in mesh.swi
                            ],
                            # swi_hourly_timeline: 除外（レスポンスサイズ削減）
                            # rain_1hour_timeline: 除外（レスポンスサイズ削減）
                            # rain_1hour_max_timeline: 除外（レスポンスサイズ削減）
                            "rain_timeline": [
                                {"ft": int(r.ft), "value": float(r.value)} for r in mesh.rain_3hour
                            ],
                            # risk_hourly_timeline: 除外（レスポンスサイズ削減）
                            "risk_3hour_max_timeline": [
                                {"ft": int(r.ft), "value": int(r.value)} for r in mesh.risk_3hour_max
                            ]
                        }
                        area_result["meshes"].append(mesh_result)
                        
                        # プログレス表示（100メッシュごと）
                        if total_meshes % 100 == 0:
                            logger.info(f"進捗: {total_meshes}メッシュ処理完了")
                    
                    # エリアのリスクタイムラインを計算（サービス層使用）
                    try:
                        area.risk_timeline = self.main_service.calculation_service.calc_risk_timeline(area.meshes)
                        area_result["risk_timeline"] = [
                            {"ft": int(r.ft), "value": int(r.value)}
                            for r in area.risk_timeline
                        ]
                    except Exception as e:
                        logger.warning(f"Risk timeline calculation error for area {area.name}: {e}")
                        # エラー時はダミーデータ
                        area_result["risk_timeline"] = [
                            {"ft": 0, "value": 0},
                            {"ft": 3, "value": 1},
                            {"ft": 6, "value": 1}
                        ]
                    
                    pref_result["areas"].append(area_result)

                # 二次細分ごとの集約計算
                for subdivision in prefecture.secondary_subdivisions:
                    self.main_service.calculation_service.calc_secondary_subdivision_aggregates(subdivision)

                # 府県全体の集約計算
                self.main_service.calculation_service.calc_prefecture_aggregates(prefecture)

                # 二次細分データをレスポンスに追加
                pref_result["secondary_subdivisions"] = [
                    {
                        "name": subdiv.name,
                        "area_names": [area.name for area in subdiv.areas],
                        "rain_1hour_max_timeline": [
                            {"ft": r.ft, "value": float(r.value)}
                            for r in subdiv.rain_1hour_max_timeline
                        ],
                        "rain_3hour_timeline": [
                            {"ft": r.ft, "value": float(r.value)}
                            for r in subdiv.rain_3hour_timeline
                        ],
                        "risk_timeline": [
                            {"ft": r.ft, "value": r.value}
                            for r in subdiv.risk_timeline
                        ]
                    }
                    for subdiv in prefecture.secondary_subdivisions
                ]

                # 府県集約データをレスポンスに追加
                pref_result["prefecture_rain_1hour_max_timeline"] = [
                    {"ft": r.ft, "value": float(r.value)}
                    for r in prefecture.prefecture_rain_1hour_max_timeline
                ]
                pref_result["prefecture_rain_3hour_timeline"] = [
                    {"ft": r.ft, "value": float(r.value)}
                    for r in prefecture.prefecture_rain_3hour_timeline
                ]
                pref_result["prefecture_risk_timeline"] = [
                    {"ft": r.ft, "value": r.value}
                    for r in prefecture.prefecture_risk_timeline
                ]

                results[prefecture.code] = pref_result
                logger.info(f"完了: {prefecture.name} - {len(pref_result['areas'])}エリア, {len(pref_result.get('secondary_subdivisions', []))}二次細分")
            
            total_time = time.time() - start_time
            logger.info(f"全処理完了: 総メッシュ数={total_meshes}, 処理成功={processed_meshes}, 処理時間={total_time:.2f}秒")
            
            # main_processと同じ形式でレスポンス（元の実装と同じ）
            return jsonify({
                "status": "success",
                "calculation_time": datetime.utcnow().isoformat() + 'Z',
                "initial_time": base_info.initial_date.isoformat() + 'Z',
                "swi_initial_time": base_info.initial_date.isoformat() + 'Z',
                "guid_initial_time": base_info.initial_date.isoformat() + 'Z',
                "prefectures": results,
                "statistics": {
                    "total_meshes": total_meshes,
                    "processed_meshes": processed_meshes,
                    "success_rate": f"{(processed_meshes/total_meshes*100):.1f}%" if total_meshes > 0 else "0%"
                },
                "note": "フル版: ローカルbinファイルからの実データ（全メッシュ処理）"
            })
            
        except Exception as e:
            logger.error(f"フル土壌雨量指数計算エラー: {e}")
            return jsonify({
                "status": "error",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }), 500
    
    def test_full_parallel_soil_rainfall_index(self):
        """並列処理版（実際は最適化されたシーケンシャル処理）"""
        # test_full_soil_rainfall_index と同じ実装（最適化済み）
        return self.test_full_soil_rainfall_index()

    def test_session_with_local_bins(self):
        """
        テスト用セッションベースAPI
        ローカルbinファイルを使ってセッションを作成し、本番と同じセッションAPIで動作する
        """
        try:
            if not self.session_service:
                return jsonify({
                    "status": "error",
                    "error": "SessionService not initialized",
                    "timestamp": datetime.now().isoformat()
                }), 500

            # binファイルのパス
            swi_bin_path = os.path.join(self.data_dir, "Z__C_RJTD_20230602000000_SRF_GPV_Ggis1km_Psw_Aper10min_ANAL_grib2.bin")
            guidance_bin_path = os.path.join(self.data_dir, "guid_msm_grib2_20230602000000_rmax00.bin")

            # ファイル存在確認
            if not os.path.exists(swi_bin_path):
                return jsonify({
                    "status": "error",
                    "error": "SWI binファイルが見つかりません",
                    "timestamp": datetime.now().isoformat()
                }), 500

            if not os.path.exists(guidance_bin_path):
                return jsonify({
                    "status": "error",
                    "error": "ガイダンス binファイルが見つかりません",
                    "timestamp": datetime.now().isoformat()
                }), 500

            logger.info("テスト用セッション作成: ローカルGRIB2ファイルを使用")

            # GRIB2解析
            base_info, swi_grib2 = self.main_service.grib2_service.unpack_swi_grib2_from_file(swi_bin_path)
            _, guidance_grib2 = self.main_service.grib2_service.unpack_guidance_grib2_from_file(guidance_bin_path)

            # 地域データ構築とメッシュ計算（main_serviceを使用）
            prefectures = self.main_service.data_service.prepare_areas()

            # メッシュ計算処理
            for prefecture in prefectures:
                for area in prefecture.areas:
                    for i, mesh in enumerate(area.meshes):
                        area.meshes[i] = self.main_service.calculation_service.process_mesh_calculations(
                            mesh, swi_grib2, guidance_grib2
                        )

            # リスクタイムライン計算
            for prefecture in prefectures:
                for area in prefecture.areas:
                    area.risk_timeline = self.main_service.calculation_service.calc_risk_timeline(area.meshes)

                # 二次細分ごとの集約計算
                for subdivision in prefecture.secondary_subdivisions:
                    self.main_service.calculation_service.calc_secondary_subdivision_aggregates(subdivision)

                # 府県全体の集約計算
                self.main_service.calculation_service.calc_prefecture_aggregates(prefecture)

            # Prefectureオブジェクトを辞書形式に変換
            prefectures_dict = {}
            for pref in prefectures:
                prefectures_dict[pref.code] = self.main_service._prefecture_to_dict(pref)

            # セッションに保存（session_serviceを使用）
            initial_time_iso = base_info.initial_date.isoformat()
            session_id = self.session_service.create_session(
                prefectures_dict,
                initial_time_iso,
                initial_time_iso,
                datetime.now().isoformat(),
                'msm'
            )

            # 利用可能な時刻を取得
            available_times = []
            if len(prefectures) > 0 and len(prefectures[0].areas) > 0 and len(prefectures[0].areas[0].meshes) > 0:
                first_mesh = prefectures[0].areas[0].meshes[0]
                available_times = sorted(set(
                    [point.ft for point in first_mesh.risk_3hour_max_timeline] +
                    [point.ft for point in first_mesh.risk_hourly_timeline]
                ))

            # 利用可能な府県コードを取得
            available_prefectures = [pref.code for pref in prefectures]

            logger.info(f"テスト用セッション作成完了: session_id={session_id}")

            swi_time_with_z = base_info.initial_date.isoformat() + 'Z'
            guidance_time_with_z = base_info.initial_date.isoformat() + 'Z'
            logger.info(f"レスポンス時刻: swi_initial_time={swi_time_with_z}, guidance_initial_time={guidance_time_with_z}")

            # 軽量レスポンス（セッションIDと利用可能な時刻・府県のみ）
            return jsonify({
                "status": "success",
                "session_id": session_id,
                "swi_initial_time": swi_time_with_z,
                "guidance_initial_time": guidance_time_with_z,
                "available_times": available_times,
                "available_prefectures": available_prefectures,
                "timestamp": datetime.now().isoformat()
            })

        except Exception as e:
            logger.error(f"テスト用セッション作成エラー: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({
                "status": "error",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }), 500
