"""
キャッシュサービス - GRIB2計算結果の圧縮保存・取得

機能:
- gzip圧縮によるJSON保存（209MB → 約20MB）
- キャッシュキー生成（SWI初期時刻 + ガイダンス初期時刻 + ガイダンス種別 + 危険度ルール）
- 自動TTL管理（デフォルト7日）
- メタデータ管理
- 計算中ロック機能（重複計算防止）
"""

import gzip
import json
import logging
import time
import tempfile
from threading import Thread
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, List, Tuple
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

    def _get_meta_path(self, cache_key: str) -> Path:
        """メタデータファイルパス取得（.meta.json）"""
        return self.cache_dir / f"{cache_key}.meta.json"

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
        os.close(fd)
        try:
            with gzip.open(temp_path, 'wt', encoding='utf-8', compresslevel=6) as f:
                json.dump(data, f, ensure_ascii=False)
            os.replace(temp_path, path)
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
        guidance_initial: str,
        guidance_type: str = "msm",
        risk_rule: str = "legacy"
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

            # データ保存（temp file + atomic rename）
            self._write_gzip_json_atomic(cache_path, result)

            elapsed = (datetime.now() - start_time).total_seconds()
            file_size_mb = cache_path.stat().st_size / (1024 * 1024)

            # メタデータ保存
            self._save_metadata(
                cache_key, result, swi_initial, guidance_initial, guidance_type, risk_rule, file_size_mb
            )

            logger.info(f"キャッシュ保存完了: {cache_key} "
                       f"({file_size_mb:.1f}MB, {elapsed:.2f}秒)")

        except Exception as e:
            logger.error(f"キャッシュ保存エラー: {cache_key} - {e}")
            # エラー時は中途半端なファイルを削除
            if cache_path.exists():
                cache_path.unlink()

    def set_cached_result_async(
        self,
        cache_key: str,
        result: dict,
        swi_initial: str,
        guidance_initial: str,
        guidance_type: str = "msm",
        risk_rule: str = "legacy"
    ) -> None:
        """
        計算結果をバックグラウンドでキャッシュ保存する。

        レスポンス返却をブロックしないため、保存処理は daemon thread で実行する。
        """
        logger.info(f"キャッシュ非同期保存を開始: {cache_key}")

        worker = Thread(
            target=self.set_cached_result,
            args=(cache_key, result, swi_initial, guidance_initial, guidance_type, risk_rule),
            daemon=True,
            name=f"cache-save-{cache_key}",
        )
        worker.start()

    def _save_metadata(
        self,
        cache_key: str,
        result: dict,
        swi_initial: str,
        guidance_initial: str,
        guidance_type: str,
        risk_rule: str,
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
            "guidance_type": guidance_type,
            "risk_rule": risk_rule,
            "mesh_count": mesh_count,
            "file_size_mb": round(file_size_mb, 2),
            "compressed": True,
            "compression_format": "gzip"
        }

        self._write_json_atomic(meta_path, metadata)

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

            # 計算完了済みならロック中ではない
            if lock_data.get('completed_at') or lock_data.get('base_session_id'):
                return False

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
                "base_session_id": None  # 計算完了後に設定
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
            base_session_id: 計算完了後のベースセッションID（オプション）
        """
        lock_path = self._get_lock_path(cache_key)

        if base_session_id:
            # ベースセッションIDを保存してからロック解放
            try:
                if lock_path.exists():
                    with open(lock_path, 'r', encoding='utf-8') as f:
                        lock_data = json.load(f)
                    lock_data['base_session_id'] = base_session_id
                    lock_data['completed_at'] = datetime.now().isoformat()
                    self._write_json_atomic(lock_path, lock_data)
                    logger.info(f"ベースセッションID保存: {cache_key} -> {base_session_id}")
            except Exception as e:
                logger.error(f"ベースセッションID保存エラー: {cache_key} - {e}")
            # 完了済みロックは待機中リクエストが参照できるようファイルを残す
            logger.info(f"計算ロック解放: {cache_key}")
            return

        # エラー時やセッション未生成時はロックファイルを削除して再試行可能にする
        try:
            if lock_path.exists():
                lock_path.unlink()
            logger.info(f"計算ロック削除: {cache_key}")
        except Exception as e:
            logger.error(f"計算ロック削除エラー: {cache_key} - {e}")

    def get_base_session_id(self, cache_key: str) -> Optional[str]:
        """
        計算完了後のベースセッションIDを取得

        Args:
            cache_key: キャッシュキー

        Returns:
            ベースセッションID、未完了または存在しない場合None
        """
        lock_path = self._get_lock_path(cache_key)

        if not lock_path.exists():
            return None

        try:
            with open(lock_path, 'r', encoding='utf-8') as f:
                lock_data = json.load(f)
            return lock_data.get('base_session_id')
        except Exception as e:
            logger.error(f"ベースセッションID取得エラー: {cache_key} - {e}")
            return None

    def wait_for_calculation(
        self,
        cache_key: str,
        timeout_seconds: int = 300,
        poll_interval: float = 1.0
    ) -> Tuple[bool, Optional[str]]:
        """
        計算完了を待機

        Args:
            cache_key: キャッシュキー
            timeout_seconds: タイムアウト秒数（デフォルト5分）
            poll_interval: ポーリング間隔秒数

        Returns:
            (成功フラグ, ベースセッションID)
            - 計算完了: (True, session_id)
            - タイムアウト: (False, None)
        """
        logger.info(f"計算完了待機開始: {cache_key} (timeout={timeout_seconds}s)")
        start_time = time.time()

        while time.time() - start_time < timeout_seconds:
            # ベースセッションIDが設定されているか確認
            base_session_id = self.get_base_session_id(cache_key)
            if base_session_id:
                elapsed = time.time() - start_time
                logger.info(f"計算完了検出: {cache_key} ({elapsed:.1f}秒待機)")
                return True, base_session_id

            # 計算中でなければ（異常終了など）待機終了
            if not self.is_calculation_in_progress(cache_key):
                logger.warning(f"計算中ステータス消失: {cache_key}")
                return False, None

            time.sleep(poll_interval)

        logger.warning(f"計算完了待機タイムアウト: {cache_key}")
        return False, None

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
