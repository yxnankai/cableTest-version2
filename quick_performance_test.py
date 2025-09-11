#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
快速性能测试脚本
用于快速验证测试系统的性能改进
"""

import time
import requests
import json
import sys
import os

# 添加项目路径
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))
from utils.performance_timer import get_timer, print_performance_report

def test_server_availability():
    """测试服务器可用性"""
    print("🔍 检查服务器可用性...")
    
    try:
        response = requests.get("http://localhost:5000/api/health", timeout=5)
        if response.status_code == 200:
            print("✅ 服务器运行正常")
            return True
        else:
            print(f"❌ 服务器响应异常: HTTP {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ 无法连接到服务器: {e}")
        return False

def test_api_response_times():
    """测试API响应时间"""
    print("\n⏱️ 测试API响应时间...")
    
    apis = [
        ("/api/health", "GET", None),
        ("/api/system/info", "GET", None),
        ("/api/points/status", "GET", None),
        ("/api/clusters", "GET", None),
    ]
    
    results = []
    
    for endpoint, method, data in apis:
        try:
            start_time = time.time()
            
            if method == "GET":
                response = requests.get(f"http://localhost:5000{endpoint}", timeout=10)
            elif method == "POST":
                response = requests.post(f"http://localhost:5000{endpoint}", json=data, timeout=10)
            
            end_time = time.time()
            response_time = end_time - start_time
            
            if response.status_code == 200:
                print(f"  ✅ {endpoint}: {response_time*1000:.2f}ms")
                results.append((endpoint, response_time, True))
            else:
                print(f"  ❌ {endpoint}: HTTP {response.status_code} - {response_time*1000:.2f}ms")
                results.append((endpoint, response_time, False))
                
        except Exception as e:
            print(f"  ❌ {endpoint}: 错误 - {str(e)}")
            results.append((endpoint, 0, False))
    
    return results

def test_experiment_performance():
    """测试实验性能"""
    print("\n🧪 测试实验性能...")
    
    # 测试配置
    power_source = 0
    test_points = list(range(1, 11))  # 测试10个点位
    
    print(f"🔌 电源点位: {power_source}")
    print(f"📍 测试点位: {test_points}")
    
    try:
        start_time = time.time()
        
        response = requests.post("http://localhost:5000/api/experiment", 
            json={
                "power_source": power_source,
                "test_points": test_points,
                "strategy": "binary_search"
            },
            timeout=30
        )
        
        end_time = time.time()
        total_time = end_time - start_time
        
        if response.status_code == 200:
            result = response.json()
            if result.get('success'):
                print(f"✅ 实验完成: {total_time:.3f}秒")
                
                # 显示实验详情
                if 'data' in result and 'test_result' in result['data']:
                    test_result = result['data']['test_result']
                    print(f"  继电器操作: {test_result.get('relay_operations', 0)}次")
                    print(f"  检测到连接: {len(test_result.get('detected_connections', []))}个")
                    print(f"  测试耗时: {test_result.get('test_duration', 0)*1000:.2f}ms")
                    print(f"  通电次数: {test_result.get('power_on_operations', 0)}次")
                
                return total_time, True
            else:
                print(f"❌ 实验失败: {result.get('error', '未知错误')}")
                return total_time, False
        else:
            print(f"❌ 实验请求失败: HTTP {response.status_code}")
            return total_time, False
            
    except Exception as e:
        print(f"❌ 实验执行错误: {str(e)}")
        return 0, False

def test_multiple_experiments(num_tests=3):
    """测试多个实验的性能"""
    print(f"\n🔄 测试多个实验性能 ({num_tests}次)...")
    
    times = []
    success_count = 0
    
    for i in range(num_tests):
        print(f"\n实验 {i+1}/{num_tests}:")
        experiment_time, success = test_experiment_performance()
        
        if success:
            times.append(experiment_time)
            success_count += 1
    
    if times:
        avg_time = sum(times) / len(times)
        min_time = min(times)
        max_time = max(times)
        success_rate = (success_count / num_tests) * 100
        
        print(f"\n📊 多实验性能统计:")
        print(f"  成功率: {success_rate:.1f}%")
        print(f"  平均时间: {avg_time:.3f}秒")
        print(f"  最小时间: {min_time:.3f}秒")
        print(f"  最大时间: {max_time:.3f}秒")
        
        return {
            'success_rate': success_rate,
            'avg_time': avg_time,
            'min_time': min_time,
            'max_time': max_time,
            'times': times
        }
    else:
        print("❌ 所有实验都失败了")
        return None

def main():
    """主函数"""
    print("🚀 快速性能测试工具")
    print("="*50)
    
    # 1. 检查服务器可用性
    if not test_server_availability():
        print("\n💡 请确保服务器已启动:")
        print("   python run_web_server.py")
        print("   或")
        print("   python start_server.py")
        return
    
    # 2. 测试API响应时间
    api_results = test_api_response_times()
    
    # 3. 测试单个实验性能
    experiment_time, success = test_experiment_performance()
    
    # 4. 测试多个实验性能
    multi_results = test_multiple_experiments(3)
    
    # 5. 打印性能计时器报告
    print("\n⏱️ 系统内部性能计时器报告:")
    print_performance_report()
    
    # 6. 总结
    print("\n" + "="*50)
    print("📊 性能测试总结")
    print("="*50)
    
    # API性能总结
    successful_apis = [r for r in api_results if r[2]]
    if successful_apis:
        avg_api_time = sum(r[1] for r in successful_apis) / len(successful_apis)
        print(f"✅ API平均响应时间: {avg_api_time*1000:.2f}ms")
    else:
        print("❌ API测试失败")
    
    # 实验性能总结
    if success:
        print(f"✅ 单个实验时间: {experiment_time:.3f}秒")
    else:
        print("❌ 单个实验失败")
    
    if multi_results:
        print(f"✅ 多实验平均时间: {multi_results['avg_time']:.3f}秒")
        print(f"✅ 多实验成功率: {multi_results['success_rate']:.1f}%")
    else:
        print("❌ 多实验测试失败")
    
    print("\n💡 性能优化建议:")
    print("1. 如果API响应时间 > 100ms，考虑优化数据库查询")
    print("2. 如果实验时间 > 1秒，检查继电器操作和检测逻辑")
    print("3. 如果成功率 < 100%，检查错误日志")
    print("4. 查看上方的性能计时器报告，定位具体瓶颈")

if __name__ == "__main__":
    main()
