#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
演示脚本 - Flask接口系统完整功能展示
"""

import time
import json
import subprocess
import sys
import os
from pathlib import Path

def print_header(title):
    """打印标题"""
    print("\n" + "="*60)
    print(f" {title}")
    print("="*60)

def print_step(step_num, description):
    """打印步骤"""
    print(f"\n步骤 {step_num}: {description}")
    print("-" * 40)

def check_dependencies():
    """检查依赖包"""
    print_step(1, "检查依赖包")
    
    try:
        import flask
        import flask_cors
        import requests
        print("✓ 所有依赖包已安装")
        return True
    except ImportError as e:
        print(f"✗ 缺少依赖包: {e}")
        print("请运行: pip install -r requirements.txt")
        return False

def start_server():
    """启动服务端"""
    print_step(2, "启动Flask服务端")
    
    print("正在启动服务端...")
    print("注意: 服务端将在后台运行，请保持此终端窗口打开")
    
    # 检查服务端是否已经在运行
    try:
        import requests
        response = requests.get("http://localhost:5000/api/health", timeout=2)
        if response.status_code == 200:
            print("✓ 服务端已在运行")
            return True
    except:
        pass
    
    # 启动服务端
    try:
        # 使用subprocess启动服务端
        server_process = subprocess.Popen([
            sys.executable, "run_server.py"
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        # 等待服务端启动
        print("等待服务端启动...")
        time.sleep(5)
        
        # 检查服务端是否成功启动
        for i in range(10):
            try:
                response = requests.get("http://localhost:5000/api/health", timeout=2)
                if response.status_code == 200:
                    print("✓ 服务端启动成功")
                    return True
            except:
                pass
            time.sleep(1)
        
        print("✗ 服务端启动失败")
        return False
        
    except Exception as e:
        print(f"✗ 启动服务端时出错: {e}")
        return False

def test_client_functionality():
    """测试客户端功能"""
    print_step(3, "测试客户端功能")
    
    try:
        from flask_client import FlaskTestClient, ExperimentConfig
        
        client = FlaskTestClient("http://localhost:5000")
        
        # 测试健康检查
        print("1. 测试健康检查...")
        result = client.health_check()
        if 'status' in result:
            print(f"   ✓ 服务端状态: {result['status']}")
        else:
            print(f"   ✗ 健康检查失败: {result.get('error', '未知错误')}")
        
        # 测试系统信息查询
        print("2. 测试系统信息查询...")
        result = client.get_system_info()
        if result.get('success'):
            data = result['data']
            print(f"   ✓ 总点位: {data.get('total_points')}")
            print(f"   ✓ 继电器切换时间: {data.get('relay_switch_time')} 秒")
        else:
            print(f"   ✗ 系统信息查询失败: {result.get('error', '未知错误')}")
        
        # 测试点位状态查询
        print("3. 测试点位状态查询...")
        result = client.get_point_status(1)
        if result.get('success'):
            data = result['data']
            print(f"   ✓ 点位1状态: {data.get('relay_state')}")
        else:
            print(f"   ✗ 点位状态查询失败: {result.get('error', '未知错误')}")
        
        # 测试集群信息查询
        print("4. 测试集群信息查询...")
        result = client.get_cluster_info()
        if result.get('success'):
            data = result['data']
            print(f"   ✓ 已确认集群数量: {data.get('total_clusters')}")
        else:
            print(f"   ✗ 集群信息查询失败: {result.get('error', '未知错误')}")
        
        return client
        
    except Exception as e:
        print(f"✗ 测试客户端功能时出错: {e}")
        return None

def test_experiment_execution(client):
    """测试实验执行"""
    print_step(4, "测试实验执行")
    
    if not client:
        print("✗ 客户端未初始化，跳过实验测试")
        return
    
    try:
        from flask_client import ExperimentConfig
        
        # 测试单个实验
        print("1. 测试单个实验执行...")
        config = ExperimentConfig(power_source=1, test_points=[2, 3, 4])
        result = client.run_experiment(config)
        
        if result.get('success'):
            data = result['data']
            print(f"   ✓ 实验执行成功")
            print(f"     测试ID: {data.get('test_id')}")
            print(f"     电源点位: {data.get('power_source')}")
            print(f"     检测到的连接数: {len(data.get('detected_connections', []))}")
            print(f"     测试耗时: {data.get('test_duration'):.3f} 秒")
            print(f"     继电器操作次数: {data.get('relay_operations')}")
        else:
            print(f"   ✗ 实验执行失败: {result.get('error', '未知错误')}")
        
        # 测试批量实验
        print("2. 测试批量实验执行...")
        result = client.run_batch_experiments(test_count=2, max_points_per_test=50)
        
        if result.get('success'):
            data = result['data']
            print(f"   ✓ 批量实验执行成功")
            print(f"     总测试数: {data.get('total_tests')}")
            for i, test_result in enumerate(data.get('test_results', [])):
                print(f"     测试 {i+1}: 电源点位 {test_result.get('power_source')}, "
                      f"检测连接 {test_result.get('detected_connections')} 个")
        else:
            print(f"   ✗ 批量实验执行失败: {result.get('error', '未知错误')}")
        
    except Exception as e:
        print(f"✗ 测试实验执行时出错: {e}")

def test_status_updates(client):
    """测试状态更新"""
    print_step(5, "测试状态更新")
    
    if not client:
        print("✗ 客户端未初始化，跳过状态更新测试")
        return
    
    try:
        from flask_client import ExperimentConfig
        
        # 运行前查询集群信息
        before_result = client.get_cluster_info()
        before_count = before_result.get('data', {}).get('total_clusters', 0)
        print(f"运行前集群数量: {before_count}")
        
        # 运行实验
        print("运行实验以更新状态...")
        config = ExperimentConfig(power_source=10, test_points=[11, 12, 13])
        experiment_result = client.run_experiment(config)
        
        if experiment_result.get('success'):
            # 运行后查询集群信息
            after_result = client.get_cluster_info()
            after_count = after_result.get('data', {}).get('total_clusters', 0)
            
            print(f"运行后集群数量: {after_count}")
            
            if after_count > before_count:
                print("✓ 集群信息已成功更新")
            else:
                print("- 集群信息无变化")
        else:
            print(f"✗ 实验执行失败: {experiment_result.get('error', '未知错误')}")
        
    except Exception as e:
        print(f"✗ 测试状态更新时出错: {e}")

def show_api_examples():
    """显示API使用示例"""
    print_step(6, "API使用示例")
    
    print("以下是主要的API接口使用示例:")
    
    print("\n1. 健康检查:")
    print("   GET http://localhost:5000/api/health")
    
    print("\n2. 查询点位状态:")
    print("   GET http://localhost:5000/api/points/status?point_id=1")
    print("   GET http://localhost:5000/api/points/status")
    
    print("\n3. 查询集群信息:")
    print("   GET http://localhost:5000/api/clusters")
    
    print("\n4. 执行实验:")
    print("   POST http://localhost:5000/api/experiment")
    print("   Content-Type: application/json")
    print("   Body: {\"power_source\": 1, \"test_points\": [2, 3, 4]}")
    
    print("\n5. 执行批量实验:")
    print("   POST http://localhost:5000/api/experiment/batch")
    print("   Content-Type: application/json")
    print("   Body: {\"test_count\": 5, \"max_points_per_test\": 100}")
    
    print("\n6. 获取系统信息:")
    print("   GET http://localhost:5000/api/system/info")

def show_client_usage():
    """显示客户端使用方法"""
    print_step(7, "客户端使用方法")
    
    print("客户端支持多种使用方式:")
    
    print("\n1. 交互式界面:")
    print("   python flask_client.py --interactive")
    
    print("\n2. 演示模式:")
    print("   python flask_client.py")
    
    print("\n3. 指定服务端地址:")
    print("   python flask_client.py --server http://192.168.1.100:5000")
    
    print("\n4. 编程方式:")
    print("   from flask_client import FlaskTestClient, ExperimentConfig")
    print("   client = FlaskTestClient('http://localhost:5000')")
    print("   result = client.get_point_status(1)")

def main():
    """主函数"""
    print_header("Flask接口系统完整功能演示")
    
    print("本演示将展示Flask接口系统的完整功能，包括:")
    print("• 服务端启动和健康检查")
    print("• 客户端功能测试")
    print("• 实验执行和状态更新")
    print("• API接口使用示例")
    print("• 客户端使用方法")
    
    # 检查依赖
    if not check_dependencies():
        return
    
    # 启动服务端
    if not start_server():
        print("\n❌ 无法启动服务端，演示终止")
        return
    
    # 测试客户端功能
    client = test_client_functionality()
    
    # 测试实验执行
    test_experiment_execution(client)
    
    # 测试状态更新
    test_status_updates(client)
    
    # 显示API示例
    show_api_examples()
    
    # 显示客户端使用方法
    show_client_usage()
    
    print_header("演示完成")
    print("Flask接口系统演示已完成！")
    print("\n下一步操作:")
    print("1. 保持服务端运行，使用客户端进行测试")
    print("2. 查看详细文档: Flask接口使用说明.md")
    print("3. 运行完整测试: python test_flask_interface.py")
    print("4. 使用交互式客户端: python flask_client.py --interactive")
    
    print("\n服务端地址: http://localhost:5000")
    print("API文档: 查看上述API使用示例")

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n用户中断，演示终止")
    except Exception as e:
        print(f"\n演示过程中出现错误: {e}")
        print("请检查错误信息并重试")
