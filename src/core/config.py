#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
配置文件 - 线缆测试系统Flask接口
"""

import os
from typing import Dict, Any

class Config:
    """基础配置类"""
    
    # Flask服务端配置
    FLASK_HOST = os.getenv('FLASK_HOST', '127.0.0.1')
    FLASK_PORT = int(os.getenv('FLASK_PORT', 5000))
    FLASK_DEBUG = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
    
    # 测试系统配置
    TOTAL_POINTS = int(os.getenv('TOTAL_POINTS', 100))  # 总测试点位数量 (测试版本使用100个点位)
    # 测试加速：默认 0.5ms，可通过环境变量覆盖
    RELAY_SWITCH_TIME = float(os.getenv('RELAY_SWITCH_TIME', 0.0005))  # 继电器切换时间（秒）
    
    # 数据库配置（如果需要持久化）
    DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///cable_test.db')
    
    # 日志配置
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FILE = os.getenv('LOG_FILE', 'cable_test.log')
    
    # 安全配置
    SECRET_KEY = os.getenv('SECRET_KEY', 'your-secret-key-here')
    CORS_ORIGINS = os.getenv('CORS_ORIGINS', '*').split(',')
    
    # 客户端配置
    CLIENT_TIMEOUT = int(os.getenv('CLIENT_TIMEOUT', 30))
    CLIENT_RETRY_COUNT = int(os.getenv('CLIENT_RETRY_COUNT', 3))
    
    # 监控配置
    DEFAULT_MONITOR_INTERVAL = float(os.getenv('DEFAULT_MONITOR_INTERVAL', 1.0))
    DEFAULT_MONITOR_DURATION = float(os.getenv('DEFAULT_MONITOR_DURATION', 60.0))
    
    # API配置
    API_PREFIX = '/api'
    API_VERSION = 'v1'
    
    @classmethod
    def get_flask_config(cls) -> Dict[str, Any]:
        """获取Flask配置"""
        return {
            'host': cls.FLASK_HOST,
            'port': cls.FLASK_PORT,
            'debug': cls.FLASK_DEBUG,
            'secret_key': cls.SECRET_KEY
        }
    
    @classmethod
    def get_test_system_config(cls) -> Dict[str, Any]:
        """获取测试系统配置"""
        return {
            'total_points': cls.TOTAL_POINTS,
            'relay_switch_time': cls.RELAY_SWITCH_TIME
        }
    
    @classmethod
    def get_client_config(cls) -> Dict[str, Any]:
        """获取客户端配置"""
        return {
            'timeout': cls.CLIENT_TIMEOUT,
            'retry_count': cls.CLIENT_RETRY_COUNT,
            'monitor_interval': cls.DEFAULT_MONITOR_INTERVAL,
            'monitor_duration': cls.DEFAULT_MONITOR_DURATION
        }

class DevelopmentConfig(Config):
    """开发环境配置"""
    FLASK_DEBUG = False
    LOG_LEVEL = 'DEBUG'
    TOTAL_POINTS = 1000  # 开发环境使用较少的点位

class ProductionConfig(Config):
    """生产环境配置"""
    FLASK_DEBUG = False
    LOG_LEVEL = 'WARNING'
    CORS_ORIGINS = ['http://localhost:3000', 'https://yourdomain.com']

class TestingConfig(Config):
    """测试环境配置"""
    FLASK_DEBUG = False
    LOG_LEVEL = 'DEBUG'
    TOTAL_POINTS = 100
    DATABASE_URL = 'sqlite:///test.db'

# 配置映射
config_map = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig
}

def get_config(env: str = None) -> Config:
    """获取配置实例"""
    if env is None:
        env = os.getenv('FLASK_ENV', 'development')
    
    return config_map.get(env, DevelopmentConfig)
