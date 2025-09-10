#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试端Flask服务器
提供测试端的前端配置界面和API接口
"""

from flask import Flask, render_template_string, request, jsonify
import json
import time
from adaptive_grouping_test import AdaptiveGroupingTester
from adaptive_grouping_config import get_config, PRESETS

app = Flask(__name__)

# 全局测试器实例
tester = None
test_config = None

# 测试端前端页面
TEST_FRONTEND_HTML = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>测试端配置界面</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #f5f5f5;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            overflow: hidden;
        }
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            text-align: center;
        }
        .content {
            padding: 30px;
        }
        .section {
            margin-bottom: 30px;
            padding: 20px;
            border: 1px solid #e0e0e0;
            border-radius: 8px;
            background: #fafafa;
        }
        .section h3 {
            margin-top: 0;
            color: #333;
            border-bottom: 2px solid #667eea;
            padding-bottom: 10px;
        }
        .form-group {
            margin-bottom: 15px;
        }
        .form-group label {
            display: block;
            margin-bottom: 5px;
            font-weight: bold;
            color: #555;
        }
        .form-group input, .form-group select {
            width: 100%;
            padding: 8px 12px;
            border: 1px solid #ddd;
            border-radius: 4px;
            font-size: 14px;
        }
        .form-group input[type="number"] {
            width: 100px;
        }
        .form-row {
            display: flex;
            gap: 15px;
            align-items: end;
        }
        .form-row .form-group {
            flex: 1;
        }
        .btn {
            background: #667eea;
            color: white;
            border: none;
            padding: 10px 20px;
            border-radius: 4px;
            cursor: pointer;
            font-size: 14px;
            margin-right: 10px;
        }
        .btn:hover {
            background: #5a6fd8;
        }
        .btn-danger {
            background: #e74c3c;
        }
        .btn-danger:hover {
            background: #c0392b;
        }
        .btn-success {
            background: #27ae60;
        }
        .btn-success:hover {
            background: #229954;
        }
        .status {
            padding: 15px;
            border-radius: 4px;
            margin-bottom: 20px;
        }
        .status.running {
            background: #d4edda;
            border: 1px solid #c3e6cb;
            color: #155724;
        }
        .status.stopped {
            background: #f8d7da;
            border: 1px solid #f5c6cb;
            color: #721c24;
        }
        .status.idle {
            background: #d1ecf1;
            border: 1px solid #bee5eb;
            color: #0c5460;
        }
        .config-display {
            background: #f8f9fa;
            border: 1px solid #dee2e6;
            border-radius: 4px;
            padding: 15px;
            margin-top: 15px;
        }
        .config-display pre {
            margin: 0;
            white-space: pre-wrap;
            font-size: 12px;
        }
        .strategy-thresholds {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-top: 15px;
        }
        .threshold-item {
            background: white;
            border: 1px solid #ddd;
            border-radius: 4px;
            padding: 15px;
        }
        .threshold-item h4 {
            margin: 0 0 10px 0;
            color: #667eea;
        }
        .log-container {
            background: #2d3748;
            color: #e2e8f0;
            border-radius: 4px;
            padding: 15px;
            height: 300px;
            overflow-y: auto;
            font-family: 'Courier New', monospace;
            font-size: 12px;
        }
        .log-entry {
            margin-bottom: 5px;
        }
        .log-entry.info { color: #63b3ed; }
        .log-entry.success { color: #68d391; }
        .log-entry.warning { color: #f6e05e; }
        .log-entry.error { color: #fc8181; }
        
        /* 实验进展样式 */
        .experiment-progress {
            background: #f8f9fa;
            border: 1px solid #dee2e6;
            border-radius: 8px;
            padding: 20px;
        }
        
        .progress-stats {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-bottom: 20px;
        }
        
        .stat-item {
            background: white;
            border: 1px solid #ddd;
            border-radius: 4px;
            padding: 15px;
            text-align: center;
        }
        
        .stat-label {
            display: block;
            font-weight: bold;
            color: #666;
            margin-bottom: 5px;
        }
        
        .stat-value {
            display: block;
            font-size: 18px;
            font-weight: bold;
            color: #333;
        }
        
        .progress-chart {
            background: white;
            border: 1px solid #ddd;
            border-radius: 4px;
            padding: 15px;
            text-align: center;
        }
        
        /* 策略控制按钮样式 */
        .strategy-controls {
            display: flex;
            gap: 10px;
            margin: 15px 0;
            padding: 10px;
            background: #f8f9fa;
            border-radius: 4px;
        }
        
        .strategy-controls .btn {
            padding: 8px 16px;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-size: 14px;
            transition: all 0.3s ease;
        }
        
        .strategy-controls .btn:disabled {
            opacity: 0.5;
            cursor: not-allowed;
        }
        
        .btn-secondary {
            background: #6c757d;
            color: white;
        }
        
        .btn-secondary:hover:not(:disabled) {
            background: #5a6268;
        }
        
        .btn-danger {
            background: #dc3545;
            color: white;
        }
        
        .btn-danger:hover:not(:disabled) {
            background: #c82333;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🔬 测试端配置界面</h1>
            <p>配置自适应分组测试策略和参数</p>
        </div>
        
        <div class="content">
            <!-- 系统状态 -->
            <div class="section">
                <h3>📊 系统状态</h3>
                <div id="systemStatus" class="status idle">
                    <strong>状态:</strong> 未初始化
                </div>
                <div class="form-row">
                    <button class="btn btn-success" onclick="initializeSystem()">初始化系统</button>
                    <button class="btn btn-danger" onclick="resetSystem()">重置系统</button>
                    <button class="btn" onclick="refreshStatus()">刷新状态</button>
                </div>
            </div>
            
            <!-- 基础配置 -->
            <div class="section">
                <h3>⚙️ 基础配置</h3>
                <div class="form-row">
                    <div class="form-group">
                        <label for="totalPoints">总点位数:</label>
                        <input type="number" id="totalPoints" value="100" min="10" max="1000">
                    </div>
                    <div class="form-group">
                        <label for="maxTests">最大测试次数:</label>
                        <input type="number" id="maxTests" value="2000" min="100" max="10000">
                    </div>
                    <div class="form-group">
                        <label for="concurrency">并发数:</label>
                        <input type="number" id="concurrency" value="4" min="1" max="10">
                    </div>
                </div>
            </div>
            
            <!-- 策略配置 -->
            <div class="section">
                <h3>🎯 策略配置</h3>
                <div class="form-group">
                    <label for="strategyPreset">预设策略:</label>
                    <select id="strategyPreset" onchange="loadPreset()">
                        <option value="balanced">平衡策略</option>
                        <option value="conservative">保守策略</option>
                        <option value="aggressive">激进策略</option>
                        <option value="custom">自定义</option>
                    </select>
                </div>
                
                <div class="strategy-controls">
                    <button type="button" id="addStrategyBtn" class="btn btn-secondary" onclick="addStrategy()">
                        ➕ 添加策略
                    </button>
                    <button type="button" id="removeStrategyBtn" class="btn btn-danger" onclick="removeStrategy()" disabled>
                        ➖ 删除策略
                    </button>
                </div>
                
                <div id="strategyConfig" class="strategy-thresholds">
                    <!-- 策略卡片将通过JavaScript动态生成 -->
                </div>
            </div>
            
            <!-- 高级配置 -->
            <div class="section">
                <h3>🔧 高级配置</h3>
                <div class="form-row">
                    <div class="form-group">
                        <label for="minGroupSize">最小分组大小:</label>
                        <input type="number" id="minGroupSize" value="5" min="2" max="50">
                    </div>
                    <div class="form-group">
                        <label for="maxGroupSize">最大分组大小:</label>
                        <input type="number" id="maxGroupSize" value="50" min="10" max="200">
                    </div>
                    <div class="form-group">
                        <label for="minUnknownRatio">最小未知关系比例:</label>
                        <input type="number" id="minUnknownRatio" value="70" min="0" max="100" step="1">%
                    </div>
                </div>
                <div class="form-row">
                    <div class="form-group">
                        <label for="enableDynamicAdjustment">启用动态调整:</label>
                        <select id="enableDynamicAdjustment">
                            <option value="true">是</option>
                            <option value="false">否</option>
                        </select>
                    </div>
                    <div class="form-group">
                        <label for="adjustmentThreshold">调整阈值:</label>
                        <input type="number" id="adjustmentThreshold" value="80" min="0" max="100" step="1">%
                    </div>
                </div>
            </div>
            
            <!-- 测试控制 -->
            <div class="section">
                <h3>🚀 测试控制</h3>
                <div class="form-row">
                    <button class="btn btn-success" onclick="startTest()">开始测试</button>
                    <button class="btn btn-danger" onclick="stopTest()">停止测试</button>
                    <button class="btn" onclick="pauseTest()">暂停测试</button>
                    <button class="btn" onclick="resumeTest()">继续测试</button>
                </div>
                <div class="form-row">
                    <button class="btn" onclick="saveConfig()">保存配置</button>
                    <button class="btn" onclick="loadConfig()">加载配置</button>
                    <button class="btn" onclick="exportResults()">导出结果</button>
                </div>
            </div>
            
            <!-- 当前配置显示 -->
            <div class="section">
                <h3>📋 当前配置</h3>
                <div id="currentConfig" class="config-display">
                    <pre>配置未加载</pre>
                </div>
            </div>
            
            <!-- 实验进展 -->
            <div class="section">
                <h3>📊 实验进展</h3>
                <div id="experimentProgress" class="experiment-progress">
                    <div class="progress-stats">
                        <div class="stat-item">
                            <span class="stat-label">当前策略:</span>
                            <span id="currentStrategy" class="stat-value">未开始</span>
                        </div>
                        <div class="stat-item">
                            <span class="stat-label">测试次数:</span>
                            <span id="testCount" class="stat-value">0</span>
                        </div>
                        <div class="stat-item">
                            <span class="stat-label">未知关系比例:</span>
                            <span id="unknownRatio" class="stat-value">100.0%</span>
                        </div>
                        <div class="stat-item">
                            <span class="stat-label">已知关系数量:</span>
                            <span id="knownRelations" class="stat-value">0</span>
                        </div>
                    </div>
                    <div class="progress-chart">
                        <canvas id="progressChart" width="800" height="300"></canvas>
                    </div>
                </div>
            </div>
            
            <!-- 测试日志 -->
            <div class="section">
                <h3>📝 测试日志</h3>
                <div id="testLog" class="log-container">
                    <div class="log-entry info">等待测试开始...</div>
                </div>
            </div>
        </div>
    </div>

    <script>
        let testRunning = false;
        let testPaused = false;
        let progressChart = null;
        let progressData = [];
        let strategies = []; // 存储策略配置
        let strategyCounter = 0; // 策略计数器
        
        // 页面加载完成后初始化
        document.addEventListener('DOMContentLoaded', function() {
            loadPreset();
            refreshStatus();
            initProgressChart();
            initDefaultStrategies();
        });
        
        // 初始化默认策略
        function initDefaultStrategies() {
            strategies = [
                {
                    id: 'strategy_1',
                    name: '50%集群策略',
                    minRatio: 10,
                    maxRatio: 100,
                    clusterRatio: 50,
                    type: 'cluster'
                },
                {
                    id: 'strategy_2',
                    name: '30%集群策略',
                    minRatio: 10,
                    maxRatio: 100,
                    clusterRatio: 30,
                    type: 'cluster'
                },
                {
                    id: 'strategy_3',
                    name: '10%集群策略',
                    minRatio: 10,
                    maxRatio: 100,
                    clusterRatio: 10,
                    type: 'cluster'
                },
                {
                    id: 'strategy_4',
                    name: '二分法策略',
                    minRatio: 0,
                    maxRatio: 10,
                    clusterRatio: 0,
                    type: 'binary_search'
                }
            ];
            strategyCounter = 4;
            // 确保范围正确连接
            adjustStrategyRanges();
            renderStrategies();
        }
        
        // 渲染策略配置
        function renderStrategies() {
            const container = document.getElementById('strategyConfig');
            container.innerHTML = '';
            
            strategies.forEach((strategy, index) => {
                const strategyDiv = document.createElement('div');
                strategyDiv.className = 'threshold-item';
                strategyDiv.id = strategy.id;
                
                const isLast = index === strategies.length - 1;
                const isBinary = strategy.type === 'binary_search';
                
                strategyDiv.innerHTML = `
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
                        <h4>${strategy.name}</h4>
                        ${!isLast ? `<button type="button" class="btn btn-sm btn-outline-danger" onclick="removeSpecificStrategy('${strategy.id}')" style="padding: 4px 8px; font-size: 12px;">删除</button>` : ''}
                    </div>
                    <div class="form-group">
                        <label>未知关系比例范围:</label>
                        <input type="number" id="${strategy.id}_min" value="${strategy.minRatio}" min="0" max="100" step="1" onchange="updateStrategy('${strategy.id}')">% - 
                        <input type="number" id="${strategy.id}_max" value="${strategy.maxRatio}" min="0" max="100" step="1" onchange="updateStrategy('${strategy.id}')">%
                    </div>
                    ${!isBinary ? `
                        <div class="form-group">
                            <label>集群比例:</label>
                            <input type="number" id="${strategy.id}_cluster" value="${strategy.clusterRatio}" min="1" max="100" step="1" onchange="updateStrategy('${strategy.id}')">%
                        </div>
                    ` : `
                        <div class="form-group">
                            <label>策略类型:</label>
                            <select id="${strategy.id}_type" onchange="updateStrategy('${strategy.id}')">
                                <option value="binary_search" ${strategy.type === 'binary_search' ? 'selected' : ''}>二分法</option>
                                <option value="exhaustive" ${strategy.type === 'exhaustive' ? 'selected' : ''}>穷举法</option>
                            </select>
                        </div>
                    `}
                `;
                
                container.appendChild(strategyDiv);
            });
            
            updateRemoveButtonState();
        }
        
        // 添加策略
        function addStrategy() {
            if (strategies.length >= 10) {
                alert('最多只能添加10个策略！');
                return;
            }
            
            // 找到最后一个非二分法策略
            const lastClusterIndex = strategies.findIndex(s => s.type === 'binary_search') - 1;
            const lastCluster = strategies[lastClusterIndex];
            
            strategyCounter++;
            const newStrategy = {
                id: `strategy_${strategyCounter}`,
                name: `${lastCluster.clusterRatio}%集群策略`,
                minRatio: lastCluster.maxRatio,
                maxRatio: Math.min(lastCluster.maxRatio + 20, 100),
                clusterRatio: Math.max(lastCluster.clusterRatio - 10, 5),
                type: 'cluster'
            };
            
            // 在二分法策略之前插入新策略
            const binaryIndex = strategies.findIndex(s => s.type === 'binary_search');
            strategies.splice(binaryIndex, 0, newStrategy);
            
            // 更新二分法策略的最小比例
            const binaryStrategy = strategies.find(s => s.type === 'binary_search');
            binaryStrategy.minRatio = newStrategy.maxRatio;
            
            renderStrategies();
        }
        
        // 删除策略
        function removeStrategy() {
            if (strategies.length <= 2) {
                alert('至少需要保留2个策略！');
                return;
            }
            
            // 删除最后一个非二分法策略
            const lastClusterIndex = strategies.findIndex(s => s.type === 'binary_search') - 1;
            if (lastClusterIndex >= 0) {
                strategies.splice(lastClusterIndex, 1);
                
                // 更新二分法策略的最小比例
                const binaryStrategy = strategies.find(s => s.type === 'binary_search');
                const newLastCluster = strategies[lastClusterIndex - 1];
                if (newLastCluster) {
                    binaryStrategy.minRatio = newLastCluster.maxRatio;
                }
                
                renderStrategies();
            }
        }
        
        // 删除特定策略
        function removeSpecificStrategy(strategyId) {
            if (strategies.length <= 2) {
                alert('至少需要保留2个策略！');
                return;
            }
            
            const index = strategies.findIndex(s => s.id === strategyId);
            if (index >= 0 && strategies[index].type !== 'binary_search') {
                strategies.splice(index, 1);
                
                // 重新调整比例范围
                adjustStrategyRanges();
                renderStrategies();
            }
        }
        
        // 调整策略范围
        function adjustStrategyRanges() {
            // 找到二分法策略
            const binaryStrategy = strategies.find(s => s.type === 'binary_search');
            const clusterStrategies = strategies.filter(s => s.type !== 'binary_search');
            
            if (binaryStrategy && clusterStrategies.length > 0) {
                // 设置二分法策略的范围为 0% - 10%
                binaryStrategy.minRatio = 0;
                binaryStrategy.maxRatio = 10;
                
                // 设置其他策略的范围，以10%为基底
                const totalRange = 100 - 10; // 90%的范围给集群策略
                const rangePerStrategy = totalRange / clusterStrategies.length;
                
                for (let i = 0; i < clusterStrategies.length; i++) {
                    const strategy = clusterStrategies[i];
                    strategy.minRatio = 10 + (i * rangePerStrategy);
                    strategy.maxRatio = 10 + ((i + 1) * rangePerStrategy);
                }
                
                // 确保最后一个集群策略的最大值是100%
                clusterStrategies[clusterStrategies.length - 1].maxRatio = 100;
            } else {
                // 如果没有二分法策略，使用原来的逻辑
                for (let i = 0; i < strategies.length - 1; i++) {
                    const current = strategies[i];
                    const next = strategies[i + 1];
                    current.maxRatio = next.minRatio;
                }
            }
        }
        
        // 更新策略
        function updateStrategy(strategyId) {
            const strategy = strategies.find(s => s.id === strategyId);
            if (!strategy) return;
            
            const minInput = document.getElementById(`${strategyId}_min`);
            const maxInput = document.getElementById(`${strategyId}_max`);
            const clusterInput = document.getElementById(`${strategyId}_cluster`);
            const typeSelect = document.getElementById(`${strategyId}_type`);
            
            if (minInput) strategy.minRatio = parseInt(minInput.value);
            if (maxInput) strategy.maxRatio = parseInt(maxInput.value);
            if (clusterInput) strategy.clusterRatio = parseInt(clusterInput.value);
            if (typeSelect) strategy.type = typeSelect.value;
            
            // 自动调整相邻策略的范围
            adjustStrategyRanges();
            renderStrategies();
        }
        
        // 更新删除按钮状态
        function updateRemoveButtonState() {
            const removeBtn = document.getElementById('removeStrategyBtn');
            const clusterStrategies = strategies.filter(s => s.type !== 'binary_search');
            removeBtn.disabled = clusterStrategies.length <= 1;
        }
        
        // 加载预设配置
        function loadPreset() {
            const preset = document.getElementById('strategyPreset').value;
            
            if (preset === 'custom') {
                return; // 自定义配置，不自动填充
            }
            
            // 根据预设设置策略
            if (preset === 'balanced') {
                // 平衡策略
                strategies = [
                    { id: 'strategy_1', name: '50%集群策略', minRatio: 10, maxRatio: 100, clusterRatio: 50, type: 'cluster' },
                    { id: 'strategy_2', name: '30%集群策略', minRatio: 10, maxRatio: 100, clusterRatio: 30, type: 'cluster' },
                    { id: 'strategy_3', name: '10%集群策略', minRatio: 10, maxRatio: 100, clusterRatio: 10, type: 'cluster' },
                    { id: 'strategy_4', name: '二分法策略', minRatio: 0, maxRatio: 10, clusterRatio: 0, type: 'binary_search' }
                ];
            } else if (preset === 'aggressive') {
                // 激进策略
                strategies = [
                    { id: 'strategy_1', name: '60%集群策略', minRatio: 10, maxRatio: 100, clusterRatio: 60, type: 'cluster' },
                    { id: 'strategy_2', name: '40%集群策略', minRatio: 10, maxRatio: 100, clusterRatio: 40, type: 'cluster' },
                    { id: 'strategy_3', name: '20%集群策略', minRatio: 10, maxRatio: 100, clusterRatio: 20, type: 'cluster' },
                    { id: 'strategy_4', name: '二分法策略', minRatio: 0, maxRatio: 10, clusterRatio: 0, type: 'binary_search' }
                ];
            } else if (preset === 'conservative') {
                // 保守策略
                strategies = [
                    { id: 'strategy_1', name: '40%集群策略', minRatio: 10, maxRatio: 100, clusterRatio: 40, type: 'cluster' },
                    { id: 'strategy_2', name: '20%集群策略', minRatio: 10, maxRatio: 100, clusterRatio: 20, type: 'cluster' },
                    { id: 'strategy_3', name: '10%集群策略', minRatio: 10, maxRatio: 100, clusterRatio: 10, type: 'cluster' },
                    { id: 'strategy_4', name: '二分法策略', minRatio: 0, maxRatio: 10, clusterRatio: 0, type: 'binary_search' }
                ];
            }
            
            strategyCounter = strategies.length;
            // 确保范围正确连接
            adjustStrategyRanges();
            renderStrategies();
            updateConfigDisplay();
        }
        
        // 应用配置到界面
        function applyConfig(config) {
            document.getElementById('totalPoints').value = config.total_points || 100;
            document.getElementById('maxTests').value = config.test_execution?.max_total_tests || 2000;
            document.getElementById('concurrency').value = config.concurrency || 4;
            
            // 应用策略阈值
            const thresholds = config.test_execution?.phase_switch_criteria?.phase_thresholds || {};
            
            if (thresholds.phase_1) {
                document.getElementById('threshold50Min').value = Math.round(thresholds.phase_1.min_unknown_ratio * 100);
                document.getElementById('threshold50Max').value = Math.round(thresholds.phase_1.max_unknown_ratio * 100);
                document.getElementById('ratio50').value = Math.round(thresholds.phase_1.group_ratio * 100);
            }
            
            if (thresholds.phase_2) {
                document.getElementById('threshold30Min').value = Math.round(thresholds.phase_2.min_unknown_ratio * 100);
                document.getElementById('threshold30Max').value = Math.round(thresholds.phase_2.max_unknown_ratio * 100);
                document.getElementById('ratio30').value = Math.round(thresholds.phase_2.group_ratio * 100);
            }
            
            if (thresholds.phase_3) {
                document.getElementById('threshold10Min').value = Math.round(thresholds.phase_3.min_unknown_ratio * 100);
                document.getElementById('threshold10Max').value = Math.round(thresholds.phase_3.max_unknown_ratio * 100);
                document.getElementById('ratio10').value = Math.round(thresholds.phase_3.group_ratio * 100);
            }
            
            if (thresholds.binary_search) {
                document.getElementById('thresholdBinaryMin').value = Math.round(thresholds.binary_search.min_unknown_ratio * 100);
                document.getElementById('thresholdBinaryMax').value = Math.round(thresholds.binary_search.max_unknown_ratio * 100);
            }
            
            // 应用高级配置
            const adaptive = config.adaptive_grouping || {};
            document.getElementById('minGroupSize').value = adaptive.min_group_size || 5;
            document.getElementById('maxGroupSize').value = adaptive.max_group_size || 50;
            document.getElementById('minUnknownRatio').value = Math.round((adaptive.min_unknown_relations_per_group || 0.7) * 100);
            document.getElementById('enableDynamicAdjustment').value = adaptive.enable_dynamic_adjustment ? 'true' : 'false';
            document.getElementById('adjustmentThreshold').value = Math.round((adaptive.adjustment_threshold || 0.8) * 100);
        }
        
        // 更新配置显示
        function updateConfigDisplay() {
            const config = getCurrentConfig();
            document.getElementById('currentConfig').innerHTML = '<pre>' + JSON.stringify(config, null, 2) + '</pre>';
        }
        
        // 获取当前配置
        function getCurrentConfig() {
            // 从动态策略生成配置
            const phaseThresholds = {};
            const groupRatios = [];
            
            strategies.forEach((strategy, index) => {
                const phaseKey = `phase_${index + 1}`;
                phaseThresholds[phaseKey] = {
                    min_unknown_ratio: strategy.minRatio / 100,
                    max_unknown_ratio: strategy.maxRatio / 100,
                    group_ratio: strategy.type === 'binary_search' ? 0 : strategy.clusterRatio / 100,
                    strategy_type: strategy.type
                };
                
                if (strategy.type !== 'binary_search') {
                    groupRatios.push(strategy.clusterRatio / 100);
                }
            });
            
            return {
                total_points: parseInt(document.getElementById('totalPoints').value),
                concurrency: parseInt(document.getElementById('concurrency').value),
                test_execution: {
                    max_total_tests: parseInt(document.getElementById('maxTests').value),
                    max_tests_per_phase: parseInt(document.getElementById('maxTests').value) / strategies.length,
                    phase_switch_criteria: {
                        phase_thresholds: phaseThresholds,
                        min_tests_per_phase: 10
                    }
                },
                adaptive_grouping: {
                    group_ratios: groupRatios,
                    min_group_size: parseInt(document.getElementById('minGroupSize').value),
                    max_group_size: parseInt(document.getElementById('maxGroupSize').value),
                    min_unknown_relations_per_group: parseInt(document.getElementById('minUnknownRatio').value) / 100,
                    enable_dynamic_adjustment: document.getElementById('enableDynamicAdjustment').value === 'true',
                    adjustment_threshold: parseInt(document.getElementById('adjustmentThreshold').value) / 100
                }
            };
        }
        
        // 初始化系统
        function initializeSystem() {
            addLog('正在初始化系统...', 'info');
            
            fetch('/api/system/init', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(getCurrentConfig())
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    addLog('系统初始化成功', 'success');
                    refreshStatus();
                } else {
                    addLog('系统初始化失败: ' + data.error, 'error');
                }
            })
            .catch(error => {
                addLog('系统初始化失败: ' + error.message, 'error');
            });
        }
        
        // 重置系统
        function resetSystem() {
            if (!confirm('确定要重置系统吗？这将清除所有测试数据。')) {
                return;
            }
            
            addLog('正在重置系统...', 'info');
            
            fetch('/api/system/reset', {method: 'POST'})
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    addLog('系统重置成功', 'success');
                    refreshStatus();
                } else {
                    addLog('系统重置失败: ' + data.error, 'error');
                }
            })
            .catch(error => {
                addLog('系统重置失败: ' + error.message, 'error');
            });
        }
        
        // 刷新状态
        function refreshStatus() {
            fetch('/api/system/status')
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    updateSystemStatus(data.status);
                }
            })
            .catch(error => {
                console.error('获取状态失败:', error);
            });
        }
        
        // 更新系统状态显示
        function updateSystemStatus(status) {
            const statusDiv = document.getElementById('systemStatus');
            statusDiv.className = 'status ' + status.state;
            statusDiv.innerHTML = `
                <strong>状态:</strong> ${status.state_text}<br>
                <strong>总测试次数:</strong> ${status.total_tests}<br>
                <strong>当前策略:</strong> ${status.current_strategy}<br>
                <strong>未知关系比例:</strong> ${status.unknown_ratio.toFixed(1)}%
            `;
        }
        
        // 开始测试
        function startTest() {
            if (testRunning) {
                addLog('测试已在运行中', 'warning');
                return;
            }
            
            addLog('正在启动测试...', 'info');
            
            fetch('/api/test/start', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(getCurrentConfig())
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    testRunning = true;
                    addLog('测试已启动', 'success');
                    refreshStatus();
                    startStatusPolling();
                } else {
                    addLog('测试启动失败: ' + data.error, 'error');
                }
            })
            .catch(error => {
                addLog('测试启动失败: ' + error.message, 'error');
            });
        }
        
        // 停止测试
        function stopTest() {
            if (!testRunning) {
                addLog('没有正在运行的测试', 'warning');
                return;
            }
            
            addLog('正在停止测试...', 'info');
            
            fetch('/api/test/stop', {method: 'POST'})
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    testRunning = false;
                    testPaused = false;
                    addLog('测试已停止', 'success');
                    refreshStatus();
                } else {
                    addLog('测试停止失败: ' + data.error, 'error');
                }
            })
            .catch(error => {
                addLog('测试停止失败: ' + error.message, 'error');
            });
        }
        
        // 暂停测试
        function pauseTest() {
            if (!testRunning || testPaused) {
                addLog('没有可暂停的测试', 'warning');
                return;
            }
            
            addLog('正在暂停测试...', 'info');
            testPaused = true;
            addLog('测试已暂停', 'success');
        }
        
        // 继续测试
        function resumeTest() {
            if (!testRunning || !testPaused) {
                addLog('没有可继续的测试', 'warning');
                return;
            }
            
            addLog('正在继续测试...', 'info');
            testPaused = false;
            addLog('测试已继续', 'success');
        }
        
        // 保存配置
        function saveConfig() {
            const config = getCurrentConfig();
            const configStr = JSON.stringify(config, null, 2);
            const blob = new Blob([configStr], {type: 'application/json'});
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = 'test_config.json';
            a.click();
            URL.revokeObjectURL(url);
            addLog('配置已保存到文件', 'success');
        }
        
        // 加载配置
        function loadConfig() {
            const input = document.createElement('input');
            input.type = 'file';
            input.accept = '.json';
            input.onchange = function(e) {
                const file = e.target.files[0];
                if (file) {
                    const reader = new FileReader();
                    reader.onload = function(e) {
                        try {
                            const config = JSON.parse(e.target.result);
                            applyConfig(config);
                            updateConfigDisplay();
                            addLog('配置已加载', 'success');
                        } catch (error) {
                            addLog('配置加载失败: ' + error.message, 'error');
                        }
                    };
                    reader.readAsText(file);
                }
            };
            input.click();
        }
        
        // 导出结果
        function exportResults() {
            fetch('/api/results/export')
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    const resultsStr = JSON.stringify(data.results, null, 2);
                    const blob = new Blob([resultsStr], {type: 'application/json'});
                    const url = URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.href = url;
                    a.download = 'test_results.json';
                    a.click();
                    URL.revokeObjectURL(url);
                    addLog('结果已导出', 'success');
                } else {
                    addLog('结果导出失败: ' + data.error, 'error');
                }
            })
            .catch(error => {
                addLog('结果导出失败: ' + error.message, 'error');
            });
        }
        
        // 添加日志
        function addLog(message, type = 'info') {
            const logContainer = document.getElementById('testLog');
            const timestamp = new Date().toLocaleTimeString();
            const logEntry = document.createElement('div');
            logEntry.className = 'log-entry ' + type;
            logEntry.textContent = `[${timestamp}] ${message}`;
            logContainer.appendChild(logEntry);
            logContainer.scrollTop = logContainer.scrollHeight;
        }
        
        // 初始化进度图表
        function initProgressChart() {
            const ctx = document.getElementById('progressChart').getContext('2d');
            progressChart = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: [],
                    datasets: [{
                        label: '已知关系数量',
                        data: [],
                        borderColor: '#36A2EB',
                        backgroundColor: 'rgba(54, 162, 235, 0.1)',
                        tension: 0.1
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                        y: {
                            beginAtZero: true,
                            title: {
                                display: true,
                                text: '已知关系数量'
                            }
                        },
                        x: {
                            title: {
                                display: true,
                                text: '测试次数'
                            }
                        }
                    },
                    plugins: {
                        legend: {
                            display: true
                        }
                    }
                }
            });
        }
        
        // 更新实验进展
        function updateExperimentProgress() {
            fetch('/api/experiment/progress')
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    updateProgressStats(data.data);
                    updateProgressChart(data.data);
                }
            })
            .catch(error => {
                console.error('获取实验进展失败:', error);
            });
        }
        
        // 更新进度统计
        function updateProgressStats(data) {
            if (data && data.length > 0) {
                const latest = data[data.length - 1];
                document.getElementById('currentStrategy').textContent = getStrategyName(latest.strategy);
                document.getElementById('testCount').textContent = latest.test_id || data.length;
                document.getElementById('knownRelations').textContent = latest.known_relations || 0;
                
                // 计算未知关系比例
                const totalPoints = 100; // 假设总点位数
                const totalRelations = totalPoints * (totalPoints - 1);
                const unknownRelations = totalRelations - (latest.known_relations || 0);
                const unknownRatio = (unknownRelations / totalRelations * 100).toFixed(1);
                document.getElementById('unknownRatio').textContent = unknownRatio + '%';
            }
        }
        
        // 更新进度图表
        function updateProgressChart(data) {
            if (!progressChart || !data) return;
            
            const labels = data.map((item, index) => index + 1);
            const values = data.map(item => item.known_relations || 0);
            
            progressChart.data.labels = labels;
            progressChart.data.datasets[0].data = values;
            progressChart.update();
        }
        
        // 获取策略名称
        function getStrategyName(strategy) {
            const strategyNames = {
                'adaptive_50': '50%集群策略',
                'adaptive_30': '30%集群策略',
                'adaptive_10': '10%集群策略',
                'binary_search': '二分法策略',
                'unknown': '未知策略'
            };
            return strategyNames[strategy] || strategy;
        }
        
        // 开始状态轮询
        function startStatusPolling() {
            if (!testRunning) return;
            
            refreshStatus();
            updateExperimentProgress();
            setTimeout(startStatusPolling, 2000);
        }
        
        // 监听配置变化
        document.addEventListener('change', function(e) {
            if (e.target.tagName === 'INPUT' || e.target.tagName === 'SELECT') {
                updateConfigDisplay();
            }
        });
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    """主页面"""
    return TEST_FRONTEND_HTML

@app.route('/api/config/preset/<preset_name>')
def get_preset_config(preset_name):
    """获取预设配置"""
    try:
        if preset_name not in PRESETS:
            return jsonify({'success': False, 'error': f'预设 {preset_name} 不存在'})
        
        config = get_config(preset_name)
        return jsonify({'success': True, 'config': config})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/system/status')
def get_system_status():
    """获取系统状态"""
    try:
        if tester is None:
            return jsonify({
                'success': True,
                'status': {
                    'state': 'idle',
                    'state_text': '未初始化',
                    'total_tests': 0,
                    'current_strategy': '未知',
                    'unknown_ratio': 100.0
                }
            })
        
        # 获取当前状态
        total_tests = tester.total_tests
        current_strategy = tester.get_strategy_name_by_ratio(tester.get_current_group_ratio())
        
        # 计算未知关系比例
        try:
            import requests
            response = requests.get("http://localhost:5000/api/system/info")
            if response.status_code == 200:
                system_info = response.json()
                if system_info.get('success'):
                    server_confirmed_count = system_info.get('confirmed_points_count', 0)
                    total_possible_relations = tester.total_points * (tester.total_points - 1)
                    unknown_ratio = (total_possible_relations - server_confirmed_count) / total_possible_relations * 100
                else:
                    unknown_ratio = 100.0
            else:
                unknown_ratio = 100.0
        except:
            unknown_ratio = 100.0
        
        return jsonify({
            'success': True,
            'status': {
                'state': 'running' if tester else 'idle',
                'state_text': '运行中' if tester else '未初始化',
                'total_tests': total_tests,
                'current_strategy': current_strategy,
                'unknown_ratio': unknown_ratio
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/system/init', methods=['POST'])
def initialize_system():
    """初始化系统"""
    global tester, test_config
    
    try:
        config_data = request.json
        test_config = config_data
        
        # 创建测试器实例
        tester = AdaptiveGroupingTester(test_config)
        
        return jsonify({'success': True, 'message': '系统初始化成功'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/system/reset', methods=['POST'])
def reset_system():
    """重置系统"""
    global tester, test_config
    
    try:
        tester = None
        test_config = None
        
        return jsonify({'success': True, 'message': '系统重置成功'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/test/start', methods=['POST'])
def start_test():
    """开始测试"""
    global tester
    
    try:
        if tester is None:
            return jsonify({'success': False, 'error': '系统未初始化'})
        
        # 在后台线程中运行测试
        import threading
        
        def run_test():
            try:
                tester.run_full_test_cycle()
            except Exception as e:
                print(f"测试运行错误: {e}")
        
        test_thread = threading.Thread(target=run_test)
        test_thread.daemon = True
        test_thread.start()
        
        return jsonify({'success': True, 'message': '测试已启动'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/test/stop', methods=['POST'])
def stop_test():
    """停止测试"""
    try:
        # 这里可以实现停止测试的逻辑
        # 由于测试在后台线程中运行，可以通过设置标志位来停止
        return jsonify({'success': True, 'message': '测试已停止'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/experiment/progress')
def get_experiment_progress():
    """获取实验进展数据"""
    try:
        if tester is None:
            return jsonify({'success': True, 'data': []})
        
        # 从主服务器获取测试进度数据
        import requests
        try:
            response = requests.get("http://localhost:5000/api/test/progress")
            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    return jsonify({'success': True, 'data': data.get('data', [])})
        except Exception as e:
            print(f"获取主服务器数据失败: {e}")
        
        # 如果主服务器不可用，返回本地数据
        progress_data = []
        for i, test_result in enumerate(tester.test_history):
            progress_data.append({
                'test_id': i + 1,
                'known_relations': len(tester.known_relations),
                'strategy': tester.get_strategy_name_by_ratio(tester.get_current_group_ratio()),
                'timestamp': time.time(),
                'connections_found': 0,
                'power_source': 0,
                'test_points_count': 0
            })
        
        return jsonify({'success': True, 'data': progress_data})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/results/export')
def export_results():
    """导出测试结果"""
    try:
        if tester is None:
            return jsonify({'success': False, 'error': '系统未初始化'})
        
        # 获取测试结果
        results = {
            'config': test_config,
            'test_summary': {
                'total_tests': tester.total_tests,
                'total_relay_operations': tester.performance_stats['total_relay_operations'],
                'total_test_time': tester.performance_stats['total_test_time'],
                'phase_test_counts': tester.phase_test_counts,
                'final_known_relations': len(tester.known_relations),
                'final_unknown_relations': len(tester.unknown_relations),
            },
            'group_history': tester.group_history,
            'power_source_usage': dict(tester.power_source_usage),
            'performance_stats': tester.performance_stats,
            'timestamp': time.time()
        }
        
        return jsonify({'success': True, 'results': results})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

if __name__ == '__main__':
    print("🚀 启动测试端服务器...")
    print("访问地址: http://localhost:5001")
    app.run(host='0.0.0.0', port=5001, debug=True)
