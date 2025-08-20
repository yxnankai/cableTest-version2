#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Flask服务端 - 线缆测试系统双向测试接口
提供继电器状态查询、集群信息查询和实验执行功能
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import json
import time
import logging
from typing import Dict, List, Any
from core.cable_test_system import CableTestSystem, TestResult, RelayState

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)  # 允许跨域请求

class FlaskTestServer:
    """Flask测试服务端"""
    
    def __init__(self, total_points: int = 100):
        self.test_system = CableTestSystem(total_points=total_points)
        self.current_point_states = {}  # 当前点位状态缓存
        self.confirmed_clusters = []    # 兼容保留：不再使用
        self._update_current_states()
    
    def _update_current_states(self):
        """更新当前点位状态"""
        for point_id, point in self.test_system.test_points.items():
            self.current_point_states[point_id] = {
                'point_id': point_id,
                'relay_state': point.relay_state.value,
                'voltage': point.voltage,
                'current': point.current,
                'is_connected': point.is_connected
            }
    
    def _update_clusters_from_test(self, test_result: TestResult):
        """根据测试结果更新集群信息"""
        # 更新点位状态
        for point_id in test_result.active_points:
            if point_id in self.test_system.test_points:
                point = self.test_system.test_points[point_id]
                self.current_point_states[point_id] = {
                    'point_id': point_id,
                    'relay_state': point.relay_state.value,
                    'voltage': point.voltage,
                    'current': point.current,
                    'is_connected': point.is_connected
                }
        
        # 更新集群信息
        for connection in test_result.detected_connections:
            cluster_info = {
                'cluster_id': f"cluster_{len(self.confirmed_clusters) + 1}",
                'power_source': connection.source_point,
                'connected_points': connection.target_points,
                'connection_type': connection.connection_type,
                'discovered_at': time.time(),
                'test_id': test_result.test_id
            }
            self.confirmed_clusters.append(cluster_info)
    
    def get_point_status(self, point_id: int = None) -> Dict[str, Any]:
        """获取点位状态"""
        if point_id is not None:
            if point_id in self.current_point_states:
                return {
                    'success': True,
                    'data': self.current_point_states[point_id]
                }
            else:
                return {
                    'success': False,
                    'error': f'点位 {point_id} 不存在'
                }
        else:
            return {
                'success': True,
                'data': list(self.current_point_states.values())
            }
    
    def get_cluster_info(self) -> Dict[str, Any]:
        """获取集群信息（兼容保留）"""
        return {
            'success': True,
            'data': {
                'total_clusters': 0,
                'clusters': []
            }
        }
    
    def get_unconfirmed_cluster_relationships(self) -> Dict[str, Any]:
        """兼容保留：返回点-点未确认对及建议。"""
        try:
            unconfirmed_info = self.test_system.get_unconfirmed_cluster_relationships()
            return {
                'success': True,
                'data': unconfirmed_info
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def run_experiment(self, experiment_config: Dict[str, Any]) -> Dict[str, Any]:
        """运行实验"""
        try:
            power_source = experiment_config.get('power_source')
            test_points = experiment_config.get('test_points', [])
            
            if power_source is None:
                return {
                    'success': False,
                    'error': '缺少电源点位参数'
                }
            
            # 运行测试
            test_result = self.test_system.run_single_test(
                power_source=power_source,
                test_points=test_points
            )
            
            # 更新状态
            self._update_clusters_from_test(test_result)
            
            # 返回测试结果
            return {
                'success': True,
                'data': {
                    'test_id': test_result.test_id,
                    'timestamp': test_result.timestamp,
                    'power_source': test_result.power_source,
                    'active_points': test_result.active_points,
                    'detected_connections': [
                        {
                            'source_point': conn.source_point,
                            'target_points': conn.target_points,
                            'connection_type': conn.connection_type
                        }
                        for conn in test_result.detected_connections
                    ],
                    'test_duration': test_result.test_duration,
                    'relay_operations': test_result.relay_operations,
                    'power_on_operations': getattr(test_result, 'power_on_operations', 0),
                    'total_points': test_result.total_points
                }
            }
            
        except Exception as e:
            logger.error(f"实验执行失败: {str(e)}")
            return {
                'success': False,
                'error': f'实验执行失败: {str(e)}'
            }

# 创建服务端实例
server = FlaskTestServer()

@app.route('/api/health', methods=['GET'])
def health_check():
    """健康检查接口"""
    return jsonify({
        'status': 'healthy',
        'timestamp': time.time(),
        'total_points': server.test_system.total_points
    })

@app.route('/api/points/status', methods=['GET'])
def get_points_status():
    """获取点位状态"""
    point_id = request.args.get('point_id', type=int)
    result = server.get_point_status(point_id)
    return jsonify(result)

@app.route('/api/clusters', methods=['GET'])
def get_clusters():
    """获取集群信息"""
    result = server.get_cluster_info()
    return jsonify(result)

@app.route('/api/clusters/unconfirmed_relationships', methods=['GET'])
def get_unconfirmed_cluster_relationships():
    """获取未确认集群关系信息"""
    result = server.get_unconfirmed_cluster_relationships()
    return jsonify(result)

@app.route('/api/experiment', methods=['POST'])
def run_experiment():
    """运行实验"""
    try:
        experiment_config = request.get_json()
        if not experiment_config:
            return jsonify({
                'success': False,
                'error': '缺少实验配置参数'
            })
        
        result = server.run_experiment(experiment_config)
        return jsonify(result)
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'请求处理失败: {str(e)}'
        })

@app.route('/api/system/info', methods=['GET'])
def get_system_info():
    """获取系统信息"""
    try:
        total_power_on_ops = sum(getattr(tr, 'power_on_operations', 0) for tr in server.test_system.test_history)
    except Exception:
        total_power_on_ops = 0
    return jsonify({
        'success': True,
        'data': {
            'total_points': server.test_system.total_points,
            'relay_switch_time': server.test_system.relay_switch_time,
            'total_connections': len(server.test_system.true_pairs),
            'total_tests': len(server.test_system.test_history),
            'total_relay_operations': server.test_system.relay_operation_count,
            'total_power_on_operations': total_power_on_ops,
            'current_point_states_count': len(server.current_point_states),
            'confirmed_clusters_count': 0
        }
    })

@app.route('/api/experiment/batch', methods=['POST'])
def run_batch_experiments():
    """运行批量实验"""
    try:
        batch_config = request.get_json()
        if not batch_config:
            return jsonify({
                'success': False,
                'error': '缺少批量实验配置参数'
            })
        
        test_count = batch_config.get('test_count', 5)
        max_points_per_test = batch_config.get('max_points_per_test', 100)
        
        # 生成随机测试配置
        test_configs = server.test_system.generate_random_test_configs(
            test_count=test_count,
            max_points_per_test=max_points_per_test
        )
        
        # 运行批量测试
        test_results = server.test_system.run_batch_tests(test_configs)
        
        # 更新状态和集群信息
        for test_result in test_results:
            server._update_clusters_from_test(test_result)
        
        return jsonify({
            'success': True,
            'data': {
                'total_tests': len(test_results),
                'test_results': [
                    {
                        'test_id': result.test_id,
                        'power_source': result.power_source,
                        'active_points': result.active_points,
                        'detected_connections': len(result.detected_connections),
                        'test_duration': result.test_duration,
                        'relay_operations': result.relay_operations
                    }
                    for result in test_results
                ]
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'批量实验执行失败: {str(e)}'
        })

if __name__ == '__main__':
    logger.info("启动Flask测试服务端...")
    logger.info(f"系统配置: {server.test_system.total_points} 个测试点位")
    logger.info("服务端启动完成，监听端口 5000")
    
    app.run(host='0.0.0.0', port=5000, debug=False)
