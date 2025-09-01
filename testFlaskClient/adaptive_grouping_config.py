#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自适应分组测试配置
实现逐步递减的分组比例：30% → 20% → 10%
确保各分组中点位关系尽可能未知
"""

# 基础配置
BASE_CONFIG = {
    'total_points': 100,
    'concurrency': 4,
    'relay_switch_time': 50,
    'test_duration': 100,
    'max_test_time': 300,
    'enable_logging': True,
    'save_results': True,
    'results_file': 'adaptive_grouping_results.json'
}

# 自适应分组策略配置
ADAPTIVE_GROUPING_CONFIG = {
    'strategy_name': 'adaptive_grouping',
    'description': '逐步递减分组比例策略：30% → 20% → 10%',
    
    # 分组比例配置
    'group_ratios': [0.30, 0.20, 0.10],  # 30%, 20%, 10%
    'min_group_size': 5,  # 最小分组大小
    'max_group_size': 50,  # 最大分组大小
    
    # 关系未知性优化
    'max_known_relations_per_group': 0.1,  # 每组最多10%的点位关系已知
    'prefer_unknown_relations': True,  # 优先选择关系未知的点位
    'min_unknown_relations_per_group': 0.7,  # 每组至少70%的点位关系未知
    'unknown_relation_priority': 0.9,  # 未知关系优先权重
    
    # 分组选择策略
    'selection_strategy': 'max_unknown_relations',  # 最大化未知关系
    'balance_power_sources': True,  # 平衡电源点位分布
    'group_quality_threshold': 0.8,  # 分组质量阈值
    
    # 动态调整参数
    'enable_dynamic_adjustment': True,  # 启用动态调整
    'adjustment_threshold': 0.8,  # 当已知关系超过80%时调整策略
    'min_unknown_ratio': 0.3,  # 保持至少30%的未知关系
}

# 测试执行配置
TEST_EXECUTION_CONFIG = {
    'max_total_tests': 2000,  # 最大总测试次数（考虑到组内全点位测试）
    'max_tests_per_phase': 500,  # 每阶段最大测试次数（考虑到组内全点位测试）
    'phase_switch_criteria': {
        # 基于未知关系比例的阶段切换策略
        'phase_thresholds': {
            'phase_1': {'min_unknown_ratio': 0.6, 'max_unknown_ratio': 1.0, 'group_ratio': 0.30},  # 30%集群策略：100%>未知关系>50%
            'phase_2': {'min_unknown_ratio': 0.20, 'max_unknown_ratio': 0.6, 'group_ratio': 0.20},  # 20%集群策略：50%>未知关系>20%
            'phase_3': {'min_unknown_ratio': 0.10, 'max_unknown_ratio': 0.20, 'group_ratio': 0.10},  # 10%集群策略：20%>未知关系>10%
            'binary_search': {'min_unknown_ratio': 0.0, 'max_unknown_ratio': 0.10, 'group_ratio': 0.0},  # 二分法策略：10%>未知关系
        },
        'min_tests_per_phase': 50,  # 每阶段最少测试次数
    },
    
    # 二分法测试配置
    'binary_search': {
        'enabled': True,  # 启用二分法测试
        'switch_threshold': 0.10,  # 当未知关系少于10%时切换到二分法
        'min_unknown_relations': 100,  # 当未知关系少于100个时切换到二分法
        'max_tests_per_pair': 2,  # 每对点位最多测试2次（正向+反向）
        'enable_reverse_testing': True,  # 启用反向测试
    },
    
    # 性能优化
    'enable_batch_optimization': True,  # 启用批量优化
    'batch_size_multiplier': 1.5,  # 批量大小倍数
    'relay_operation_optimization': True,  # 继电器操作优化
}

# 关系矩阵分析配置
RELATION_ANALYSIS_CONFIG = {
    'enable_real_time_analysis': True,  # 实时关系分析
    'analysis_interval': 10,  # 每10次测试分析一次
    'unknown_relation_threshold': 0.1,  # 未知关系阈值
    
    # 分组质量评估
    'group_quality_metrics': [
        'unknown_relations_ratio',  # 未知关系比例
        'power_source_distribution',  # 电源点位分布
        'test_coverage_efficiency',  # 测试覆盖效率
    ],
    
    # 动态分组调整
    'enable_dynamic_grouping': True,  # 启用动态分组
    'group_adjustment_interval': 20,  # 每20次测试调整一次分组
}

# 完整配置
ADAPTIVE_GROUPING_STRATEGY = {
    **BASE_CONFIG,
    'adaptive_grouping': ADAPTIVE_GROUPING_CONFIG,
    'test_execution': TEST_EXECUTION_CONFIG,
    'relation_analysis': RELATION_ANALYSIS_CONFIG,
    
    # 策略描述
    'strategy_summary': """
    自适应分组测试策略：
    
    1. 基于未知关系比例的阶段切换策略：
       - 第一阶段（30%集群）：100% > 未知关系 > 50%
       - 第二阶段（20%集群）：50% > 未知关系 > 20%
       - 第三阶段（10%集群）：20% > 未知关系 > 10%
       - 第四阶段（二分法）：10% > 未知关系
    
    2. 集群内部关系未知性优化：
       - 优先选择关系未知的点位组合
       - 每组最多10%的点位关系已知
       - 动态调整分组以保持未知关系比例
       - 确保集群内部关系尽可能未知
    
    3. 智能分组选择：
       - 最大化未知关系数量
       - 平衡电源点位分布
       - 避免冗余测试
    
    4. 动态策略调整：
       - 实时监控关系矩阵状态
       - 基于未知关系比例自动切换测试阶段
       - 优化测试效率
    """
}

# 预设配置
PRESETS = {
    'conservative': {
        'group_ratios': [0.25, 0.15, 0.08],  # 更保守的比例
        'max_known_relations_per_group': 0.05,  # 更严格的未知性要求
        'min_unknown_ratio': 0.4,  # 保持更多未知关系
    },
    
    'aggressive': {
        'group_ratios': [0.35, 0.25, 0.15],  # 更激进的比例
        'max_known_relations_per_group': 0.15,  # 允许更多已知关系
        'min_unknown_ratio': 0.2,  # 允许更少未知关系
    },
    
    'balanced': ADAPTIVE_GROUPING_STRATEGY,  # 平衡配置
}

def get_config(preset_name: str = 'balanced') -> dict:
    """获取指定预设的配置"""
    if preset_name not in PRESETS:
        print(f"⚠️  预设 '{preset_name}' 不存在，使用 'balanced' 预设")
        preset_name = 'balanced'
    
    config = PRESETS[preset_name].copy()
    
    # 应用预设覆盖
    if preset_name != 'balanced':
        config['adaptive_grouping'].update(PRESETS[preset_name])
    
    return config

def print_config_summary(config: dict):
    """打印配置摘要"""
    print("🔧 自适应分组测试配置")
    print("=" * 50)
    print(f"策略名称: {config['adaptive_grouping']['strategy_name']}")
    print(f"分组比例: {config['adaptive_grouping']['group_ratios']}")
    print(f"总点位: {config['total_points']}")
    print(f"并发数: {config['concurrency']}")
    print(f"最大测试次数: {config['test_execution']['max_total_tests']}")
    print(f"关系未知性要求: {config['adaptive_grouping']['max_known_relations_per_group']:.1%}")
    print(f"动态调整: {'启用' if config['adaptive_grouping']['enable_dynamic_adjustment'] else '禁用'}")
    print("\n策略描述:")
    print(config['strategy_summary'])

if __name__ == "__main__":
    # 测试配置
    config = get_config('balanced')
    print_config_summary(config)
    
    print("\n可用的预设配置:")
    for preset_name in PRESETS.keys():
        print(f"  - {preset_name}")
