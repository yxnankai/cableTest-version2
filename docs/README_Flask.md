# Flask接口系统 - 线缆测试双向测试接口

## 🚀 快速开始

### 1. 安装依赖
```bash
pip install -r requirements.txt
```

### 2. 启动服务端
```bash
# 方式1：使用启动脚本（推荐）
python run_server.py

# 方式2：启动Web版本（带前端界面）
python run_web_server.py

# 方式3：直接运行
python flask_server.py
```

### 3. 使用客户端
```bash
# 交互式界面
python flask_client.py --interactive

# 命令行模式
python flask_client.py --command "get_point_status"
```

### 4. 访问Web界面
```bash
# 启动Web版本后，在浏览器中访问：
http://localhost:5000
```

## 📋 系统功能

### ✅ 已实现功能
- **继电器状态查询**: 查询指定点位或所有点位的继电器开关状态
- **集群信息查询**: 查询已确认的继电器集群连接信息
- **实验设置和执行**: 客户端可设置实验参数，服务端执行并返回结果
- **状态自动更新**: 服务端根据实验结果自动更新点位状态和集群信息
- **批量操作支持**: 支持批量实验执行
- **实时监控**: 客户端可监控指定点位的状态变化
- **错误处理**: 完善的错误处理和日志记录
- **配置管理**: 支持多环境配置

### 🌐 Web版本新增功能
- **前端实时界面**: 现代化的Web界面，支持实时监控
- **WebSocket实时更新**: 每2秒自动推送状态变化，无需刷新
- **可视化数据展示**: 点位状态网格、集群信息、测试历史
- **交互式实验控制**: 手动设置参数、随机实验生成器
- **响应式设计**: 支持桌面和移动设备访问
- **集群可视化**: 不同颜色标识已确认集群，灰色标识未确认点位
- **智能集群合并**: 自动合并共享共同点位的集群
- **系统重置功能**: 一键重置测试数据，重新生成随机连接
- **真实集群对比**: 对比预定义的真实集群与测试发现的集群

## 🏗️ 系统架构

### 核心组件
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Flask Client  │    │  Flask Server   │    │ CableTestSystem │
│                 │◄──►│                 │◄──►│                 │
│ • 状态查询      │    │ • API接口       │    │ • 核心测试逻辑  │
│ • 实验执行      │    │ • 状态管理      │    │ • 继电器控制    │
│ • 批量操作      │    │ • 集群更新      │    │ • 连接检测      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

### Web版本架构
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Web Browser  │    │  Flask Server   │    │ CableTestSystem │
│                 │◄──►│                 │◄──►│                 │
│ • 前端界面      │    │ • Web API       │    │ • 核心测试逻辑  │
│ • WebSocket     │    │ • WebSocket     │    │ • 继电器控制    │
│ • 实时更新      │    │ • 状态推送      │    │ • 连接检测      │
│ • 集群可视化    │    │ • 集群管理      │    │ • 智能合并      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## 📁 文件结构

```
cableTest/
├── README.md                    # 项目说明
├── README_Flask.md             # Flask接口说明
├── requirements.txt             # 依赖包列表
├── config.py                   # 配置文件
├── cable_test_system.py        # 核心测试系统
├── flask_server.py             # Flask服务端（基础版）
├── flask_server_web.py         # Flask服务端（Web版）
├── flask_client.py             # Flask客户端
├── run_server.py               # 服务端启动脚本
├── run_web_server.py           # Web服务端启动脚本
├── demo_flask_system.py        # 系统演示脚本
├── demo_web_system.py          # Web版本演示脚本
├── test_flask_interface.py     # 接口测试脚本
├── Flask_API_测试报文示例.md    # API测试报文示例
└── 使用说明.md                 # 使用说明文档
```

## 🔌 API接口

| 接口 | 方法 | 描述 | 参数 |
|------|------|------|------|
| `/api/health` | GET | 健康检查 | 无 |
| `/api/points/status` | GET | 获取点位状态 | `point_id` (可选) |
| `/api/clusters` | GET | 获取集群信息 | 无 |
| `/api/experiment` | POST | 运行实验 | `power_source`, `test_points` |
| `/api/system/info` | GET | 获取系统信息 | 无 |
| `/api/experiment/batch` | POST | 批量运行实验 | `test_count`, `max_points_per_test` |
| `/api/test/history` | GET | 获取测试历史 | `limit` (可选) |
| `/api/system/reset` | POST | 重置系统 | 无 |
| `/api/clusters/real` | GET | 获取真实集群信息 | 无 |
| `/api/clusters/comparison` | GET | 获取集群对比信息 | 无 |
| `/api/clusters/detailed` | GET | 获取详细集群信息 | 无 |
| `/api/clusters/visualization` | GET | 获取集群可视化数据 | 无 |

## 🎨 集群可视化特性

### 颜色编码系统
- **蓝色系**: 已确认集群1 - `#2196F3`
- **绿色系**: 已确认集群2 - `#4CAF50`
- **紫色系**: 已确认集群3 - `#9C27B0`
- **橙色系**: 已确认集群4 - `#FF9800`
- **青色系**: 已确认集群5 - `#00BCD4`
- **灰色**: 未确认集群点位 - `#9E9E9E`
- **红色**: 关闭状态点位 - `#f44336`

### 智能集群合并
- **共享点位合并**: 自动合并包含共同点位的集群
- **跨集群检测**: 通过导通测试验证集群间连接关系
- **实时更新**: 每次测试后自动重新计算和合并集群

## 🧪 使用示例

### 基础功能测试
```python
from flask_client import FlaskTestClient

# 创建客户端
client = FlaskTestClient("http://localhost:5000")

# 健康检查
health = client.health_check()
print(f"服务状态: {health['status']}")

# 获取点位状态
status = client.get_point_status()
print(f"总点位: {status['total_points']}")

# 运行实验
result = client.run_experiment(
    power_source=0,
    test_points=[1, 2, 3, 4, 5]
)
print(f"实验完成，发现连接: {len(result['connections'])}")
```

### Web界面使用
1. **启动Web服务器**: `python run_web_server.py`
2. **访问界面**: 浏览器打开 `http://localhost:5000`
3. **实时监控**: 查看点位状态、集群信息、测试历史
4. **运行实验**: 设置电源点位和测试点位，点击"开始实验"
5. **随机实验**: 点击"随机实验"自动生成测试参数
6. **系统重置**: 点击"重置系统"清除测试数据
7. **集群分析**: 使用"集群对比"分析测试准确性

## ⚙️ 配置说明

### 环境变量
```bash
# 服务端配置
export FLASK_ENV=testing              # 环境: development/production/testing
export FLASK_HOST=0.0.0.0            # 监听地址
export FLASK_PORT=5000               # 监听端口
export FLASK_DEBUG=True              # 调试模式

# 系统配置
export TOTAL_POINTS=100              # 总点位数量（测试环境）
export RELAY_SWITCH_TIME=0.003      # 继电器切换时间(秒)
```

### 配置文件
```python
# config.py
class TestingConfig(Config):
    FLASK_DEBUG = True
    LOG_LEVEL = 'DEBUG'
    TOTAL_POINTS = 100              # 测试环境使用100个点位
    DATABASE_URL = 'sqlite:///test.db'

class DevelopmentConfig(Config):
    TOTAL_POINTS = 1000             # 开发环境使用1000个点位

class ProductionConfig(Config):
    TOTAL_POINTS = 10000            # 生产环境使用10000个点位
```

## 🚀 启动方式

### 1. 基础版本（无前端界面）
```bash
# 使用启动脚本
python run_server.py

# 直接运行
python flask_server.py
```

### 2. Web版本（带前端界面）
```bash
# 使用启动脚本（推荐）
python run_web_server.py

# 直接运行
python flask_server_web.py
```

### 3. 演示模式
```bash
# 基础版本演示
python demo_flask_system.py

# Web版本演示
python demo_web_system.py
```

## 🧪 测试和验证

### 接口测试
```bash
# 运行接口测试
python test_flask_interface.py

# 测试特定功能
python -c "
from test_flask_interface import test_server_health
test_server_health()
"
```

### 性能测试
```bash
# 使用Apache Bench进行压力测试
ab -n 1000 -c 10 -T "application/json" \
   -p test_data.json "http://localhost:5000/api/experiment"
```

## 🔧 故障排除

### 常见问题

#### 1. 依赖安装失败
```bash
# 解决方案：使用国内镜像
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

#### 2. 端口被占用
```bash
# 解决方案：修改端口
export FLASK_PORT=5001
python run_server.py
```

#### 3. WebSocket连接失败
```bash
# 解决方案：检查防火墙设置
# 确保5000端口开放
```

#### 4. 前端界面无法访问
```bash
# 解决方案：检查服务器是否启动
curl http://localhost:5000/api/health
```

#### 5. 集群对比报错
```bash
# 解决方案：已修复 'target_points is not iterable' 错误
# 现在使用新的 'points' 字段结构
```

### 日志查看
```bash
# 查看服务端日志
tail -f web_server.log

# 查看Flask调试信息
export FLASK_DEBUG=True
python run_web_server.py
```

## 📊 性能指标

- **响应时间**: API接口响应 < 100ms
- **并发处理**: 支持多客户端同时访问
- **实时更新**: WebSocket推送延迟 < 2秒
- **内存使用**: 100点位约占用 5MB 内存（测试环境）
- **CPU使用**: 单次测试 < 5% CPU
- **集群合并**: 支持最多100个集群的智能合并

## 🔮 未来扩展

### 计划功能
- [ ] 数据库持久化存储
- [ ] 用户认证和权限管理
- [ ] 测试报告生成和导出
- [ ] 移动端APP支持
- [ ] 分布式部署支持
- [ ] 实时数据分析和可视化
- [ ] 高级集群分析算法
- [ ] 测试策略优化建议

### 技术改进
- [ ] Redis缓存优化
- [ ] 异步任务队列
- [ ] 微服务架构重构
- [ ] 容器化部署
- [ ] 监控和告警系统
- [ ] 集群合并算法优化

## 📞 技术支持

### 文档资源
- **API文档**: `Flask_API_测试报文示例.md`
- **使用说明**: `使用说明.md`
- **配置说明**: `config.py`
- **快速启动**: `快速启动指南.md`

### 测试工具
- **接口测试**: `test_flask_interface.py`
- **系统演示**: `demo_web_system.py`
- **性能测试**: Apache Bench, JMeter

### 日志和调试
- **服务日志**: `web_server.log`
- **调试模式**: 设置 `FLASK_DEBUG=True`
- **WebSocket**: 浏览器开发者工具

## 🆕 最新更新

### v2.1.0 (2025-08-11)
- ✅ 修复集群对比功能中的 `target_points is not iterable` 错误
- ✅ 改进集群颜色系统，避免与未确认点位混淆
- ✅ 修复开启/关闭数量统计不准确的问题
- ✅ 优化集群合并逻辑，支持智能合并
- ✅ 新增集群可视化API接口
- ✅ 改进前端实时更新机制

### v2.0.0 (2025-08-10)
- 🎉 新增Web前端界面
- 🎉 支持WebSocket实时更新
- 🎉 新增集群可视化功能
- 🎉 支持系统重置和重新生成
- 🎉 新增真实集群对比功能
