#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Waitress性能测试脚本
用于验证waitress服务器相比Flask开发服务器的性能提升
"""

import time
import requests
import threading
from concurrent.futures import ThreadPoolExecutor
import statistics

def test_single_request(url, timeout=5):
    """测试单个请求的响应时间"""
    try:
        start_time = time.time()
        response = requests.get(url, timeout=timeout)
        end_time = time.time()
        
        if response.status_code == 200:
            return end_time - start_time, True
        else:
            return end_time - start_time, False
    except Exception as e:
        return None, False

def test_concurrent_requests(url, num_requests=50, max_workers=10):
    """测试并发请求性能"""
    print(f"🚀 开始性能测试...")
    print(f"📊 测试参数: {num_requests} 个请求, {max_workers} 个并发线程")
    print(f"🎯 目标URL: {url}")
    print("-" * 50)
    
    start_time = time.time()
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(test_single_request, url) for _ in range(num_requests)]
        results = [future.result() for future in futures]
    
    end_time = time.time()
    total_time = end_time - start_time
    
    # 分析结果
    successful_requests = [r for r in results if r[1]]
    failed_requests = [r for r in results if not r[1]]
    response_times = [r[0] for r in successful_requests if r[0] is not None]
    
    if response_times:
        avg_response_time = statistics.mean(response_times)
        min_response_time = min(response_times)
        max_response_time = max(response_times)
        median_response_time = statistics.median(response_times)
    else:
        avg_response_time = min_response_time = max_response_time = median_response_time = 0
    
    success_rate = len(successful_requests) / len(results) * 100
    requests_per_second = len(successful_requests) / total_time if total_time > 0 else 0
    
    print(f"📈 测试结果:")
    print(f"  ✅ 成功请求: {len(successful_requests)}/{num_requests} ({success_rate:.1f}%)")
    print(f"  ❌ 失败请求: {len(failed_requests)}")
    print(f"  ⏱️  总耗时: {total_time:.2f} 秒")
    print(f"  🚀 吞吐量: {requests_per_second:.2f} 请求/秒")
    print(f"  📊 响应时间统计:")
    print(f"    - 平均: {avg_response_time*1000:.2f} ms")
    print(f"    - 最小: {min_response_time*1000:.2f} ms")
    print(f"    - 最大: {max_response_time*1000:.2f} ms")
    print(f"    - 中位数: {median_response_time*1000:.2f} ms")
    
    return {
        'success_rate': success_rate,
        'requests_per_second': requests_per_second,
        'avg_response_time': avg_response_time,
        'total_time': total_time
    }

def main():
    """主测试函数"""
    print("🔧 Waitress性能测试工具")
    print("=" * 50)
    
    # 测试URL - 可以根据实际服务器调整
    test_urls = [
        "http://localhost:5000/api/status",
        "http://localhost:5000/api/relay/stats",
        "http://localhost:5001/api/status"  # 测试客户端
    ]
    
    for url in test_urls:
        print(f"\n🌐 测试URL: {url}")
        try:
            # 先测试单个请求确保服务器可用
            response_time, success = test_single_request(url)
            if not success:
                print(f"❌ 服务器不可用: {url}")
                continue
                
            print(f"✅ 服务器可用，响应时间: {response_time*1000:.2f} ms")
            
            # 进行并发测试
            result = test_concurrent_requests(url, num_requests=100, max_workers=20)
            
        except Exception as e:
            print(f"❌ 测试失败: {e}")
        
        print("-" * 50)

if __name__ == "__main__":
    main()
