#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简化启动脚本 - 启动Flask服务器
"""

import sys
import os

# 添加src目录到Python路径
current_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.join(current_dir, 'src')
sys.path.insert(0, src_dir)

print("🚀 启动线缆测试系统Flask服务器...")
print(f"当前目录: {current_dir}")
print(f"添加路径: {src_dir}")

try:
    # 导入服务器
    from server.flask_server import app
    
    print("✅ 服务器导入成功")
    print("🌐 启动服务器...")
    
    # 启动服务器
    app.run(host='0.0.0.0', port=5000, debug=False)
    
except ImportError as e:
    print(f"❌ 导入错误: {e}")
    print("请确保在项目根目录运行此脚本")
    sys.exit(1)
except Exception as e:
    print(f"❌ 启动错误: {e}")
    sys.exit(1)
