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
        """选择批量测试的点位"""
        if not self.relationship_matrix:
            return []
        
        # 策略1: 优先选择未知关系最多的点位
        unknown_counts = []
        for i in range(self.total_points):
            unknown_count = 0
            for j in range(self.total_points):
                if i != j and self.relationship_matrix[i][j] == 0:
                    unknown_count += 1
            unknown_counts.append((i, unknown_count))
        
        # 按未知关系数量排序，选择前batch_size个
        unknown_counts.sort(key=lambda x: x[1], reverse=True)
        selected_points = [p[0] for p in unknown_counts[:self.batch_size]]
        
        print(f"选择了 {len(selected_points)} 个点位进行批量测试")
        print(f"选中的点位: {selected_points[:10]}{'...' if len(selected_points) > 10 else ''}")
        
        return selected_points
    
    def plan_massive_batch_tests(self, batch_points: List[int]) -> List[TestRequest]:
        """规划大规模批量测试"""
        if not batch_points:
            return []
        
        test_requests = []
        
        # 策略: 每个选中的点位作为电源点，测试其他所有选中的点位
        for i, power_source in enumerate(batch_points):
            # 选择其他点位作为测试目标
            test_targets = [p for p in batch_points if p != power_source]
            
            # 过滤掉已知关系的点位
            filtered_targets = []
            for target in test_targets:
                if self.relationship_matrix[power_source][target] == 0:  # 未知关系
                    filtered_targets.append(target)
            
            if filtered_targets:
                # 计算优先级（未知关系越多，优先级越高）
                priority = len(filtered_targets)
                
                test_requests.append(TestRequest(
                    power_source=power_source,
                    test_points=filtered_targets,
                    strategy='massive_batch',
                    batch_size=len(filtered_targets),
                    priority=priority
                ))
        
        # 按优先级排序，高优先级的先执行
        test_requests.sort(key=lambda x: x.priority, reverse=True)
        
        print(f"生成了 {len(test_requests)} 个大规模批量测试请求")
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
                        total_connections_found += len(connections)
                        print(f"  发现导通关系: {len(connections)}个")
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
                self.batch_size = min(80, self.batch_size + 10)  # 增加批量大小
                print(f"检测率较低，增加批量大小到 {self.batch_size}")
            elif current_rate < 80:
                self.batch_size = max(30, self.batch_size - 5)   # 适度减少批量大小
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
    
    def print_final_statistics(self):
        """打印最终统计信息"""
        print(f"总测试次数: {self.total_tests}")
        print(f"已测试点对: {len(self.tested_pairs)}")
        print(f"确认导通: {len(self.confirmed_conductive)}")
        print(f"确认不导通: {len(self.confirmed_non_conductive)}")
        
        if self.relationship_matrix:
            total_off_diagonal = self.total_points * (self.total_points - 1)
            coverage = len(self.tested_pairs) / total_off_diagonal * 100
            print(f"测试覆盖率: {coverage:.1f}%")
            
            # 计算效率提升
            efficiency = self.analyze_matrix_efficiency()
            if efficiency:
                print(f"最终检测率: {efficiency['detected']['rate']:.1f}%")
                print(f"矩阵填充效率: {efficiency['detected']['rate']:.1f}%")

def main():
    """主函数"""
    client = EfficientBatchTestClient()
    
    # 运行高效批量测试
    print("选择测试模式:")
    print("1. 固定批量大小测试")
    print("2. 自适应批量大小测试")
    
    choice = input("请输入选择 (1 或 2): ").strip()
    
    if choice == "1":
        # 固定批量大小测试
        client.run_efficient_batch_testing(max_rounds=3)
    elif choice == "2":
        # 自适应批量大小测试
        target_rate = float(input("请输入目标检测率 (默认95.0): ") or "95.0")
        client.run_adaptive_batch_testing(target_detection_rate=target_rate)
    else:
        print("无效选择，使用默认模式")
        client.run_efficient_batch_testing(max_rounds=3)

if __name__ == "__main__":
    main()
