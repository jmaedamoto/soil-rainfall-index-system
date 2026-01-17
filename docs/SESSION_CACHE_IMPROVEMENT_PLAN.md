# セッション・キャッシュ改善計画

**作成日**: 2026年1月17日
**ステータス**: 検討完了、実装待ち

---

## 1. 背景・目的

本システムでは1回のデータ取得に対するサーバー処理が非常に重い（2-3分）。
同一条件で複数ユーザーからリクエストが来ることが想定されるため、以下を実現したい：

1. **一度計算した結果を複数ユーザーで共有**
2. **計算中に同条件リクエストが来た場合の重複計算防止**
3. **メモリ使用量の効率化**

---

## 2. 現状分析

### 2.1 現在の2層キャッシュ構造

| 層 | サービス | 保存先 | キー | TTL | 複数ユーザー共有 |
|----|---------|--------|------|-----|------------------|
| **計算結果** | `CacheService` | ディスク（gzip） | `swi_時刻_guid_時刻` | 7日 | ✅ 共有される |
| **セッション** | `SessionService` | メモリ | ランダムID | 1時間 | ❌ 共有されない |

### 2.2 関連ファイル

- `server/services/cache_service.py` - ファイルベースキャッシュ
- `server/services/session_service.py` - インメモリセッション管理
- `server/services/main_service.py` - メイン処理（キャッシュ利用）
- `server/src/api/controllers/main_controller.py` - APIエンドポイント
- `server/src/api/controllers/session_controller.py` - セッションAPI

### 2.3 現状で実現されていること

| 要件 | 状態 | 実装箇所 |
|------|------|----------|
| 2回目以降の計算処理スキップ | ✅ | `main_service.py:192-196` |
| 計算結果のディスク保存 | ✅ | `cache_service.py` |
| 複数ユーザーでの計算結果共有 | ✅ | 同上 |

### 2.4 問題点

#### 問題1: 重複計算（Thundering Herd問題）

```
ユーザーA: リクエスト → キャッシュミス → 計算開始（2-3分）
                                          ↓ この間に...
ユーザーB: リクエスト → キャッシュミス → 計算開始（重複！）
```

- 計算中はまだキャッシュに保存されていない
- 同条件の後続リクエストも計算を開始してしまう
- サーバーリソースの無駄遣い

#### 問題2: セッションメモリの重複

```python
# 現在の動作（session_service.py:55）
session_id = secrets.token_urlsafe(16)  # 毎回新規ID生成
```

- 同条件でも各ユーザーに別セッションが作成される
- 同じデータがメモリに重複保持される
- 同時10ユーザー × 数十MB = 数百MBのメモリ消費

---

## 3. 解決策

### 3.1 全体アーキテクチャ

```
┌─────────────────────────────────────────────────────────────────────┐
│                         サービス構成（改善後）                        │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐  │
│  │  CacheService    │  │ ComputationLock  │  │ SessionService   │  │
│  │  (既存)          │  │  Service (新規)  │  │ (改修)           │  │
│  │                  │  │                  │  │                  │  │
│  │ - 計算結果保存   │  │ - 重複計算防止   │  │ - メタデータのみ │  │
│  │ - gzip圧縮       │  │ - 待機管理       │  │ - cache_key参照  │  │
│  │ - TTL 7日        │  │ - タイムアウト   │  │ - 調整時のみ     │  │
│  │                  │  │                  │  │   データ保持     │  │
│  └──────────────────┘  └──────────────────┘  └──────────────────┘  │
│           ↑                    ↑                    ↑               │
│           └────────────────────┼────────────────────┘               │
│                    ┌───────────┴───────────┐                        │
│                    │     MainService       │                        │
│                    │  (オーケストレーション) │                        │
│                    └───────────────────────┘                        │
└─────────────────────────────────────────────────────────────────────┘
```

### 3.2 処理フロー（改善後）

```
リクエスト (swi=12:00, guid=12:00)
     │
     ▼
┌─────────────────┐
│ キャッシュ確認   │
└────────┬────────┘
         │
   ┌─────┴─────┐
   │           │
 ヒット      ミス
   │           │
   ▼           ▼
即座に      ┌─────────────────┐
返却        │ 計算ロック確認   │
            └────────┬────────┘
                     │
               ┌─────┴─────┐
               │           │
          ロック取得成功  ロック取得失敗
          (= 最初の      (= 他が計算中)
            リクエスト)
               │           │
               ▼           ▼
          ┌────────┐   ┌────────────┐
          │ 計算   │   │ 待機       │
          │ 実行   │   │ (通知待ち) │
          └───┬────┘   └─────┬──────┘
              │              │
              ▼              │
          キャッシュ保存     │
          ロック解放 ────────┘
              │              │
              ▼              ▼
          ┌─────────────────────┐
          │ キャッシュから取得   │
          │ セッション作成      │
          │ レスポンス返却      │
          └─────────────────────┘
```

---

## 4. 実装詳細

### 4.1 新規: ComputationLockService

**ファイル**: `server/services/computation_lock_service.py`（新規作成）

```python
# -*- coding: utf-8 -*-
"""
計算ロック管理サービス

同一条件の計算が重複実行されることを防止（Singleflightパターン）
"""

import threading
from typing import Dict
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class ComputationLockService:
    """
    計算ロック管理サービス

    同一条件の計算が重複実行されることを防止
    """

    def __init__(self, timeout_seconds: int = 300):
        """
        Args:
            timeout_seconds: 計算タイムアウト（デフォルト5分）
        """
        self.locks: Dict[str, dict] = {}  # cache_key -> lock_info
        self.condition = threading.Condition()
        self.timeout = timeout_seconds
        logger.info(f"ComputationLockService initialized: timeout={timeout_seconds}s")

    def acquire(self, cache_key: str) -> bool:
        """
        計算ロックを取得

        Args:
            cache_key: キャッシュキー

        Returns:
            True: ロック取得成功（計算を実行すべき）
            False: 他が計算中（待機すべき）
        """
        with self.condition:
            if cache_key in self.locks:
                logger.info(f"Lock already held for {cache_key}")
                return False

            self.locks[cache_key] = {
                'started_at': datetime.now(),
                'thread_id': threading.current_thread().ident
            }
            logger.info(f"Lock acquired for {cache_key}")
            return True

    def release(self, cache_key: str):
        """
        計算完了、ロック解放

        Args:
            cache_key: キャッシュキー
        """
        with self.condition:
            if cache_key in self.locks:
                del self.locks[cache_key]
                logger.info(f"Lock released for {cache_key}")
            self.condition.notify_all()  # 待機中のスレッドに通知

    def wait_for_completion(self, cache_key: str) -> bool:
        """
        他の計算完了を待機

        Args:
            cache_key: キャッシュキー

        Returns:
            True: 完了（キャッシュ利用可能）
            False: タイムアウト
        """
        deadline = datetime.now() + timedelta(seconds=self.timeout)

        with self.condition:
            while cache_key in self.locks:
                remaining = (deadline - datetime.now()).total_seconds()
                if remaining <= 0:
                    logger.warning(f"Wait timeout for {cache_key}")
                    return False
                self.condition.wait(timeout=remaining)

        logger.info(f"Wait completed for {cache_key}")
        return True

    def is_computing(self, cache_key: str) -> bool:
        """計算中かどうか確認"""
        return cache_key in self.locks

    def get_stats(self) -> dict:
        """統計情報取得"""
        with self.condition:
            return {
                'active_locks': len(self.locks),
                'lock_keys': list(self.locks.keys())
            }


# シングルトンインスタンス
_lock_service_instance = None


def get_computation_lock_service() -> ComputationLockService:
    """ComputationLockServiceシングルトン取得"""
    global _lock_service_instance

    if _lock_service_instance is None:
        _lock_service_instance = ComputationLockService()

    return _lock_service_instance
```

### 4.2 改修: MainService

**ファイル**: `server/services/main_service.py`

**変更箇所**: `main_process_from_separate_urls` メソッド

```python
# 追加インポート
from .computation_lock_service import get_computation_lock_service

class MainService:
    def __init__(self, data_dir: str = "data"):
        # ... 既存コード ...
        self.lock_service = get_computation_lock_service()  # 追加

    def main_process_from_separate_urls(
        self,
        swi_url: str,
        guidance_url: str,
        use_cache: bool = True
    ) -> Dict[str, Any]:
        """個別URLベースのメイン処理（ロック機構追加版）"""
        try:
            # GRIB2データダウンロード・解析（キャッシュキー生成のため）
            swi_data_bytes = self.grib2_service.download_file(swi_url)
            guidance_data_bytes = self.grib2_service.download_file(guidance_url)

            base_info, swi_grib2 = self.grib2_service.unpack_swi_grib2(swi_data_bytes)
            guidance_base_info, guidance_grib2 = self.grib2_service.unpack_guidance_grib2(guidance_data_bytes)

            swi_initial_time = base_info.initial_date
            guidance_initial_time = guidance_base_info.initial_date

            # キャッシュキー生成
            cache_key = self.cache_service.generate_cache_key(
                swi_initial_time.isoformat(),
                guidance_initial_time.isoformat()
            )

            # 1. キャッシュ確認
            if use_cache:
                cached_result = self.cache_service.get_cached_result(cache_key)
                if cached_result:
                    logger.info(f"キャッシュヒット: {cache_key}")
                    return cached_result

            # 2. 計算ロック取得を試みる
            if self.lock_service.acquire(cache_key):
                try:
                    # 再度キャッシュ確認（ロック待機中に他が完了した可能性）
                    if use_cache:
                        cached_result = self.cache_service.get_cached_result(cache_key)
                        if cached_result:
                            return cached_result

                    # ロック取得成功 → 計算実行
                    logger.info(f"計算開始: {cache_key}")

                    guidance_grib2_filtered = self._filter_guidance_data(
                        guidance_grib2, swi_initial_time, guidance_initial_time
                    )

                    result = self._process_data(
                        base_info, swi_grib2, guidance_grib2_filtered, swi_initial_time
                    )

                    # キャッシュ保存
                    if use_cache:
                        self.cache_service.set_cached_result(
                            cache_key, result,
                            swi_initial_time.isoformat(),
                            guidance_initial_time.isoformat()
                        )

                    return result

                finally:
                    # ロック解放
                    self.lock_service.release(cache_key)
            else:
                # ロック取得失敗 → 他が計算中 → 待機
                logger.info(f"他が計算中、待機開始: {cache_key}")

                if self.lock_service.wait_for_completion(cache_key):
                    # 計算完了 → キャッシュから取得
                    cached_result = self.cache_service.get_cached_result(cache_key)
                    if cached_result:
                        return cached_result
                    else:
                        raise Exception("計算完了後もキャッシュが見つかりません")
                else:
                    # タイムアウト
                    raise TimeoutError(f"計算タイムアウト: {cache_key}")

        except Exception as e:
            logger.error(f"処理エラー: {e}")
            raise
```

### 4.3 改修: SessionService（キャッシュ参照型）

**ファイル**: `server/services/session_service.py`

```python
# -*- coding: utf-8 -*-
"""
セッション管理サービス（キャッシュ参照型・改修版）

計算結果をサーバー側で保持し、クライアントへの段階的データ配信を実現
メモリ効率化: セッションはメタデータのみ保持、データはキャッシュから参照
"""

import secrets
import logging
import copy
from typing import Dict, Optional, Any
from datetime import datetime, timedelta
from threading import Lock

from .cache_service import CacheService

logger = logging.getLogger(__name__)


class SessionService:
    """
    セッション管理サービス（キャッシュ参照型）

    - 通常時: セッションはメタデータのみ保持、データはCacheServiceから取得
    - 雨量調整時: 調整されたデータのみセッションに保持（Copy-on-Write）
    """

    def __init__(self, cache_service: CacheService, ttl_hours: int = 1):
        """
        Args:
            cache_service: キャッシュサービス
            ttl_hours: セッションの有効期限（時間）
        """
        self.cache_service = cache_service
        self.sessions: Dict[str, Dict[str, Any]] = {}
        self.lock = Lock()
        self.ttl_hours = ttl_hours
        logger.info(f"SessionService initialized (cache-reference mode): TTL={ttl_hours}h")

    def create_session(
        self,
        cache_key: str,
        swi_initial_time: str,
        guidance_initial_time: str,
        available_prefectures: list,
        available_times: list
    ) -> str:
        """
        新しいセッションを作成（メタデータのみ）

        Args:
            cache_key: キャッシュキー（データ参照用）
            swi_initial_time: SWI初期時刻
            guidance_initial_time: ガイダンス初期時刻
            available_prefectures: 利用可能な府県コードリスト
            available_times: 利用可能な時刻リスト

        Returns:
            session_id: セッションID
        """
        session_id = secrets.token_urlsafe(16)

        now = datetime.now()
        expires_at = now + timedelta(hours=self.ttl_hours)

        with self.lock:
            self.sessions[session_id] = {
                'cache_key': cache_key,  # データはキャッシュを参照
                'swi_initial_time': swi_initial_time,
                'guidance_initial_time': guidance_initial_time,
                'available_prefectures': available_prefectures,
                'available_times': available_times,
                'created_at': now,
                'expires_at': expires_at,
                'last_accessed': now,
                'adjusted': False,
                'adjusted_data': None  # 雨量調整時のみデータ保持
            }

        logger.info(
            f"Session created: {session_id}, "
            f"cache_key={cache_key}, "
            f"expires at {expires_at.isoformat()}"
        )

        return session_id

    def get_prefectures(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        セッションから府県データを取得

        Args:
            session_id: セッションID

        Returns:
            府県データ辞書、または None
        """
        with self.lock:
            session = self.sessions.get(session_id)

            if session is None:
                logger.warning(f"Session not found: {session_id}")
                return None

            # 期限チェック
            if datetime.now() > session['expires_at']:
                logger.warning(f"Session expired: {session_id}")
                del self.sessions[session_id]
                return None

            # 最終アクセス時刻更新
            session['last_accessed'] = datetime.now()

            # 雨量調整済みの場合はセッション内のデータを返す
            if session['adjusted'] and session['adjusted_data']:
                return session['adjusted_data']

            # 通常時はキャッシュから取得
            cache_key = session['cache_key']

        # ロック外でキャッシュ読み込み（I/O処理）
        cached_result = self.cache_service.get_cached_result(cache_key)
        if cached_result and 'prefectures' in cached_result:
            return cached_result['prefectures']

        return None

    def mark_as_adjusted(self, session_id: str, adjusted_data: Dict[str, Any]):
        """
        セッションを雨量調整済みとしてマーク

        Args:
            session_id: セッションID
            adjusted_data: 調整後のデータ
        """
        with self.lock:
            if session_id in self.sessions:
                self.sessions[session_id]['adjusted'] = True
                self.sessions[session_id]['adjusted_data'] = adjusted_data
                logger.info(f"Session marked as adjusted: {session_id}")

    def prepare_for_adjustment(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        雨量調整のためにデータをコピー（Copy-on-Write）

        初回調整時にキャッシュからデータをコピーしてセッションに保持

        Args:
            session_id: セッションID

        Returns:
            編集可能なデータのコピー
        """
        with self.lock:
            session = self.sessions.get(session_id)
            if session is None:
                return None

            # 既に調整済みの場合はそのデータを返す
            if session['adjusted'] and session['adjusted_data']:
                return session['adjusted_data']

            cache_key = session['cache_key']

        # キャッシュからデータ取得
        cached_result = self.cache_service.get_cached_result(cache_key)
        if not cached_result or 'prefectures' not in cached_result:
            return None

        # ディープコピーして返す
        adjusted_data = copy.deepcopy(cached_result['prefectures'])

        with self.lock:
            if session_id in self.sessions:
                self.sessions[session_id]['adjusted'] = True
                self.sessions[session_id]['adjusted_data'] = adjusted_data

        return adjusted_data

    # ... 以下、既存メソッド（get_session_info, delete_session等）は
    #     メタデータのみ扱うよう調整 ...
```

---

## 5. 実装優先順位

| 順序 | タスク | 重要度 | 影響範囲 |
|------|--------|--------|----------|
| **1** | ComputationLockService 新規作成 | 最高 | 新規ファイル |
| **2** | MainService にロック機構追加 | 最高 | main_service.py |
| **3** | SessionService をキャッシュ参照型に改修 | 高 | session_service.py |
| **4** | SessionController の調整 | 高 | session_controller.py |
| **5** | MainController の調整 | 中 | main_controller.py |
| **6** | 単体テスト作成 | 中 | 新規ファイル |

---

## 6. テスト観点

### 6.1 ComputationLockService

- [ ] 同一キーでのロック取得は1スレッドのみ成功
- [ ] ロック解放後は他スレッドがキャッシュ取得可能
- [ ] タイムアウト時の適切なエラー処理
- [ ] 複数キーの同時処理

### 6.2 重複計算防止

- [ ] 同条件の同時リクエストで計算は1回のみ
- [ ] 2番目以降のリクエストは待機後にキャッシュから取得
- [ ] 異なる条件のリクエストは並列処理可能

### 6.3 セッション

- [ ] 通常時はキャッシュからデータ取得
- [ ] 雨量調整時はセッション内データを使用
- [ ] メモリ使用量の削減確認

---

## 7. 期待効果

| 指標 | 現状 | 改善後 |
|------|------|--------|
| 同条件重複計算 | 発生する | 発生しない |
| 同条件10ユーザーのメモリ使用 | ~数百MB | ~数KB（調整なし時） |
| 2番目以降のユーザー待機時間 | 2-3分（再計算） | 計算完了まで待機のみ |

---

## 8. 注意事項

### 8.1 スレッドセーフティ

- `threading.Condition` を使用した適切な排他制御
- デッドロック防止のためロック順序を統一

### 8.2 タイムアウト設定

- 計算タイムアウト: 300秒（5分）
- 必要に応じて設定可能に

### 8.3 エラーハンドリング

- ロック取得中の例外発生時は必ずロック解放
- `try-finally` パターンの徹底

### 8.4 雨量調整機能との整合性

- 調整前: キャッシュ参照（共有）
- 調整後: セッション固有データ（Copy-on-Write）

---

## 9. 関連ドキュメント

- `CLAUDE.md` - プロジェクト概要
- `server/deploy/DEPLOY_GUIDE.md` - デプロイ手順

---

**次回作業時**: 上記「5. 実装優先順位」に従って実装を進める
