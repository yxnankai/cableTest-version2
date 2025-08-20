"""
客户端模块

包含Flask客户端和命令行工具
"""

from .flask_client import FlaskTestClient, ExperimentConfig

# 兼容保留别名
FlaskClient = FlaskTestClient

__all__ = ['FlaskTestClient', 'ExperimentConfig', 'FlaskClient']
