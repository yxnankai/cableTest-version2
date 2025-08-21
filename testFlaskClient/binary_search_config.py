#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
二分法智能测试配置文件
专门针对高精度、高效率的导通关系测试优化
"""

# 二分法测试核心配置
BINARY_SEARCH_CORE = {
    'enabled': True,
    'strategy_name': 'binary_search_intelligent',
    'description': '二分法智能测试 - 基于概率的逐步收敛策略',
}

# 批次大小配置
BATCH_SIZING = {
    'initial_batch_size': 20,          # 初始批次大小
    'min_batch_size': 10,              # 最小批次大小
    'max_batch_size': 30,              # 最大批次大小
    'adaptive_enabled': True,           # 启用自适应批次大小
    'size_adjustment_factor': 0.8,     # 批次大小调整因子
}

# 概率估算配置
PROBABILITY_ESTIMATION = {
    'neighbor_weight': 0.7,            # 邻居关系权重
    'global_density_weight': 0.3,      # 全局密度权重
    'probability_threshold': 0.5,       # 导通概率阈值
    'min_probability': 0.1,            # 最小概率值
    'max_probability': 0.9,            # 最大概率值
    'default_probability': 0.5,        # 默认概率值
}

# 电源点选择策略
SOURCE_SELECTION = {
    'unknown_relation_weight': 0.7,    # 未知关系数量权重
    'potential_conductive_weight': 0.3, # 潜在导通关系权重
    'min_unknown_relations': 5,        # 最小未知关系数量要求
    'max_candidates': 10,              # 最大候选电源点数量
    'selection_rounds': 3,             # 电源点选择轮数
}

# 测试执行配置
TEST_EXECUTION = {
    'max_iterations_per_source': 5,    # 每个电源点的最大迭代次数
    'concurrent_tests': 3,             # 并发测试数量
    'test_interval': 0.1,              # 测试间隔（秒）
    'result_update_delay': 0.05,       # 结果更新延迟（秒）
}

# 收敛控制配置
CONVERGENCE_CONTROL = {
    'target_detection_rate': 98.0,     # 目标检测率
    'early_stop_threshold': 99.0,      # 提前停止阈值
    'min_improvement_rate': 0.5,       # 最小改进率
    'stagnation_rounds': 3,            # 停滞轮数阈值
    'convergence_check_interval': 2,   # 收敛检查间隔（轮数）
}

# 性能监控配置
PERFORMANCE_MONITORING = {
    'enable_real_time_monitoring': True,    # 启用实时监控
    'metrics_update_interval': 1.0,        # 指标更新间隔（秒）
    'performance_logging': True,            # 性能日志记录
    'efficiency_tracking': True,            # 效率跟踪
}

# 错误处理和重试配置
ERROR_HANDLING = {
    'max_retry_attempts': 3,               # 最大重试次数
    'retry_delay': 1.0,                    # 重试延迟（秒）
    'exponential_backoff': True,            # 指数退避
    'fault_tolerance_threshold': 0.1,      # 容错阈值
}

# 配置验证函数
def validate_binary_search_config():
    """验证二分法测试配置的有效性"""
    print("验证二分法测试配置...")
    
    # 验证批次大小配置
    if BATCH_SIZING['min_batch_size'] > BATCH_SIZING['max_batch_size']:
        raise ValueError("最小批次大小不能大于最大批次大小")
    
    if BATCH_SIZING['initial_batch_size'] < BATCH_SIZING['min_batch_size']:
        raise ValueError("初始批次大小不能小于最小批次大小")
    
    # 验证概率配置
    if PROBABILITY_ESTIMATION['neighbor_weight'] + PROBABILITY_ESTIMATION['global_density_weight'] != 1.0:
        raise ValueError("邻居权重和全局密度权重之和必须等于1.0")
    
    if PROBABILITY_ESTIMATION['min_probability'] >= PROBABILITY_ESTIMATION['max_probability']:
        raise ValueError("最小概率值必须小于最大概率值")
    
    # 验证权重配置
    if SOURCE_SELECTION['unknown_relation_weight'] + SOURCE_SELECTION['potential_conductive_weight'] != 1.0:
        raise ValueError("电源点选择权重之和必须等于1.0")
    
    print("二分法测试配置验证通过")
    return True

# 配置预设
BINARY_SEARCH_PRESETS = {
    'high_precision': {
        'description': '高精度配置 - 适合需要极高精度的测试',
        'batch_size': 15,
        'probability_threshold': 0.6,
        'target_detection_rate': 99.0,
        'concurrent_tests': 2,
    },
    'balanced': {
        'description': '平衡配置 - 平衡精度和效率',
        'batch_size': 20,
        'probability_threshold': 0.5,
        'target_detection_rate': 98.0,
        'concurrent_tests': 3,
    },
    'high_efficiency': {
        'description': '高效率配置 - 适合快速测试',
        'batch_size': 25,
        'probability_threshold': 0.4,
        'target_detection_rate': 95.0,
        'concurrent_tests': 4,
    }
}

def apply_binary_search_preset(preset_name: str):
    """应用二分法测试预设配置"""
    if preset_name not in BINARY_SEARCH_PRESETS:
        print(f"未知的二分法测试预设配置: {preset_name}")
        return False
    
    preset = BINARY_SEARCH_PRESETS[preset_name]
    print(f"应用二分法测试预设配置: {preset['description']}")
    
    # 应用配置
    BATCH_SIZING['initial_batch_size'] = preset['batch_size']
    PROBABILITY_ESTIMATION['probability_threshold'] = preset['probability_threshold']
    CONVERGENCE_CONTROL['target_detection_rate'] = preset['target_detection_rate']
    TEST_EXECUTION['concurrent_tests'] = preset['concurrent_tests']
    
    print("二分法测试预设配置应用完成")
    return True

# 配置信息打印
def print_binary_search_config_summary():
    """打印二分法测试配置摘要"""
    print("\n=== 二分法智能测试配置摘要 ===")
    print(f"策略: {BINARY_SEARCH_CORE['strategy_name']}")
    print(f"描述: {BINARY_SEARCH_CORE['description']}")
    print(f"批次大小: {BATCH_SIZING['initial_batch_size']} (范围: {BATCH_SIZING['min_batch_size']}-{BATCH_SIZING['max_batch_size']})")
    print(f"概率阈值: {PROBABILITY_ESTIMATION['probability_threshold']}")
    print(f"目标检测率: {CONVERGENCE_CONTROL['target_detection_rate']}%")
    print(f"并发测试数: {TEST_EXECUTION['concurrent_tests']}")
    print(f"邻居权重: {PROBABILITY_ESTIMATION['neighbor_weight']}")
    print(f"全局密度权重: {PROBABILITY_ESTIMATION['global_density_weight']}")

if __name__ == "__main__":
    # 验证配置
    validate_binary_search_config()
    
    # 打印配置摘要
    print_binary_search_config_summary()
    
    # 显示可用预设
    print(f"\n可用预设配置: {list(BINARY_SEARCH_PRESETS.keys())}")
