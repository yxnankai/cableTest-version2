#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试修复后的服务器启动
"""

import requests
import time

def test_server():
    """测试服务器是否正常启动"""
    print("🧪 测试修复后的服务器启动")
    print("=" * 50)
    
    try:
        print("1. 测试主页访问...")
        response = requests.get("http://localhost:5000", timeout=10)
        
        if response.status_code == 200:
            print("✅ 主页访问成功")
            content = response.text
            
            # 检查关键元素
            checks = [
                ('progressChart', '图表容器'),
                ('Chart.js', 'Chart.js库'),
                ('initProgressChart', '图表初始化函数'),
                ('实验进度图表', '图表标题')
            ]
            
            for check, name in checks:
                if check in content:
                    print(f"✅ {name} 已找到")
                else:
                    print(f"❌ {name} 未找到")
                    
        else:
            print(f"❌ 主页访问失败: {response.status_code}")
            
    except Exception as e:
        print(f"❌ 测试失败: {e}")

if __name__ == "__main__":
    test_server()
