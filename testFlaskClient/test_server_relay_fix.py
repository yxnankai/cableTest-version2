#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试服务端继电器操作次数和通电次数修复
验证服务端API返回的数据是否正确
"""

import requests
import time
import json

def test_server_relay_fix():
    """测试服务端继电器操作次数和通电次数修复"""
    print("🧪 测试服务端继电器操作次数和通电次数修复")
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
            print(f"  通电次数: {data.get('power_on_count', 'N/A')}")
        else:
            print(f"❌ 获取系统状态失败: {response.status_code}")
            return
        
        # 2. 第一次测试 - 点位0作为电源，测试点位1-29
        print(f"\n🔬 第一次测试 - 点位0作为电源，测试点位1-29")
        payload1 = {
            "power_source": 0,
            "test_points": list(range(1, 30))
        }
        
        response = requests.post(f"{base_url}/api/experiment", json=payload1, timeout=30)
        if response.status_code == 200:
            result1 = response.json()
            if result1.get('success'):
                test_data1 = result1['data']
                print(f"✅ 第一次测试成功")
                print(f"  继电器操作次数: {test_data1.get('relay_operations', 'N/A')}")
                print(f"  通电次数: {test_data1.get('power_on_operations', 'N/A')}")
                print(f"  检测到连接: {len(test_data1.get('detected_connections', []))}个")
            else:
                print(f"❌ 第一次测试失败: {result1.get('error', '未知错误')}")
                return
        else:
            print(f"❌ 第一次测试HTTP请求失败: {response.status_code}")
            return
        
        # 等待一下
        time.sleep(1)
        
        # 3. 第二次测试 - 点位1作为电源，测试点位0,2-29
        print(f"\n🔬 第二次测试 - 点位1作为电源，测试点位0,2-29")
        payload2 = {
            "power_source": 1,
            "test_points": [0] + list(range(2, 30))
        }
        
        response = requests.post(f"{base_url}/api/experiment", json=payload2, timeout=30)
        if response.status_code == 200:
            result2 = response.json()
            if result2.get('success'):
                test_data2 = result2['data']
                print(f"✅ 第二次测试成功")
                print(f"  继电器操作次数: {test_data2.get('relay_operations', 'N/A')}")
                print(f"  通电次数: {test_data2.get('power_on_operations', 'N/A')}")
                print(f"  检测到连接: {len(test_data2.get('detected_connections', []))}个")
            else:
                print(f"❌ 第二次测试失败: {result2.get('error', '未知错误')}")
                return
        else:
            print(f"❌ 第二次测试HTTP请求失败: {response.status_code}")
            return
        
        # 等待一下
        time.sleep(1)
        
        # 4. 第三次测试 - 点位2作为电源，测试点位0,1,3-29
        print(f"\n🔬 第三次测试 - 点位2作为电源，测试点位0,1,3-29")
        payload3 = {
            "power_source": 2,
            "test_points": [0, 1] + list(range(3, 30))
        }
        
        response = requests.post(f"{base_url}/api/experiment", json=payload3, timeout=30)
        if response.status_code == 200:
            result3 = response.json()
            if result3.get('success'):
                test_data3 = result3['data']
                print(f"✅ 第三次测试成功")
                print(f"  继电器操作次数: {test_data3.get('relay_operations', 'N/A')}")
                print(f"  通电次数: {test_data3.get('power_on_operations', 'N/A')}")
                print(f"  检测到连接: {len(test_data3.get('detected_connections', []))}个")
            else:
                print(f"❌ 第三次测试失败: {result3.get('error', '未知错误')}")
                return
        else:
            print(f"❌ 第三次测试HTTP请求失败: {response.status_code}")
            return
        
        # 5. 获取最终系统状态
        print(f"\n📊 获取最终系统状态...")
        response = requests.get(f"{base_url}/api/system/info")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ 最终系统状态获取成功")
            print(f"  继电器操作总次数: {data.get('total_relay_operations', 'N/A')}")
            print(f"  通电次数: {data.get('power_on_count', 'N/A')}")
        else:
            print(f"❌ 获取最终系统状态失败: {response.status_code}")
        
        # 6. 验证结果
        print(f"\n🎯 测试结果验证:")
        print(f"继电器操作次数验证:")
        print(f"  第一次测试: {test_data1.get('relay_operations', 'N/A')} (应该 > 0，需要开启30个继电器)")
        print(f"  第二次测试: {test_data2.get('relay_operations', 'N/A')} (应该 <= 2，主要是电源点位切换)")
        print(f"  第三次测试: {test_data3.get('relay_operations', 'N/A')} (应该 <= 2，主要是电源点位切换)")
        
        print(f"\n通电次数验证:")
        print(f"  第一次测试: {test_data1.get('power_on_operations', 'N/A')} (应该 = 1)")
        print(f"  第二次测试: {test_data2.get('power_on_operations', 'N/A')} (应该 = 1)")
        print(f"  第三次测试: {test_data3.get('power_on_operations', 'N/A')} (应该 = 1)")
        
        # 验证继电器操作次数
        relay_ops1 = test_data1.get('relay_operations', 0)
        relay_ops2 = test_data2.get('relay_operations', 0)
        relay_ops3 = test_data3.get('relay_operations', 0)
        
        if relay_ops1 > 0 and relay_ops2 <= 2 and relay_ops3 <= 2:
            print("✅ 继电器操作次数计算逻辑正确")
        else:
            print("❌ 继电器操作次数计算逻辑有问题")
        
        # 验证通电次数
        power_on1 = test_data1.get('power_on_operations', 0)
        power_on2 = test_data2.get('power_on_operations', 0)
        power_on3 = test_data3.get('power_on_operations', 0)
        
        if power_on1 == 1 and power_on2 == 1 and power_on3 == 1:
            print("✅ 通电次数计算逻辑正确")
        else:
            print("❌ 通电次数计算逻辑有问题")
        
        print(f"\n🎯 测试完成")
        
    except Exception as e:
        print(f"❌ 测试过程中发生错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_server_relay_fix()
