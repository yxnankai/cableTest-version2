#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试API端点是否正常工作
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
            else:
                print(f"❌ {endpoint} - 状态码: {response.status_code}")
                print(f"   响应内容: {response.text[:200]}")
                
        except Exception as e:
            print(f"❌ {endpoint} - 错误: {e}")

if __name__ == "__main__":
    test_api_endpoints()
