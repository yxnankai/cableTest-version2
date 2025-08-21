#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试继电器操作次数计算修复
验证当电源点位改变但测试点位基本相同时的计算逻辑
"""

import requests
import time
import json

def test_relay_calculation():
    """测试继电器操作次数计算修复"""
    print("🧪 测试继电器操作次数计算修复")
    print("=" * 60)
    
    base_url = "http://localhost:5000"
    
    try:
        # 1. 获取初始系统状态
        print("📊 获取初始系统状态...")
        response = requests.get(f"{base_url}/api/system/info")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ 系统状态获取成功")
            print(f"  继电器操作总次数: {data.get('total_relay_operations', 'N/A')}")
        else:
            print(f"❌ 获取系统状态失败: {response.status_code}")
            return
        
        # 2. 第一次测试 - 点位0作为电源，测试点位1
        print(f"\n🔬 第一次测试 - 点位0作为电源，测试点位1")
        payload1 = {
            "power_source": 0,
            "test_points": [1]
        }
        
        response = requests.post(f"{base_url}/api/experiment", json=payload1, timeout=30)
        if response.status_code == 200:
            result1 = response.json()
            if result1.get('success'):
                test_data1 = result1['data']['test_result']
                print(f"✅ 第一次测试成功")
                print(f"  继电器操作次数: {test_data1.get('relay_operations', 'N/A')}")
                print(f"  通电次数: {test_data1.get('power_on_operations', 'N/A')}")
            else:
                print(f"❌ 第一次测试失败: {result1.get('error', '未知错误')}")
                return
        else:
            print(f"❌ 第一次测试HTTP请求失败: {response.status_code}")
            return
        
        # 等待一下
        time.sleep(1)
        
        # 3. 第二次测试 - 点位1作为电源，测试点位0
        print(f"\n🔬 第二次测试 - 点位1作为电源，测试点位0")
        payload2 = {
            "power_source": 1,
            "test_points": [0]
        }
        
        response = requests.post(f"{base_url}/api/experiment", json=payload2, timeout=30)
        if response.status_code == 200:
            result2 = response.json()
            if result2.get('success'):
                test_data2 = result2['data']['test_result']
                print(f"✅ 第二次测试成功")
                print(f"  继电器操作次数: {test_data2.get('relay_operations', 'N/A')}")
                print(f"  通电次数: {test_data2.get('power_on_operations', 'N/A')}")
            else:
                print(f"❌ 第二次测试失败: {result2.get('error', '未知错误')}")
                return
        else:
            print(f"❌ 第二次测试HTTP请求失败: {response.status_code}")
            return
        
        # 4. 获取最终系统状态
        print(f"\n📊 获取最终系统状态...")
        response = requests.get(f"{base_url}/api/system/info")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ 最终系统状态获取成功")
            print(f"  继电器操作总次数: {data.get('total_relay_operations', 'N/A')}")
        else:
            print(f"❌ 获取最终系统状态失败: {response.status_code}")
        
        # 5. 验证结果
        print(f"\n🎯 测试结果验证:")
        print(f"继电器操作次数验证:")
        print(f"  第一次测试: {test_data1.get('relay_operations', 'N/A')} (应该 > 0，需要开启2个继电器)")
        print(f"  第二次测试: {test_data2.get('relay_operations', 'N/A')} (应该 = 0，继电器状态基本相同)")
        
        print(f"\n通电次数验证:")
        print(f"  第一次测试: {test_data1.get('power_on_operations', 'N/A')} (应该 = 1)")
        print(f"  第二次测试: {test_data2.get('power_on_operations', 'N/A')} (应该 = 1)")
        
        # 验证继电器操作次数
        relay_ops1 = test_data1.get('relay_operations', 0)
        relay_ops2 = test_data2.get('relay_operations', 0)
        
        if relay_ops1 > 0 and relay_ops2 == 0:
            print("✅ 继电器操作次数计算逻辑正确")
        else:
            print("❌ 继电器操作次数计算逻辑有问题")
        
        # 验证通电次数
        power_on1 = test_data1.get('power_on_operations', 0)
        power_on2 = test_data2.get('power_on_operations', 0)
        
        if power_on1 == 1 and power_on2 == 1:
            print("✅ 通电次数计算逻辑正确")
        else:
            print("❌ 通电次数计算逻辑有问题")
        
        print(f"\n🎯 测试完成")
        
    except Exception as e:
        print(f"❌ 测试过程中发生错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_relay_calculation()
