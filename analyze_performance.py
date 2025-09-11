#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
性能分析脚本
用于测试和分析测试系统的性能瓶颈
"""

import time
import requests
import json
import threading
from concurrent.futures import ThreadPoolExecutor
import statistics
import sys
import os

# 添加项目路径
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))
from utils.performance_timer import get_timer, print_performance_report, export_performance_data

class PerformanceAnalyzer:
    """性能分析器"""
    
    def __init__(self, base_url="http://localhost:5000"):
        self.base_url = base_url
        self.timer = get_timer()
        self.results = []
    
    def test_api_performance(self, endpoint, method="GET", data=None, num_requests=10):
        """测试API性能"""
        print(f"\n🔍 测试API性能: {method} {endpoint}")
        print(f"📊 请求数量: {num_requests}")
        
        url = f"{self.base_url}{endpoint}"
        response_times = []
        success_count = 0
        
        for i in range(num_requests):
            try:
                start_time = time.time()
                
                if method == "GET":
                    response = requests.get(url, timeout=10)
                elif method == "POST":
                    response = requests.post(url, json=data, timeout=10)
                
                end_time = time.time()
                response_time = end_time - start_time
                response_times.append(response_time)
                
                if response.status_code == 200:
                    success_count += 1
                    print(f"  ✅ 请求 {i+1}: {response_time*1000:.2f}ms")
                else:
                    print(f"  ❌ 请求 {i+1}: HTTP {response.status_code} - {response_time*1000:.2f}ms")
                
            except Exception as e:
                print(f"  ❌ 请求 {i+1}: 错误 - {str(e)}")
        
        if response_times:
            avg_time = statistics.mean(response_times)
            min_time = min(response_times)
            max_time = max(response_times)
            success_rate = (success_count / num_requests) * 100
            
            result = {
                'endpoint': endpoint,
                'method': method,
                'num_requests': num_requests,
                'success_count': success_count,
                'success_rate': success_rate,
                'avg_response_time': avg_time,
                'min_response_time': min_time,
                'max_response_time': max_time,
                'response_times': response_times
            }
            
            self.results.append(result)
            
            print(f"\n📈 性能统计:")
            print(f"  成功率: {success_rate:.1f}%")
            print(f"  平均响应时间: {avg_time*1000:.2f}ms")
            print(f"  最小响应时间: {min_time*1000:.2f}ms")
            print(f"  最大响应时间: {max_time*1000:.2f}ms")
            
            return result
        else:
            print(f"  ❌ 所有请求都失败了")
            return None
    
    def test_concurrent_performance(self, endpoint, method="GET", data=None, num_requests=20, max_workers=5):
        """测试并发性能"""
        print(f"\n🚀 测试并发性能: {method} {endpoint}")
        print(f"📊 请求数量: {num_requests}, 并发数: {max_workers}")
        
        url = f"{self.base_url}{endpoint}"
        response_times = []
        success_count = 0
        
        def make_request(request_id):
            nonlocal success_count
            try:
                start_time = time.time()
                
                if method == "GET":
                    response = requests.get(url, timeout=10)
                elif method == "POST":
                    response = requests.post(url, json=data, timeout=10)
                
                end_time = time.time()
                response_time = end_time - start_time
                
                if response.status_code == 200:
                    success_count += 1
                    print(f"  ✅ 并发请求 {request_id}: {response_time*1000:.2f}ms")
                else:
                    print(f"  ❌ 并发请求 {request_id}: HTTP {response.status_code} - {response_time*1000:.2f}ms")
                
                return response_time, response.status_code == 200
                
            except Exception as e:
                print(f"  ❌ 并发请求 {request_id}: 错误 - {str(e)}")
                return None, False
        
        start_time = time.time()
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [executor.submit(make_request, i+1) for i in range(num_requests)]
            results = [future.result() for future in futures]
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # 分析结果
        successful_results = [r for r in results if r[0] is not None and r[1]]
        response_times = [r[0] for r in successful_results]
        
        if response_times:
            avg_time = statistics.mean(response_times)
            min_time = min(response_times)
            max_time = max(response_times)
            requests_per_second = len(response_times) / total_time
            
            result = {
                'endpoint': endpoint,
                'method': method,
                'num_requests': num_requests,
                'max_workers': max_workers,
                'success_count': len(response_times),
                'success_rate': (len(response_times) / num_requests) * 100,
                'avg_response_time': avg_time,
                'min_response_time': min_time,
                'max_response_time': max_time,
                'total_time': total_time,
                'requests_per_second': requests_per_second,
                'response_times': response_times
            }
            
            self.results.append(result)
            
            print(f"\n📈 并发性能统计:")
            print(f"  成功率: {(len(response_times) / num_requests) * 100:.1f}%")
            print(f"  总耗时: {total_time:.2f}秒")
            print(f"  吞吐量: {requests_per_second:.2f} 请求/秒")
            print(f"  平均响应时间: {avg_time*1000:.2f}ms")
            print(f"  最小响应时间: {min_time*1000:.2f}ms")
            print(f"  最大响应时间: {max_time*1000:.2f}ms")
            
            return result
        else:
            print(f"  ❌ 所有并发请求都失败了")
            return None
    
    def test_experiment_performance(self, power_source=0, test_points=None, num_tests=5):
        """测试实验性能"""
        if test_points is None:
            test_points = list(range(1, 21))  # 默认测试20个点位
        
        print(f"\n🧪 测试实验性能")
        print(f"📊 实验次数: {num_tests}")
        print(f"🔌 电源点位: {power_source}")
        print(f"📍 测试点位: {test_points[:10]}{'...' if len(test_points) > 10 else ''}")
        
        experiment_times = []
        success_count = 0
        
        for i in range(num_tests):
            try:
                start_time = time.time()
                
                response = requests.post(f"{self.base_url}/api/experiment", 
                    json={
                        "power_source": power_source,
                        "test_points": test_points,
                        "strategy": "binary_search"
                    },
                    timeout=30
                )
                
                end_time = time.time()
                experiment_time = end_time - start_time
                
                if response.status_code == 200:
                    result = response.json()
                    if result.get('success'):
                        success_count += 1
                        print(f"  ✅ 实验 {i+1}: {experiment_time:.3f}秒")
                        
                        # 记录实验详情
                        if 'data' in result and 'test_result' in result['data']:
                            test_result = result['data']['test_result']
                            print(f"     继电器操作: {test_result.get('relay_operations', 0)}次")
                            print(f"     检测到连接: {len(test_result.get('detected_connections', []))}个")
                            print(f"     测试耗时: {test_result.get('test_duration', 0)*1000:.2f}ms")
                    else:
                        print(f"  ❌ 实验 {i+1}: 失败 - {result.get('error', '未知错误')}")
                else:
                    print(f"  ❌ 实验 {i+1}: HTTP {response.status_code}")
                
                experiment_times.append(experiment_time)
                
            except Exception as e:
                print(f"  ❌ 实验 {i+1}: 错误 - {str(e)}")
                experiment_times.append(0)
        
        if experiment_times:
            avg_time = statistics.mean(experiment_times)
            min_time = min(experiment_times)
            max_time = max(experiment_times)
            success_rate = (success_count / num_tests) * 100
            
            result = {
                'test_type': 'experiment',
                'num_tests': num_tests,
                'success_count': success_count,
                'success_rate': success_rate,
                'avg_time': avg_time,
                'min_time': min_time,
                'max_time': max_time,
                'times': experiment_times
            }
            
            self.results.append(result)
            
            print(f"\n📈 实验性能统计:")
            print(f"  成功率: {success_rate:.1f}%")
            print(f"  平均实验时间: {avg_time:.3f}秒")
            print(f"  最小实验时间: {min_time:.3f}秒")
            print(f"  最大实验时间: {max_time:.3f}秒")
            
            return result
        else:
            print(f"  ❌ 所有实验都失败了")
            return None
    
    def print_summary(self):
        """打印性能分析摘要"""
        print("\n" + "="*80)
        print("📊 性能分析摘要")
        print("="*80)
        
        if not self.results:
            print("❌ 没有性能测试结果")
            return
        
        # 按测试类型分组
        api_tests = [r for r in self.results if 'endpoint' in r]
        experiment_tests = [r for r in self.results if r.get('test_type') == 'experiment']
        
        if api_tests:
            print(f"\n🌐 API性能测试结果:")
            print(f"{'端点':<30} {'方法':<8} {'成功率':<10} {'平均响应时间':<15} {'吞吐量':<15}")
            print("-" * 80)
            
            for result in api_tests:
                endpoint = result['endpoint']
                method = result['method']
                success_rate = result['success_rate']
                avg_time = result['avg_response_time'] * 1000
                rps = result.get('requests_per_second', 0)
                
                print(f"{endpoint:<30} {method:<8} {success_rate:<10.1f}% {avg_time:<15.2f}ms {rps:<15.2f}")
        
        if experiment_tests:
            print(f"\n🧪 实验性能测试结果:")
            print(f"{'测试次数':<10} {'成功率':<10} {'平均时间':<15} {'最小时间':<15} {'最大时间':<15}")
            print("-" * 80)
            
            for result in experiment_tests:
                num_tests = result['num_tests']
                success_rate = result['success_rate']
                avg_time = result['avg_time']
                min_time = result['min_time']
                max_time = result['max_time']
                
                print(f"{num_tests:<10} {success_rate:<10.1f}% {avg_time:<15.3f}s {min_time:<15.3f}s {max_time:<15.3f}s")
        
        print("="*80)
    
    def export_results(self, filename=None):
        """导出测试结果"""
        if filename is None:
            filename = f"performance_analysis_{int(time.time())}.json"
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, indent=2, ensure_ascii=False)
        
        print(f"📁 性能测试结果已导出到: {filename}")

def main():
    """主函数"""
    print("🔧 线缆测试系统性能分析工具")
    print("="*60)
    
    # 检查服务器是否可用
    try:
        response = requests.get("http://localhost:5000/api/health", timeout=5)
        if response.status_code != 200:
            print("❌ 服务器不可用，请确保服务器已启动")
            return
    except Exception as e:
        print(f"❌ 无法连接到服务器: {e}")
        print("💡 请确保服务器已启动并运行在 http://localhost:5000")
        return
    
    print("✅ 服务器连接正常，开始性能分析...")
    
    analyzer = PerformanceAnalyzer()
    
    # 1. 测试基础API性能
    print("\n🔍 第一阶段：基础API性能测试")
    analyzer.test_api_performance("/api/health", num_requests=10)
    analyzer.test_api_performance("/api/system/info", num_requests=10)
    analyzer.test_api_performance("/api/points/status", num_requests=10)
    analyzer.test_api_performance("/api/clusters", num_requests=10)
    
    # 2. 测试并发性能
    print("\n🚀 第二阶段：并发性能测试")
    analyzer.test_concurrent_performance("/api/health", num_requests=20, max_workers=5)
    analyzer.test_concurrent_performance("/api/system/info", num_requests=20, max_workers=5)
    
    # 3. 测试实验性能
    print("\n🧪 第三阶段：实验性能测试")
    analyzer.test_experiment_performance(power_source=0, test_points=list(range(1, 11)), num_tests=3)
    
    # 4. 打印摘要
    analyzer.print_summary()
    
    # 5. 导出结果
    analyzer.export_results()
    
    # 6. 打印性能计时器报告
    print("\n⏱️ 系统内部性能计时器报告:")
    print_performance_report()
    
    # 7. 导出性能计时器数据
    export_performance_data()

if __name__ == "__main__":
    main()
