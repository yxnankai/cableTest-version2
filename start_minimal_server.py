#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
最简化的线缆测试系统Web服务器启动脚本
完全避免SSL和WebSocket问题
"""

import os
import sys
import logging

# 添加src目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# 修复Windows SSL证书问题
os.environ['PYTHONHTTPSVERIFY'] = '0'
os.environ['SSL_CERT_FILE'] = ''
os.environ['SSL_CERT_DIR'] = ''

# 禁用SSL警告
import warnings
warnings.filterwarnings('ignore', category=DeprecationWarning)
warnings.filterwarnings('ignore', category=UserWarning)

def main():
    """主函数"""
    # 设置环境变量
    env = os.getenv('FLASK_ENV', 'testing')
    
    # 配置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(os.path.join('logs', 'web_server.log'), encoding='utf-8')
        ]
    )
    
    logger = logging.getLogger(__name__)
    logger.info(f"🚀 启动线缆测试系统Web服务器 (环境: {env})")
    logger.info(f"📁 工作目录: {os.getcwd()}")
    
    # 启动Flask服务器
    try:
        # 直接导入Flask应用，避免WebSocket
        from server.flask_server_web import app
        
        logger.info(f"📱 前端界面: http://localhost:5000")
        logger.info(f"🔌 API接口: http://localhost:5000/api/")
        
        # 使用简单的Flask开发服务器
        app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False)
        
    except Exception as e:
        logger.error(f"启动服务器失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()
