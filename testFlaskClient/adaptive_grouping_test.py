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
        self.group_ratios = config['adaptive_grouping']['group_ratios']
        
        # 关系矩阵状态
        self.relationship_matrix = [[None] * self.total_points for _ in range(self.total_points)]
        self.known_relations = set()  # 已知关系集合（本地备用）
        self.unknown_relations = set()  # 未知关系集合（本地备用）
        
        # 测试状态
        self.current_phase = 0  # 当前测试阶段
        self.phase_test_counts = [0] * len(self.group_ratios)  # 每阶段测试次数
        self.total_tests = 0  # 总测试次数
        
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
    
    def run_single_test(self, test_points: List[int], power_source: int) -> Dict[str, Any]:
        """运行单次测试"""
        try:
            payload = {
                "power_source": power_source,
                "test_points": test_points
            }
            
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
                    
                    # 🔧 重要：根据未知关系比例确定目标策略
                    if unknown_ratio >= 0.5:  # 50%以上
                        target_strategy = "adaptive_50"
                        target_ratio = 0.5
                    elif unknown_ratio >= 0.3:  # 30%-50%
                        target_strategy = "adaptive_30"
                        target_ratio = 0.3
                    elif unknown_ratio >= 0.1:  # 10%-30%
                        target_strategy = "adaptive_10"
                        target_ratio = 0.1
                    else:  # 10%以下
                        target_strategy = "binary_search"
                        target_ratio = 0.0
                    
                    # 获取当前策略
                    current_ratio = self.get_current_group_ratio()
                    current_strategy = self.get_strategy_name_by_ratio(current_ratio)
                    
                    # 如果目标策略与当前策略不同，需要切换
                    if current_strategy != target_strategy:
                        print(f"🔄 未知关系比例: {unknown_ratio:.1%}")
                        print(f"当前策略: {current_strategy} ({current_ratio:.1%})")
                        print(f"目标策略: {target_strategy} ({target_ratio:.1%})")
                        print(f"准备切换策略")
                        return True
                    
                    return False
        except Exception as e:
            print(f"⚠️  获取服务端数据失败，使用本地数据: {e}")
        
        # 如果服务端获取失败，使用本地数据作为备用
        total_possible_relations = self.total_points * (self.total_points - 1)
        unknown_ratio = len(self.unknown_relations) / total_possible_relations
        
        # 🔧 重要：根据未知关系比例确定目标策略
        if unknown_ratio >= 0.5:  # 50%以上
            target_strategy = "adaptive_50"
            target_ratio = 0.5
        elif unknown_ratio >= 0.3:  # 30%-50%
            target_strategy = "adaptive_30"
            target_ratio = 0.3
        elif unknown_ratio >= 0.1:  # 10%-30%
            target_strategy = "adaptive_10"
            target_ratio = 0.1
        else:  # 10%以下
            target_strategy = "binary_search"
            target_ratio = 0.0
        
        # 获取当前策略
        current_ratio = self.get_current_group_ratio()
        current_strategy = self.get_strategy_name_by_ratio(current_ratio)
        
        # 如果目标策略与当前策略不同，需要切换
        if current_strategy != target_strategy:
            print(f"🔄 未知关系比例: {unknown_ratio:.1%}")
            print(f"当前策略: {current_strategy} ({current_ratio:.1%})")
            print(f"目标策略: {target_strategy} ({target_ratio:.1%})")
            print(f"准备切换策略")
            return True
        
        return False
    
    def get_strategy_name_by_ratio(self, ratio: float) -> str:
        """根据分组比例获取策略名称"""
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
        
        # 如果都不匹配，返回二分法阶段
        return 'binary_search'
    
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
                    
                    # 🔧 重要：根据未知关系比例确定目标策略
                    if unknown_ratio >= 0.5:  # 50%以上
                        target_strategy = "adaptive_50"
                        target_ratio = 0.5
                    elif unknown_ratio >= 0.3:  # 30%-50%
                        target_strategy = "adaptive_30"
                        target_ratio = 0.3
                    elif unknown_ratio >= 0.1:  # 10%-30%
                        target_strategy = "adaptive_10"
                        target_ratio = 0.1
                    else:  # 10%以下
                        target_strategy = "binary_search"
                        target_ratio = 0.0
                    
                    # 如果是二分法策略，不需要切换阶段
                    if target_strategy == "binary_search":
                        print(f"🏁 切换到二分法策略")
                        return False
                    
                    # 找到对应的阶段索引
                    target_phase_index = None
                    for i, ratio in enumerate(self.group_ratios):
                        if abs(ratio - target_ratio) < 0.01:  # 允许小的浮点误差
                            target_phase_index = i
                            break
                    
                    if target_phase_index is None:
                        print(f"⚠️ 无法找到匹配的阶段索引，保持当前阶段")
                        return False
                    
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
        
        # 🔧 重要：根据未知关系比例确定目标策略
        if unknown_ratio >= 0.5:  # 50%以上
            target_strategy = "adaptive_50"
            target_ratio = 0.5
        elif unknown_ratio >= 0.3:  # 30%-50%
            target_strategy = "adaptive_30"
            target_ratio = 0.3
        elif unknown_ratio >= 0.1:  # 10%-30%
            target_strategy = "adaptive_10"
            target_ratio = 0.1
        else:  # 10%以下
            target_strategy = "binary_search"
            target_ratio = 0.0
        
        # 如果是二分法策略，不需要切换阶段
        if target_strategy == "binary_search":
            print(f"🏁 切换到二分法策略")
            return False
        
        # 找到对应的阶段索引
        target_phase_index = None
        for i, ratio in enumerate(self.group_ratios):
            if abs(ratio - target_ratio) < 0.01:  # 允许小的浮点误差
                target_phase_index = i
                break
        
        if target_phase_index is None:
            print(f"⚠️ 无法找到匹配的阶段索引，保持当前阶段")
            return False
        
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
        # 🔧 重要：优先使用服务端数据计算未知关系比例，确保与状态显示一致
        try:
            response = requests.get(f"{self.base_url}/api/system/info")
            if response.status_code == 200:
                system_info = response.json()
                if system_info.get('success'):
                    server_confirmed_count = system_info.get('confirmed_points_count', 0)
                    total_possible_relations = self.total_points * (self.total_points - 1)
                    unknown_ratio = (total_possible_relations - server_confirmed_count) / total_possible_relations
                    
                    # 🔧 重要：根据未知关系比例动态选择策略
                    if unknown_ratio >= 0.5:  # 50%以上
                        strategy_ratio = 0.5
                        strategy_name = "adaptive_50"
                    elif unknown_ratio >= 0.3:  # 30%-50%
                        strategy_ratio = 0.3
                        strategy_name = "adaptive_30"
                    elif unknown_ratio >= 0.1:  # 10%-30%
                        strategy_ratio = 0.1
                        strategy_name = "adaptive_10"
                    else:  # 10%以下
                        strategy_ratio = 0.0
                        strategy_name = "binary_search"
                    
                    print(f"🔍 动态策略选择 (服务端数据):")
                    print(f"  未知关系比例: {unknown_ratio:.1%}")
                    print(f"  选择策略: {strategy_name}")
                    print(f"  分组比例: {strategy_ratio:.1%}")
                    
                    return strategy_ratio
        except Exception as e:
            print(f"⚠️  获取服务端数据失败，使用本地数据: {e}")
        
        # 如果服务端获取失败，使用本地数据作为备用
        total_possible_relations = self.total_points * (self.total_points - 1)
        unknown_ratio = len(self.unknown_relations) / total_possible_relations
        
        # 🔧 重要：根据未知关系比例动态选择策略
        if unknown_ratio >= 0.5:  # 50%以上
            strategy_ratio = 0.5
            strategy_name = "adaptive_50"
        elif unknown_ratio >= 0.3:  # 30%-50%
            strategy_ratio = 0.3
            strategy_name = "adaptive_30"
        elif unknown_ratio >= 0.1:  # 10%-30%
            strategy_ratio = 0.1
            strategy_name = "adaptive_10"
        else:  # 10%以下
            strategy_ratio = 0.0
            strategy_name = "binary_search"
        
        print(f"🔍 动态策略选择 (本地数据):")
        print(f"  未知关系比例: {unknown_ratio:.1%}")
        print(f"  选择策略: {strategy_name}")
        print(f"  分组比例: {strategy_ratio:.1%}")
        
        return strategy_ratio
    
    def create_point_clusters(self) -> List[List[int]]:
        """创建点位集群 - 按比例切割为不相交的集群，使用随机分组策略"""
        print(f"🔍 创建点位集群（随机分组策略）...")
        
        # 获取当前阶段的分组比例 - 使用动态计算而不是固定数组
        current_ratio = self.get_current_group_ratio()
        cluster_size = int(self.total_points * current_ratio)
        
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
    
    def test_cluster_internally(self, cluster: List[int], cluster_id: int) -> int:
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
                test_result = self.run_single_test(other_points, power_source)
                
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
        if max_tests is None:
            max_tests = self.config['test_execution']['max_tests_per_phase']
        
        # 🔧 重要：检查当前策略，如果是二分法则直接调用二分法测试
        current_ratio = self.get_current_group_ratio()
        if current_ratio == 0.0:  # 二分法策略
            print(f"\n🔍 检测到二分法策略，切换到二分法测试")
            return self.run_binary_search_testing(max_tests)
        
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
            cluster_tests = self.test_cluster_internally(cluster, cluster_id)
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
        
        # 当已知关系超过85%时，切换到二分法
        binary_search_threshold = 0.85
        
        # 或者当未知关系少于100个时，切换到二分法
        min_unknown_relations = 100
        
        # 确保至少进行一定数量的测试后再考虑切换
        min_tests_before_switch = 50
        
        should_switch = False
        
        if self.total_tests >= min_tests_before_switch:
            should_switch = (known_ratio >= binary_search_threshold or 
                            len(self.unknown_relations) <= min_unknown_relations)
        
        if should_switch:
            print(f"🔄 检测到二分法切换条件:")
            print(f"  已知关系比例: {known_ratio:.1%}")
            print(f"  剩余未知关系: {len(self.unknown_relations)} 个")
            print(f"  阈值: {binary_search_threshold:.1%} 或 {min_unknown_relations} 个")
            print(f"  已运行测试: {self.total_tests} 次")
        else:
            if self.total_tests < min_tests_before_switch:
                print(f"⏳ 测试次数不足 ({self.total_tests}/{min_tests_before_switch})，继续自适应分组测试")
        
        return should_switch
    
    def run_binary_search_testing(self, max_tests: int = None) -> int:
        """运行二分法测试"""
        if max_tests is None:
            max_tests = self.config['test_execution']['max_total_tests'] - self.total_tests
        
        print(f"\n🔍 开始二分法测试")
        print(f"目标测试次数: {max_tests}")
        print(f"剩余未知关系: {len(self.unknown_relations)} 个")
        
        tests_run = 0
        binary_start_time = time.time()
        
        # 获取所有未知关系的点位对
        unknown_point_pairs = list(self.unknown_relations)
        
        # 🔧 重要：记录测试前的关系数量，用于计算新探查的关系数量
        initial_known_relations = len(self.known_relations)
        
        while tests_run < max_tests and unknown_point_pairs:
            # 🔧 重要：智能选择点位对，优先选择概率较高的
            point_pair = self.select_optimal_binary_pair(unknown_point_pairs)
            if point_pair not in unknown_point_pairs:
                continue
                
            unknown_point_pairs.remove(point_pair)
            point1, point2 = point_pair
            
            print(f"\n🔬 二分法测试 #{self.total_tests + 1}")
            print(f"测试点位对: {point1} <-> {point2}")
            
            try:
                # 测试点位1作为电源，点位2作为测试点
                test_start_time = time.time()
                test_result = self.run_single_test([point2], point1)
                
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
                    
                    # 🔧 重要：显示新探查的关系数量
                    if new_relations > 0:
                        print(f"🎯 新探查到 {new_relations} 个点位关系！")
                    else:
                        print(f"📊 本次测试未发现新的点位关系")
                    
                    # 打印测试结果
                    print(f"✅ 测试完成")
                    print(f"检测到连接: {len(test_result.get('detected_connections', []))}个")
                    print(f"继电器操作: {test_result.get('relay_operations', 0)}次")
                    
                    # 🔧 重要：安全地获取通电次数，避免KeyError
                    power_on_count = 1  # 默认值
                    if 'test_result' in test_result:
                        power_on_count = test_result['test_result'].get('power_on_operations', 1)
                    else:
                        power_on_count = test_result.get('power_on_operations', 1)
                    
                    print(f"通电次数: {power_on_count}次")  # 使用设置的值
                    print(f"测试耗时: {test_duration:.2f}秒")
                    
                    # 🔧 重要：显示新探查的关系数量
                    if new_relations > 0:
                        print(f"🎯 新探查到 {new_relations} 个点位关系！")
                    else:
                        print(f"📊 本次测试未发现新的点位关系")
                    
                    # 检查是否已经确认了这对点位的关系
                    if (point1, point2) not in self.unknown_relations:
                        print(f"✅ 点位 {point1} 和 {point2} 的关系已确认")
                    else:
                        print(f"⚠️  点位 {point1} 和 {point2} 的关系仍未确认")
                        
                        # 如果第一次测试没有确认关系，尝试反向测试
                        if tests_run < max_tests:
                            print(f"🔄 尝试反向测试: {point2} -> {point1}")
                            
                            reverse_test_start = time.time()
                            reverse_result = self.run_single_test([point1], point2)
                            
                            if reverse_result:
                                reverse_duration = time.time() - reverse_test_start
                                
                                # 🔧 重要：强制设置正确的测试数据，确保不被API数据覆盖
                                if 'test_result' in reverse_result:
                                    reverse_result['test_result']['power_on_operations'] = 1
                                else:
                                    reverse_result['power_on_operations'] = 1
                                
                                reverse_result['test_duration'] = reverse_duration
                                
                                # 🔧 重要：记录反向测试前的关系数量
                                before_reverse_relations = len(self.known_relations)
                                
                                # 更新关系矩阵
                                self.update_relationship_matrix(reverse_result)
                                
                                # 计算反向测试新探查的关系数量
                                after_reverse_relations = len(self.known_relations)
                                new_reverse_relations = after_reverse_relations - before_reverse_relations
                                
                                # 更新统计
                                self.total_tests += 1
                                tests_run += 1
                                
                                print(f"✅ 反向测试完成")
                                print(f"检测到连接: {len(reverse_result.get('detected_connections', []))}个")
                                print(f"继电器操作: {reverse_result.get('relay_operations', 0)}次")
                                
                                # 🔧 重要：安全地获取通电次数，避免KeyError
                                power_on_count = 1  # 默认值
                                if 'test_result' in reverse_result:
                                    power_on_count = reverse_result['test_result'].get('power_on_operations', 1)
                                else:
                                    power_on_count = reverse_result.get('power_on_operations', 1)
                                
                                print(f"通电次数: {power_on_count}次")  # 使用设置的值
                                print(f"测试耗时: {reverse_duration:.2f}秒")
                                
                                # 🔧 重要：显示反向测试新探查的关系数量
                                if new_reverse_relations > 0:
                                    print(f"🎯 反向测试新探查到 {new_reverse_relations} 个点位关系！")
                                else:
                                    print(f"📊 反向测试未发现新的点位关系")
                                
                                # 再次检查关系是否确认
                                if (point1, point2) not in self.unknown_relations:
                                    print(f"✅ 点位 {point1} 和 {point2} 的关系已确认")
                                else:
                                    print(f"❌ 点位 {point1} 和 {point2} 的关系仍未确认，可能存在问题")
                    
                    # 显示当前状态
                    self.print_current_status()
                    
                else:
                    print(f"❌ 测试失败，跳过")
                    time.sleep(0.1)
                    
            except Exception as e:
                print(f"❌ 二分法测试过程中发生错误: {e}")
                import traceback
                traceback.print_exc()
                time.sleep(0.1)
                continue
            
            # 短暂休息
            time.sleep(0.1)
        
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
        
        while current_phase <= len(self.config['adaptive_grouping']['group_ratios']):
            # 检查是否应该切换到二分法
            if self.should_switch_to_binary_search():
                print(f"\n🔄 检测到二分法切换条件，提前结束自适应分组测试")
                break
            
            # 运行当前阶段测试
            phase_tests = self.run_phase_tests()
            
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
            ratio = self.group_ratios[i]
            print(f"阶段 {i+1} ({ratio:.1%}): {count} 次测试")
        
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
