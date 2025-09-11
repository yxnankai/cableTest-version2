#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
优化版线缆测试系统 - 高性能版本
主要优化：
1. 减少不必要的计算
2. 使用缓存机制
3. 优化数据结构
4. 减少内存分配
"""

import random
import time
import json
from typing import List, Dict, Set, Tuple, Optional, Any
from dataclasses import dataclass
from enum import Enum
import logging
import sys
import os

# 添加性能计时器和缓存
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from utils.performance_timer import get_timer, time_step
from utils.cache_manager import cached, get_cache_manager

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class RelayState(Enum):
    """继电器状态枚举"""
    OFF = 0  # 关闭
    ON = 1   # 开启

@dataclass
class TestPoint:
    """测试点位信息（优化版）"""
    point_id: int
    relay_state: RelayState = RelayState.OFF
    voltage: float = 0.0
    current: float = 0.0
    is_connected: bool = False
    # 添加缓存字段
    _cached_connections: Optional[Set[int]] = None
    _last_update: float = 0.0

@dataclass
class Connection:
    """连接关系（优化版）"""
    source_point: int
    target_points: List[int]
    connection_type: str  # "one_to_one" 或 "one_to_many"
    # 添加缓存字段
    _cached_hash: Optional[int] = None

@dataclass
class TestResult:
    """测试结果（优化版）"""
    test_id: str
    power_source: int
    test_points: List[int]
    results: Dict[int, Dict[str, Any]]
    timestamp: float
    duration: float
    success: bool
    error_message: Optional[str] = None

class OptimizedCableTestSystem:
    """优化版线缆测试系统"""
    
    def __init__(self, total_points: int = 100, relay_switch_time: float = 0.0005):
        self.total_points = total_points
        self.relay_switch_time = relay_switch_time
        
        # 使用更高效的数据结构
        self.test_points: Dict[int, TestPoint] = {}
        self.connections: List[Connection] = []
        self.test_history: List[TestResult] = []
        
        # 添加缓存和性能优化
        self.cache = get_cache_manager()
        self._connection_matrix: Optional[Dict[int, Set[int]]] = None
        self._last_matrix_update = 0.0
        self._matrix_ttl = 60.0  # 矩阵缓存60秒
        
        # 初始化系统
        self._initialize_system()
    
    def _initialize_system(self):
        """初始化系统（优化版）"""
        timer = get_timer()
        
        with timer.time_step("system_init", {"total_points": self.total_points}):
            # 批量创建测试点位
            self.test_points = {
                i: TestPoint(point_id=i, _last_update=time.time())
                for i in range(self.total_points)
            }
            
            # 生成连接关系（优化版）
            self._generate_connections_optimized()
            
            logger.info(f"优化版测试系统初始化完成，总点位: {self.total_points}")
    
    def _generate_connections_optimized(self):
        """优化版连接关系生成"""
        timer = get_timer()
        
        with timer.time_step("generate_connections", {"total_points": self.total_points}):
            # 使用更高效的算法生成连接关系
            connections = []
            
            # 预分配列表大小
            target_connections = []
            
            for point_id in range(self.total_points):
                # 使用更高效的随机数生成
                num_connections = self._get_connection_count_optimized(point_id)
                
                if num_connections > 0:
                    # 使用集合操作优化目标点选择
                    available_targets = set(range(self.total_points)) - {point_id}
                    targets = random.sample(list(available_targets), min(num_connections, len(available_targets)))
                    
                    connection = Connection(
                        source_point=point_id,
                        target_points=targets,
                        connection_type="one_to_many",
                        _cached_hash=hash((point_id, tuple(sorted(targets))))
                    )
                    connections.append(connection)
                    
                    # 更新测试点位的连接信息
                    self.test_points[point_id]._cached_connections = set(targets)
            
            self.connections = connections
            self._invalidate_connection_matrix()
            
            logger.info(f"生成连接关系完成，总连接数: {len(connections)}")
    
    def _get_connection_count_optimized(self, point_id: int) -> int:
        """优化版连接数量计算"""
        # 使用更简单的分布算法
        rand = random.random()
        if rand < 0.9:  # 90% 概率1个连接
            return 1
        elif rand < 0.96:  # 6% 概率2个连接
            return 2
        elif rand < 0.99:  # 3% 概率3个连接
            return 3
        else:  # 1% 概率4个连接
            return 4
    
    @cached(ttl=60)
    def get_connection_matrix(self) -> Dict[int, Set[int]]:
        """获取连接矩阵（带缓存）"""
        current_time = time.time()
        
        # 检查缓存是否有效
        if (self._connection_matrix is not None and 
            current_time - self._last_matrix_update < self._matrix_ttl):
            return self._connection_matrix
        
        # 重新计算矩阵
        timer = get_timer()
        with timer.time_step("build_connection_matrix", {"total_points": self.total_points}):
            matrix = {}
            for point_id in range(self.total_points):
                matrix[point_id] = set()
            
            for connection in self.connections:
                source = connection.source_point
                for target in connection.target_points:
                    matrix[source].add(target)
                    matrix[target].add(source)  # 双向连接
            
            self._connection_matrix = matrix
            self._last_matrix_update = current_time
            
            return matrix
    
    def _invalidate_connection_matrix(self):
        """使连接矩阵缓存失效"""
        self._connection_matrix = None
        self._last_matrix_update = 0.0
    
    @cached(ttl=30)
    def run_single_test_optimized(self, power_source: int, test_points: List[int]) -> TestResult:
        """优化版单次测试"""
        timer = get_timer()
        test_id = f"test_{int(time.time() * 1000)}_{random.randint(1000, 9999)}"
        
        with timer.time_step("single_test", {"power_source": power_source, "test_count": len(test_points)}):
            start_time = time.time()
            results = {}
            
            try:
                # 优化版电源切换
                self._switch_power_source_optimized(power_source)
                
                # 批量激活测试点位
                self._activate_test_points_optimized(test_points)
                
                # 批量测试
                for point_id in test_points:
                    result = self._test_point_optimized(point_id)
                    results[point_id] = result
                
                duration = time.time() - start_time
                
                test_result = TestResult(
                    test_id=test_id,
                    power_source=power_source,
                    test_points=test_points,
                    results=results,
                    timestamp=start_time,
                    duration=duration,
                    success=True
                )
                
                # 添加到历史记录
                self.test_history.append(test_result)
                
                return test_result
                
            except Exception as e:
                duration = time.time() - start_time
                logger.error(f"测试失败: {e}")
                
                return TestResult(
                    test_id=test_id,
                    power_source=power_source,
                    test_points=test_points,
                    results={},
                    timestamp=start_time,
                    duration=duration,
                    success=False,
                    error_message=str(e)
                )
    
    def _switch_power_source_optimized(self, power_source: int):
        """优化版电源切换"""
        timer = get_timer()
        
        with timer.time_step("switch_power", {"power_source": power_source}):
            # 关闭所有继电器
            for point in self.test_points.values():
                point.relay_state = RelayState.OFF
            
            # 开启指定电源
            if power_source in self.test_points:
                self.test_points[power_source].relay_state = RelayState.ON
                self.test_points[power_source].voltage = 5.0  # 模拟5V电压
            
            # 模拟继电器切换时间
            time.sleep(self.relay_switch_time)
    
    def _activate_test_points_optimized(self, test_points: List[int]):
        """优化版测试点位激活"""
        timer = get_timer()
        
        with timer.time_step("activate_points", {"point_count": len(test_points)}):
            # 批量激活测试点位
            for point_id in test_points:
                if point_id in self.test_points:
                    point = self.test_points[point_id]
                    point.is_connected = True
                    point._last_update = time.time()
            
            # 模拟激活时间
            time.sleep(self.relay_switch_time * 0.5)
    
    def _test_point_optimized(self, point_id: int) -> Dict[str, Any]:
        """优化版点位测试"""
        timer = get_timer()
        
        with timer.time_step("test_point", {"point_id": point_id}):
            point = self.test_points[point_id]
            
            # 检查是否导通
            is_conductive = self._check_conductivity_optimized(point_id)
            
            # 模拟测量值
            if is_conductive:
                voltage = 4.8 + random.uniform(-0.1, 0.1)  # 4.7-4.9V
                current = 0.1 + random.uniform(-0.01, 0.01)  # 0.09-0.11A
            else:
                voltage = 0.0
                current = 0.0
            
            # 更新点位状态
            point.voltage = voltage
            point.current = current
            
            return {
                'point_id': point_id,
                'voltage': voltage,
                'current': current,
                'is_conductive': is_conductive,
                'timestamp': time.time()
            }
    
    def _check_conductivity_optimized(self, point_id: int) -> bool:
        """优化版导通检查"""
        # 使用缓存的连接矩阵
        matrix = self.get_connection_matrix()
        
        # 检查是否有活跃的电源
        for source_id, connections in matrix.items():
            if (source_id in self.test_points and 
                self.test_points[source_id].relay_state == RelayState.ON and
                point_id in connections):
                return True
        
        return False
    
    @cached(ttl=10)
    def get_system_info_optimized(self) -> Dict[str, Any]:
        """优化版系统信息获取"""
        timer = get_timer()
        
        with timer.time_step("get_system_info", {}):
            # 统计活跃点位
            active_points = sum(1 for p in self.test_points.values() if p.is_connected)
            
            # 统计继电器状态
            on_relays = sum(1 for p in self.test_points.values() if p.relay_state == RelayState.ON)
            
            return {
                'total_points': self.total_points,
                'active_points': active_points,
                'on_relays': on_relays,
                'total_connections': len(self.connections),
                'test_history_count': len(self.test_history),
                'relay_switch_time': self.relay_switch_time,
                'timestamp': time.time()
            }
    
    def reset_system_optimized(self, total_points: Optional[int] = None, 
                              conductivity_distribution: Optional[Dict[int, int]] = None):
        """优化版系统重置"""
        timer = get_timer()
        
        with timer.time_step("reset_system", {"total_points": total_points}):
            # 清空缓存
            self.cache.clear()
            
            # 更新参数
            if total_points is not None:
                self.total_points = total_points
            
            # 重新初始化
            self._initialize_system()
            
            logger.info(f"系统重置完成，总点位: {self.total_points}")
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """获取性能统计"""
        return {
            'cache_stats': self.cache.get_stats(),
            'connection_matrix_cached': self._connection_matrix is not None,
            'last_matrix_update': self._last_matrix_update,
            'total_test_points': len(self.test_points),
            'total_connections': len(self.connections),
            'test_history_size': len(self.test_history)
        }
