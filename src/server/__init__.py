"""
服务器模块

包含Flask服务器和Web服务器的实现
"""

from .flask_server import app, FlaskTestServer
from .flask_server_web import app as web_app
# from .flask_server_web import socketio  # 暂时禁用WebSocket

__all__ = ['app', 'web_app', 'FlaskTestServer']
