# -*- coding: utf-8 -*-
"""
GRIB2データ処理サービス
"""
from typing import List, Optional, Tuple, Dict, Any
import struct
import requests
import logging
import os
import sys
from datetime import datetime, timedelta

from models import BaseInfo, SwiTimeSeries, GuidanceTimeSeries

# 設定サービスのインポート（パス追加）
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'src'))
from config.config_service import ConfigService


logger = logging.getLogger(__name__)


class Grib2Service:
    """GRIB2データ処理サービス"""
    
    def __init__(self):
        self.session = requests.Session()
        self.config = ConfigService()
        # 設定ファイルからproxy設定を取得
        self._setup_proxy()
    
    def _setup_proxy(self):
        """設定ファイルからproxy設定をセットアップ"""
        proxy_config = self.config.get_proxy_config()
        http_proxy = proxy_config.get('http')
        https_proxy = proxy_config.get('https') or http_proxy
        
        if http_proxy:
            proxies = {
                'http': http_proxy,
                'https': https_proxy
            }
            self.session.proxies.update(proxies)
            logger.info(f"Proxy設定: HTTP={http_proxy}, HTTPS={https_proxy}")
        else:
            logger.info("Proxy設定なし（直接接続）")
    
    def download_file(self, url: str) -> Optional[bytes]:
        """ファイルダウンロード（設定ファイル対応）"""
        grib2_config = self.config.get_grib2_config()
        timeout = grib2_config['download_timeout']
        retry_count = grib2_config['retry_count']
        retry_delay = grib2_config['retry_delay']
        
        # プロキシ設定を取得
        proxy_config = self.config.get_proxy_config()
        proxies = None
        if proxy_config.get('http'):
            proxies = {
                'http': proxy_config.get('http'),
                'https': proxy_config.get('https') or proxy_config.get('http')
            }
        
        for attempt in range(retry_count):
            try:
                if attempt > 0:
                    logger.info(f"リトライ {attempt}/{retry_count-1}: {url}")
                    import time
                    time.sleep(retry_delay)
                else:
                    logger.info(f"ダウンロード開始: {url}")
                
                if proxies:
                    logger.debug(f"Proxy経由でアクセス: {proxies}")
                
                response = self.session.get(url, stream=True, timeout=timeout, proxies=proxies)
                response.raise_for_status()
                
                content_length = len(response.content)
                logger.info(f"ダウンロード完了: {url} ({content_length:,} bytes)")
                return response.content
                
            except requests.exceptions.ProxyError as e:
                logger.error(f"Proxyエラー (試行 {attempt+1}/{retry_count}): {url} - {e}")
                if attempt == retry_count - 1:
                    logger.error("Proxy設定を確認してください: config/app_config.yaml")
                    return None
            except requests.exceptions.ConnectionError as e:
                logger.error(f"接続エラー (試行 {attempt+1}/{retry_count}): {url} - {e}")
                if attempt == retry_count - 1:
                    logger.error("ネットワーク接続またはProxy設定を確認してください")
                    return None
            except requests.exceptions.Timeout as e:
                logger.error(f"タイムアウトエラー (試行 {attempt+1}/{retry_count}): {url} - {e}")
                if attempt == retry_count - 1:
                    return None
            except Exception as e:
                logger.error(f"ダウンロードエラー (試行 {attempt+1}/{retry_count}): {url} - {e}")
                if attempt == retry_count - 1:
                    return None
        
        return None
    
    def get_dat(self, bin_data: bytes, i: int, j: int) -> int:
        """Big-Endianバイナリデータ読み取り（VBA版完全対応）"""
        if i + j > len(bin_data):
            return 0
        
        # VBAのget_dat関数と同じロジック
        # VBA: get_dat = get_dat + dat * (256 ^ (e - i))
        result = 0
        for k in range(j):
            if i + k < len(bin_data):
                byte_val = bin_data[i + k]
                result = result + byte_val * (256 ** (j - 1 - k))
        
        return result
    
    def unpack_info(self, data: bytes, position: int) -> Tuple[BaseInfo, int, int]:
        """GRIB2ファイルのヘッダー情報を解析"""
        try:
            # セクション0: total_sizeを取得
            total_size = self.get_dat(data, 8, 8)
            position = 16

            # セクション1: 日時情報
            section_size = self.get_dat(data, position, 4)
            year = self.get_dat(data, position + 12, 2)
            month = self.get_dat(data, position + 14, 1)
            day = self.get_dat(data, position + 15, 1)
            hour = self.get_dat(data, position + 16, 1)
            minute = self.get_dat(data, position + 17, 1)
            second = self.get_dat(data, position + 18, 1)

            initial_date = datetime(year, month, day, hour, minute, second)
            position += section_size

            # セクション3: グリッド情報
            section_size = self.get_dat(data, position, 4)
            grid_num = self.get_dat(data, position + 6, 4)
            x_num = self.get_dat(data, position + 30, 4)
            y_num = self.get_dat(data, position + 34, 4)
            s_lat = self.get_dat(data, position + 46, 4)
            s_lon = self.get_dat(data, position + 50, 4)
            e_lat = self.get_dat(data, position + 55, 4)
            e_lon = self.get_dat(data, position + 59, 4)
            d_lon = self.get_dat(data, position + 63, 4)
            d_lat = self.get_dat(data, position + 67, 4)
            position += section_size

            # BaseInfo dataclass instance creation
            base_info = BaseInfo(
                initial_date=initial_date,
                grid_num=grid_num,
                x_num=x_num,
                y_num=y_num,
                s_lat=s_lat,
                s_lon=s_lon,
                e_lat=e_lat,
                e_lon=e_lon,
                d_lat=d_lat,
                d_lon=d_lon
            )

            return base_info, position, total_size
            
        except Exception as e:
            logger.error(f"GRIB2ヘッダー解析エラー: {e}")
            raise
    
    def unpack_runlength(self, data: bytes, bit_num: int, level_num: int, level_max: int,
                         grid_num: int, level: List[int], s_position: int,
                         e_position: int) -> List[float]:
        """ランレングス圧縮データの展開（詳細デバッグ版）"""
        try:
            # 手動トレースで完全一致が確認されたアルゴリズムを移植
            result = [0.0] * grid_num
            d_index = 0
            p = s_position
            byte_size = bit_num // 8
            
            # TARGET位置のデバッグ用（座標 X=2869, Y=4187 → data_num=4025749）
            target_d_index = 4025749
            debug_enabled = True

            while p < e_position and d_index < grid_num:
                if p + 2 * byte_size > len(data):
                    break
                
                d = self.get_dat(data, p, byte_size)
                p += byte_size
                
                if d > level_num:
                    logger.error(f"VBA停止条件: d({d}) > level_num({level_num})")
                    break
                
                dd = self.get_dat(data, p, byte_size)
                
                # TARGET位置での詳細デバッグ
                if debug_enabled and d_index == target_d_index:
                    level_val = level[d - 1] if 1 <= d <= len(level) else 0
                    logger.error(f"★ grib2_service TARGET位置:")
                    logger.error(f"  d_index={d_index}")
                    logger.error(f"  d={d}")
                    logger.error(f"  dd={dd}")
                    logger.error(f"  level[{d}] → level[{d-1}] = {level_val}")
                    logger.error(f"  ÷10結果: {level_val/10}")
                
                if dd <= level_max:
                    # 配列に値を格納（VBAロジック完全再現）
                    if 1 <= d <= len(level):
                        result[d_index] = float(level[d - 1])
                    else:
                        result[d_index] = 0.0
                    d_index += 1
                else:
                    # ランレングス圧縮処理（手動トレースと同一）
                    lngu = 2 ** bit_num - 1 - level_max
                    nlength = 0
                    p2 = 1
                    
                    while p <= e_position and dd > level_max:
                        nlength = nlength + ((lngu ** (p2 - 1)) * (dd - level_max - 1))
                        p += byte_size
                        if p + byte_size > len(data):
                            break
                        dd = self.get_dat(data, p, byte_size)
                        p2 += 1
                    
                    # nlength + 1個の同じ値を格納
                    for i in range(nlength + 1):
                        if d_index >= grid_num:
                            break
                        if 1 <= d <= len(level):
                            result[d_index] = float(level[d - 1])
                        else:
                            result[d_index] = 0.0
                        d_index += 1

            return result
            
        except Exception as e:
            logger.error(f"ランレングス展開エラー: {e}")
            return [0.0] * grid_num
    
    def unpack_data(self, data: bytes, position: int, grid_num: int,
                    data_type: int, level: List[int], ref_val: float) -> List[float]:
        """GRIB2データ値解析（VBA版に完全対応）"""
        try:
            if data_type == 200:  # ランレングス圧縮
                # セクション5: データ表現（VBA版完全対応）
                section_size = self.get_dat(data, position, 4)
                bit_num = self.get_dat(data, position + 11, 1)    # VBA: position + 12, 1 (1ベース調整)
                level_max = self.get_dat(data, position + 12, 2)  # VBA: position + 13, 2 (1ベース調整)
                level_num = self.get_dat(data, position + 14, 2)  # VBA: position + 15, 2 (1ベース調整)
                
                # レベル配列を作成（VBA版完全対応）
                # VBA: ReDim level(level_num), For i = 1 To level_max
                level = [0] * (level_num + 1)  # VBAの1ベース配列に対応（0番目は未使用）
                for i in range(1, min(level_max + 1, level_num + 1)):  # level_numを超えないように制限
                    # VBA: level(i) = get_dat(buf, position + 16 + 2 * i, 2) (1ベース)
                    val = self.get_dat(data, position + 15 + 2 * i, 2)  # 0ベース調整
                    if val >= 65536 // 2:  # 整数除算に修正
                        val = int(val - 65536 // 2)
                    if i < len(level):  # 安全のため境界チェック
                        level[i] = val  # VBAの1ベース配列に合わせてインデックス使用
                
                position += section_size
                
                # セクション6: ビットマップ（スキップ）
                section_size = self.get_dat(data, position, 4)
                position += section_size
                
                # セクション7: データ
                section_size = self.get_dat(data, position, 4)
                s_position = position + 5  # VBA版の position + 6 - 1 (0ベース)
                e_position = position + section_size
                
                data_values = self.unpack_runlength(
                    data, bit_num, level_num, level_max, grid_num,
                    level, s_position, e_position
                )
                
                # VBA版では ref_val を使わずに直接値を返す
                return [float(val) if val < 9999 else float('nan') for val in data_values]
            else:
                return [float('nan')] * grid_num
                
        except Exception as e:
            logger.error(f"データ展開エラー: {e}")
            return [float('nan')] * grid_num
    
    def unpack_swi_grib2_from_file(self, file_path: str) -> Tuple[BaseInfo, List[float]]:
        """土壌雨量指数ファイル解析（ファイルパス版）"""
        try:
            with open(file_path, 'rb') as f:
                data = f.read()
            return self.unpack_swi_grib2(data)
        except Exception as e:
            logger.error(f"SWI GRIB2ファイル読み込みエラー: {e}")
            raise
    
    def unpack_swi_grib2(self, data: bytes) -> Tuple[BaseInfo, Dict[str, Any]]:
        """土壌雨量指数データ解析（元の実装と同じ形式で返却）"""
        try:
            base_info, position, total_size = self.unpack_info(data, 0)
            
            swi_data = None
            first_tunk = None
            second_tunk = None
            
            # VBAのDo While total_size - position > 4ループを再現
            # VBAでは最初のdata_type=200セクションのみ処理するため、フラグで制御
            swi_processed = False
            
            while total_size - position > 4:
                # セクション4: プロダクト定義
                section_size = self.get_dat(data, position, 4)
                data_type = self.get_dat(data, position + 22, 1)
                data_sub_type = self.get_dat(data, position + 24, 4)
                position += section_size
                
                # データタイプに応じて処理を分岐（VBAの動作を正確に再現）
                if data_type == 200 and not swi_processed:  # 最初の土壌雨量指数のみ処理
                    logger.warning(f"SWI処理: data_type=200セクションを処理開始")
                    swi_data, position = self._unpack_data_section(data, position, base_info.grid_num)
                    swi_processed = True  # 最初の処理のみで終了
                    logger.warning(f"SWI処理: data_type=200セクション処理完了、今後スキップ")
                elif data_type == 200 and swi_processed:  # 2番目以降のdata_type=200はスキップ
                    logger.warning(f"スキップ: data_type=200セクション（既に処理済み）")
                    dummy_data, position = self._skip_data_sections(data, position)
                elif data_type == 201 and data_sub_type == 1:  # 第1タンク値
                    logger.debug(f"スキップ: data_type=201, sub_type=1")
                    first_tunk, position = self._skip_data_sections(data, position)
                elif data_type == 201 and data_sub_type == 2:  # 第2タンク値  
                    logger.debug(f"スキップ: data_type=201, sub_type=2")
                    second_tunk, position = self._skip_data_sections(data, position)
                else:
                    # 不明なデータタイプはスキップ
                    logger.warning(f"不明データタイプ: data_type={data_type}, sub_type={data_sub_type}")
                    break
            
            # 元の実装と同じ辞書形式で返却
            result = {
                'base_info': base_info,
                'swi': swi_data or [],
                'first_tunk': first_tunk or [],
                'second_tunk': second_tunk or []
            }
            
            return base_info, result
            
        except Exception as e:
            logger.error(f"SWI GRIB2解析エラー: {e}")
            raise
    
    def _skip_data_sections(self, data: bytes, position: int) -> Tuple[List[float], int]:
        """データセクションをスキップ（セクション5,6,7の位置計算のみ）"""
        try:
            section5_size = self.get_dat(data, position, 4)
            section6_size = self.get_dat(data, position + section5_size, 4)  
            section7_size = self.get_dat(data, position + section5_size + section6_size, 4)
            
            next_position = position + section5_size + section6_size + section7_size
            return [], next_position  # 空の配列を返す
            
        except Exception as e:
            logger.error(f"データセクションスキップエラー: {e}")
            raise
    
    def _unpack_data_section(self, data: bytes, position: int, grid_num: int) -> Tuple[List[float], int]:
        """データセクションの解析（VBA版完全対応）"""
        try:
            # セクション5からレベル配列を読み取り
            section5_size = self.get_dat(data, position, 4)
            level_max = self.get_dat(data, position + 12, 2)
            
            # VBAと同様にレベル配列を構築
            level = []
            for i in range(1, level_max + 1):
                val = self.get_dat(data, position + 15 + 2 * i, 2)
                if val >= 32768:  # 符号付き16bit処理
                    val = val - 65536
                level.append(val)
            
            # レベル配列のデバッグ出力
            logger.warning(f"レベル配列構築: level_max={level_max}, len(level)={len(level)}")
            if len(level) > 14:
                logger.warning(f"level[13]={level[12]} level[14]={level[13]} (期待値680,700)")
            logger.warning(f"level配列例: {level[:5]} ... {level[-5:] if len(level) > 5 else level}")
            
            # VBAのunpack_dataに完全対応（正しいlevel配列を渡す）
            data_values = self.unpack_data(data, position, grid_num, 200, level, 0.0)
            
            # position の更新は unpack_data 内で行われるので、
            # セクションサイズを計算して位置を更新
            section5_size = self.get_dat(data, position, 4)
            section6_size = self.get_dat(data, position + section5_size, 4)  
            section7_size = self.get_dat(data, position + section5_size + section6_size, 4)
            
            next_position = position + section5_size + section6_size + section7_size
            
            return data_values, next_position
            
        except Exception as e:
            logger.error(f"データセクション解析エラー: {e}")
            raise
    
    def unpack_guidance_grib2_from_file(self, file_path: str) -> Tuple[BaseInfo, List[List[float]]]:
        """降水量予測ファイル解析（ファイルパス版）"""
        try:
            with open(file_path, 'rb') as f:
                data = f.read()
            return self.unpack_guidance_grib2(data)
        except Exception as e:
            logger.error(f"Guidance GRIB2ファイル読み込みエラー: {e}")
            raise
    
    def unpack_guidance_grib2(self, data: bytes) -> Tuple[BaseInfo, Dict[str, Any]]:
        """降水量予測データ解析（元の実装と同じ形式で返却）"""
        try:
            base_info, position, total_size = self.unpack_info(data, 0)
            guidance_data = []
            
            loop_count = 1
            prev_ft = 0
            
            # VBAのDoループを再現（1ベース→0ベース変換）
            while position < total_size - 4:
                # セクション4: プロダクト定義（VBA: position+1 → Python: position+0）
                section_size = self.get_dat(data, position + 0, 4)  # VBA: position+1
                span = self.get_dat(data, position + 49, 4)  # VBA: position+50
                ft = self.get_dat(data, position + 18, 4) + span  # VBA: position+19
                
                if prev_ft > ft:
                    loop_count += 1
                
                position += section_size
                
                # VBAの条件: span = 3 And loop_count = 2
                if span == 3 and loop_count == 2:
                    data_values, position = self._unpack_data_section(data, position, base_info.grid_num)
                    # VBA: data(n).ft = ft, data(n).value = value
                    guidance_data.append({
                        'ft': ft,
                        'value': data_values
                    })
                else:
                    # 条件に合わない場合はスキップ
                    position = self._skip_data_section(data, position)
                
                prev_ft = ft
            
            # 元の実装と同じ辞書形式で返却
            result = {
                'base_info': base_info,
                'data': guidance_data
            }
            
            return base_info, result
            
        except Exception as e:
            logger.error(f"Guidance GRIB2解析エラー: {e}")
            raise
    
    def _skip_data_section(self, data: bytes, position: int) -> int:
        """データセクションをスキップ"""
        try:
            # セクション5をスキップ
            section_size = self.get_dat(data, position, 4)
            position += section_size
            
            # セクション6をスキップ
            if position < len(data) - 4:
                bitmap_size = self.get_dat(data, position, 4)
                position += bitmap_size
            
            # セクション7をスキップ
            if position < len(data) - 4:
                section7_size = self.get_dat(data, position, 4)
                position += section7_size
            
            return position
            
        except Exception as e:
            logger.error(f"データセクションスキップエラー: {e}")
            return position