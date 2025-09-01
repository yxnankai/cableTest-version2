#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简单的服务器测试脚本
"""

import requests
import time

def test_server():
    """测试服务器是否正常启动"""
    print("🧪 测试服务器启动")
    print("=" * 50)
    
    try:
        print("1. 测试主页访问...")
        response = requests.get("http://localhost:5000", timeout=5)
        
        if response.status_code == 200:
            print("✅ 主页访问成功")
            content = response.text
            
            # 检查关键元素
            if 'progressChart' in content:
                print("✅ 图表容器已找到")
            else:
                print("❌ 图表容器未找到")
                
            if 'Chart.js' in content:
                print("✅ Chart.js库已加载")
            else:
                print("❌ Chart.js库未找到")
                
        else:
            print(f"❌ 主页访问失败: {response.status_code}")
            
    except Exception as e:
        print(f"❌ 测试失败: {e}")

if __name__ == "__main__":
    test_server()
