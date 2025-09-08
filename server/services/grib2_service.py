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
        """Big-Endianバイナリデータ読み取り"""
        if i + j > len(bin_data):
            return 0
        return struct.unpack(f">{j}B", bin_data[i:i+j])[0] if j == 1 else int.from_bytes(bin_data[i:i+j], 'big')
    
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
        """ランレングス圧縮データの展開"""
        try:
            lngu = 2 ** bit_num - 1 - level_max
            result = [0.0] * grid_num
            d_index = 0
            p = s_position
            byte_size = bit_num // 8

            while p < e_position and d_index < grid_num:
                if p + byte_size > len(data):
                    break
                
                val = 0
                for k in range(byte_size):
                    val = val * 256 + data[p + k]
                p += byte_size

                if val <= level_max:
                    result[d_index] = level[val]
                    d_index += 1
                else:
                    length = val - lngu
                    if length > 0 and d_index > 0:
                        prev_val = result[d_index - 1]
                        for _ in range(min(length, grid_num - d_index)):
                            result[d_index] = prev_val
                            d_index += 1

            return result
            
        except Exception as e:
            logger.error(f"ランレングス展開エラー: {e}")
            return [0.0] * grid_num
    
    def unpack_data(self, data: bytes, position: int, grid_num: int,
                    data_type: int, level: List[int], ref_val: float) -> List[float]:
        """GRIB2データ値解析"""
        try:
            if data_type == 200:  # ランレングス圧縮
                bit_num = self.get_dat(data, position + 11, 1)
                level_num = self.get_dat(data, position + 13, 2)
                level_max = self.get_dat(data, position + 15, 2)
                s_position = position + 21
                e_position = len(data) - 4
                
                data_values = self.unpack_runlength(
                    data, bit_num, level_num, level_max, grid_num,
                    level, s_position, e_position
                )
                
                # 実際の値に変換
                return [(val * ref_val) if val < 9999 else float('nan') for val in data_values]
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
            while total_size - position > 4:
                # セクション4: プロダクト定義
                section_size = self.get_dat(data, position, 4)
                data_type = self.get_dat(data, position + 22, 1)
                data_sub_type = self.get_dat(data, position + 24, 4)
                position += section_size
                
                # データタイプに応じて処理を分岐
                if data_type == 200:  # 土壌雨量指数
                    swi_data, position = self._unpack_data_section(data, position, base_info.grid_num)
                elif data_type == 201 and data_sub_type == 1:  # 第1タンク値
                    first_tunk, position = self._unpack_data_section(data, position, base_info.grid_num)
                elif data_type == 201 and data_sub_type == 2:  # 第2タンク値
                    second_tunk, position = self._unpack_data_section(data, position, base_info.grid_num)
                else:
                    # 不明なデータタイプはスキップ
                    logger.warning(f"Unknown data type: {data_type}, sub_type: {data_sub_type}")
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
    
    def _unpack_data_section(self, data: bytes, position: int, grid_num: int) -> Tuple[List[float], int]:
        """データセクションの解析"""
        try:
            # セクション5: データ表現
            section_size = self.get_dat(data, position, 4)
            data_type = self.get_dat(data, position + 9, 2)
            ref_val = struct.unpack('>f', data[position + 11:position + 15])[0]
            
            if data_type == 200:  # ランレングス圧縮
                level_num = self.get_dat(data, position + 19, 2)
                level = []
                for i in range(level_num):
                    val = self.get_dat(data, position + 21 + i * 2, 2)
                    level.append(val)
            else:
                level = []
            
            position += section_size
            
            # セクション6: ビットマップ（スキップ）
            if position < len(data) - 4:
                bitmap_size = self.get_dat(data, position, 4)
                position += bitmap_size
            
            # セクション7: データ
            data_values = self.unpack_data(data, position, grid_num, data_type, level, ref_val)
            
            # 次のセクションの位置を計算
            section7_size = self.get_dat(data, position, 4)
            position += section7_size
            
            return data_values, position
            
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
            
            # VBAのDoループを再現
            while position < total_size - 4:
                # セクション4: プロダクト定義
                section_size = self.get_dat(data, position, 4)
                span = self.get_dat(data, position + 49, 4)
                ft = self.get_dat(data, position + 18, 4) + span
                
                if prev_ft > ft:
                    loop_count += 1
                
                position += section_size
                
                # VBAの条件: span = 3 And loop_count = 2
                if span == 3 and loop_count == 2:
                    data_values, position = self._unpack_data_section(data, position, base_info.grid_num)
                    guidance_data.append(data_values)
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