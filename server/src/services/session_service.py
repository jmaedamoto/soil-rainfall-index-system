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
import json
import os
import tempfile
from typing import Dict, Optional, Any, List
from datetime import datetime, timedelta
from threading import Lock
from pathlib import Path
from models import Prefecture
from services.cache_service import get_cache_service

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
        self.cache_service = get_cache_service()
        self.session_ref_dir = self.cache_service.cache_dir / "session_refs"
        self.session_ref_dir.mkdir(exist_ok=True)
        logger.info(f"SessionService initialized with TTL={ttl_hours}h")

    def _build_base_session_data(
        self,
        prefectures: Dict[str, Prefecture],
        swi_initial_time: str,
        guidance_initial_time: str,
        calculation_time: str,
        guidance_type: str,
        risk_rule: str,
        cache_key: Optional[str],
    ) -> Dict[str, Any]:
        now = datetime.now()
        expires_at = now + timedelta(hours=self.ttl_hours)
        return {
            'is_fork': False,
            'prefectures': prefectures,
            'swi_initial_time': swi_initial_time,
            'guidance_initial_time': guidance_initial_time,
            'guidance_type': guidance_type,
            'risk_rule': risk_rule,
            'input_mode': '3hour',
            'adjustment_mode': 'ratio_3hour',
            'calculation_time': calculation_time,
            'cache_key': cache_key,
            'created_at': now,
            'expires_at': expires_at,
            'last_accessed': now,
        }

    def _get_session_ref_path(self, session_id: str) -> Path:
        return self.session_ref_dir / f"{session_id}.json"

    def _write_json_atomic(self, path: Path, data: Dict[str, Any]) -> None:
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

    def _save_session_reference(
        self,
        session_id: str,
        session_data: Dict[str, Any]
    ) -> None:
        cache_key = session_data.get('cache_key')
        if not cache_key:
            return

        ref_path = self._get_session_ref_path(session_id)
        payload = {
            "session_id": session_id,
            "cache_key": cache_key,
            "swi_initial_time": session_data['swi_initial_time'],
            "guidance_initial_time": session_data['guidance_initial_time'],
            "guidance_type": session_data.get('guidance_type', 'msm'),
            "risk_rule": session_data.get('risk_rule', 'legacy'),
            "calculation_time": session_data.get('calculation_time'),
        }
        self._write_json_atomic(ref_path, payload)

    def _restore_session_from_reference(self, session_id: str) -> Optional[Dict[str, Any]]:
        ref_path = self._get_session_ref_path(session_id)
        if not ref_path.exists():
            return None

        try:
            with open(ref_path, 'r', encoding='utf-8') as f:
                ref_data = json.load(f)
        except Exception as e:
            logger.error(f"Session reference read error: {session_id} - {e}")
            return None

        cache_key = ref_data.get("cache_key")
        if not cache_key:
            return None

        cached_result = self.cache_service.get_cached_result(cache_key)
        if not cached_result:
            cache_write_in_progress = self.cache_service.is_cache_write_in_progress(cache_key)
            cache_materializing = self.cache_service.is_cache_materializing(cache_key)
            calculation_in_progress = self.cache_service.is_calculation_in_progress(cache_key)

            if cache_write_in_progress or cache_materializing or calculation_in_progress:
                logger.info(
                    "Session restore waiting for cache: session=%s cache=%s calculating=%s tmp=%s materializing=%s",
                    session_id,
                    cache_key,
                    calculation_in_progress,
                    cache_write_in_progress,
                    cache_materializing,
                )
                if self.cache_service.wait_for_cache_materialization(
                    cache_key,
                    timeout_seconds=300.0,
                ):
                    cached_result = self.cache_service.get_cached_result(cache_key)

        if not cached_result or 'prefectures' not in cached_result:
            logger.warning(f"Session restore skipped, cache unavailable: {session_id} -> {cache_key}")
            return None

        session_data = self._build_base_session_data(
            cached_result['prefectures'],
            ref_data['swi_initial_time'],
            ref_data['guidance_initial_time'],
            ref_data.get('calculation_time') or datetime.now().isoformat(),
            ref_data.get('guidance_type', 'msm'),
            ref_data.get('risk_rule', 'legacy'),
            cache_key,
        )

        with self.lock:
            self.sessions[session_id] = session_data

        logger.info(f"Session restored from cache reference: {session_id} -> {cache_key}")
        return session_data

    def create_session(
        self,
        prefectures: Dict[str, Prefecture],
        swi_initial_time: str,
        guidance_initial_time: str,
        calculation_time: str,
        guidance_type: str = 'msm',
        risk_rule: str = 'legacy',
        cache_key: Optional[str] = None
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
        session_data = self._build_base_session_data(
            prefectures,
            swi_initial_time,
            guidance_initial_time,
            calculation_time,
            guidance_type,
            risk_rule,
            cache_key,
        )

        with self.lock:
            self.sessions[session_id] = session_data

        self._save_session_reference(session_id, session_data)

        logger.info(
            f"Base session created: {session_id}, "
            f"expires at {session_data['expires_at'].isoformat()}, "
            f"prefectures: {list(prefectures.keys())}"
        )

        return session_id

    def create_fork_session(
        self,
        base_session_id: str,
        adjustments: Dict[str, List[Dict]],
        recalculated_meshes: Dict[str, Dict],
        input_mode: str = '3hour',
        adjustment_mode: str = 'ratio_3hour'
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
                'guidance_type': base_session.get('guidance_type', 'msm'),
                'risk_rule': base_session.get('risk_rule', 'legacy'),
                'input_mode': input_mode,
                'adjustment_mode': adjustment_mode,
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

        # --- A案: fork作成時に一度だけベースとマージしてprefecturesを確定（materialize） ---
        # これにより以後の get_session() で毎回マージを行わずに済む
        try:
            merged = self.get_session(fork_session_id)  # この1回だけ _merge_fork_with_base が走る
            if merged is None:
                logger.error(f"Failed to materialize fork session: {fork_session_id}")
            else:
                with self.lock:
                    s = self.sessions.get(fork_session_id)
                    if s is not None and s.get('is_fork') and 'prefectures' not in s:
                        # マージ済みprefecturesを保存して、以後のget_sessionでマージを発生させない
                        s['prefectures'] = merged['prefectures']
                        s['materialized'] = True

                        # 差分は以後不要なので捨ててメモリを節約
                        s.pop('recalculated_meshes', None)
                        logger.info(f"Fork session materialized: {fork_session_id}")
        except Exception:
            logger.exception(f"Exception while materializing fork session: {fork_session_id}")
        # --- ここまで ---

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
            logger.warning(f"Session not found in memory: {session_id}")
            session = self._restore_session_from_reference(session_id)
            if session is None:
                return None

        with self.lock:
            # 復元直後に別スレッドが更新している可能性があるため再取得
            session = self.sessions.get(session_id, session)

            # 期限チェック
            if datetime.now() > session['expires_at']:
                logger.warning(f"Session expired: {session_id}")
                del self.sessions[session_id]
                return None

            # 最終アクセス時刻更新
            session['last_accessed'] = datetime.now()

            # フォークセッションの場合
            if session.get('is_fork'):
                # A案: forkが既にmaterialize済みなら、そのまま返す（毎回マージしない）
                if 'prefectures' in session:
                    return session
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
        import time
        merge_start = time.time()

        base_session_id = fork_session.get('base_session_id')
        base_session = self.sessions.get(base_session_id)

        if base_session is None:
            logger.error(f"Base session not found for fork: {base_session_id}")
            return None

        # フォークの再計算済みメッシュを適用
        recalculated_meshes = fork_session.get('recalculated_meshes', {})
        recalculated_mesh_codes = set(recalculated_meshes.keys())

        # Step 1: 影響を受ける府県を特定（O(N)スキャンを避ける）
        # メッシュコードから府県を逆引きするインデックスを構築
        mesh_to_pref = {}
        for pref_code, prefecture in base_session['prefectures'].items():
            for area in prefecture.get('areas', []):
                for mesh in area.get('meshes', []):
                    mesh_code = mesh.get('code')
                    if mesh_code in recalculated_mesh_codes:
                        mesh_to_pref[mesh_code] = pref_code

        affected_pref_codes = set(mesh_to_pref.values())
        index_time = time.time() - merge_start
        logger.info(f"[Merge] Index build: {index_time:.3f}s, affected prefs: {affected_pref_codes}")

        # Step 2: 影響を受ける府県のみdeepcopy、それ以外は参照
        copy_start = time.time()
        merged_prefectures = {}
        for pref_code, prefecture in base_session['prefectures'].items():
            if pref_code in affected_pref_codes:
                # この府県は変更されるのでdeepcopy
                merged_prefectures[pref_code] = copy.deepcopy(prefecture)
            else:
                # この府県は変更されないので参照（コピーしない）
                merged_prefectures[pref_code] = prefecture
        copy_time = time.time() - copy_start
        logger.info(f"[Merge] Selective deepcopy: {copy_time:.3f}s")

        # 影響を受けたエリアを追跡（再集約の最適化用）
        # キー: (pref_code, area_name), 値: area参照
        affected_areas: Dict[tuple, Any] = {}

        # Step 3: 影響を受けた府県のメッシュのみ更新
        update_start = time.time()
        for pref_code in affected_pref_codes:
            prefecture = merged_prefectures[pref_code]
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
                        mesh['swi_hourly_timeline'] = recalc_data.get(
                            'swi_hourly_timeline', mesh.get('swi_hourly_timeline', []))
                        mesh['rain_timeline'] = recalc_data.get(
                            'rain_timeline', mesh.get('rain_timeline', []))
                        mesh['rain_1hour_timeline'] = recalc_data.get(
                            'rain_1hour_timeline', mesh.get('rain_1hour_timeline', []))
                        mesh['rain_1hour_max_timeline'] = recalc_data.get(
                            'rain_1hour_max_timeline', mesh.get('rain_1hour_max_timeline', []))
                        if 'risk_hourly_timeline' in recalc_data:
                            mesh['risk_hourly_timeline'] = recalc_data['risk_hourly_timeline']

                        # このエリアを影響リストに追加
                        affected_areas[(pref_code, area.get('name'))] = area

        update_time = time.time() - update_start
        logger.info(f"[Merge] Mesh update: {update_time:.3f}s, updated areas: {len(affected_areas)}")

        # メッシュ更新後、影響を受けたエリアのみリスクタイムラインを再集約
        reagg_start = time.time()
        if affected_areas:
            # 影響を受けた府県を特定
            affected_prefs = set(pref_code for pref_code, _ in affected_areas.keys())

            logger.info(
                f"Optimized re-aggregation: {len(affected_areas)} areas in "
                f"{len(affected_prefs)} prefectures (total meshes: {len(recalculated_meshes)})"
            )

            for (pref_code, area_name), area in affected_areas.items():
                # このエリアのリスクタイムラインを再集約
                ft_max_risk = {}
                for mesh in area.get('meshes', []):
                    for risk_point in mesh.get('risk_3hour_max_timeline', []):
                        ft = risk_point['ft']
                        value = risk_point['value']
                        if ft not in ft_max_risk or value > ft_max_risk[ft]:
                            ft_max_risk[ft] = value
                if ft_max_risk:
                    area['risk_timeline'] = [
                        {"ft": ft, "value": ft_max_risk[ft]}
                        for ft in sorted(ft_max_risk.keys())
                    ]

            # 影響を受けた府県のみ二次細分・府県タイムラインを再集約
            for pref_code in affected_prefs:
                prefecture = merged_prefectures[pref_code]

                # この府県で影響を受けたエリア名のセット
                affected_area_names = set(
                    area_name for (pc, area_name) in affected_areas.keys()
                    if pc == pref_code
                )

                # 二次細分別リスクタイムライン再集約（影響を受けたエリアを含む二次細分のみ）
                for subdiv in prefecture.get('secondary_subdivisions', []):
                    subdiv_area_names = set(subdiv.get('area_names', []))
                    # この二次細分が影響を受けたエリアを含むかチェック
                    if subdiv_area_names & affected_area_names:
                        ft_max_risk = {}
                        for area_name in subdiv.get('area_names', []):
                            area = next(
                                (a for a in prefecture['areas'] if a['name'] == area_name), None)
                            if area:
                                for rt in area.get('risk_timeline', []):
                                    ft = rt['ft']
                                    value = rt['value']
                                    if ft not in ft_max_risk or value > ft_max_risk[ft]:
                                        ft_max_risk[ft] = value
                        if ft_max_risk:
                            subdiv['risk_timeline'] = [
                                {"ft": ft, "value": ft_max_risk[ft]}
                                for ft in sorted(ft_max_risk.keys())
                            ]

                # 府県全体リスクタイムライン再集約
                ft_max_risk = {}
                for area in prefecture.get('areas', []):
                    for rt in area.get('risk_timeline', []):
                        ft = rt['ft']
                        value = rt['value']
                        if ft not in ft_max_risk or value > ft_max_risk[ft]:
                            ft_max_risk[ft] = value
                if ft_max_risk:
                    prefecture['prefecture_risk_timeline'] = [
                        {"ft": ft, "value": ft_max_risk[ft]}
                        for ft in sorted(ft_max_risk.keys())
                    ]

        reagg_time = time.time() - reagg_start
        total_time = time.time() - merge_start
        logger.info(f"[Merge] Re-aggregation: {reagg_time:.3f}s, Total merge: {total_time:.3f}s")

        # マージ結果を返す
        return {
            'is_fork': True,
            'base_session_id': base_session_id,
            'prefectures': merged_prefectures,
            'swi_initial_time': fork_session['swi_initial_time'],
            'guidance_initial_time': fork_session['guidance_initial_time'],
            'guidance_type': fork_session.get('guidance_type', base_session.get('guidance_type', 'msm')),
            'risk_rule': fork_session.get('risk_rule', base_session.get('risk_rule', 'legacy')),
            'input_mode': fork_session.get('input_mode', base_session.get('input_mode', '3hour')),
            'adjustment_mode': fork_session.get('adjustment_mode', base_session.get('adjustment_mode', 'ratio_3hour')),
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
                ref_path = self._get_session_ref_path(session_id)
                if ref_path.exists():
                    ref_path.unlink()
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
                ref_path = self._get_session_ref_path(session_id)
                if ref_path.exists():
                    ref_path.unlink()

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
            'guidance_type': session.get('guidance_type', 'msm'),
            'risk_rule': session.get('risk_rule', 'legacy'),
            'input_mode': session.get('input_mode', '3hour'),
            'adjustment_mode': session.get('adjustment_mode', 'ratio_3hour'),
            'prefecture_count': len(session['prefectures']),
            'prefecture_codes': list(session['prefectures'].keys()),
            'prefecture_details': [
                {
                    'code': pref_code,
                    'name': pref_data.get('name', pref_code)
                    if isinstance(pref_data, dict)
                    else getattr(pref_data, 'name', pref_code),
                }
                for pref_code, pref_data in session['prefectures'].items()
            ]
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
