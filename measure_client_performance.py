"""
クライアント側パフォーマンス計測スクリプト
API呼び出しからJSONパースまでの時間を計測
"""
import requests
import json
import time

def measure_client_performance():
    api_url = "http://localhost:5000/api/test-full-soil-rainfall-index"
    
    print("=" * 80)
    print("クライアント側パフォーマンス計測")
    print("=" * 80)
    print()
    
    # 全体計測開始
    total_start = time.time()
    
    # API呼び出し（サーバー処理含む）
    print("API呼び出し中...")
    api_call_start = time.time()
    
    response = requests.get(api_url)
    
    api_call_end = time.time()
    api_duration = api_call_end - api_call_start
    
    print(f"[計測] API呼び出し時間: {api_duration:.2f}秒")
    print(f"レスポンスステータス: {response.status_code}")
    print(f"レスポンスサイズ: {len(response.content)} bytes")
    print()
    
    if response.status_code != 200:
        print(f"エラー: ステータスコード {response.status_code}")
        print(f"レスポンス: {response.text[:500]}")
        return
    
    # JSONパース
    print("JSONパース中...")
    parse_start = time.time()
    
    try:
        data = response.json()
    except json.JSONDecodeError as e:
        print(f"JSONパースエラー: {e}")
        print(f"レスポンス先頭500文字: {response.text[:500]}")
        return
    
    parse_end = time.time()
    parse_duration = parse_end - parse_start
    
    print(f"[計測] JSONパース時間: {parse_duration:.2f}秒")
    print()
    
    # 全体時間
    total_end = time.time()
    total_duration = total_end - total_start
    
    # データサイズ・メッシュ数
    json_str = json.dumps(data)
    data_size_mb = len(json_str) / 1024 / 1024
    
    mesh_count = 0
    for pref in data.get('prefectures', {}).values():
        for area in pref.get('areas', []):
            mesh_count += len(area.get('meshes', []))
    
    # 結果サマリー
    print("=" * 80)
    print("計測結果サマリー")
    print("=" * 80)
    print(f"API呼び出し（サーバー処理含む）: {api_duration:.2f}秒")
    print(f"JSONパース:                      {parse_duration:.2f}秒")
    print(f"合計時間:                        {total_duration:.2f}秒")
    print(f"メッシュ数:                      {mesh_count:,}")
    print(f"データサイズ:                    {data_size_mb:.2f} MB")
    print("=" * 80)
    print()
    
    # キャッシュ情報の確認
    if 'cache_info' in data:
        cache_info = data['cache_info']
        print("キャッシュ情報:")
        print(f"  キャッシュヒット: {cache_info.get('is_cache_hit', False)}")
        if cache_info.get('is_cache_hit'):
            print(f"  キャッシュキー: {cache_info.get('cache_key', 'N/A')}")
    print()

if __name__ == "__main__":
    try:
        measure_client_performance()
    except Exception as e:
        print(f"エラー: {e}")
        import traceback
        traceback.print_exc()
