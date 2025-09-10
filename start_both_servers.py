#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
同时启动主服务器和测试端服务器
"""

import subprocess
import sys
import time
import threading
import os

def start_main_server():
    """启动主服务器"""
    print("🚀 启动主服务器...")
    try:
        subprocess.run([sys.executable, "run_web_server.py"], check=True)
    except subprocess.CalledProcessError as e:
        print(f"❌ 主服务器启动失败: {e}")
    except KeyboardInterrupt:
        print("⚠️  主服务器已停止")

def start_test_server():
    """启动测试端服务器"""
    print("🚀 启动测试端服务器...")
    try:
        os.chdir("testFlaskClient")
        subprocess.run([sys.executable, "start_test_server.py"], check=True)
    except subprocess.CalledProcessError as e:
        print(f"❌ 测试端服务器启动失败: {e}")
    except KeyboardInterrupt:
        print("⚠️  测试端服务器已停止")

def main():
    print("=" * 60)
    print("🔬 电缆测试系统 - 双服务器启动")
    print("=" * 60)
    print("主服务器: http://localhost:5000")
    print("测试端配置界面: http://localhost:5001")
    print("=" * 60)
    print("按 Ctrl+C 停止所有服务器")
    print("=" * 60)
    
    try:
        # 启动主服务器（在后台线程中）
        main_thread = threading.Thread(target=start_main_server)
        main_thread.daemon = True
        main_thread.start()
        
        # 等待主服务器启动
        print("⏳ 等待主服务器启动...")
        time.sleep(3)
        
        # 启动测试端服务器（主线程）
        start_test_server()
        
    except KeyboardInterrupt:
        print("\n⚠️  正在停止所有服务器...")
        print("✅ 所有服务器已停止")

if __name__ == "__main__":
    main()
