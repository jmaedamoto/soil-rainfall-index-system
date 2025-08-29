#!/usr/bin/env python3
"""
GRIB2解析関数のテストスクリプト
dataフォルダ内のbinファイルを使用してunpack_swi_grib2とunpack_guidance_grib2の動作をテスト
"""

import os
import sys
from datetime import datetime
from typing import Dict, Any

# app.pyから必要な関数をインポート
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from app import unpack_swi_grib2, unpack_guidance_grib2


def load_bin_file(filepath: str) -> bytes:
    """binファイルを読み込み"""
    try:
        with open(filepath, 'rb') as f:
            return f.read()
    except FileNotFoundError:
        print(f"エラー: ファイルが見つかりません: {filepath}")
        return None
    except Exception as e:
        print(f"エラー: ファイル読み込み失敗: {e}")
        return None


def test_unpack_swi_grib2():
    """unpack_swi_grib2関数のテスト"""
    print("=== unpack_swi_grib2 テスト開始 ===")
    
    # SWI GRIB2ファイルのパス
    swi_file = "data/Z__C_RJTD_20250101000000_SRF_GPV_Ggis1km_Psw_Aper10min_ANAL_grib2.bin"
    
    if not os.path.exists(swi_file):
        print(f"エラー: SWIファイルが見つかりません: {swi_file}")
        return False
    
    # ファイル読み込み
    print(f"ファイル読み込み: {swi_file}")
    data = load_bin_file(swi_file)
    if data is None:
        return False
    
    print(f"ファイルサイズ: {len(data)} bytes")
    
    try:
        # unpack_swi_grib2関数を実行
        print("unpack_swi_grib2関数を実行中...")
        result = unpack_swi_grib2(data)
        
        # 結果の表示
        print("\n=== 解析結果 ===")
        print(f"base_info: {result.get('base_info', 'None')}")
        
        if 'swi_data' in result and result['swi_data'] is not None:
            swi_data = result['swi_data']
            print(f"swi_data length: {len(swi_data)}")
            if len(swi_data) > 0:
                print(f"swi_data[0]: {swi_data[0]}")
                print(f"swi_data[-1]: {swi_data[-1]}")
        
        if 'first_tunk' in result and result['first_tunk'] is not None:
            first_tunk = result['first_tunk']
            print(f"first_tunk length: {len(first_tunk)}")
            if len(first_tunk) > 0:
                print(f"first_tunk[0]: {first_tunk[0]}")
                print(f"first_tunk[-1]: {first_tunk[-1]}")
        
        if 'second_tunk' in result and result['second_tunk'] is not None:
            second_tunk = result['second_tunk']
            print(f"second_tunk length: {len(second_tunk)}")
            if len(second_tunk) > 0:
                print(f"second_tunk[0]: {second_tunk[0]}")
                print(f"second_tunk[-1]: {second_tunk[-1]}")
        
        print("unpack_swi_grib2テスト 成功")
        return True
        
    except Exception as e:
        print(f"エラー: unpack_swi_grib2実行失敗: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_unpack_guidance_grib2():
    """unpack_guidance_grib2関数のテスト"""
    print("\n=== unpack_guidance_grib2 テスト開始 ===")
    
    # ガイダンス GRIB2ファイルのパス
    guidance_file = "data/guid_msm_grib2_20250101000000_rmax00.bin"
    
    if not os.path.exists(guidance_file):
        print(f"エラー: ガイダンスファイルが見つかりません: {guidance_file}")
        return False
    
    # ファイル読み込み
    print(f"ファイル読み込み: {guidance_file}")
    data = load_bin_file(guidance_file)
    if data is None:
        return False
    
    print(f"ファイルサイズ: {len(data)} bytes")
    
    try:
        # unpack_guidance_grib2関数を実行
        print("unpack_guidance_grib2関数を実行中...")
        result = unpack_guidance_grib2(data)
        
        # 結果の表示
        print("\n=== 解析結果 ===")
        print(f"base_info: {result.get('base_info', 'None')}")
        
        if 'guidance_data' in result and result['guidance_data'] is not None:
            guidance_data = result['guidance_data']
            print(f"guidance_data length: {len(guidance_data)}")
            
            for i, gdata in enumerate(guidance_data):
                if isinstance(gdata, list) and len(gdata) > 0:
                    print(f"guidance_data[{i}] length: {len(gdata)}")
                    print(f"guidance_data[{i}][0]: {gdata[0]}")
                    print(f"guidance_data[{i}][-1]: {gdata[-1]}")
                else:
                    print(f"guidance_data[{i}]: {gdata}")
        
        print("unpack_guidance_grib2テスト 成功")
        return True
        
    except Exception as e:
        print(f"エラー: unpack_guidance_grib2実行失敗: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """メイン関数"""
    print("GRIB2解析関数テスト開始")
    print(f"現在時刻: {datetime.now()}")
    print(f"作業ディレクトリ: {os.getcwd()}")
    
    # テスト実行
    swi_success = test_unpack_swi_grib2()
    guidance_success = test_unpack_guidance_grib2()
    
    # 結果サマリー
    print("\n=== テスト結果サマリー ===")
    print(f"unpack_swi_grib2: {'成功' if swi_success else '失敗'}")
    print(f"unpack_guidance_grib2: {'成功' if guidance_success else '失敗'}")
    
    if swi_success and guidance_success:
        print("全テスト成功！")
        return 0
    else:
        print("一部のテストが失敗しました")
        return 1


if __name__ == "__main__":
    sys.exit(main())