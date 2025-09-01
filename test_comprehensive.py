#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试修复后的前端功能
"""

import requests
import json

def test_api_endpoints():
    """测试所有API端点"""
    base_url = "http://localhost:5000"
    
    print("🧪 测试API端点")
    print("=" * 50)
    
    endpoints = [
        '/api/system/info',
        '/api/clusters',
        '/api/points/status',
        '/api/test/history',
        '/api/clusters/unconfirmed_relationships',
        '/api/test/progress'
    ]
    
    results = {}
    
    for endpoint in endpoints:
        try:
            print(f"\n测试 {endpoint}...")
            response = requests.get(f"{base_url}{endpoint}", timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ {endpoint} - 状态码: {response.status_code}")
                print(f"   响应类型: {type(data)}")
                if isinstance(data, dict):
                    print(f"   主要字段: {list(data.keys())}")
                    if 'success' in data:
                        print(f"   成功状态: {data['success']}")
                results[endpoint] = data
            else:
                print(f"❌ {endpoint} - 状态码: {response.status_code}")
                print(f"   响应内容: {response.text[:200]}")
                results[endpoint] = None
                
        except Exception as e:
            print(f"❌ {endpoint} - 错误: {e}")
            results[endpoint] = None
    
    return results

def test_frontend():
    """测试前端页面"""
    base_url = "http://localhost:5000"
    
    print("\n🧪 测试前端页面")
    print("=" * 50)
    
    try:
        response = requests.get(base_url, timeout=10)
        
        if response.status_code == 200:
            print("✅ 前端页面访问成功")
            content = response.text
            
            # 检查关键元素
            checks = [
                ('systemInfo', '系统信息容器'),
                ('clusterInfo', '集群信息容器'),
                ('pointStatus', '点位状态容器'),
                ('testHistory', '测试历史容器'),
                ('progressChart', '图表容器'),
                ('loadInitialData', '数据加载函数'),
                ('updateSystemInfo', '系统信息更新函数')
            ]
            
            for check, name in checks:
                if check in content:
                    print(f"✅ {name} 已找到")
                else:
                    print(f"❌ {name} 未找到")
                    
        else:
            print(f"❌ 前端页面访问失败: {response.status_code}")
            
    except Exception as e:
        print(f"❌ 前端页面测试失败: {e}")

if __name__ == "__main__":
    print("🚀 开始测试修复后的功能")
    api_results = test_api_endpoints()
    test_frontend()
    
    print("\n📊 测试总结:")
    print("=" * 50)
    
    # 检查API结果
    success_count = sum(1 for result in api_results.values() if result and isinstance(result, dict) and result.get('success') is not False)
    total_count = len(api_results)
    
    print(f"API端点测试: {success_count}/{total_count} 成功")
    
    if success_count == total_count:
        print("✅ 所有API端点正常工作")
    else:
        print("⚠️  部分API端点有问题，请检查服务器日志")
    
    print("\n💡 建议:")
    print("1. 打开浏览器访问 http://localhost:5000")
    print("2. 打开浏览器开发者工具查看控制台输出")
    print("3. 检查是否有JavaScript错误")
    print("4. 查看网络请求是否成功")
