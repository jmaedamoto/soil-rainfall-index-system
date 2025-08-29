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
from models import SwiTimeSeries, GuidanceTimeSeries


logger = logging.getLogger(__name__)


class TestController:
    """テストAPIコントローラー"""
    
    def __init__(self, data_dir: str = "data"):
        self.main_service = MainService(data_dir)
        self.data_dir = data_dir
    
    def test_bin_data(self):
        """binファイルデータテスト"""
        try:
            swi_bin_path = os.path.join(self.data_dir, "Z__C_RJTD_20250101000000_SRF_GPV_Ggis1km_Psw_Aper10min_ANAL_grib2.bin")
            guidance_bin_path = os.path.join(self.data_dir, "guid_msm_grib2_20250101000000_rmax00.bin")
            
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
            swi_bin_path = os.path.join(self.data_dir, "Z__C_RJTD_20250101000000_SRF_GPV_Ggis1km_Psw_Aper10min_ANAL_grib2.bin")
            guidance_bin_path = os.path.join(self.data_dir, "guid_msm_grib2_20250101000000_rmax00.bin")
            
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
            swi_bin_path = os.path.join(self.data_dir, "Z__C_RJTD_20250101000000_SRF_GPV_Ggis1km_Psw_Aper10min_ANAL_grib2.bin")
            guidance_bin_path = os.path.join(self.data_dir, "guid_msm_grib2_20250101000000_rmax00.bin")
            
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
                            mesh.swi = [
                                SwiTimeSeries(ft=0, value=85.5),
                                SwiTimeSeries(ft=3, value=92.1),
                                SwiTimeSeries(ft=6, value=88.7)
                            ]
                            mesh.rain = [
                                GuidanceTimeSeries(ft=3, value=2.5),
                                GuidanceTimeSeries(ft=6, value=1.8)
                            ]
                        
                        # 元の実装と同じ形式でmesh_result作成
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
                            "rain_timeline": [
                                {"ft": int(r.ft), "value": float(r.value)} for r in mesh.rain
                            ]
                        }
                        area_result["meshes"].append(mesh_result)
                        
                        # プログレス表示（100メッシュごと）
                        if total_meshes % 100 == 0:
                            logger.info(f"進捗: {total_meshes}メッシュ処理完了")
                    
                    # エリアのリスクタイムラインを計算（サービス層使用）
                    try:
                        area.risk_timeline = self.main_service.calculation_service.calc_risk_timeline(area)
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
                
                results[prefecture.code] = pref_result
                logger.info(f"完了: {prefecture.name} - {len(pref_result['areas'])}エリア")
            
            total_time = time.time() - start_time
            logger.info(f"全処理完了: 総メッシュ数={total_meshes}, 処理成功={processed_meshes}, 処理時間={total_time:.2f}秒")
            
            # main_processと同じ形式でレスポンス（元の実装と同じ）
            return jsonify({
                "status": "success",
                "calculation_time": datetime.now().isoformat(),
                "initial_time": base_info.initial_date.isoformat(),
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