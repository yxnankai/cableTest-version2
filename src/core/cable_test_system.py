#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
线缆测试系统 - 基于README实验说明的测试程序接口
主要功能：模拟线缆导通测试，随机生成测试数据，模拟继电器控制
"""

import random
import time
import json
from typing import List, Dict, Set, Tuple, Optional
from dataclasses import dataclass
from enum import Enum
import logging

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class RelayState(Enum):
    """继电器状态枚举"""
    OFF = 0  # 关闭
    ON = 1   # 开启

@dataclass
class TestPoint:
    """测试点位信息"""
    point_id: int
    relay_state: RelayState = RelayState.OFF
    voltage: float = 0.0
    current: float = 0.0
    is_connected: bool = False

@dataclass
class Connection:
    """连接关系"""
    source_point: int
    target_points: List[int]
    connection_type: str  # "one_to_one" 或 "one_to_many"

@dataclass
class TestResult:
    """测试结果"""
    test_id: str
    timestamp: float
    power_source: int
    active_points: List[int]
    detected_connections: List[Connection]
    test_duration: float
    relay_operations: int
    power_on_operations: int
    total_points: int

class CableTestSystem:
    """
    线缆测试系统（已取消集群/传递性推断）
    目标：仅测量并记录各点位之间的两两导通关系，不进行任何依赖性或传递性归纳。
    """
    
    def __init__(self, total_points: int = 100, relay_switch_time: float = 0.003,
                 min_cluster_size: int = 2, max_cluster_size: int = 5):
        """
        初始化测试系统
        
        Args:
            total_points: 总测试点位数量
            relay_switch_time: 继电器切换时间（秒）
        """
        self.total_points = total_points
        self.relay_switch_time = relay_switch_time
        self.test_points = {}
        # 历史"检测到的连接"（随测试产生）
        self.connections = []
        # 真实的点-点导通关系（对称/无向，不公开为"集群"）
        # 以(min(a,b), max(a,b))的二元组形式存储
        self.true_pairs: Set[Tuple[int, int]] = set()
        self.test_history = []
        self.relay_operation_count = 0  # 继电器操作总次数
        self.power_on_count = 0         # 通电（ON切换）总次数
        
        # N*N矩阵记录所有点位之间的导通关系
        # -1: 不导通, 0: 未知, 1: 导通
        self.relationship_matrix = [[0 for _ in range(total_points)] for _ in range(total_points)]
        
        # 真实关系矩阵（基于true_pairs生成）
        self.true_relationship_matrix = [[0 for _ in range(total_points)] for _ in range(total_points)]
        
        # 确保对角线始终为1（点位与自身的关系）
        for i in range(total_points):
            self.relationship_matrix[i][i] = 1
            self.true_relationship_matrix[i][i] = 1
        
        # 兼容旧参数，但不再以"集群大小"生成；仅保留配置占位（无实际含义）
        try:
            m1 = int(min_cluster_size)
            m2 = int(max_cluster_size)
        except Exception:
            m1, m2 = 2, 5
        if m1 < 2:
            m1 = 2
        if m2 < m1:
            m2 = m1
        self.min_cluster_size = m1
        self.max_cluster_size = m2

        self._initialize_test_points()
        self._generate_random_connections()
        
        logger.info(f"已初始化 {total_points} 个测试点位")
        logger.info(f"已生成 {len(self.connections)} 个连接关系")
        logger.info(f"测试系统初始化完成，总点位: {total_points}")
    
    def _initialize_test_points(self):
        """初始化所有测试点位"""
        for i in range(self.total_points):
            self.test_points[i] = TestPoint(point_id=i)
        logger.info(f"已初始化 {self.total_points} 个测试点位")
    
    def _generate_random_connections(self):
        """生成随机连接关系"""
        logger.info("开始生成随机连接关系")
        
        # 清空现有连接
        self.true_pairs.clear()
        
        # 新的精细化连接生成逻辑
        # 设置不同导通数量的点位分布
        conductivity_distribution = {
            1: 50,  # 与1个点导通的点有50个
            2: 30,  # 与2个点导通的点有30个
            3: 20,  # 与3个点导通的点有20个
            4: 0    # 与4个点导通的点有0个（因为50+30+20=100）
        }
        
        # 验证总数是否匹配
        total_points_from_distribution = sum(conductivity_distribution.values())
        if total_points_from_distribution != self.total_points:
            logger.warning(f"导通分布总数({total_points_from_distribution})与总点数({self.total_points})不匹配，将自动调整")
            # 自动调整分布
            if total_points_from_distribution > self.total_points:
                # 如果分布总数过多，减少高导通数量的点位
                excess = total_points_from_distribution - self.total_points
                for i in range(4, 0, -1):
                    if conductivity_distribution[i] >= excess:
                        conductivity_distribution[i] -= excess
                        break
                    else:
                        excess -= conductivity_distribution[i]
                        conductivity_distribution[i] = 0
            else:
                # 如果分布总数过少，增加低导通数量的点位
                shortage = self.total_points - total_points_from_distribution
                conductivity_distribution[1] += shortage
        
        logger.info(f"调整后的导通分布: {conductivity_distribution}")
        
        # 为每个点位分配导通数量
        point_conductivity_counts = {}
        
        # 首先处理高导通数量的点位
        for conductivity_count in range(4, 0, -1):
            num_points_needed = conductivity_distribution[conductivity_count]
            if num_points_needed <= 0:
                continue
                
            # 随机选择需要这个导通数量的点位
            available_points = [i for i in range(self.total_points) if i not in point_conductivity_counts]
            if len(available_points) < num_points_needed:
                logger.warning(f"可用点位不足，需要{num_points_needed}个，但只有{len(available_points)}个可用")
                num_points_needed = len(available_points)
            
            selected_points = random.sample(available_points, num_points_needed)
            
            for point_id in selected_points:
                point_conductivity_counts[point_id] = conductivity_count
                logger.debug(f"点位 {point_id} 设置为导通 {conductivity_count} 个点位")
        
        # 生成具体的连接关系
        # 每个点位的导通关系是独立的，不需要双向一致性
        # 简单直接的随机选择策略
        
        for point_id, target_conductivity_count in point_conductivity_counts.items():
            # 为当前点位选择目标导通点位（不包括自己）
            available_targets = [i for i in range(self.total_points) if i != point_id]
            
            # 确保不超过设定的导通数量
            actual_connections = min(target_conductivity_count, len(available_targets))
            
            if actual_connections > 0:
                # 随机选择目标点位（完全随机，不考虑冲突）
                target_points = random.sample(available_targets, actual_connections)
                
                # 创建单向连接关系（A->B不代表B->A）
                for target_point in target_points:
                    # 创建从point_id到target_point的连接
                    self.true_relationship_matrix[point_id][target_point] = 1
                    logger.debug(f"创建连接: 点位 {point_id} -> 点位 {target_point}")
        
        # 确保对角线为1，其他未设置的位置为-1
        for i in range(self.total_points):
            for j in range(self.total_points):
                if i == j:
                    self.true_relationship_matrix[i][j] = 1  # 对角线始终为1
                elif self.true_relationship_matrix[i][j] != 1:
                    # 如果还没有设置为导通，则设置为不导通
                    self.true_relationship_matrix[i][j] = -1
        
        logger.info(f"连接关系生成完成")
        logger.info(f"实际导通分布统计（除自己外的导通数量）:")
        
        # 统计实际的导通分布
        actual_distribution = {}
        for i in range(self.total_points):
            count = 0
            for j in range(self.total_points):
                if i != j and self.true_relationship_matrix[i][j] == 1:
                    count += 1
            actual_distribution[count] = actual_distribution.get(count, 0) + 1
        
        for count in sorted(actual_distribution.keys()):
            logger.info(f"  除自己外导通{count}个点位的点: {actual_distribution[count]}个")
        
        # 额外统计信息
        total_connections = sum(actual_distribution.values())
        logger.info(f"  总连接数: {total_connections}")
        
        # 统计作为目标的被选择次数分布
        target_selection_count = {}
        for j in range(self.total_points):
            count = 0
            for i in range(self.total_points):
                if i != j and self.true_relationship_matrix[i][j] == 1:
                    count += 1
            target_selection_count[count] = target_selection_count.get(count, 0) + 1
        
        logger.info(f"  作为目标被选择的次数分布:")
        for count in sorted(target_selection_count.keys()):
            logger.info(f"    被{count}个点位选择的点: {target_selection_count[count]}个")
    
    def _check_real_connection(self, power_source: int, test_point: int) -> bool:
        """
        检查两个点位之间是否存在真实的导通关系
        
        Args:
            power_source: 电源点位ID
            test_point: 测试点位ID
            
        Returns:
            bool: 是否存在导通关系
        """
        # 直接使用真实关系矩阵检查导通关系
        return self.true_relationship_matrix[power_source][test_point] == 1
    
    def _simulate_relay_operation(self, point_id: int, target_state: RelayState) -> bool:
        """
        模拟继电器操作
        
        Args:
            point_id: 点位ID
            target_state: 目标状态
            
        Returns:
            bool: 操作是否成功
        """
        if point_id not in self.test_points:
            logger.error(f"点位 {point_id} 不存在")
            return False
        
        current_state = self.test_points[point_id].relay_state
        
        if current_state != target_state:
            # 模拟继电器开关时间
            time.sleep(self.relay_switch_time)
            self.test_points[point_id].relay_state = target_state
            self.relay_operation_count += 1
            # 若由 OFF -> ON 视为一次“通电”操作
            if current_state == RelayState.OFF and target_state == RelayState.ON:
                self.power_on_count += 1
            logger.debug(f"点位 {point_id} 继电器状态从 {current_state} 切换到 {target_state}")
            return True
        
        return False
    
    def _detect_connections(self, power_source: int, active_points: List[int]) -> List[Connection]:
        """
        检测导通连接关系
        
        Args:
            power_source: 电源输入点位
            active_points: 当前激活的点位列表
            
        Returns:
            List[Connection]: 检测到的连接关系
        """
        detected_connections: List[Connection] = []

        # 直接使用真实关系矩阵检查导通关系
        connected_targets: List[int] = []
        for t in active_points:
            if t == power_source:
                continue
            # 检查power_source到t的导通关系
            if self.true_relationship_matrix[power_source][t] == 1:
                connected_targets.append(t)

        if connected_targets:
            detected_connections.append(Connection(
                source_point=power_source,
                target_points=connected_targets,
                connection_type="one_to_many" if len(connected_targets) > 1 else "one_to_one"
            ))

        return detected_connections

    def _update_relationship_matrix(self, power_source: int, active_points: List[int], detected_connections: List[Connection]):
        """
        更新关系矩阵
        
        Args:
            power_source: 通电点位ID
            active_points: 激活的点位列表
            detected_connections: 检测到的连接关系
        """
        logger.info(f"更新关系矩阵: 通电点位={power_source}, 激活点位={active_points}")
        
        # 对于多对多测试，我们无法确定具体的导通关系
        # 只能知道是否存在导通关系，但不能确定具体是哪个点位导通
        
        if len(active_points) > 2:  # 多对多测试（1个电源点位 + 多个测试点位）
            logger.info(f"多对多测试：点位 {power_source} 作为通电点位，测试点位 {len(active_points)-1} 个")
            
            # 检查是否存在导通关系
            has_conductive_relationship = len(detected_connections) > 0
            
            if has_conductive_relationship:
                logger.info(f"多对多测试发现导通关系，但无法确定具体点位，保持关系矩阵为未知状态")
                # 不更新关系矩阵，保持为0（未知）
            else:
                logger.info(f"多对多测试未发现导通关系，将所有测试点位标记为不导通")
                # 当没有检测到导通关系时，将所有测试点位标记为不导通
                for test_point in active_points:
                    if test_point != power_source:  # 排除电源点位
                        self.relationship_matrix[power_source][test_point] = -1
                        logger.info(f"多对多测试标记不导通：E[{power_source},{test_point}] = -1")
                
        else:  # 1对1测试（1个电源点位 + 1个测试点位）
            test_point = active_points[1] if len(active_points) > 1 else None
            if test_point is not None:
                logger.info(f"1对1测试：点位 {power_source} 与点位 {test_point}")
                
                # 检查是否存在导通关系
                has_conductive_relationship = len(detected_connections) > 0
                
                if has_conductive_relationship:
                    # 确认导通
                    self.relationship_matrix[power_source][test_point] = 1
                    logger.info(f"1对1测试确认导通：E[{power_source},{test_point}] = 1")
                else:
                    # 确认不导通
                    self.relationship_matrix[power_source][test_point] = -1
                    logger.info(f"1对1测试确认不导通：E[{power_source},{test_point}] = -1")
        
        logger.info(f"关系矩阵更新完成")

    def run_single_test(self, power_source: int, test_points: List[int]) -> TestResult:
        """
        运行单次测试
        
        Args:
            power_source: 电源点位ID
            test_points: 要测试的点位ID列表
            
        Returns:
            TestResult: 测试结果
        """
        if power_source not in self.test_points:
            raise ValueError(f"电源点位 {power_source} 不存在")
        
        # 验证测试点位
        for point_id in test_points:
            if point_id not in self.test_points:
                raise ValueError(f"测试点位 {point_id} 不存在")
            if point_id == power_source:
                raise ValueError(f"测试点位不能与电源点位相同: {point_id}")
        
        test_id = f"test_{int(time.time())}_{random.randint(1000, 9999)}"
        start_time = time.time()
        
        logger.info(f"开始测试 {test_id}，电源点位: {power_source}，测试点位: {test_points}")
        
        # 记录继电器操作次数
        relay_operations = 0
        power_on_operations = 0
        
        try:
            # 收集本次测试需要激活的点位（包括电源点位和测试点位）
            points_to_activate = [power_source] + test_points
            
            # 找出当前需要关闭的点位（之前开启但现在不需要的）
            points_to_close = []
            for point_id in self.test_points:
                if (point_id not in points_to_activate and 
                    self.test_points[point_id].relay_state == RelayState.ON):
                    points_to_close.append(point_id)
            
            # 先关闭不需要的点位
            for point_id in points_to_close:
                if self._simulate_relay_operation(point_id, RelayState.OFF):
                    relay_operations += 1
                self.test_points[point_id].relay_state = RelayState.OFF
                self.test_points[point_id].voltage = 0.0
                self.test_points[point_id].current = 0.0
                self.test_points[point_id].is_connected = False
                logger.debug(f"关闭点位 {point_id}")
            
            # 激活本次测试需要的点位
            for point_id in points_to_activate:
                if point_id < self.total_points:
                    point = self.test_points[point_id]
                    if point.relay_state == RelayState.OFF:
                        # 只有当前关闭的点位才需要开启操作
                        if self._simulate_relay_operation(point_id, RelayState.ON):
                            relay_operations += 1
                        point.relay_state = RelayState.ON
                        point.voltage = 5.0 if point_id == power_source else 0.0
                        point.is_connected = True
                        logger.debug(f"开启点位 {point_id}")
                    else:
                        # 如果点位已经是开启状态，不需要额外操作
                        logger.debug(f"点位 {point_id} 已经是开启状态，跳过")
            
            # 通电次数 = 1（表示进行了一次通电测试）
            power_on_operations = 1
            
            # 检测导通情况
            detected_connections = self._detect_connections(power_source, points_to_activate)
            
            # 更新关系矩阵
            self._update_relationship_matrix(power_source, points_to_activate, detected_connections)
            
            # 计算测试时间
            test_duration = time.time() - start_time
            
            # 创建测试结果
            test_result = TestResult(
                test_id=test_id,
                timestamp=start_time,
                power_source=power_source,
                active_points=points_to_activate,
                detected_connections=detected_connections,
                test_duration=test_duration,
                relay_operations=relay_operations,
                power_on_operations=power_on_operations,
                total_points=self.total_points
            )
            
            # 记录测试历史
            self.test_history.append(test_result)
            
            logger.info(f"测试 {test_id} 完成，检测到 {len(detected_connections)} 个连接关系，继电器操作 {relay_operations} 次")
            logger.info(f"关闭了 {len(points_to_close)} 个点位: {points_to_close}")
            logger.info(f"激活了 {len(points_to_activate)} 个点位: {points_to_activate}")
            
            return test_result
            
        except Exception as e:
            # 发生异常时，确保关闭所有激活的点位
            for point_id in points_to_activate:
                try:
                    self._simulate_relay_operation(point_id, RelayState.OFF)
                except:
                    pass
            
            logger.error(f"测试 {test_id} 失败: {e}")
            raise
    
    def run_batch_tests(self, test_configs: List[Dict]) -> List[TestResult]:
        """
        运行批量测试
        
        Args:
            test_configs: 测试配置列表，每个配置包含 power_source 和 test_points
            
        Returns:
            List[TestResult]: 所有测试结果
        """
        results = []
        
        for i, config in enumerate(test_configs):
            logger.info(f"运行批量测试 {i+1}/{len(test_configs)}")
            
            power_source = config.get('power_source', 0)
            test_points = config.get('test_points', [])
            
            result = self.run_single_test(power_source, test_points)
            results.append(result)
            
            # 测试间隔
            time.sleep(0.1)
        
        return results
    
    def generate_random_test_configs(self, test_count: int = 10, max_points_per_test: int = 100) -> List[Dict]:
        """
        生成随机测试配置
        
        Args:
            test_count: 测试次数
            max_points_per_test: 每次测试的最大点位数量
            
        Returns:
            List[Dict]: 随机测试配置列表
        """
        configs = []
        
        for _ in range(test_count):
            power_source = random.randint(0, self.total_points - 1)
            test_points_count = random.randint(10, max_points_per_test)
            test_points = random.sample(range(self.total_points), test_points_count)
            
            configs.append({
                'power_source': power_source,
                'test_points': test_points
            })
        
        return configs
    
    def get_point_state(self, point_id: int) -> Optional[TestPoint]:
        """
        获取指定点位的状态信息
        
        Args:
            point_id: 点位ID
            
        Returns:
            TestPoint: 点位状态信息，如果点位不存在则返回None
        """
        return self.test_points.get(point_id)
    
    def get_all_point_states(self) -> Dict[int, TestPoint]:
        """
        获取所有点位的状态信息
        
        Returns:
            Dict[int, TestPoint]: 所有点位的状态信息字典
        """
        return self.test_points.copy()
    
    def test_cluster_connectivity(self, cluster1_points: List[int], cluster2_points: List[int]) -> bool:
        """
        测试两个集群之间是否导通
        
        Args:
            cluster1_points: 第一个集群的点位列表
            cluster2_points: 第二个集群的点位列表
            
        Returns:
            bool: 两个集群是否导通
        """
        # 从第一个集群中选择一个点位作为电源
        power_source = cluster1_points[0]
        
        # 测试第二个集群的所有点位
        test_points = cluster2_points
        
        # 运行测试
        test_result = self.run_single_test(power_source, test_points)
        
        # 检查是否检测到连接
        return len(test_result.detected_connections) > 0

    def merge_connectivity_tested_clusters(self, confirmed_clusters: List[Dict]) -> List[Dict]:
        """
        基于导通测试结果合并集群
        需要测试不同集群之间的导通性来决定是否合并
        
        Args:
            confirmed_clusters: 已确认的集群列表
            
        Returns:
            List[Dict]: 合并后的集群列表
        """
        if len(confirmed_clusters) <= 1:
            return confirmed_clusters
        
        # 创建集群的副本用于处理
        clusters = [cluster.copy() for cluster in confirmed_clusters]
        merged_clusters = []
        
        # 检查每个集群对之间是否应该合并
        i = 0
        while i < len(clusters):
            if i >= len(clusters):  # 安全检查
                break
                
            current_cluster = clusters[i]
            merged = False
            
            # 检查当前集群是否应该与已合并的集群合并
            for merged_cluster in merged_clusters:
                if self.test_cluster_connectivity(current_cluster['points'], merged_cluster['points']):
                    # 两个集群导通，应该合并
                    print(f"集群 {current_cluster['points']} 与集群 {merged_cluster['points']} 导通，进行合并")
                    
                    # 合并点位
                    for point in current_cluster['points']:
                        if point not in merged_cluster['points']:
                            merged_cluster['points'].append(point)
                    
                    merged_cluster['points'].sort()
                    merged_cluster['point_count'] = len(merged_cluster['points'])
                    merged = True
                    break
            
            if not merged:
                # 检查是否应该与后续未处理的集群合并
                j = i + 1
                while j < len(clusters):
                    if self.test_cluster_connectivity(current_cluster['points'], clusters[j]['points']):
                        # 两个集群导通，应该合并
                        print(f"集群 {current_cluster['points']} 与集群 {clusters[j]['points']} 导通，进行合并")
                        
                        # 合并点位
                        for point in clusters[j]['points']:
                            if point not in current_cluster['points']:
                                current_cluster['points'].append(point)
                        
                        current_cluster['points'].sort()
                        current_cluster['point_count'] = len(current_cluster['points'])
                        
                        # 移除已合并的集群
                        clusters.pop(j)
                        break
                    j += 1
                
                # 将当前集群添加到已合并列表
                merged_clusters.append(current_cluster)
            
            i += 1
        
        return merged_clusters

    def get_confirmed_clusters(self) -> List[Dict]:
        """
        已废弃：不再提供“集群”概念。为兼容旧接口，返回空列表。
        """
        return []
    
    def get_system_status(self) -> Dict:
        """获取系统状态信息"""
        return {
            'total_points': self.total_points,
            'relay_switch_time': self.relay_switch_time,
            'total_connections': len(self.true_pairs),
            'total_tests': len(self.test_history),
            'total_relay_operations': self.relay_operation_count,
            'system_uptime': time.time()
        }

    # ================= 纯“点-点关系”接口 =================
    def _iter_detected_conductive_pairs(self) -> Set[Tuple[int, int]]:
        pairs: Set[Tuple[int, int]] = set()
        for tr in self.test_history:
            for c in tr.detected_connections:
                s = int(c.source_point)
                for t in c.target_points:
                    a, b = (s, int(t)) if s <= int(t) else (int(t), s)
                    pairs.add((a, b))
        return pairs

    def get_confirmed_conductive_pairs(self) -> List[Dict]:
        """返回已确认导通的点对列表。"""
        pairs = sorted(list(self._iter_detected_conductive_pairs()))
        return [{'point1': a, 'point2': b} for (a, b) in pairs]

    def _were_points_cotested_without_link(self, p1: int, p2: int) -> bool:
        cotested = False
        for tr in self.test_history:
            ap = tr.active_points
            if p1 in ap and p2 in ap:
                cotested = True
                # 若此轮存在二者之间的连接，则视为非“不导通”
                linked = False
                for c in tr.detected_connections:
                    if (c.source_point == p1 and p2 in c.target_points) or (c.source_point == p2 and p1 in c.target_points):
                        linked = True
                        break
                if linked:
                    return False
        return cotested

    def get_confirmed_non_conductive_pairs(self) -> List[Dict]:
        """返回已确认不导通（同测且未出现连接）的点对列表。"""
        res: List[Dict] = []
        for a in range(self.total_points):
            for b in range(a + 1, self.total_points):
                if self._were_points_cotested_without_link(a, b):
                    res.append({'point1': a, 'point2': b})
        return res

    def get_unconfirmed_pairs(self) -> List[Dict]:
        """返回尚未确认导通/不导通的点对（可能较多）。"""
        conductive = set((p['point1'], p['point2']) for p in self.get_confirmed_conductive_pairs())
        non_cond = set((p['point1'], p['point2']) for p in self.get_confirmed_non_conductive_pairs())
        res: List[Dict] = []
        for a in range(self.total_points):
            for b in range(a + 1, self.total_points):
                if (a, b) in conductive or (a, b) in non_cond:
                    continue
                res.append({'point1': a, 'point2': b})
        return res

    def get_relationship_summary(self) -> Dict:
        """返回关系计数摘要。"""
        cp = len(self.get_confirmed_conductive_pairs())
        ncp = len(self.get_confirmed_non_conductive_pairs())
        up = len(self.get_unconfirmed_pairs())
        return {
            'total_points': self.total_points,
            'confirmed_conductive_pairs': cp,
            'confirmed_non_conductive_pairs': ncp,
            'unconfirmed_pairs': up
        }
    
    def get_point_relationships(self, point_id: int) -> Dict:
        """
        获取指定点位与其他所有点位的导通关系
        
        Args:
            point_id: 点位ID
            
        Returns:
            Dict: 包含导通关系的字典
        """
        if point_id < 0 or point_id >= self.total_points:
            return {'error': '点位ID超出范围'}
        
        relationships = {
            'point_id': point_id,
            'total_points': self.total_points,
            'conductive_points': [],
            'non_conductive_points': [],
            'unknown_points': [],
            'relationship_matrix_row': self.relationship_matrix[point_id]
        }
        
        for i in range(self.total_points):
            if i == point_id:
                continue
                
            relation = self.relationship_matrix[point_id][i]
            if relation == 1:
                relationships['conductive_points'].append(i)
            elif relation == -1:
                relationships['non_conductive_points'].append(i)
            else:  # relation == 0
                relationships['unknown_points'].append(i)
        
        return relationships
    
    def get_relationship_matrix(self) -> List[List[int]]:
        """
        获取完整的关系矩阵
        
        Returns:
            List[List[int]]: N*N的关系矩阵
        """
        return self.relationship_matrix
    
    def get_true_relationship_matrix(self) -> List[List[int]]:
        """
        获取真实关系矩阵（基于true_pairs生成）
        
        Returns:
            List[List[int]]: N*N的真实关系矩阵
        """
        return self.true_relationship_matrix
    
    def get_relationship_matrices_comparison(self) -> Dict:
        """
        获取检测到的关系矩阵与真实关系矩阵的对比
        
        Returns:
            Dict: 包含两个矩阵和对比信息的字典
        """
        detected_matrix = self.get_relationship_matrix()
        true_matrix = self.get_true_relationship_matrix()
        
        # 计算对比信息
        total_cells = self.total_points * self.total_points
        diagonal_cells = self.total_points  # 对角线上的单元格
        off_diagonal_cells = total_cells - diagonal_cells  # 非对角线上的单元格
        
        # 统计检测到的关系
        detected_conductive = 0
        detected_non_conductive = 0
        detected_unknown = 0
        
        # 统计真实关系
        true_conductive = 0
        true_unknown = 0
        
        # 统计匹配情况
        matched_conductive = 0
        matched_non_conductive = 0
        false_positive = 0  # 误报：检测到导通但实际不导通
        false_negative = 0  # 漏报：实际导通但未检测到
        
        for i in range(self.total_points):
            for j in range(self.total_points):
                if i == j:  # 跳过对角线
                    continue
                    
                detected = detected_matrix[i][j]
                true_val = true_matrix[i][j]
                
                # 统计检测到的关系
                if detected == 1:
                    detected_conductive += 1
                elif detected == -1:
                    detected_non_conductive += 1
                else:  # detected == 0
                    detected_unknown += 1
                
                # 统计真实关系
                if true_val == 1:
                    true_conductive += 1
                else:  # true_val == 0
                    true_unknown += 1
                
                # 统计匹配情况
                if detected == 1 and true_val == 1:
                    matched_conductive += 1
                elif detected == -1 and true_val == 0:
                    matched_non_conductive += 1
                elif detected == 1 and true_val == 0:
                    false_positive += 1
                elif detected == -1 and true_val == 1:
                    false_negative += 1
        
        # 计算准确率
        total_detected = detected_conductive + detected_non_conductive
        if total_detected > 0:
            accuracy = (matched_conductive + matched_non_conductive) / total_detected * 100
        else:
            accuracy = 0
        
        return {
            'detected_matrix': detected_matrix,
            'true_matrix': true_matrix,
            'comparison': {
                'total_points': self.total_points,
                'off_diagonal_cells': off_diagonal_cells,
                'detected': {
                    'conductive': detected_conductive,
                    'non_conductive': detected_non_conductive,
                    'unknown': detected_unknown
                },
                'true': {
                    'conductive': true_conductive,
                    'unknown': true_unknown
                },
                'matching': {
                    'matched_conductive': matched_conductive,
                    'matched_non_conductive': matched_non_conductive,
                    'false_positive': false_positive,
                    'false_negative': false_negative,
                    'accuracy_percentage': accuracy
                }
            }
        }
    
    def get_point_relationships(self, point_id: int) -> Dict:
        """
        获取指定点位与其他所有点位的导通关系
        
        Args:
            point_id: 点位ID
            
        Returns:
            Dict: 包含导通关系的字典
        """
        if point_id < 0 or point_id >= self.total_points:
            return {'error': '点位ID超出范围'}
        
        relationships = {
            'point_id': point_id,
            'total_points': self.total_points,
            'conductive_points': [],
            'non_conductive_points': [],
            'unknown_points': [],
            'relationship_matrix_row': self.relationship_matrix[point_id]
        }
        
        for i in range(self.total_points):
            if i == point_id:
                continue
                
            relation = self.relationship_matrix[point_id][i]
            if relation == 1:
                relationships['conductive_points'].append(i)
            elif relation == -1:
                relationships['non_conductive_points'].append(i)
            else:  # relation == 0
                relationships['unknown_points'].append(i)
        
        return relationships
    
    def get_real_conductive_points(self, point_id: int) -> Dict:
        """
        获取指定点位作为通电点位时的真实导通点位信息
        
        Args:
            point_id: 点位ID
            
        Returns:
            Dict: 包含真实导通点位信息的字典
        """
        if point_id < 0 or point_id >= self.total_points:
            return {'error': '点位ID超出范围'}
        
        # 获取该点位作为电源时能导通的所有目标点位
        conductive_targets = []
        for target_id in range(self.total_points):
            if target_id == point_id:
                continue
            # 检查是否存在真实的导通关系
            a, b = (point_id, target_id) if point_id <= target_id else (target_id, point_id)
            if (a, b) in self.true_pairs:
                conductive_targets.append(target_id)
        
        return {
            'power_point': point_id,
            'total_points': self.total_points,
            'conductive_targets': conductive_targets,
            'conductive_count': len(conductive_targets),
            'description': f'点位 {point_id} 作为通电点位时，能导通 {len(conductive_targets)} 个目标点位'
        }
    
    def get_all_real_conductive_info(self) -> Dict:
        """
        获取所有点位的真实导通信息概览
        
        Returns:
            Dict: 包含所有点位真实导通信息的字典
        """
        all_info = []
        total_conductive_pairs = 0
        
        for point_id in range(self.total_points):
            info = self.get_real_conductive_points(point_id)
            if 'error' not in info:
                all_info.append(info)
                total_conductive_pairs += info['conductive_count']
        
        return {
            'total_points': self.total_points,
            'total_conductive_pairs': total_conductive_pairs,
            'points_info': all_info,
            'summary': {
                'points_with_conductive_relations': len([p for p in all_info if p['conductive_count'] > 0]),
                'points_without_conductive_relations': len([p for p in all_info if p['conductive_count'] == 0]),
                'average_conductive_targets': total_conductive_pairs / max(1, self.total_points)
            }
        }
    
    def export_test_results(self, filename: str = None) -> str:
        """
        导出测试结果到JSON文件
        
        Args:
            filename: 文件名，如果为None则自动生成
            
        Returns:
            str: 导出的文件路径
        """
        if filename is None:
            filename = f"cable_test_results_{int(time.time())}.json"
        
        export_data = {
            'system_info': self.get_system_status(),
            'true_pairs': [ {'point1': a, 'point2': b} for (a, b) in sorted(self.true_pairs) ],
            'test_results': [
                {
                    'test_id': result.test_id,
                    'timestamp': result.timestamp,
                    'power_source': result.power_source,
                    'active_points': result.active_points,
                    'detected_connections': [
                        {
                            'source_point': conn.source_point,
                            'target_points': conn.target_points,
                            'connection_type': conn.connection_type
                        }
                        for conn in result.detected_connections
                    ],
                    'test_duration': result.test_duration,
                    'relay_operations': result.relay_operations
                }
                for result in self.test_history
            ]
        }
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"测试结果已导出到: {filename}")
        return filename
    
    def reset_system(self):
        """重置系统状态"""
        self.test_history.clear()
        self.relay_operation_count = 0
        
        for point in self.test_points.values():
            point.relay_state = RelayState.OFF
            point.voltage = 0.0
            point.current = 0.0
            point.is_connected = False
        
        logger.info("系统已重置")
    
    def reset_and_regenerate(self, min_cluster_size: Optional[int] = None, max_cluster_size: Optional[int] = None,
                             total_points: Optional[int] = None):
        """重置系统并重新生成随机“点-点导通对”。
        兼容参数保留，但不再表示“集群大小”。
        """
        # 若需要调整总点位，先更新并重新初始化点位表
        if isinstance(total_points, int) and total_points >= 2:
            self.total_points = int(total_points)
            self.test_points = {}
            self.connections = []
            self.test_history = []
            self.relay_operation_count = 0
            self.power_on_count = 0
            self._initialize_test_points()
        else:
            self.reset_system()
        # 参数仅作占位
        if isinstance(min_cluster_size, int):
            self.min_cluster_size = max(2, int(min_cluster_size))
        if isinstance(max_cluster_size, int):
            self.max_cluster_size = max(self.min_cluster_size, int(max_cluster_size))
        self._generate_random_connections()
        logger.info(
            f"系统已重置并重新生成随机点对导通关系，总点位={self.total_points}"
        )
    
    def reset_and_regenerate_with_distribution(self, total_points: int = None, conductivity_distribution: Dict[int, int] = None):
        """
        重置系统并重新生成连接关系，支持精细化的导通分布控制
        
        Args:
            total_points: 总点位数量
            conductivity_distribution: 导通分布字典，格式为 {1: 50, 2: 30, 3: 20, 4: 0}
        """
        logger.info("开始重置系统并重新生成连接关系")
        
        # 更新总点位数量
        if total_points is not None:
            if total_points < 2:
                raise ValueError("总点位数量必须大于等于2")
            self.total_points = total_points
            logger.info(f"更新总点位数量为: {self.total_points}")
        
        # 清空现有数据
        self.test_points.clear()
        self.true_pairs.clear()
        self.relationship_matrix = []
        self.true_relationship_matrix = []
        self.test_history.clear()
        
        # 重新初始化测试点位
        self._initialize_test_points()
        
        # 重新初始化关系矩阵
        self.relationship_matrix = [[0 for _ in range(self.total_points)] for _ in range(self.total_points)]
        self.true_relationship_matrix = [[0 for _ in range(self.total_points)] for _ in range(self.total_points)]
        
        # 确保对角线始终为1（点位与自身的关系）
        for i in range(self.total_points):
            self.relationship_matrix[i][i] = 1
            self.true_relationship_matrix[i][i] = 1
        
        # 使用指定的导通分布生成连接关系
        if conductivity_distribution is not None:
            # 直接调用工作正常的_generate_random_connections方法，但传入自定义分布
            self._generate_random_connections_with_custom_distribution(conductivity_distribution)
        else:
            # 使用默认分布
            self._generate_random_connections()
        
        logger.info("系统重置完成")
    
    def _generate_random_connections_with_custom_distribution(self, conductivity_distribution: Dict[int, int]):
        """
        使用自定义导通分布生成随机连接关系（基于原有的工作逻辑）
        
        Args:
            conductivity_distribution: 导通分布字典，格式为 {1: 50, 2: 30, 3: 20, 4: 0}
        """
        logger.info(f"使用自定义导通分布生成随机连接关系: {conductivity_distribution}")
        
        # 清空现有连接
        self.true_pairs.clear()
        
        # 确保键是整数类型（处理前端可能发送字符串键的情况）
        normalized_distribution = {}
        for key, value in conductivity_distribution.items():
            try:
                int_key = int(key)
                normalized_distribution[int_key] = int(value)
            except (ValueError, TypeError):
                logger.warning(f"跳过无效的导通分布键值对: {key}: {value}")
                continue
        
        conductivity_distribution = normalized_distribution
        logger.info(f"标准化后的导通分布: {conductivity_distribution}")
        
        # 验证总数是否匹配
        total_points_from_distribution = sum(conductivity_distribution.values())
        if total_points_from_distribution != self.total_points:
            logger.warning(f"导通分布总数({total_points_from_distribution})与总点数({self.total_points})不匹配，将自动调整")
            # 自动调整分布
            if total_points_from_distribution > self.total_points:
                # 如果分布总数过多，减少高导通数量的点位
                excess = total_points_from_distribution - self.total_points
                for i in range(4, 0, -1):
                    if conductivity_distribution.get(i, 0) >= excess:
                        conductivity_distribution[i] = conductivity_distribution.get(i, 0) - excess
                        break
                    else:
                        excess -= conductivity_distribution.get(i, 0)
                        conductivity_distribution[i] = 0
            else:
                # 如果分布总数过少，增加低导通数量的点位
                shortage = self.total_points - total_points_from_distribution
                conductivity_distribution[1] = conductivity_distribution.get(1, 0) + shortage
        
        logger.info(f"调整后的导通分布: {conductivity_distribution}")
        
        # 为每个点位分配导通数量
        point_conductivity_counts = {}
        
        # 首先处理高导通数量的点位
        for conductivity_count in range(4, 0, -1):
            num_points_needed = conductivity_distribution.get(conductivity_count, 0)
            if num_points_needed <= 0:
                continue
                
            # 随机选择需要这个导通数量的点位
            available_points = [i for i in range(self.total_points) if i not in point_conductivity_counts]
            if len(available_points) < num_points_needed:
                logger.warning(f"可用点位不足，需要{num_points_needed}个，但只有{len(available_points)}个可用")
                num_points_needed = len(available_points)
            
            selected_points = random.sample(available_points, num_points_needed)
            
            for point_id in selected_points:
                point_conductivity_counts[point_id] = conductivity_count
                logger.debug(f"点位 {point_id} 设置为除自己外导通 {conductivity_count} 个其他点位")
        
        # 生成具体的连接关系
        # 每个点位的导通关系是独立的，不需要双向一致性
        # 简单直接的随机选择策略
        
        for point_id, target_conductivity_count in point_conductivity_counts.items():
            # 为当前点位选择目标导通点位（不包括自己）
            available_targets = [i for i in range(self.total_points) if i != point_id]
            
            # 确保不超过设定的导通数量
            actual_connections = min(target_conductivity_count, len(available_targets))
            
            if actual_connections > 0:
                # 随机选择目标点位（完全随机，不考虑冲突）
                target_points = random.sample(available_targets, actual_connections)
                
                # 创建单向连接关系（A->B不代表B->A）
                for target_point in target_points:
                    # 创建从point_id到target_point的连接
                    self.true_relationship_matrix[point_id][target_point] = 1
                    logger.debug(f"创建连接: 点位 {point_id} -> 点位 {target_point}")
        
        # 确保对角线为1，其他未设置的位置为-1
        for i in range(self.total_points):
            for j in range(self.total_points):
                if i == j:
                    self.true_relationship_matrix[i][j] = 1  # 对角线始终为1
                elif self.true_relationship_matrix[i][j] != 1:
                    # 如果还没有设置为导通，则设置为不导通
                    self.true_relationship_matrix[i][j] = -1
        
        logger.info(f"连接关系生成完成")
        logger.info(f"实际导通分布统计（除自己外的导通数量）:")
        
        # 统计实际的导通分布
        actual_distribution = {}
        for i in range(self.total_points):
            count = 0
            for j in range(self.total_points):
                if i != j and self.true_relationship_matrix[i][j] == 1:
                    count += 1
            actual_distribution[count] = actual_distribution.get(count, 0) + 1
        
        for count in sorted(actual_distribution.keys()):
            logger.info(f"  除自己外导通{count}个点位的点: {actual_distribution[count]}个")
        
        # 额外统计信息
        total_connections = sum(actual_distribution.values())
        logger.info(f"  总连接数: {total_connections}")
        
        # 统计作为目标的被选择次数分布
        target_selection_count = {}
        for j in range(self.total_points):
            count = 0
            for i in range(self.total_points):
                if i != j and self.true_relationship_matrix[i][j] == 1:
                    count += 1
            target_selection_count[count] = target_selection_count.get(count, 0) + 1
        
        logger.info(f"  作为目标被选择的次数分布:")
        for count in sorted(target_selection_count.keys()):
            logger.info(f"    被{count}个点位选择的点: {target_selection_count[count]}个")
    
    def get_real_clusters(self) -> List[Dict]:
        """
        已废弃：不再提供“真实集群”。为兼容旧接口，返回空列表。
        """
        return []

    def get_cluster_comparison(self) -> Dict:
        """已废弃：返回空的集群对比信息。"""
        return {
            'real_clusters_count': 0,
            'confirmed_clusters_count': 0,
            'matched_clusters_count': 0,
            'accuracy_rate': 0,
            'real_clusters': [],
            'confirmed_clusters': [],
            'matched_clusters': []
        }

    def get_unconfirmed_points(self) -> List[int]:
        """（兼容保留）返回在任何导通对中尚未出现过的点位。"""
        if len(self.test_history) == 0:
            return list(range(self.total_points))
        appeared: Set[int] = set()
        for tr in self.test_history:
            for c in tr.detected_connections:
                appeared.add(int(c.source_point))
                for t in c.target_points:
                    appeared.add(int(t))
        return [p for p in range(self.total_points) if p not in appeared]

    def get_cluster_visualization_data(self) -> Dict:
        """已废弃：返回空结构（兼容前端调用）。"""
        return {
            'confirmed_clusters': [],
            'cluster_colors': {},
            'unconfirmed_points': self.get_unconfirmed_points(),
            'total_confirmed_points': 0,
            'total_unconfirmed_points': len(self.get_unconfirmed_points())
        }

    def get_detailed_cluster_info(self) -> Dict:
        """已废弃：返回空结构（兼容前端调用）。"""
        unconfirmed_points = self.get_unconfirmed_points()
        return {
            'confirmed_clusters': [],
            'unconfirmed_points': {
                'points': unconfirmed_points,
                'count': len(unconfirmed_points),
                'description': f"未参与任何导通对的点位: {len(unconfirmed_points)}个"
            },
            'summary': {
                'total_clusters': 0,
                'total_confirmed_points': 0,
                'total_unconfirmed_points': len(unconfirmed_points),
                'total_points': self.total_points
            }
        }

    def get_confirmed_non_conductive_relationships(self) -> Dict:
        """（兼容保留）仅返回点-点不导通集合，其余返回空。"""
        pp = self.get_confirmed_non_conductive_pairs()
        return {
            'summary': {
                'cluster_pairs': 0,
                'point_cluster_pairs': 0,
                'point_point_pairs': len(pp)
            },
            'cluster_non_conductive_pairs': [],
            'point_cluster_non_conductive': [],
            'point_point_non_conductive': [
                {'point1': x['point1'], 'point2': x['point2'], 'status': 'confirmed_non_conductive'} for x in pp
            ]
        }

    def get_unconfirmed_cluster_relationships(self) -> Dict:
        """已废弃：改为返回点-点关系的未确认对与测试建议。"""
        confirmed_pairs = self.get_confirmed_conductive_pairs()
        non_cond_pairs = self.get_confirmed_non_conductive_pairs()
        unconfirmed_pairs = self.get_unconfirmed_pairs()

        # 生成若干“单对测试”建议（按未确认对前若干）
        max_suggestions = min(100, len(unconfirmed_pairs))
        suggestions: List[Dict] = []
        for item in unconfirmed_pairs[:max_suggestions]:
            p1, p2 = int(item['point1']), int(item['point2'])
            suggestions.append({
                'type': 'point_to_point_test',
                'priority': 'medium',
                'test_config': {
                    'power_source': p1,
                    'test_points': [p2],
                    'expected_result': '判定该对点位是否直接导通'
                }
            })

        return {
            'summary': {
                'total_confirmed_clusters': 0,
                'total_unconfirmed_points': len(self.get_unconfirmed_points()),
                'total_unconfirmed_cluster_relationships': 0,
                'total_unconfirmed_point_relationships': 0,
                'total_unconfirmed_point_to_point_relationships': len(unconfirmed_pairs),
                'total_testing_suggestions': len(suggestions)
            },
            'unconfirmed_cluster_relationships': [],
            'unconfirmed_point_relationships': [],
            'unconfirmed_point_to_point_relationships': unconfirmed_pairs,
            'testing_suggestions': suggestions,
            'analysis': {
                'description': '点-点关系未确认分析（无集群/无传递性）',
                'details': [
                    '系统仅记录直接导通/不导通关系',
                    '建议优先测试未确认点对'
                ]
            },
            'debug': {
                'num_tests': len(self.test_history),
                'num_detected_connections': sum(len(tr.detected_connections) for tr in self.test_history),
                'non_conductive_summary': {'point_point_pairs': len(non_cond_pairs)},
            }
        }
    
    def _are_clusters_confirmed_non_conductive(self, cluster1_points: List[int], cluster2_points: List[int]) -> bool:
        """已废弃：集群概念移除，恒返回 False。"""
        return False
    
    def _is_point_cluster_confirmed_non_conductive(self, point_id: int, cluster_points: List[int]) -> bool:
        """已废弃：集群概念移除。"""
        return False
    
    def _are_points_confirmed_non_conductive(self, point1: int, point2: int) -> bool:
        """
        检查两个点位是否已经确认不导通（基于同测且未观察到连接）
        
        Args:
            point1: 第一个点位ID
            point2: 第二个点位ID
            
        Returns:
            bool: True表示已确认不导通，False表示未确认
        """
        return self._were_points_cotested_without_link(point1, point2)

# 测试接口函数
def create_test_interface():
    """创建测试接口实例"""
    return CableTestSystem()

def run_demo_test():
    """运行演示测试"""
    print("=== 线缆测试系统演示 ===")
    
    # 创建测试系统
    test_system = CableTestSystem(total_points=1000)  # 使用较小的点数进行演示
    
    # 显示系统状态
    status = test_system.get_system_status()
    print(f"系统状态: {json.dumps(status, ensure_ascii=False, indent=2)}")
    
    # 生成随机测试配置
    test_configs = test_system.generate_random_test_configs(test_count=3, max_points_per_test=50)
    
    # 运行测试
    print("\n开始运行测试...")
    results = test_system.run_batch_tests(test_configs)
    
    # 显示测试结果摘要
    print(f"\n测试完成，共运行 {len(results)} 次测试:")
    for result in results:
        print(f"  测试 {result.test_id}: 检测到 {len(result.detected_connections)} 个连接关系，耗时 {result.test_duration:.3f}秒")
    
    # 导出结果
    export_file = test_system.export_test_results()
    print(f"\n测试结果已导出到: {export_file}")
    
    return test_system

if __name__ == "__main__":
    # 运行演示测试
    test_system = run_demo_test()
