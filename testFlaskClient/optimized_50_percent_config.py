#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
50%批量测试策略配置文件
专门针对减少冗余、提高效率的优化配置
"""

# 核心策略配置
CORE_STRATEGY = {
    'strategy_name': 'optimized_50_percent',
    'description': '50%批量测试策略 - 平衡覆盖率和效率，减少冗余测试',
    'target_coverage': 50.0,           # 目标覆盖率50%
    'max_batch_size': 50,              # 最大批量大小50
    'min_batch_size': 20,              # 最小批量大小20
    'default_batch_size': 40,          # 默认批量大小40
}

# 智能去重配置
DEDUPLICATION_CONFIG = {
    'enabled': True,
    'avoid_known_relations': True,     # 避免测试已知关系
    'track_tested_combinations': True, # 跟踪已测试组合
    'max_targets_per_batch': 25,      # 每批最多25个目标点
    'combination_cache_size': 1000,    # 组合缓存大小
}

# 批量大小自适应配置
ADAPTIVE_BATCH_SIZING = {
    'enabled': True,
    'rate_based_adjustment': True,     # 基于检测率调整
    'adjustment_rules': {
        'low_rate_threshold': 50.0,    # 低检测率阈值
        'medium_rate_threshold': 80.0, # 中等检测率阈值
        'high_rate_threshold': 90.0,   # 高检测率阈值
        'low_rate_increase': 10,       # 低检测率时增加数量
        'medium_rate_decrease': 5,     # 中等检测率时减少数量
        'high_rate_decrease': 10,      # 高检测率时大幅减少
        'max_batch_size_limit': 50,    # 最大批量大小限制
    }
}

# 点位选择策略
POINT_SELECTION_STRATEGY = {
    'unknown_relation_weight': 0.8,    # 未知关系权重
    'redundancy_penalty_weight': 0.2,  # 冗余惩罚权重
    'min_unknown_relations': 5,        # 最小未知关系数量要求
    'max_candidates': 50,              # 最大候选点位数量
    'selection_rounds': 3,             # 选择轮数
}

# 测试规划配置
TEST_PLANNING = {
    'strategy': 'smart_batch_formation', # 智能批量形成
    'power_source_rotation': True,      # 电源点轮换
    'batch_optimization': True,         # 批量优化
    'constraint_satisfaction': True,    # 约束满足
    'max_tests_per_round': 100,        # 每轮最大测试数
}

# 效率监控配置
EFFICIENCY_MONITORING = {
    'enable_redundancy_analysis': True, # 启用冗余度分析
    'track_test_combinations': True,    # 跟踪测试组合
    'monitor_batch_efficiency': True,   # 监控批量效率
    'performance_thresholds': {
        'min_efficiency_rate': 60.0,    # 最小效率率
        'max_redundancy_rate': 30.0,    # 最大冗余率
        'target_coverage_rate': 50.0,   # 目标覆盖率
    }
}

# 网络和并发配置
NETWORK_AND_CONCURRENCY = {
    'max_concurrent_requests': 15,     # 最大并发请求数
    'request_batch_size': 25,          # 请求批次大小
    'thread_pool_workers': 12,         # 线程池工作线程数
    'connection_timeout': 30,          # 连接超时时间
    'retry_count': 3,                  # 重试次数
}

# 配置验证函数
def validate_50_percent_config():
    """验证50%批量测试配置的有效性"""
    print("验证50%批量测试配置...")
    
    # 验证批量大小配置
    if CORE_STRATEGY['min_batch_size'] > CORE_STRATEGY['max_batch_size']:
        raise ValueError("最小批量大小不能大于最大批量大小")
    
    if CORE_STRATEGY['default_batch_size'] < CORE_STRATEGY['min_batch_size']:
        raise ValueError("默认批量大小不能小于最小批量大小")
    
    if CORE_STRATEGY['default_batch_size'] > CORE_STRATEGY['max_batch_size']:
        raise ValueError("默认批量大小不能大于最大批量大小")
    
    # 验证权重配置
    if POINT_SELECTION_STRATEGY['unknown_relation_weight'] + POINT_SELECTION_STRATEGY['redundancy_penalty_weight'] != 1.0:
        raise ValueError("点位选择权重之和必须等于1.0")
    
    # 验证阈值配置
    if ADAPTIVE_BATCH_SIZING['adjustment_rules']['max_batch_size_limit'] != CORE_STRATEGY['max_batch_size']:
        raise ValueError("自适应批量大小限制必须与最大批量大小一致")
    
    print("50%批量测试配置验证通过")
    return True

# 配置预设
OPTIMIZED_PRESETS = {
    'balanced_50_percent': {
        'description': '平衡50%配置 - 平衡覆盖率和效率',
        'batch_size': 40,
        'max_targets_per_batch': 25,
        'max_concurrent_requests': 15,
        'target_coverage': 50.0,
    },
    'efficient_50_percent': {
        'description': '高效50%配置 - 优先效率',
        'batch_size': 35,
        'max_targets_per_batch': 20,
        'max_concurrent_requests': 12,
        'target_coverage': 45.0,
    },
    'thorough_50_percent': {
        'description': '全面50%配置 - 优先覆盖率',
        'batch_size': 50,
        'max_targets_per_batch': 30,
        'max_concurrent_requests': 18,
        'target_coverage': 55.0,
    }
}

def apply_optimized_preset(preset_name: str):
    """应用优化预设配置"""
    if preset_name not in OPTIMIZED_PRESETS:
        print(f"未知的优化预设配置: {preset_name}")
        return False
    
    preset = OPTIMIZED_PRESETS[preset_name]
    print(f"应用优化预设配置: {preset['description']}")
    
    # 应用配置
    CORE_STRATEGY['default_batch_size'] = preset['batch_size']
    DEDUPLICATION_CONFIG['max_targets_per_batch'] = preset['max_targets_per_batch']
    NETWORK_AND_CONCURRENCY['max_concurrent_requests'] = preset['max_concurrent_requests']
    CORE_STRATEGY['target_coverage'] = preset['target_coverage']
    
    print("优化预设配置应用完成")
    return True

# 配置信息打印
def print_optimized_config_summary():
    """打印优化配置摘要"""
    print("\n=== 50%批量测试优化配置摘要 ===")
    print(f"策略: {CORE_STRATEGY['strategy_name']}")
    print(f"描述: {CORE_STRATEGY['description']}")
    print(f"目标覆盖率: {CORE_STRATEGY['target_coverage']}%")
    print(f"批量大小: {CORE_STRATEGY['default_batch_size']} (范围: {CORE_STRATEGY['min_batch_size']}-{CORE_STRATEGY['max_batch_size']})")
    print(f"智能去重: {'启用' if DEDUPLICATION_CONFIG['enabled'] else '禁用'}")
    print(f"避免已知关系: {'启用' if DEDUPLICATION_CONFIG['avoid_known_relations'] else '禁用'}")
    print(f"每批最大目标数: {DEDUPLICATION_CONFIG['max_targets_per_batch']}")
    print(f"最大并发请求: {NETWORK_AND_CONCURRENCY['max_concurrent_requests']}")

if __name__ == "__main__":
    # 验证配置
    validate_50_percent_config()
    
    # 打印配置摘要
    print_optimized_config_summary()
    
    # 显示可用预设
    print(f"\n可用优化预设配置: {list(OPTIMIZED_PRESETS.keys())}")
    
    # 显示配置优势
    print("\n=== 配置优势 ===")
    print("1. 50%覆盖率平衡了测试效率和系统负载")
    print("2. 智能去重避免重复测试已知关系")
    print("3. 自适应批量大小根据检测率动态调整")
    print("4. 冗余度分析帮助优化测试策略")
