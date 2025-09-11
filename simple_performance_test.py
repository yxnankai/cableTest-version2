#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简化的性能测试脚本
用于快速诊断性能问题
"""

import time
import requests
import sys
import os

# 添加项目路径
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))
from utils.performance_timer import get_timer, print_performance_report

def test_api_timing():
    """测试API响应时间"""
    print("🔍 测试API响应时间...")
    
    apis = [
        "/api/health",
        "/api/system/info", 
        "/api/points/status",
        "/api/clusters"
    ]
    
    for api in apis:
        try:
            start_time = time.time()
            response = requests.get(f"http://localhost:5000{api}", timeout=10)
            end_time = time.time()
            
            response_time = end_time - start_time
            
            if response.status_code == 200:
                print(f"  ✅ {api}: {response_time:.3f}秒")
            else:
                print(f"  ❌ {api}: HTTP {response.status_code} - {response_time:.3f}秒")
                
        except Exception as e:
            print(f"  ❌ {api}: 错误 - {str(e)}")

def test_experiment_timing():
    """测试实验执行时间"""
    print("\n🧪 测试实验执行时间...")
    
    try:
        start_time = time.time()
        
        response = requests.post("http://localhost:5000/api/experiment", 
            json={
                "power_source": 0,
                "test_points": [1, 2, 3, 4, 5],
                "strategy": "binary_search"
            },
            timeout=30
        )
        
        end_time = time.time()
        total_time = end_time - start_time
        
        if response.status_code == 200:
            result = response.json()
            if result.get('success'):
                print(f"  ✅ 实验完成: {total_time:.3f}秒")
                
                if 'data' in result and 'test_result' in result['data']:
                    test_result = result['data']['test_result']
                    print(f"     继电器操作: {test_result.get('relay_operations', 0)}次")
                    print(f"     检测到连接: {len(test_result.get('detected_connections', []))}个")
                    print(f"     测试耗时: {test_result.get('test_duration', 0)*1000:.2f}ms")
            else:
                print(f"  ❌ 实验失败: {result.get('error', '未知错误')}")
        else:
            print(f"  ❌ 实验请求失败: HTTP {response.status_code}")
            
    except Exception as e:
        print(f"  ❌ 实验执行错误: {str(e)}")

def main():
    """主函数"""
    print("🚀 简化性能测试")
    print("="*50)
    
    # 测试API响应时间
    test_api_timing()
    
    # 测试实验执行时间
    test_experiment_timing()
    
    # 打印性能计时器报告
    print("\n⏱️ 系统内部性能计时器报告:")
    print_performance_report()

if __name__ == "__main__":
    main()
