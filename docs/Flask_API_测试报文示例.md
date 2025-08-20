# Flask API 测试报文示例说明

## 📋 概述

本文档提供了线缆测试系统Flask API的详细测试报文示例，包括所有接口的请求格式、响应格式和实际使用案例。

## 🔌 基础信息

- **基础URL**: `http://localhost:5000`
- **API前缀**: `/api`
- **内容类型**: `application/json`
- **字符编码**: `UTF-8`

## 📡 API接口列表

### 1. 健康检查

#### 请求
```bash
GET /api/health
```

#### 响应示例
```json
{
    "status": "healthy",
    "timestamp": 1703123456.789,
    "service": "Cable Test System Web Server"
}
```

#### cURL示例
```bash
curl -X GET "http://localhost:5000/api/health"
```

### 2. 获取点位状态

#### 请求
```bash
# 获取所有点位状态
GET /api/points/status

# 获取指定点位状态
GET /api/points/status?point_id=123
```

#### 响应示例

**所有点位状态:**
```json
{
    "success": true,
    "total_points": 10000,
    "point_states": {
        "0": "off",
        "1": "off",
        "2": "on",
        "3": "off",
        "9999": "off"
    },
    "timestamp": 1703123456.789
}
```

**指定点位状态:**
```json
{
    "success": true,
    "point_id": 123,
    "state": "on",
    "timestamp": 1703123456.789
}
```

#### cURL示例
```bash
# 获取所有点位状态
curl -X GET "http://localhost:5000/api/points/status"

# 获取指定点位状态
curl -X GET "http://localhost:5000/api/points/status?point_id=123"
```

### 3. 获取集群信息

#### 请求
```bash
GET /api/clusters
```

#### 响应示例
```json
{
    "success": true,
    "total_clusters": 3,
    "clusters": [
        {
            "power_source": 0,
            "connected_points": [1, 2, 5],
            "connection_type": "one_to_many"
        },
        {
            "power_source": 10,
            "connected_points": [15],
            "connection_type": "one_to_one"
        },
        {
            "power_source": 100,
            "connected_points": [101, 102, 103, 104],
            "connection_type": "one_to_many"
        }
    ],
    "timestamp": 1703123456.789
}
```

#### cURL示例
```bash
curl -X GET "http://localhost:5000/api/clusters"
```

### 4. 运行实验

#### 请求
```bash
POST /api/experiment
Content-Type: application/json

{
    "power_source": 0,
    "test_points": [1, 2, 3, 4, 5]
}
```

#### 请求参数说明
- `power_source` (必需): 电源点位ID (0-9999)
- `test_points` (可选): 测试点位ID列表，留空则测试所有点位

#### 响应示例
```json
{
    "success": true,
    "test_result": {
        "power_source": 0,
        "test_points": [1, 2, 3, 4, 5],
        "connections": [
            {
                "power_source": 0,
                "connected_points": [1, 2],
                "connection_type": "one_to_many"
            }
        ],
        "duration": 0.045,
        "relay_operations": 15,
        "timestamp": 1703123456.789
    }
}
```

#### cURL示例
```bash
curl -X POST "http://localhost:5000/api/experiment" \
     -H "Content-Type: application/json" \
     -d '{
         "power_source": 0,
         "test_points": [1, 2, 3, 4, 5]
     }'
```

### 5. 获取系统信息

#### 请求
```bash
GET /api/system/info
```

#### 响应示例
```json
{
    "success": true,
    "total_points": 10000,
    "relay_switch_time": 0.003,
    "confirmed_clusters": 3,
    "total_tests": 15,
    "timestamp": 1703123456.789
}
```

#### cURL示例
```bash
curl -X GET "http://localhost:5000/api/system/info"
```

### 6. 获取测试历史

#### 请求
```bash
# 获取最近50次测试记录
GET /api/test/history

# 获取最近10次测试记录
GET /api/test/history?limit=10
```

#### 响应示例
```json
{
    "success": true,
    "test_history": [
        {
            "timestamp": 1703123456.789,
            "test_id": 15,
            "power_source": 0,
            "test_points": [1, 2, 3, 4, 5],
            "connections_found": 1,
            "duration": 0.045,
            "relay_operations": 15
        },
        {
            "timestamp": 1703123400.123,
            "test_id": 14,
            "power_source": 10,
            "test_points": [11, 12, 13],
            "connections_found": 1,
            "duration": 0.032,
            "relay_operations": 12
        }
    ],
    "total_tests": 15,
    "timestamp": 1703123456.789
}
```

#### cURL示例
```bash
# 获取最近50次测试记录
curl -X GET "http://localhost:5000/api/test/history"

# 获取最近10次测试记录
curl -X GET "http://localhost:5000/api/test/history?limit=10"
```

### 7. 批量运行实验

#### 请求
```bash
POST /api/experiment/batch
Content-Type: application/json

{
    "test_count": 5,
    "max_points_per_test": 100
}
```

#### 请求参数说明
- `test_count`: 要运行的测试数量 (默认: 5)
- `max_points_per_test`: 每次测试的最大点位数量 (默认: 100)

#### 响应示例
```json
{
    "success": true,
    "batch_results": [
        {
            "success": true,
            "test_result": {
                "power_source": 0,
                "test_points": [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
                "connections": [],
                "duration": 0.023,
                "relay_operations": 10,
                "timestamp": 1703123456.789
            }
        },
        {
            "success": true,
            "test_result": {
                "power_source": 10,
                "test_points": [10, 11, 12, 13, 14, 15, 16, 17, 18, 19],
                "connections": [
                    {
                        "power_source": 10,
                        "connected_points": [15],
                        "connection_type": "one_to_one"
                    }
                ],
                "duration": 0.034,
                "relay_operations": 10,
                "timestamp": 1703123457.123
            }
        }
    ],
    "total_tests": 2
}
```

#### cURL示例
```bash
curl -X POST "http://localhost:5000/api/experiment/batch" \
     -H "Content-Type: application/json" \
     -d '{
         "test_count": 5,
         "max_points_per_test": 100
     }'
```

## 🧪 测试场景示例

### 场景1: 基础功能测试

```bash
# 1. 检查服务健康状态
curl -X GET "http://localhost:5000/api/health"

# 2. 获取系统信息
curl -X GET "http://localhost:5000/api/system/info"

# 3. 运行简单实验
curl -X POST "http://localhost:5000/api/experiment" \
     -H "Content-Type: application/json" \
     -d '{"power_source": 0}'

# 4. 查看实验结果
curl -X GET "http://localhost:5000/api/points/status"
curl -X GET "http://localhost:5000/api/clusters"
```

### 场景2: 批量测试

```bash
# 运行批量测试
curl -X POST "http://localhost:5000/api/experiment/batch" \
     -H "Content-Type: application/json" \
     -d '{"test_count": 10, "max_points_per_test": 50}'

# 查看测试历史
curl -X GET "http://localhost:5000/api/test/history?limit=20"
```

### 场景3: 指定点位测试

```bash
# 测试指定点位
curl -X POST "http://localhost:5000/api/experiment" \
     -H "Content-Type: application/json" \
     -d '{
         "power_source": 100,
         "test_points": [101, 102, 103, 104, 105]
     }'

# 查看特定点位状态
curl -X GET "http://localhost:5000/api/points/status?point_id=101"
```

## 🔧 错误处理

### 常见错误响应

#### 400 Bad Request
```json
{
    "success": false,
    "error": "无效的请求数据"
}
```

#### 500 Internal Server Error
```json
{
    "success": false,
    "error": "实验执行失败: 点位超出范围"
}
```

#### 点位不存在
```json
{
    "success": false,
    "error": "点位 99999 不存在"
}
```

## 📱 前端界面使用

### 访问地址
- **主页**: `http://localhost:5000`
- **实时监控**: 自动刷新，每2秒更新一次

### 功能特性
- 🧪 **实验设置**: 手动输入电源点位和测试点位
- 🎲 **随机实验**: 自动生成随机测试参数
- 📊 **实时状态**: 显示点位开关状态、集群信息
- 📈 **测试历史**: 查看所有测试记录和结果
- 🔄 **自动更新**: WebSocket实时推送状态变化

## 🚀 性能测试

### 压力测试示例

```bash
# 使用Apache Bench进行压力测试
ab -n 1000 -c 10 -T "application/json" -p test_data.json "http://localhost:5000/api/experiment"

# test_data.json 内容:
{
    "power_source": 0,
    "test_points": [1, 2, 3, 4, 5]
}
```

### 批量测试性能
- **单次测试**: 通常 < 100ms
- **批量测试**: 10次测试约 500ms
- **并发处理**: 支持多客户端同时访问

## 📝 注意事项

1. **点位范围**: 所有点位ID必须在 0-9999 范围内
2. **数据格式**: 请求必须使用JSON格式，Content-Type设置为application/json
3. **实时更新**: 前端界面通过WebSocket实时更新，无需手动刷新
4. **错误处理**: 所有API都返回统一的错误格式，包含success字段和error信息
5. **性能考虑**: 大量点位测试时建议分批进行，避免超时

## 🔍 调试技巧

### 查看日志
```bash
# 查看Web服务器日志
tail -f web_server.log

# 查看Flask调试信息
export FLASK_DEBUG=True
python run_web_server.py
```

### 测试工具推荐
- **Postman**: API测试和调试
- **curl**: 命令行测试
- **浏览器开发者工具**: 查看WebSocket连接和API请求
- **Apache Bench**: 性能压力测试

## 🆕 新增功能API

### 8. 重置系统

#### 请求
```bash
POST /api/system/reset
```

#### 响应示例
```json
{
    "success": true,
    "message": "系统已重置并重新生成随机连接关系",
    "timestamp": 1703123456.789
}
```

#### cURL示例
```bash
curl -X POST "http://localhost:5000/api/system/reset"
```

### 9. 获取真实集群信息
#### 请求
```bash
GET /api/clusters/real
```

#### 响应示例
```json
{
    "success": true,
    "real_clusters": [
        {
            "cluster_id": "real_cluster_0",
            "points": [0, 1, 2, 3],
            "point_count": 4,
            "is_real": true,
            "timestamp": 1703123456.789
        },
        {
            "cluster_id": "real_cluster_1",
            "points": [5, 6, 7],
            "point_count": 3,
            "is_real": true,
            "timestamp": 1703123456.789
        }
    ],
    "total_real_clusters": 2,
    "timestamp": 1703123456.789
}
```

#### cURL示例
```bash
curl -X GET "http://localhost:5000/api/clusters/real"
```

### 10. 获取集群对比信息
#### 请求
```bash
GET /api/clusters/comparison
```

#### 响应示例
```json
{
    "success": true,
    "comparison": {
        "real_clusters_count": 5,
        "confirmed_clusters_count": 3,
        "matched_clusters_count": 2,
        "accuracy_rate": 40.0,
        "real_clusters": [
            {
                "cluster_id": "real_cluster_0",
                "points": [0, 1, 2, 3],
                "point_count": 4,
                "is_real": true,
                "timestamp": 1703123456.789
            }
        ],
        "confirmed_clusters": [
            {
                "cluster_id": "cluster_1_0",
                "source_point": 0,
                "target_points": [1, 2, 3],
                "connection_type": "one_to_many",
                "test_id": 1,
                "timestamp": 1703123456.789
            }
        ],
        "matched_clusters": [
            {
                "real_cluster": {
                    "cluster_id": "real_cluster_0",
                    "points": [0, 1, 2, 3],
                    "point_count": 4,
                    "is_real": true,
                    "timestamp": 1703123456.789
                },
                "confirmed_cluster": {
                    "cluster_id": "cluster_1_0",
                    "source_point": 0,
                    "target_points": [1, 2, 3],
                    "connection_type": "one_to_many",
                    "test_id": 1,
                    "timestamp": 1703123456.789
                }
            }
        ]
    },
    "timestamp": 1703123456.789
}
```

#### cURL示例
```bash
curl -X GET "http://localhost:5000/api/clusters/comparison"
```

## 🎯 新增功能使用说明
### 系统重置功能
- **用途**: 清除所有测试历史，重新生成随机连接关系
- **适用场景**: 测试完成后重新开始，或需要新的随机数据
- **注意事项**: 重置后所有历史数据将丢失

### 真实集群查看
- **用途**: 查看系统预定义的真实连接关系，以点位群组的形式展示
- **适用场景**: 验证测试结果的准确性，了解系统真实状态
- **数据来源**: 系统初始化时随机生成的连接关系，自动归并为点位群组
- **数据结构**: 每个真实集群包含一个点位组，点位之间完全对等，不区分电源和目标

### 集群对比分析
- **用途**: 对比真实集群与已确认集群的差异
- **适用场景**: 评估测试算法的准确性，发现未检测到的连接
- **指标说明**:
  - 准确率 = 匹配集群数 / 真实集群数 × 100%
  - 匹配集群数 = 真实集群中与已确认集群点位完全匹配的数量
- **匹配逻辑**: 通过点位集合比较，如果两个集群包含相同的点位集合，则认为匹配
