#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
高效批量测试客户端 - 实现最高效率的矩阵信息填充

核心策略：
1. 一次性规划所有测试请求
2. 批量发送试验请求，减少网络延迟
3. 统一获取关系矩阵进行分析
4. 基于分析结果组织二次试验
"""

import json
import time
import random
import math
from typing import Dict, List, Set, Tuple, Optional, Any
import requests
import concurrent.futures
from dataclasses import dataclass

@dataclass
class TestRequest:
    """测试请求数据结构"""
    power_source: int
    test_points: List[int]
    strategy: str
    batch_size: int
    priority: int = 1

class EfficientBatchTestClient:
    """高效批量测试客户端"""
    
    def __init__(self, base_url: str = "http://localhost:5000"):
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update({'Content-Type': 'application/json'})
        
        # 关系矩阵缓存
        self.relationship_matrix = None
        self.true_relationship_matrix = None
        self.total_points = 0
        
        # 测试历史
        self.tested_pairs: Set[Tuple[int, int]] = set()
        self.confirmed_conductive: Set[Tuple[int, int]] = set()
        self.confirmed_non_conductive: Set[Tuple[int, int]] = set()
        
        # 统计信息
        self.total_tests = 0
        self.total_relay_operations = 0
        
        # 批量测试配置
        self.batch_size = 50  # 默认批量大小
        self.min_batch_size = 20  # 最小批量大小
        self.max_batch_size = 80  # 最大批量大小
        
        # 并发配置
        self.max_concurrent_requests = 10  # 最大并发请求数
        self.request_batch_size = 20  # 每批发送的请求数量
        
        # 继电器优化配置
        self.current_power_source = None  # 当前通电点位
        self.relay_switch_count = 0      # 继电器切换次数
        self.relay_optimization_enabled = True  # 启用继电器优化
    
    def get_system_info(self) -> Dict[str, Any]:
        """获取系统信息"""
        try:
            response = self.session.get(f"{self.base_url}/api/system/info")
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            print(f"获取系统信息失败: {e}")
        return {}
    
    def get_relationship_matrix(self) -> Dict[str, Any]:
        """获取检测到的关系矩阵"""
        try:
            response = self.session.get(f"{self.base_url}/api/relationships/matrix")
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            print(f"获取关系矩阵失败: {e}")
        return {}
    
    def get_true_relationship_matrix(self) -> Dict[str, Any]:
        """获取真实关系矩阵"""
        try:
            response = self.session.get(f"{self.base_url}/api/relationships/true_matrix")
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            print(f"获取真实关系矩阵失败: {e}")
        return {}
    
    def run_experiment(self, power_source: int, test_points: List[int]) -> Dict[str, Any]:
        """运行单个实验"""
        try:
            payload = {
                "power_source": power_source,
                "test_points": test_points
            }
            response = self.session.post(f"{self.base_url}/api/experiment", json=payload)
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            print(f"运行实验失败: {e}")
        return {}
    
    def run_experiment_batch(self, test_requests: List[TestRequest]) -> List[Dict[str, Any]]:
        """批量运行实验"""
        results = []
        
        # 分批发送请求，避免服务器压力过大
        for i in range(0, len(test_requests), self.request_batch_size):
            batch = test_requests[i:i + self.request_batch_size]
            print(f"发送第 {i//self.request_batch_size + 1} 批请求 ({len(batch)} 个)")
            
            # 使用线程池并发执行
            with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_concurrent_requests) as executor:
                future_to_request = {
                    executor.submit(self.run_experiment, req.power_source, req.test_points): req
                    for req in batch
                }
                
                for future in concurrent.futures.as_completed(future_to_request):
                    request = future_to_request[future]
                    try:
                        result = future.result()
                        results.append({
                            'request': request,
                            'result': result,
                            'success': result.get('success', False)
                        })
                        
                        if result.get('success'):
                            print(f"  电源点{request.power_source} -> {len(request.test_points)}个目标点: 成功")
                        else:
                            print(f"  电源点{request.power_source} -> {len(request.test_points)}个目标点: 失败")
                            
                    except Exception as e:
                        print(f"  电源点{request.power_source} -> {len(request.test_points)}个目标点: 异常 {e}")
                        results.append({
                            'request': request,
                            'result': {'error': str(e)},
                            'success': False
                        })
            
            # 批次间短暂延迟
            if i + self.request_batch_size < len(test_requests):
                time.sleep(0.1)
        
        return results
    
    def update_matrices(self):
        """更新关系矩阵"""
        print("更新关系矩阵...")
        
        # 获取检测到的关系矩阵
        detected_result = self.get_relationship_matrix()
        if detected_result.get('success'):
            self.relationship_matrix = detected_result['data']['matrix']
            self.total_points = detected_result['data']['total_points']
            print(f"检测到的关系矩阵: {self.total_points}x{self.total_points}")
        
        # 获取真实关系矩阵
        true_result = self.get_true_relationship_matrix()
        if true_result.get('success'):
            self.true_relationship_matrix = true_result['data']['matrix']
            print("真实关系矩阵已更新")
    
    def analyze_matrix_efficiency(self) -> Dict[str, Any]:
        """分析矩阵效率"""
        if not self.relationship_matrix:
            return {}
        
        total_cells = self.total_points * self.total_points
        diagonal_cells = self.total_points
        off_diagonal_cells = total_cells - diagonal_cells
        
        # 统计检测到的关系
        detected_conductive = 0
        detected_non_conductive = 0
        detected_unknown = 0
        
        for i in range(self.total_points):
            for j in range(self.total_points):
                if i == j:  # 跳过对角线
                    continue
                
                detected = self.relationship_matrix[i][j]
                
                # 统计检测到的关系
                if detected == 1:
                    detected_conductive += 1
                elif detected == -1:
                    detected_non_conductive += 1
                else:  # detected == 0
                    detected_unknown += 1
        
        # 计算效率指标
        detection_rate = (detected_conductive + detected_non_conductive) / off_diagonal_cells * 100 if off_diagonal_cells > 0 else 0
        
        return {
            'total_points': self.total_points,
            'off_diagonal_cells': off_diagonal_cells,
            'detected': {
                'conductive': detected_conductive,
                'non_conductive': detected_non_conductive,
                'unknown': detected_unknown,
                'rate': detection_rate
            }
        }
    
    def select_batch_points(self) -> List[int]:
        """选择批量测试的点位（智能去重版本）"""
        if not self.relationship_matrix:
            return []
        
        # 策略1: 优先选择未知关系最多的点位
        # 策略2: 避免选择与已知关系过多的点位（减少冗余测试）
        candidate_scores = []
        
        for i in range(self.total_points):
            unknown_count = 0
            known_conductive = 0
            known_non_conductive = 0
            
            for j in range(self.total_points):
                if i != j:
                    relation = self.relationship_matrix[i][j]
                    if relation == 0:  # 未知关系
                        unknown_count += 1
                    elif relation == 1:  # 已知导通
                        known_conductive += 1
                    elif relation == -1:  # 已知不导通
                        known_non_conductive += 1
            
            if unknown_count > 0:  # 只考虑还有未知关系的点位
                # 评分公式：未知关系数量 * 0.8 + 避免冗余 * 0.2
                # 已知关系越少，评分越高（减少冗余测试）
                redundancy_penalty = (known_conductive + known_non_conductive) / (self.total_points - 1)
                score = unknown_count * 0.8 - redundancy_penalty * 0.2
                
                candidate_scores.append((i, score, unknown_count, known_conductive, known_non_conductive))
        
        if not candidate_scores:
            return []
        
        # 按评分排序，选择最优的点位
        candidate_scores.sort(key=lambda x: x[1], reverse=True)
        
        # 调整批量大小为50%左右
        target_batch_size = min(50, self.total_points // 2)  # 50%覆盖率
        selected_points = [p[0] for p in candidate_scores[:target_batch_size]]
        
        print(f"选择了 {len(selected_points)} 个点位进行批量测试（目标50%覆盖率）")
        print(f"选中的点位: {selected_points[:10]}{'...' if len(selected_points) > 10 else ''}")
        
        # 打印选择策略信息
        if candidate_scores:
            best_candidate = candidate_scores[0]
            print(f"最优候选点位: {best_candidate[0]}, 评分{best_candidate[1]:.2f}")
            print(f"  未知关系: {best_candidate[2]}, 已知导通: {best_candidate[3]}, 已知不导通: {best_candidate[4]}")
        
        return selected_points
    
    def plan_massive_batch_tests(self, batch_points: List[int]) -> List[TestRequest]:
        """规划大规模批量测试（智能去重版本）"""
        if not batch_points:
            return []
        
        test_requests = []
        tested_combinations = set()  # 记录已测试的组合，避免重复
        
        # 策略: 每个选中的点位作为电源点，测试其他所有选中的点位
        for i, power_source in enumerate(batch_points):
            # 选择其他点位作为测试目标
            test_targets = [p for p in batch_points if p != power_source]
            
            # 过滤掉已知关系的点位和已测试的组合
            filtered_targets = []
            for target in test_targets:
                # 检查是否已知关系
                if self.relationship_matrix[power_source][target] == 0:  # 未知关系
                    # 检查是否已经测试过这个组合
                    combination = tuple(sorted([power_source, target]))
                    if combination not in tested_combinations:
                        filtered_targets.append(target)
                        tested_combinations.add(combination)
            
            if filtered_targets:
                # 计算优先级（未知关系越多，优先级越高）
                priority = len(filtered_targets)
                
                # 避免生成过大的批次，分批处理
                max_targets_per_batch = 25  # 每批最多25个目标点
                for j in range(0, len(filtered_targets), max_targets_per_batch):
                    batch_targets = filtered_targets[j:j + max_targets_per_batch]
                    
                    test_requests.append(TestRequest(
                        power_source=power_source,
                        test_points=batch_targets,
                        strategy='massive_batch_smart',
                        batch_size=len(batch_targets)
                    ))
        
        # 按优先级排序，高优先级的先执行
        test_requests.sort(key=lambda x: x.batch_size, reverse=True)
        
        print(f"生成了 {len(test_requests)} 个智能去重批量测试请求")
        print(f"避免了 {len(tested_combinations)} 个重复测试组合")
        
        return test_requests
    
    def analyze_test_results(self, test_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """分析测试结果"""
        print("分析测试结果...")
        
        successful_tests = 0
        failed_tests = 0
        total_connections_found = 0
        total_non_conductive_relations = 0
        
        for result in test_results:
            if result['success']:
                successful_tests += 1
                
                # 分析测试结果
                test_result = result['result'].get('data', {}).get('test_result', {})
                if test_result:
                    connections = test_result.get('connections', [])
                    if connections:
                        # 处理不同类型的connections数据
                        if isinstance(connections, list):
                            # 如果是列表，计算有效连接数
                            valid_connections = 0
                            for conn in connections:
                                if isinstance(conn, dict):
                                    # 如果是字典，检查是否有有效数据
                                    if conn.get('point_id') is not None or conn.get('id') is not None:
                                        valid_connections += 1
                                elif isinstance(conn, (int, str)):
                                    # 如果是数字或字符串，认为是有效连接
                                    valid_connections += 1
                            total_connections_found += valid_connections
                            print(f"  发现导通关系: {valid_connections}个")
                        else:
                            print(f"  发现导通关系: 0个")
                    else:
                        # 计算不导通关系数量
                        request = result['request']
                        non_conductive_count = len(request.test_points)
                        total_non_conductive_relations += non_conductive_count
                        print(f"  电源点{request.power_source}与{non_conductive_count}个目标点不导通")
            else:
                failed_tests += 1
        
        print(f"测试结果分析:")
        print(f"  成功测试: {successful_tests}")
        print(f"  失败测试: {failed_tests}")
        print(f"  发现导通关系: {total_connections_found}")
        print(f"  确认不导通关系: {total_non_conductive_relations}")
        
        return {
            'successful_tests': successful_tests,
            'failed_tests': failed_tests,
            'total_connections_found': total_connections_found,
            'total_non_conductive_relations': total_non_conductive_relations
        }
    
    def run_efficient_batch_testing(self, max_rounds: int = 3):
        """运行高效批量测试流程"""
        print("=== 开始高效批量测试流程 ===")
        print(f"批量大小: {self.batch_size}")
        print(f"并发请求数: {self.max_concurrent_requests}")
        print(f"请求批次大小: {self.request_batch_size}")
        print(f"目标: 通过批量测试快速填充关系矩阵")
        
        for round_num in range(1, max_rounds + 1):
            print(f"\n--- 第 {round_num} 轮高效批量测试 ---")
            
            # 更新关系矩阵
            self.update_matrices()
            
            # 分析当前效率
            efficiency = self.analyze_matrix_efficiency()
            if efficiency:
                print(f"当前检测率: {efficiency['detected']['rate']:.1f}%")
                print(f"已知关系: {efficiency['detected']['conductive'] + efficiency['detected']['non_conductive']}")
                print(f"未知关系: {efficiency['detected']['unknown']}")
            
            # 检查是否已完成大部分测试
            if efficiency and efficiency['detected']['rate'] > 95:
                print("检测率已超过95%，测试基本完成")
                break
            
            # 选择批量测试点位
            batch_points = self.select_batch_points()
            if not batch_points:
                print("没有更多点位可进行批量测试")
                break
            
            # 规划大规模批量测试
            test_requests = self.plan_massive_batch_tests(batch_points)
            if not test_requests:
                print("没有更多测试请求")
                break
            
            print(f"本轮将执行 {len(test_requests)} 个大规模批量测试")
            
            # 批量执行测试
            start_time = time.time()
            test_results = self.run_experiment_batch(test_requests)
            end_time = time.time()
            
            print(f"批量测试完成，耗时: {end_time - start_time:.2f}秒")
            
            # 分析测试结果
            analysis = self.analyze_test_results(test_results)
            
            # 更新统计信息
            self.total_tests += analysis['successful_tests']
            
            # 轮次间延迟
            if round_num < max_rounds:
                print(f"等待 {2} 秒后开始下一轮...")
                time.sleep(2)
        
        # 最终统计
        print("\n=== 高效批量测试完成 ===")
        self.print_final_statistics()
    
    def run_adaptive_batch_testing(self, target_detection_rate: float = 95.0):
        """运行自适应批量测试流程"""
        print("=== 开始自适应批量测试流程 ===")
        print(f"目标检测率: {target_detection_rate}%")
        
        round_num = 0
        while True:
            round_num += 1
            print(f"\n--- 第 {round_num} 轮自适应批量测试 ---")
            
            # 更新关系矩阵
            self.update_matrices()
            
            # 分析当前效率
            efficiency = self.analyze_matrix_efficiency()
            if not efficiency:
                print("无法获取矩阵效率信息，退出")
                break
            
            current_rate = efficiency['detected']['rate']
            print(f"当前检测率: {current_rate:.1f}%")
            print(f"已知关系: {efficiency['detected']['conductive'] + efficiency['detected']['non_conductive']}")
            print(f"未知关系: {efficiency['detected']['unknown']}")
            
            # 检查是否达到目标
            if current_rate >= target_detection_rate:
                print(f"已达到目标检测率 {target_detection_rate}%，测试完成")
                break
            
            # 根据当前检测率调整批量大小
            if current_rate < 50:
                self.batch_size = min(50, self.batch_size + 10)  # 最大限制在50
                print(f"检测率较低，增加批量大小到 {self.batch_size}")
            elif current_rate < 80:
                self.batch_size = max(25, self.batch_size - 5)   # 适度减少批量大小
                print(f"检测率中等，调整批量大小到 {self.batch_size}")
            else:
                self.batch_size = max(20, self.batch_size - 10)  # 大幅减少批量大小
                print(f"检测率较高，减少批量大小到 {self.batch_size}")
            
            # 选择批量测试点位
            batch_points = self.select_batch_points()
            if not batch_points:
                print("没有更多点位可进行批量测试")
                break
            
            # 规划大规模批量测试
            test_requests = self.plan_massive_batch_tests(batch_points)
            if not test_requests:
                print("没有更多测试请求")
                break
            
            print(f"本轮将执行 {len(test_requests)} 个大规模批量测试")
            
            # 批量执行测试
            start_time = time.time()
            test_results = self.run_experiment_batch(test_requests)
            end_time = time.time()
            
            print(f"批量测试完成，耗时: {end_time - start_time:.2f}秒")
            
            # 分析测试结果
            analysis = self.analyze_test_results(test_results)
            
            # 更新统计信息
            self.total_tests += analysis['successful_tests']
            
            # 检查是否有进展
            if analysis['successful_tests'] == 0:
                print("本轮没有成功执行的测试，可能已达到极限")
                break
            
            # 轮次间延迟
            print(f"等待 {1} 秒后开始下一轮...")
            time.sleep(1)
        
        # 最终统计
        print("\n=== 自适应批量测试完成 ===")
        self.print_final_statistics()
    
    def run_binary_search_testing(self, target_detection_rate: float = 95.0):
        """运行二分法智能测试流程"""
        print("=== 开始二分法智能测试流程 ===")
        print(f"目标检测率: {target_detection_rate}%")
        print("策略: 对单个点通过二分法逐步找出其导通的点，并对其他所有点确认不导通")
        
        round_num = 0
        while True:
            round_num += 1
            print(f"\n--- 第 {round_num} 轮二分法智能测试 ---")
            
            # 更新关系矩阵
            self.update_matrices()
            
            # 分析当前效率
            efficiency = self.analyze_matrix_efficiency()
            if not efficiency:
                print("无法获取矩阵效率信息，退出")
                break
            
            current_rate = efficiency['detected']['rate']
            print(f"当前检测率: {current_rate:.1f}%")
            print(f"已知关系: {efficiency['detected']['conductive'] + efficiency['detected']['non_conductive']}")
            print(f"未知关系: {efficiency['detected']['unknown']}")
            
            # 检查是否达到目标
            if current_rate >= target_detection_rate:
                print(f"已达到目标检测率 {target_detection_rate}%，测试完成")
                break
            
            # 选择最优的电源点进行二分法测试
            optimal_source = self.select_optimal_binary_source()
            if optimal_source is None:
                print("没有找到合适的电源点进行二分法测试")
                break
            
            print(f"选择电源点 {optimal_source} 进行二分法测试")
            
            # 执行二分法测试
            test_results = self.run_binary_search_test(optimal_source)
            
            # 分析测试结果
            if test_results:
                analysis = self.analyze_binary_test_results(test_results)
                self.total_tests += analysis['successful_tests']
                print(f"二分法测试完成，发现 {analysis['conductive_found']} 个导通关系")
            
            # 轮次间延迟
            print(f"等待 {1} 秒后开始下一轮...")
            time.sleep(1)
        
        # 最终统计
        print("\n=== 二分法智能测试完成 ===")
        self.print_final_statistics()
    
    def run_hybrid_strategy_testing(self, target_detection_rate: float = 95.0):
        """运行混合策略测试流程：分块策略 + 二分法策略"""
        print("=== 开始混合策略测试流程 ===")
        print(f"目标检测率: {target_detection_rate}%")
        print("策略: 前序使用分块策略快速确认关系，后续使用二分法策略精细化处理")
        
        round_num = 0
        phase = "block"  # 当前阶段：block(分块) 或 binary(二分法)
        
        while True:
            round_num += 1
            print(f"\n--- 第 {round_num} 轮混合策略测试 ({phase}阶段) ---")
            
            # 更新关系矩阵
            self.update_matrices()
            
            # 分析当前效率
            efficiency = self.analyze_matrix_efficiency()
            if not efficiency:
                print("无法获取矩阵效率信息，退出")
                break
            
            current_rate = efficiency['detected']['rate']
            print(f"当前检测率: {current_rate:.1f}%")
            print(f"已知关系: {efficiency['detected']['conductive'] + efficiency['detected']['non_conductive']}")
            print(f"未知关系: {efficiency['detected']['unknown']}")
            
            # 检查是否达到目标
            if current_rate >= target_detection_rate:
                print(f"已达到目标检测率 {target_detection_rate}%，测试完成")
                break
            
            # 阶段切换逻辑
            if phase == "block" and current_rate >= 70.0:
                # 当检测率达到70%时，切换到二分法策略
                phase = "binary"
                print(f"检测率达到70%，切换到二分法策略进行精细化处理")
                print("策略说明：")
                print("  - 分块策略已完成大部分关系的快速确认")
                print("  - 二分法策略将针对剩余未知关系进行精确测试")
                print("  - 优先测试高概率导通的点位，提高测试效率")
            
            # 根据当前阶段选择测试策略
            if phase == "block":
                # 分块策略阶段
                print(f"执行分块策略测试（第{round_num}轮）")
                test_results = self.run_block_strategy_phase()
            else:
                # 二分法策略阶段
                print(f"执行二分法策略测试（第{round_num}轮）")
                test_results = self.run_binary_strategy_phase()
            
            # 分析测试结果
            if test_results:
                if phase == "block":
                    analysis = self.analyze_test_results(test_results)
                    self.total_tests += analysis['successful_tests']
                    print(f"分块策略测试完成，发现 {analysis['total_connections_found']} 个导通关系")
                else:
                    analysis = self.analyze_binary_test_results(test_results)
                    self.total_tests += analysis['successful_tests']
                    print(f"二分法策略测试完成，发现 {analysis['conductive_found']} 个导通关系")
            
            # 轮次间延迟
            delay_time = 2 if phase == "block" else 1
            print(f"等待 {delay_time} 秒后开始下一轮...")
            time.sleep(delay_time)
        
        # 最终统计
        print("\n=== 混合策略测试完成 ===")
        self.print_final_statistics()
    
    def run_block_strategy_phase(self) -> List[Dict[str, Any]]:
        """执行分块策略阶段测试（优化版本：所有点位轮询作为通电点位）"""
        print("分块策略：使用大规模批量测试快速确认关系")
        print("优化策略：所有点位轮询作为通电点位，优化继电器切换")
        
        # 选择批量测试点位（使用50%策略）
        batch_points = self.select_batch_points()
        if not batch_points:
            print("没有更多点位可进行分块测试")
            return []
        
        # 优化：确保所有点位都有机会作为通电点位
        all_points = list(range(self.total_points))
        power_source_candidates = [p for p in all_points if self.has_unknown_relations(p)]
        
        if not power_source_candidates:
            print("所有点位都没有未知关系，分块策略完成")
            return []
        
        print(f"找到 {len(power_source_candidates)} 个可作为通电点位的候选点")
        print(f"目标：让每个候选点都有机会作为通电点位进行测试")
        
        # 规划优化的分块测试请求
        test_requests = self.plan_optimized_block_tests(batch_points, power_source_candidates)
        if not test_requests:
            print("没有更多测试请求")
            return []
        
        print(f"分块策略将执行 {len(test_requests)} 个优化批量测试")
        print("策略：优先选择未知关系多的点位作为通电点位，优化继电器切换顺序")
        
        # 继电器切换优化
        optimized_requests = self.optimize_relay_switching(test_requests)
        
        # 跟踪继电器操作
        self.track_relay_operations(optimized_requests)
        
        # 批量执行测试
        start_time = time.time()
        test_results = self.run_experiment_batch(optimized_requests)
        end_time = time.time()
        
        print(f"分块策略测试完成，耗时: {end_time - start_time:.2f}秒")
        
        return test_results
    
    def has_unknown_relations(self, point: int) -> bool:
        """检查点位是否还有未知关系"""
        if not self.relationship_matrix:
            return False
        
        for j in range(self.total_points):
            if j != point and self.relationship_matrix[point][j] == 0:
                return True
        return False
    
    def plan_optimized_block_tests(self, batch_points: List[int], power_source_candidates: List[int]) -> List[TestRequest]:
        """规划优化的分块测试（所有点位轮询作为通电点位）"""
        if not batch_points or not power_source_candidates:
            return []
        
        test_requests = []
        tested_combinations = set()  # 记录已测试的组合，避免重复
        
        # 策略1: 优先选择未知关系最多的点位作为通电点位
        # 策略2: 优化继电器切换顺序，减少切换次数
        power_source_scores = []
        
        for power_source in power_source_candidates:
            unknown_count = 0
            potential_targets = []
            
            # 计算该点位作为通电点位时的未知关系数量
            for target in batch_points:
                if target != power_source:
                    if self.relationship_matrix[power_source][target] == 0:  # 未知关系
                        unknown_count += 1
                        potential_targets.append(target)
            
            if unknown_count > 0:
                # 评分：未知关系数量 + 继电器切换优化
                score = unknown_count * 10 + len(potential_targets) * 2
                power_source_scores.append((power_source, score, unknown_count, potential_targets))
        
        # 按评分排序，优先选择高分点位作为通电点位
        power_source_scores.sort(key=lambda x: x[1], reverse=True)
        
        print(f"通电点位优先级排序（前5个）:")
        for i, (power_source, score, unknown_count, potential_targets) in enumerate(power_source_scores[:5]):
            print(f"  {i+1}. 点位{power_source}: 评分{score}, 未知关系{unknown_count}个")
        
        # 为每个通电点位生成测试请求
        for power_source, score, unknown_count, potential_targets in power_source_scores:
            if not potential_targets:
                continue
            
            # 过滤掉已知关系的点位和已测试的组合
            filtered_targets = []
            for target in potential_targets:
                # 检查是否已知关系
                if self.relationship_matrix[power_source][target] == 0:  # 未知关系
                    # 检查是否已经测试过这个组合
                    combination = tuple(sorted([power_source, target]))
                    if combination not in tested_combinations:
                        filtered_targets.append(target)
                        tested_combinations.add(combination)
            
            if filtered_targets:
                # 避免生成过大的批次，分批处理
                max_targets_per_batch = 25  # 每批最多25个目标点
                for j in range(0, len(filtered_targets), max_targets_per_batch):
                    batch_targets = filtered_targets[j:j + max_targets_per_batch]
                    
                    test_requests.append(TestRequest(
                        power_source=power_source,
                        test_points=batch_targets,
                        strategy='optimized_block_phase',
                        batch_size=len(batch_targets),
                        priority=unknown_count  # 优先级基于未知关系数量
                    ))
        
        # 按优先级排序，高优先级的先执行
        test_requests.sort(key=lambda x: x.priority, reverse=True)
        
        print(f"生成了 {len(test_requests)} 个优化分块测试请求")
        print(f"避免了 {len(tested_combinations)} 个重复测试组合")
        print(f"通电点位轮询策略：优先选择未知关系多的点位作为通电点位")
        
        return test_requests
    
    def run_binary_strategy_phase(self) -> List[Dict[str, Any]]:
        """执行二分法策略阶段测试"""
        print("二分法策略：针对剩余未知关系进行精确测试")
        
        # 选择最优的电源点进行二分法测试
        optimal_source = self.select_optimal_binary_source()
        if optimal_source is None:
            print("没有找到合适的电源点进行二分法测试")
            return []
        
        print(f"选择电源点 {optimal_source} 进行二分法测试")
        
        # 执行二分法测试
        test_results = self.run_binary_search_test(optimal_source)
        
        return test_results
    
    def select_optimal_binary_source(self) -> Optional[int]:
        """选择最优的电源点进行二分法测试"""
        if not self.relationship_matrix:
            return None
        
        # 策略：选择未知关系最多且可能导通关系最多的点位作为电源点
        candidate_scores = []
        
        for i in range(self.total_points):
            unknown_count = 0
            potential_conductive = 0
            
            for j in range(self.total_points):
                if i != j:
                    if self.relationship_matrix[i][j] == 0:  # 未知关系
                        unknown_count += 1
                        # 基于已知信息估算导通概率
                        if self.estimate_conductivity_probability(i, j) > 0.5:
                            potential_conductive += 1
            
            if unknown_count > 0:  # 只考虑还有未知关系的点位
                # 评分公式：未知关系数量 * 0.7 + 潜在导通关系数量 * 0.3
                score = unknown_count * 0.7 + potential_conductive * 0.3
                candidate_scores.append((i, score, unknown_count, potential_conductive))
        
        if not candidate_scores:
            return None
        
        # 按评分排序，选择最优的
        candidate_scores.sort(key=lambda x: x[1], reverse=True)
        best_candidate = candidate_scores[0]
        
        print(f"最优电源点候选: 点位{best_candidate[0]}, 评分{best_candidate[1]:.2f}")
        print(f"  未知关系: {best_candidate[2]}, 潜在导通: {best_candidate[3]}")
        
        return best_candidate[0]
    
    def estimate_conductivity_probability(self, point1: int, point2: int) -> float:
        """估算两个点位之间的导通概率"""
        if not self.relationship_matrix:
            return 0.5
        
        # 基于已知的导通关系模式估算
        # 如果两个点位都与某个共同点位导通，则它们导通的概率较高
        
        common_conductive_neighbors = 0
        total_common_neighbors = 0
        
        for k in range(self.total_points):
            if k != point1 and k != point2:
                # 检查k是否与point1和point2都有已知关系
                if (self.relationship_matrix[point1][k] != 0 and 
                    self.relationship_matrix[point2][k] != 0):
                    total_common_neighbors += 1
                    # 如果都与k导通，增加导通概率
                    if (self.relationship_matrix[point1][k] == 1 and 
                        self.relationship_matrix[point2][k] == 1):
                        common_conductive_neighbors += 1
        
        if total_common_neighbors == 0:
            return 0.5  # 默认概率
        
        # 基于共同导通邻居的比例估算
        conductivity_ratio = common_conductive_neighbors / total_common_neighbors
        
        # 考虑全局导通密度
        global_conductivity = self.get_global_conductivity_density()
        
        # 综合概率：局部模式 * 0.7 + 全局密度 * 0.3
        final_probability = conductivity_ratio * 0.7 + global_conductivity * 0.3
        
        return max(0.1, min(0.9, final_probability))  # 限制在[0.1, 0.9]范围内
    
    def get_global_conductivity_density(self) -> float:
        """获取全局导通密度"""
        if not self.relationship_matrix:
            return 0.5
        
        total_known = 0
        total_conductive = 0
        
        for i in range(self.total_points):
            for j in range(self.total_points):
                if i != j and self.relationship_matrix[i][j] != 0:
                    total_known += 1
                    if self.relationship_matrix[i][j] == 1:
                        total_conductive += 1
        
        if total_known == 0:
            return 0.5
        
        return total_conductive / total_known
    
    def run_binary_search_test(self, power_source: int) -> List[Dict[str, Any]]:
        """对指定电源点执行二分法测试"""
        print(f"开始对电源点 {power_source} 执行二分法测试...")
        
        # 获取所有未知关系的目标点
        unknown_targets = []
        for j in range(self.total_points):
            if j != power_source and self.relationship_matrix[power_source][j] == 0:
                unknown_targets.append(j)
        
        if not unknown_targets:
            print(f"电源点 {power_source} 没有未知关系的目标点")
            return []
        
        print(f"找到 {len(unknown_targets)} 个未知关系的目标点")
        
        # 按导通概率排序目标点，优先测试高概率点位
        unknown_targets.sort(key=lambda x: self.estimate_conductivity_probability(power_source, x), reverse=True)
        
        # 分批测试，每批大小适中以提高效率（调整为50%策略）
        batch_size = min(25, len(unknown_targets) // 2)  # 每批最多25个，或未知关系的一半
        if batch_size < 10:  # 确保最小批次大小
            batch_size = min(10, len(unknown_targets))
        test_results = []
        
        for i in range(0, len(unknown_targets), batch_size):
            batch_targets = unknown_targets[i:i + batch_size]
            print(f"测试批次 {i//batch_size + 1}: 电源点{power_source} -> {len(batch_targets)}个目标点")
            
            # 执行测试
            result = self.run_experiment(power_source, batch_targets)
            if result.get('success'):
                test_results.append({
                    'power_source': power_source,
                    'targets': batch_targets,
                    'result': result,
                    'success': True
                })
                
                # 分析结果，更新关系矩阵
                self.update_relationship_from_test(power_source, batch_targets, result)
            else:
                print(f"批次测试失败: {result.get('error', '未知错误')}")
                test_results.append({
                    'power_source': power_source,
                    'targets': batch_targets,
                    'result': result,
                    'success': False
                })
        
        return test_results
    
    def update_relationship_from_test(self, power_source: int, targets: List[int], test_result: Dict):
        """从测试结果更新关系矩阵"""
        if not test_result.get('success'):
            return
        
        test_data = test_result.get('data', {}).get('test_result', {})
        if not test_data:
            return
        
        # 获取检测到的导通关系
        detected_connections = test_data.get('connections', [])
        
        # 处理不同类型的connections数据
        if isinstance(detected_connections, list):
            # 如果是列表，提取点位ID
            detected_points = []
            for conn in detected_connections:
                if isinstance(conn, dict):
                    # 如果是字典，尝试提取point_id或id字段
                    point_id = conn.get('point_id') or conn.get('id')
                    if point_id is not None:
                        detected_points.append(point_id)
                elif isinstance(conn, (int, str)):
                    # 如果是数字或字符串，直接转换
                    try:
                        detected_points.append(int(conn))
                    except (ValueError, TypeError):
                        continue
        else:
            detected_points = []
        
        # 转换为集合以便快速查找
        detected_set = set(detected_points)
        
        # 更新关系矩阵
        for target in targets:
            if target in detected_set:
                # 导通关系
                self.relationship_matrix[power_source][target] = 1
                self.relationship_matrix[target][power_source] = 1  # 对称关系
                print(f"  确认: 点位{power_source} <-> 点位{target} 导通")
            else:
                # 不导通关系
                self.relationship_matrix[power_source][target] = -1
                self.relationship_matrix[target][power_source] = -1  # 对称关系
                print(f"  确认: 点位{power_source} <-> 点位{target} 不导通")
    
    def analyze_binary_test_results(self, test_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """分析二分法测试结果"""
        print("分析二分法测试结果...")
        
        successful_tests = 0
        failed_tests = 0
        conductive_found = 0
        non_conductive_confirmed = 0
        
        for result in test_results:
            if result['success']:
                successful_tests += 1
                
                # 统计导通和不导通的关系
                test_data = result['result'].get('data', {}).get('test_result', {})
                if test_data:
                    connections = test_data.get('connections', [])
                    
                    # 处理不同类型的connections数据
                    if isinstance(connections, list):
                        # 如果是列表，计算有效连接数
                        valid_connections = 0
                        for conn in connections:
                            if isinstance(conn, dict):
                                # 如果是字典，检查是否有有效数据
                                if conn.get('point_id') is not None or conn.get('id') is not None:
                                    valid_connections += 1
                            elif isinstance(conn, (int, str)):
                                # 如果是数字或字符串，认为是有效连接
                                valid_connections += 1
                        conductive_found += valid_connections
                    else:
                        conductive_found += 0
                    
                    # 计算不导通关系数量
                    total_targets = len(result['targets'])
                    non_conductive_confirmed += (total_targets - conductive_found)
            else:
                failed_tests += 1
        
        print(f"二分法测试结果分析:")
        print(f"  成功测试: {successful_tests}")
        print(f"  失败测试: {failed_tests}")
        print(f"  发现导通关系: {conductive_found}")
        print(f"  确认不导通关系: {non_conductive_confirmed}")
        
        return {
            'successful_tests': successful_tests,
            'failed_tests': failed_tests,
            'conductive_found': conductive_found,
            'non_conductive_confirmed': non_conductive_confirmed
        }
    
    def analyze_test_redundancy(self) -> Dict[str, Any]:
        """分析测试冗余度"""
        if not self.relationship_matrix:
            return {}
        
        total_off_diagonal = self.total_points * (self.total_points - 1)
        known_relations = 0
        unknown_relations = 0
        redundant_potential = 0
        
        for i in range(self.total_points):
            for j in range(self.total_points):
                if i != j:
                    if self.relationship_matrix[i][j] != 0:
                        known_relations += 1
                        # 检查是否可能产生冗余测试
                        if self.relationship_matrix[i][j] == 1:  # 导通关系
                            # 如果两个点都导通，它们之间的测试可能是冗余的
                            redundant_potential += 1
                    else:
                        unknown_relations += 1
        
        redundancy_rate = redundant_potential / total_off_diagonal * 100 if total_off_diagonal > 0 else 0
        efficiency_rate = known_relations / total_off_diagonal * 100 if total_off_diagonal > 0 else 0
        
        return {
            'total_off_diagonal': total_off_diagonal,
            'known_relations': known_relations,
            'unknown_relations': unknown_relations,
            'redundant_potential': redundant_potential,
            'redundancy_rate': redundancy_rate,
            'efficiency_rate': efficiency_rate,
            'recommendation': self._get_redundancy_recommendation(redundancy_rate, efficiency_rate)
        }
    
    def _get_redundancy_recommendation(self, redundancy_rate: float, efficiency_rate: float) -> str:
        """根据冗余度和效率给出建议"""
        if redundancy_rate > 30:
            return "冗余度较高，建议使用二分法智能测试减少重复"
        elif efficiency_rate < 50:
            return "效率较低，建议增加批量大小到50%覆盖率"
        elif efficiency_rate < 80:
            return "效率中等，建议优化测试策略，避免已知关系"
        else:
            return "效率良好，可以继续当前策略"
    
    def print_redundancy_analysis(self):
        """打印冗余度分析结果"""
        analysis = self.analyze_test_redundancy()
        if not analysis:
            print("无法分析测试冗余度")
            return
        
        print("\n=== 测试冗余度分析 ===")
        print(f"总非对角线关系: {analysis['total_off_diagonal']}")
        print(f"已知关系: {analysis['known_relations']}")
        print(f"未知关系: {analysis['unknown_relations']}")
        print(f"潜在冗余: {analysis['redundant_potential']}")
        print(f"冗余率: {analysis['redundancy_rate']:.1f}%")
        print(f"效率率: {analysis['efficiency_rate']:.1f}%")
        print(f"建议: {analysis['recommendation']}")
    
    def print_final_statistics(self):
        """打印最终统计信息"""
        print(f"总测试次数: {self.total_tests}")
        print(f"已测试点对: {len(self.tested_pairs)}")
        print(f"确认导通: {len(self.confirmed_conductive)}")
        print(f"确认不导通: {len(self.confirmed_non_conductive)}")
        
        # 继电器操作统计
        if self.relay_optimization_enabled:
            print(f"继电器切换次数: {self.relay_switch_count}")
            if self.total_tests > 0:
                avg_switches_per_test = self.relay_switch_count / self.total_tests
                print(f"平均每次测试继电器切换: {avg_switches_per_test:.2f}次")
            
            # 添加继电器优化统计
            self.print_relay_optimization_stats()
        
        # 系统信息统计
        print("\n=== 系统状态统计 ===")
        system_info = self.get_system_info()
        if system_info.get('success'):
            data = system_info['data']
            print(f"总点位: {data['total_points']}")
            print(f"已确认点位数量: {data.get('confirmed_points_count', 0)}")
            print(f"总测试次数: {data['total_tests']}")
            print(f"继电器操作总次数: {data['total_relay_operations']}")
            
            # 计算确认率
            if data['total_points'] > 1:
                total_possible_relations = data['total_points'] * (data['total_points'] - 1) // 2
                confirmed_rate = data.get('confirmed_points_count', 0) / total_possible_relations * 100
                print(f"点位关系确认率: {confirmed_rate:.1f}%")

    def get_strategy_recommendation(self) -> Dict[str, Any]:
        """获取策略建议"""
        if not self.relationship_matrix:
            return {}
        
        efficiency = self.analyze_matrix_efficiency()
        if not efficiency:
            return {}
        
        current_rate = efficiency['detected']['rate']
        
        # 基于当前检测率给出策略建议
        if current_rate < 50:
            recommendation = {
                'strategy': 'block',
                'reason': '检测率较低，建议使用分块策略快速确认关系',
                'priority': 'high',
                'expected_improvement': '15-25%'
            }
        elif current_rate < 70:
            recommendation = {
                'strategy': 'block',
                'reason': '检测率中等，继续使用分块策略提高覆盖率',
                'priority': 'medium',
                'expected_improvement': '10-20%'
            }
        elif current_rate < 85:
            recommendation = {
                'strategy': 'hybrid',
                'reason': '检测率较高，建议切换到混合策略：分块+二分法',
                'priority': 'medium',
                'expected_improvement': '8-15%'
            }
        else:
            recommendation = {
                'strategy': 'binary',
                'reason': '检测率很高，建议使用二分法策略精细化处理',
                'priority': 'low',
                'expected_improvement': '3-8%'
            }
        
        return {
            'current_rate': current_rate,
            'recommendation': recommendation,
            'efficiency_analysis': efficiency
        }
    
    def print_strategy_analysis(self):
        """打印策略分析结果"""
        analysis = self.get_strategy_recommendation()
        if not analysis:
            print("无法分析策略建议")
            return
        
        print("\n=== 策略分析 ===")
        print(f"当前检测率: {analysis['current_rate']:.1f}%")
        print(f"推荐策略: {analysis['recommendation']['strategy']}")
        print(f"推荐原因: {analysis['recommendation']['reason']}")
        print(f"优先级: {analysis['recommendation']['priority']}")
        print(f"预期改进: {analysis['recommendation']['expected_improvement']}")
        
        # 显示效率分析
        efficiency = analysis['efficiency_analysis']
        print(f"效率详情:")
        print(f"  已知导通: {efficiency['detected']['conductive']}")
        print(f"  已知不导通: {efficiency['detected']['non_conductive']}")
        print(f"  未知关系: {efficiency['detected']['unknown']}")
        
        # 给出具体建议
        if analysis['recommendation']['strategy'] == 'hybrid':
            print("\n混合策略执行建议:")
            print("1. 继续使用分块策略直到检测率达到70%")
            print("2. 然后切换到二分法策略进行精细化处理")
            print("3. 优先测试高概率导通的点位")
        elif analysis['recommendation']['strategy'] == 'block':
            print("\n分块策略执行建议:")
            print("1. 使用50%覆盖率策略平衡效率和负载")
            print("2. 智能去重避免重复测试")
            print("3. 优先选择未知关系多的点位")
        else:
            print("\n二分法策略执行建议:")
            print("1. 针对剩余未知关系进行精确测试")
            print("2. 使用概率估算优化测试顺序")
            print("3. 小批次测试提高精度")

    def optimize_relay_switching(self, test_requests: List[TestRequest]) -> List[TestRequest]:
        """优化继电器切换顺序，减少切换次数"""
        if not self.relay_optimization_enabled or not test_requests:
            return test_requests
        
        print("优化继电器切换顺序...")
        
        # 按通电点位分组
        power_source_groups = {}
        for request in test_requests:
            power_source = request.power_source
            if power_source not in power_source_groups:
                power_source_groups[power_source] = []
            power_source_groups[power_source].append(request)
        
        # 计算每个通电点位的总目标数
        power_source_totals = {}
        for power_source, requests in power_source_groups.items():
            total_targets = sum(len(req.test_points) for req in requests)
            power_source_totals[power_source] = total_targets
        
        # 按总目标数排序，优先选择目标数多的通电点位
        sorted_power_sources = sorted(power_source_totals.items(), key=lambda x: x[1], reverse=True)
        
        print(f"通电点位优化排序（按目标数）:")
        for i, (power_source, total_targets) in enumerate(sorted_power_sources[:5]):
            print(f"  {i+1}. 点位{power_source}: {total_targets}个目标")
        
        # 重新组织测试请求，相同通电点位的请求连续执行
        optimized_requests = []
        for power_source, _ in sorted_power_sources:
            if power_source in power_source_groups:
                optimized_requests.extend(power_source_groups[power_source])
        
        # 计算继电器切换次数
        switch_count = 0
        last_power_source = None
        for request in optimized_requests:
            if last_power_source is not None and request.power_source != last_power_source:
                switch_count += 1
            last_power_source = request.power_source
        
        print(f"继电器切换优化完成:")
        print(f"  原始顺序切换次数: {len(set(req.power_source for req in test_requests))}")
        print(f"  优化后切换次数: {switch_count}")
        print(f"  减少切换次数: {len(set(req.power_source for req in test_requests)) - switch_count}")
        
        return optimized_requests
    
    def track_relay_operations(self, test_requests: List[TestRequest]):
        """跟踪继电器操作"""
        if not test_requests:
            return
        
        # 计算继电器切换次数
        switch_count = 0
        last_power_source = None
        
        for request in test_requests:
            if last_power_source is not None and request.power_source != last_power_source:
                switch_count += 1
            last_power_source = request.power_source
        
        self.relay_switch_count += switch_count
        print(f"继电器操作统计:")
        print(f"  本轮切换次数: {switch_count}")
        print(f"  累计切换次数: {self.relay_switch_count}")
        
        # 更新当前通电点位
        if test_requests:
            self.current_power_source = test_requests[-1].power_source

    def get_relay_stats(self) -> Dict[str, Any]:
        """获取继电器操作统计信息"""
        try:
            response = self.session.get(f"{self.base_url}/api/relay/stats")
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            print(f"获取继电器统计信息失败: {e}")
        return {}
    
    def reset_relay_states(self) -> Dict[str, Any]:
        """重置所有继电器状态"""
        try:
            response = self.session.post(f"{self.base_url}/api/relay/reset")
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            print(f"重置继电器状态失败: {e}")
        return {}
    
    def print_relay_optimization_stats(self):
        """打印继电器优化统计信息"""
        relay_stats = self.get_relay_stats()
        if not relay_stats.get('success'):
            print("无法获取继电器统计信息")
            return
        
        stats = relay_stats['data']['relay_stats']
        print("\n=== 继电器优化统计 ===")
        print(f"优化后继电器操作: {stats['total_relay_operations']}次")
        print(f"传统方式继电器操作: {stats['legacy_total_operations']}次")
        print(f"优化比例: {stats['optimization_ratio']:.1f}%")
        print(f"当前通电点位: {stats['current_power_source']}")
        print(f"当前激活测试点位: {stats['active_test_points']}个")
        print(f"通电操作次数: {stats['power_on_count']}次")
        
        if stats['optimization_ratio'] > 0:
            print(f"✅ 继电器优化效果显著，减少了 {stats['optimization_ratio']:.1f}% 的操作")
        else:
            print("⚠️ 继电器优化效果不明显，可能需要进一步调整")

    def print_system_info(self):
        """打印系统信息"""
        system_info = self.get_system_info()
        if not system_info.get('success'):
            print("无法获取系统信息")
            return
        
        data = system_info['data']
        print("\n=== 系统信息 ===")
        print(f"总点位: {data['total_points']}")
        print(f"已确认点位数量: {data.get('confirmed_points_count', 0)}")  # 新增：已确认点位数量
        print(f"继电器切换时间: {data['relay_switch_time']}ms")
        print(f"总测试次数: {data['total_tests']}")
        print(f"继电器操作总次数: {data['total_relay_operations']}")
        print(f"通电次数总和: {data['total_power_on_operations']}")
        
        # 计算确认率
        if data['total_points'] > 1:
            total_possible_relations = data['total_points'] * (data['total_points'] - 1) // 2
            confirmed_rate = data.get('confirmed_points_count', 0) / total_possible_relations * 100
            print(f"点位关系确认率: {confirmed_rate:.1f}%")

def main():
    """主函数"""
    client = EfficientBatchTestClient()
    
    # 运行高效批量测试
    print("选择测试模式:")
    print("1. 固定批量大小测试")
    print("2. 自适应批量大小测试")
    print("3. 二分法智能测试")
    print("4. 混合策略测试")
    
    choice = input("请输入选择 (1, 2, 3 或 4): ").strip()
    
    if choice == "1":
        # 固定批量大小测试
        client.run_efficient_batch_testing(max_rounds=3)
    elif choice == "2":
        # 自适应批量大小测试
        target_rate = float(input("请输入目标检测率 (默认95.0): ") or "95.0")
        client.run_adaptive_batch_testing(target_detection_rate=target_rate)
    elif choice == "3":
        # 二分法智能测试
        target_rate = float(input("请输入目标检测率 (默认95.0): ") or "95.0")
        client.run_binary_search_testing(target_detection_rate=target_rate)
    elif choice == "4":
        # 混合策略测试
        target_rate = float(input("请输入目标检测率 (默认95.0): ") or "95.0")
        client.run_hybrid_strategy_testing(target_detection_rate=target_rate)
    else:
        print("无效选择，使用默认模式")
        client.run_efficient_batch_testing(max_rounds=3)

if __name__ == "__main__":
    main()
