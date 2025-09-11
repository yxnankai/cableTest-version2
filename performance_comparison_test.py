#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
性能对比测试脚本
对比原始服务器和优化服务器的性能
"""

import requests
import time
import json
import statistics
from typing import List, Dict, Any

class PerformanceTester:
    """性能测试器"""
    
    def __init__(self, base_url: str = "http://localhost:5000"):
        self.base_url = base_url
        self.results = {}
    
    def test_api_endpoint(self, endpoint: str, method: str = "GET", data: Dict = None, 
                         iterations: int = 10) -> Dict[str, Any]:
        """测试单个API端点"""
        print(f"🧪 测试 {method} {endpoint} ({iterations}次迭代)...")
        
        response_times = []
        success_count = 0
        error_count = 0
        
        for i in range(iterations):
            try:
                start_time = time.time()
                
                if method == "GET":
                    response = requests.get(f"{self.base_url}{endpoint}", timeout=10)
                elif method == "POST":
                    response = requests.post(f"{self.base_url}{endpoint}", 
                                           json=data, timeout=10)
                
                end_time = time.time()
                response_time = end_time - start_time
                response_times.append(response_time)
                
                if response.status_code == 200:
                    success_count += 1
                else:
                    error_count += 1
                    print(f"  ❌ 第{i+1}次请求失败: {response.status_code}")
                
            except Exception as e:
                error_count += 1
                print(f"  ❌ 第{i+1}次请求异常: {e}")
                response_times.append(10.0)  # 超时时间作为失败时间
        
        if response_times:
            stats = {
                'endpoint': endpoint,
                'method': method,
                'iterations': iterations,
                'success_count': success_count,
                'error_count': error_count,
                'success_rate': success_count / iterations,
                'avg_response_time': statistics.mean(response_times),
                'min_response_time': min(response_times),
                'max_response_time': max(response_times),
                'median_response_time': statistics.median(response_times),
                'std_deviation': statistics.stdev(response_times) if len(response_times) > 1 else 0
            }
        else:
            stats = {
                'endpoint': endpoint,
                'method': method,
                'iterations': iterations,
                'success_count': 0,
                'error_count': error_count,
                'success_rate': 0,
                'avg_response_time': 0,
                'min_response_time': 0,
                'max_response_time': 0,
                'median_response_time': 0,
                'std_deviation': 0
            }
        
        print(f"  ✅ 平均响应时间: {stats['avg_response_time']:.3f}s")
        print(f"  ✅ 成功率: {stats['success_rate']:.1%}")
        
        return stats
    
    def run_comprehensive_test(self) -> Dict[str, Any]:
        """运行综合性能测试"""
        print("🚀 开始综合性能测试...")
        print("=" * 60)
        
        # 测试端点列表
        test_cases = [
            {"endpoint": "/api/health", "method": "GET"},
            {"endpoint": "/api/system/info", "method": "GET"},
            {"endpoint": "/api/points/status", "method": "GET", "params": {"point_id": 1}},
            {"endpoint": "/api/clusters", "method": "GET"},
            {"endpoint": "/api/experiment", "method": "POST", "data": {
                "power_source": 1,
                "test_points": [1, 2, 3, 4, 5]
            }},
            {"endpoint": "/api/test/progress", "method": "GET"},
        ]
        
        all_results = []
        
        for test_case in test_cases:
            endpoint = test_case["endpoint"]
            method = test_case["method"]
            data = test_case.get("data")
            
            # 添加查询参数
            if "params" in test_case:
                params = test_case["params"]
                param_str = "&".join([f"{k}={v}" for k, v in params.items()])
                endpoint = f"{endpoint}?{param_str}"
            
            result = self.test_api_endpoint(endpoint, method, data, iterations=5)
            all_results.append(result)
            print()
        
        # 计算总体统计
        total_requests = sum(r['iterations'] for r in all_results)
        total_success = sum(r['success_count'] for r in all_results)
        avg_response_times = [r['avg_response_time'] for r in all_results if r['avg_response_time'] > 0]
        
        overall_stats = {
            'total_endpoints_tested': len(test_cases),
            'total_requests': total_requests,
            'total_success': total_success,
            'overall_success_rate': total_success / total_requests if total_requests > 0 else 0,
            'avg_response_time_across_endpoints': statistics.mean(avg_response_times) if avg_response_times else 0,
            'fastest_endpoint': min(all_results, key=lambda x: x['avg_response_time'])['endpoint'],
            'slowest_endpoint': max(all_results, key=lambda x: x['avg_response_time'])['endpoint'],
            'detailed_results': all_results
        }
        
        return overall_stats
    
    def print_summary(self, stats: Dict[str, Any]):
        """打印测试摘要"""
        print("=" * 60)
        print("📊 性能测试摘要")
        print("=" * 60)
        print(f"总测试端点: {stats['total_endpoints_tested']}")
        print(f"总请求数: {stats['total_requests']}")
        print(f"成功请求数: {stats['total_success']}")
        print(f"总体成功率: {stats['overall_success_rate']:.1%}")
        print(f"平均响应时间: {stats['avg_response_time_across_endpoints']:.3f}s")
        print(f"最快端点: {stats['fastest_endpoint']}")
        print(f"最慢端点: {stats['slowest_endpoint']}")
        print()
        
        print("📈 各端点详细结果:")
        print("-" * 60)
        for result in stats['detailed_results']:
            print(f"{result['method']} {result['endpoint']}")
            print(f"  平均响应时间: {result['avg_response_time']:.3f}s")
            print(f"  成功率: {result['success_rate']:.1%}")
            print(f"  响应时间范围: {result['min_response_time']:.3f}s - {result['max_response_time']:.3f}s")
            print()

def main():
    """主函数"""
    print("🔧 线缆测试系统性能对比测试")
    print("=" * 60)
    
    # 检查服务器是否运行
    try:
        response = requests.get("http://localhost:5000/api/health", timeout=5)
        if response.status_code == 200:
            print("✅ 服务器运行正常")
        else:
            print("❌ 服务器响应异常")
            return
    except Exception as e:
        print(f"❌ 无法连接到服务器: {e}")
        print("请确保服务器正在运行: python run_web_server.py")
        return
    
    # 运行性能测试
    tester = PerformanceTester()
    stats = tester.run_comprehensive_test()
    tester.print_summary(stats)
    
    # 保存结果
    with open('performance_test_results.json', 'w', encoding='utf-8') as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)
    
    print("💾 测试结果已保存到 performance_test_results.json")

if __name__ == "__main__":
    main()
