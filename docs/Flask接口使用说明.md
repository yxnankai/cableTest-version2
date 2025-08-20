# Flask接口系统使用说明

## 概述

本系统提供了一个基于Flask的双向测试接口，用于线缆测试系统的远程控制和监控。系统分为服务端和客户端两个部分，支持继电器状态查询、集群信息查询以及实验设置和执行。

## 系统架构

```
┌─────────────────┐    HTTP API    ┌─────────────────┐
│   Flask客户端   │ ◄────────────► │   Flask服务端   │
│                 │                │                 │
│ • 状态查询      │                │ • 状态管理      │
│ • 集群查询      │                │ • 实验执行      │
│ • 实验设置      │                │ • 数据更新      │
│ • 结果接收      │                │ • 结果返回      │
└─────────────────┘                └─────────────────┘
```

## 文件结构

```
cableTest/
├── flask_server.py          # Flask服务端主程序
├── flask_client.py          # Flask客户端主程序
├── run_server.py            # 服务端启动脚本
├── config.py                # 配置文件
├── test_flask_interface.py  # 接口测试脚本
├── cable_test_system.py     # 核心测试系统
├── requirements.txt         # 依赖包列表
└── Flask接口使用说明.md     # 本文档
```

## 安装依赖

在运行系统之前，请确保安装所需的Python包：

```bash
pip install -r requirements.txt
```

主要依赖包：
- `flask>=2.3.0` - Web框架
- `flask-cors>=4.0.0` - 跨域支持
- `requests>=2.31.0` - HTTP客户端

## 快速开始

### 1. 启动服务端

```bash
# 方式1：使用启动脚本（推荐）
python run_server.py

# 方式2：直接运行
python flask_server.py

# 方式3：设置环境变量后运行
set FLASK_ENV=development
python run_server.py
```

服务端将在 `http://localhost:5000` 启动，提供以下API接口：

- `GET /api/health` - 健康检查
- `GET /api/points/status` - 查询点位状态
- `GET /api/clusters` - 查询集群信息
- `POST /api/experiment` - 执行单个实验
- `POST /api/experiment/batch` - 执行批量实验
- `GET /api/system/info` - 获取系统信息

### 2. 使用客户端

```bash
# 方式1：交互式界面
python flask_client.py --interactive

# 方式2：演示模式
python flask_client.py

# 方式3：指定服务端地址
python flask_client.py --server http://192.168.1.100:5000
```

## API接口详解

### 健康检查

**接口**: `GET /api/health`

**响应示例**:
```json
{
  "status": "healthy",
  "timestamp": 1703123456.789,
  "total_points": 10000
}
```

### 点位状态查询

**接口**: `GET /api/points/status`

**参数**:
- `point_id` (可选): 指定点位ID，不提供则返回所有点位状态

**响应示例**:
```json
{
  "success": true,
  "data": {
    "point_id": 1,
    "relay_state": 0,
    "voltage": 0.0,
    "current": 0.0,
    "is_connected": false
  }
}
```

**继电器状态说明**:
- `0`: 关闭 (OFF)
- `1`: 开启 (ON)

### 集群信息查询

**接口**: `GET /api/clusters`

**响应示例**:
```json
{
  "success": true,
  "data": {
    "total_clusters": 2,
    "clusters": [
      {
        "cluster_id": "cluster_1",
        "power_source": 1,
        "connected_points": [2, 3, 4],
        "connection_type": "one_to_many",
        "discovered_at": 1703123456.789,
        "test_id": "test_001"
      }
    ]
  }
}
```

### 实验执行

**接口**: `POST /api/experiment`

**请求体**:
```json
{
  "power_source": 1,
  "test_points": [2, 3, 4, 5]
}
```

**参数说明**:
- `power_source`: 电源点位ID（必需）
- `test_points`: 测试点位ID列表（可选，不提供则随机选择）

**响应示例**:
```json
{
  "success": true,
  "data": {
    "test_id": "test_001",
    "timestamp": 1703123456.789,
    "power_source": 1,
    "active_points": [2, 3, 4, 5],
    "detected_connections": [
      {
        "source_point": 1,
        "target_points": [2, 3],
        "connection_type": "one_to_many"
      }
    ],
    "test_duration": 0.015,
    "relay_operations": 8,
    "total_points": 10000
  }
}
```

### 批量实验

**接口**: `POST /api/experiment/batch`

**请求体**:
```json
{
  "test_count": 5,
  "max_points_per_test": 100
}
```

**参数说明**:
- `test_count`: 测试数量
- `max_points_per_test`: 每个测试的最大点位数量

## 客户端功能

### 基本功能

1. **健康检查**: 验证服务端连接状态
2. **状态查询**: 查询指定点位或所有点位的继电器状态
3. **集群查询**: 查询已确认的继电器集群信息
4. **实验执行**: 设置并执行单个实验
5. **批量实验**: 执行多个随机配置的实验
6. **系统信息**: 获取系统配置和统计信息

### 高级功能

1. **状态监控**: 持续监控指定点位的状态变化
2. **交互式界面**: 提供命令行交互界面
3. **错误处理**: 自动重试和错误报告
4. **日志记录**: 详细的操作日志

### 使用示例

#### 查询点位状态

```python
from flask_client import FlaskTestClient

client = FlaskTestClient("http://localhost:5000")

# 查询特定点位状态
result = client.get_point_status(1)
if result['success']:
    print(f"点位1状态: {result['data']['relay_state']}")

# 查询所有点位状态
result = client.get_point_status()
if result['success']:
    print(f"总点位数量: {len(result['data'])}")
```

#### 执行实验

```python
from flask_client import FlaskTestClient, ExperimentConfig

client = FlaskTestClient("http://localhost:5000")

# 创建实验配置
config = ExperimentConfig(
    power_source=1,
    test_points=[2, 3, 4, 5]
)

# 执行实验
result = client.run_experiment(config)
if result['success']:
    data = result['data']
    print(f"实验完成，检测到 {len(data['detected_connections'])} 个连接")
```

#### 监控点位状态

```python
# 监控点位1和2的状态变化，每2秒检查一次，持续60秒
client.monitor_point_status([1, 2], interval=2.0, duration=60.0)
```

## 配置管理

### 环境变量

系统支持通过环境变量进行配置：

```bash
# Flask配置
set FLASK_HOST=0.0.0.0
set FLASK_PORT=5000
set FLASK_DEBUG=True

# 测试系统配置
set TOTAL_POINTS=10000
set RELAY_SWITCH_TIME=0.003

# 日志配置
set LOG_LEVEL=INFO
set LOG_FILE=cable_test.log
```

### 配置文件

系统使用 `config.py` 进行配置管理，支持三种环境：

- **development**: 开发环境（默认）
- **production**: 生产环境
- **testing**: 测试环境

## 测试验证

### 运行测试

```bash
# 确保服务端已启动
python run_server.py

# 在另一个终端运行测试
python test_flask_interface.py
```

### 测试内容

测试脚本将验证以下功能：

1. 服务端健康状态
2. 客户端基本功能
3. 实验执行流程
4. 状态更新机制
5. 错误处理能力

## 故障排除

### 常见问题

1. **服务端无法启动**
   - 检查端口是否被占用
   - 确认依赖包已正确安装
   - 查看错误日志

2. **客户端连接失败**
   - 确认服务端已启动
   - 检查服务端地址和端口
   - 验证网络连接

3. **实验执行失败**
   - 检查实验配置参数
   - 确认点位ID有效
   - 查看服务端日志

### 日志查看

系统会生成详细的日志文件：

```bash
# 查看日志文件
tail -f cable_test.log

# 查看Flask应用日志
python flask_server.py 2>&1 | tee server.log
```

## 扩展开发

### 添加新的API接口

1. 在 `flask_server.py` 中添加新的路由
2. 在 `FlaskTestServer` 类中实现相应的方法
3. 在客户端中添加对应的调用方法

### 自定义配置

1. 修改 `config.py` 中的配置类
2. 添加新的环境变量支持
3. 更新启动脚本的配置逻辑

### 集成其他系统

系统设计为模块化架构，可以轻松集成：

- 数据库持久化
- 消息队列
- 监控系统
- Web界面

## 性能优化

### 服务端优化

1. 使用生产级WSGI服务器（如Gunicorn）
2. 启用缓存机制
3. 优化数据库查询
4. 负载均衡

### 客户端优化

1. 连接池管理
2. 请求重试机制
3. 批量操作
4. 异步处理

## 安全考虑

1. **身份验证**: 在生产环境中添加API密钥或JWT认证
2. **访问控制**: 限制API访问权限
3. **输入验证**: 验证所有输入参数
4. **日志安全**: 避免记录敏感信息
5. **HTTPS**: 在生产环境中使用HTTPS

## 总结

Flask接口系统为线缆测试提供了完整的双向测试能力，支持：

- ✅ 继电器状态查询
- ✅ 集群信息查询  
- ✅ 实验设置和执行
- ✅ 状态自动更新
- ✅ 批量操作支持
- ✅ 实时监控功能
- ✅ 错误处理机制
- ✅ 配置管理
- ✅ 扩展性设计

通过本系统，用户可以远程控制测试设备，实时监控测试状态，并自动更新系统信息，大大提高了测试效率和便利性。
