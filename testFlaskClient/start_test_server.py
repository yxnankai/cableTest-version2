#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
启动测试端服务器
"""

import sys
import os

# 添加当前目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from test_server import app

if __name__ == '__main__':
    print("🚀 启动测试端服务器...")
    print("=" * 50)
    print("测试端配置界面: http://localhost:5001")
    print("主服务器地址: http://localhost:5000")
    print("=" * 50)
    print("请确保主服务器已启动！")
    print("=" * 50)
    
    try:
        app.run(host='0.0.0.0', port=5001, debug=True)
    except KeyboardInterrupt:
        print("\n⚠️  服务器已停止")
    except Exception as e:
        print(f"\n❌ 服务器启动失败: {e}")
