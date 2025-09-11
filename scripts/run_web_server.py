#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
线缆测试系统Web服务器启动脚本
提供前端界面和WebSocket实时更新功能
"""

import os
import sys
import logging
# 添加src目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from core.config import get_config

def setup_logging(config):
    """设置日志配置"""
    logging.basicConfig(
        level=getattr(logging, config.LOG_LEVEL.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(os.path.join('..', 'logs', 'web_server.log'), encoding='utf-8')
        ]
    )

def main():
    """主函数"""
    # 设置环境变量
    env = os.getenv('FLASK_ENV', 'testing')  # 默认使用测试环境（100个点位）
    
    # 获取配置
    test_config = get_config(env)
    
    # 配置日志
    logging.basicConfig(
        level=getattr(logging, test_config.LOG_LEVEL),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(test_config.LOG_FILE, encoding='utf-8')
        ]
    )
    
    logger = logging.getLogger(__name__)
    logger.info(f"🚀 启动线缆测试系统Web服务器 (环境: {env})")
    logger.info(f"📁 工作目录: {os.getcwd()}")
    
    logger.info(f"🔌 系统配置: {test_config.TOTAL_POINTS}个点位, 继电器切换时间: {test_config.RELAY_SWITCH_TIME * 1000:.1f}ms")
    logger.info(f"📱 前端界面: http://0.0.0.0:5000")
    logger.info(f"🔌 API接口: http://0.0.0.0:5000/api/")
    logger.info(f"📡 WebSocket: ws://0.0.0.0:5000/socket.io/")
    
    # 启动Flask服务器
    from server.flask_server_web import app
    # from server.flask_server_web import socketio  # 暂时禁用WebSocket
    
    logger.info(f"🚀 启动线缆测试系统Web服务器...")
    logger.info(f"📱 前端界面: http://localhost:5000")
    logger.info(f"🔌 API接口: http://localhost:5000/api/")
    # logger.info(f"📡 WebSocket: ws://localhost:5000/socket.io/")  # 暂时禁用WebSocket
    
    # 使用高性能waitress服务器替代Flask开发服务器
    from waitress import serve
    serve(app, host='127.0.0.1', port=5000, threads=6)

if __name__ == '__main__':
    main()
