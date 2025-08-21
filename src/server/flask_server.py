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
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
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

    def get_relay_stats(self) -> Dict[str, Any]:
        """获取继电器操作统计信息"""
        try:
            relay_stats = self.test_system.get_relay_operation_stats()
            return {
                'success': True,
                'data': {
                    'relay_stats': relay_stats,
                    'timestamp': time.time()
                }
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def reset_relay_states(self) -> Dict[str, Any]:
        """重置所有继电器状态"""
        try:
            operations = self.test_system.reset_relay_states()
            return {
                'success': True,
                'data': {
                    'reset_operations': operations,
                    'message': f'重置完成，关闭了 {operations} 个点位',
                    'timestamp': time.time()
                }
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}

# 创建服务端实例
server = FlaskTestServer()

@app.route('/', methods=['GET'])
def index():
    """根路径 - 显示完整的系统仪表板"""
    try:
        # 获取系统信息
        total_power_on_ops = sum(getattr(tr, 'power_on_operations', 0) for tr in server.test_system.test_history)
    except Exception:
        total_power_on_ops = 0
    
    confirmed_points_count = server.test_system.get_confirmed_points_count()
    
    # 获取测试历史
    test_history = server.test_system.test_history[-10:] if server.test_system.test_history else []  # 最近10次测试
    
    html_content = f"""
    <!DOCTYPE html>
    <html lang="zh-CN">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>线缆测试系统 - 仪表板</title>
        <style>
            body {{
                font-family: 'Microsoft YaHei', Arial, sans-serif;
                margin: 0;
                padding: 20px;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                min-height: 100vh;
            }}
            .container {{
                max-width: 1400px;
                margin: 0 auto;
            }}
            .header {{
                text-align: center;
                margin-bottom: 30px;
            }}
            h1 {{
                color: #fff;
                text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.5);
                margin-bottom: 10px;
            }}
            .dashboard-grid {{
                display: grid;
                grid-template-columns: 1fr 1fr;
                gap: 20px;
                margin-bottom: 30px;
            }}
            .section {{
                background: rgba(255, 255, 255, 0.1);
                border-radius: 15px;
                padding: 25px;
                backdrop-filter: blur(10px);
                box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
                border: 1px solid rgba(255, 255, 255, 0.3);
            }}
            .section-title {{
                font-size: 1.3em;
                margin-bottom: 20px;
                color: #ffd700;
                text-align: center;
                font-weight: bold;
            }}
            .status-grid {{
                display: grid;
                grid-template-columns: repeat(2, 1fr);
                gap: 15px;
            }}
            .status-item {{
                background: rgba(255, 255, 255, 0.15);
                border-radius: 8px;
                padding: 15px;
                text-align: center;
            }}
            .status-value {{
                font-size: 1.8em;
                font-weight: bold;
                color: #ffd700;
                margin-bottom: 5px;
            }}
            .status-label {{
                font-size: 0.9em;
                opacity: 0.9;
            }}
            .button-group {{
                display: flex;
                flex-wrap: wrap;
                gap: 10px;
                justify-content: center;
                margin-top: 20px;
            }}
            .btn {{
                padding: 8px 16px;
                border: none;
                border-radius: 20px;
                cursor: pointer;
                font-size: 0.9em;
                transition: all 0.2s;
                color: white;
            }}
            .btn-primary {{ background: #007bff; }}
            .btn-success {{ background: #28a745; }}
            .btn-info {{ background: #17a2b8; }}
            .btn-warning {{ background: #ffc107; color: #000; }}
            .btn:hover {{ transform: translateY(-2px); box-shadow: 0 4px 8px rgba(0,0,0,0.3); }}
            .points-grid {{
                display: grid;
                grid-template-columns: repeat(10, 1fr);
                gap: 2px;
                margin-top: 20px;
                max-height: 300px;
                overflow-y: auto;
            }}
            .point-item {{
                aspect-ratio: 1;
                display: flex;
                align-items: center;
                justify-content: center;
                font-size: 0.7em;
                font-weight: bold;
                border-radius: 4px;
                cursor: pointer;
                transition: all 0.2s;
            }}
            .point-closed {{ background: #dc3545; color: white; }}
            .point-open {{ background: #28a745; color: white; }}
            .point-conductive {{ background: #17a2b8; color: white; }}
            .point-item:hover {{ transform: scale(1.1); }}
            .legend {{
                display: flex;
                justify-content: center;
                gap: 20px;
                margin-top: 15px;
                font-size: 0.8em;
            }}
            .legend-item {{
                display: flex;
                align-items: center;
                gap: 5px;
            }}
            .legend-color {{
                width: 16px;
                height: 16px;
                border-radius: 3px;
            }}
            .test-history {{
                max-height: 300px;
                overflow-y: auto;
            }}
            .test-item {{
                background: rgba(255, 255, 255, 0.1);
                border-radius: 8px;
                padding: 15px;
                margin-bottom: 10px;
                border-left: 4px solid #ffd700;
            }}
            .test-header {{
                display: flex;
                justify-content: space-between;
                margin-bottom: 10px;
                font-weight: bold;
            }}
            .test-details {{
                font-size: 0.9em;
                opacity: 0.9;
            }}
            .refresh-controls {{
                text-align: center;
                margin: 20px 0;
            }}
            .auto-refresh {{
                background: linear-gradient(45deg, #ff6b6b, #ee5a24);
                color: white;
                border: none;
                padding: 12px 24px;
                border-radius: 25px;
                cursor: pointer;
                font-size: 1em;
                margin: 0 10px;
                transition: transform 0.2s;
            }}
            .auto-refresh:hover {{ transform: scale(1.05); }}
            .timestamp {{
                text-align: center;
                opacity: 0.7;
                font-size: 0.9em;
                margin-top: 20px;
            }}
            .loading {{
                text-align: center;
                padding: 20px;
                font-style: italic;
                opacity: 0.7;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🔌 线缆测试系统仪表板</h1>
                <p>实时监控系统状态、点位关系和测试历史</p>
            </div>
            
            <div class="dashboard-grid">
                <!-- 左侧：系统状态和点对关系信息 -->
                <div class="section">
                    <div class="section-title">📊 系统状态</div>
                    <div class="status-grid">
                        <div class="status-item">
                            <div class="status-value">{server.test_system.total_points}</div>
                            <div class="status-label">总点位</div>
                        </div>
                        <div class="status-item">
                            <div class="status-value">{server.test_system.relay_switch_time}ms</div>
                            <div class="status-label">继电器切换时间</div>
                        </div>
                        <div class="status-item">
                            <div class="status-value">0</div>
                            <div class="status-label">已确认连接组</div>
                        </div>
                        <div class="status-item">
                            <div class="status-value">{len(server.test_system.test_history)}</div>
                            <div class="status-label">总测试次数</div>
                        </div>
                        <div class="status-item">
                            <div class="status-value">{server.test_system.relay_operation_count}</div>
                            <div class="status-label">继电器操作总次数</div>
                        </div>
                        <div class="status-item">
                            <div class="status-value">{total_power_on_ops}</div>
                            <div class="status-label">通电次数总和</div>
                        </div>
                    </div>
                    <div style="text-align: center; margin-top: 15px; padding: 10px; background: rgba(40, 167, 69, 0.3); border-radius: 8px;">
                        <strong>系统状态: 运行中</strong>
                    </div>
                </div>
                
                <!-- 右侧：点对关系信息 -->
                <div class="section">
                    <div class="section-title">🔗 点对关系信息</div>
                    <div style="text-align: center; margin: 20px 0; padding: 20px; background: rgba(255, 255, 255, 0.1); border-radius: 8px;">
                        暂无点对关系信息
                    </div>
                    <div class="button-group">
                        <button class="btn btn-primary" onclick="showDetailedInfo()">详细点对信息</button>
                        <button class="btn btn-success" onclick="showConfirmedNonConductive()">已确认不导通</button>
                        <button class="btn btn-info" onclick="showDetectedMatrix()">检测到的关系矩阵</button>
                        <button class="btn btn-warning" onclick="showTrueMatrix()">真实关系矩阵</button>
                        <button class="btn btn-info" onclick="showMatrixComparison()">矩阵对比</button>
                        <button class="btn btn-warning" onclick="showTrueConductive()">真实导通点位信息</button>
                    </div>
                </div>
            </div>
            
            <!-- 点位状态概览 -->
            <div class="section">
                <div class="section-title">📍 点位状态概览</div>
                <div class="status-grid">
                    <div class="status-item">
                        <div class="status-value">{server.test_system.total_points}</div>
                        <div class="status-label">总点位</div>
                    </div>
                    <div class="status-item">
                        <div class="status-value">0</div>
                        <div class="status-label">开启</div>
                    </div>
                    <div class="status-item">
                        <div class="status-value">{server.test_system.total_points}</div>
                        <div class="status-label">关闭</div>
                    </div>
                    <div class="status-item">
                        <div class="status-value">0个</div>
                        <div class="status-label">已确认连接组</div>
                    </div>
                    <div class="status-item">
                        <div class="status-value">{confirmed_points_count}个</div>
                        <div class="status-label">已确认点位</div>
                    </div>
                    <div class="status-item">
                        <div class="status-value">{server.test_system.total_points - confirmed_points_count}个</div>
                        <div class="status-label">未确认点位</div>
                    </div>
                </div>
                
                <div class="points-grid" id="pointsGrid">
                    {''.join([f'<div class="point-item point-closed" title="点位 {i}">{i}</div>' for i in range(server.test_system.total_points)])}
                </div>
                
                <div class="legend">
                    <div class="legend-item">
                        <div class="legend-color" style="background: #28a745;"></div>
                        <span>有导通能力</span>
                    </div>
                    <div class="legend-item">
                        <div class="legend-color" style="background: #6c757d;"></div>
                        <span>无导通能力</span>
                    </div>
                    <div class="legend-item">
                        <div class="legend-color" style="background: #dc3545;"></div>
                        <span>关闭状态</span>
                    </div>
                </div>
                <div style="text-align: center; margin-top: 10px; font-size: 0.8em; opacity: 0.8;">
                    注意: 关系是非对称的,点位A能导通点位B不代表点位B能导通点位A
                </div>
            </div>
            
            <!-- 测试历史 -->
            <div class="section">
                <div class="section-title">📋 测试历史</div>
                <div class="test-history" id="testHistory">
                    {''.join([f'''
                    <div class="test-item">
                        <div class="test-header">
                            <span>测试 #{test.test_id}</span>
                            <span>{time.strftime('%H:%M:%S', time.localtime(test.timestamp))}</span>
                        </div>
                        <div class="test-details">
                            电源点位: {test.power_source} | 测试点位: {', '.join(map(str, test.active_points))} | 
                            继电器操作: {test.relay_operations}次 | 检测到连接: {len(test.detected_connections)}个
                        </div>
                    </div>
                    ''' for test in test_history]) if test_history else '<div class="loading">暂无测试历史</div>'}
                </div>
            </div>
            
            <!-- 刷新控制 -->
            <div class="refresh-controls">
                <button class="auto-refresh" onclick="refreshData()">🔄 刷新数据</button>
                <button class="auto-refresh" onclick="toggleAutoRefresh()" id="autoRefreshBtn">⏸️ 暂停自动刷新</button>
                <button class="auto-refresh" onclick="location.reload()">🔄 刷新页面</button>
            </div>
            
            <div class="timestamp">
                最后更新时间: {time.strftime('%Y-%m-%d %H:%M:%S')}
            </div>
        </div>
        
        <script>
            let autoRefreshInterval;
            let isAutoRefreshEnabled = true;
            
            // 初始化自动刷新
            function initAutoRefresh() {{
                if (isAutoRefreshEnabled) {{
                    autoRefreshInterval = setInterval(refreshData, 5000); // 每5秒刷新
                }}
            }}
            
            // 切换自动刷新
            function toggleAutoRefresh() {{
                if (isAutoRefreshEnabled) {{
                    clearInterval(autoRefreshInterval);
                    isAutoRefreshEnabled = false;
                    document.getElementById('autoRefreshBtn').textContent = '▶️ 启动自动刷新';
                }} else {{
                    isAutoRefreshEnabled = true;
                    document.getElementById('autoRefreshBtn').textContent = '⏸️ 暂停自动刷新';
                    initAutoRefresh();
                }}
            }}
            
            // 刷新数据
            async function refreshData() {{
                try {{
                    // 刷新系统信息
                    const systemResponse = await fetch('/api/system/info');
                    const systemData = await systemResponse.json();
                    
                    if (systemData.success) {{
                        updateSystemStatus(systemData.data);
                    }}
                    
                    // 刷新测试历史
                    await updateTestHistory();
                    
                    // 更新时间戳
                    document.querySelector('.timestamp').textContent = '最后更新时间: ' + new Date().toLocaleString('zh-CN');
                    
                }} catch (error) {{
                    console.error('刷新数据失败:', error);
                }}
            }}
            
            // 更新系统状态
            function updateSystemStatus(data) {{
                console.log('开始更新系统状态:', data);
                
                // 更新系统状态数值
                const statusItems = document.querySelectorAll('.status-item');
                let updatedCount = 0;
                
                statusItems.forEach(item => {{
                    const label = item.querySelector('.status-label').textContent;
                    const valueElement = item.querySelector('.status-value');
                    
                    if (label === '总测试次数') {{
                        valueElement.textContent = data.total_tests;
                        updatedCount++;
                        console.log('更新总测试次数:', data.total_tests);
                    }} else if (label === '继电器操作总次数') {{
                        valueElement.textContent = data.total_relay_operations;
                        updatedCount++;
                        console.log('更新继电器操作总次数:', data.total_relay_operations);
                    }} else if (label === '通电次数总和') {{
                        valueElement.textContent = data.total_power_on_operations;
                        updatedCount++;
                        console.log('更新通电次数总和:', data.total_power_on_operations);
                    }}
                }});
                
                // 更新点位状态概览
                const pointStatusItems = document.querySelectorAll('.section:nth-child(3) .status-item');
                pointStatusItems.forEach(item => {{
                    const label = item.querySelector('.status-label').textContent;
                    const valueElement = item.querySelector('.status-value');
                    
                    if (label === '已确认点位') {{
                        valueElement.textContent = data.confirmed_points_count + '个';
                        updatedCount++;
                        console.log('更新已确认点位:', data.confirmed_points_count);
                    }} else if (label === '未确认点位') {{
                        const totalPoints = data.total_points;
                        const confirmedPoints = data.confirmed_points_count;
                        const unconfirmedPoints = totalPoints - confirmedPoints;
                        valueElement.textContent = unconfirmedPoints + '个';
                        updatedCount++;
                        console.log('更新未确认点位:', unconfirmedPoints);
                    }}
                }});
                
                console.log(`系统状态更新完成，共更新了 ${updatedCount} 个数值`);
            }}
            
            // 更新测试历史
            async function updateTestHistory() {{
                try {{
                    console.log('开始更新测试历史...');
                    const response = await fetch('/api/test/history?page=1&page_size=10');
                    
                    if (!response.ok) {{
                        console.error('测试历史API请求失败:', response.status, response.statusText);
                        return;
                    }}
                    
                    const data = await response.json();
                    console.log('测试历史API响应:', data);
                    
                    const testHistoryDiv = document.getElementById('testHistory');
                    if (!testHistoryDiv) {{
                        console.error('找不到测试历史容器元素');
                        return;
                    }}
                    
                    if (data.success) {{
                        if (data.data.tests && data.data.tests.length > 0) {{
                            console.log(`找到 ${data.data.tests.length} 条测试记录`);
                            
                            // 清空现有内容
                            testHistoryDiv.innerHTML = '';
                            
                            // 添加新的测试历史
                            data.data.tests.forEach(test => {{
                                const testItem = document.createElement('div');
                                testItem.className = 'test-item';
                                
                                const testTime = new Date(test.timestamp * 1000).toLocaleTimeString('zh-CN');
                                
                                testItem.innerHTML = `
                                    <div class="test-header">
                                        <span>测试 #${test.test_id}</span>
                                        <span>${testTime}</span>
                                    </div>
                                    <div class="test-details">
                                        电源点位: ${test.power_source} | 测试点位: ${test.active_points.join(', ')} | 
                                        继电器操作: ${test.relay_operations}次 | 检测到连接: ${test.detected_connections.length}个
                                    </div>
                                `;
                                
                                testHistoryDiv.appendChild(testItem);
                            }});
                            
                            console.log('测试历史已更新，总测试次数:', data.data.total_tests);
                        }} else {{
                            console.log('暂无测试记录');
                            testHistoryDiv.innerHTML = '<div class="loading">暂无测试历史</div>';
                        }}
                    }} else {{
                        console.error('测试历史API返回失败:', data.error);
                        testHistoryDiv.innerHTML = '<div class="loading">获取测试历史失败</div>';
                    }}
                }} catch (error) {{
                    console.error('更新测试历史失败:', error);
                    const testHistoryDiv = document.getElementById('testHistory');
                    if (testHistoryDiv) {{
                        testHistoryDiv.innerHTML = '<div class="loading">更新测试历史时发生错误</div>';
                    }}
                }}
            }}
            
            // 显示详细点对信息
            function showDetailedInfo() {{
                alert('详细点对信息功能开发中...');
            }}
            
            // 显示已确认不导通
            function showConfirmedNonConductive() {{
                alert('已确认不导通功能开发中...');
            }}
            
            // 显示检测到的关系矩阵
            function showDetectedMatrix() {{
                alert('检测到的关系矩阵功能开发中...');
            }}
            
            // 显示真实关系矩阵
            function showTrueMatrix() {{
                alert('真实关系矩阵功能开发中...');
            }}
            
            // 显示矩阵对比
            function showMatrixComparison() {{
                alert('矩阵对比功能开发中...');
            }}
            
            // 显示真实导通点位信息
            function showTrueConductive() {{
                alert('真实导通点位信息功能开发中...');
            }}
            
            // 页面加载完成后启动自动刷新
            document.addEventListener('DOMContentLoaded', function() {{
                initAutoRefresh();
            }});
            
            // 页面卸载前清理定时器
            window.addEventListener('beforeunload', function() {{
                if (autoRefreshInterval) {{
                    clearInterval(autoRefreshInterval);
                }}
            }});
        </script>
    </body>
    </html>
    """
    
    return html_content

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
    
    # 获取已确认的点位关系数量
    confirmed_points_count = server.test_system.get_confirmed_points_count()
    
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
            'confirmed_clusters_count': 0,
            'confirmed_points_count': confirmed_points_count  # 新增：已确认点位数量
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

@app.route('/api/test/history', methods=['GET'])
def get_test_history():
    """获取测试历史"""
    try:
        page = request.args.get('page', 1, type=int)
        page_size = request.args.get('page_size', 50, type=int)
        
        # 获取测试历史
        test_history = server.test_system.test_history
        
        # 分页处理
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        page_tests = test_history[start_idx:end_idx]
        
        # 格式化测试历史
        formatted_tests = []
        for test in page_tests:
            formatted_test = {
                'test_id': test.test_id,
                'timestamp': test.timestamp,
                'power_source': test.power_source,
                'active_points': test.active_points,
                'detected_connections': [
                    {
                        'source_point': conn.source_point,
                        'target_points': conn.target_points,
                        'connection_type': conn.connection_type
                    }
                    for conn in test.detected_connections
                ],
                'test_duration': test.test_duration,
                'relay_operations': test.relay_operations,
                'power_on_operations': getattr(test, 'power_on_operations', 0),
                'total_points': test.total_points
            }
            formatted_tests.append(formatted_test)
        
        return jsonify({
            'success': True,
            'data': {
                'tests': formatted_tests,
                'total_tests': len(test_history),
                'page': page,
                'page_size': page_size,
                'total_pages': (len(test_history) + page_size - 1) // page_size,
                'timestamp': time.time()
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'获取测试历史失败: {str(e)}'
        })

@app.route('/api/relay/stats', methods=['GET'])
def get_relay_stats():
    """获取继电器操作统计信息"""
    return jsonify(server.get_relay_stats())

@app.route('/api/relationships/matrix', methods=['GET'])
def get_relationship_matrix():
    """获取关系矩阵"""
    try:
        matrix = server.test_system.relationship_matrix
        if matrix is None:
            return jsonify({
                'success': False,
                'error': '关系矩阵未初始化'
            })
        
        return jsonify({
            'success': True,
            'data': {
                'matrix': matrix,
                'total_points': server.test_system.total_points,
                'timestamp': time.time()
            }
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'获取关系矩阵失败: {str(e)}'
        })

@app.route('/api/relationships/true_matrix', methods=['GET'])
def get_true_relationship_matrix():
    """获取真实关系矩阵"""
    try:
        # 构建真实关系矩阵
        total_points = server.test_system.total_points
        true_matrix = [[0] * total_points for _ in range(total_points)]
        
        # 填充真实连接关系
        for i in range(total_points):
            true_matrix[i][i] = 1  # 对角线为1（自己连接自己）
            
            # 填充真实连接关系
            if hasattr(server.test_system, 'true_pairs'):
                for pair in server.test_system.true_pairs:
                    if pair[0] == i:
                        true_matrix[i][pair[1]] = 1
                        true_matrix[pair[1]][i] = 1
        
        return jsonify({
            'success': True,
            'data': {
                'matrix': true_matrix,
                'total_points': total_points,
                'timestamp': time.time()
            }
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'获取真实关系矩阵失败: {str(e)}'
        })

@app.route('/api/relay/reset', methods=['POST'])
def reset_relay_states():
    """重置所有继电器状态"""
    return jsonify(server.reset_relay_states())

if __name__ == '__main__':
    logger.info("启动Flask测试服务端...")
    logger.info(f"系统配置: {server.test_system.total_points} 个测试点位")
    logger.info("服务端启动完成，监听端口 5000")
    
    app.run(host='0.0.0.0', port=5000, debug=False)
