#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
基于 Flask Web 端接口的迭代式测试客户端。

目标：
- 周期性从服务端拉取“未确认关系”，根据服务端返回的 testing_suggestions 自动触发实验
- 持续迭代，直到未确认的集群和点位关系消除或达到迭代上限
- 在每轮结束时输出进度摘要

可用接口（来自 Web 版本服务端）：
- GET  /api/system/info
- GET  /api/clusters
- GET  /api/clusters/unconfirmed_relationships
- GET  /api/relationships/confirmed_non_conductive
- POST /api/experiment
"""

from __future__ import annotations

import argparse
import json
import time
from typing import Any, Dict, List, Optional
import math
import random

import requests
from requests.adapters import HTTPAdapter

DEBUG_MODE = False
# 是否从服务端拉取“已确认不导通”集合。新策略默认不需要。
USE_SERVER_NON_CONDUCTIVE = False


class RelationshipMatrix:
    """稀疏关系矩阵：记录点对的导通状态。
    - 1: 已确认导通
    - -1: 已确认不导通
    - 0: 未知（不存储）
    """

    def __init__(self, total_points: int) -> None:
        self.total_points = int(total_points)
        self._conductive: set[tuple[int, int]] = set()
        self._non_conductive: set[tuple[int, int]] = set()

    @staticmethod
    def _key(a: int, b: int) -> tuple[int, int]:
        return (a, b) if a <= b else (b, a)

    def set_conductive(self, a: int, b: int) -> None:
        if a == b:
            return
        k = self._key(int(a), int(b))
        if k in self._non_conductive:
            self._non_conductive.discard(k)
        self._conductive.add(k)

    def set_non_conductive(self, a: int, b: int) -> None:
        if a == b:
            return
        k = self._key(int(a), int(b))
        if k in self._conductive:
            self._conductive.discard(k)
        self._non_conductive.add(k)

    def get(self, a: int, b: int) -> int:
        if a == b:
            return 1
        k = self._key(int(a), int(b))
        if k in self._conductive:
            return 1
        if k in self._non_conductive:
            return -1
        return 0

    def mark_cluster_conductive(self, points: List[int]) -> None:
        pts = [int(p) for p in (points or [])]
        for i in range(len(pts)):
            for j in range(i + 1, len(pts)):
                self.set_conductive(pts[i], pts[j])

    def mark_point_cluster_non_conductive(self, point: int, cluster_points: List[int]) -> None:
        for q in cluster_points or []:
            self.set_non_conductive(int(point), int(q))

    def mark_cluster_cluster_non_conductive(self, c1: List[int], c2: List[int]) -> None:
        for a in c1 or []:
            for b in c2 or []:
                self.set_non_conductive(int(a), int(b))

    def summarize(self) -> str:
        return f"矩阵汇总: 导通={len(self._conductive)} 对, 不导通={len(self._non_conductive)} 对"

    def conductive_pairs(self) -> List[tuple[int, int]]:
        return list(self._conductive)



class WebApiClient:
    """对 Web 端提供的 API 进行轻量封装。"""

    def __init__(self, base_url: str) -> None:
        self.base_url = base_url.rstrip("/")
        # 持久连接与连接池，避免每次握手导致的延迟
        self.session = requests.Session()
        self.session.headers.update({"Connection": "keep-alive"})
        # 禁用系统代理，避免公司代理/杀软插入导致的慢
        self.session.trust_env = False
        adapter = HTTPAdapter(pool_connections=20, pool_maxsize=100)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

    def _get(self, path: str, timeout: int = 10) -> Dict[str, Any]:
        url = f"{self.base_url}{path}"
        resp = self.session.get(url, timeout=timeout)
        resp.raise_for_status()
        return resp.json()

    def _post(self, path: str, payload: Dict[str, Any], timeout: int = 30) -> Dict[str, Any]:
        url = f"{self.base_url}{path}"
        resp = self.session.post(url, json=payload, timeout=timeout)
        resp.raise_for_status()
        return resp.json()

    def get_system_info(self) -> Dict[str, Any]:
        return self._get("/api/system/info")

    def get_clusters(self) -> Dict[str, Any]:
        return self._get("/api/clusters")

    def get_unconfirmed(self) -> Dict[str, Any]:
        return self._get("/api/clusters/unconfirmed_relationships")

    def get_confirmed_non_conductive(self) -> Dict[str, Any]:
        # 优先使用分页接口一次取全量，兼容老接口
        try:
            return self._get("/api/relationships/confirmed_non_conductive?category=all&page_size=100000")
        except Exception:
            return self._get("/api/relationships/confirmed_non_conductive")

    def get_clusters_detailed(self) -> Dict[str, Any]:
        # 加上时间戳避免缓存
        return self._get(f"/api/clusters/detailed?ts={time.time()}")

    def get_clusters_visualization(self) -> Dict[str, Any]:
        return self._get(f"/api/clusters/visualization?ts={time.time()}")

    def run_experiment(self, power_source: int, test_points: List[int]) -> Dict[str, Any]:
        payload = {"power_source": int(power_source), "test_points": [int(p) for p in test_points]}
        return self._post("/api/experiment", payload)

    def run_batch_experiments(self, test_count: int = 3, max_points_per_test: int = 100) -> Dict[str, Any]:
        payload = {"test_count": int(test_count), "max_points_per_test": int(max_points_per_test)}
        return self._post("/api/experiment/batch", payload)


def select_tests_from_suggestions(
    unconfirmed_data: Dict[str, Any],
    max_tests: int,
    tested_pairs: set[tuple[int, int]] | None = None,
    point_point_ban: set[tuple[int, int]] | None = None,
    confirmed_point_pairs: set[tuple[int, int]] | None = None,
) -> List[Dict[str, Any]]:
    """已废弃：客户端不再依赖服务端建议，保留空实现以兼容旧脚本调用。"""
    return []


def summarize(unconfirmed: Dict[str, Any]) -> str:
    summary = unconfirmed.get("summary", {})
    return (
        f"已确集群: {summary.get('total_confirmed_clusters', 0)} | "
        f"未确点位: {summary.get('total_unconfirmed_points', 0)} | "
        f"未确集群关: {summary.get('total_unconfirmed_cluster_relationships', 0)} | "
        f"未确点位关: {summary.get('total_unconfirmed_point_relationships', 0)} | "
        f"未确点位间: {summary.get('total_unconfirmed_point_to_point_relationships', 0)} | "
        f"建议数: {summary.get('total_testing_suggestions', 0)}"
    )


def estimate_from_clusters(client: WebApiClient) -> Dict[str, int]:
    """当 /unconfirmed 返回异常或为空时，根据集群与系统信息做估计，用于打印参考。"""
    try:
        sys_info = client.get_system_info()
        total_points = int(sys_info.get("total_points", 0))
        clusters = client.get_clusters()
        if clusters.get("success"):
            cl = clusters.get("clusters", [])
            confirmed_points = set()
            for c in cl:
                for p in c.get("points", []):
                    confirmed_points.add(int(p))
            return {
                "confirmed_clusters": clusters.get("total_clusters", len(cl)),
                "unconfirmed_points": max(0, total_points - len(confirmed_points)),
            }
    except Exception:
        pass
    return {"confirmed_clusters": 0, "unconfirmed_points": 0}


def plan_single_pair_tests(
    client: WebApiClient,
    limit: int,
    tested_pairs: set | None = None,
    banned_point_pairs: set[tuple[int, int]] | None = None,
) -> List[Dict[str, Any]]:
    """已废弃：现行算法改为固定电源点 + 本地矩阵过滤。保留空实现以兼容旧脚本调用。"""
    return []

def plan_from_server_state(
    client: WebApiClient,
    max_tests: int,
    tested_pairs: set | None = None,
    banned_point_cluster: set[tuple[int, str]] | None = None,
    banned_cluster_pairs: set[tuple[str, str]] | None = None,
    confirmed_point_cluster: set[tuple[int, str]] | None = None,
    confirmed_point_pairs: set[tuple[int, int]] | None = None,
    rel_matrix: 'RelationshipMatrix' | None = None,
) -> List[Dict[str, Any]]:
    """
    基于服务端当前状态生成测试计划。
    1) 未确认点位 → 各已确认集群代表点
    2) 未确认点位之间单对
    3) 集群代表点之间单对
    """
    plan: List[Dict[str, Any]] = []
    print("尝试从服务器端获取当前状态")
    try:
        det = client.get_clusters_detailed()
        if not det.get("success"):
            return plan
        data = det["data"]
        if DEBUG_MODE:
            print("获取到服务器端状态,", data)
        # 这里已经能够正常获取当前集群和相关点位
        unconfirmed = list(data.get("unconfirmed_points", {}).get("points", []))
        confirmed: List[Dict[str, Any]] = data.get("confirmed_clusters", [])

        # 构造“已确认导通”的过滤集（点-集群、点-点）
        # 
        if confirmed_point_cluster is None or confirmed_point_pairs is None:
            cpc: set[tuple[int, str]] = set()
            cpp: set[tuple[int, int]] = set()
            for c in confirmed:
                cid = str(c.get('cluster_id'))
                pts = c.get('points', []) or []
                for p in pts:
                    cpc.add((int(p), cid))
                # 在同一集群内的点对视为已导通
                for i_idx, a in enumerate(pts):
                    for b in pts[i_idx+1:]:
                        cpp.add((min(int(a), int(b)), max(int(a), int(b))))
            confirmed_point_cluster = cpc if confirmed_point_cluster is None else confirmed_point_cluster
            confirmed_point_pairs = cpp if confirmed_point_pairs is None else confirmed_point_pairs

        # 归纳：若 p 归属 C，且历史认为 p 与 E 不导通 或 p 与集群 D 不导通，
        # 则提升为 C 与 E、C 与 D 不导通（只用于客户端计划过滤）
        try:
            pp_ban, pc_ban, cc_ban = fetch_non_conductive_sets(client)
        except Exception:
            pp_ban, pc_ban, cc_ban = set(), set(), set()

        point_to_cluster_id_local: Dict[int, str] = {}
        for c in confirmed:
            cid = str(c.get('cluster_id'))
            for p in c.get('points', []) or []:
                point_to_cluster_id_local[int(p)] = cid

        derived_pc_ban, derived_cc_ban = derive_bans_from_assignment(
            point_to_cluster_id_local, pp_ban, pc_ban
        )

        # 并入现有禁止集
        before_pc = len(banned_point_cluster or [])
        before_cc = len(banned_cluster_pairs or [])
        banned_point_cluster = (banned_point_cluster or set()) | derived_pc_ban
        banned_cluster_pairs = (banned_cluster_pairs or set()) | derived_cc_ban
        after_pc = len(banned_point_cluster)
        after_cc = len(banned_cluster_pairs)
        added_pc = after_pc - before_pc
        added_cc = after_cc - before_cc
        if added_pc or added_cc:
            print(f"   [对比] 由点归属推导新增禁止：点-集群 {added_pc} 条, 集群-集群 {added_cc} 条")

        # 若尚无任何已确认集群：执行“引导式批量扫描”
        # 选取若干 power_source，每个一次性测试一批候选点，加速发现连接
        if not confirmed:
            if unconfirmed:
                pivots = unconfirmed[:min(20, len(unconfirmed))]
            else:
                pivots = list(range(0, 20))
            for ps in pivots:
                # 选取 batch_size 个不同于 ps 的点位
                candidates = [p for p in (unconfirmed or list(range(0, 1000))) if p != ps]
                if not candidates:
                    continue
                batch = candidates[:min(50, len(candidates))]
                # 过滤已测试的对
                filtered = []
                for x in batch:
                    pair = (min(ps, x), max(ps, x))
                    if rel_matrix and rel_matrix.get(pair[0], pair[1]) != 0:
                        continue
                    if tested_pairs and pair in tested_pairs:
                        continue
                    if confirmed_point_pairs and pair in confirmed_point_pairs:
                        continue
                    filtered.append(int(x))
                    if len(filtered) >= max_tests - len(plan):
                        break
                if not filtered:
                    continue
                plan.append({'power_source': int(ps), 'test_points': filtered})
                if len(plan) >= max_tests:
                    return plan

        # 构建点->集群映射，用于硬禁止
        point_to_cluster_id: Dict[int, str] = {}
        for c in confirmed:
            cid = str(c.get('cluster_id'))
            for p in c.get('points', []) or []:
                point_to_cluster_id[int(p)] = cid

        def _is_hard_banned(a: int, b: int) -> bool:
            # 已确认导通：同一集群
            ca = point_to_cluster_id.get(int(a))
            cb = point_to_cluster_id.get(int(b))
            if ca is not None and cb is not None:
                if ca == cb:
                    return True  # 同集群，必导通，禁止
                else:
                    return True  # 异集群，必不导通，禁止
            # 已确认不导通点对
            if confirmed_point_pairs and (min(a, b), max(a, b)) in confirmed_point_pairs:
                return True
            return False

        # 1) 未确认点位 → 批量对多个已确认集群代表点（信息增益更高）
        # 动态选择批量大小 K：随集群数增长而增大
        if confirmed:
            C = max(1, len(confirmed))
            batch_k = min(20, 3 + int(math.log2(C + 1)))
            for p in unconfirmed:
                if len(plan) >= max_tests:
                    return plan
                candidates: List[int] = []
                for c in confirmed:
                    reps = c.get('points', [])[:1]
                    if not reps:
                        continue
                    rp = int(reps[0])
                    # 若电源候选点 p 尚未归属：允许 p → 已确集群代表点，用于尽快确认 p 的归属
                    sa_local = point_to_cluster_id_local.get(int(p))
                    if _is_hard_banned(p, rp):
                        continue
                    cid = c.get('cluster_id')
                    if banned_point_cluster and cid is not None and (int(p), str(cid)) in banned_point_cluster:
                        continue
                    if confirmed_point_cluster and cid is not None and (int(p), str(cid)) in confirmed_point_cluster:
                        continue
                    pair = (min(p, rp), max(p, rp))
                    if rel_matrix and rel_matrix.get(pair[0], pair[1]) != 0:
                        continue
                    if tested_pairs and pair in tested_pairs:
                        continue
                    if confirmed_point_pairs and pair in confirmed_point_pairs:
                        continue
                    candidates.append(rp)
                if candidates:
                    batch_targets = candidates[:batch_k]
                    plan.append({'power_source': int(p), 'test_points': [int(x) for x in batch_targets]})
                    if len(plan) >= max_tests:
                        return plan

        # 2) 未确认点位之间
        for i, p1 in enumerate(unconfirmed):
            for p2 in unconfirmed[i+1:]:
                if _is_hard_banned(p1, p2):
                    continue
                pair = (min(p1, p2), max(p1, p2))
                if rel_matrix and rel_matrix.get(pair[0], pair[1]) != 0:
                    continue
                if tested_pairs and pair in tested_pairs:
                    continue
                if confirmed_point_pairs and pair in confirmed_point_pairs:
                    continue
                plan.append({'power_source': int(p1), 'test_points': [int(p2)]})
                if len(plan) >= max_tests:
                    return plan

        # 3) 集群代表点之间
        if len(confirmed) > 1:
            for i, c1 in enumerate(confirmed):
                for c2 in confirmed[i+1:]:
                    r1 = c1.get('points', [])[:1]
                    r2 = c2.get('points', [])[:1]
                    if not r1 or not r2:
                        continue
                    # 硬禁止：不同已确认集群之间视为不导通，不再安排代表点测试
                    # 因此直接跳过该类计划
                    continue
    except Exception:
        pass
    return plan

def fetch_non_conductive_sets(client: WebApiClient) -> tuple[set[tuple[int, int]], set[tuple[int, str]], set[tuple[str, str]]]:
    """从服务端获取已确认不导通信息并转换为便于过滤的集合。
    返回：
      - point_point_set: {(min(p1,p2), max(p1,p2)), ...}
      - point_cluster_set: {(point_id, cluster_id), ...}
      - cluster_cluster_set: {(min(id1,id2), max(id1,id2)), ...}
    """
    pp_set: set[tuple[int, int]] = set()
    pc_set: set[tuple[int, str]] = set()
    cc_set: set[tuple[str, str]] = set()
    print("尝试从服务器端获取已确认不导通信息")
    try:
        resp = client.get_confirmed_non_conductive()
        if isinstance(resp, dict) and resp.get('success'):
            data = resp.get('data') or {}
            if DEBUG_MODE:
                print("获取到已确认不导通信息,", data)
            # 兼容两种返回形态：
            # A) 旧接口：直接包含 point_point_non_conductive / point_cluster_non_conductive / cluster_non_conductive_pairs
            # B) 新分页接口(category=all)：data.items.{point_point,point_cluster,cluster_cluster}.items
            if 'items' in data and isinstance(data.get('items'), dict):
                # 分页(all)
                all_items = data.get('items') or {}
                pp_items = ((all_items.get('point_point') or {}).get('items')) or []
                pc_items = ((all_items.get('point_cluster') or {}).get('items')) or []
                cc_items = ((all_items.get('cluster_cluster') or {}).get('items')) or []
            else:
                pp_items = data.get('point_point_non_conductive', []) or []
                pc_items = data.get('point_cluster_non_conductive', []) or []
                cc_items = data.get('cluster_non_conductive_pairs', []) or []

            for item in pp_items:
                p1 = int(item.get('point1'))
                p2 = int(item.get('point2'))
                pp_set.add((min(p1, p2), max(p1, p2)))
            for item in pc_items:
                pid = int(item.get('point_id'))
                cluster = item.get('cluster') or {}
                cid = str(cluster.get('cluster_id'))
                pc_set.add((pid, cid))
            for item in cc_items:
                c1 = item.get('cluster1') or {}
                c2 = item.get('cluster2') or {}
                id1 = str(c1.get('cluster_id'))
                id2 = str(c2.get('cluster_id'))
                cc_set.add(tuple(sorted([id1, id2])))
    except Exception:
        pass
    return pp_set, pc_set, cc_set

def derive_bans_from_assignment(
    point_to_cluster_id: Dict[int, str],
    point_point_ban: set[tuple[int, int]],
    point_cluster_ban: set[tuple[int, str]],
) -> tuple[set[tuple[int, str]], set[tuple[str, str]]]:
    """根据点位已归属的集群信息，推导新增的禁止集合：
    - 若 p∈C 且 (p,E) 不导通 ⇒ (E,C) 点-集群不导通
    - 若 p∈C 且 (p,D) 不导通 ⇒ (C,D) 集群-集群不导通
    返回 (derived_pc_ban, derived_cc_ban)
    """
    derived_pc_ban: set[tuple[int, str]] = set()
    derived_cc_ban: set[tuple[str, str]] = set()
    for p, cid in point_to_cluster_id.items():
        # p 与 E 不导通 → C 与 E 不导通
        for a, b in point_point_ban:
            if a == p:
                derived_pc_ban.add((b, cid))
            elif b == p:
                derived_pc_ban.add((a, cid))
        # p 与集群 D 不导通 → C 与 D 不导通
        for pt, did in point_cluster_ban:
            if pt == p:
                derived_cc_ban.add(tuple(sorted([cid, str(did)])))
    return derived_pc_ban, derived_cc_ban

def run_iterative_testing(
    client: WebApiClient,
    max_rounds: int,
    max_tests_per_round: int,
    sleep_seconds: float,
) -> None:
    """迭代到完成。max_rounds<=0 表示仅在完成条件满足时退出。"""
    did_bootstrap = False
    idle_rounds = 0
    round_idx = 1
    # 记录已测试的无序点对，防止重复测试 A↔B 与 B↔A
    tested_pairs: set[tuple[int, int]] = set()
    # 初始化关系矩阵
    try:
        sysinfo0 = client.get_system_info()
        total_points0 = int(sysinfo0.get("total_points", 100))
    except Exception:
        total_points0 = 100
    rel_matrix = RelationshipMatrix(total_points0)
    # 顺序电源点策略：从 0 开始，逐次递增
    current_power_source = 0
    processed_clusters: set[str] = set()
    def _is_source_done(src: int) -> bool:
        try:
            for q in range(total_points0):
                if q == src:
                    continue
                if rel_matrix.get(src, q) == 0:
                    return False
            return True
        except Exception:
            return False
    while True:
        round_start_ts = time.perf_counter()
        round_times = {
            "fetch_unconfirmed": 0.0,
            "fetch_clusters_detailed": 0.0,
            "update_matrix": 0.0,
            "fetch_non_conductive": 0.0,
            "plan_generation": 0.0,
            "preflight_checks": 0.0,
            "experiment_calls": 0.0,
            "post_unconfirmed": 0.0,
            "sleep": 0.0,
        }
        # 这里是直接获取未确认导通点
        _ts = time.perf_counter()
        unconfirmed_resp = client.get_unconfirmed()
        round_times["fetch_unconfirmed"] += time.perf_counter() - _ts
        if DEBUG_MODE:
            print("未确认导通点信息为", unconfirmed_resp)
        print(f"\n=== 第 {round_idx} 轮 ===")
        if isinstance(unconfirmed_resp, dict) and unconfirmed_resp.get('success'):
            unconfirmed_data = unconfirmed_resp.get("data", {})
            print("进度:", summarize(unconfirmed_data))
            # 对比打印：从 /unconfirmed 与 /detailed 双来源核对“已确认集群数/未确认点位数”
            try:
                s = (unconfirmed_data.get("summary") or {})
                s_confirmed = int(s.get("total_confirmed_clusters", 0))
                s_unconf_pts = int(s.get("total_unconfirmed_points", 0))
            except Exception:
                s_confirmed, s_unconf_pts = -1, -1
            try:
                det = client.get_clusters_detailed()
                if det.get("success"):
                    dd = det.get("data") or {}
                    d_confirmed = len(dd.get("confirmed_clusters", []) or [])
                    d_unconf_pts = len((dd.get("unconfirmed_points", {}) or {}).get("points", []) or [])
                    print(f"   [对比] 未确认接口: 已确集群={s_confirmed}, 未确点位={s_unconf_pts} | 详细接口: 已确集群={d_confirmed}, 未确点位={d_unconf_pts}")
                else:
                    print(f"   [对比] 详细接口异常: {det}")
            except Exception as e:
                print(f"   [对比] 获取详细接口异常: {e}")
        else:
            print("进度: 暂无（未确认接口返回异常）")
            unconfirmed_data = {}

        # 每轮开始强制刷新一次集群详细状态（用于打印与后续过滤基础）
        # 先初始化本轮所需的映射与集合
        point_to_cluster: Dict[int, str] = {}
        cluster_to_points: Dict[str, List[int]] = {}
        confirmed_points_global: set[int] = set()
        confirmed_point_pairs: set[tuple[int, int]] = set()
        try:
            _ts = time.perf_counter()
            det_round = client.get_clusters_detailed()
            round_times["fetch_clusters_detailed"] += time.perf_counter() - _ts
            if det_round.get("success"):
                dd = det_round.get("data") or {}
                d_confirmed = len(dd.get("confirmed_clusters", []) or [])
                d_unconf_pts = len((dd.get("unconfirmed_points", {}) or {}).get("points", []) or [])
                print(f"本轮起始集群: 已确集群={d_confirmed}, 未确点位={d_unconf_pts}")
                # 基于快照构建映射与本地矩阵导通（集群内两两导通），并推导已确认点对
                _proc_ts = time.perf_counter()
                for c in dd.get('confirmed_clusters', []) or []:
                    cid = str(c.get('cluster_id'))
                    pts = [int(x) for x in (c.get('points', []) or [])]
                    if not pts:
                        continue
                    cluster_to_points[cid] = pts
                    # 集群内两两导通
                    rel_matrix.mark_cluster_conductive(pts)
                    for p in pts:
                        point_to_cluster[int(p)] = cid
                        confirmed_points_global.add(int(p))
                    for i_idx, a in enumerate(pts):
                        for b in pts[i_idx+1:]:
                            confirmed_point_pairs.add((min(int(a), int(b)), max(int(a), int(b))))
                round_times["update_matrix"] += time.perf_counter() - _proc_ts
        except Exception:
            pass

        # 获取“不导通”集合（可选）。默认关闭：不再依赖后端不导通集合。
        if USE_SERVER_NON_CONDUCTIVE:
            _ts = time.perf_counter()
            point_point_ban, point_cluster_ban, cluster_cluster_ban = fetch_non_conductive_sets(client)
            round_times["fetch_non_conductive"] += time.perf_counter() - _ts
            for a, b in point_point_ban:
                rel_matrix.set_non_conductive(int(a), int(b))
        else:
            point_point_ban, point_cluster_ban, cluster_cluster_ban = set(), set(), set()

        # 注：已使用本轮快照构建 point_to_cluster / cluster_to_points / confirmed_points_global

        # 若当前固定电源点已归属某已确认集群，则直接跳过该点（该集群已知，无需再测该点作为电源）
        try:
            cur_cid = point_to_cluster.get(int(current_power_source))
        except Exception:
            cur_cid = None
        if cur_cid is not None:
            processed_clusters.add(str(cur_cid))
            current_power_source += 1
            # 立即进入下一轮，避免继续在本轮针对已确认集群的点生成用例
            time.sleep(max(sleep_seconds, 0.0))
            round_idx += 1
            if max_rounds > 0 and round_idx > max_rounds:
                print("\n结束：达到迭代上限（仍可能未完全探明）。")
                break
            continue

        # 构造“已确认导通”的过滤集已在快照处理时生成为 confirmed_point_pairs

        # 客户端不再依赖服务端 suggestions，仅使用本地规划
        suggestions: List[Dict[str, Any]] = []
        if not suggestions:
            # 在“固定电源点”策略下，不再进行随机批量引导，直接围绕当前电源点生成目标
            if not did_bootstrap:
                did_bootstrap = True
            # 非首轮仍无建议：改为“单点对”探索，更有助于确认 one-to-one
            idle_rounds += 1
            # 策略：固定电源点，从 0 开始顺序递增；未完成前不更换
            if current_power_source >= total_points0:
                print("所有电源点已完成关系确认")
                return
            # 若当前电源点已确认完与其他所有点关系，则递增到下一点
            if _is_source_done(current_power_source):
                scid_done = point_to_cluster.get(int(current_power_source))
                if scid_done:
                    processed_clusters.add(str(scid_done))
                current_power_source += 1
                if current_power_source >= total_points0:
                    print("所有电源点已完成关系确认")
                    return
            static_power: Optional[int] = current_power_source

            _plan_ts = time.perf_counter()
            single_tests = plan_from_server_state(
                client,
                max_tests_per_round,
                tested_pairs=tested_pairs,
                banned_point_cluster=point_cluster_ban,
                banned_cluster_pairs=cluster_cluster_ban,
                confirmed_point_cluster=None,
                confirmed_point_pairs=confirmed_point_pairs,
                rel_matrix=rel_matrix,
            )
            # 若生成了多电源的计划，则将其重写为同一电源 static_power 的批量测试
            # 构造针对 static_power 的目标集合：选择其与之“未知关系”的点位
            if static_power is not None:
                # 若当前电源点已与任一其他点被确认导通，则视为其已归属某集群，直接跳过该电源点
                try:
                    if any(rel_matrix.get(static_power, q) == 1 for q in range(total_points0) if q != static_power):
                        current_power_source += 1
                        continue
                except Exception:
                    pass
                targets: List[int] = []
                # 若当前电源点已归属某已确认集群，则直接推进到下一电源点（该点不再作为电源测试）
                sa = point_to_cluster.get(int(static_power))
                # 若电源点已归属，或电源点就在全局已确认点集合中，直接跳过该电源点
                if sa is not None or int(static_power) in confirmed_points_global:
                    if DEBUG_MODE:
                        print(f"电源点 {static_power} 已归属({sa}) 或在已确认集合中，跳过该电源点")
                    current_power_source += 1
                    continue
                for t in range(total_points0):
                    if t == static_power:
                        continue
                    # 强化：若电源点尚未归属，则全局跳过所有已归属点
                    if sa is None and t in confirmed_points_global:
                        if DEBUG_MODE:
                            print(f"  目标点 {t} 已归属，且电源点未归属 -> 跳过")
                        continue
                    # 进一步强化：即便服务端尚未归档到集群，只要目标点在本地矩阵与任意点导通，也视为已归属，跳过
                    if sa is None:
                        try:
                            if any(rel_matrix.get(t, u) == 1 for u in range(total_points0) if u != t):
                                if DEBUG_MODE:
                                    print(f"  目标点 {t} 在本地矩阵已有导通证据 -> 跳过")
                                continue
                        except Exception:
                            pass
                    # 若目标点属于已处理完的集群，则跳过
                    tcid0 = point_to_cluster.get(int(t))
                    if tcid0 and str(tcid0) in processed_clusters:
                        continue
                    # 已确认集群规则：
                    # - 若电源点与目标点均已归属某已确认集群，则无需再测（同集群必导通，异集群必不导通）
                    # - 若电源点尚未归属，而目标点已归属某已确认集群，优先跳过，先在未确认点集合中确认其归属
                    sb = point_to_cluster.get(int(t))
                    if sa is not None and sb is not None:
                        if DEBUG_MODE:
                            print(f"  电源点与目标点均已归属({sa},{sb}) -> 跳过")
                        continue
                    if sa is None and sb is not None:
                        # 电源点未归属，目标点已归属：先不测，避免出现 1↔7 这类已知集群的重复判定
                        if DEBUG_MODE:
                            print(f"  目标点 {t} 已归属 {sb}，电源点未归属 -> 跳过")
                        continue
                    if rel_matrix.get(static_power, t) != 0:
                        continue
                    # 跳过由服务端已确认/推导的不导通（点-点 / 点-集群 / 集群-集群）
                    pair_pp = (min(static_power, t), max(static_power, t))
                    if pair_pp in point_point_ban:
                        if DEBUG_MODE:
                            print(f"  {pair_pp} 在 point_point_ban 中 -> 跳过")
                        continue
                    tcid = point_to_cluster.get(int(t))
                    if tcid and (static_power, str(tcid)) in point_cluster_ban:
                        if DEBUG_MODE:
                            print(f"  ({static_power}, {tcid}) 在 point_cluster_ban 中 -> 跳过")
                        continue
                    scid = point_to_cluster.get(int(static_power))
                    if scid and tcid and tuple(sorted([str(scid), str(tcid)])) in cluster_cluster_ban:
                        if DEBUG_MODE:
                            print(f"  集群对 ({scid},{tcid}) 在 cluster_cluster_ban 中 -> 跳过")
                        continue
                    # 进一步基于矩阵/服务端推断：若 static_power 与目标所属集群任一成员已知不导通，则整个集群可判为不导通
                    if tcid and any(rel_matrix.get(static_power, int(u)) == -1 for u in cluster_to_points.get(str(tcid), [])):
                        continue
                    if tcid and any((min(static_power, int(u)), max(static_power, int(u))) in point_point_ban for u in cluster_to_points.get(str(tcid), [])):
                        continue
                    # 若 static_power 已与某点导通，则其所属集群已知；同集群中其他点都不需要再测
                    if sa is not None and tcid0 is not None and str(sa) == str(tcid0):
                        continue
                    pair = (min(static_power, t), max(static_power, t))
                    if pair in tested_pairs:
                        continue
                    targets.append(int(t))
                    if len(targets) >= max_tests_per_round:
                        break
                if targets:
                    # 将批量目标拆成多个“单对判断”用例，逐个提交，避免同测歧义
                    single_tests = [
                        {'power_source': static_power, 'test_points': [int(t)]}
                        for t in targets[:max_tests_per_round]
                    ]
                else:
                    single_tests = []
            round_times["plan_generation"] += time.perf_counter() - _plan_ts
            if not single_tests:
                # 当前电源点暂时没有可测目标，推进到下一个电源点
                current_power_source += 1
                continue
            # 这里需要震度已有的电源点位进行确认
            print(f"固定电源点 {static_power}，本轮批量目标 {len(single_tests[0]['test_points'])} 个 (idle_rounds={idle_rounds}) ...")
            for i, cfg in enumerate(single_tests, 1):
                ps = cfg["power_source"]
                pts = cfg["test_points"]
                # 更新已测试对
                for t in pts:
                    pair = (min(ps, t), max(ps, t))
                    # 若已确认不导通，则不再提交该测试
                    # 这里是已经确认不导通的点对，需要跳过
                    if pair in point_point_ban:
                        continue
                    tested_pairs.add(pair)
                # 运行前最后一道防线：基于最新集群/不导通信息再做一次（多次）跳过判断
                try:
                    attempts = 1
                    should_skip = False
                    while attempts > 0:
                        _chk_ts = time.perf_counter()
                        det_now = client.get_clusters_detailed()
                        round_times["preflight_checks"] += time.perf_counter() - _chk_ts
                        ptc_now: Dict[int, str] = {}
                        if det_now.get('success'):
                            for c in det_now['data'].get('confirmed_clusters', []) or []:
                                cid = str(c.get('cluster_id'))
                                for p in c.get('points', []) or []:
                                    ptc_now[int(p)] = cid
                        # 强制固定电源点：只允许 current_power_source 作为电源
                        if ps != current_power_source:
                            should_skip = True
                            break
                        tmp_skip = False
                        for t in pts:
                            sa = ptc_now.get(int(ps))
                            sb = ptc_now.get(int(t))
                            # 若双方都已归属任一已确认集群，则无需再测
                            if sa is not None and sb is not None:
                                tmp_skip = True
                                break
                            # 若电源点未归属而目标已归属，也跳过，避免已知集群的重复判定
                            if sa is None and sb is not None:
                                tmp_skip = True
                                break
                            # 本地矩阵兜底：若电源未归属，且目标在本地矩阵与任一点导通，则跳过
                            if sa is None:
                                try:
                                    if any(rel_matrix.get(int(t), u) == 1 for u in range(total_points0) if u != int(t)):
                                        tmp_skip = True
                                        break
                                except Exception:
                                    pass
                            # 若电源点与目标所属集群已有任意成员被确认不导通，亦跳过
                            if (min(ps, t), max(ps, t)) in point_point_ban:
                                tmp_skip = True
                                break
                        if tmp_skip:
                            should_skip = True
                            break
                        # 仅一次预检，不再等待重试
                        attempts -= 1
                    if should_skip:
                        continue
                except Exception:
                    pass

                _exp_ts = time.perf_counter()
                r = client.run_experiment(ps, pts)
                round_times["experiment_calls"] += time.perf_counter() - _exp_ts
                if r.get("success"):
                    tr = r.get("test_result") or r.get("data") or {}
                    print(
                        f"  ✓ 单对测试 {i}/{len(single_tests)} 电源{ps}→点位{pts[0]}, 耗时{tr.get('duration', tr.get('test_duration', 0)):.3f}s, 继电器{tr.get('relay_operations', 0)}"
                    )
                    # 同步导通证据到矩阵，并进行基于集群的推导
                    try:
                        # 兼容 web 与 api 两种返回结构
                        conns = tr.get("detected_connections")
                        if not conns:
                            conns = tr.get("connections")
                        for conn in (conns or []):
                          
                            src = int(conn.get("source_point") or conn.get("source") or conn.get("power_source") or ps)
                            tgts_raw = conn.get("target_points") or conn.get("targets") or []
                            tgts = [int(x) for x in (tgts_raw or [])]
                            for tgt in tgts:
                                rel_matrix.set_conductive(src, tgt)
                                # 传播：src 所在集群的所有点 与 tgt 导通
                                scid = point_to_cluster.get(src)
                                if scid and scid in cluster_to_points:
                                    for sp in cluster_to_points[scid]:
                                        rel_matrix.set_conductive(sp, tgt)
                                # 传播：tgt 所在集群的所有点 与 src 导通
                                tcid = point_to_cluster.get(tgt)
                                if tcid and tcid in cluster_to_points:
                                    for tp in cluster_to_points[tcid]:
                                        rel_matrix.set_conductive(src, tp)
                                # 若双方均有集群：全对导通
                                if scid and tcid and scid in cluster_to_points and tcid in cluster_to_points:
                                    for sp in cluster_to_points[scid]:
                                        for tp in cluster_to_points[tcid]:
                                            rel_matrix.set_conductive(sp, tp)
                    except Exception:
                        pass
                    # 打印一次试验后的集群点位信息，便于观察收敛进度
                    # 按你的要求：不再在单次试验后获取/打印集群信息。
                    pass
                else:
                    print(f"  ✗ 单对测试 {i}/{len(single_tests)} 失败:", r.get("error"))

            # 不再因为无建议而提前终止；但在本分支也做一次收敛判定
            _ts = time.perf_counter()
            post = client.get_unconfirmed()
            round_times["post_unconfirmed"] += time.perf_counter() - _ts
            if isinstance(post, dict) and post.get("success"):
                s = (post.get("data") or {}).get("summary") or {}
                if (
                    s.get("total_unconfirmed_points", 1) == 0
                    and s.get("total_unconfirmed_cluster_relationships", 1) == 0
                    and s.get("total_unconfirmed_point_relationships", 1) == 0
                    and s.get("total_unconfirmed_point_to_point_relationships", 1) == 0
                ):
                    print("\n🎉 完成：所有点位已归属集群，且所有集群/点位间关系均已探明。")
                    print("—— 客户端确认：拓扑已完成 ——")
                    return

            # 矩阵小结
            try:
                print(rel_matrix.summarize())
            except Exception:
                pass
            # 继续下一轮（受 max_rounds 控制）。默认无等待，避免空耗。
            if sleep_seconds > 0:
                _sl_ts = time.perf_counter()
                time.sleep(sleep_seconds)
                round_times["sleep"] += time.perf_counter() - _sl_ts
            # 输出本轮步骤耗时
            try:
                round_total = time.perf_counter() - round_start_ts
                print(
                    "步骤耗时: "
                    f"未确认={round_times['fetch_unconfirmed']:.3f}s, "
                    f"集群详细={round_times['fetch_clusters_detailed']:.3f}s, "
                    f"矩阵更新={round_times['update_matrix']:.3f}s, "
                    f"不导通={round_times['fetch_non_conductive']:.3f}s, "
                    f"规划={round_times['plan_generation']:.3f}s, "
                    f"预检={round_times['preflight_checks']:.3f}s, "
                    f"提交试验={round_times['experiment_calls']:.3f}s, "
                    f"轮后检查={round_times['post_unconfirmed']:.3f}s, "
                    f"休眠={round_times['sleep']:.3f}s, "
                    f"总计={round_total:.3f}s"
                )
            except Exception:
                pass
            round_idx += 1
            if max_rounds > 0 and round_idx > max_rounds:
                print("\n结束：达到迭代上限（仍可能未完全探明）。")
                break
            continue

        # 省略旧的“建议分支”路径与重复的轮后检查/打印逻辑


def main() -> None:
    parser = argparse.ArgumentParser(description="迭代式 Web API 测试客户端")
    parser.add_argument("--server", default="http://localhost:5000", help="服务器基地址")
    parser.add_argument("--rounds", type=int, default=0, help="最大测试轮数（0 表示直到完成）")
    parser.add_argument("--per-round", type=int, default=200, help="每轮最多执行的测试数（默认自适应上限 200）")
    parser.add_argument("--sleep", type=float, default=0.0, help="每轮结束后的等待秒数（默认0，结果返回即下一轮）")
    args = parser.parse_args()

    client = WebApiClient(args.server)

    try:
        sys_info = client.get_system_info()
        if sys_info.get("success"):
            d = sys_info
            print(
                f"连接成功: 总点位 {d.get('total_points')}, "
                f"继电器切换 {d.get('relay_switch_time')}s"
            )
        else:
            print("系统信息返回异常: ", sys_info)
    except Exception as e:
        print("无法连接到服务端: ", e)
        return

    run_iterative_testing(
        client=client,
        max_rounds=args.rounds,
        max_tests_per_round=args.per_round,
        sleep_seconds=args.sleep,
    )


if __name__ == "__main__":
    main()

