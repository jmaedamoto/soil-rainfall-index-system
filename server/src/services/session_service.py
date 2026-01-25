#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
セッション管理サービス

計算結果をサーバー側で保持し、クライアントへの段階的データ配信を実現

セッションタイプ:
- ベースセッション: 計算結果の完全なデータを保持（複数ユーザーで共有可能）
- フォークセッション: ベースセッションへの参照 + 編集差分のみを保持（ユーザー固有）
"""

import secrets
import logging
import copy
from typing import Dict, Optional, Any, List
from datetime import datetime, timedelta
from threading import Lock
from models import Prefecture

logger = logging.getLogger(__name__)


class SessionService:
    """
    セッション管理サービス（インメモリ版）

    計算結果をセッションとして保存し、session_idで参照可能にする
    """

    def __init__(self, ttl_hours: int = 1):
        """
        Args:
            ttl_hours: セッションの有効期限（時間）
        """
        self.sessions: Dict[str, Dict[str, Any]] = {}
        self.lock = Lock()
        self.ttl_hours = ttl_hours
        logger.info(f"SessionService initialized with TTL={ttl_hours}h")

    def create_session(
        self,
        prefectures: Dict[str, Prefecture],
        swi_initial_time: str,
        guidance_initial_time: str,
        calculation_time: str
    ) -> str:
        """
        新しいベースセッションを作成

        Args:
            prefectures: 計算結果（全府県データ）
            swi_initial_time: SWI初期時刻
            guidance_initial_time: ガイダンス初期時刻
            calculation_time: 計算時刻

        Returns:
            session_id: セッションID
        """
        session_id = secrets.token_urlsafe(16)

        now = datetime.now()
        expires_at = now + timedelta(hours=self.ttl_hours)

        with self.lock:
            self.sessions[session_id] = {
                'is_fork': False,  # ベースセッション
                'prefectures': prefectures,
                'swi_initial_time': swi_initial_time,
                'guidance_initial_time': guidance_initial_time,
                'calculation_time': calculation_time,
                'created_at': now,
                'expires_at': expires_at,
                'last_accessed': now
            }

        logger.info(
            f"Base session created: {session_id}, "
            f"expires at {expires_at.isoformat()}, "
            f"prefectures: {list(prefectures.keys())}"
        )

        return session_id

    def create_fork_session(
        self,
        base_session_id: str,
        adjustments: Dict[str, List[Dict]],
        recalculated_meshes: Dict[str, Dict]
    ) -> Optional[str]:
        """
        フォークセッションを作成（編集用）

        ベースセッションを参照し、編集差分のみを保持する軽量セッション。
        雨量編集時にベースセッションを変更せず、ユーザー固有の編集結果を保持。

        Args:
            base_session_id: ベースセッションID
            adjustments: 編集データ {"府県名_市町村名": [{"ft": 0, "value": 10.5}, ...]}
            recalculated_meshes: 再計算済みメッシュ結果
                {"mesh_code": {"risk_3hour_max_timeline": [...], "swi_timeline": [...], ...}}

        Returns:
            fork_session_id: フォークセッションID、ベースセッション不在時はNone
        """
        # ベースセッションの存在確認
        base_session = self._get_raw_session(base_session_id)
        if base_session is None:
            logger.error(f"Fork failed: base session not found: {base_session_id}")
            return None

        # ベースセッションがフォークの場合、そのベースを参照
        if base_session.get('is_fork'):
            actual_base_id = base_session.get('base_session_id')
            logger.info(f"Fork of fork detected, using original base: {actual_base_id}")
            base_session_id = actual_base_id

        fork_session_id = secrets.token_urlsafe(16)

        now = datetime.now()
        expires_at = now + timedelta(hours=self.ttl_hours)

        with self.lock:
            self.sessions[fork_session_id] = {
                'is_fork': True,  # フォークセッション
                'base_session_id': base_session_id,
                'adjustments': adjustments,
                'recalculated_meshes': recalculated_meshes,
                'swi_initial_time': base_session['swi_initial_time'],
                'guidance_initial_time': base_session['guidance_initial_time'],
                'created_at': now,
                'expires_at': expires_at,
                'last_accessed': now
            }

        logger.info(
            f"Fork session created: {fork_session_id}, "
            f"base: {base_session_id}, "
            f"adjustments: {len(adjustments)} areas, "
            f"recalculated: {len(recalculated_meshes)} meshes"
        )

        return fork_session_id

    def _get_raw_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        セッションデータを生で取得（マージなし、内部用）

        Args:
            session_id: セッションID

        Returns:
            セッションデータ、または None
        """
        with self.lock:
            session = self.sessions.get(session_id)

            if session is None:
                return None

            # 期限チェック
            if datetime.now() > session['expires_at']:
                del self.sessions[session_id]
                return None

            return session

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        セッションデータを取得

        フォークセッションの場合、ベースセッションのデータと
        フォークの差分をマージして返す。

        Args:
            session_id: セッションID

        Returns:
            セッションデータ、または None（存在しない/期限切れ）
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

            # フォークセッションの場合、ベースとマージ
            if session.get('is_fork'):
                return self._merge_fork_with_base(session)

            return session

    def _merge_fork_with_base(self, fork_session: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        フォークセッションとベースセッションをマージ

        Args:
            fork_session: フォークセッションデータ

        Returns:
            マージされたセッションデータ
        """
        base_session_id = fork_session.get('base_session_id')
        base_session = self.sessions.get(base_session_id)

        if base_session is None:
            logger.error(f"Base session not found for fork: {base_session_id}")
            return None

        # ベースセッションのprefecturesをディープコピー
        merged_prefectures = copy.deepcopy(base_session['prefectures'])

        # フォークの再計算済みメッシュを適用
        recalculated_meshes = fork_session.get('recalculated_meshes', {})

        for pref_code, prefecture in merged_prefectures.items():
            for area in prefecture.get('areas', []):
                for mesh in area.get('meshes', []):
                    mesh_code = mesh.get('code')
                    if mesh_code in recalculated_meshes:
                        # 再計算済みデータで上書き
                        recalc_data = recalculated_meshes[mesh_code]
                        mesh['risk_3hour_max_timeline'] = recalc_data.get(
                            'risk_3hour_max_timeline', mesh.get('risk_3hour_max_timeline', []))
                        mesh['swi_timeline'] = recalc_data.get(
                            'swi_timeline', mesh.get('swi_timeline', []))
                        mesh['rain_timeline'] = recalc_data.get(
                            'rain_timeline', mesh.get('rain_timeline', []))

        # マージ結果を返す
        return {
            'is_fork': True,
            'base_session_id': base_session_id,
            'prefectures': merged_prefectures,
            'swi_initial_time': fork_session['swi_initial_time'],
            'guidance_initial_time': fork_session['guidance_initial_time'],
            'created_at': fork_session['created_at'],
            'expires_at': fork_session['expires_at'],
            'last_accessed': fork_session['last_accessed'],
            'adjustments': fork_session.get('adjustments', {})
        }

    def get_prefecture(
        self,
        session_id: str,
        prefecture_code: str
    ) -> Optional[Prefecture]:
        """
        セッションから特定の府県データを取得

        Args:
            session_id: セッションID
            prefecture_code: 府県コード（例: "shiga"）

        Returns:
            府県データ、または None
        """
        session = self.get_session(session_id)
        if session is None:
            return None

        prefectures = session['prefectures']
        return prefectures.get(prefecture_code)

    def delete_session(self, session_id: str) -> bool:
        """
        セッションを削除

        Args:
            session_id: セッションID

        Returns:
            削除成功: True、セッション不在: False
        """
        with self.lock:
            if session_id in self.sessions:
                del self.sessions[session_id]
                logger.info(f"Session deleted: {session_id}")
                return True
            return False

    def cleanup_expired_sessions(self) -> int:
        """
        期限切れセッションを削除

        Returns:
            削除されたセッション数
        """
        now = datetime.now()
        expired_ids = []

        with self.lock:
            for session_id, session in self.sessions.items():
                if now > session['expires_at']:
                    expired_ids.append(session_id)

            for session_id in expired_ids:
                del self.sessions[session_id]

        if expired_ids:
            logger.info(f"Cleaned up {len(expired_ids)} expired sessions")

        return len(expired_ids)

    def get_session_info(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        セッション情報を取得（デバッグ用）

        Args:
            session_id: セッションID

        Returns:
            セッション情報（メタデータのみ）
        """
        session = self.get_session(session_id)
        if session is None:
            return None

        info = {
            'session_id': session_id,
            'is_fork': session.get('is_fork', False),
            'created_at': session['created_at'].isoformat(),
            'expires_at': session['expires_at'].isoformat(),
            'last_accessed': session['last_accessed'].isoformat(),
            'swi_initial_time': session['swi_initial_time'],
            'guidance_initial_time': session['guidance_initial_time'],
            'prefecture_count': len(session['prefectures']),
            'prefecture_codes': list(session['prefectures'].keys())
        }

        # フォークセッションの場合、追加情報
        if session.get('is_fork'):
            info['base_session_id'] = session.get('base_session_id')
            info['adjustments_count'] = len(session.get('adjustments', {}))

        return info

    def list_sessions(self) -> list:
        """
        全セッション一覧を取得（デバッグ用）

        Returns:
            セッション情報のリスト
        """
        with self.lock:
            return [
                self.get_session_info(session_id)
                for session_id in self.sessions.keys()
            ]

    def get_stats(self) -> Dict[str, Any]:
        """
        セッション統計情報を取得

        Returns:
            統計情報
        """
        with self.lock:
            total = len(self.sessions)

            if total == 0:
                return {
                    'total_sessions': 0,
                    'oldest_session': None,
                    'newest_session': None
                }

            sorted_sessions = sorted(
                self.sessions.items(),
                key=lambda x: x[1]['created_at']
            )

            oldest = sorted_sessions[0][1]
            newest = sorted_sessions[-1][1]

            return {
                'total_sessions': total,
                'oldest_session': {
                    'created_at': oldest['created_at'].isoformat(),
                    'expires_at': oldest['expires_at'].isoformat()
                },
                'newest_session': {
                    'created_at': newest['created_at'].isoformat(),
                    'expires_at': newest['expires_at'].isoformat()
                }
            }
