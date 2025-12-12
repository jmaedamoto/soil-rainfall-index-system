#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
セッション管理サービス

計算結果をサーバー側で保持し、クライアントへの段階的データ配信を実現
"""

import secrets
import logging
from typing import Dict, Optional, Any
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
        新しいセッションを作成

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
                'prefectures': prefectures,
                'swi_initial_time': swi_initial_time,
                'guidance_initial_time': guidance_initial_time,
                'calculation_time': calculation_time,
                'created_at': now,
                'expires_at': expires_at,
                'last_accessed': now
            }

        logger.info(
            f"Session created: {session_id}, "
            f"expires at {expires_at.isoformat()}, "
            f"prefectures: {list(prefectures.keys())}"
        )

        return session_id

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        セッションデータを取得

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

            return session

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

        return {
            'session_id': session_id,
            'created_at': session['created_at'].isoformat(),
            'expires_at': session['expires_at'].isoformat(),
            'last_accessed': session['last_accessed'].isoformat(),
            'swi_initial_time': session['swi_initial_time'],
            'guidance_initial_time': session['guidance_initial_time'],
            'prefecture_count': len(session['prefectures']),
            'prefecture_codes': list(session['prefectures'].keys())
        }

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
