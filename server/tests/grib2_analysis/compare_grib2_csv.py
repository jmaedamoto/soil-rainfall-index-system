#!/usr/bin/env python3
"""
全メッシュでのCSVデータとGRIB2処理結果の完全一致確認
"""

import pandas as pd
from services.grib2_service import Grib2Service
import logging

# ログレベルを設定
logging.basicConfig(level=logging.WARNING, format='%(levelname)s: %(message)s')

def compare_all_meshes():
    """全メッシュでの完全一致確認"""
    print("=== 全メッシュでのCSVとGRIB2完全一致確認 ===")
    
    grib2_service = Grib2Service()
    swi_file = "data/Z__C_RJTD_20230602000000_SRF_GPV_Ggis1km_Psw_Aper10min_ANAL_grib2.bin"
    
    try:
        # GRIB2データを解析
        print("GRIB2ファイル解析中...")
        base_info, swi_data = grib2_service.unpack_swi_grib2_from_file(swi_file)
        swi_values = swi_data.get('swi', [])
        
        print(f"GRIB2基本情報:")
        print(f"  グリッド数: {base_info.grid_num}")
        print(f"  SWI値数: {len(swi_values)}")
        print(f"  非ゼロ値数: {sum(1 for v in swi_values if v != 0.0)}")
        
        # 滋賀県CSVデータを読み込み
        print("\n滋賀県CSVデータ読み込み中...")
        csv_df = pd.read_csv("data/shiga_swi.csv", header=None, skiprows=1, encoding='shift-jis')
        print(f"CSVメッシュ数: {len(csv_df)}")
        
        # 比較統計
        total_meshes = len(csv_df)
        exact_matches = 0
        close_matches = 0  # ±1以内
        error_matches = 0  # エラーケース（範囲外等）
        
        print(f"\n比較実行中（{total_meshes}メッシュ）...")
        
        # 最初の20メッシュの詳細表示用
        detailed_results = []
        
        for i, row in csv_df.iterrows():
            area = row[0]
            csv_x, csv_y = int(row[1]), int(row[2])
            expected_swi = row[6]
            
            # 座標変換（VBAロジック完全再現）
            lat = (csv_y + 0.5) * 30 / 3600
            lon = (csv_x + 0.5) * 45 / 3600 + 100
            
            # GRIB2グリッド座標計算
            y_grid = int((base_info.s_lat / 1000000 - lat) / (base_info.d_lat / 1000000)) + 1
            x_grid = int((lon - base_info.s_lon / 1000000) / (base_info.d_lon / 1000000)) + 1
            # VBAのget_data_numは1ベースだが、Pythonは0ベース配列なので-1が必要
            data_num_vba = (y_grid - 1) * base_info.x_num + x_grid
            data_num = data_num_vba - 1  # Python 0ベースアクセス用
            
            # GRIB2値取得
            if 0 <= data_num < len(swi_values):
                grib2_swi_raw = swi_values[data_num]
                grib2_swi_divided = grib2_swi_raw / 10  # VBAでは÷10
                
                # 比較結果
                diff = abs(grib2_swi_divided - expected_swi)
                
                if diff < 0.01:  # 完全一致（浮動小数点誤差考慮）
                    exact_matches += 1
                    match_type = "完全一致"
                elif diff <= 1.0:  # 近似一致
                    close_matches += 1
                    match_type = "近似一致"
                else:
                    match_type = "不一致"
                
                # 最初の20件は詳細記録
                if i < 20:
                    detailed_results.append({
                        'mesh_num': i + 2,  # CSVは2行目から
                        'area': area,
                        'csv_x': csv_x,
                        'csv_y': csv_y,
                        'data_num': data_num,
                        'expected': expected_swi,
                        'grib2_raw': grib2_swi_raw,
                        'grib2_divided': grib2_swi_divided,
                        'diff': diff,
                        'match_type': match_type
                    })
                
            else:
                error_matches += 1
                if i < 20:
                    detailed_results.append({
                        'mesh_num': i + 2,
                        'area': area,
                        'csv_x': csv_x,
                        'csv_y': csv_y,
                        'data_num': data_num,
                        'expected': expected_swi,
                        'grib2_raw': 'N/A',
                        'grib2_divided': 'N/A',
                        'diff': 'N/A',
                        'match_type': 'データ範囲外'
                    })
        
        # 結果表示
        print(f"\n=== 比較結果統計 ===")
        print(f"総メッシュ数: {total_meshes}")
        print(f"完全一致: {exact_matches} ({exact_matches/total_meshes*100:.1f}%)")
        print(f"近似一致: {close_matches} ({close_matches/total_meshes*100:.1f}%)")
        print(f"エラー: {error_matches} ({error_matches/total_meshes*100:.1f}%)")
        print(f"不一致: {total_meshes - exact_matches - close_matches - error_matches}")
        
        print(f"\n=== 最初の20メッシュの詳細結果 ===")
        for result in detailed_results:
            print(f"行{result['mesh_num']:4d}: {result['area'][:10]:10s} "
                  f"座標({result['csv_x']:4d},{result['csv_y']:4d}) "
                  f"data_num={result['data_num']:7d} "
                  f"期待={result['expected']:6.1f} "
                  f"GRIB2={result['grib2_divided']} "
                  f"差={result['diff']} "
                  f"{result['match_type']}")
        
        # 完全一致率が高い場合の成功判定
        success_rate = exact_matches / total_meshes * 100
        if success_rate > 90:
            print(f"\n成功: {success_rate:.1f}%の完全一致を達成！")
        elif success_rate > 50:
            print(f"\n部分成功: {success_rate:.1f}%の一致")
        else:
            print(f"\n失敗: {success_rate:.1f}%の一致のみ")
            
    except Exception as e:
        print(f"エラー: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    compare_all_meshes()
