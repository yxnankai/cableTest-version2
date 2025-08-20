#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
线缆测试系统Web版本演示脚本
展示前端界面、WebSocket实时更新和API功能
"""

import time
import json
import subprocess
import sys
import os
import requests
from pathlib import Path

def print_header(title):
    """打印标题"""
    print("\n" + "="*60)
    print(f"  {title}")
    print("="*60)

def print_step(step_num, description):
    """打印步骤"""
    print(f"\n🔹 步骤 {step_num}: {description}")

def check_dependencies():
    """检查依赖"""
    print_step(1, "检查系统依赖")
    
    try:
        import flask
        import flask_socketio
        import requests
        print("✅ 所有依赖已安装")
        return True
    except ImportError as e:
        print(f"❌ 缺少依赖: {e}")
        print("请运行: pip install -r requirements.txt")
        return False

def start_web_server():
    """启动Web服务器"""
    print_step(2, "启动Web服务器")
    
    try:
        # 启动Web服务器
        server_process = subprocess.Popen(
            [sys.executable, "run_web_server.py"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        print("🔄 正在启动Web服务器...")
        
        # 等待服务器启动
        for i in range(30):  # 最多等待30秒
            try:
                response = requests.get("http://localhost:5000/api/health", timeout=1)
                if response.status_code == 200:
                    print("✅ Web服务器启动成功!")
                    print("📱 前端界面: http://localhost:5000")
                    print("🔌 API接口: http://localhost:5000/api/")
                    return server_process
            except requests.exceptions.RequestException:
                pass
            
            time.sleep(1)
            if i % 5 == 0:
                print(f"⏳ 等待服务器启动... ({i+1}/30)")
        
        print("❌ 服务器启动超时")
        server_process.terminate()
        return None
        
    except Exception as e:
        print(f"❌ 启动服务器失败: {e}")
        return None

def test_api_endpoints():
    """测试API接口"""
    print_step(3, "测试API接口功能")
    
    base_url = "http://localhost:5000"
    
    # 测试健康检查
    try:
        response = requests.get(f"{base_url}/api/health")
        if response.status_code == 200:
            print("✅ 健康检查接口正常")
            print(f"   响应: {response.json()}")
        else:
            print(f"❌ 健康检查失败: {response.status_code}")
    except Exception as e:
        print(f"❌ 健康检查异常: {e}")
    
    # 测试系统信息
    try:
        response = requests.get(f"{base_url}/api/system/info")
        if response.status_code == 200:
            data = response.json()
            print("✅ 系统信息接口正常")
            print(f"   总点位: {data.get('total_points', 'N/A')}")
            print(f"   继电器切换时间: {data.get('relay_switch_time', 'N/A')}s")
        else:
            print(f"❌ 系统信息接口失败: {response.status_code}")
    except Exception as e:
        print(f"❌ 系统信息接口异常: {e}")
    
    # 测试点位状态
    try:
        response = requests.get(f"{base_url}/api/points/status")
        if response.status_code == 200:
            data = response.json()
            print("✅ 点位状态接口正常")
            print(f"   总点位: {data.get('total_points', 'N/A')}")
        else:
            print(f"❌ 点位状态接口失败: {response.status_code}")
    except Exception as e:
        print(f"❌ 点位状态接口异常: {e}")
    
    # 测试集群信息
    try:
        response = requests.get(f"{base_url}/api/clusters")
        if response.status_code == 200:
            data = response.json()
            print("✅ 集群信息接口正常")
            print(f"   已确认集群: {data.get('total_clusters', 'N/A')}")
        else:
            print(f"❌ 集群信息接口失败: {response.status_code}")
    except Exception as e:
        print(f"❌ 集群信息接口异常: {e}")

def test_experiment_execution():
    """测试实验执行"""
    print_step(4, "测试实验执行功能")
    
    base_url = "http://localhost:5000"
    
    # 测试简单实验
    try:
        experiment_data = {
            "power_source": 0,
            "test_points": [1, 2, 3, 4, 5]
        }
        
        response = requests.post(
            f"{base_url}/api/experiment",
            json=experiment_data,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                print("✅ 实验执行成功")
                result = data.get('test_result', {})
                print(f"   电源点位: {result.get('power_source')}")
                print(f"   测试点位: {result.get('test_points')}")
                print(f"   发现连接: {len(result.get('connections', []))}")
                print(f"   执行时间: {result.get('duration', 0):.3f}s")
                print(f"   继电器操作: {result.get('relay_operations')}")
            else:
                print(f"❌ 实验执行失败: {data.get('error')}")
        else:
            print(f"❌ 实验执行请求失败: {response.status_code}")
    except Exception as e:
        print(f"❌ 实验执行异常: {e}")
    
    # 等待一下让状态更新
    time.sleep(2)
    
    # 检查状态是否更新
    try:
        response = requests.get(f"{base_url}/api/points/status")
        if response.status_code == 200:
            data = response.json()
            print("✅ 状态更新检查完成")
        else:
            print(f"❌ 状态更新检查失败: {response.status_code}")
    except Exception as e:
        print(f"❌ 状态更新检查异常: {e}")

def test_batch_experiments():
    """测试批量实验"""
    print_step(5, "测试批量实验功能")
    
    base_url = "http://localhost:5000"
    
    try:
        batch_data = {
            "test_count": 3,
            "max_points_per_test": 20
        }
        
        response = requests.post(
            f"{base_url}/api/experiment/batch",
            json=batch_data,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                print("✅ 批量实验执行成功")
                results = data.get('batch_results', [])
                print(f"   执行测试数: {len(results)}")
                
                for i, result in enumerate(results):
                    if result.get('success'):
                        test_result = result.get('test_result', {})
                        print(f"   测试 {i+1}: 电源{test_result.get('power_source')}, "
                              f"连接{len(test_result.get('connections', []))}, "
                              f"耗时{test_result.get('duration', 0):.3f}s")
                    else:
                        print(f"   测试 {i+1}: 失败 - {result.get('error')}")
            else:
                print(f"❌ 批量实验执行失败: {data.get('error')}")
        else:
            print(f"❌ 批量实验请求失败: {response.status_code}")
    except Exception as e:
        print(f"❌ 批量实验异常: {e}")

def show_web_interface_info():
    """显示Web界面信息"""
    print_step(6, "Web界面功能说明")
    
    print("""
🌐 Web界面功能特性:

📱 实时监控界面:
   • 系统状态仪表板
   • 点位状态网格显示 (前100个点位)
   • 集群连接信息
   • 测试历史记录

🧪 实验控制:
   • 手动设置电源点位和测试点位
   • 随机实验生成器
   • 实时实验状态反馈

🔄 自动更新:
   • WebSocket实时推送状态变化
   • 每2秒自动刷新数据
   • 无需手动刷新页面

📊 数据可视化:
   • 点位开关状态颜色区分 (绿色=开启, 红色=关闭)
   • 测试历史时间线
   • 系统性能指标
    """)

def show_api_examples():
    """显示API使用示例"""
    print_step(7, "API使用示例")
    
    print("""
🔌 常用API调用示例:

1. 健康检查:
   curl -X GET "http://localhost:5000/api/health"

2. 获取系统信息:
   curl -X GET "http://localhost:5000/api/system/info"

3. 运行实验:
   curl -X POST "http://localhost:5000/api/experiment" \\
        -H "Content-Type: application/json" \\
        -d '{"power_source": 0, "test_points": [1,2,3,4,5]}'

4. 获取点位状态:
   curl -X GET "http://localhost:5000/api/points/status"

5. 获取集群信息:
   curl -X GET "http://localhost:5000/api/clusters"

6. 批量实验:
   curl -X POST "http://localhost:5000/api/experiment/batch" \\
        -H "Content-Type: application/json" \\
        -d '{"test_count": 5, "max_points_per_test": 100}'
    """)

def main():
    """主函数"""
    print_header("线缆测试系统 Web版本演示")
    
    print("本演示将展示线缆测试系统的Web界面和API功能")
    print("包括前端实时监控、WebSocket更新、API接口测试等")
    
    # 检查依赖
    if not check_dependencies():
        return
    
    # 启动Web服务器
    server_process = start_web_server()
    if not server_process:
        return
    
    try:
        # 等待服务器完全启动
        time.sleep(3)
        
        # 测试API接口
        test_api_endpoints()
        
        # 测试实验执行
        test_experiment_execution()
        
        # 测试批量实验
        test_batch_experiments()
        
        # 显示Web界面信息
        show_web_interface_info()
        
        # 显示API示例
        show_api_examples()
        
        print_header("演示完成")
        print("🎉 Web版本线缆测试系统演示完成!")
        print("\n📱 请在浏览器中访问: http://localhost:5000")
        print("🔌 可以尝试运行实验、查看实时状态更新")
        print("📖 详细API文档请参考: Flask_API_测试报文示例.md")
        
        print("\n⏹️  按 Ctrl+C 停止服务器...")
        
        # 保持服务器运行
        try:
            server_process.wait()
        except KeyboardInterrupt:
            print("\n🛑 正在停止服务器...")
            server_process.terminate()
            server_process.wait()
            print("✅ 服务器已停止")
    
    except KeyboardInterrupt:
        print("\n🛑 演示被中断")
        server_process.terminate()
        server_process.wait()
    except Exception as e:
        print(f"❌ 演示过程中出现错误: {e}")
        server_process.terminate()
        server_process.wait()

if __name__ == '__main__':
    main()
