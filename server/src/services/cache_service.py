"""
キャッシュサービス - GRIB2計算結果の圧縮保存・取得

機能:
- gzip圧縮によるJSON保存（209MB → 約20MB）
- キャッシュキー生成（SWI初期時刻 + ガイダンス初期時刻 + ガイダンス種別 + 危険度ルール）
- 自動TTL管理（デフォルト7日）
- 計算中ロック機能（重複計算防止）
"""

import gzip
import json
import logging
import time
import tempfile
import io
from threading import Thread
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, List, Callable
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
    def generate_cache_key(
        swi_initial: str,
        guidance_initial: str,
        guidance_type: str = "msm",
        risk_rule: str = "legacy"
    ) -> str:
        """
        キャッシュキー生成

        Args:
            swi_initial: SWI初期時刻（ISO8601形式）
            guidance_initial: ガイダンス初期時刻（ISO8601形式）

        Returns:
            キャッシュキー（例: "swi_20251014120000_guid_msm_20251014060000"）
        """
        swi_dt = datetime.fromisoformat(
            swi_initial.replace('Z', '+00:00'))
        guid_dt = datetime.fromisoformat(
            guidance_initial.replace('Z', '+00:00'))

        swi_key = swi_dt.strftime("%Y%m%d%H%M%S")
        guid_key = guid_dt.strftime("%Y%m%d%H%M%S")

        return f"swi_{swi_key}_guid_{guidance_type.lower()}_{guid_key}_risk_{risk_rule.lower()}"

    def _get_cache_path(self, cache_key: str) -> Path:
        """キャッシュファイルパス取得（.json.gz）"""
        return self.cache_dir / f"{cache_key}.json.gz"

    def _get_cache_temp_glob(self, cache_key: str) -> str:
        """キャッシュ保存中の一時ファイルglob"""
        return f"{cache_key}.json.gz.*.tmp"

    def _get_legacy_meta_path(self, cache_key: str) -> Path:
        """旧メタデータファイルパス取得（後方互換の削除用）"""
        return self.cache_dir / f"{cache_key}.meta.json"

    @staticmethod
    def _extract_cache_sample(result: dict) -> dict:
        """キャッシュ内容比較用に先頭府県・先頭エリア・先頭メッシュの要約を返す"""
        prefectures = result.get("prefectures") or {}
        if not prefectures:
            return {"prefecture_count": 0}

        pref_code, prefecture = next(iter(prefectures.items()))
        areas = prefecture.get("areas") or []
        if not areas:
            return {
                "prefecture_count": len(prefectures),
                "pref_code": pref_code,
                "area_count": 0,
            }

        area = areas[0]
        meshes = area.get("meshes") or []
        if not meshes:
            return {
                "prefecture_count": len(prefectures),
                "pref_code": pref_code,
                "area_name": area.get("name"),
                "mesh_count": 0,
                "area_risk_timeline": area.get("risk_timeline", [])[:3],
            }

        mesh = meshes[0]
        return {
            "prefecture_count": len(prefectures),
            "pref_code": pref_code,
            "area_name": area.get("name"),
            "mesh_count": len(meshes),
            "mesh_code": mesh.get("code"),
            "mesh_swi_timeline": mesh.get("swi_timeline", [])[:3],
            "mesh_risk_3hour_max_timeline": mesh.get("risk_3hour_max_timeline", [])[:3],
            "mesh_risk_hourly_timeline": mesh.get("risk_hourly_timeline", [])[:6],
            "area_risk_timeline": area.get("risk_timeline", [])[:3],
            "prefecture_risk_timeline": prefecture.get("prefecture_risk_timeline", [])[:3],
        }

    def _write_json_atomic(self, path: Path, data: dict) -> None:
        """JSONを一時ファイル経由で原子的に保存する"""
        fd, temp_path = tempfile.mkstemp(
            prefix=f"{path.name}.",
            suffix=".tmp",
            dir=str(path.parent),
            text=True,
        )
        try:
            with os.fdopen(fd, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
                f.flush()
                os.fsync(f.fileno())
            os.replace(temp_path, path)
        except Exception:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
            raise

    def _write_gzip_json_atomic(self, path: Path, data: dict) -> None:
        """gzip JSONを一時ファイル経由で原子的に保存する"""
        fd, temp_path = tempfile.mkstemp(
            prefix=f"{path.name}.",
            suffix=".tmp",
            dir=str(path.parent),
        )
        try:
            with os.fdopen(fd, 'wb') as raw_file:
                with gzip.GzipFile(
                    filename='',
                    mode='wb',
                    fileobj=raw_file,
                    compresslevel=6,
                ) as gzip_file:
                    with io.TextIOWrapper(gzip_file, encoding='utf-8') as text_file:
                        json.dump(data, text_file, ensure_ascii=False)
                        text_file.flush()
                raw_file.flush()
                os.fsync(raw_file.fileno())
            os.replace(temp_path, path)
            dir_fd = os.open(path.parent, os.O_RDONLY)
            try:
                os.fsync(dir_fd)
            finally:
                os.close(dir_fd)
        except Exception:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
            raise

    def exists(self, cache_key: str) -> bool:
        """
        キャッシュ存在確認

        Args:
            cache_key: キャッシュキー

        Returns:
            存在する場合True
        """
        return self._get_cache_path(cache_key).exists()

    def is_cache_write_in_progress(self, cache_key: str) -> bool:
        """キャッシュ保存用tmpファイルが存在するか確認"""
        return any(self.cache_dir.glob(self._get_cache_temp_glob(cache_key)))

    def is_cache_materializing(self, cache_key: str) -> bool:
        """キャッシュ本体はあるが保存用tmpがまだ残っている中間状態か確認"""
        cache_exists = self._get_cache_path(cache_key).exists()
        return cache_exists and self.is_cache_write_in_progress(cache_key)

    def wait_for_cache_materialization(
        self,
        cache_key: str,
        timeout_seconds: float = 10.0,
        poll_interval: float = 0.2,
    ) -> bool:
        """
        保存中tmpの完了と本体gzの出現を短時間待機する
        """
        cache_path = self._get_cache_path(cache_key)
        start_time = time.time()

        while time.time() - start_time < timeout_seconds:
            if (
                cache_path.exists()
                and not self.is_cache_write_in_progress(cache_key)
            ):
                return True
            time.sleep(poll_interval)

        return cache_path.exists() and not self.is_cache_write_in_progress(cache_key)

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
            sample = self._extract_cache_sample(result)

            logger.info(f"キャッシュ読み込み完了: {cache_key} "
                       f"({file_size_mb:.1f}MB, {elapsed:.2f}秒)")
            logger.info("キャッシュ読み込み内容サンプル: cache_key=%s sample=%s", cache_key, sample)

            return result

        except Exception as e:
            logger.error(f"キャッシュ読み込みエラー: {cache_key} - {e}")
            return None

    def set_cached_result(
        self,
        cache_key: str,
        result: dict,
        swi_initial: str,
        guidance_initial: str,
        guidance_type: str = "msm",
        risk_rule: str = "legacy"
    ) -> bool:
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
            legacy_meta_path = self._get_legacy_meta_path(cache_key)

            # データ保存（temp file + atomic rename）
            self._write_gzip_json_atomic(cache_path, result)
            if legacy_meta_path.exists():
                legacy_meta_path.unlink()

            elapsed = (datetime.now() - start_time).total_seconds()
            file_size_mb = cache_path.stat().st_size / (1024 * 1024)

            logger.info(f"キャッシュ保存完了: {cache_key} "
                       f"({file_size_mb:.1f}MB, {elapsed:.2f}秒)")
            return True

        except Exception as e:
            logger.error(f"キャッシュ保存エラー: {cache_key} - {e}")
            # エラー時は中途半端なファイルを削除
            if cache_path.exists():
                cache_path.unlink()
            legacy_meta_path = self._get_legacy_meta_path(cache_key)
            if legacy_meta_path.exists():
                legacy_meta_path.unlink()
            return False

    def set_cached_result_async(
        self,
        cache_key: str,
        result: dict,
        swi_initial: str,
        guidance_initial: str,
        guidance_type: str = "msm",
        risk_rule: str = "legacy",
        on_complete: Optional[Callable[[bool], None]] = None,
    ) -> None:
        """
        計算結果をバックグラウンドでキャッシュ保存する。

        レスポンス返却をブロックしないため、保存処理は daemon thread で実行する。
        """
        logger.info(f"キャッシュ非同期保存を開始: {cache_key}")

        def run_save() -> None:
            success = self.set_cached_result(
                cache_key,
                result,
                swi_initial,
                guidance_initial,
                guidance_type,
                risk_rule,
            )
            if on_complete:
                try:
                    on_complete(success)
                except Exception as callback_error:
                    logger.error(
                        f"キャッシュ保存完了コールバックエラー: {cache_key} - {callback_error}"
                    )

        worker = Thread(
            target=run_save,
            daemon=True,
            name=f"cache-save-{cache_key}",
        )
        worker.start()

    def _build_metadata_from_gzip(self, cache_key: str) -> Optional[Dict]:
        """gzip ファイルから管理用メタデータを組み立てる"""
        cache_path = self._get_cache_path(cache_key)
        if not cache_path.exists():
            return None

        try:
            cache_stat = cache_path.stat()
            return {
                "cache_key": cache_key,
                "created_at": datetime.fromtimestamp(cache_stat.st_mtime).isoformat(),
                "file_size_mb": round(cache_stat.st_size / (1024 * 1024), 2),
                "compressed": True,
                "compression_format": "gzip",
            }
        except Exception as e:
            logger.error(f"gzipメタデータ生成エラー: {cache_key} - {e}")
            return None

    def get_metadata(self, cache_key: str) -> Optional[Dict]:
        """gzipファイル由来のメタデータを取得"""
        return self._build_metadata_from_gzip(cache_key)

    def _is_cache_valid(self, cache_key: str) -> bool:
        """
        キャッシュ有効期限チェック

        Args:
            cache_key: キャッシュキー

        Returns:
            有効期限内の場合True
        """
        cache_path = self._get_cache_path(cache_key)
        if not cache_path.exists():
            return False

        created_at = datetime.fromtimestamp(cache_path.stat().st_mtime)
        expiry_date = created_at + timedelta(days=self.default_ttl_days)

        return datetime.now() < expiry_date

    def invalidate_cache(self, cache_key: str):
        """
        キャッシュ無効化（削除）

        Args:
            cache_key: キャッシュキー
        """
        cache_path = self._get_cache_path(cache_key)
        legacy_meta_path = self._get_legacy_meta_path(cache_key)

        if cache_path.exists():
            cache_path.unlink()
            logger.info(f"キャッシュ削除: {cache_key}")

        if legacy_meta_path.exists():
            legacy_meta_path.unlink()

    def list_caches(self) -> List[Dict]:
        """
        全キャッシュ一覧取得

        Returns:
            キャッシュ情報のリスト
        """
        caches = []

        for cache_path in self.cache_dir.glob("*.json.gz"):
            cache_key = cache_path.name[:-8]
            metadata = self._build_metadata_from_gzip(cache_key)
            if metadata:
                caches.append(metadata)

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

        for cache_path in self.cache_dir.glob("*.json.gz"):
            cache_key = cache_path.name[:-8]
            try:
                if not self._is_cache_valid(cache_key):
                    self.invalidate_cache(cache_key)
                    deleted_count += 1
            except Exception as e:
                logger.error(f"期限切れチェックエラー: {cache_path} - {e}")

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

    # ========================================
    # 計算中ロック機能（重複計算防止）
    # ========================================

    def _get_lock_path(self, cache_key: str) -> Path:
        """計算中ロックファイルパス取得（.calculating.json）"""
        return self.cache_dir / f"{cache_key}.calculating.json"

    def is_calculation_in_progress(self, cache_key: str) -> bool:
        """
        計算中かどうか確認

        Args:
            cache_key: キャッシュキー

        Returns:
            計算中の場合True
        """
        lock_path = self._get_lock_path(cache_key)
        if not lock_path.exists():
            return False

        # ロックファイルのタイムアウトチェック（10分）
        try:
            with open(lock_path, 'r', encoding='utf-8') as f:
                lock_data = json.load(f)

            started_at = datetime.fromisoformat(lock_data['started_at'])
            if datetime.now() - started_at > timedelta(minutes=10):
                # タイムアウト: 古いロックを削除
                logger.warning(f"計算ロックタイムアウト: {cache_key}")
                self.release_calculation_lock(cache_key)
                return False
            return True
        except Exception as e:
            logger.error(f"ロックファイル読み込みエラー: {cache_key} - {e}")
            return False

    def acquire_calculation_lock(self, cache_key: str) -> bool:
        """
        計算ロックを取得

        Args:
            cache_key: キャッシュキー

        Returns:
            ロック取得成功: True、既にロック中: False
        """
        lock_path = self._get_lock_path(cache_key)

        try:
            lock_data = {
                "cache_key": cache_key,
                "started_at": datetime.now().isoformat(),
            }
            fd = os.open(
                lock_path,
                os.O_WRONLY | os.O_CREAT | os.O_EXCL,
                0o644,
            )
            with os.fdopen(fd, 'w', encoding='utf-8') as f:
                json.dump(lock_data, f, ensure_ascii=False, indent=2)
                f.flush()
                os.fsync(f.fileno())

            logger.info(f"計算ロック取得成功: {cache_key}")
            return True

        except FileExistsError:
            if self.is_calculation_in_progress(cache_key):
                logger.info(f"計算ロック取得失敗（既にロック中）: {cache_key}")
                return False
            logger.warning(f"古い計算ロックを検出: {cache_key} - 再取得を試行")
            try:
                if lock_path.exists():
                    lock_path.unlink()
            except Exception as cleanup_error:
                logger.error(f"古いロック削除エラー: {cache_key} - {cleanup_error}")
                return False
            return self.acquire_calculation_lock(cache_key)
        except Exception as e:
            logger.error(f"計算ロック取得エラー: {cache_key} - {e}")
            return False

    def release_calculation_lock(self, cache_key: str, base_session_id: str = None):
        """
        計算ロックを解放

        Args:
            cache_key: キャッシュキー
            base_session_id: 互換性維持のための未使用引数
        """
        lock_path = self._get_lock_path(cache_key)

        try:
            if lock_path.exists():
                lock_path.unlink()
            logger.info(f"計算ロック削除: {cache_key}")
        except Exception as e:
            logger.error(f"計算ロック削除エラー: {cache_key} - {e}")

    def cleanup_calculation_locks(self, max_age_minutes: int = 30) -> int:
        """
        古い計算ロックファイルを削除

        Args:
            max_age_minutes: 削除対象の経過時間（分）

        Returns:
            削除したロックファイル数
        """
        deleted_count = 0
        cutoff_time = datetime.now() - timedelta(minutes=max_age_minutes)

        for lock_path in self.cache_dir.glob("*.calculating.json"):
            try:
                with open(lock_path, 'r', encoding='utf-8') as f:
                    lock_data = json.load(f)
                started_at = datetime.fromisoformat(lock_data['started_at'])
                if started_at < cutoff_time:
                    lock_path.unlink()
                    deleted_count += 1
                    logger.info(f"古い計算ロック削除: {lock_path.name}")
            except Exception as e:
                logger.error(f"計算ロッククリーンアップエラー: {lock_path} - {e}")

        return deleted_count


# シングルトンインスタンス
_cache_service_instance = None

# デフォルトキャッシュディレクトリ（開発環境用）
DEFAULT_CACHE_DIR = "cache"


def get_cache_service() -> CacheService:
    """
    CacheServiceシングルトン取得

    環境変数 CACHE_DIR でキャッシュディレクトリを指定可能。
    - 未設定の場合: "cache" (開発環境用)
    - 本番環境: 環境変数で指定されたディレクトリをそのまま使用

    Returns:
        CacheServiceインスタンス
    """
    global _cache_service_instance

    if _cache_service_instance is None:
        cache_root = os.environ.get("CACHE_DIR")
        if cache_root:
            # 本番環境: 環境変数で指定されたディレクトリをそのまま使用
            cache_dir = cache_root
        else:
            # 開発環境: デフォルトの cache フォルダを使用
            cache_dir = DEFAULT_CACHE_DIR
        logger.info(f"キャッシュディレクトリ設定: {cache_dir}")
        _cache_service_instance = CacheService(cache_dir=cache_dir)

    return _cache_service_instance
