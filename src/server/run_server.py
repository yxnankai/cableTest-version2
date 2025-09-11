#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
启动脚本 - Flask服务端
"""

import os
import sys
import logging
from core.config import get_config

def setup_logging(config):
    """设置日志配置"""
    logging.basicConfig(
        level=getattr(logging, config.LOG_LEVEL),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(config.LOG_FILE),
            logging.StreamHandler(sys.stdout)
        ]
    )

def main():
    """主函数"""
    # 获取环境配置
    env = os.getenv('FLASK_ENV', 'development')
    config = get_config(env)
    
    print(f"=== 线缆测试系统Flask服务端 ===")
    print(f"环境: {env}")
    print(f"配置: {config.get_flask_config()}")
    print(f"测试系统: {config.get_test_system_config()}")
    
    # 设置日志
    setup_logging(config)
    logger = logging.getLogger(__name__)
    
    try:
        # 导入并启动Flask应用
        from flask_server import app, server
        
        # 更新服务端配置
        server.test_system.total_points = config.TOTAL_POINTS
        server.test_system.relay_switch_time = config.RELAY_SWITCH_TIME
        
        logger.info(f"启动Flask测试服务端...")
        logger.info(f"系统配置: {server.test_system.total_points} 个测试点位")
        logger.info(f"继电器切换时间: {server.test_system.relay_switch_time} 秒")
        logger.info(f"服务端启动完成，监听端口 {config.FLASK_PORT}")
        
        # 使用高性能waitress服务器替代Flask开发服务器
        from waitress import serve
        serve(app, host=config.FLASK_HOST, port=config.FLASK_PORT, threads=6)
        
    except ImportError as e:
        logger.error(f"导入模块失败: {e}")
        print(f"错误: 无法导入必要的模块，请确保已安装所有依赖")
        sys.exit(1)
    except Exception as e:
        logger.error(f"启动失败: {e}")
        print(f"错误: 服务端启动失败 - {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
