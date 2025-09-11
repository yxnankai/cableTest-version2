#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from flask import Flask, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

@app.route('/')
def index():
    return '''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>线缆测试系统 - 简化版</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.js"></script>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        .container { max-width: 1200px; margin: 0 auto; }
        .section { margin: 20px 0; padding: 20px; border: 1px solid #ddd; border-radius: 5px; }
        .loading { text-align: center; color: #666; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🔌 线缆测试系统 - 简化版</h1>
        
        <div class="section">
            <h3>📊 系统状态</h3>
            <div id="systemInfo">
                <div class="loading">加载中...</div>
            </div>
        </div>
        
        <div class="section">
            <h3>🔗 点对关系信息</h3>
            <div id="clusterInfo">
                <div class="loading">加载中...</div>
            </div>
        </div>
        
        <div class="section">
            <h3>📍 点位状态概览</h3>
            <div id="pointStatus">
                <div class="loading">加载中...</div>
            </div>
        </div>
        
        <div class="section">
            <h3>📈 实验进度图表</h3>
            <canvas id="progressChart" width="400" height="200"></canvas>
        </div>
    </div>
    
    <script>
        // 版本标识符
        console.log('简化版页面版本: 2025-09-10-simple');
        
        // 初始化数据加载
        async function loadInitialData() {
            try {
                console.log('开始加载数据...');
                
                // 加载系统信息
                const systemResponse = await fetch('/api/system/info');
                const systemData = await systemResponse.json();
                console.log('系统信息:', systemData);
                
                document.getElementById('systemInfo').innerHTML = `
                    <div><strong>总点位:</strong> ${systemData.total_points || 0}</div>
                    <div><strong>已确认点位:</strong> ${systemData.confirmed_points_count || 0}</div>
                    <div><strong>系统状态:</strong> <span style="color: #4CAF50;">运行中</span></div>
                `;
                
                // 加载集群信息
                const clusterResponse = await fetch('/api/clusters');
                const clusterData = await clusterResponse.json();
                console.log('集群信息:', clusterData);
                
                document.getElementById('clusterInfo').innerHTML = `
                    <div><strong>连接组数量:</strong> ${clusterData.total_clusters || 0}</div>
                    <div><strong>状态:</strong> 正常</div>
                `;
                
                // 加载点位状态
                const pointResponse = await fetch('/api/points/status');
                const pointData = await pointResponse.json();
                console.log('点位状态:', pointData);
                
                const totalPoints = pointData.total_points || 0;
                const onPoints = Object.values(pointData.point_states || {}).filter(state => state === 1).length;
                
                document.getElementById('pointStatus').innerHTML = `
                    <div><strong>总点位:</strong> ${totalPoints}</div>
                    <div><strong>开启:</strong> <span style="color: #4CAF50;">${onPoints}</span></div>
                    <div><strong>关闭:</strong> <span style="color: #f44336;">${totalPoints - onPoints}</span></div>
                `;
                
                // 初始化图表
                initChart();
                
                console.log('数据加载完成');
                
            } catch (error) {
                console.error('加载数据失败:', error);
                document.querySelectorAll('.loading').forEach(el => {
                    el.innerHTML = '加载失败，请检查服务器连接';
                });
            }
        }
        
        // 初始化图表
        function initChart() {
            const ctx = document.getElementById('progressChart');
            const chart = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: ['开始', '测试1', '测试2', '测试3'],
                    datasets: [{
                        label: '已知关系数量',
                        data: [0, 10, 25, 50],
                        borderColor: '#4CAF50',
                        backgroundColor: 'rgba(76, 175, 80, 0.1)',
                        borderWidth: 2,
                        fill: true
                    }]
                },
                options: {
                    responsive: true,
                    plugins: {
                        title: {
                            display: true,
                            text: '实验进度图表'
                        }
                    },
                    scales: {
                        y: {
                            beginAtZero: true
                        }
                    }
                }
            });
        }
        
        // 页面加载完成后初始化
        document.addEventListener('DOMContentLoaded', () => {
            loadInitialData();
        });
    </script>
</body>
</html>'''

@app.route('/api/system/info')
def system_info():
    return jsonify({
        "success": True,
        "total_points": 100,
        "confirmed_points_count": 0,
        "detected_conductive_count": 0,
        "relay_switch_time": 0.003,
        "total_tests": 0,
        "total_relay_operations": 0,
        "total_power_on_operations": 0,
        "timestamp": 1757482000.0
    })

@app.route('/api/clusters')
def clusters():
    return jsonify({
        "success": True,
        "clusters": [],
        "total_clusters": 0,
        "timestamp": 1757482000.0
    })

@app.route('/api/points/status')
def points_status():
    point_states = {str(i): 0 for i in range(100)}
    return jsonify({
        "success": True,
        "point_states": point_states,
        "total_points": 100,
        "timestamp": 1757482000.0
    })

if __name__ == '__main__':
    print("🚀 启动简化版线缆测试系统...")
    print("📱 访问地址: http://localhost:5001")
    # 使用高性能waitress服务器替代Flask开发服务器
    from waitress import serve
    serve(app, host='127.0.0.1', port=5001, threads=6)