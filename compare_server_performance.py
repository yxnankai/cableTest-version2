#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
服务器性能对比测试
对比Flask开发服务器和Waitress服务器的性能差异
"""

import time
import requests
import threading
from concurrent.futures import ThreadPoolExecutor
import statistics
import subprocess
import sys
import os

class ServerTester:
    def __init__(self):
        self.results = {}
    
    def test_server_performance(self, server_name, base_url, num_requests=50, max_workers=10):
        """测试指定服务器的性能"""
        print(f"\n🔧 测试 {server_name} 服务器性能...")
        print(f"🎯 URL: {base_url}")
        
        # 测试API端点
        test_endpoints = [
            "/api/status",
            "/api/relay/stats"
        ]
        
        all_results = []
        
        for endpoint in test_endpoints:
            url = base_url + endpoint
            print(f"\n📡 测试端点: {endpoint}")
            
            try:
                # 先测试单个请求
                response_time, success = self.test_single_request(url)
                if not success:
                    print(f"❌ 端点不可用: {url}")
                    continue
                
                print(f"✅ 端点可用，响应时间: {response_time*1000:.2f} ms")
                
                # 进行并发测试
                result = self.test_concurrent_requests(url, num_requests, max_workers)
                all_results.append(result)
                
            except Exception as e:
                print(f"❌ 测试失败: {e}")
        
        if all_results:
            # 计算平均性能
            avg_rps = statistics.mean([r['requests_per_second'] for r in all_results])
            avg_response_time = statistics.mean([r['avg_response_time'] for r in all_results])
            avg_success_rate = statistics.mean([r['success_rate'] for r in all_results])
            
            self.results[server_name] = {
                'avg_rps': avg_rps,
                'avg_response_time': avg_response_time,
                'avg_success_rate': avg_success_rate,
                'details': all_results
            }
            
            print(f"\n📊 {server_name} 平均性能:")
            print(f"  🚀 吞吐量: {avg_rps:.2f} 请求/秒")
            print(f"  ⏱️  平均响应时间: {avg_response_time*1000:.2f} ms")
            print(f"  ✅ 成功率: {avg_success_rate:.1f}%")
        
        return all_results
    
    def test_single_request(self, url, timeout=5):
        """测试单个请求"""
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
    
    def test_concurrent_requests(self, url, num_requests=50, max_workers=10):
        """测试并发请求性能"""
        start_time = time.time()
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [executor.submit(self.test_single_request, url) for _ in range(num_requests)]
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
        else:
            avg_response_time = min_response_time = max_response_time = 0
        
        success_rate = len(successful_requests) / len(results) * 100
        requests_per_second = len(successful_requests) / total_time if total_time > 0 else 0
        
        return {
            'success_rate': success_rate,
            'requests_per_second': requests_per_second,
            'avg_response_time': avg_response_time,
            'total_time': total_time,
            'successful_requests': len(successful_requests),
            'failed_requests': len(failed_requests)
        }
    
    def print_comparison(self):
        """打印性能对比结果"""
        if len(self.results) < 2:
            print("\n❌ 需要至少两个服务器的测试结果才能进行对比")
            return
        
        print("\n" + "="*60)
        print("📊 服务器性能对比结果")
        print("="*60)
        
        servers = list(self.results.keys())
        
        print(f"{'服务器':<20} {'吞吐量(RPS)':<15} {'响应时间(ms)':<15} {'成功率(%)':<10}")
        print("-" * 60)
        
        for server in servers:
            result = self.results[server]
            print(f"{server:<20} {result['avg_rps']:<15.2f} {result['avg_response_time']*1000:<15.2f} {result['avg_success_rate']:<10.1f}")
        
        # 计算性能提升
        if len(servers) >= 2:
            server1, server2 = servers[0], servers[1]
            rps_improvement = (self.results[server2]['avg_rps'] / self.results[server1]['avg_rps'] - 1) * 100
            response_improvement = (1 - self.results[server2]['avg_response_time'] / self.results[server1]['avg_response_time']) * 100
            
            print(f"\n🚀 性能提升 ({server2} vs {server1}):")
            print(f"  吞吐量提升: {rps_improvement:+.1f}%")
            print(f"  响应时间改善: {response_improvement:+.1f}%")

def main():
    """主测试函数"""
    print("🔧 服务器性能对比测试工具")
    print("="*60)
    print("📝 使用说明:")
    print("1. 确保服务器已启动")
    print("2. 本工具将测试不同服务器的性能")
    print("3. 建议先启动Flask开发服务器，再启动Waitress服务器进行对比")
    print("="*60)
    
    tester = ServerTester()
    
    # 测试配置
    test_configs = [
        {
            'name': 'Flask开发服务器',
            'url': 'http://localhost:5000',
            'description': '使用app.run()的Flask开发服务器'
        },
        {
            'name': 'Waitress服务器',
            'url': 'http://localhost:5001',
            'description': '使用waitress的WSGI服务器'
        }
    ]
    
    for config in test_configs:
        print(f"\n🔍 准备测试: {config['name']}")
        print(f"📋 描述: {config['description']}")
        
        # 检查服务器是否可用
        try:
            response = requests.get(config['url'] + '/api/status', timeout=3)
            if response.status_code == 200:
                print(f"✅ 服务器可用，开始性能测试...")
                tester.test_server_performance(
                    config['name'], 
                    config['url'], 
                    num_requests=100, 
                    max_workers=20
                )
            else:
                print(f"❌ 服务器响应异常: {response.status_code}")
        except requests.exceptions.RequestException as e:
            print(f"❌ 无法连接到服务器: {e}")
            print(f"💡 请确保服务器已启动并运行在 {config['url']}")
    
    # 打印对比结果
    tester.print_comparison()
    
    print(f"\n💡 测试完成！")
    print(f"📈 建议使用Waitress服务器以获得更好的性能")

if __name__ == "__main__":
    main()
