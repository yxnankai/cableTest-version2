#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
高效批量测试客户端配置文件
"""

# 服务器配置
SERVER_CONFIG = {
    'base_url': 'http://localhost:5000',
    'timeout': 30,
    'retry_count': 3
}

# 批量测试配置
BATCH_TESTING = {
    'enabled': True,
    'default_batch_size': 50,      # 默认批量大小
    'min_batch_size': 20,          # 最小批量大小
    'max_batch_size': 80,          # 最大批量大小
    'adaptive_batch_size': True,   # 启用自适应批量大小
}

# 并发配置
CONCURRENCY = {
    'max_concurrent_requests': 10,  # 最大并发请求数
    'request_batch_size': 20,       # 每批发送的请求数量
    'thread_pool_workers': 10,      # 线程池工作线程数
    'enable_concurrent_execution': True,  # 启用并发执行
}

# 测试策略配置
TEST_STRATEGY = {
    'strategy': 'massive_batch',    # 策略：massive_batch, adaptive, hybrid
    'priority_based_ordering': True,  # 基于优先级排序
    'unknown_relation_focus': True,   # 优先测试未知关系
    'batch_optimization': True,       # 启用批量优化
}

# 效率阈值配置
EFFICIENCY_THRESHOLDS = {
    'detection_rate_target': 95.0,   # 检测率目标（%）
    'coverage_target': 90.0,         # 覆盖率目标（%）
    'early_stop_threshold': 98.0,    # 提前停止阈值（%）
}

# 自适应配置
ADAPTIVE_CONFIG = {
    'enabled': True,
    'rate_based_adjustment': True,   # 基于检测率调整
    'batch_size_adjustment_rules': {
        'low_rate_threshold': 50.0,   # 低检测率阈值
        'medium_rate_threshold': 80.0, # 中等检测率阈值
        'high_rate_threshold': 90.0,   # 高检测率阈值
        'low_rate_increase': 10,       # 低检测率时增加数量
        'medium_rate_decrease': 5,     # 中等检测率时减少数量
        'high_rate_decrease': 10,      # 高检测率时大幅减少
    }
}

# 性能监控配置
PERFORMANCE_MONITORING = {
    'enabled': True,
    'measure_execution_time': True,   # 测量执行时间
    'track_request_latency': True,    # 跟踪请求延迟
    'monitor_concurrency_efficiency': True,  # 监控并发效率
    'performance_thresholds': {
        'max_batch_execution_time': 60,  # 最大批量执行时间（秒）
        'max_request_latency': 5,        # 最大请求延迟（秒）
        'min_concurrency_efficiency': 0.8,  # 最小并发效率
    }
}

# 网络优化配置
NETWORK_OPTIMIZATION = {
    'connection_pooling': True,      # 启用连接池
    'keep_alive': True,              # 启用保持连接
    'request_compression': False,    # 请求压缩（如果服务器支持）
    'batch_request_optimization': True,  # 批量请求优化
    'network_retry_strategy': {
        'max_retries': 3,
        'retry_delay': 1,
        'exponential_backoff': True,
        'retry_on_status_codes': [500, 502, 503, 504],
    }
}

# 测试结果分析配置
RESULT_ANALYSIS = {
    'detailed_analysis': True,       # 详细分析
    'connection_pattern_analysis': True,  # 连接模式分析
    'efficiency_metrics': True,      # 效率指标
    'progress_tracking': True,       # 进度跟踪
    'result_caching': True,          # 结果缓存
}

# 日志和报告配置
LOGGING_AND_REPORTING = {
    'log_level': 'INFO',             # 日志级别
    'enable_progress_logging': True, # 启用进度日志
    'enable_performance_logging': True,  # 启用性能日志
    'report_format': 'detailed',     # 报告格式
    'save_test_results': True,       # 保存测试结果
    'generate_efficiency_report': True,  # 生成效率报告
}

# 错误处理和恢复配置
ERROR_HANDLING = {
    'max_consecutive_failures': 5,   # 最大连续失败次数
    'failure_recovery_strategy': 'adaptive',  # 失败恢复策略
    'graceful_degradation': True,    # 优雅降级
    'error_logging': True,           # 错误日志
    'automatic_retry': True,         # 自动重试
}

# 测试用例生成配置
TEST_CASE_GENERATION = {
    'strategy': 'unknown_relation_priority',  # 策略
    'point_selection_algorithm': 'max_unknown_count',  # 点位选择算法
    'batch_formation_strategy': 'power_source_centric',  # 批量形成策略
    'constraints': {
        'max_tests_per_round': 100,   # 每轮最大测试数
        'min_tests_per_round': 10,    # 每轮最小测试数
        'max_power_source_changes': 5,  # 最大电源点变更次数
    }
}

# 矩阵分析配置
MATRIX_ANALYSIS = {
    'update_frequency': 'per_round',  # 更新频率
    'analysis_depth': 'full',         # 分析深度
    'efficiency_calculation': True,   # 效率计算
    'progress_tracking': True,        # 进度跟踪
    'prediction_analysis': False,     # 预测分析（如果启用真实矩阵）
}

# 继电器优化配置
RELAY_OPTIMIZATION = {
    'enabled': True,
    'batch_mode': True,               # 批量模式
    'power_source_rotation': True,    # 电源点轮换
    'minimize_switching': True,       # 最小化切换
    'efficiency_tracking': True,      # 效率跟踪
}

# 配置验证
def validate_config():
    """验证配置的有效性"""
    errors = []
    
    # 检查批量大小配置
    if BATCH_TESTING['min_batch_size'] > BATCH_TESTING['default_batch_size']:
        errors.append("最小批量大小不能大于默认批量大小")
    
    if BATCH_TESTING['default_batch_size'] > BATCH_TESTING['max_batch_size']:
        errors.append("默认批量大小不能大于最大批量大小")
    
    # 检查并发配置
    if CONCURRENCY['max_concurrent_requests'] <= 0:
        errors.append("最大并发请求数必须大于0")
    
    if CONCURRENCY['request_batch_size'] <= 0:
        errors.append("请求批次大小必须大于0")
    
    # 检查效率阈值
    if EFFICIENCY_THRESHOLDS['detection_rate_target'] > 100:
        errors.append("检测率目标不能超过100%")
    
    if EFFICIENCY_THRESHOLDS['coverage_target'] > 100:
        errors.append("覆盖率目标不能超过100%")
    
    if errors:
        print("配置验证失败:")
        for error in errors:
            print(f"  - {error}")
        return False
    
    print("配置验证通过")
    return True

# 配置预设
PRESET_CONFIGS = {
    'high_performance': {
        'description': '高性能配置 - 适合大规模系统',
        'batch_size': 80,
        'max_concurrent_requests': 20,
        'request_batch_size': 30,
        'detection_rate_target': 98.0,
    },
    'balanced': {
        'description': '平衡配置 - 平衡性能和稳定性',
        'batch_size': 50,
        'max_concurrent_requests': 10,
        'request_batch_size': 20,
        'detection_rate_target': 95.0,
    },
    'conservative': {
        'description': '保守配置 - 适合稳定性要求高的环境',
        'batch_size': 30,
        'max_concurrent_requests': 5,
        'request_batch_size': 10,
        'detection_rate_target': 90.0,
    }
}

def apply_preset_config(preset_name: str):
    """应用预设配置"""
    if preset_name not in PRESET_CONFIGS:
        print(f"未知的预设配置: {preset_name}")
        return False
    
    preset = PRESET_CONFIGS[preset_name]
    print(f"应用预设配置: {preset['description']}")
    
    # 应用配置
    BATCH_TESTING['default_batch_size'] = preset['batch_size']
    CONCURRENCY['max_concurrent_requests'] = preset['max_concurrent_requests']
    CONCURRENCY['request_batch_size'] = preset['request_batch_size']
    EFFICIENCY_THRESHOLDS['detection_rate_target'] = preset['detection_rate_target']
    
    print("预设配置应用完成")
    return True

# 配置信息
def print_config_summary():
    """打印配置摘要"""
    print("=== 高效批量测试客户端配置摘要 ===")
    print(f"批量大小: {BATCH_TESTING['default_batch_size']} (范围: {BATCH_TESTING['min_batch_size']}-{BATCH_TESTING['max_batch_size']})")
    print(f"并发请求数: {CONCURRENCY['max_concurrent_requests']}")
    print(f"请求批次大小: {CONCURRENCY['request_batch_size']}")
    print(f"检测率目标: {EFFICIENCY_THRESHOLDS['detection_rate_target']}%")
    print(f"自适应批量大小: {'启用' if BATCH_TESTING['adaptive_batch_size'] else '禁用'}")
    print(f"并发执行: {'启用' if CONCURRENCY['enable_concurrent_execution'] else '禁用'}")
    print("=" * 50)

if __name__ == "__main__":
    # 验证配置
    validate_config()
    
    # 打印配置摘要
    print_config_summary()
    
    # 显示可用预设
    print("\n可用预设配置:")
    for name, preset in PRESET_CONFIGS.items():
        print(f"  {name}: {preset['description']}")
