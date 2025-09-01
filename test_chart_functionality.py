#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试图表功能
验证实验进度图表是否正常工作
"""

import requests
import json
import time

def test_chart_api():
    """测试图表API"""
    base_url = "http://localhost:5000"
    
    print("🧪 测试图表功能")
    print("=" * 50)
    
    try:
        # 测试实验进度API
        print("1. 测试实验进度API...")
        response = requests.get(f"{base_url}/api/test/progress")
        
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                progress_data = data.get('data', [])
                print(f"✅ API调用成功，获取到 {len(progress_data)} 条进度数据")
                
                if progress_data:
                    print("📊 进度数据示例:")
                    for i, item in enumerate(progress_data[:5]):  # 显示前5条
                        print(f"  测试 {item['test_id']}: 已知关系 {item['known_relations']}, 策略 {item['strategy']}")
                else:
                    print("⚠️  暂无进度数据")
            else:
                print(f"❌ API返回错误: {data.get('error', '未知错误')}")
        else:
            print(f"❌ HTTP请求失败: {response.status_code}")
            
    except Exception as e:
        print(f"❌ 测试失败: {e}")

def test_web_interface():
    """测试Web界面"""
    base_url = "http://localhost:5000"
    
    print("\n2. 测试Web界面...")
    
    try:
        response = requests.get(base_url)
        if response.status_code == 200:
            print("✅ Web界面访问成功")
            
            # 检查是否包含图表相关代码
            content = response.text
            if 'progressChart' in content:
                print("✅ 图表容器已添加")
            else:
                print("❌ 图表容器未找到")
                
            if 'Chart.js' in content:
                print("✅ Chart.js库已加载")
            else:
                print("❌ Chart.js库未找到")
                
            if 'initProgressChart' in content:
                print("✅ 图表初始化函数已添加")
            else:
                print("❌ 图表初始化函数未找到")
                
        else:
            print(f"❌ Web界面访问失败: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Web界面测试失败: {e}")

if __name__ == "__main__":
    print("🚀 开始测试图表功能")
    test_chart_api()
    test_web_interface()
    print("\n✅ 测试完成")
