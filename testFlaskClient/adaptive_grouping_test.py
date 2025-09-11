#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自适应分组测试实现
实现只使用二分法的测试策略
"""

import json
import time
import random
import math
import requests
import traceback
from concurrent.futures import ThreadPoolExecutor
import logging
from typing import List, Tuple, Dict, Set, Optional, Any

# 配置日志
def setup_logging(enable_logging: bool = True):
    """设置日志配置"""
    if enable_logging:
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler("adaptive_grouping.log"),
                logging.StreamHandler()
            ]
        )
    return logging.getLogger("AdaptiveGrouping")

class AdaptiveGroupingTester:
    """自适应分组测试器 - 只使用二分法策略"""
    
    def __init__(self, config: Dict, server_url: str = "http://localhost:5000"):
        """初始化测试器"""
        self.config = config
        self.server_url = server_url
        self.logger = setup_logging(config.get('enable_logging', True))
        
        # 测试状态
        self.total_points = config.get('total_points', 100)
        self.concurrency = config.get('concurrency', 4)
        self.current_phase = 0
        self.test_count = 0
        self.start_time = time.time()
        
        # 关系矩阵和状态
        self.relation_matrix = {}
        self.unknown_relations = set()
        self.known_relations = set()
        self.power_sources = set()
        
        # 初始化未知关系
        self._initialize_unknown_relations()
        
        # 二分法测试配置
        self.binary_search_config = config.get('test_execution', {}).get('binary_search', {})
        
        self.logger.info("🚀 自适应分组测试器初始化完成")
        self.logger.info(f"  总点位: {self.total_points}")
        self.logger.info(f"  并发数: {self.concurrency}")
        self.logger.info(f"  服务器地址: {self.server_url}")
        self.logger.info(f"  只使用二分法策略")
    
    def _initialize_unknown_relations(self):
        """初始化未知关系集合"""
        for i in range(1, self.total_points + 1):
            for j in range(i + 1, self.total_points + 1):
                self.unknown_relations.add((i, j))
        self.logger.info(f"🔍 初始化未知关系: {len(self.unknown_relations)} 对")
    
    def run_full_test_cycle(self):
        """运行完整的测试循环"""
        self.logger.info("📊 开始运行完整测试循环")
        self.start_time = time.time()
        
        try:
            # 只执行二分法测试阶段
            self._run_binary_search_phase()
            
            # 测试完成
            self.logger.info("✅ 测试循环完成")
            self.print_current_status()
            self._save_results()
            
        except Exception as e:
            self.logger.error(f"❌ 测试过程中发生错误: {str(e)}")
            traceback.print_exc()
            self.print_current_status()
    
    def _run_binary_search_phase(self):
        """运行二分法测试阶段 - 实现真正的二分法策略"""
        self.logger.info("🔍 开始二分法测试阶段")
        max_tests = self.config.get('test_execution', {}).get('max_total_tests', 2000)
        
        # 导入二分法配置
        try:
            from binary_search_config import BATCH_SIZING
            initial_batch_size = BATCH_SIZING.get('initial_batch_size', 20)
            min_batch_size = BATCH_SIZING.get('min_batch_size', 10)
            max_batch_size = BATCH_SIZING.get('max_batch_size', 30)
            self.logger.info(f"📊 加载二分法配置: 初始批次大小={initial_batch_size}, 最小={min_batch_size}, 最大={max_batch_size}")
        except:
            # 如果配置加载失败，使用默认值
            initial_batch_size = 20
            min_batch_size = 10
            max_batch_size = 30
            self.logger.warning(f"⚠️  无法加载二分法配置，使用默认值: 初始批次大小={initial_batch_size}")
        
        with ThreadPoolExecutor(max_workers=self.concurrency) as executor:
            while self.test_count < max_tests and self.unknown_relations:
                remaining_tests = max_tests - self.test_count
                tests_to_run = min(remaining_tests, self.concurrency)
                
                # 准备二分法测试任务
                test_tasks = []
                for _ in range(tests_to_run):
                    if not self.unknown_relations:
                        break
                    
                    # 1. 选择一个电源点（source）
                    # 收集所有可能的源点
                    potential_sources = set()
                    for pair in self.unknown_relations:
                        potential_sources.add(pair[0])
                    
                    if not potential_sources:
                        break
                    
                    # 随机选择一个源点
                    source = random.choice(list(potential_sources))
                    
                    # 2. 收集该源点相关的所有未知关系目标点
                    source_unknown_dests = []
                    for pair in list(self.unknown_relations):
                        if pair[0] == source:
                            source_unknown_dests.append(pair[1])
                    
                    if not source_unknown_dests:
                        continue
                    
                    # 3. 根据配置确定批次大小
                    # 批次大小应该根据剩余未知点数动态调整
                    batch_size = min(len(source_unknown_dests), initial_batch_size)
                    batch_size = max(min(batch_size, max_batch_size), min_batch_size)
                    
                    # 4. 随机选择一批目标点进行二分测试
                    selected_dests = random.sample(source_unknown_dests, min(batch_size, len(source_unknown_dests)))
                    
                    # 记录这个批次的测试任务
                    test_tasks.append((source, selected_dests))
                    
                    # 从未知关系中移除这些点对，避免重复测试
                    for dest in selected_dests:
                        if (source, dest) in self.unknown_relations:
                            self.unknown_relations.remove((source, dest))
                
                # 执行测试任务
                futures = [executor.submit(self._perform_binary_batch_test, src, dests) for src, dests in test_tasks]
                
                # 等待所有任务完成
                for future in futures:
                    try:
                        future.result()
                    except Exception as e:
                        self.logger.error(f"❌ 测试任务执行失败: {str(e)}")
            
        self.logger.info(f"📋 二分法测试阶段结束")
        self.logger.info(f"  总测试次数: {self.test_count}")
        self.logger.info(f"  剩余未知关系: {len(self.unknown_relations)}")
    
    def _perform_binary_test(self, source: int, destination: int):
        """执行二分法测试 - 一对一版本"""
        try:
            self.test_count += 1
            
            # 构建测试请求 - 使用主服务器期望的参数格式
            test_data = {
                "power_source": source,
                "test_points": [destination],
                "strategy": "binary_search",
                "phase": self.current_phase
            }
            
            # 发送测试请求到服务器 - 注意：使用正确的API端点/api/experiment
            response = requests.post(
                f"{self.server_url}/api/experiment",
                json=test_data,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                self._update_relation_matrix(source, destination, result)
                
                # 打印测试进度
                if self.test_count % 10 == 0:
                    self.logger.info(f"📈 测试进度: {self.test_count} 次测试完成")
                    
            else:
                self.logger.error(f"❌ 测试请求失败: HTTP {response.status_code}")
                # 将点位对重新添加到未知关系中
                self.unknown_relations.add((source, destination))
                
        except Exception as e:
            self.logger.error(f"❌ 测试执行异常 (源: {source}, 目标: {destination}): {str(e)}")
            # 将点位对重新添加到未知关系中
            self.unknown_relations.add((source, destination))
    
    def _perform_binary_batch_test(self, source: int, destinations: List[int]):
        """执行二分法批次测试"""
        try:
            self.test_count += 1
            
            # 记录批次信息
            self.logger.info(f"📋 执行二分法批次测试 (源: {source}, 目标点数: {len(destinations)})")
            
            # 构建测试请求 - 使用主服务器期望的参数格式
            test_data = {
                "power_source": source,
                "test_points": destinations,
                "strategy": "binary_search",
                "phase": self.current_phase
            }
            
            # 发送测试请求到服务器 - 使用正确的API端点/api/experiment
            response = requests.post(
                f"{self.server_url}/api/experiment",
                json=test_data,
                timeout=60  # 批次测试可能需要更长时间
            )
            
            if response.status_code == 200:
                result = response.json()
                
                # 处理批次测试结果
                if isinstance(result, dict) and 'results' in result:
                    # 主服务器返回的是批次结果
                    batch_results = result['results']
                    for dest_idx, dest_result in enumerate(batch_results):
                        dest = destinations[dest_idx]
                        self._update_relation_matrix(source, dest, dest_result)
                else:
                    # 如果返回的是单个结果，为每个目标点使用相同结果
                    for dest in destinations:
                        self._update_relation_matrix(source, dest, result)
                
                # 打印测试进度
                if self.test_count % 10 == 0:
                    self.logger.info(f"📈 测试进度: {self.test_count} 次测试完成")
                    
            else:
                self.logger.error(f"❌ 批次测试请求失败: HTTP {response.status_code}")
                # 将所有点位对重新添加到未知关系中
                for dest in destinations:
                    self.unknown_relations.add((source, dest))
                
        except Exception as e:
            self.logger.error(f"❌ 批次测试执行异常 (源: {source}, 目标点数: {len(destinations)}): {str(e)}")
            # 将所有点位对重新添加到未知关系中
            for dest in destinations:
                self.unknown_relations.add((source, dest))
            
    def _update_relation_matrix(self, source: int, destination: int, result: Dict):
        """更新关系矩阵"""
        relation_key = (source, destination)
        self.relation_matrix[relation_key] = result
        
        # 更新已知关系
        self.known_relations.add(relation_key)
        
        # 检查是否是电源点位
        if result.get('is_power_source', False):
            self.power_sources.add(source)
    
    def get_current_group_ratio(self) -> float:
        """获取当前的分组比例"""
        # 始终返回0.0表示使用二分法
        return 0.0
    
    def get_current_strategy_name(self) -> str:
        """获取当前的策略名称"""
        # 始终返回二分法策略名称
        return "binary_search"
    
    def _get_strategy_by_unknown_ratio(self, unknown_ratio: float) -> tuple:
        """根据未知关系比例和配置的策略阈值选择策略，返回(策略比例, 策略名称)"""
        # 确保 unknown_ratio 是有效的数值
        if not isinstance(unknown_ratio, (int, float)) or unknown_ratio < 0 or unknown_ratio > 1:
            print(f"⚠️  无效的未知关系比例: {unknown_ratio}，使用默认值 1.0")
            unknown_ratio = 1.0
            
        try:
            # 🔧 强制使用二分法策略进行整体流程
            # 无论未知关系比例如何，始终返回二分法策略
            strategy_name = "binary_search"
            group_ratio = 0.0  # 二分法策略的分组比例通常为0
            
            print(f"🔍 强制使用二分法策略进行整体流程")
            print(f"  当前未知关系比例: {unknown_ratio:.1%}")
            print(f"  选择策略: {strategy_name}")
            print(f"  分组比例: {group_ratio:.1%}")
            
            return group_ratio, strategy_name
            
        except Exception as e:
            print(f"⚠️  策略选择出错: {e}")
            import traceback
            traceback.print_exc()
            # 返回默认策略标识符，避免无限循环
            return 0.1, "unknown"
    
    def get_strategy_name_by_ratio(self, ratio: float) -> str:
        """根据分组比例获取策略名称"""
        if ratio == 0.0:
            return "binary_search"
        elif ratio <= 0.1:
            return "10%集群策略"
        elif ratio <= 0.2:
            return "20%集群策略"
        elif ratio <= 0.3:
            return "30%集群策略"
        else:
            return "unknown"
    
    def print_current_status(self):
        """打印当前测试状态"""
        elapsed_time = time.time() - self.start_time
        total_relations = self.total_points * (self.total_points - 1) // 2
        known_ratio = len(self.known_relations) / total_relations if total_relations > 0 else 0
        
        print("\n📊 测试状态摘要")
        print("=" * 50)
        print(f"总测试次数: {self.test_count}")
        print(f"已知关系: {len(self.known_relations)}/{total_relations} ({known_ratio:.1%})")
        print(f"未知关系: {len(self.unknown_relations)}")
        print(f"电源点位: {len(self.power_sources)}")
        print(f"当前阶段: {self.current_phase} (二分法测试)")
        print(f"耗时: {elapsed_time:.2f} 秒")
        print(f"测试速度: {self.test_count/elapsed_time:.2f} 测试/秒")
        print("=" * 50)
    
    def _save_results(self):
        """保存测试结果"""
        if not self.config.get('save_results', True):
            return
        
        results = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "total_points": self.total_points,
            "test_count": self.test_count,
            "known_relations": len(self.known_relations),
            "unknown_relations": len(self.unknown_relations),
            "power_sources": list(self.power_sources),
            "elapsed_time": time.time() - self.start_time,
            "strategy": "binary_search_only",
            "relation_matrix": self.relation_matrix
        }
        
        try:
            results_file = self.config.get('results_file', 'adaptive_grouping_results.json')
            with open(results_file, 'w', encoding='utf-8') as f:
                json.dump(results, f, ensure_ascii=False, indent=2)
            self.logger.info(f"💾 测试结果已保存到 {results_file}")
        except Exception as e:
            self.logger.error(f"❌ 保存测试结果失败: {str(e)}")
    
    def switch_to_next_phase(self):
        """切换到下一阶段"""
        # 在只使用二分法的模式下，不进行阶段切换
        self.logger.info("🔄 已配置只使用二分法策略，不进行阶段切换")
    
    def get_current_phase_name(self) -> str:
        """获取当前阶段名称"""
        return "二分法测试阶段"
    
    def get_target_phase_name(self) -> str:
        """获取目标阶段名称"""
        return "二分法测试阶段"
    
    def _get_strategy_info(self, strategy_name: str) -> Dict:
        """获取策略信息"""
        return {
            "strategy_name": "binary_search",
            "group_ratio": 0.0,
            "description": "二分法测试策略"
        }

if __name__ == "__main__":
    # 用于测试的简单配置
    test_config = {
        'total_points': 100,
        'concurrency': 4,
        'enable_logging': True,
        'save_results': True,
        'test_execution': {
            'max_total_tests': 2000,
            'binary_search': {
                'enabled': True
            }
        }
    }
    
    # 创建测试器
    tester = AdaptiveGroupingTester(test_config)
    print("✅ 自适应分组测试器创建成功")
    print("使用命令行运行: python run_adaptive_grouping.py")
