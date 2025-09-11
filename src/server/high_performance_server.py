#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
高性能Flask服务器 - 优化版
主要优化：
1. 使用缓存机制
2. 优化响应处理
3. 减少不必要的计算
4. 使用异步处理
"""

from flask import Flask, request, jsonify, render_template_string
from flask_cors import CORS
import json
import time
import logging
import sys
import os
from typing import Dict, Any, List

# 添加优化模块
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from core.optimized_cable_test_system import OptimizedCableTestSystem
from utils.response_optimizer import optimized_response, api_cache, get_performance_stats, clear_api_cache
from utils.performance_timer import get_timer, time_step, print_performance_report
from core import config

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['SECRET_KEY'] = 'cable_test_secret_key'
CORS(app)

class HighPerformanceWebServer:
    """高性能Web服务器"""
    
    def __init__(self, total_points: int = None):
        # 使用配置文件中的点位数量
        if total_points is None:
            test_config = config.get_config('testing')
            total_points = test_config.TOTAL_POINTS
        
        # 使用优化版测试系统
        self.test_system = OptimizedCableTestSystem(total_points=total_points)
        self.current_point_states = {}
        self.confirmed_clusters = []
        self.test_history = []
        self.active_experiments = {}
        
        # 性能统计
        self.request_count = 0
        self.start_time = time.time()
        
        # 初始化状态
        self._update_current_states()
        self.confirmed_clusters = self.test_system.get_confirmed_clusters()
        
        logger.info(f"高性能服务器初始化完成，总点位: {total_points}")
    
    def _update_current_states(self):
        """更新当前点位状态（优化版）"""
        # 批量更新状态
        for point_id, point in self.test_system.test_points.items():
            self.current_point_states[point_id] = {
                'point_id': point_id,
                'relay_state': point.relay_state.value,
                'voltage': point.voltage,
                'current': point.current,
                'is_connected': point.is_connected
            }
    
    @api_cache(ttl=30)  # 缓存30秒
    def get_system_info(self) -> Dict[str, Any]:
        """获取系统信息（优化版）"""
        timer = get_timer()
        
        with timer.time_step("get_system_info", {"endpoint": "/api/system/info"}):
            info = self.test_system.get_system_info_optimized()
            info.update({
                'server_uptime': time.time() - self.start_time,
                'request_count': self.request_count,
                'performance_stats': get_performance_stats()
            })
            return info
    
    @api_cache(ttl=10)  # 缓存10秒
    def get_point_status(self, point_id: int) -> Dict[str, Any]:
        """获取点位状态（优化版）"""
        timer = get_timer()
        
        with timer.time_step("get_point_status", {"endpoint": "/api/points/status", "point_id": point_id}):
            if point_id not in self.test_system.test_points:
                return {'success': False, 'error': f'点位 {point_id} 不存在'}
            
            point = self.test_system.test_points[point_id]
            return {
                'success': True,
                'data': {
                    'point_id': point_id,
                    'relay_state': point.relay_state.value,
                    'voltage': point.voltage,
                    'current': point.current,
                    'is_connected': point.is_connected,
                    'last_update': point._last_update
                }
            }
    
    @api_cache(ttl=60)  # 缓存60秒
    def get_cluster_info(self) -> Dict[str, Any]:
        """获取集群信息（优化版）"""
        timer = get_timer()
        
        with timer.time_step("get_cluster_info", {"endpoint": "/api/clusters"}):
            # 使用优化版连接矩阵
            matrix = self.test_system.get_connection_matrix()
            
            clusters = []
            for source, targets in matrix.items():
                if targets:  # 只包含有连接的源点
                    clusters.append({
                        'source': source,
                        'targets': list(targets),
                        'connection_count': len(targets)
                    })
            
            return {
                'success': True,
                'data': {
                    'clusters': clusters,
                    'total_clusters': len(clusters),
                    'total_connections': sum(len(targets) for targets in matrix.values())
                }
            }
    
    def run_experiment(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """运行实验（优化版）"""
        timer = get_timer()
        
        with timer.time_step("run_experiment", {"endpoint": "/api/experiment"}):
            try:
                power_source = data.get('power_source', 0)
                test_points = data.get('test_points', [])
                
                if not test_points:
                    return {'success': False, 'error': '测试点位列表不能为空'}
                
                # 使用优化版测试
                result = self.test_system.run_single_test_optimized(power_source, test_points)
                
                # 更新状态
                self._update_current_states()
                
                return {
                    'success': result.success,
                    'data': {
                        'test_id': result.test_id,
                        'power_source': result.power_source,
                        'test_points': result.test_points,
                        'results': result.results,
                        'duration': result.duration,
                        'timestamp': result.timestamp
                    },
                    'error': result.error_message
                }
                
            except Exception as e:
                logger.error(f"实验执行失败: {e}")
                return {'success': False, 'error': str(e)}
    
    def get_test_progress(self) -> Dict[str, Any]:
        """获取测试进度（优化版）"""
        timer = get_timer()
        
        with timer.time_step("get_test_progress", {"endpoint": "/api/test/progress"}):
            # 使用优化版历史记录
            recent_tests = self.test_system.test_history[-10:]  # 最近10次测试
            
            progress_data = []
            for test in recent_tests:
                progress_data.append({
                    'test_id': test.test_id,
                    'power_source': test.power_source,
                    'test_points': test.test_points,
                    'success': test.success,
                    'duration': test.duration,
                    'timestamp': test.timestamp
                })
            
            return {
                'success': True,
                'data': {
                    'recent_tests': progress_data,
                    'total_tests': len(self.test_system.test_history),
                    'success_rate': sum(1 for t in self.test_system.test_history if t.success) / max(len(self.test_system.test_history), 1)
                }
            }
    
    def reset_system(self, data: Dict[str, Any] = None) -> Dict[str, Any]:
        """重置系统（优化版）"""
        timer = get_timer()
        
        with timer.time_step("reset_system", {"endpoint": "/api/system/reset"}):
            try:
                total_points = data.get('total_points') if data else None
                conductivity_distribution = data.get('conductivity_distribution') if data else None
                
                # 使用优化版重置
                self.test_system.reset_system_optimized(total_points, conductivity_distribution)
                
                # 清空API缓存
                clear_api_cache()
                
                # 更新状态
                self._update_current_states()
                self.confirmed_clusters = self.test_system.get_confirmed_clusters()
                
                return {
                    'success': True,
                    'message': '系统重置成功',
                    'data': {
                        'total_points': self.test_system.total_points,
                        'timestamp': time.time()
                    }
                }
                
            except Exception as e:
                logger.error(f"系统重置失败: {e}")
                return {'success': False, 'error': str(e)}

# 创建服务器实例（延迟初始化）
server = None

def get_server():
    """获取服务器实例（单例模式）"""
    global server
    if server is None:
        server = HighPerformanceWebServer()
    return server

# ============== API路由 ==============

@app.route('/api/health')
def health_check():
    """健康检查接口"""
    return optimized_response({
        'status': 'healthy',
        'timestamp': time.time(),
        'service': 'High Performance Cable Test System',
        'version': '2.0.0'
    })

@app.route('/api/system/info')
def get_system_info():
    """获取系统信息"""
    timer = get_timer()
    
    with timer.time_step("api_get_system_info", {"endpoint": "/api/system/info"}):
        result = get_server().get_system_info()
        return optimized_response(result)

@app.route('/api/points/status')
def get_point_status():
    """获取点位状态"""
    timer = get_timer()
    point_id = request.args.get('point_id', type=int)
    
    with timer.time_step("api_get_point_status", {"endpoint": "/api/points/status", "point_id": point_id}):
        result = get_server().get_point_status(point_id)
        return optimized_response(result)

@app.route('/api/clusters')
def get_cluster_info():
    """获取集群信息"""
    timer = get_timer()
    
    with timer.time_step("api_get_cluster_info", {"endpoint": "/api/clusters"}):
        result = get_server().get_cluster_info()
        return optimized_response(result)

@app.route('/api/experiment', methods=['POST'])
def run_experiment():
    """运行实验"""
    timer = get_timer()
    
    with timer.time_step("api_run_experiment", {"endpoint": "/api/experiment"}):
        try:
            data = request.get_json()
            if not data:
                return optimized_response({'success': False, 'error': '无效的请求数据'}, 400)
            
            result = get_server().run_experiment(data)
            return optimized_response(result)
        except Exception as e:
            return optimized_response({'success': False, 'error': str(e)}, 500)

@app.route('/api/test/progress')
def get_test_progress():
    """获取测试进度"""
    timer = get_timer()
    
    with timer.time_step("api_get_test_progress", {"endpoint": "/api/test/progress"}):
        result = get_server().get_test_progress()
        return optimized_response(result)

@app.route('/api/system/reset', methods=['POST'])
def reset_system():
    """重置系统"""
    timer = get_timer()
    
    with timer.time_step("api_reset_system", {"endpoint": "/api/system/reset"}):
        try:
            data = request.get_json(silent=True) or {}
            result = get_server().reset_system(data)
            return optimized_response(result)
        except Exception as e:
            return optimized_response({'success': False, 'error': str(e)}, 500)

@app.route('/api/performance/stats')
def get_performance_stats():
    """获取性能统计"""
    timer = get_timer()
    
    with timer.time_step("api_get_performance_stats", {"endpoint": "/api/performance/stats"}):
        stats = {
            'server_stats': get_performance_stats(),
            'system_stats': get_server().test_system.get_performance_stats(),
            'request_count': get_server().request_count,
            'uptime': time.time() - get_server().start_time
        }
        return optimized_response({'success': True, 'data': stats})

@app.route('/api/performance/report')
def get_performance_report():
    """获取性能报告"""
    timer = get_timer()
    
    with timer.time_step("api_get_performance_report", {"endpoint": "/api/performance/report"}):
        report = print_performance_report()
        return optimized_response({'success': True, 'data': report})

# ============== 主程序 ==============

if __name__ == '__main__':
    logger.info("🚀 启动高性能线缆测试系统Web服务器...")
    logger.info("📱 前端界面: http://localhost:5000")
    logger.info("🔌 API接口: http://localhost:5000/api/")
    
    # 使用高性能waitress服务器
    from waitress import serve
    serve(app, host='127.0.0.1', port=5000, threads=8)  # 增加线程数
