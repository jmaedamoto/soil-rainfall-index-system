# -*- coding: utf-8 -*-
"""
設定ファイル管理サービス
"""
import yaml
import os
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class ConfigService:
    """設定ファイル管理サービス"""
    
    def __init__(self, config_path: Optional[str] = None):
        if config_path is None:
            # デフォルトの設定ファイルパス
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            config_path = os.path.join(project_root, "config", "app_config.yaml")
        
        self.config_path = config_path
        self.config = self._load_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """設定ファイルを読み込み"""
        try:
            if not os.path.exists(self.config_path):
                logger.warning(f"設定ファイルが見つかりません: {self.config_path}")
                return self._get_default_config()
            
            with open(self.config_path, 'r', encoding='utf-8') as file:
                config = yaml.safe_load(file) or {}
                logger.info(f"設定ファイル読み込み完了: {self.config_path}")
                return config
                
        except Exception as e:
            logger.error(f"設定ファイル読み込みエラー: {e}")
            logger.info("デフォルト設定を使用します")
            return self._get_default_config()
    
    def _get_default_config(self) -> Dict[str, Any]:
        """デフォルト設定を取得"""
        return {
            "proxy": {
                "http": None,
                "https": None
            },
            "grib2": {
                "base_url": "http://lunar1.fcd.naps.kishou.go.jp/srf/Grib2/Rtn",
                "swi_path": "/swi10",
                "guidance_path": "/gdc",
                "download_timeout": 300,
                "retry_count": 3,
                "retry_delay": 5
            },
            "data": {
                "directory": "data"
            },
            "logging": {
                "level": "INFO",
                "format": "%(asctime)s - %(levelname)s - %(message)s"
            }
        }
    
    def get(self, key_path: str, default=None):
        """設定値を取得（ドット記法対応）"""
        keys = key_path.split('.')
        value = self.config
        
        try:
            for key in keys:
                value = value[key]
            return value
        except (KeyError, TypeError):
            return default
    
    def get_proxy_config(self) -> Dict[str, Optional[str]]:
        """プロキシ設定を取得"""
        return {
            "http": self.get("proxy.http"),
            "https": self.get("proxy.https")
        }
    
    def get_grib2_config(self) -> Dict[str, Any]:
        """GRIB2設定を取得"""
        return {
            "base_url": self.get("grib2.base_url", "http://lunar1.fcd.naps.kishou.go.jp/srf/Grib2/Rtn"),
            "swi_path": self.get("grib2.swi_path", "/swi10"),
            "guidance_path": self.get("grib2.guidance_path", "/gdc"),
            "download_timeout": self.get("grib2.download_timeout", 300),
            "retry_count": self.get("grib2.retry_count", 3),
            "retry_delay": self.get("grib2.retry_delay", 5)
        }

    def get_data_directory(self) -> str:
        """データディレクトリを取得"""
        return self.get("data.directory", "data")

    def build_swi_url(self, initial_time) -> str:
        """SWI GRIB2 URL構築"""
        base_url = self.get("grib2.base_url", "http://lunar1.fcd.naps.kishou.go.jp/srf/Grib2/Rtn")
        swi_path = self.get("grib2.swi_path", "/swi10")
        return f"{base_url}{swi_path}/{initial_time.strftime('%Y/%m/%d')}/Z__C_RJTD_{initial_time.strftime('%Y%m%d%H%M%S')}_SRF_GPV_Ggis1km_Psw_Aper10min_ANAL_grib2.bin"

    def build_guidance_url(self, initial_time) -> str:
        """ガイダンス GRIB2 URL構築"""
        base_url = self.get("grib2.base_url", "http://lunar1.fcd.naps.kishou.go.jp/srf/Grib2/Rtn")
        guidance_path = self.get("grib2.guidance_path", "/gdc")

        # ガイダンスファイル名の時刻変換（0,6,12,18時 → "00"、3,9,15,21時 → "03"）
        hour = initial_time.hour
        if hour % 6 == 0:
            rmax_hour = "00"
        else:
            rmax_hour = "03"

        return f"{base_url}{guidance_path}/{initial_time.strftime('%Y/%m/%d')}/guid_msm_grib2_{initial_time.strftime('%Y%m%d%H%M%S')}_rmax{rmax_hour}.bin"