#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试修复后的二分法逻辑和新探查关系数量显示
"""

import sys
import os
import time

# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from testFlaskClient.adaptive_grouping_test import AdaptiveGroupingTester
from testFlaskClient.adaptive_grouping_config import load_config

def test_binary_search_logic():
    """测试修复后的二分法逻辑"""
    print("🔍 测试修复后的二分法逻辑")
    print("=" * 60)
    
    # 加载配置
    config = load_config()
    
    # 创建测试器
    tester = AdaptiveGroupingTester(config)
    
    # 初始化关系矩阵
    tester.initialize_relationship_matrix()
    
    print(f"📊 初始状态:")
    print(f"  总点位: {tester.total_points}")
    print(f"  已知关系: {len(tester.known_relations)}")
    print(f"  未知关系: {len(tester.unknown_relations)}")
    
    # 模拟一些已知关系，以便测试二分法逻辑
    print(f"\n🔧 模拟一些已知关系...")
    
    # 添加一些模拟的已知关系
    for i in range(10):
        for j in range(i+1, min(i+5, 10)):
            if (i, j) in tester.unknown_relations:
                tester.unknown_relations.remove((i, j))
                tester.known_relations.add((i, j))
                print(f"  添加已知关系: {i} <-> {j}")
    
    print(f"\n📊 模拟后的状态:")
    print(f"  已知关系: {len(tester.known_relations)}")
    print(f"  未知关系: {len(tester.unknown_relations)}")
    
    # 测试智能二分法选择
    print(f"\n🔍 测试智能二分法选择...")
    
    # 获取一些未知关系的点位对
    unknown_pairs = list(tester.unknown_relations)[:5]
    print(f"  测试点位对: {unknown_pairs}")
    
    for pair in unknown_pairs:
        score = tester.calculate_binary_pair_score(pair[0], pair[1])
        cluster1 = tester.get_point_cluster(pair[0])
        cluster2 = tester.get_point_cluster(pair[1])
        test_count1 = tester.get_point_test_count(pair[0])
        test_count2 = tester.get_point_test_count(pair[1])
        
        print(f"    点位对 {pair}: 分数={score:.2f}, 集群=({cluster1},{cluster2}), 测试次数=({test_count1},{test_count2})")
    
    # 选择最优的点位对
    optimal_pair = tester.select_optimal_binary_pair(unknown_pairs)
    print(f"  最优选择: {optimal_pair}")
    
    # 测试二分法测试（只运行少量测试）
    print(f"\n🔬 测试二分法测试逻辑（限制测试次数）...")
    
    # 临时修改最大测试次数
    original_max_tests = config['test_execution']['max_total_tests']
    config['test_execution']['max_total_tests'] = 1000  # 设置较大的值
    
    try:
        # 运行少量二分法测试
        tests_run = tester.run_binary_search_testing(max_tests=3)
        print(f"✅ 二分法测试完成，运行了 {tests_run} 次测试")
        
    except Exception as e:
        print(f"❌ 二分法测试过程中发生错误: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # 恢复原始配置
        config['test_execution']['max_total_tests'] = original_max_tests
    
    print(f"\n📊 最终状态:")
    print(f"  已知关系: {len(tester.known_relations)}")
    print(f"  未知关系: {len(tester.unknown_relations)}")
    print(f"  总测试次数: {tester.total_tests}")

if __name__ == "__main__":
    try:
        test_binary_search_logic()
        print(f"\n✅ 测试完成")
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
