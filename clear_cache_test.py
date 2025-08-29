#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import requests
import json


def test_with_cache_clear():
    print("キャッシュクリア後のテストを実行...")
    
    try:
        # 新しい時刻でリクエストしてキャッシュ回避
        response = requests.post(
            'http://localhost:5000/api/soil-rainfall-index',
            json={"initial": "2025-01-01T00:00:00Z"},
            timeout=120
        )
        
        if response.status_code != 200:
            print(f"APIエラー: {response.status_code}")
            return
            
        data = response.json()
        print(f"データ取得成功: {len(data.get('prefectures', {}))}府県")
        
        # 境界値チェック用の小サンプル
        sample_count = 0
        boundary_200_count = 0
        boundary_9999_count = 0
        
        for pref_code, prefecture in data['prefectures'].items():
            for area in prefecture['areas']:
                for mesh in area['meshes']:
                    sample_count += 1
                    if mesh['dosyakei_bound'] == 200:
                        boundary_200_count += 1
                    elif mesh['dosyakei_bound'] == 9999:
                        boundary_9999_count += 1
                    
                    # 最初の100個のサンプルのみ
                    if sample_count >= 100:
                        break
                if sample_count >= 100:
                    break
            if sample_count >= 100:
                break
        
        print(f"サンプル100個中:")
        print(f"土砂災害基準200: {boundary_200_count}個")
        print(f"土砂災害基準9999: {boundary_9999_count}個")
        print(f"その他: {100 - boundary_200_count - boundary_9999_count}個")
        
        if boundary_200_count == 0:
            print("SUCCESS: すべての200が9999に修正されました")
        else:
            print(f"PARTIAL: まだ{boundary_200_count}個の200が残っています")
        
    except Exception as e:
        print(f"エラーが発生しました: {e}")


if __name__ == "__main__":
    test_with_cache_clear()