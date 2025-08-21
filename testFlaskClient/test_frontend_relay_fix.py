#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试前端继电器操作次数计算修复
验证当电源点位改变但测试点位基本相同时的计算逻辑
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from adaptive_grouping_test import AdaptiveGroupingTester
from adaptive_grouping_config import get_config

def test_frontend_relay_fix():
    """测试前端继电器操作次数计算修复"""
    print("🧪 测试前端继电器操作次数计算修复")
    print("=" * 60)
    
    # 获取配置
    config = get_config('balanced')
    
    # 创建测试器实例
    tester = AdaptiveGroupingTester(config)
    
    # 模拟第一次测试：电源点位0，测试点位[1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28,29]
    print("\n🔬 第一次测试")
    print("电源点位: 0")
    test_points_1 = [1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28,29]
    print(f"测试点位: {test_points_1}")
    
    # 计算继电器操作次数
    relay_ops_1 = tester.calculate_relay_operations(0, test_points_1)
    print(f"继电器操作次数: {relay_ops_1}")
    
    # 更新继电器状态
    tester.update_relay_states(0, test_points_1)
    
    # 模拟第二次测试：电源点位1，测试点位[0,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28,29]
    print("\n🔬 第二次测试")
    print("电源点位: 1")
    test_points_2 = [0,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28,29]
    print(f"测试点位: {test_points_2}")
    
    # 计算继电器操作次数
    relay_ops_2 = tester.calculate_relay_operations(1, test_points_2)
    print(f"继电器操作次数: {relay_ops_2}")
    
    # 更新继电器状态
    tester.update_relay_states(1, test_points_2)
    
    # 模拟第三次测试：电源点位2，测试点位[0,1,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28,29]
    print("\n🔬 第三次测试")
    print("电源点位: 2")
    test_points_3 = [0,1,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28,29]
    print(f"测试点位: {test_points_3}")
    
    # 计算继电器操作次数
    relay_ops_3 = tester.calculate_relay_operations(2, test_points_3)
    print(f"继电器操作次数: {relay_ops_3}")
    
    # 验证结果
    print(f"\n🎯 测试结果验证:")
    print(f"第一次测试继电器操作: {relay_ops_1} (应该 = 30，需要开启30个继电器)")
    print(f"第二次测试继电器操作: {relay_ops_2} (应该 = 0，继电器状态完全相同)")
    print(f"第三次测试继电器操作: {relay_ops_3} (应该 = 0，继电器状态完全相同)")
    
    # 验证继电器操作次数
    if relay_ops_1 == 30 and relay_ops_2 == 0 and relay_ops_3 == 0:
        print("✅ 前端继电器操作次数计算逻辑正确")
    else:
        print("❌ 前端继电器操作次数计算逻辑有问题")
    
    print(f"\n🎯 测试完成")

if __name__ == "__main__":
    test_frontend_relay_fix()
