#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
专门测试继电器操作次数计算的调试脚本
模拟Web界面看到的测试序列
"""

import requests
import time
import json

def test_specific_relay_sequence():
    """测试特定的继电器操作序列，模拟Web界面的问题"""
    print("🧪 测试特定继电器操作序列")
    print("=" * 60)
    
    base_url = "http://localhost:5000"
    
    try:
        # 重置系统状态
        print("🔄 重置系统状态...")
        response = requests.post(f"{base_url}/api/system/reset")
        if response.status_code == 200:
            print("✅ 系统重置成功")
        else:
            print(f"❌ 系统重置失败: {response.status_code}")
        
        time.sleep(1)
        
        # 测试序列 1: 电源点位未知，测试点位1 (第一次测试)
        print(f"\n🔬 测试 #1 - 电源点位0，测试点位1")
        payload1 = {
            "power_source": 0,
            "test_points": [1]
        }
        
        response = requests.post(f"{base_url}/api/experiment", json=payload1, timeout=30)
        if response.status_code == 200:
            result1 = response.json()
            if result1.get('success'):
                test_data1 = result1['data']['test_result']
                print(f"✅ 测试 #1 成功")
                print(f"  继电器操作次数: {test_data1.get('relay_operations', 'N/A')} (应该 > 0)")
                print(f"  通电次数: {test_data1.get('power_on_operations', 'N/A')} (应该 = 1)")
            else:
                print(f"❌ 测试 #1 失败: {result1.get('error', '未知错误')}")
                return
        else:
            print(f"❌ 测试 #1 HTTP请求失败: {response.status_code}")
            return
        
        time.sleep(2)
        
        # 测试序列 2: 电源点位2，测试点位1
        print(f"\n🔬 测试 #2 - 电源点位2，测试点位1")
        payload2 = {
            "power_source": 2,
            "test_points": [1]
        }
        
        response = requests.post(f"{base_url}/api/experiment", json=payload2, timeout=30)
        if response.status_code == 200:
            result2 = response.json()
            if result2.get('success'):
                test_data2 = result2['data']['test_result']
                print(f"✅ 测试 #2 成功")
                print(f"  继电器操作次数: {test_data2.get('relay_operations', 'N/A')} (应该 = 2，需要切换)")
                print(f"  通电次数: {test_data2.get('power_on_operations', 'N/A')} (应该 = 1)")
            else:
                print(f"❌ 测试 #2 失败: {result2.get('error', '未知错误')}")
                return
        else:
            print(f"❌ 测试 #2 HTTP请求失败: {response.status_code}")
            return
        
        time.sleep(2)
        
        # 测试序列 3: 电源点位1，测试点位2 (继电器状态集合应该相同 {1,2})
        print(f"\n🔬 测试 #3 - 电源点位1，测试点位2")
        payload3 = {
            "power_source": 1,
            "test_points": [2]
        }
        
        response = requests.post(f"{base_url}/api/experiment", json=payload3, timeout=30)
        if response.status_code == 200:
            result3 = response.json()
            if result3.get('success'):
                test_data3 = result3['data']['test_result']
                print(f"✅ 测试 #3 成功")
                print(f"  继电器操作次数: {test_data3.get('relay_operations', 'N/A')} (应该 = 0，继电器状态相同 {{1,2}})")
                print(f"  通电次数: {test_data3.get('power_on_operations', 'N/A')} (应该 = 1)")
            else:
                print(f"❌ 测试 #3 失败: {result3.get('error', '未知错误')}")
                return
        else:
            print(f"❌ 测试 #3 HTTP请求失败: {response.status_code}")
            return
        
        # 分析结果
        print(f"\n🎯 测试结果分析:")
        print(f"测试 #1: 继电器操作 {test_data1.get('relay_operations', 'N/A')} 次")
        print(f"测试 #2: 继电器操作 {test_data2.get('relay_operations', 'N/A')} 次 (电源0→2，测试点位1→1)")
        print(f"测试 #3: 继电器操作 {test_data3.get('relay_operations', 'N/A')} 次 (电源2→1，测试点位1→2)")
        
        print(f"\n🔍 继电器状态分析:")
        print(f"测试 #1 后: 继电器状态集合 = {{0, 1}}")
        print(f"测试 #2 后: 继电器状态集合 = {{2, 1}}")
        print(f"测试 #3 后: 继电器状态集合 = {{1, 2}} = {{2, 1}} (应该相同)")
        
        # 验证
        relay_ops2 = test_data2.get('relay_operations', 0)
        relay_ops3 = test_data3.get('relay_operations', 0)
        
        if relay_ops3 == 0:
            print("✅ 测试 #3 继电器操作次数正确 (0次)")
        else:
            print(f"❌ 测试 #3 继电器操作次数错误 ({relay_ops3}次，应该为0次)")
        
        print(f"\n🎯 测试完成")
        
    except Exception as e:
        print(f"❌ 测试过程中发生错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_specific_relay_sequence()
