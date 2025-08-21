#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
启动脚本 - 正确启动Flask服务器
解决模块导入问题
"""

import sys
import os

# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

# 添加src目录到Python路径
src_path = os.path.join(project_root, 'src')
sys.path.insert(0, src_path)

print("🚀 启动线缆测试系统Flask服务器...")
print(f"项目根目录: {project_root}")
print(f"Python路径: {sys.path[:3]}")

try:
    # 导入并启动服务器
    from src.server.flask_server import app
    
    print("✅ 服务器导入成功")
    print("🌐 服务器将在 http://localhost:5000 启动")
    print("📡 API接口:")
    print("  - GET  /api/system/info          - 系统信息")
    print("  - GET  /api/relationships/matrix - 关系矩阵")
    print("  - POST /api/experiment           - 执行测试")
    print("  - GET  /api/relay/stats          - 继电器统计")
    print("  - POST /api/relay/reset          - 重置继电器")
    print("\n按 Ctrl+C 停止服务器")
    
    # 启动服务器
    app.run(host='0.0.0.0', port=5000, debug=False)
    
except ImportError as e:
    print(f"❌ 导入错误: {e}")
    print("请检查项目结构和依赖")
    sys.exit(1)
except Exception as e:
    print(f"❌ 启动错误: {e}")
    sys.exit(1)
