#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
快速启动自适应分组测试
"""

import sys
import os
import argparse
from adaptive_grouping_config import get_config, print_config_summary
from adaptive_grouping_test import AdaptiveGroupingTester

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='自适应分组测试系统')
    parser.add_argument('--preset', '-p', default='balanced', 
                       choices=['conservative', 'balanced', 'aggressive'],
                       help='选择预设配置 (默认: balanced)')
    parser.add_argument('--url', '-u', default='http://localhost:5000',
                       help='Flask服务器地址 (默认: http://localhost:5000)')
    parser.add_argument('--max-tests', '-m', type=int, default=None,
                       help='最大测试次数 (默认: 使用配置文件中的值)')
    parser.add_argument('--show-config', '-s', action='store_true',
                       help='显示配置信息后退出')
    
    args = parser.parse_args()
    
    print("🚀 自适应分组测试系统")
    print("=" * 60)
    
    # 获取配置
    config = get_config(args.preset)
    
    # 显示配置
    print_config_summary(config)
    
    # 如果只是显示配置，退出
    if args.show_config:
        return
    
    # 应用命令行参数
    if args.max_tests:
        config['test_execution']['max_total_tests'] = args.max_tests
        print(f"\n📝 命令行覆盖: 最大测试次数 = {args.max_tests}")
    
    # 创建测试器
    tester = AdaptiveGroupingTester(config, args.url)
    
    # 运行测试
    try:
        tester.run_full_test_cycle()
    except KeyboardInterrupt:
        print("\n⚠️  测试被用户中断")
        tester.print_current_status()
    except Exception as e:
        print(f"\n❌ 测试过程中发生错误: {str(e)}")
        tester.print_current_status()

if __name__ == "__main__":
    main()
