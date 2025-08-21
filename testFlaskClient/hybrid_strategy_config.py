#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
混合策略测试配置文件
结合分块策略和二分法策略的智能测试配置
"""

# 混合策略核心配置
HYBRID_STRATEGY_CORE = {
    'enabled': True,
    'strategy_name': 'hybrid_block_binary',
    'description': '混合策略测试 - 分块策略快速确认 + 二分法策略精细化处理',
    'auto_phase_switch': True,  # 自动阶段切换
}

# 阶段切换配置
PHASE_SWITCH_CONFIG = {
    'block_to_binary_threshold': 70.0,  # 分块策略切换到二分法策略的阈值
    'binary_to_block_threshold': 60.0,  # 二分法策略切换回分块策略的阈值（如果效率下降）
    'phase_switch_check_interval': 2,   # 阶段切换检查间隔（轮数）
    'min_phase_duration': 3,            # 最小阶段持续时间（轮数）
}

# 分块策略阶段配置
BLOCK_PHASE_CONFIG = {
    'enabled': True,
    'target_coverage': 50.0,            # 目标覆盖率50%
    'max_batch_size': 50,               # 最大批量大小50
    'min_batch_size': 20,               # 最小批量大小20
    'default_batch_size': 40,           # 默认批量大小40
    'max_targets_per_batch': 25,        # 每批最大目标数25
    'smart_deduplication': True,        # 智能去重
    'avoid_known_relations': True,      # 避免已知关系
    'power_source_rotation': True,      # 电源点轮换
    'batch_optimization': True,         # 批量优化
    'relay_optimization': True,         # 继电器切换优化
    'power_source_prioritization': True, # 通电点位优先级排序
    'min_power_source_coverage': 80.0,  # 最小通电点位覆盖率80%
}

# 二分法策略阶段配置
BINARY_PHASE_CONFIG = {
    'enabled': True,
    'batch_size': 20,                   # 二分法测试批次大小
    'probability_threshold': 0.5,       # 导通概率阈值
    'neighbor_weight': 0.7,             # 邻居关系权重
    'global_density_weight': 0.3,       # 全局密度权重
    'max_iterations_per_source': 5,     # 每个电源点最大迭代次数
    'adaptive_batch_sizing': True,      # 自适应批次大小
    'priority_based_selection': True,   # 基于优先级选择
    'convergence_optimization': True,   # 收敛优化
}

# 性能监控配置
PERFORMANCE_MONITORING = {
    'enable_phase_monitoring': True,    # 启用阶段监控
    'track_phase_efficiency': True,     # 跟踪阶段效率
    'monitor_switch_effectiveness': True, # 监控切换效果
    'performance_thresholds': {
        'min_block_efficiency': 60.0,   # 分块策略最小效率
        'min_binary_efficiency': 40.0,  # 二分法策略最小效率
        'max_phase_switch_frequency': 3, # 最大阶段切换频率（每10轮）
    }
}

# 自适应配置
ADAPTIVE_CONFIG = {
    'enabled': True,
    'dynamic_threshold_adjustment': True, # 动态阈值调整
    'efficiency_based_switching': True,   # 基于效率的切换
    'learning_from_previous_runs': True,  # 从之前运行中学习
    'threshold_adjustment_rules': {
        'efficiency_drop_threshold': 0.1,  # 效率下降阈值
        'improvement_rate_threshold': 0.05, # 改进率阈值
        'stagnation_detection_rounds': 5,   # 停滞检测轮数
    }
}

# 继电器优化配置
RELAY_OPTIMIZATION_CONFIG = {
    'enabled': True,
    'switch_reduction_target': 0.3,     # 切换次数减少目标30%
    'power_source_grouping': True,      # 通电点位分组执行
    'batch_consolidation': True,        # 批次合并优化
    'switch_pattern_analysis': True,    # 切换模式分析
    'optimization_algorithms': {
        'greedy_grouping': True,        # 贪心分组算法
        'dynamic_prioritization': True, # 动态优先级调整
        'switch_cost_analysis': True,   # 切换成本分析
    }
}

# 配置验证函数
def validate_hybrid_strategy_config():
    """验证混合策略配置的有效性"""
    print("验证混合策略配置...")
    
    # 验证阶段切换配置
    if PHASE_SWITCH_CONFIG['block_to_binary_threshold'] <= PHASE_SWITCH_CONFIG['binary_to_block_threshold']:
        raise ValueError("分块到二分法切换阈值必须大于二分法到分块切换阈值")
    
    if PHASE_SWITCH_CONFIG['min_phase_duration'] <= 0:
        raise ValueError("最小阶段持续时间必须大于0")
    
    # 验证分块策略配置
    if BLOCK_PHASE_CONFIG['min_batch_size'] > BLOCK_PHASE_CONFIG['max_batch_size']:
        raise ValueError("分块策略最小批量大小不能大于最大批量大小")
    
    if BLOCK_PHASE_CONFIG['default_batch_size'] < BLOCK_PHASE_CONFIG['min_batch_size']:
        raise ValueError("分块策略默认批量大小不能小于最小批量大小")
    
    # 验证二分法策略配置
    if BINARY_PHASE_CONFIG['neighbor_weight'] + BINARY_PHASE_CONFIG['global_density_weight'] != 1.0:
        raise ValueError("二分法策略权重之和必须等于1.0")
    
    # 验证继电器优化配置
    if RELAY_OPTIMIZATION_CONFIG['switch_reduction_target'] < 0 or RELAY_OPTIMIZATION_CONFIG['switch_reduction_target'] > 1:
        raise ValueError("继电器切换减少目标必须在0-1之间")
    
    print("混合策略配置验证通过")
    return True

# 配置预设
HYBRID_STRATEGY_PRESETS = {
    'balanced_hybrid': {
        'description': '平衡混合配置 - 平衡分块和二分法策略',
        'block_coverage': 50.0,
        'binary_batch_size': 20,
        'switch_threshold': 70.0,
        'max_concurrent_requests': 15,
    },
    'efficient_hybrid': {
        'description': '高效混合配置 - 优先效率',
        'block_coverage': 45.0,
        'binary_batch_size': 25,
        'switch_threshold': 65.0,
        'max_concurrent_requests': 20,
    },
    'precise_hybrid': {
        'description': '精确混合配置 - 优先精度',
        'block_coverage': 55.0,
        'binary_batch_size': 15,
        'switch_threshold': 75.0,
        'max_concurrent_requests': 10,
    }
}

def apply_hybrid_strategy_preset(preset_name: str):
    """应用混合策略预设配置"""
    if preset_name not in HYBRID_STRATEGY_PRESETS:
        print(f"未知的混合策略预设配置: {preset_name}")
        return False
    
    preset = HYBRID_STRATEGY_PRESETS[preset_name]
    print(f"应用混合策略预设配置: {preset['description']}")
    
    # 应用配置
    BLOCK_PHASE_CONFIG['target_coverage'] = preset['block_coverage']
    BINARY_PHASE_CONFIG['batch_size'] = preset['binary_batch_size']
    PHASE_SWITCH_CONFIG['block_to_binary_threshold'] = preset['switch_threshold']
    
    print("混合策略预设配置应用完成")
    return True

# 配置信息打印
def print_hybrid_strategy_config_summary():
    """打印混合策略配置摘要"""
    print("\n=== 混合策略测试配置摘要 ===")
    print(f"策略: {HYBRID_STRATEGY_CORE['strategy_name']}")
    print(f"描述: {HYBRID_STRATEGY_CORE['description']}")
    print(f"自动阶段切换: {'启用' if HYBRID_STRATEGY_CORE['auto_phase_switch'] else '禁用'}")
    print(f"阶段切换阈值: {PHASE_SWITCH_CONFIG['block_to_binary_threshold']}%")
    print(f"分块策略覆盖率: {BLOCK_PHASE_CONFIG['target_coverage']}%")
    print(f"二分法批次大小: {BINARY_PHASE_CONFIG['batch_size']}")
    print(f"智能去重: {'启用' if BLOCK_PHASE_CONFIG['smart_deduplication'] else '禁用'}")
    print(f"自适应配置: {'启用' if ADAPTIVE_CONFIG['enabled'] else '禁用'}")
    print(f"继电器优化: {'启用' if RELAY_OPTIMIZATION_CONFIG['enabled'] else '禁用'}")
    print(f"通电点位轮询: {'启用' if BLOCK_PHASE_CONFIG['power_source_rotation'] else '禁用'}")
    print(f"切换减少目标: {RELAY_OPTIMIZATION_CONFIG['switch_reduction_target']*100:.0f}%")

# 策略执行建议
def get_strategy_execution_advice():
    """获取策略执行建议"""
    advice = {
        'phase_1_block': {
            'description': '第一阶段：分块策略快速确认（优化版）',
            'target': '检测率达到70%',
            'strategy': '使用50%覆盖率策略，所有点位轮询作为通电点位，智能去重，优化继电器切换',
            'expected_duration': '3-5轮',
            'key_metrics': ['检测率', '批量效率', '去重效果', '继电器切换次数', '通电点位覆盖率']
        },
        'phase_2_binary': {
            'description': '第二阶段：二分法策略精细化处理',
            'target': '检测率达到95%+',
            'strategy': '基于概率估算，优先测试高概率点位，小批次精确测试',
            'expected_duration': '5-8轮',
            'key_metrics': ['检测率', '测试精度', '收敛速度']
        },
        'phase_switch': {
            'description': '阶段切换策略',
            'target': '检测率达到70%时自动切换',
            'strategy': '如果二分法效率下降，可切换回分块策略',
            'expected_duration': '实时切换',
            'key_metrics': ['切换时机', '策略效果', '优化建议']
        },
        'relay_optimization': {
            'description': '继电器切换优化策略',
            'target': '减少30%继电器切换次数',
            'strategy': '通电点位分组执行，优先级排序，批量合并优化',
            'expected_duration': '持续优化',
            'key_metrics': ['切换次数', '切换效率', '优化效果']
        }
    }
    return advice

if __name__ == "__main__":
    # 验证配置
    validate_hybrid_strategy_config()
    
    # 打印配置摘要
    print_hybrid_strategy_config_summary()
    
    # 显示可用预设
    print(f"\n可用混合策略预设配置: {list(HYBRID_STRATEGY_PRESETS.keys())}")
    
    # 显示策略执行建议
    advice = get_strategy_execution_advice()
    print("\n=== 策略执行建议 ===")
    for phase, details in advice.items():
        print(f"\n{details['description']}:")
        print(f"  目标: {details['target']}")
        print(f"  策略: {details['strategy']}")
        print(f"  预期时长: {details['expected_duration']}")
        print(f"  关键指标: {', '.join(details['key_metrics'])}")
