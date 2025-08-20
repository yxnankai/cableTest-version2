# 优化测试客户端使用说明

## 概述

优化测试客户端是一个基于关系矩阵分析的高效测试策略实现，主要目标是：

1. **减少继电器切换次数** - 通过批量测试和智能规划
2. **最大化信息增益** - 利用关系矩阵分析选择最优测试点位
3. **提高测试效率** - 减少单对单测试，增加批量测试
4. **智能测试规划** - 基于当前状态动态调整测试策略

## 主要特性

### 🚀 批量测试优化
- **批量模式**：一次测试多个目标点位，减少继电器切换
- **智能分组**：根据信息增益和测试约束自动分组
- **动态调整**：根据测试结果动态调整批量大小

### 🧠 智能测试规划
- **信息增益计算**：基于真实关系矩阵计算每个测试的信息价值
- **优先级排序**：优先测试高信息增益的点位
- **约束满足**：满足继电器操作次数和测试时间约束

### 📊 矩阵分析
- **实时监控**：监控检测率和准确率
- **效率分析**：分析当前测试效率
- **预测优化**：基于已知信息预测最优测试路径

### ⚡ 继电器优化
- **批量切换**：减少单个继电器的切换次数
- **智能轮换**：智能选择电源点，避免重复测试
- **操作计数**：监控继电器操作次数，避免过度使用

## 使用方法

### 1. 基本使用

```python
from optimized_test import OptimizedTestClient

# 创建客户端
client = OptimizedTestClient()

# 运行优化测试
client.run_optimized_testing(
    max_rounds=5,      # 最大测试轮数
    tests_per_round=30  # 每轮测试数量
)
```

### 2. 配置参数

```python
# 导入配置
from config import TEST_STRATEGY, RELAY_OPTIMIZATION

# 查看当前配置
print(f"批量测试: {TEST_STRATEGY['batch_testing']['enabled']}")
print(f"继电器优化: {RELAY_OPTIMIZATION['enabled']}")
```

### 3. 自定义测试策略

```python
# 自定义批量测试参数
client = OptimizedTestClient()
client.run_optimized_testing(
    max_rounds=3,           # 减少轮数
    tests_per_round=50,     # 增加每轮测试数量
)
```

## 测试策略详解

### 策略1: 批量优化测试
```
电源点A → [目标点1, 目标点2, 目标点3, ..., 目标点N]
```
- **优势**：一次继电器操作测试多个点位
- **适用场景**：未归属点位的大规模扫描
- **信息增益**：高（一次测试获得多个关系信息）

### 策略2: 信息增益优先
```
高信息增益点位 → 优先测试
中等信息增益点位 → 次优先测试
低信息增益点位 → 最后测试
```
- **计算方式**：基于真实关系矩阵预测
- **权重设置**：导通(2.0) > 不导通(1.5) > 未知(1.0)

### 策略3: 智能电源点选择
```
未归属点位 → 优先作为电源点
已归属点位 → 跳过（避免重复测试）
边界点位 → 中等优先级
```
- **选择逻辑**：避免测试已知的导通关系
- **轮换机制**：智能轮换电源点，最大化覆盖

## 性能指标

### 检测率 (Detection Rate)
```
检测率 = (已知导通 + 已知不导通) / 总非对角线单元格 × 100%
```

### 准确率 (Accuracy Rate)
```
准确率 = 匹配的关系数量 / 总非对角线单元格 × 100%
```

### 测试覆盖率 (Test Coverage)
```
覆盖率 = 已测试点对数量 / 总点对数量 × 100%
```

### 继电器效率 (Relay Efficiency)
```
继电器效率 = 测试次数 / 继电器操作次数
```

## 配置选项

### 批量测试配置
```python
'batch_testing': {
    'enabled': True,                    # 启用批量测试
    'max_targets_per_source': 20,      # 每个电源点最大目标数
    'min_batch_size': 5,               # 最小批量大小
    'max_batch_size': 50               # 最大批量大小
}
```

### 效率阈值配置
```python
'efficiency_thresholds': {
    'detection_rate_target': 90.0,     # 检测率目标
    'accuracy_rate_target': 95.0,      # 准确率目标
    'coverage_target': 85.0            # 覆盖率目标
}
```

### 继电器优化配置
```python
'relay_optimization': {
    'enabled': True,                    # 启用继电器优化
    'max_relay_operations': 1000,      # 最大操作次数
    'batch_mode': True,                # 批量模式
    'smart_switching': True            # 智能切换
}
```

## 最佳实践

### 1. 测试前准备
- 确保服务器正常运行
- 检查关系矩阵是否已初始化
- 验证导通分布设置是否正确

### 2. 参数调优
- 根据系统规模调整批量大小
- 根据继电器性能调整测试间隔
- 根据时间要求调整轮次数量

### 3. 监控和调整
- 实时监控检测率和准确率
- 观察继电器操作次数
- 根据性能指标动态调整策略

### 4. 错误处理
- 设置合理的重试次数
- 监控网络连接状态
- 记录测试失败的原因

## 故障排除

### 常见问题

1. **连接失败**
   - 检查服务器地址和端口
   - 验证网络连接
   - 检查防火墙设置

2. **测试超时**
   - 增加超时时间
   - 减少每轮测试数量
   - 检查服务器性能

3. **继电器操作过多**
   - 启用批量模式
   - 减少测试轮次
   - 优化测试策略

4. **检测率不提升**
   - 检查测试计划生成
   - 验证关系矩阵更新
   - 调整信息增益权重

### 调试模式

```python
# 启用调试模式
import logging
logging.basicConfig(level=logging.DEBUG)

# 运行测试
client.run_optimized_testing()
```

## 扩展和定制

### 自定义测试策略
```python
class CustomTestClient(OptimizedTestClient):
    def custom_test_strategy(self):
        # 实现自定义测试逻辑
        pass
```

### 自定义信息增益计算
```python
def custom_information_gain(self, power_source, target):
    # 实现自定义信息增益算法
    return custom_score
```

### 自定义批量分组
```python
def custom_batch_grouping(self, candidates):
    # 实现自定义分组逻辑
    return grouped_candidates
```

## 总结

优化测试客户端通过智能的测试规划和批量测试策略，显著提高了测试效率，减少了继电器操作次数。通过关系矩阵分析和信息增益计算，确保每次测试都能获得最大的信息价值。

建议根据具体的系统规模和性能要求，调整配置参数，找到最适合的测试策略。
