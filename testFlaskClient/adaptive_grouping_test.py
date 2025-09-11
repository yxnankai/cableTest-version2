#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自适应分组测试实现
实现逐步递减的分组比例：30% → 20% → 10%
确保各分组中点位关系尽可能未知
"""

import time
import random
import json
from typing import List, Dict, Set, Tuple, Any
from collections import defaultdict
import requests
from adaptive_grouping_config import get_config

class AdaptiveGroupingTester:
    """自适应分组测试器"""
    
    def __init__(self, config: dict, base_url: str = "http://localhost:5000"):
        self.config = config
        self.base_url = base_url
        self.total_points = config['total_points']
        
        # 动态获取分组比例配置
        if 'test_execution' in config and 'phase_switch_criteria' in config['test_execution']:
            # 从新的配置结构中提取分组比例
            phase_thresholds = config['test_execution']['phase_switch_criteria']['phase_thresholds']
            self.group_ratios = []
            # 动态读取所有非binary_search的阶段
            for phase_name, threshold in phase_thresholds.items():
                if phase_name != 'binary_search':
                    self.group_ratios.append(threshold['group_ratio'])
        else:
            # 兼容旧的配置结构
            self.group_ratios = config['adaptive_grouping']['group_ratios']
        
        # 关系矩阵状态
        self.relationship_matrix = [[None] * self.total_points for _ in range(self.total_points)]
        self.known_relations = set()  # 已知关系集合（本地备用）
        self.unknown_relations = set()  # 未知关系集合（本地备用）
        
        # 测试状态
        self.current_phase = 0  # 当前测试阶段
        self.phase_test_counts = [0] * len(self.group_ratios)  # 每阶段测试次数
        self.total_tests = 0  # 总测试次数
        
        # 循环检测
        self.last_strategy_ratio = None
        self.strategy_repeat_count = 0
        self.max_strategy_repeats = 10  # 最大重复次数
        
        # 分组历史
        self.group_history = []
        self.power_source_usage = defaultdict(int)  # 电源点位使用次数
        
        # 初始化所有点位的使用次数为0
        for i in range(self.total_points):
            self.power_source_usage[i] = 0
        
        # 性能统计
        self.performance_stats = {
            'total_relay_operations': 0,
            'total_test_time': 0,
            'phase_efficiency': [],
            'group_quality_scores': []
        }
        
        # 继电器状态管理
        self.relay_states = set()  # 当前开启的继电器集合
        self.last_power_source = None  # 上次的电源点位
        self.last_test_points = set()  # 上次的测试点位集合
        
        # 测试历史跟踪 - 避免重复测试
        self.tested_combinations = set()  # 已测试的点位组合
        self.tested_power_sources = set()  # 已作为电源测试过的点位
        
        print(f"🚀 初始化自适应分组测试器")
        print(f"总点位: {self.total_points}")
        print(f"分组比例: {self.group_ratios}")
        print(f"当前阶段: {self.current_phase + 1} ({self.get_current_group_ratio():.1%})")
    
    def initialize_relationship_matrix(self):
        """初始化关系矩阵"""
        print(f"📊 初始化关系矩阵...")
        
        # 初始化关系矩阵
        self.relationship_matrix = [[0 for _ in range(self.total_points)] for _ in range(self.total_points)]
        
        # 初始化已知和未知关系集合
        self.known_relations = set()
        self.unknown_relations = set()
        
        # 初始化所有可能的点位关系为未知
        for i in range(self.total_points):
            for j in range(self.total_points):
                if i != j:  # 排除自己到自己的关系
                    self.unknown_relations.add((i, j))
        
        print(f"✅ 关系矩阵初始化完成")
        print(f"已知关系: {len(self.known_relations)}")
        print(f"未知关系: {len(self.unknown_relations)}")
        
        # 验证初始化结果
        total_possible_relations = self.total_points * (self.total_points - 1)
        print(f"总可能关系数: {total_possible_relations}")
        print(f"初始化验证: {len(self.unknown_relations)} == {total_possible_relations} ? {len(self.unknown_relations) == total_possible_relations}")
    
    def get_current_group_size(self) -> int:
        """获取当前阶段的分组大小"""
        ratio = self.get_current_group_ratio()
        group_size = max(
            self.config['adaptive_grouping']['min_group_size'],
            min(
                int(self.total_points * ratio),
                self.config['adaptive_grouping']['max_group_size']
            )
        )
        return group_size
    
    def calculate_relation_unknown_score(self, points: List[int]) -> float:
        """计算点位组合的关系未知性得分"""
        if len(points) < 2:
            return 0.0
        
        total_relations = len(points) * (len(points) - 1)
        unknown_count = 0
        
        for i in points:
            for j in points:
                if i != j:
                    if (i, j) in self.unknown_relations:
                        unknown_count += 1
        
        return unknown_count / total_relations
    
    def select_optimal_power_source(self, test_points: List[int]) -> int:
        """选择最优的电源点位"""
        # 如果power_source_usage为空，初始化所有点位为0
        if not self.power_source_usage:
            for point in test_points:
                self.power_source_usage[point] = 0
        
        # 优先选择使用次数少的点位
        min_usage = min(self.power_source_usage.values())
        candidates = [p for p in test_points if self.power_source_usage[p] == min_usage]
        
        if len(candidates) > 1:
            # 如果多个候选，选择关系未知性最高的
            best_source = candidates[0]
            best_score = self.calculate_relation_unknown_score([best_source] + test_points)
            
            for candidate in candidates[1:]:
                score = self.calculate_relation_unknown_score([candidate] + test_points)
                if score > best_score:
                    best_score = score
                    best_source = candidate
            
            return best_source
        
        return candidates[0]
    
    def create_optimal_group(self, group_size: int) -> Tuple[List[int], int]:
        """创建最优测试分组"""
        if group_size <= 0:
            return [], -1
        
        # 🔧 重要：从服务端获取关系矩阵，确保数据一致性
        server_matrix = self.get_server_relationship_matrix()
        
        # 获取所有可用的点位
        available_points = list(range(self.total_points))
        
        # 优先选择关系未知的点位
        unknown_points = []
        known_points = []
        
        for point in available_points:
            # 基于服务端矩阵计算该点位的关系未知数量
            unknown_count = 0
            for other_point in range(self.total_points):
                if point != other_point and server_matrix[point][other_point] == 0:  # 0表示未知关系
                    unknown_count += 1
            
            if unknown_count > 0:
                unknown_points.append((point, unknown_count))
            else:
                known_points.append(point)
        
        # 按未知关系数量排序，优先选择未知关系多的点位
        unknown_points.sort(key=lambda x: x[1], reverse=True)
        
        print(f"🔍 点位分析:")
        print(f"  关系未知的点位: {len(unknown_points)} 个")
        print(f"  关系已知的点位: {len(known_points)} 个")
        print(f"  已测试电源点位: {len(self.tested_power_sources)} 个")
        print(f"  已测试组合数: {len(self.tested_combinations)} 个")
        
        # 优先从关系未知的点位中选择
        selected_points = []
        power_source = -1
        
        if len(unknown_points) >= group_size:
            # 如果未知关系点位足够，全部从其中选择
            print(f"✅ 从关系未知点位中选择 {group_size} 个点位")
            selected_points = [point for point, _ in unknown_points[:group_size]]
            
            # 选择使用次数最少的点位作为电源
            power_source = self.select_optimal_power_source(selected_points)
            
        elif len(unknown_points) > 0:
            # 如果未知关系点位不够，先选择所有未知关系点位，再从已知关系点位补充
            print(f"⚠️  关系未知点位不足，需要补充 {group_size - len(unknown_points)} 个已知关系点位")
            
            # 先选择所有未知关系点位
            selected_points = [point for point, _ in unknown_points]
            
            # 从已知关系点位中补充，优先选择关系较少的点位
            remaining_needed = group_size - len(selected_points)
            
            # 基于服务端矩阵计算每个已知关系点位的已知关系数量
            known_point_scores = []
            for point in known_points:
                known_count = 0
                for other_point in range(self.total_points):
                    if point != other_point and server_matrix[point][other_point] != 0:  # 非0表示已知关系（1或-1）
                        known_count += 1
                known_point_scores.append((point, known_count))
            
            # 按已知关系数量排序，优先选择已知关系少的点位（这样可能还有更多未知关系）
            known_point_scores.sort(key=lambda x: x[1])
            
            # 补充点位
            for point, _ in known_point_scores[:remaining_needed]:
                selected_points.append(point)
            
            # 选择使用次数最少的点位作为电源
            power_source = self.select_optimal_power_source(selected_points)
            
        else:
            # 如果完全没有未知关系点位，从已知关系点位中选择
            print(f"⚠️  所有点位关系都已确认，从已知关系点位中选择")
            
            # 基于服务端矩阵计算每个点位的已知关系数量，优先选择关系较少的点位
            point_scores = []
            for point in available_points:
                known_count = 0
                for other_point in range(self.total_points):
                    if point != other_point and server_matrix[point][other_point] != 0:  # 非0表示已知关系（1或-1）
                        known_count += 1
                point_scores.append((point, known_count))
            
            # 按已知关系数量排序，优先选择已知关系少的点位
            point_scores.sort(key=lambda x: x[1])
            selected_points = [point for point, _ in point_scores[:group_size]]
            
            # 选择使用次数最少的点位作为电源
            power_source = self.select_optimal_power_source(selected_points)
        
        # 检查是否已经测试过这个组合
        if selected_points:
            # 创建组合标识符（排序后确保一致性）
            combination_key = tuple(sorted(selected_points))
            
            if combination_key in self.tested_combinations:
                print(f"⚠️  警告: 点位组合 {combination_key} 已经测试过，尝试创建新的组合")
                
                # 尝试创建不同的组合
                alternative_group = self.create_alternative_group(group_size, combination_key)
                if alternative_group:
                    selected_points, power_source = alternative_group
                    print(f"✅ 创建了替代分组: {selected_points}")
                else:
                    print(f"❌ 无法创建替代分组，跳过此分组")
                    return [], -1
        
        # 验证分组质量
        if selected_points:
            # 计算分组内的未知关系比例
            total_relations = len(selected_points) * (len(selected_points) - 1)
            unknown_relations_in_group = 0
            
            for i, point1 in enumerate(selected_points):
                for j, point2 in enumerate(selected_points):
                    if i != j and (point1, point2) in self.unknown_relations:
                        unknown_relations_in_group += 1
            
            unknown_ratio = unknown_relations_in_group / total_relations if total_relations > 0 else 0
            
            print(f"✅ 分组创建完成")
            print(f"  分组点位: {selected_points}")
            print(f"  电源点位: {power_source}")
            print(f"  组内未知关系比例: {unknown_ratio:.1%} ({unknown_relations_in_group}/{total_relations})")
            
            # 检查是否满足未知关系要求
            min_unknown_ratio = self.config['adaptive_grouping']['min_unknown_relations_per_group']
            if unknown_ratio < (1 - min_unknown_ratio):
                print(f"⚠️  警告: 组内未知关系比例过低 ({unknown_ratio:.1%} < {1-min_unknown_ratio:.1%})")
        
        return selected_points, power_source
    
    def create_alternative_group(self, group_size: int, exclude_combination: tuple) -> Tuple[List[int], int]:
        """创建替代分组，避免重复"""
        # 获取所有点位
        all_points = list(range(self.total_points))
        
        # 排除已经测试过的组合中的点位
        available_points = [p for p in all_points if p not in exclude_combination]
        
        if len(available_points) < group_size:
            print(f"⚠️  可用点位不足 ({len(available_points)} < {group_size})")
            return [], -1
        
        # 随机选择点位
        import random
        selected_points = random.sample(available_points, group_size)
        
        # 选择电源点位
        power_source = self.select_optimal_power_source(selected_points)
        
        return selected_points, power_source
    
    def run_single_test(self, test_points: List[int], power_source: int, strategy_name: str = None) -> Dict[str, Any]:
        """运行单次测试"""
        try:
            payload = {
                "power_source": power_source,
                "test_points": test_points
            }
            
            # 如果提供了策略名称，添加到payload中
            if strategy_name:
                payload["strategy"] = strategy_name
            else:
                # 如果没有提供策略名称，使用当前策略名称
                current_strategy = self.get_current_strategy_name()
                payload["strategy"] = current_strategy
            
            print(f"🔍 发送测试请求: {payload}")
            
            response = requests.post(f"{self.base_url}/api/experiment", json=payload, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                print(f"🔍 API响应: {result}")
                
                if result.get('success'):
                    return result['data']
                else:
                    print(f"❌ 测试执行失败: {result.get('error', '未知错误')}")
                    return None
            else:
                print(f"❌ HTTP请求失败: {response.status_code}")
                print(f"响应内容: {response.text[:200]}")
                return None
                
        except Exception as e:
            print(f"❌ 测试异常: {str(e)}")
            import traceback
            traceback.print_exc()
            return None
    
    def update_relationship_matrix(self, test_result: Dict[str, Any]):
        """更新关系矩阵"""
        print(f"🔍 调试: test_result 结构: {test_result}")
        print(f"🔍 调试: test_result 键: {list(test_result.keys())}")
        
        # 安全地获取测试结果数据 - 处理嵌套结构
        try:
            # 检查是否有嵌套的 test_result 结构
            if 'test_result' in test_result:
                # 嵌套结构：test_result['test_result']['power_source']
                nested_result = test_result['test_result']
                power_source = nested_result.get('power_source')
                active_points = nested_result.get('test_points', [])  # 注意：API 返回的是 test_points
                detected_connections = nested_result.get('connections', [])  # 注意：API 返回的是 connections
            else:
                # 直接结构：test_result['power_source']
                power_source = test_result.get('power_source')
                active_points = test_result.get('active_points', [])
                detected_connections = test_result.get('detected_connections', [])
            
            if power_source is None:
                print(f"❌ 错误: test_result 中缺少 'power_source' 键")
                print(f"可用的键: {list(test_result.keys())}")
                if 'test_result' in test_result:
                    print(f"嵌套结构键: {list(test_result['test_result'].keys())}")
                return
            
            print(f"✅ 成功获取测试数据: power_source={power_source}, active_points={active_points}")
            
        except Exception as e:
            print(f"❌ 获取测试数据失败: {e}")
            return
        
        # 更新已知关系
        for connection in detected_connections:
            try:
                source = connection.get('source_point')
                targets = connection.get('target_points', [])
                
                if source is None or not targets:
                    continue
                
                for target in targets:
                    # 标记为已知关系
                    self.relationship_matrix[source][target] = 1
                    self.relationship_matrix[target][source] = 1
                    
                    # 更新集合
                    if (source, target) in self.unknown_relations:
                        self.unknown_relations.remove((source, target))
                    if (target, source) in self.unknown_relations:
                        self.unknown_relations.remove((target, source))
                    
                    self.known_relations.add((source, target))
                    self.known_relations.add((target, source))
                    
            except Exception as e:
                print(f"⚠️  处理连接关系时出错: {e}")
                continue
        
        # 更新电源点位使用次数
        self.power_source_usage[power_source] += 1
        
        # 记录分组历史
        group_info = {
            'phase': self.current_phase,
            'group_size': len(active_points),
            'power_source': power_source,
            'test_points': active_points,
            'detected_connections': len(detected_connections),
            'relay_operations': test_result.get('relay_operations', 0),
            'test_duration': test_result.get('test_duration', 0),
            'timestamp': time.time()
        }
        self.group_history.append(group_info)
    
    def calculate_relay_operations(self, new_power_source: int, new_test_points: List[int]) -> int:
        """计算继电器操作次数 - 基于状态变化"""
        if self.last_power_source is None:
            # 第一次测试，需要开启所有继电器
            # 通电点位 + 测试点位 = 所有需要打开的继电器
            operations = 1 + len(new_test_points)
            print(f"🔌 第一次测试，需要开启 {operations} 个继电器")
            return operations
        
        # 计算新的继电器状态集合（所有需要打开的继电器）
        new_relay_states = {new_power_source} | set(new_test_points)
        
        # 🔧 重要：如果继电器状态完全相同，切换次数为0
        if new_relay_states == self.relay_states:
            print(f"🔌 继电器状态完全相同，切换次数: 0")
            print(f"  当前继电器状态: {sorted(self.relay_states)} (打开的点位)")
            print(f"  新继电器状态: {sorted(new_relay_states)} (需要打开的点位)")
            return 0
        
        # 🔧 重要：如果只是电源点位改变，测试点位集合基本相同，切换次数应该很少
        # 计算测试点位的差异
        test_points_diff = set(new_test_points).symmetric_difference(set(self.last_test_points))
        if len(test_points_diff) <= 1:  # 最多1个测试点位不同
            print(f"🔌 测试点位基本相同，主要是电源点位切换")
            print(f"  测试点位差异: {sorted(test_points_diff)}")
            # 🔧 重要：如果测试点位完全相同，说明只是电源点位改变
            # 由于通电点位和测试点位的继电器都是ON状态，所以无需切换
            if len(test_points_diff) == 0:
                print(f"🔌 测试点位完全相同，继电器操作次数: 0 (电源切换，但继电器状态无变化)")
                return 0
            
            # 🔧 重要：如果测试点位差异很小（只有1个），且继电器状态集合基本相同，也返回0
            # 因为通电点位和测试点位的继电器都是ON状态，只是位置交换
            if len(test_points_diff) == 1:
                # 检查是否只是电源点位和测试点位的交换
                diff_point = list(test_points_diff)[0]
                if (diff_point == self.last_power_source and new_power_source in self.last_test_points):
                    print(f"🔌 只是电源点位和测试点位交换，继电器状态无变化，操作次数: 0")
                    return 0
        
        # 🔧 重要：继电器状态有变化，但需要仔细分析
        # 通电点位和测试点位的继电器都是 ON 状态
        # 不参加实验的点位继电器是 OFF 状态
        # 切换次数 = 需要从 OFF 变 ON 的继电器数量
        
        # 计算需要新开启的继电器（之前关闭，现在需要打开）
        to_open = new_relay_states - self.relay_states
        
        # 计算需要关闭的继电器（之前打开，现在不需要）
        to_close = self.relay_states - new_relay_states
        
        # 每个状态变化的继电器都需要一次切换操作
        operations = len(to_open) + len(to_close)
        
        print(f"🔌 继电器状态变化分析:")
        print(f"  上次继电器状态: {sorted(self.relay_states)} (打开的点位)")
        print(f"  本次继电器状态: {sorted(new_relay_states)} (需要打开的点位)")
        print(f"  需要关闭: {sorted(to_close)} (之前打开，现在关闭)")
        print(f"  需要开启: {sorted(to_open)} (之前关闭，现在打开)")
        print(f"  继电器切换次数: {operations}")
        
        # 🔧 重要：如果只是更换电源点位，大部分继电器状态应该相同
        # 这种情况下切换次数应该很少
        if len(to_open) + len(to_close) <= 2:
            print(f"🔌 继电器状态变化很小，主要是电源点位切换")
        
        return operations
    
    def update_relay_states(self, power_source: int, test_points: List[int]):
        """更新继电器状态"""
        # 更新当前继电器状态
        self.relay_states = {power_source} | set(test_points)
        self.last_power_source = power_source
        self.last_test_points = set(test_points)
        
        print(f"🔌 继电器状态更新:")
        print(f"  电源点位: {power_source}")
        print(f"  测试点位: {test_points}")
        print(f"  开启继电器数量: {len(self.relay_states)}")
    
    def get_power_on_count(self) -> int:
        """获取通电次数 - 始终为1，表示从通电点位进行通电"""
        return 1
    
    def should_switch_phase(self) -> bool:
        """判断是否应该切换测试阶段 - 基于未知关系比例"""
        current_phase_tests = self.phase_test_counts[self.current_phase]
        min_tests = self.config['test_execution']['phase_switch_criteria']['min_tests_per_phase']
        
        # 检查最少测试次数要求
        if current_phase_tests < min_tests:
            return False
        
        # 🔧 重要：优先使用服务端数据计算未知关系比例，确保与状态显示一致
        try:
            response = requests.get(f"{self.base_url}/api/system/info")
            if response.status_code == 200:
                system_info = response.json()
                if system_info.get('success'):
                    server_confirmed_count = system_info.get('confirmed_points_count', 0)
                    total_possible_relations = self.total_points * (self.total_points - 1)
                    unknown_ratio = (total_possible_relations - server_confirmed_count) / total_possible_relations
                    
                    # 🔧 重要：根据配置的策略阈值确定目标策略
                    # _get_strategy_by_unknown_ratio返回元组(ratio, name)
                    target_ratio_tuple = self._get_strategy_by_unknown_ratio(unknown_ratio)
                    
                    # 正确处理返回的元组
                    if isinstance(target_ratio_tuple, tuple) and len(target_ratio_tuple) >= 1:
                        target_ratio_value = target_ratio_tuple[0]
                        target_strategy = target_ratio_tuple[1] if len(target_ratio_tuple) > 1 else self.get_strategy_name_by_ratio(target_ratio_value)
                    else:
                        target_ratio_value = target_ratio_tuple
                        target_strategy = self.get_strategy_name_by_ratio(target_ratio_value)
                    
                    # 获取当前策略
                    current_ratio = self.get_current_group_ratio()
                    current_strategy = self.get_strategy_name_by_ratio(current_ratio)
                    
                    # 如果目标策略与当前策略不同，需要切换
                    if current_strategy != target_strategy:
                        print(f"🔄 未知关系比例: {unknown_ratio:.1%}")
                        print(f"当前策略: {current_strategy} ({current_ratio:.1%})")
                        print(f"目标策略: {target_strategy} ({target_ratio_value:.1%})")
                        print(f"准备切换策略")
                        return True
                    
                    return False
        except Exception as e:
            print(f"⚠️  获取服务端数据失败，使用本地数据: {e}")
            import traceback
            traceback.print_exc()
        
        # 如果服务端获取失败，使用本地数据作为备用
        total_possible_relations = self.total_points * (self.total_points - 1)
        unknown_ratio = len(self.unknown_relations) / total_possible_relations
        
        # 🔧 重要：根据配置的策略阈值确定目标策略
        try:
            target_ratio_tuple = self._get_strategy_by_unknown_ratio(unknown_ratio)
        except Exception as e:
            print(f"⚠️  策略选择失败: {e}")
            import traceback
            traceback.print_exc()
            target_ratio_tuple = (0.1, "unknown")  # 返回默认值
        
        # 处理target_ratio可能是元组的情况
        print(f"🔍 调试 should_switch_phase: target_ratio_tuple 类型={type(target_ratio_tuple)}, 值={target_ratio_tuple}")
        
        if isinstance(target_ratio_tuple, tuple) and len(target_ratio_tuple) >= 1:
            print(f"🔍 检测到元组，提取元素: {target_ratio_tuple}")
            target_ratio_value = target_ratio_tuple[0]
            target_strategy = target_ratio_tuple[1] if len(target_ratio_tuple) > 1 else self.get_strategy_name_by_ratio(target_ratio_value)
        else:
            print(f"🔍 非元组类型，调用 get_strategy_name_by_ratio")
            target_ratio_value = target_ratio_tuple
            target_strategy = self.get_strategy_name_by_ratio(target_ratio_value)
        
        # 获取当前策略
        current_ratio = self.get_current_group_ratio()
        current_strategy = self.get_strategy_name_by_ratio(current_ratio)
        
        # 如果目标策略与当前策略不同，需要切换
        if current_strategy != target_strategy:
            print(f"🔄 未知关系比例: {unknown_ratio:.1%}")
            print(f"当前策略: {current_strategy} ({current_ratio:.1%})")
            print(f"目标策略: {target_strategy} ({target_ratio_value:.1%})")
            print(f"准备切换策略")
            return True
        
        return False
    
    def get_strategy_name_by_ratio(self, ratio) -> str:
        """根据分组比例获取策略名称"""
        print(f"🔍 调试 get_strategy_name_by_ratio: 输入类型={type(ratio)}, 值={ratio}")
        
        # 处理元组类型
        if isinstance(ratio, tuple):
            print(f"⚠️  检测到元组类型，提取第一个元素: {ratio[0] if ratio else 0.0}")
            ratio = ratio[0] if ratio else 0.0
        
        # 确保是数值类型
        if not isinstance(ratio, (int, float)):
            print(f"⚠️  非数值类型，尝试转换: {ratio}")
            try:
                ratio = float(ratio)
            except (ValueError, TypeError):
                print(f"❌ 无法转换为数值，使用默认值 0.0")
                ratio = 0.0
        
        print(f"🔍 处理后的比例: {ratio} (类型: {type(ratio)})")
        
        if ratio >= 0.5:
            return "adaptive_50"
        elif ratio >= 0.3:
            return "adaptive_30"
        elif ratio >= 0.1:
            return "adaptive_10"
        else:
            return "binary_search"
    
    def get_current_phase_name(self, unknown_ratio: float) -> str:
        """根据当前分组比例确定当前阶段名称"""
        # 使用当前阶段索引来确定阶段名称，避免循环依赖
        phase_names = ['phase_1', 'phase_2', 'phase_3']
        if self.current_phase < len(phase_names):
            return phase_names[self.current_phase]
        return f"phase_{self.current_phase + 1}"
    
    def get_target_phase_name(self, unknown_ratio: float) -> str:
        """根据未知关系比例确定目标阶段名称"""
        phase_thresholds = self.config['test_execution']['phase_switch_criteria']['phase_thresholds']
        
        for phase_name, threshold in phase_thresholds.items():
            min_ratio = threshold['min_unknown_ratio']
            max_ratio = threshold['max_unknown_ratio']
            
            if min_ratio <= unknown_ratio <= max_ratio:
                return phase_name
        
        # 如果都不匹配，返回默认阶段
        return 'unknown_phase'
    
    def switch_to_next_phase(self):
        """切换到下一个测试阶段 - 基于未知关系比例"""
        # 🔧 重要：优先使用服务端数据计算未知关系比例，确保与状态显示一致
        try:
            response = requests.get(f"{self.base_url}/api/system/info")
            if response.status_code == 200:
                system_info = response.json()
                if system_info.get('success'):
                    server_confirmed_count = system_info.get('confirmed_points_count', 0)
                    total_possible_relations = self.total_points * (self.total_points - 1)
                    unknown_ratio = (total_possible_relations - server_confirmed_count) / total_possible_relations
                    
                    # 🔧 重要：根据配置的策略阈值确定目标策略
                    # _get_strategy_by_unknown_ratio返回元组(ratio, name)
                    target_ratio_tuple = self._get_strategy_by_unknown_ratio(unknown_ratio)
                    
                    # 正确处理返回的元组
                    if isinstance(target_ratio_tuple, tuple) and len(target_ratio_tuple) >= 1:
                        target_ratio_value = target_ratio_tuple[0]
                        target_strategy = target_ratio_tuple[1] if len(target_ratio_tuple) > 1 else self.get_strategy_name_by_ratio(target_ratio_value)
                    else:
                        target_ratio_value = target_ratio_tuple
                        target_strategy = self.get_strategy_name_by_ratio(target_ratio_value)
                    
                    # 找到对应的阶段索引
                    target_phase_index = None
                    for i, ratio in enumerate(self.group_ratios):
                        if abs(ratio - target_ratio_value) < 0.01:  # 允许小的浮点误差
                            target_phase_index = i
                            break
                    
                    if target_phase_index is None:
                        print(f"⚠️ 无法找到匹配的阶段索引，使用策略配置的比例")
                        # 即使没有找到匹配的阶段索引，也使用策略配置的比例
                        self.current_phase = min(len(self.group_ratios) - 1, max(0, int((1 - target_ratio_value) * len(self.group_ratios))))
                    
                    # 切换到目标阶段
                    self.current_phase = target_phase_index
                    new_ratio = self.get_current_group_ratio()
                    
                    print(f"🔄 切换到测试策略: {target_strategy}")
                    print(f"新的分组比例: {new_ratio:.1%}")
                    print(f"新的分组大小: {self.get_current_group_size()}")
                    print(f"未知关系比例: {unknown_ratio:.1%}")
                    
                    return True
        except Exception as e:
            print(f"⚠️  获取服务端数据失败，使用本地数据: {e}")
        
        # 如果服务端获取失败，使用本地数据作为备用
        total_possible_relations = self.total_points * (self.total_points - 1)
        unknown_ratio = len(self.unknown_relations) / total_possible_relations
        
        # 🔧 重要：根据配置的策略阈值确定目标策略
        # _get_strategy_by_unknown_ratio返回元组(ratio, name)
        target_ratio_tuple = self._get_strategy_by_unknown_ratio(unknown_ratio)
        
        # 正确处理返回的元组
        if isinstance(target_ratio_tuple, tuple) and len(target_ratio_tuple) >= 1:
            target_ratio_value = target_ratio_tuple[0]
            target_strategy = target_ratio_tuple[1] if len(target_ratio_tuple) > 1 else self.get_strategy_name_by_ratio(target_ratio_value)
        else:
            target_ratio_value = target_ratio_tuple
            target_strategy = self.get_strategy_name_by_ratio(target_ratio_value)
        
        # 找到对应的阶段索引
        target_phase_index = None
        for i, ratio in enumerate(self.group_ratios):
            if abs(ratio - target_ratio_value) < 0.01:  # 允许小的浮点误差
                target_phase_index = i
                break
        
        if target_phase_index is None:
            print(f"⚠️ 无法找到匹配的阶段索引，使用策略配置的比例")
            # 即使没有找到匹配的阶段索引，也使用策略配置的比例
            self.current_phase = min(len(self.group_ratios) - 1, max(0, int((1 - target_ratio_value) * len(self.group_ratios))))
        
        # 切换到目标阶段
        self.current_phase = target_phase_index
        new_ratio = self.get_current_group_ratio()
        
        print(f"🔄 切换到测试策略: {target_strategy}")
        print(f"新的分组比例: {new_ratio:.1%}")
        print(f"新的分组大小: {self.get_current_group_size()}")
        print(f"未知关系比例: {unknown_ratio:.1%}")
        
        return True
    
    def get_current_group_ratio(self) -> float:
        """获取当前阶段的分组比例 - 基于未知关系比例动态计算"""
        strategy_ratio, _ = self._get_strategy_info()
        
        # 处理 strategy_ratio 可能是元组的情况
        if isinstance(strategy_ratio, tuple):
            print(f"🔍 调试 get_current_group_ratio: 检测到元组类型，提取第一个元素: {strategy_ratio}")
            strategy_ratio = strategy_ratio[0] if strategy_ratio else 0.0
        
        # 确保是数值类型
        if not isinstance(strategy_ratio, (int, float)):
            print(f"🔍 调试 get_current_group_ratio: 非数值类型，尝试转换: {strategy_ratio}")
            try:
                strategy_ratio = float(strategy_ratio)
            except (ValueError, TypeError):
                print(f"❌ 无法转换为数值，使用默认值 0.0")
                strategy_ratio = 0.0
        
        print(f"🔍 调试 get_current_group_ratio: 返回比例={strategy_ratio} (类型: {type(strategy_ratio)})")
        return strategy_ratio
    
    def get_current_strategy_name(self) -> str:
        """获取当前策略名称"""
        _, strategy_name = self._get_strategy_info()
        
        # 处理 strategy_name 可能是元组的情况
        if isinstance(strategy_name, tuple):
            print(f"🔍 调试 get_current_strategy_name: 检测到元组类型，提取第一个元素: {strategy_name}")
            strategy_name = strategy_name[0] if strategy_name else "默认策略"
        
        # 确保是字符串类型
        if not isinstance(strategy_name, str):
            print(f"🔍 调试 get_current_strategy_name: 非字符串类型，尝试转换: {strategy_name}")
            try:
                strategy_name = str(strategy_name)
            except (ValueError, TypeError):
                print(f"❌ 无法转换为字符串，使用默认值")
                strategy_name = "默认策略"
        
        print(f"🔍 调试 get_current_strategy_name: 返回策略名称={strategy_name} (类型: {type(strategy_name)})")
        return strategy_name
    
    def _get_strategy_info(self) -> tuple:
        """获取策略信息 - 返回(策略比例, 策略名称)"""
        # 🔧 重要：优先使用服务端数据计算未知关系比例，确保与状态显示一致
        try:
            response = requests.get(f"{self.base_url}/api/system/info")
            if response.status_code == 200:
                system_info = response.json()
                if system_info.get('success'):
                    server_confirmed_count = system_info.get('confirmed_points_count', 0)
                    total_possible_relations = self.total_points * (self.total_points - 1)
                    unknown_ratio = (total_possible_relations - server_confirmed_count) / total_possible_relations
                    
                    # 🔧 重要：根据配置的策略阈值动态选择策略
                    strategy_ratio, strategy_name = self._get_strategy_by_unknown_ratio(unknown_ratio)
                    
                    print(f"🔍 动态策略选择 (服务端数据):")
                    print(f"  未知关系比例: {unknown_ratio:.1%}")
                    print(f"  选择策略: {strategy_name}")
                    print(f"  分组比例: {strategy_ratio:.1%}")
                    
                    return strategy_ratio, strategy_name
        except Exception as e:
            print(f"⚠️  获取服务端数据失败，使用本地数据: {e}")
        
        # 如果服务端获取失败，使用本地数据作为备用
        total_possible_relations = self.total_points * (self.total_points - 1)
        unknown_ratio = len(self.unknown_relations) / total_possible_relations
        
        # 🔧 重要：根据配置的策略阈值动态选择策略
        strategy_ratio, strategy_name = self._get_strategy_by_unknown_ratio(unknown_ratio)
        
        print(f"🔍 动态策略选择 (本地数据):")
        print(f"  未知关系比例: {unknown_ratio:.1%}")
        print(f"  选择策略: {strategy_name}")
        print(f"  分组比例: {strategy_ratio:.1%}")
        
        return strategy_ratio, strategy_name
    
    def _get_strategy_by_unknown_ratio(self, unknown_ratio: float) -> tuple:
        """根据未知关系比例和配置的策略阈值选择策略，返回(策略比例, 策略名称)"""
        # 确保 unknown_ratio 是有效的数值
        if not isinstance(unknown_ratio, (int, float)) or unknown_ratio < 0 or unknown_ratio > 1:
            print(f"⚠️  无效的未知关系比例: {unknown_ratio}，使用默认值 1.0")
            unknown_ratio = 1.0
        
        try:
            # 获取策略配置
            if 'test_execution' in self.config and 'phase_switch_criteria' in self.config['test_execution']:
                phase_thresholds = self.config['test_execution']['phase_switch_criteria']['phase_thresholds']
                
                print(f"🔍 当前配置的策略阈值: {phase_thresholds}")
                print(f"🔍 当前未知关系比例: {unknown_ratio:.1%}")
                
                # 检查所有阶段，包括二分法策略
                # 首先提取二分法策略进行特殊处理
                binary_threshold = None
                regular_phases = []
                
                for phase_name, threshold in phase_thresholds.items():
                    if phase_name == 'binary_search' or (threshold.get('strategy_type') == 'binary_search' or threshold.get('strategy_name') == '二分法策略'):
                        binary_threshold = threshold
                    else:
                        regular_phases.append((phase_name, threshold))
                
                # 先检查普通阶段
                for phase_name, threshold in regular_phases:
                    # 使用 .get() 方法获取配置值，避免 KeyError
                    min_ratio = threshold.get('min_unknown_ratio', 0.0)
                    max_ratio = threshold.get('max_unknown_ratio', 1.0)
                    
                    # 确保 min_ratio 和 max_ratio 是数值类型
                    if isinstance(min_ratio, (list, tuple)):
                        min_ratio = min_ratio[0] if min_ratio else 0.0
                    elif not isinstance(min_ratio, (int, float)):
                        min_ratio = float(min_ratio) if min_ratio else 0.0
                    
                    if isinstance(max_ratio, (list, tuple)):
                        max_ratio = max_ratio[0] if max_ratio else 1.0
                    elif not isinstance(max_ratio, (int, float)):
                        max_ratio = float(max_ratio) if max_ratio else 1.0
                    
                    print(f"  检查策略 {phase_name}: {min_ratio:.1%} <= {unknown_ratio:.1%} <= {max_ratio:.1%}")
                    
                    # 使用正确的范围检查
                    if min_ratio <= unknown_ratio <= max_ratio:
                        # 返回策略标识符而不是显示名称，用于前端正确映射显示名称
                        strategy_name = threshold.get('strategy_type', phase_name)
                        # 使用 .get() 方法获取 group_ratio，避免 KeyError
                        group_ratio = threshold.get('group_ratio', 0.1)
                        
                        # 确保 group_ratio 是浮点数
                        if isinstance(group_ratio, (list, tuple)):
                            group_ratio = group_ratio[0] if group_ratio else 0.1
                        elif not isinstance(group_ratio, (int, float)):
                            group_ratio = float(group_ratio) if group_ratio else 0.1
                        
                        print(f"  ✅ 匹配策略 {phase_name} ({strategy_name}): {min_ratio:.1%} <= {unknown_ratio:.1%} <= {max_ratio:.1%}")
                        print(f"  分组比例: {group_ratio:.1%}")
                        
                        return group_ratio, strategy_name
                    else:
                        print(f"  ❌ 不匹配策略 {phase_name}: {min_ratio:.1%} <= {unknown_ratio:.1%} <= {max_ratio:.1%}")
                
                # 然后检查二分法策略（当没有匹配到普通阶段时）
                if binary_threshold:
                    # 使用 .get() 方法获取配置值，避免 KeyError
                    min_ratio = binary_threshold.get('min_unknown_ratio', 0.0)
                    max_ratio = binary_threshold.get('max_unknown_ratio', 1.0)
                    
                    # 确保 min_ratio 和 max_ratio 是数值类型
                    if isinstance(min_ratio, (list, tuple)):
                        min_ratio = min_ratio[0] if min_ratio else 0.0
                    elif not isinstance(min_ratio, (int, float)):
                        min_ratio = float(min_ratio) if min_ratio else 0.0
                    
                    if isinstance(max_ratio, (list, tuple)):
                        max_ratio = max_ratio[0] if max_ratio else 1.0
                    elif not isinstance(max_ratio, (int, float)):
                        max_ratio = float(max_ratio) if max_ratio else 1.0
                    
                    print(f"  检查二分法策略: {min_ratio:.1%} <= {unknown_ratio:.1%} <= {max_ratio:.1%}")
                    
                    # 特殊处理：当未知关系比例低于某个阈值时直接使用二分法策略
                    # 这是为了确保当普通阶段都不匹配时（即未知关系较少时）能正确切换到二分法
                    binary_match = min_ratio <= unknown_ratio <= max_ratio or (unknown_ratio < max_ratio and max_ratio < 1.0)
                    
                    if binary_match:
                        # 返回策略标识符而不是显示名称，用于前端正确映射显示名称
                        strategy_name = binary_threshold.get('strategy_type', 'binary_search')
                        group_ratio = binary_threshold.get('group_ratio', 0.0)
                        
                        # 确保 group_ratio 是浮点数
                        if isinstance(group_ratio, (list, tuple)):
                            group_ratio = group_ratio[0] if group_ratio else 0.0
                        elif not isinstance(group_ratio, (int, float)):
                            group_ratio = float(group_ratio) if group_ratio else 0.0
                        
                        print(f"  ✅ 匹配二分法策略 ({strategy_name}): {min_ratio:.1%} <= {unknown_ratio:.1%} <= {max_ratio:.1%} 或未知关系比例低于阈值")
                        print(f"  分组比例: {group_ratio:.1%}")
                        
                        return group_ratio, strategy_name
                

        except Exception as e:
            print(f"⚠️  策略选择出错: {e}")
            import traceback
            traceback.print_exc()
            # 返回默认策略标识符，避免无限循环
            return 0.1, "unknown"
        
        # 未匹配到任何策略时，返回默认策略
        print(f"  ⚠️  没有匹配的策略，返回默认策略")
        return 0.1, "unknown"
    
    def create_point_clusters(self) -> List[List[int]]:
        """创建点位集群 - 按比例切割为不相交的集群，使用随机分组策略"""
        print(f"\n" + "="*60)
        print(f"🔍 创建点位集群（随机分组策略）...")
        print(f"="*60)
        
        # 获取当前阶段的分组比例 - 使用动态计算而不是固定数组
        current_ratio = self.get_current_group_ratio()
        cluster_size = int(self.total_points * current_ratio)
        
        print(f"🔍 调试 create_point_clusters: current_ratio={current_ratio}")
        print(f"🔍 调试 create_point_clusters: cluster_size={cluster_size}")
        
        print(f"当前阶段: {self.current_phase + 1}")
        print(f"分组比例: {current_ratio:.1%}")
        print(f"集群大小: {cluster_size}")
        
        # 🔧 重要：实现随机分组策略，避免前后两次分组过于接近
        clusters = self.create_random_clusters_with_unknown_priority(cluster_size)
        
        # 记录分组历史，避免重复
        self.record_cluster_history(clusters)
        
        print(f"集群创建完成，共 {len(clusters)} 个集群")
        for i, cluster in enumerate(clusters):
            print(f"  集群 {i+1}: {cluster} (大小: {len(cluster)})")
        
        return clusters
    
    def create_random_clusters_with_unknown_priority(self, cluster_size: int) -> List[List[int]]:
        """创建随机集群，优先考虑未知关系但增加随机性"""
        print(f"🎲 使用随机分组策略创建集群...")
        
        # 获取所有点位
        all_points = list(range(self.total_points))
        
        # 分析点位的未知关系数量
        point_unknown_counts = []
        for point in all_points:
            unknown_count = 0
            for other_point in range(self.total_points):
                if point != other_point and (point, other_point) in self.unknown_relations:
                    unknown_count += 1
            point_unknown_counts.append((point, unknown_count))
        
        print(f"点位分析:")
        print(f"  总点位数: {len(all_points)}")
        print(f"  集群大小: {cluster_size}")
        
        # 🔧 重要：随机分组策略
        # 1. 将点位按未知关系数量分为三个层级
        high_unknown = []  # 高未知关系（>70%）
        medium_unknown = []  # 中等未知关系（30%-70%）
        low_unknown = []  # 低未知关系（<30%）
        
        max_possible_unknown = self.total_points - 1
        
        for point, unknown_count in point_unknown_counts:
            unknown_ratio = unknown_count / max_possible_unknown if max_possible_unknown > 0 else 0
            
            if unknown_ratio > 0.7:
                high_unknown.append(point)
            elif unknown_ratio > 0.3:
                medium_unknown.append(point)
            else:
                low_unknown.append(point)
        
        print(f"  高未知关系点位: {len(high_unknown)} 个")
        print(f"  中等未知关系点位: {len(medium_unknown)} 个") 
        print(f"  低未知关系点位: {len(low_unknown)} 个")
        
        # 2. 随机打乱各个层级的点位顺序
        random.shuffle(high_unknown)
        random.shuffle(medium_unknown)
        random.shuffle(low_unknown)
        
        # 3. 检查是否与历史分组过于相似
        max_attempts = 5
        for attempt in range(max_attempts):
            # 创建候选集群
            candidate_clusters = self.generate_random_clusters(
                high_unknown, medium_unknown, low_unknown, cluster_size
            )
            
            # 检查与历史分组的相似度
            similarity = self.calculate_cluster_similarity(candidate_clusters)
            print(f"  尝试 {attempt + 1}: 与历史分组相似度 {similarity:.2%}")
            
            # 如果相似度低于阈值，接受这个分组
            if similarity < 0.6:  # 相似度低于60%
                print(f"✅ 分组相似度合适，采用此分组")
                return candidate_clusters
            
            # 如果相似度过高，重新打乱并尝试
            print(f"⚠️  分组相似度过高 ({similarity:.2%})，重新随机化...")
            random.shuffle(high_unknown)
            random.shuffle(medium_unknown)
            random.shuffle(low_unknown)
        
        # 如果多次尝试仍然相似度过高，强制使用最后一次的结果
        print(f"⚠️  经过 {max_attempts} 次尝试，强制使用当前分组")
        return candidate_clusters
    
    def generate_random_clusters(self, high_unknown: List[int], medium_unknown: List[int], 
                                low_unknown: List[int], cluster_size: int) -> List[List[int]]:
        """生成随机集群"""
        clusters = []
        available_points = high_unknown + medium_unknown + low_unknown
        used_points = set()
        
        # 随机打乱所有可用点位
        random.shuffle(available_points)
        
        # 创建集群，每个集群尽量包含不同层级的点位
        while len(available_points) - len(used_points) >= cluster_size:
            cluster = []
            
            # 🔧 重要：随机选择策略
            # 60%概率优先选择高未知关系点位，40%概率完全随机
            use_priority = random.random() < 0.6
            
            if use_priority:
                # 优先策略：先选择高未知关系点位
                remaining_high = [p for p in high_unknown if p not in used_points]
                remaining_medium = [p for p in medium_unknown if p not in used_points]
                remaining_low = [p for p in low_unknown if p not in used_points]
                
                # 按比例选择：60%高，30%中，10%低
                high_count = min(int(cluster_size * 0.6), len(remaining_high))
                medium_count = min(int(cluster_size * 0.3), len(remaining_medium))
                low_count = min(cluster_size - high_count - medium_count, len(remaining_low))
                
                # 随机选择各层级的点位
                if high_count > 0:
                    cluster.extend(random.sample(remaining_high, high_count))
                if medium_count > 0:
                    cluster.extend(random.sample(remaining_medium, medium_count))
                if low_count > 0:
                    cluster.extend(random.sample(remaining_low, low_count))
                
                # 如果集群还不够大，从剩余点位中随机补充
                while len(cluster) < cluster_size:
                    remaining = [p for p in available_points if p not in used_points and p not in cluster]
                    if not remaining:
                        break
                    cluster.append(random.choice(remaining))
                        
            else:
                # 完全随机策略
                remaining_points = [p for p in available_points if p not in used_points]
                cluster_points = random.sample(remaining_points, min(cluster_size, len(remaining_points)))
                cluster.extend(cluster_points)
            
            # 添加到已使用点位集合
            for point in cluster:
                used_points.add(point)
            
            clusters.append(sorted(cluster))  # 排序以便比较
            print(f"  生成集群 {len(clusters)}: {cluster} ({'优先' if use_priority else '随机'}策略)")
        
        # 处理剩余点位
        remaining_points = [p for p in available_points if p not in used_points]
        if remaining_points:
            if len(remaining_points) >= cluster_size // 2:  # 如果剩余点位够多，创建新集群
                clusters.append(sorted(remaining_points))
                print(f"  生成剩余集群: {remaining_points}")
            else:
                # 如果剩余点位较少，随机分配到现有集群中
                for point in remaining_points:
                    target_cluster = random.choice(clusters)
                    target_cluster.append(point)
                    target_cluster.sort()
                print(f"  剩余点位 {remaining_points} 已分配到现有集群")
        
        return clusters
    
    def calculate_cluster_similarity(self, candidate_clusters: List[List[int]]) -> float:
        """计算候选集群与历史分组的相似度"""
        if not self.group_history:
            return 0.0  # 没有历史记录，相似度为0
        
        max_similarity = 0.0
        
        # 与最近的几次分组比较
        recent_history = self.group_history[-3:]  # 最近3次分组
        
        for historical_clusters in recent_history:
            similarity = self.compare_cluster_sets(candidate_clusters, historical_clusters)
            max_similarity = max(max_similarity, similarity)
        
        return max_similarity
    
    def compare_cluster_sets(self, clusters1: List[List[int]], clusters2: List[List[int]]) -> float:
        """比较两个集群集合的相似度"""
        if not clusters1 or not clusters2:
            return 0.0
        
        total_similarity = 0.0
        comparisons = 0
        
        # 比较每个集群与另一个集群集合中最相似的集群
        for cluster1 in clusters1:
            max_cluster_similarity = 0.0
            for cluster2 in clusters2:
                # 计算两个集群的交集比例
                intersection = len(set(cluster1) & set(cluster2))
                union = len(set(cluster1) | set(cluster2))
                cluster_similarity = intersection / union if union > 0 else 0.0
                max_cluster_similarity = max(max_cluster_similarity, cluster_similarity)
            
            total_similarity += max_cluster_similarity
            comparisons += 1
        
        return total_similarity / comparisons if comparisons > 0 else 0.0
    
    def record_cluster_history(self, clusters: List[List[int]]):
        """记录集群历史"""
        # 深拷贝集群列表
        clusters_copy = [cluster.copy() for cluster in clusters]
        self.group_history.append(clusters_copy)
        
        # 只保留最近的10次分组历史
        if len(self.group_history) > 10:
            self.group_history = self.group_history[-10:]
        
        print(f"📝 已记录分组历史，当前历史记录数: {len(self.group_history)}")
    
    def test_cluster_internally(self, cluster: List[int], cluster_id: int, strategy_name: str = None) -> int:
        """在集群内部进行测试 - 每个点位轮流作为通电点位"""
        print(f"\n🔬 开始测试集群 {cluster_id + 1}")
        print(f"集群点位: {cluster}")
        print(f"集群大小: {len(cluster)}")
        
        tests_run = 0
        
        # 🔧 重要：为集群内每个点位创建测试组合，确保完成所有测试
        print(f"🔄 集群内全点位测试流程:")
        for i, power_source in enumerate(cluster):
            print(f"\n⚡ 集群内第 {i+1}/{len(cluster)} 个点位作为通电点位: {power_source}")
            
            # 其他点位作为测试点位
            other_points = [p for p in cluster if p != power_source]
            
            # 🔧 重要：修复combination_key逻辑，使用电源点位作为唯一标识
            # 之前的问题：所有测试都使用相同的组合键，导致后续测试被跳过
            combination_key = (power_source, tuple(sorted(other_points)))
            if combination_key in self.tested_combinations:
                print(f"⚠️  跳过已测试的组合: 电源点位 {power_source}")
                continue
            
            print(f"测试点位: {other_points}")
            
            try:
                test_start_time = time.time()
                
                # 计算继电器操作次数
                relay_operations = self.calculate_relay_operations(power_source, other_points)
                print(f"🔌 继电器操作次数: {relay_operations}")
                
                # 运行测试
                test_result = self.run_single_test(other_points, power_source, strategy_name)
                
                if test_result:
                    test_duration = time.time() - test_start_time
                    
                    # 🔧 重要：强制设置正确的测试数据，确保不被API数据覆盖
                    # 注意：这里需要直接修改test_result的嵌套结构
                    if 'test_result' in test_result:
                        test_result['test_result']['power_on_operations'] = 1
                        test_result['test_result']['relay_operations'] = relay_operations
                    else:
                        test_result['power_on_operations'] = 1
                        test_result['relay_operations'] = relay_operations
                    
                    test_result['test_duration'] = test_duration
                    
                    # 打印调试信息
                    print(f"🔍 调试: 设置通电次数为: 1")
                    print(f"🔍 调试: 设置继电器操作次数为: {relay_operations}")
                    
                    # 🔧 重要：验证设置是否成功
                    if 'test_result' in test_result:
                        actual_power_on = test_result['test_result'].get('power_on_operations', '未设置')
                        actual_relay = test_result['test_result'].get('relay_operations', '未设置')
                    else:
                        actual_power_on = test_result.get('power_on_operations', '未设置')
                        actual_relay = test_result.get('relay_operations', '未设置')
                    
                    print(f"🔍 验证: 通电次数={actual_power_on}, 继电器操作={actual_relay}")
                    
                    # 更新继电器状态
                    self.update_relay_states(power_source, other_points)
                    
                    # 🔧 重要：记录测试前的关系数量，用于计算新探查的关系数量
                    before_relations = len(self.known_relations)
                    
                    # 更新关系矩阵
                    self.update_relationship_matrix(test_result)
                    
                    # 计算新探查的关系数量
                    after_relations = len(self.known_relations)
                    new_relations = after_relations - before_relations
                    
                    # 记录测试历史
                    self.tested_combinations.add(combination_key)
                    self.tested_power_sources.add(power_source)
                    
                    # 更新统计
                    self.total_tests += 1
                    self.phase_test_counts[self.current_phase] += 1
                    self.performance_stats['total_relay_operations'] += relay_operations
                    self.performance_stats['total_test_time'] += test_duration
                    
                    tests_run += 1
                    
                    # 打印测试结果
                    print(f"✅ 测试完成")
                    print(f"检测到连接: {len(test_result.get('detected_connections', []))}个")
                    print(f"继电器操作: {relay_operations}次")
                    
                    # 🔧 重要：安全地获取通电次数，避免KeyError
                    power_on_count = 1  # 默认值
                    if 'test_result' in test_result:
                        power_on_count = test_result['test_result'].get('power_on_operations', 1)
                    else:
                        power_on_count = test_result.get('power_on_operations', 1)
                    
                    print(f"通电次数: {power_on_count}次")
                    print(f"测试耗时: {test_duration:.2f}秒")
                    
                    # 显示当前状态
                    self.print_current_status()
                    
                else:
                    print(f"❌ 测试失败，跳过")
                    time.sleep(0.1)
                    
            except Exception as e:
                print(f"❌ 测试执行过程中发生错误: {e}")
                import traceback
                traceback.print_exc()
                time.sleep(0.1)
                # 🔧 重要：即使出错也要继续测试下一个点位，不要退出
                continue
        
        print(f"✅ 集群 {cluster_id + 1} 内部测试完成，运行测试: {tests_run} 次")
        print(f"集群内点位数量: {len(cluster)}")
        print(f"预期测试次数: {len(cluster)}")
        print(f"实际测试次数: {tests_run}")
        
        return tests_run
    
    def run_phase_tests(self, max_tests: int = None) -> int:
        """运行当前阶段的测试 - 按集群进行"""
        print(f"\n" + "="*80)
        print(f"🚀🚀🚀 进入 run_phase_tests 方法 🚀🚀🚀")
        print(f"="*80)

        print(f"🔍🔍🔍 当前分组比例: {self.get_current_group_ratio()} 🔍🔍🔍")
        
        if max_tests is None:
            max_tests = self.config['test_execution']['max_tests_per_phase']
        
        current_ratio = self.get_current_group_ratio()
        print(f"🔍 调试 run_phase_tests: current_ratio={current_ratio}, 类型={type(current_ratio)}")
        
        # 确保是浮点数进行比较
        current_ratio_float = float(current_ratio)
        print(f"🔍 调试 run_phase_tests: current_ratio_float={current_ratio_float}, 类型={type(current_ratio_float)}")
        print(f"🔍 调试 run_phase_tests: current_ratio_float == 0.0 结果={current_ratio_float == 0.0}")
        
        # 策略切换仅取决于策略配置
        if current_ratio_float == 0.0:  # 二分法策略 - 使用浮点数比较
            print(f"\n🚀🚀🚀 检测到二分法策略，切换到二分法测试 🚀🚀🚀")
            # 🔧 重要：设置较大的max_tests值，确保二分查找能够执行完整
            binary_max_tests = max(max_tests, 100)  # 至少执行100次测试
            print(f"🔍 二分法测试最大次数: {binary_max_tests}")
            return self.run_binary_search_testing(binary_max_tests)
        
        # 获取当前策略名称
        current_strategy_name = self.get_current_strategy_name()
        
        print(f"\n🚀 开始运行阶段 {self.current_phase} 测试")
        print(f"目标测试次数: {max_tests}")
        print(f"当前分组比例: {current_ratio:.1%}")
        
        tests_run = 0
        phase_start_time = time.time()
        
        # 🔧 重要：创建一次集群，然后逐个测试，而不是重复创建
        print(f"\n🔍 创建点位集群")
        clusters = self.create_point_clusters()
        
        if not clusters:
            print("❌ 无法创建有效集群，尝试切换阶段")
            if not self.switch_to_next_phase():
                print("❌ 所有阶段已完成，退出测试")
                return 0
            return 0
        
        print(f"✅ 成功创建 {len(clusters)} 个集群")
        
        # 逐个测试每个集群
        for cluster_id, cluster in enumerate(clusters):
            if tests_run >= max_tests:
                print(f"⚠️  已达到最大测试次数限制 ({max_tests})")
                break
            
            print(f"\n🔬 开始测试集群 {cluster_id + 1}/{len(clusters)}")
            print(f"集群点位: {cluster}")
            print(f"集群大小: {len(cluster)}")
            
            # 测试集群内部 - 确保完成整个集群的所有测试
            cluster_tests = self.test_cluster_internally(cluster, cluster_id, current_strategy_name)
            tests_run += cluster_tests
            
            print(f"✅ 集群 {cluster_id + 1} 测试完成，运行测试: {cluster_tests} 次")
            print(f"累计测试: {tests_run} 次")
            
            # 检查是否应该切换阶段
            if self.should_switch_phase():
                print(f"\n🔄 检测到阶段切换条件，切换到下一阶段")
                self.switch_to_next_phase()
                break
            
            # 短暂休息
            time.sleep(1)
        
        # 阶段完成统计
        phase_duration = time.time() - phase_start_time
        print(f"\n🎯 阶段 {self.current_phase} 测试完成")
        print(f"实际运行测试: {tests_run} 次")
        print(f"阶段耗时: {phase_duration:.2f} 秒")
        print(f"累计测试: {self.total_tests} 次")
        
        return tests_run
    
    def should_switch_to_binary_search(self) -> bool:
        """判断是否应该切换到二分法测试"""
        # 计算当前已知关系比例
        total_possible_relations = self.total_points * (self.total_points - 1)
        known_ratio = len(self.known_relations) / total_possible_relations
        
        # 策略切换仅取决于策略配置
        should_switch = False
        
        # 获取当前策略配置
        current_ratio = self.get_current_group_ratio()
        if current_ratio == 0.0:  # 二分法策略
            should_switch = True
        
        print(f"🔄 二分法切换状态: {'允许' if should_switch else '不允许'}")
        print(f"  当前已知关系比例: {known_ratio:.1%}")
        print(f"  剩余未知关系: {len(self.unknown_relations)} 个")
        print(f"  已运行测试: {self.total_tests} 次")
        
        return should_switch
    
    def run_binary_search_testing(self, max_tests: int = None) -> int:
        """运行二分法测试 - 按照完整的二分法逻辑从特定点位出发进行测试"""
        if max_tests is None:
            max_tests = self.config['test_execution']['max_total_tests'] - self.total_tests
        
        print(f"\n🔍 开始二分法测试")
        print(f"目标测试次数: {max_tests}")
        
        # 🔧 重要：重新计算未知关系，确保数据准确性
        self.update_unknown_relations()
        print(f"剩余未知关系: {len(self.unknown_relations)} 个")
        
        tests_run = 0
        binary_start_time = time.time()
        
        # 🔧 重要：记录测试前的关系数量，用于计算新探查的关系数量
        initial_known_relations = len(self.known_relations)
        
        # 🔧 重要：优先选择基准点位1进行测试，确保从用户指定的基准点开始
        base_points = [1] + [p for p in range(self.total_points) if p != 1]  # 先测试点位1，然后再测试其他点位
        
        # 遍历所有点位作为基准点位
        for base_point in base_points:
            if tests_run >= max_tests:
                print(f"⚠️  已达到最大测试次数限制 ({max_tests})")
                break
                
            print(f"\n🎯 选择基准点位 {base_point} 进行二分法测试")
            
            # 获取所有与基准点位有未知关系的点位
            unknown_points_with_base = []
            for point in range(self.total_points):
                if point != base_point and ((base_point, point) in self.unknown_relations or 
                                           (point, base_point) in self.unknown_relations):
                    unknown_points_with_base.append(point)
            
            if not unknown_points_with_base:
                print(f"✅ 点位 {base_point} 与所有其他点位的关系已确认，跳过")
                continue
                
            print(f"🔍 发现 {len(unknown_points_with_base)} 个点位与基准点位 {base_point} 存在未知关系")
            
            # 步骤1: 选定基准点位，将所有未知关系点位设为开启
            current_unknown_points = unknown_points_with_base.copy()
            
            # 步骤2: 对基准点位通电，测试所有未知点位
            print(f"\n🔬 二分法测试 #{self.total_tests + 1}")
            print(f"基准点位: {base_point} (通电)")
            print(f"测试点位: {current_unknown_points} (全部开启)")
            
            try:
                test_start_time = time.time()
                test_result = self.run_single_test(current_unknown_points, base_point, "二分法策略")
                
                if test_result:
                    test_duration = time.time() - test_start_time
                    
                    # 🔧 重要：强制设置正确的测试数据，确保不被API数据覆盖
                    if 'test_result' in test_result:
                        test_result['test_result']['power_on_operations'] = 1
                    else:
                        test_result['power_on_operations'] = 1
                    
                    test_result['test_duration'] = test_duration
                    
                    # 🔧 重要：记录测试前的关系数量，用于计算新探查的关系数量
                    before_relations = len(self.known_relations)
                    
                    # 更新关系矩阵
                    self.update_relationship_matrix(test_result)
                    
                    # 计算新探查的关系数量
                    after_relations = len(self.known_relations)
                    new_relations = after_relations - before_relations
                    
                    # 更新统计
                    self.total_tests += 1
                    tests_run += 1
                    
                    # 获取检测到的连接
                    detected_connections = test_result.get('detected_connections', [])
                    
                    print(f"✅ 测试完成")
                    print(f"检测到连接: {len(detected_connections)}个")
                    print(f"继电器操作: {test_result.get('relay_operations', 0)}次")
                    print(f"通电次数: 1次")
                    print(f"测试耗时: {test_duration:.2f}秒")
                    
                    # 🔧 重要：显示新探查的关系数量
                    if new_relations > 0:
                        print(f"🎯 新探查到 {new_relations} 个点位关系！")
                    
                    # 显示当前状态
                    self.print_current_status()
                    
                    # 更新未知点位列表 - 移除已经确认关系的点位
                    updated_unknown_points = []
                    for point in current_unknown_points:
                        if ((base_point, point) in self.unknown_relations or 
                            (point, base_point) in self.unknown_relations):
                            updated_unknown_points.append(point)
                    
                    current_unknown_points = updated_unknown_points
                    
                    # 步骤3: 如果没有检测到连接，将所有点位设置为不导通
                    if len(detected_connections) == 0:
                        print(f"📊 未检测到与基准点位 {base_point} 的导通关系")
                        print(f"🔄 将基准点位 {base_point} 与所有未知点位标记为不导通")
                        
                        # 手动标记所有剩余未知点位为不导通
                        for point in current_unknown_points:
                            if (base_point, point) in self.unknown_relations:
                                self.unknown_relations.remove((base_point, point))
                                self.known_relations.add((base_point, point))
                                # 更新关系矩阵为不导通
                                self.relationship_matrix[base_point][point] = 0
                                self.relationship_matrix[point][base_point] = 0
                        
                        current_unknown_points = []
                    else:
                        # 步骤4: 如果检测到连接，执行二分查找
                        print(f"🔍 检测到与基准点位 {base_point} 的导通关系，开始二分查找")
                        
                        # 执行二分查找过程 - 确保至少执行几次二分查找
                        binary_search_rounds = 0
                        max_binary_rounds = min(5, max_tests - tests_run)  # 最多执行5轮二分查找或直到达到最大测试次数
                        
                        while tests_run < max_tests and current_unknown_points and binary_search_rounds < max_binary_rounds:
                            # 将未知点位分成两半
                            mid = len(current_unknown_points) // 2
                            first_half = current_unknown_points[:mid]
                            
                            if not first_half:
                                break
                                
                            print(f"\n🔬 二分法测试 #{self.total_tests + 1}")
                            print(f"基准点位: {base_point} (通电)")
                            print(f"测试点位: {first_half} (二分测试)")
                            print(f"二分查找轮次: {binary_search_rounds + 1}/{max_binary_rounds}")
                            
                            # 测试第一半点位
                            test_start_time = time.time()
                            half_test_result = self.run_single_test(first_half, base_point, "二分法策略")
                            
                            if half_test_result:
                                test_duration = time.time() - test_start_time
                                
                                # 🔧 重要：强制设置正确的测试数据
                                if 'test_result' in half_test_result:
                                    half_test_result['test_result']['power_on_operations'] = 1
                                else:
                                    half_test_result['power_on_operations'] = 1
                                
                                half_test_result['test_duration'] = test_duration
                                
                                # 更新关系矩阵
                                self.update_relationship_matrix(half_test_result)
                                
                                # 更新统计
                                self.total_tests += 1
                                tests_run += 1
                                binary_search_rounds += 1
                                
                                # 获取检测到的连接
                                half_detected_connections = half_test_result.get('detected_connections', [])
                                
                                print(f"✅ 二分测试完成")
                                print(f"检测到连接: {len(half_detected_connections)}个")
                                print(f"通电次数: 1次")
                                print(f"测试耗时: {test_duration:.2f}秒")
                                
                                # 更新未知点位列表
                                updated_half_unknown = []
                                for point in first_half:
                                    if ((base_point, point) in self.unknown_relations or 
                                        (point, base_point) in self.unknown_relations):
                                        updated_half_unknown.append(point)
                                
                                # 如果在第一半检测到连接，则继续在第一半中查找
                                if len(half_detected_connections) > 0:
                                    print(f"🔍 在第一半点位中检测到连接，继续在第一半中查找")
                                    current_unknown_points = updated_half_unknown
                                else:
                                    # 如果在第一半未检测到连接，则在第二半中查找
                                    print(f"📊 在第一半点位中未检测到连接，切换到第二半查找")
                                    # 先将第一半中剩余的未知点位标记为不导通
                                    for point in updated_half_unknown:
                                        if (base_point, point) in self.unknown_relations:
                                            self.unknown_relations.remove((base_point, point))
                                            self.known_relations.add((base_point, point))
                                            # 更新关系矩阵为不导通
                                            self.relationship_matrix[base_point][point] = 0
                                            self.relationship_matrix[point][base_point] = 0
                                    # 然后切换到第二半
                                    second_half = current_unknown_points[mid:]
                                    # 过滤第二半中已经确认关系的点位
                                    updated_second_half = []
                                    for point in second_half:
                                        if ((base_point, point) in self.unknown_relations or 
                                            (point, base_point) in self.unknown_relations):
                                            updated_second_half.append(point)
                                    current_unknown_points = updated_second_half
                                
                                # 显示当前状态
                                self.print_current_status()
                                
                                # 短暂休息
                                time.sleep(0.1)
                                
                            else:
                                print(f"❌ 二分测试失败，跳过")
                                time.sleep(0.1)
                                binary_search_rounds += 1
                        
                        # 如果还有剩余的未知点位，强制标记为不导通
                        if current_unknown_points:
                            print(f"📊 二分查找结束，仍有 {len(current_unknown_points)} 个未知点位，标记为不导通")
                            for point in current_unknown_points:
                                if (base_point, point) in self.unknown_relations:
                                    self.unknown_relations.remove((base_point, point))
                                    self.known_relations.add((base_point, point))
                                    # 更新关系矩阵为不导通
                                    self.relationship_matrix[base_point][point] = 0
                                    self.relationship_matrix[point][base_point] = 0
                else:
                    print(f"❌ 测试失败，跳过基准点位 {base_point}")
                    time.sleep(0.1)
            except Exception as e:
                print(f"❌ 测试基准点位 {base_point} 时出错: {e}")
                import traceback
                traceback.print_exc()
                time.sleep(0.1)
                
            except Exception as e:
                print(f"❌ 二分法测试过程中发生错误: {e}")
                import traceback
                traceback.print_exc()
                time.sleep(0.1)
                continue
        
        # 二分法测试完成统计
        binary_duration = time.time() - binary_start_time
        total_new_relations = len(self.known_relations) - initial_known_relations
        
        print(f"\n🎯 二分法测试完成")
        print(f"运行测试: {tests_run} 次")
        print(f"测试耗时: {binary_duration:.2f} 秒")
        print(f"新探查关系: {total_new_relations} 个")
        print(f"剩余未知关系: {len(self.unknown_relations)} 个")
        print(f"累计测试: {self.total_tests} 次")
        
        return tests_run
    
    def update_unknown_relations(self):
        """更新未知关系集合 - 基于当前关系矩阵状态"""
        self.unknown_relations.clear()
        self.known_relations.clear()
        
        for i in range(self.total_points):
            for j in range(i + 1, self.total_points):
                if self.relationship_matrix[i][j] is None:
                    # 未知关系
                    self.unknown_relations.add((i, j))
                else:
                    # 已知关系
                    self.known_relations.add((i, j))
    
    def select_optimal_binary_pair(self, unknown_point_pairs: List[Tuple[int, int]]) -> Tuple[int, int]:
        """智能选择二分法测试的点位对 - 优先选择概率较高的"""
        if not unknown_point_pairs:
            return None
        
        # 🔧 重要：实现真正的二分查找逻辑
        # 1. 优先选择与其他点位关系较多的点位
        # 2. 基于已知关系进行概率估计
        # 3. 避免重复测试已经确认的关系
        
        best_pair = None
        best_score = -1
        
        for point_pair in unknown_point_pairs:
            point1, point2 = point_pair
            
            # 计算点位对的测试价值分数
            score = self.calculate_binary_pair_score(point1, point2)
            
            if score > best_score:
                best_score = score
                best_pair = point_pair
        
        if best_pair:
            print(f"🔍 选择最优二分法测试对: {best_pair} (分数: {best_score:.2f})")
        
        return best_pair or unknown_point_pairs[0]
    
    def calculate_binary_pair_score(self, point1: int, point2: int) -> float:
        """计算二分法测试点位对的分数 - 基于概率和关系密度"""
        score = 0.0
        
        # 1. 基于已知关系的概率估计
        # 如果点位1或点位2与其他点位有较多已知关系，说明它们更可能是导通点
        point1_known_relations = sum(1 for p in range(self.total_points) 
                                   if p != point1 and (point1, p) in self.known_relations)
        point2_known_relations = sum(1 for p in range(self.total_points) 
                                   if p != point2 and (point2, p) in self.known_relations)
        
        # 关系密度越高，分数越高
        score += (point1_known_relations + point2_known_relations) * 0.1
        
        # 2. 基于点位在集群中的位置
        # 如果点位在同一个集群中，测试价值更高
        point1_cluster = self.get_point_cluster(point1)
        point2_cluster = self.get_point_cluster(point2)
        
        if point1_cluster == point2_cluster:
            score += 2.0  # 同集群测试优先级更高
        
        # 3. 基于点位的测试历史
        # 测试次数越少的点位，优先级越高
        point1_test_count = self.get_point_test_count(point1)
        point2_test_count = self.get_point_test_count(point2)
        
        score += (10 - point1_test_count - point2_test_count) * 0.5
        
        # 4. 基于点位的空间分布
        # 距离较近的点位，测试价值更高
        distance = abs(point1 - point2)
        if distance <= 10:  # 距离小于等于10的点位对
            score += 1.0
        
        return score
    
    def get_point_cluster(self, point: int) -> int:
        """获取点位所属的集群ID"""
        for cluster_id, cluster in enumerate(self.clusters):
            if point in cluster:
                return cluster_id
        return -1  # 未分配集群
    
    def get_point_test_count(self, point: int) -> int:
        """获取点位的测试次数"""
        count = 0
        for test_record in self.test_history:
            if (test_record.get('power_source') == point or 
                point in test_record.get('test_points', [])):
                count += 1
        return count
    
    def get_server_relationship_matrix(self) -> List[List[int]]:
        """从服务端获取关系矩阵"""
        try:
            response = requests.get(f"{self.base_url}/api/relationships/matrix")
            if response.status_code == 200:
                result = response.json()
                if result.get('success') and 'data' in result:
                    return result['data']['matrix']
        except Exception as e:
            print(f"⚠️  获取服务端关系矩阵失败: {e}")
        
        # 如果获取失败，返回本地矩阵
        return self.relationship_matrix
    
    def get_server_unknown_relations(self) -> Set[Tuple[int, int]]:
        """从服务端关系矩阵计算未知关系"""
        try:
            matrix = self.get_server_relationship_matrix()
            unknown_relations = set()
            
            for i in range(self.total_points):
                for j in range(self.total_points):
                    if i != j and matrix[i][j] == 0:  # 0表示未知关系
                        unknown_relations.add((i, j))
            
            return unknown_relations
        except Exception as e:
            print(f"⚠️  计算服务端未知关系失败: {e}")
            return self.unknown_relations
    
    def print_current_status(self):
        """打印当前状态"""
        # 🔧 重要：从服务端获取真实的关系统计数据，避免客户端和服务端数据不一致
        try:
            response = requests.get(f"{self.base_url}/api/system/info")
            if response.status_code == 200:
                system_info = response.json()
                if system_info.get('success'):
                    server_confirmed_count = system_info.get('confirmed_points_count', 0)
                    server_conductive_count = system_info.get('detected_conductive_count', 0)
                    server_non_conductive_count = system_info.get('confirmed_non_conductive_count', 0)
                    server_total_tests = system_info.get('total_tests', 0)
                    server_relay_operations = system_info.get('total_relay_operations', 0)
                    
                    # 计算总的可能关系数（N*(N-1)，排除自己到自己）
                    total_possible_relations = self.total_points * (self.total_points - 1)
                    confirmed_ratio = server_confirmed_count / max(1, total_possible_relations)
                    unknown_count = total_possible_relations - server_confirmed_count
                    unknown_ratio = unknown_count / max(1, total_possible_relations)
                    
                    print(f"\n📊 当前状态:")
                    print(f"总测试次数: {server_total_tests}")
                    print(f"当前阶段: {self.current_phase + 1} ({self.get_current_group_ratio():.1%})")
                    print(f"阶段测试次数: {self.phase_test_counts[self.current_phase]}")
                    print(f"已知关系: {server_confirmed_count} ({confirmed_ratio:.1%})")
                    print(f"  - 导通关系: {server_conductive_count}")
                    print(f"  - 不导通关系: {server_non_conductive_count}")
                    print(f"未知关系: {unknown_count} ({unknown_ratio:.1%})")
                    print(f"继电器操作总数: {server_relay_operations}")
                    return
        except Exception as e:
            print(f"⚠️  获取服务器状态失败: {e}")
        
        # 如果服务器获取失败，使用本地数据作为备用
        total_possible_relations = self.total_points * (self.total_points - 1)
        known_ratio = len(self.known_relations) / total_possible_relations
        unknown_ratio = len(self.unknown_relations) / total_possible_relations
        
        print(f"\n📊 当前状态 (本地备用数据):")
        print(f"总测试次数: {self.total_tests}")
        print(f"当前阶段: {self.current_phase + 1} ({self.get_current_group_ratio():.1%})")
        print(f"阶段测试次数: {self.phase_test_counts[self.current_phase]}")
        print(f"已知关系: {len(self.known_relations)} ({known_ratio:.1%})")
        print(f"未知关系: {len(self.unknown_relations)} ({unknown_ratio:.1%})")
        print(f"继电器操作总数: {self.performance_stats['total_relay_operations']}")
    
    def run_full_test_cycle(self, max_tests: int = None) -> dict:
        """运行完整的测试周期"""
        if max_tests is None:
            max_tests = self.config['test_execution']['max_total_tests']
        
        print(f"🚀 开始运行完整测试周期")
        print("=" * 60)
        
        # 初始化关系矩阵
        self.initialize_relationship_matrix()
        
        start_time = time.time()
        
        # 🔧 重要：根据初始未知关系比例确定测试策略
        initial_ratio = self.get_current_group_ratio()
        initial_strategy = self.get_strategy_name_by_ratio(initial_ratio)
        print(f"\n🎯 初始测试策略: {initial_strategy} ({initial_ratio:.1%})")
        print("=" * 40)
        
        # 第一阶段：动态策略测试
        print(f"\n🎯 第一阶段：动态策略测试")
        print("=" * 40)
        
        phase_tests = 0
        current_phase = 1
        
        while current_phase <= len(self.group_ratios):
            # 检查是否应该切换到二分法
            if self.should_switch_to_binary_search():
                print(f"\n🔄 检测到二分法切换条件，提前结束自适应分组测试")
                break
            
            # 运行当前阶段测试
            print(f"\n" + "="*100)
            print(f"🚀🚀🚀 准备调用 run_phase_tests 方法 🚀🚀🚀")
            print(f"="*100)
            phase_tests = self.run_phase_tests()
            print(f"🚀🚀🚀 run_phase_tests 方法返回: {phase_tests} 🚀🚀🚀")
            print(f"="*100)
            
            if phase_tests == 0:
                print(f"⚠️  阶段 {current_phase} 没有运行测试，尝试切换阶段")
                if not self.switch_to_next_phase():
                    print(f"❌ 无法切换到下一阶段，结束自适应分组测试")
                    break
                current_phase += 1
                continue
            
            # 检查是否应该切换到下一阶段
            if self.should_switch_phase():
                if not self.switch_to_next_phase():
                    print(f"❌ 无法切换到下一阶段，结束自适应分组测试")
                    break
                current_phase += 1
            else:
                # 如果当前阶段测试次数很少，可能已经完成
                if phase_tests < 10:
                    print(f"⚠️  阶段 {current_phase} 测试次数过少，可能已完成")
                    break
        
        # 自适应分组测试完成统计
        adaptive_duration = time.time() - start_time
        print(f"\n🎯 自适应分组测试阶段完成")
        print(f"运行阶段数: {current_phase - 1}")
        print(f"总测试次数: {self.total_tests}")
        print(f"测试耗时: {adaptive_duration:.2f} 秒")
        print(f"剩余未知关系: {len(self.unknown_relations)} 个")
        
        # 第二阶段：二分法测试（如果还有未知关系）
        if len(self.unknown_relations) > 0:
            print(f"\n🎯 第二阶段：二分法测试")
            print("=" * 40)
            
            binary_start_time = time.time()
            binary_tests = self.run_binary_search_testing()
            binary_duration = time.time() - binary_start_time
            
            print(f"\n🎯 二分法测试阶段完成")
            print(f"运行测试: {binary_tests} 次")
            print(f"测试耗时: {binary_duration:.2f} 秒")
            print(f"剩余未知关系: {len(self.unknown_relations)} 个")
        else:
            print(f"\n🎯 所有点位关系已确认，无需二分法测试")
            binary_tests = 0
        
        # 完整测试周期统计
        total_duration = time.time() - start_time
        
        print(f"\n🏁 完整测试周期完成")
        print("=" * 60)
        print(f"总测试次数: {self.total_tests}")
        print(f"总测试耗时: {total_duration:.2f} 秒")
        print(f"自适应分组测试: {self.total_tests - binary_tests} 次")
        print(f"二分法测试: {binary_tests} 次")
        print(f"最终未知关系: {len(self.unknown_relations)} 个")
        print(f"最终已知关系: {len(self.known_relations)} 个")
        
        # 计算覆盖率
        total_possible_relations = self.total_points * (self.total_points - 1)
        coverage_ratio = len(self.known_relations) / total_possible_relations
        print(f"关系覆盖率: {coverage_ratio:.1%}")
        
        return {
            'total_tests': self.total_tests,
            'total_duration': total_duration,
            'adaptive_tests': self.total_tests - binary_tests,
            'binary_tests': binary_tests,
            'unknown_relations': len(self.unknown_relations),
            'known_relations': len(self.known_relations),
            'coverage_ratio': coverage_ratio,
            'phase_counts': self.phase_test_counts.copy(),
            'performance_stats': self.performance_stats.copy()
        }
    
    def print_final_statistics(self):
        """打印最终统计信息"""
        print("\n" + "=" * 60)
        print("🏁 测试完成 - 最终统计")
        print("=" * 60)
        
        total_possible_relations = self.total_points * (self.total_points - 1)
        known_ratio = len(self.known_relations) / total_possible_relations
        unknown_ratio = len(self.unknown_relations) / total_possible_relations
        
        print(f"总测试次数: {self.total_tests}")
        print(f"总继电器操作: {self.performance_stats['total_relay_operations']}")
        print(f"总测试时间: {self.performance_stats['total_test_time']:.2f} 秒")
        print(f"平均每次测试时间: {self.performance_stats['total_test_time'] / max(1, self.total_tests):.2f} 秒")
        
        print(f"\n关系矩阵状态:")
        print(f"已知关系: {len(self.known_relations)} ({known_ratio:.1%})")
        print(f"未知关系: {len(self.unknown_relations)} ({unknown_ratio:.1%})")
        
        print(f"\n各阶段测试统计:")
        for i, count in enumerate(self.phase_test_counts):
            if i < len(self.group_ratios):
                ratio = self.group_ratios[i]
                print(f"阶段 {i+1} ({ratio:.1%}): {count} 次测试")
            else:
                print(f"阶段 {i+1}: {count} 次测试")
        
        print(f"\n电源点位使用分布:")
        sorted_usage = sorted(self.power_source_usage.items(), key=lambda x: x[1], reverse=True)
        for point, count in sorted_usage[:10]:  # 显示前10个
            print(f"点位 {point}: {count} 次")
    
    def save_results(self):
        """保存测试结果"""
        if not self.config['save_results']:
            return
        
        results = {
            'config': self.config,
            'test_summary': {
                'total_tests': self.total_tests,
                'total_relay_operations': self.performance_stats['total_relay_operations'],
                'total_test_time': self.performance_stats['total_test_time'],
                'phase_test_counts': self.phase_test_counts,
                'final_known_relations': len(self.known_relations),
                'final_unknown_relations': len(self.unknown_relations),
            },
            'group_history': self.group_history,
            'power_source_usage': dict(self.power_source_usage),
            'performance_stats': self.performance_stats,
            'timestamp': time.time()
        }
        
        filename = self.config['results_file']
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(results, f, ensure_ascii=False, indent=2)
            print(f"✅ 测试结果已保存到: {filename}")
        except Exception as e:
            print(f"❌ 保存结果失败: {str(e)}")

def main():
    """主函数"""
    print("🚀 自适应分组测试系统")
    print("=" * 60)
    
    # 获取配置
    config = get_config('balanced')
    
    # 创建测试器
    tester = AdaptiveGroupingTester(config)
    
    # 运行完整测试周期
    try:
        tester.run_full_test_cycle()
    except KeyboardInterrupt:
        print("\n⚠️  测试被用户中断")
        tester.print_current_status()
    except Exception as e:
        print(f"\n❌ 测试过程中发生错误: {str(e)}")
        tester.print_current_status()

if __name__ == "__main__":
    main()
