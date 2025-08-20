#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
线缆测试系统使用示例
展示各种测试场景和功能
"""

from test_interface import SimpleTestInterface
from core.cable_test_system import CableTestSystem
import time

def example_1_basic_usage():
    """示例1: 基本使用方法"""
    print("=== 示例1: 基本使用方法 ===")
    
    # 创建测试接口
    interface = SimpleTestInterface(total_points=2000)
    
    # 运行快速测试
    result = interface.quick_test()
    print(f"快速测试完成，检测到 {len(result.detected_connections)} 个连接关系\n")
    
    return interface

def example_2_custom_test():
    """示例2: 自定义测试"""
    print("=== 示例2: 自定义测试 ===")
    
    interface = SimpleTestInterface(total_points=1000)
    
    # 指定电源点位和测试点位
    power_source = 100
    test_points = [200, 300, 400, 500, 600]
    
    result = interface.quick_test(
        power_source=power_source,
        test_points=test_points
    )
    
    print(f"自定义测试完成:")
    print(f"  电源点位: {power_source}")
    print(f"  测试点位: {test_points}")
    print(f"  检测到连接: {len(result.detected_connections)} 个\n")
    
    return interface

def example_3_batch_testing():
    """示例3: 批量测试"""
    print("=== 示例3: 批量测试 ===")
    
    interface = SimpleTestInterface(total_points=1500)
    
    # 运行批量测试
    results = interface.batch_test(test_count=5)
    
    # 分析结果
    total_connections = sum(len(r.detected_connections) for r in results)
    avg_time = sum(r.test_duration for r in results) / len(results)
    
    print(f"批量测试分析:")
    print(f"  平均测试时间: {avg_time:.3f} 秒")
    print(f"  总检测连接数: {total_connections}\n")
    
    return interface

def example_4_advanced_usage():
    """示例4: 高级用法 - 直接使用核心系统"""
    print("=== 示例4: 高级用法 ===")
    
    # 创建核心测试系统
    system = CableTestSystem(total_points=3000)
    
    # 生成特定的测试配置
    test_configs = [
        {'power_source': 0, 'test_points': list(range(1, 101))},      # 测试前100个点
        {'power_source': 1000, 'test_points': list(range(1001, 1101))}, # 测试1000-1100点
        {'power_source': 2000, 'test_points': list(range(2001, 2101))}  # 测试2000-2100点
    ]
    
    # 运行测试
    results = system.run_batch_tests(test_configs)
    
    # 分析结果
    for i, result in enumerate(results):
        print(f"  测试 {i+1}: 电源{result.power_source}, "
              f"检测到{len(result.detected_connections)}个连接, "
              f"耗时{result.test_duration:.3f}秒")
    
    print()
    return system

def example_5_connection_analysis():
    """示例5: 连接关系分析"""
    print("=== 示例5: 连接关系分析 ===")
    
    system = CableTestSystem(total_points=1000)
    
    # 统计连接类型
    one_to_one_count = sum(1 for conn in system.connections if conn.connection_type == "one_to_one")
    one_to_many_count = sum(1 for conn in system.connections if conn.connection_type == "one_to_many")
    
    print(f"连接关系统计:")
    print(f"  一对一连接: {one_to_one_count} 个")
    print(f"  一对多连接: {one_to_many_count} 个")
    print(f"  总连接数: {len(system.connections)} 个")
    
    # 显示一些一对多连接的详细信息
    many_connections = [conn for conn in system.connections if conn.connection_type == "one_to_many"]
    if many_connections:
        print(f"\n一对多连接示例:")
        for i, conn in enumerate(many_connections[:3]):
            print(f"  {i+1}. 源点位 {conn.source_point} -> 目标点位 {conn.target_points}")
    
    print()
    return system

def example_6_performance_test():
    """示例6: 性能测试"""
    print("=== 示例6: 性能测试 ===")
    
    # 测试不同点位数量的性能
    point_counts = [100, 500, 1000, 2000]
    
    for point_count in point_counts:
        print(f"测试 {point_count} 个点位:")
        
        start_time = time.time()
        system = CableTestSystem(total_points=point_count)
        init_time = time.time() - start_time
        
        # 运行一次测试
        test_start = time.time()
        result = system.run_single_test(0, list(range(1, min(51, point_count))))
        test_time = time.time() - test_start
        
        print(f"  初始化时间: {init_time:.3f} 秒")
        print(f"  测试时间: {test_time:.3f} 秒")
        print(f"  继电器操作: {result.relay_operations} 次")
        print()
    
    return None

def main():
    """主函数 - 运行所有示例"""
    print("线缆测试系统 - 使用示例演示\n")
    
    try:
        # 运行各种示例
        example_1_basic_usage()
        example_2_custom_test()
        example_3_batch_testing()
        example_4_advanced_usage()
        example_5_connection_analysis()
        example_6_performance_test()
        
        print("所有示例运行完成！")
        
    except Exception as e:
        print(f"运行示例时出现错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
