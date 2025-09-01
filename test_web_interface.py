#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试Web界面功能
验证界面是否正常加载和显示
"""

import requests
import time

def test_web_interface():
    """测试Web界面"""
    base_url = "http://localhost:5000"
    
    print("🧪 测试Web界面功能")
    print("=" * 50)
    
    try:
        print("1. 测试主页访问...")
        response = requests.get(base_url, timeout=10)
        
        if response.status_code == 200:
            print("✅ 主页访问成功")
            
            content = response.text
            
            # 检查关键元素
            checks = [
                ('progressChart', '图表容器'),
                ('Chart.js', 'Chart.js库'),
                ('initProgressChart', '图表初始化函数'),
                ('updateProgressChart', '图表更新函数'),
                ('实验进度图表', '图表标题'),
                ('刷新图表', '刷新按钮'),
                ('导出数据', '导出按钮')
            ]
            
            for check, name in checks:
                if check in content:
                    print(f"✅ {name} 已找到")
                else:
                    print(f"❌ {name} 未找到")
            
            # 检查是否有JavaScript错误
            if 'console.error' in content or 'console.log' in content:
                print("✅ 调试代码已添加")
            else:
                print("⚠️  调试代码未找到")
                
        else:
            print(f"❌ 主页访问失败: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Web界面测试失败: {e}")

def test_api_endpoints():
    """测试API端点"""
    base_url = "http://localhost:5000"
    
    print("\n2. 测试API端点...")
    
    endpoints = [
        '/api/system/info',
        '/api/test/progress',
        '/api/clusters',
        '/api/points/status',
        '/api/test/history'
    ]
    
    for endpoint in endpoints:
        try:
            response = requests.get(f"{base_url}{endpoint}", timeout=5)
            if response.status_code == 200:
                print(f"✅ {endpoint} - 正常")
            else:
                print(f"❌ {endpoint} - 状态码: {response.status_code}")
        except Exception as e:
            print(f"❌ {endpoint} - 错误: {e}")

if __name__ == "__main__":
    print("🚀 开始测试Web界面功能")
    test_web_interface()
    test_api_endpoints()
    print("\n✅ 测试完成")
