#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SWI参照CSVの詳細分析
期待値と実際のデータの乖離原因を特定
"""

import sys
import os
sys.path.append(os.path.dirname(__file__))

def main():
    print("=== SWI参照CSV詳細分析 ===")
    
    try:
        # 複数のエンコーディングでCSVを読み取り試行
        encodings = ['utf-8', 'iso-8859-1', 'shift_jis', 'cp932']
        csv_content = None
        used_encoding = None
        
        for encoding in encodings:
            try:
                with open('data/shiga_swi.csv', 'r', encoding=encoding) as f:
                    csv_content = f.readlines()
                used_encoding = encoding
                print(f"CSV読み取り成功: エンコーディング={encoding}")
                break
            except Exception as e:
                print(f"エンコーディング{encoding}失敗: {e}")
                continue
        
        if not csv_content:
            print("CSVファイルの読み取りに失敗しました")
            return
        
        print(f"\n1. CSV基本情報:")
        print(f"総行数: {len(csv_content)}")
        print(f"使用エンコーディング: {used_encoding}")
        
        # 最初の10行を詳細分析
        print(f"\n2. 最初の10行の詳細分析:")
        for i, line in enumerate(csv_content[:10]):
            parts = line.strip().split(',')
            print(f"行{i+1}: 列数={len(parts)}")
            
            if len(parts) >= 4:
                try:
                    area_name = parts[0]
                    x = int(parts[1]) if parts[1] else None
                    y = int(parts[2]) if parts[2] else None
                    swi_value = float(parts[3]) if parts[3] else None
                    print(f"  エリア: {area_name}, X: {x}, Y: {y}, SWI: {swi_value}")
                except Exception as e:
                    print(f"  パースエラー: {e}")
                    print(f"  生データ: {parts[:5]}")  # 最初の5列を表示
            else:
                print(f"  列不足: {parts}")
        
        # 非空のSWI値を持つ行を検索
        print(f"\n3. 有効なSWI値を持つ行の分析:")
        valid_swi_count = 0
        swi_values = []
        
        for i, line in enumerate(csv_content):
            parts = line.strip().split(',')
            if len(parts) >= 4 and parts[3]:
                try:
                    swi_value = float(parts[3])
                    swi_values.append(swi_value)
                    valid_swi_count += 1
                    
                    if valid_swi_count <= 10:  # 最初の10個を詳細表示
                        area_name = parts[0]
                        x = int(parts[1]) if parts[1] else None
                        y = int(parts[2]) if parts[2] else None
                        print(f"  行{i+1}: {area_name}, X:{x}, Y:{y}, SWI:{swi_value}")
                        
                except Exception as e:
                    continue
        
        print(f"\n有効なSWI値の数: {valid_swi_count}")
        
        if swi_values:
            print(f"SWI値の範囲: {min(swi_values)} ～ {max(swi_values)}")
            print(f"平均値: {sum(swi_values)/len(swi_values):.1f}")
            
            # 特定の値の出現頻度
            value_counts = {}
            for val in swi_values:
                value_counts[val] = value_counts.get(val, 0) + 1
            
            print(f"\n頻出値トップ10:")
            sorted_values = sorted(value_counts.items(), key=lambda x: x[1], reverse=True)
            for val, count in sorted_values[:10]:
                print(f"  {val}: {count}回")
        
        # rain CSVと比較
        print(f"\n4. Rain CSVとの比較:")
        try:
            with open('data/shiga_rain.csv', 'r', encoding=used_encoding) as f:
                rain_content = f.readlines()
            
            print(f"Rain CSV行数: {len(rain_content)}")
            
            # 最初の行を比較
            if rain_content:
                rain_parts = rain_content[0].strip().split(',')
                swi_parts = csv_content[0].strip().split(',') if csv_content else []
                
                print(f"Rain CSV最初の行: {rain_parts[:6]}...")
                print(f"SWI CSV最初の行: {swi_parts[:6]}...")
                
                # 座標の一致確認
                if len(rain_parts) >= 3 and len(swi_parts) >= 3:
                    rain_x = rain_parts[1] if rain_parts[1] else None
                    rain_y = rain_parts[2] if rain_parts[2] else None
                    swi_x = swi_parts[1] if swi_parts[1] else None
                    swi_y = swi_parts[2] if swi_parts[2] else None
                    
                    print(f"座標一致: X={rain_x == swi_x}, Y={rain_y == swi_y}")
                    
        except Exception as e:
            print(f"Rain CSV読み取りエラー: {e}")
        
        # Module.basで使われるSWI参照値を確認
        print(f"\n5. Module.basでのSWI処理確認:")
        try:
            with open('data/Module.bas', 'r', encoding='utf-8') as f:
                module_content = f.read()
            
            # SWI関連の処理を検索
            swi_lines = []
            for i, line in enumerate(module_content.split('\n')):
                if 'swi' in line.lower() and ('=' in line or 'print' in line.lower()):
                    swi_lines.append(f"行{i+1}: {line.strip()}")
            
            print(f"Module.basのSWI関連行数: {len(swi_lines)}")
            for line in swi_lines[:5]:  # 最初の5行を表示
                print(f"  {line}")
                
        except Exception as e:
            print(f"Module.bas読み取りエラー: {e}")
        
        # CSVファイルの全体的な構造を確認
        print(f"\n6. CSV全体構造確認:")
        empty_swi_count = 0
        for line in csv_content:
            parts = line.strip().split(',')
            if len(parts) >= 4:
                if not parts[3]:  # SWI値が空
                    empty_swi_count += 1
        
        print(f"SWI値が空の行数: {empty_swi_count}")
        print(f"有効なSWI値の行数: {valid_swi_count}")
        print(f"総行数: {len(csv_content)}")
        
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()