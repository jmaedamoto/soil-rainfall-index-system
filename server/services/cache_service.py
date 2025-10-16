"""
キャッシュサービス - GRIB2計算結果の圧縮保存・取得

機能:
- gzip圧縮によるJSON保存（209MB → 約20MB）
- キャッシュキー生成（SWI初期時刻 + ガイダンス初期時刻）
- 自動TTL管理（デフォルト7日）
- メタデータ管理
"""

import gzip
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, List
import os

logger = logging.getLogger(__name__)


class CacheService:
    """
    キャッシュサービスクラス

    GRIB2解析結果をgzip圧縮して保存・取得
    """

    def __init__(self, cache_dir: str = "cache", default_ttl_days: int = 7):
        """
        初期化

        Args:
            cache_dir: キャッシュディレクトリパス
            default_ttl_days: デフォルトTTL（日数）
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.default_ttl_days = default_ttl_days

        logger.info(f"CacheService初期化: dir={self.cache_dir}, "
                    f"TTL={default_ttl_days}日")

    @staticmethod
    def generate_cache_key(swi_initial: str, guidance_initial: str) -> str:
        """
        キャッシュキー生成

        Args:
            swi_initial: SWI初期時刻（ISO8601形式）
            guidance_initial: ガイダンス初期時刻（ISO8601形式）

        Returns:
            キャッシュキー（例: "swi_20251014120000_guid_20251014060000"）
        """
        swi_dt = datetime.fromisoformat(
            swi_initial.replace('Z', '+00:00'))
        guid_dt = datetime.fromisoformat(
            guidance_initial.replace('Z', '+00:00'))

        swi_key = swi_dt.strftime("%Y%m%d%H%M%S")
        guid_key = guid_dt.strftime("%Y%m%d%H%M%S")

        return f"swi_{swi_key}_guid_{guid_key}"

    def _get_cache_path(self, cache_key: str) -> Path:
        """キャッシュファイルパス取得（.json.gz）"""
        return self.cache_dir / f"{cache_key}.json.gz"

    def _get_meta_path(self, cache_key: str) -> Path:
        """メタデータファイルパス取得（.meta.json）"""
        return self.cache_dir / f"{cache_key}.meta.json"

    def exists(self, cache_key: str) -> bool:
        """
        キャッシュ存在確認

        Args:
            cache_key: キャッシュキー

        Returns:
            存在する場合True
        """
        return self._get_cache_path(cache_key).exists()

    def get_cached_result(self, cache_key: str) -> Optional[dict]:
        """
        キャッシュから結果取得

        Args:
            cache_key: キャッシュキー

        Returns:
            キャッシュされたデータ、存在しない場合None
        """
        cache_path = self._get_cache_path(cache_key)

        if not cache_path.exists():
            logger.info(f"キャッシュ未存在: {cache_key}")
            return None

        # TTLチェック
        if not self._is_cache_valid(cache_key):
            logger.info(f"キャッシュ期限切れ: {cache_key}")
            self.invalidate_cache(cache_key)
            return None

        try:
            logger.info(f"キャッシュ読み込み開始: {cache_key}")
            start_time = datetime.now()

            with gzip.open(cache_path, 'rt', encoding='utf-8') as f:
                result = json.load(f)

            elapsed = (datetime.now() - start_time).total_seconds()
            file_size_mb = cache_path.stat().st_size / (1024 * 1024)

            logger.info(f"キャッシュ読み込み完了: {cache_key} "
                       f"({file_size_mb:.1f}MB, {elapsed:.2f}秒)")

            return result

        except Exception as e:
            logger.error(f"キャッシュ読み込みエラー: {cache_key} - {e}")
            return None

    def set_cached_result(
        self,
        cache_key: str,
        result: dict,
        swi_initial: str,
        guidance_initial: str
    ):
        """
        計算結果をキャッシュに保存

        Args:
            cache_key: キャッシュキー
            result: 保存するデータ
            swi_initial: SWI初期時刻
            guidance_initial: ガイダンス初期時刻
        """
        cache_path = self._get_cache_path(cache_key)

        try:
            logger.info(f"キャッシュ保存開始: {cache_key}")
            start_time = datetime.now()

            # データ保存（gzip圧縮、レベル6=バランス良い）
            with gzip.open(cache_path, 'wt', encoding='utf-8',
                          compresslevel=6) as f:
                json.dump(result, f, ensure_ascii=False)

            elapsed = (datetime.now() - start_time).total_seconds()
            file_size_mb = cache_path.stat().st_size / (1024 * 1024)

            # メタデータ保存
            self._save_metadata(cache_key, result, swi_initial,
                               guidance_initial, file_size_mb)

            logger.info(f"キャッシュ保存完了: {cache_key} "
                       f"({file_size_mb:.1f}MB, {elapsed:.2f}秒)")

        except Exception as e:
            logger.error(f"キャッシュ保存エラー: {cache_key} - {e}")
            # エラー時は中途半端なファイルを削除
            if cache_path.exists():
                cache_path.unlink()

    def _save_metadata(
        self,
        cache_key: str,
        result: dict,
        swi_initial: str,
        guidance_initial: str,
        file_size_mb: float
    ):
        """メタデータ保存"""
        meta_path = self._get_meta_path(cache_key)

        # メッシュ数をカウント
        mesh_count = 0
        if 'prefectures' in result:
            for pref_data in result['prefectures'].values():
                if 'areas' in pref_data:
                    for area in pref_data['areas']:
                        if 'meshes' in area:
                            mesh_count += len(area['meshes'])

        metadata = {
            "cache_key": cache_key,
            "created_at": datetime.now().isoformat(),
            "swi_initial": swi_initial,
            "guidance_initial": guidance_initial,
            "mesh_count": mesh_count,
            "file_size_mb": round(file_size_mb, 2),
            "compressed": True,
            "compression_format": "gzip"
        }

        with open(meta_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)

    def get_metadata(self, cache_key: str) -> Optional[Dict]:
        """
        メタデータ取得

        Args:
            cache_key: キャッシュキー

        Returns:
            メタデータ、存在しない場合None
        """
        meta_path = self._get_meta_path(cache_key)

        if not meta_path.exists():
            return None

        try:
            with open(meta_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"メタデータ読み込みエラー: {cache_key} - {e}")
            return None

    def _is_cache_valid(self, cache_key: str) -> bool:
        """
        キャッシュ有効期限チェック

        Args:
            cache_key: キャッシュキー

        Returns:
            有効期限内の場合True
        """
        metadata = self.get_metadata(cache_key)

        if not metadata or 'created_at' not in metadata:
            return False

        created_at = datetime.fromisoformat(metadata['created_at'])
        expiry_date = created_at + timedelta(days=self.default_ttl_days)

        return datetime.now() < expiry_date

    def invalidate_cache(self, cache_key: str):
        """
        キャッシュ無効化（削除）

        Args:
            cache_key: キャッシュキー
        """
        cache_path = self._get_cache_path(cache_key)
        meta_path = self._get_meta_path(cache_key)

        if cache_path.exists():
            cache_path.unlink()
            logger.info(f"キャッシュ削除: {cache_key}")

        if meta_path.exists():
            meta_path.unlink()

    def list_caches(self) -> List[Dict]:
        """
        全キャッシュ一覧取得

        Returns:
            キャッシュ情報のリスト
        """
        caches = []

        for meta_path in self.cache_dir.glob("*.meta.json"):
            try:
                with open(meta_path, 'r', encoding='utf-8') as f:
                    metadata = json.load(f)
                    caches.append(metadata)
            except Exception as e:
                logger.error(f"メタデータ読み込みエラー: {meta_path} - {e}")

        # 作成日時でソート（新しい順）
        caches.sort(key=lambda x: x.get('created_at', ''), reverse=True)

        return caches

    def cleanup_expired_caches(self) -> int:
        """
        期限切れキャッシュの自動削除

        Returns:
            削除したキャッシュ数
        """
        deleted_count = 0

        for meta_path in self.cache_dir.glob("*.meta.json"):
            try:
                with open(meta_path, 'r', encoding='utf-8') as f:
                    metadata = json.load(f)

                cache_key = metadata.get('cache_key')
                if cache_key and not self._is_cache_valid(cache_key):
                    self.invalidate_cache(cache_key)
                    deleted_count += 1

            except Exception as e:
                logger.error(f"期限切れチェックエラー: {meta_path} - {e}")

        if deleted_count > 0:
            logger.info(f"期限切れキャッシュ削除完了: {deleted_count}件")

        return deleted_count

    def get_cache_stats(self) -> Dict:
        """
        キャッシュ統計情報取得

        Returns:
            統計情報（キャッシュ数、総サイズ等）
        """
        caches = self.list_caches()

        total_size_mb = sum(
            cache.get('file_size_mb', 0) for cache in caches)
        total_meshes = sum(
            cache.get('mesh_count', 0) for cache in caches)

        return {
            "cache_count": len(caches),
            "total_size_mb": round(total_size_mb, 2),
            "total_meshes": total_meshes,
            "cache_dir": str(self.cache_dir),
            "ttl_days": self.default_ttl_days
        }


# シングルトンインスタンス
_cache_service_instance = None


def get_cache_service() -> CacheService:
    """
    CacheServiceシングルトン取得

    Returns:
        CacheServiceインスタンス
    """
    global _cache_service_instance

    if _cache_service_instance is None:
        _cache_service_instance = CacheService()

    return _cache_service_instance
