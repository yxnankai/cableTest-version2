from flask import Flask, request, jsonify, render_template_string
from flask_cors import CORS
# from flask_socketio import SocketIO, emit  # 暂时禁用WebSocket
from core.cable_test_system import CableTestSystem, TestResult, RelayState
from core import config
import json
import time
from typing import Dict, Any, List
import threading
import queue

app = Flask(__name__)
app.config['SECRET_KEY'] = 'cable_test_secret_key'
CORS(app)
# socketio = SocketIO(app, cors_allowed_origins="*")  # 暂时禁用WebSocket

class WebFlaskTestServer:
    def __init__(self, total_points: int = None):
        # 使用配置文件中的点位数量，如果没有指定的话
        if total_points is None:
            # 获取测试环境配置（100个点位）
            test_config = config.get_config('testing')
            total_points = test_config.TOTAL_POINTS
        
        self.test_system = CableTestSystem(total_points=total_points)
        self.current_point_states = {}
        self.confirmed_clusters = []
        self.test_history = []
        self.active_experiments = {}
        self._update_current_states()
        self.confirmed_clusters = self.test_system.get_confirmed_clusters()
        
        # 启动状态更新线程
        self.status_update_thread = threading.Thread(target=self._status_update_loop, daemon=True)
        self.status_update_thread.start()
    
    def _calculate_default_conductivity_distribution(self, total_points: int) -> Dict[int, int]:
        """
        计算默认的导通分布
        
        Args:
            total_points: 总点位数
            
        Returns:
            Dict[int, int]: 导通分布字典 {导通数量: 点位数量}
        """
        # 🔧 新的比例设置：1个(90%), 2个(6%), 3个(3%), 4个(1%)
        percentages = {
            1: 0.90,  # 90%
            2: 0.06,  # 6%
            3: 0.03,  # 3%
            4: 0.01   # 1%
        }
        
        # 根据比例计算实际数量
        distribution = {}
        total_assigned = 0
        
        # 先按比例分配，除了最大的那个
        for conductivity_count in [4, 3, 2]:  # 从小到大分配
            count = round(total_points * percentages[conductivity_count])
            distribution[conductivity_count] = count
            total_assigned += count
        
        # 剩余的全部分配给1个导通的点位
        distribution[1] = total_points - total_assigned
        
        return distribution
    
    def _update_current_states(self):
        """更新当前点位状态缓存"""
        self.current_point_states = {}
        all_points = self.test_system.get_all_point_states()
        for point_id, point in all_points.items():
            self.current_point_states[point_id] = point.relay_state.value
    
    def _update_clusters_from_test(self, test_result: TestResult):
        """根据测试结果更新点位状态和点对关系信息"""
        # 更新所有点位状态 - 确保统计准确
        self._update_current_states()
        
        # 添加到测试历史
        test_record = {
            'timestamp': time.time(),
            'test_id': len(self.test_history) + 1,
            'power_source': test_result.power_source,
            'test_points': [p for p in test_result.active_points if p != test_result.power_source],  # 排除电源点位
            'connections_found': len(test_result.detected_connections),
            'duration': test_result.test_duration,
            'relay_operations': test_result.relay_operations,
            'power_on_operations': getattr(test_result, 'power_on_operations', 0)
        }
        self.test_history.append(test_record)
        
        print(f"添加测试记录: {test_record}")
        print(f"  电源点位: {test_result.power_source}")
        print(f"  测试点位: {[p for p in test_result.active_points if p != test_result.power_source]}")
        print(f"  继电器操作: {test_result.relay_operations}")
        print(f"  当前激活点位: {test_result.active_points}")
        # 🔧 重要：显示正确的继电器状态，而不是空的 current_point_states
        relay_states = self.test_system.relay_manager.relay_states
        active_relay_states = {k: v.value for k, v in relay_states.items() if v.value == 1}
        print(f"  当前继电器状态: {active_relay_states}")
        # 追加：每次试验完成后的线缆拓扑简报
        try:
            un = self.test_system.get_unconfirmed_cluster_relationships() or {}
            s = (un.get('summary') or {})
            print("—— 试验后状态简报 ——")
            print(
                                 f"已确认连接组: {len(self.confirmed_clusters)} | 未确认点位: {s.get('total_unconfirmed_points', 0)} | "
                                 f"未确认连接组关系: {s.get('total_unconfirmed_cluster_relationships', 0)} | 未确认点位关系: {s.get('total_unconfirmed_point_relationships', 0)} | "
                f"未确认点位间关系: {s.get('total_unconfirmed_point_to_point_relationships', 0)} | 总测试: {len(self.test_history)}"
            )
        except Exception as _e:
            print("状态简报生成失败:", _e)
        
        # 更新确认的点对关系信息 - 包括跨连接组导通测试
        print("开始更新点对关系信息...")
        self.confirmed_clusters = self.test_system.get_confirmed_clusters()
        print(f"点对关系信息更新完成，当前确认连接组数: {len(self.confirmed_clusters)}")
        
        # 通过WebSocket发送实时更新
        self._emit_status_update()
    
    def _emit_status_update(self):
        """通过WebSocket发送状态更新"""
        try:
            # socketio.emit('status_update', {  # 暂时禁用WebSocket
            #     'point_states': self.current_point_states,
            #     'clusters': self.confirmed_clusters,  # 已经是字典格式
            #     'test_history': self.test_history[-10:],  # 最近10次测试
            #     'timestamp': time.time()
            # })
            pass  # 暂时禁用WebSocket
        except Exception as e:
            print(f"WebSocket发送失败: {e}")
    
    def _status_update_loop(self):
        """状态更新循环"""
        while True:
            try:
                time.sleep(2)  # 每2秒更新一次
                self._emit_status_update()
            except Exception as e:
                print(f"状态更新循环错误: {e}")
    
    def get_point_status(self, point_id: int = None) -> Dict[str, Any]:
        """获取点位状态"""
        if point_id is not None:
            if point_id in self.current_point_states:
                return {
                    'success': True,
                    'point_id': point_id,
                    'state': self.current_point_states[point_id],
                    'timestamp': time.time()
                }
            else:
                return {'success': False, 'error': f'点位 {point_id} 不存在'}
        
        return {
            'success': True,
            'total_points': len(self.current_point_states),
            'point_states': self.current_point_states,
            'timestamp': time.time()
        }
    
    def get_cluster_info(self) -> Dict[str, Any]:
        """获取点对关系信息"""
        return {
            'success': True,
            'total_clusters': len(self.confirmed_clusters),
            'clusters': self.confirmed_clusters,  # 兼容旧结构：此处已为空
            'timestamp': time.time()
        }
    
    def run_experiment(self, experiment_config: Dict[str, Any]) -> Dict[str, Any]:
        """运行实验（后端不做策略判定，按请求执行；策略由客户端基于服务端状态自行判断）"""
        try:
            power_source = experiment_config.get('power_source')
            test_points = experiment_config.get('test_points', [])
            
            if power_source is None:
                return {'success': False, 'error': '缺少电源点位参数'}
            
            # 运行测试（保持客户端请求原样执行）
            test_result = self.test_system.run_single_test(power_source, test_points)
            
            # 更新状态
            self._update_clusters_from_test(test_result)
            
            return {
                'success': True,
                'data': {
                    'test_result': {
                        'power_source': test_result.power_source,
                        'test_points': test_result.active_points,
                        'connections': [c.__dict__ for c in test_result.detected_connections],
                        'duration': test_result.test_duration,
                        'relay_operations': test_result.relay_operations,
                        'power_on_operations': getattr(test_result, 'power_on_operations', 0),
                        'timestamp': time.time()
                    }
                }
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def get_system_info(self) -> Dict[str, Any]:
        """获取系统信息"""
        # 🔧 重要：统一数据源，直接使用 CableTestSystem 的数据，避免不一致
        # 使用 CableTestSystem 的 test_history 而不是 WebFlaskTestServer 的独立 test_history
        try:
            total_power_on_ops = 0
            for tr in self.test_system.test_history:
                # CableTestSystem.test_history 存储的是 TestResult 对象
                total_power_on_ops += int(getattr(tr, 'power_on_operations', 0) or 0)
        except Exception:
            total_power_on_ops = 0
        
        # 获取新的统计信息
        confirmed_points_count = self.test_system.get_confirmed_points_count()
        detected_conductive_count = self.test_system.get_detected_conductive_count()
        confirmed_non_conductive_count = self.test_system.get_confirmed_non_conductive_count()
        
        return {
            'success': True,
            'total_points': self.test_system.total_points,
            'relay_switch_time': self.test_system.relay_switch_time,
            'total_tests': len(self.test_system.test_history),  # 使用 CableTestSystem 的测试历史
            'total_relay_operations': self.test_system.relay_operation_count,  # 使用 CableTestSystem 的继电器计数
            'total_power_on_operations': total_power_on_ops,
            'confirmed_points_count': confirmed_points_count,  # 已确认点位关系总数
            'detected_conductive_count': detected_conductive_count,  # 检测到的导通关系数量
            'confirmed_non_conductive_count': confirmed_non_conductive_count,  # 确认的不导通关系数量
            'timestamp': time.time()
        }

    def get_test_progress(self) -> Dict[str, Any]:
        """获取实验进度数据"""
        try:
            # 获取测试历史
            test_history = self.test_system.test_history
            
            # 构建进度数据
            progress_data = []
            current_known_relations = 0
            
            for i, test_result in enumerate(test_history):
                # 计算当前测试后的已知关系数量
                # 这里需要根据测试结果更新已知关系数量
                # 由于每次测试可能发现多个关系，我们需要累加
                
                # 获取当前测试发现的连接数量
                connections_found = len(test_result.detected_connections)
                current_known_relations += connections_found
                
                # 确定当前使用的策略
                # 这里需要根据测试的特征来判断策略
                strategy = self._determine_test_strategy(test_result)
                
                progress_data.append({
                    'test_id': i + 1,
                    'known_relations': current_known_relations,
                    'strategy': strategy,
                    'timestamp': test_result.timestamp if hasattr(test_result, 'timestamp') else time.time(),
                    'connections_found': connections_found,
                    'power_source': test_result.power_source,
                    'test_points_count': len(test_result.active_points) - 1  # 排除电源点位
                })
            
            return {
                'success': True,
                'data': progress_data,
                'timestamp': time.time()
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def _determine_test_strategy(self, test_result) -> str:
        """根据测试结果确定使用的策略"""
        try:
            # 根据测试点位数量来判断策略
            test_points_count = len(test_result.active_points) - 1  # 排除电源点位
            total_points = self.test_system.total_points
            
            # 计算测试点位占总点位的比例
            if test_points_count == 0:
                return 'unknown'
            
            ratio = test_points_count / total_points
            
            # 根据比例判断策略
            if ratio > 0.25:  # 大于25%
                return 'phase_1'  # 30%集群策略
            elif ratio > 0.15:  # 15%-25%
                return 'phase_2'  # 20%集群策略
            elif ratio > 0.05:  # 5%-15%
                return 'phase_3'  # 10%集群策略
            else:  # 小于5%
                return 'binary_search'  # 二分法策略
        except Exception:
            return 'unknown'

    # ============== 新增：点-点关系接口封装 ==============
    def get_relationship_summary(self) -> Dict[str, Any]:
        try:
            data = self.test_system.get_relationship_summary()
            return {'success': True, 'data': data, 'timestamp': time.time()}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def get_conductive_pairs(self) -> Dict[str, Any]:
        try:
            items = self.test_system.get_confirmed_conductive_pairs()
            return {'success': True, 'data': {'items': items, 'total': len(items)}, 'timestamp': time.time()}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def get_non_conductive_pairs(self) -> Dict[str, Any]:
        try:
            items = self.test_system.get_confirmed_non_conductive_pairs()
            return {'success': True, 'data': {'items': items, 'total': len(items)}, 'timestamp': time.time()}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def get_unconfirmed_pairs(self) -> Dict[str, Any]:
        try:
            items = self.test_system.get_unconfirmed_pairs()
            return {'success': True, 'data': {'items': items, 'total': len(items)}, 'timestamp': time.time()}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def get_point_relationships(self, point_id: int) -> Dict[str, Any]:
        """获取指定点位的导通关系"""
        try:
            relationships = self.test_system.get_point_relationships(point_id)
            if 'error' in relationships:
                return {'success': False, 'error': relationships['error']}
            return {'success': True, 'data': relationships, 'timestamp': time.time()}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def get_relationship_matrix(self) -> Dict[str, Any]:
        """获取完整的关系矩阵"""
        try:
            matrix = self.test_system.get_relationship_matrix()
            return {'success': True, 'data': {'matrix': matrix, 'total_points': len(matrix)}, 'timestamp': time.time()}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def get_true_relationship_matrix(self) -> Dict[str, Any]:
        """获取真实关系矩阵"""
        try:
            matrix = self.test_system.get_true_relationship_matrix()
            return {'success': True, 'data': {'matrix': matrix, 'total_points': len(matrix)}, 'timestamp': time.time()}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def get_relationship_matrices_comparison(self) -> Dict[str, Any]:
        """获取检测到的关系矩阵与真实关系矩阵的对比"""
        try:
            comparison = self.test_system.get_relationship_matrices_comparison()
            return {'success': True, 'data': comparison, 'timestamp': time.time()}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def get_real_conductive_points(self, point_id: int) -> Dict[str, Any]:
        """获取指定点位的真实导通点位信息"""
        try:
            info = self.test_system.get_real_conductive_points(point_id)
            if 'error' in info:
                return {'success': False, 'error': info['error']}
            return {'success': True, 'data': info, 'timestamp': time.time()}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def get_all_real_conductive_info(self) -> Dict[str, Any]:
        """获取所有点位的真实导通信息概览"""
        try:
            info = self.test_system.get_all_real_conductive_info()
            return {'success': True, 'data': info, 'timestamp': time.time()}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def reset_system(self) -> Dict[str, Any]:
        """重置系统，支持前端传参控制导通分布。
        接收 JSON: { total_points?: int, conductivity_distribution?: Dict[int, int] }
        """
        try:
            try:
                payload = request.get_json(silent=True) or {}
            except Exception:
                payload = {}
            
            total_points = payload.get('total_points')
            
            # 🔧 重要修改：使用动态计算的默认导通分布
            if 'conductivity_distribution' in payload:
                conductivity_distribution = payload['conductivity_distribution']
            else:
                # 如果没有指定分布，使用动态计算的默认分布
                default_total_points = total_points or self.test_system.total_points
                conductivity_distribution = self._calculate_default_conductivity_distribution(default_total_points)
            
            # 重置系统
            self.test_system.reset_and_regenerate_with_distribution(total_points, conductivity_distribution)
            self._update_current_states()
            self.confirmed_clusters = self.test_system.get_confirmed_clusters()
            self.test_history.clear()
            
            # 通过WebSocket发送状态更新
            self._emit_status_update()
            
            return {
                'success': True,
                'message': '系统已重置并重新生成随机连接关系',
                'total_points': self.test_system.total_points,
                'conductivity_distribution': conductivity_distribution,
                'timestamp': time.time()
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def get_real_clusters(self) -> Dict[str, Any]:
        """获取真实连接点对关系信息"""
        try:
            real_clusters = self.test_system.get_real_clusters()
            return {
                'success': True,
                'real_clusters': real_clusters,
                'total_real_clusters': len(real_clusters),
                'timestamp': time.time()
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def get_cluster_comparison(self) -> Dict[str, Any]:
        """获取连接点位对比信息"""
        try:
            comparison = self.test_system.get_cluster_comparison()
            return {
                'success': True,
                'comparison': comparison,
                'timestamp': time.time()
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def get_test_history(self, limit: int = 50) -> Dict[str, Any]:
        """获取测试历史"""
        return {
            'success': True,
            'test_history': self.test_history[-limit:],
            'total_tests': len(self.test_history),
            'timestamp': time.time()
        }
    
    def get_detailed_cluster_info(self) -> Dict[str, Any]:
        """获取详细的点对关系信息（返回原始数据体，路由层再统一 success 包装）"""
        try:
            detailed_info = self.test_system.get_detailed_cluster_info()
            return detailed_info
        except Exception as e:
            # 由路由层包装错误
            raise e
    
    def get_cluster_visualization(self) -> Dict[str, Any]:
        """获取连接组可视化数据"""
        try:
            viz_data = self.test_system.get_cluster_visualization_data()
            return {
                'success': True,
                'data': viz_data,
                'timestamp': time.time()
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def get_unconfirmed_cluster_relationships(self) -> Dict[str, Any]:
        """获取未确认关系（返回原始数据体，路由层再统一 success 包装）"""
        try:
            unconfirmed_info = self.test_system.get_unconfirmed_cluster_relationships()
            return unconfirmed_info
        except Exception as e:
            raise e

# 创建服务器实例
server = WebFlaskTestServer()

# HTML模板
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>线缆测试系统 - 实时监控</title>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.0.1/socket.io.js"></script>
    <!-- 暂时禁用WebSocket -->
    <!-- <script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.0.1/socket.io.js"></script> -->
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/chartjs-adapter-date-fns@3.0.0/dist/chartjs-adapter-date-fns.bundle.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/chartjs-plugin-annotation@3.0.1/dist/chartjs-plugin-annotation.min.js"></script>
    <style>
        body { font-family: 'Microsoft YaHei', Arial, sans-serif; margin: 0; padding: 20px; background: #f5f5f5; }
        .container { max-width: 1400px; margin: 0 auto; }
        .header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; border-radius: 10px; margin-bottom: 20px; }
        .header h1 { margin: 0; font-size: 2.5em; }
        .header p { margin: 10px 0 0 0; opacity: 0.9; }
        
        .dashboard { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 20px; }
        .card {
            background: white;
            border-radius: 8px;
            padding: 20px;
            margin-bottom: 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .card h3 { margin-top: 0; color: #333; border-bottom: 2px solid #667eea; padding-bottom: 10px; }
        
        .status-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(80px, 1fr)); gap: 5px; max-height: 300px; overflow-y: auto; }
        .status-item { padding: 8px; text-align: center; border-radius: 5px; font-size: 12px; font-weight: bold; }
        .status-on { background: #4CAF50; color: white; }
        .status-off { background: #f44336; color: white; }
        
        .experiment-form { background: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); margin-bottom: 20px; }
        .form-group { margin-bottom: 15px; }
        .form-group label { display: block; margin-bottom: 5px; font-weight: bold; color: #333; }
        .form-group input, .form-group textarea { width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 5px; font-size: 14px; }
        .btn { background: #667eea; color: white; padding: 12px 24px; border: none; border-radius: 5px; cursor: pointer; font-size: 16px; }
        .btn:hover { background: #5a6fd8; }
        .btn:disabled { background: #ccc; cursor: not-allowed; }
        
        .test-history { max-height: 400px; overflow-y: auto; }
        .test-item { background: #f9f9f9; padding: 15px; margin-bottom: 10px; border-radius: 5px; border-left: 4px solid #667eea; }
        .test-item h4 { margin: 0 0 10px 0; color: #333; }
        .test-meta { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 10px; font-size: 14px; }
        .test-meta span { background: #e3f2fd; padding: 5px 10px; border-radius: 3px; }
        
        .real-time { background: #e8f5e8; border-left-color: #4CAF50; }
        .loading { text-align: center; padding: 20px; color: #666; }
        
        .test-record {
            border: 1px solid #e0e0e0;
            border-radius: 6px;
            padding: 15px;
            margin-bottom: 15px;
            background: #fafafa;
        }

        .test-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 10px;
            padding-bottom: 8px;
            border-bottom: 1px solid #e0e0e0;
        }

        .test-time {
            font-size: 12px;
            color: #666;
        }

        .test-details {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 8px;
            font-size: 14px;
        }

        .connected {
            color: #4CAF50;
            font-weight: bold;
        }

        .disconnected {
            color: #f44336;
            font-weight: bold;
        }

        .no-data {
            text-align: center;
            color: #666;
            font-style: italic;
            padding: 20px;
        }
        
        @media (max-width: 768px) {
            .dashboard { grid-template-columns: 1fr; }
            .status-grid { grid-template-columns: repeat(auto-fill, minmax(60px, 1fr)); }
        }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🔌 线缆测试系统</h1>
            <p>实时监控继电器状态、点对关系信息和测试进度</p>
        </div>
        
        <div class="experiment-form">
            <h3>🧪 实验设置</h3>
            <div class="form-group">
                <label for="powerSource">电源点位:</label>
                <input type="number" id="powerSource" placeholder="输入电源点位ID (0-99)" min="0" max="99">
            </div>
            <div class="form-group">
                <label for="testPoints">测试点位 (可选):</label>
                <textarea id="testPoints" name="testPoints" rows="3" 
                          placeholder="输入测试点位ID,用逗号分隔,支持范围选择(如: 5-15),留空则测试所有点位"></textarea>
                <small style="color: #666; display: block; margin-top: 5px;">
                    使用示例: "1,3,5" 或 "10-15" 或 "1,5-8,20" 或留空测试所有点位
                </small>
            </div>
            <div style="margin-top: 15px;">
                <button class="btn" onclick="runExperiment()">开始实验</button>
                <button class="btn" onclick="runRandomExperiment()" style="background: #ff9800; margin-left: 10px;">随机实验</button>
            </div>
            <div class="form-group" style="margin-top: 10px; display: flex; gap: 8px; align-items: center; flex-wrap: wrap;">
                <label>总点位:</label>
                <input type="number" id="totalPoints" placeholder="总点位 (>=2)" min="2" value="100" style="width: 120px;" onchange="updateConductivityDefaults()" />
                <label>导通分布设置:</label>
                <div style="display: flex; gap: 4px; align-items: center;">
                    <span>1个:</span>
                    <input type="number" id="conductivity1" placeholder="数量" min="0" value="90" style="width: 60px;" />
                    <span>2个:</span>
                    <input type="number" id="conductivity2" placeholder="数量" min="0" value="6" style="width: 60px;" />
                    <span>3个:</span>
                    <input type="number" id="conductivity3" placeholder="数量" min="0" value="3" style="width: 60px;" />
                    <span>4个:</span>
                    <input type="number" id="conductivity4" placeholder="数量" min="0" value="1" style="width: 60px;" />
                </div>
                <small style="color: #666; display: block; margin-top: 5px;">
                    说明：数字表示除自己以外，作为通电点位时能够导通的其他点位数量
                </small>
                <button class="btn" onclick="resetSystem()" style="background: #f44336;">重置系统</button>
            </div>
        </div>
        
        <div class="dashboard">
            <div class="card">
                <h3>📊 系统状态</h3>
                <div id="systemInfo">
                    <div class="loading">加载中...</div>
                </div>
            </div>
            
            <div class="card">
                <h3>🔗 点对关系信息</h3>
                <div id="clusterInfo">
                    <div class="loading">加载中...</div>
                </div>
                <div style="margin-top: 15px;">
                    <button class="btn" onclick="showDetailedClusters()" style="background: #2196F3; padding: 8px 16px; font-size: 14px;">
                        详细点对信息
                    </button>
                    
                    <button class="btn" onclick="showConfirmedNonConductive()" style="background: #795548; padding: 8px 16px; font-size: 14px;">
                        已确认不导通
                    </button>
                    
                    <button class="btn" onclick="showRelationshipMatrix()" style="background: #00BCD4; padding: 8px 16px; font-size: 14px;">
                        检测到的关系矩阵
                    </button>
                    
                    <button class="btn" onclick="showTrueRelationshipMatrix()" style="background: #E91E63; padding: 8px 16px; font-size: 14px;">
                        真实关系矩阵
                    </button>
                    
                    <button class="btn" onclick="showMatricesComparison()" style="background: #9C27B0; padding: 8px 16px; font-size: 14px;">
                        矩阵对比
                    </button>
                    
                    <button class="btn" onclick="showRealConductiveInfo()" style="background: #FF9800; padding: 8px 16px; font-size: 14px;">
                        真实导通点位信息
                    </button>
                </div>
            </div>
        </div>
        
        <div class="card">
            <h3>📍 点位状态概览</h3>
            <div id="pointStatus">
                <div class="loading">加载中...</div>
            </div>
        </div>
        
        <div class="card">
            <h3>📈 实验进度图表</h3>
            <div id="progressChart" style="height: 400px; width: 100%;">
                <div class="loading">加载中...</div>
            </div>
            <div style="margin-top: 10px; text-align: center;">
                <button class="btn" onclick="refreshProgressChart()" style="background: #4CAF50; padding: 8px 16px; font-size: 14px;">
                    刷新图表
                </button>
                <button class="btn" onclick="exportChartData()" style="background: #FF9800; padding: 8px 16px; font-size: 14px; margin-left: 10px;">
                    导出数据
                </button>
            </div>
        </div>
        
        <div class="card">
            <h3>📈 测试历史</h3>
            <div id="testHistory" class="test-history">
                <div class="loading">加载中...</div>
            </div>
        </div>
    </div>

    <script>
        // const socket = io();  // 暂时禁用WebSocket
        let lastUpdate = 0;
        let fallbackIntervalId = null; // 轮询模式定时器ID
        let progressChart = null; // 进度图表实例
        let chartData = []; // 图表数据
        let strategyColors = {
            'phase_1': '#FF6384', // 30%集群策略 - 红色
            'phase_2': '#36A2EB', // 20%集群策略 - 蓝色
            'phase_3': '#FFCE56', // 10%集群策略 - 黄色
            'binary_search': '#4BC0C0' // 二分法策略 - 青色
        };
        
        // 连接组ID到短名称的映射，保持会话内稳定
        const clusterIdToShortName = {};
        function getShortClusterName(clusterId) {
            if (!clusterId) return '';
            if (clusterIdToShortName[clusterId]) return clusterIdToShortName[clusterId];
            const nextIndex = Object.keys(clusterIdToShortName).length + 1;
            const shortName = `连接组 ${nextIndex}`;
            clusterIdToShortName[clusterId] = shortName;
            return shortName;
        }
        
        // 连接状态处理
        // socket.on('connect', () => {
        //     console.log('WebSocket已连接');
        //     loadInitialData();
        // });
        
        // socket.on('disconnect', () => {
        //     console.log('WebSocket连接断开');
        //     startFallbackPolling();
        // });

        // // 连接失败时启用兜底轮询
        // socket.on('connect_error', (err) => {
        //     console.warn('WebSocket连接失败，启用轮询模式', err);
        //     startFallbackPolling();
        // });
        
        // // 处理WebSocket错误
        // socket.on('error', (err) => {
        //     console.error('WebSocket错误:', err);
        //     startFallbackPolling();
        // });
        
        // 直接加载初始数据，不使用WebSocket
        console.log('直接加载初始数据...');
        loadInitialData();
        
        // 实时状态更新
        // socket.on('status_update', (data) => {
        //     lastUpdate = Date.now();
        //     console.log('收到WebSocket更新:', data);
        //     
        //     if (data.point_states) {
        //         updatePointStatus(data.point_states);
        //     }
        //     if (data.clusters) {
        //         updateClusterInfo(data.clusters);
        //     }
        //     if (data.test_history) {
        //         updateTestHistory(data.test_history);
        //     }
        //     
        //     // 刷新系统信息
        //     refreshSystemInfo();
        //     
        //     // 更新进度图表
        //     updateProgressChart();

        //     // 收到实时数据后，若在轮询模式则停止轮询
        //     if (fallbackIntervalId) {
        //         clearInterval(fallbackIntervalId);
        //         fallbackIntervalId = null;
        //     }
        // });
        
        // 刷新系统信息
        async function refreshSystemInfo() {
            try {
                const response = await fetch('/api/system/info');
                const data = await response.json();
                updateSystemInfo(data);
            } catch (error) {
                console.error('刷新系统信息失败:', error);
            }
        }
        
        // 加载初始数据
        async function loadInitialData() {
            try {
                console.log('开始加载初始数据...');
                
                // 逐个测试API调用，避免一个失败影响全部
                let systemInfo = null;
                let clusterInfo = null;
                let pointStatus = null;
                let testHistory = null;
                let unconfirmed = null;
                
                try {
                    console.log('获取系统信息...');
                    const response = await fetch('/api/system/info?ts='+Date.now());
                    if (response.ok) {
                        systemInfo = await response.json();
                        console.log('系统信息获取成功:', systemInfo);
                    } else {
                        console.error('系统信息API失败:', response.status, response.statusText);
                    }
                } catch (e) {
                    console.error('获取系统信息失败:', e);
                }
                
                try {
                    console.log('获取集群信息...');
                    const response = await fetch('/api/clusters?ts='+Date.now());
                    if (response.ok) {
                        clusterInfo = await response.json();
                        console.log('集群信息获取成功:', clusterInfo);
                    } else {
                        console.error('集群信息API失败:', response.status, response.statusText);
                    }
                } catch (e) {
                    console.error('获取集群信息失败:', e);
                }
                
                try {
                    console.log('获取点位状态...');
                    const response = await fetch('/api/points/status?ts='+Date.now());
                    if (response.ok) {
                        pointStatus = await response.json();
                        console.log('点位状态获取成功:', pointStatus);
                    } else {
                        console.error('点位状态API失败:', response.status, response.statusText);
                    }
                } catch (e) {
                    console.error('获取点位状态失败:', e);
                }
                
                try {
                    console.log('获取测试历史...');
                    const response = await fetch('/api/test/history?page=1&page_size=50&ts='+Date.now());
                    if (response.ok) {
                        testHistory = await response.json();
                        console.log('测试历史获取成功:', testHistory);
                    } else {
                        console.error('测试历史API失败:', response.status, response.statusText);
                    }
                } catch (e) {
                    console.error('获取测试历史失败:', e);
                }
                
                try {
                    console.log('获取未确认关系...');
                    const response = await fetch('/api/clusters/unconfirmed_relationships?ts='+Date.now());
                    if (response.ok) {
                        unconfirmed = await response.json();
                        console.log('未确认关系获取成功:', unconfirmed);
                    } else {
                        console.error('未确认关系API失败:', response.status, response.statusText);
                    }
                } catch (e) {
                    console.error('获取未确认关系失败:', e);
                }
                
                console.log('所有API调用完成，开始处理数据...');
                
                // 拓扑是否已完成
                let topoDoneInit = false;
                try {
                    const s = (unconfirmed && unconfirmed.data && unconfirmed.data.summary) || {};
                    topoDoneInit = (
                        (s.total_unconfirmed_points || 0) === 0 &&
                        (s.total_unconfirmed_cluster_relationships || 0) === 0 &&
                        (s.total_unconfirmed_point_relationships || 0) === 0 &&
                        (s.total_unconfirmed_point_to_point_relationships || 0) === 0
                    );
                } catch (_) {}
                
                if (systemInfo) {
                    systemInfo.__topologyDone = topoDoneInit;
                    updateSystemInfo(systemInfo);
                }
                
                if (clusterInfo) {
                    updateClusterInfo(clusterInfo.clusters || []);
                }
                
                if (pointStatus) {
                    updatePointStatus(pointStatus.point_states || {});
                }
                
                // 历史归档：完成后也保留历史
                if (testHistory && testHistory.success && testHistory.data) {
                    renderHistoryItems(testHistory.data.items || []);
                } else if (testHistory) {
                    updateTestHistory(testHistory.test_history || []);
                }
                
                console.log('初始数据加载完成');
                
                // 初始化并更新进度图表
                console.log('开始初始化图表...');
                initProgressChart();
                await updateProgressChart();
                console.log('图表初始化完成');
                
            } catch (error) {
                console.error('加载初始数据失败:', error);
                // 显示错误信息给用户
                document.querySelectorAll('.loading').forEach(el => {
                    el.innerHTML = '加载失败，请刷新页面重试';
                });
            }
        }

        // 兜底轮询：每5秒刷新一次关键数据
        function startFallbackPolling() {
            if (fallbackIntervalId) return; // 已在轮询
            fallbackIntervalId = setInterval(async () => {
                try {
                    await loadInitialData();
                } catch (e) {
                    console.error('轮询刷新失败:', e);
                }
            }, 5000);
        }
        
        // 初始化进度图表
        function initProgressChart() {
            const ctx = document.getElementById('progressChart');
            if (!ctx) {
                console.error('找不到图表容器');
                return;
            }
            
            // 销毁现有图表
            if (progressChart) {
                progressChart.destroy();
            }
            
            progressChart = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: [],
                    datasets: [{
                        label: '已知关系数量',
                        data: [],
                        borderColor: '#4CAF50',
                        backgroundColor: 'rgba(76, 175, 80, 0.1)',
                        borderWidth: 2,
                        fill: true,
                        tension: 0.1
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        title: {
                            display: true,
                            text: '实验进度 - 已知关系数量变化'
                        },
                        legend: {
                            display: true
                        },
                        tooltip: {
                            mode: 'index',
                            intersect: false,
                            callbacks: {
                                afterBody: function(context) {
                                    const dataIndex = context[0].dataIndex;
                                    const dataPoint = chartData[dataIndex];
                                    if (dataPoint && dataPoint.strategy) {
                                        return `策略: ${getStrategyName(dataPoint.strategy)}`;
                                    }
                                    return '';
                                }
                            }
                        }
                    },
                    scales: {
                        x: {
                            title: {
                                display: true,
                                text: '实验序号'
                            }
                        },
                        y: {
                            title: {
                                display: true,
                                text: '已知关系数量'
                            },
                            beginAtZero: true
                        }
                    },
                    interaction: {
                        mode: 'nearest',
                        axis: 'x',
                        intersect: false
                    }
                }
            });
            
            console.log('图表初始化完成');
        }
        
        // 获取策略名称
        function getStrategyName(strategy) {
            const strategyNames = {
                'phase_1': '30%集群策略',
                'phase_2': '20%集群策略', 
                'phase_3': '10%集群策略',
                'binary_search': '二分法策略'
            };
            return strategyNames[strategy] || strategy;
        }
        
        // 更新进度图表
        async function updateProgressChart() {
            try {
                const response = await fetch('/api/test/progress');
                const data = await response.json();
                
                if (data.success && data.data) {
                    chartData = data.data;
                    
                    // 准备图表数据
                    const labels = chartData.map((item, index) => index + 1);
                    const values = chartData.map(item => item.known_relations);
                    
                    // 更新图表
                    if (progressChart) {
                        progressChart.data.labels = labels;
                        progressChart.data.datasets[0].data = values;
                        progressChart.update();
                        
                        console.log(`图表更新完成，数据点: ${chartData.length}`);
                    }
                } else {
                    console.warn('获取进度数据失败:', data.error || '未知错误');
                }
            } catch (error) {
                console.error('更新进度图表失败:', error);
            }
        }
        
        // 刷新进度图表
        function refreshProgressChart() {
            updateProgressChart();
        }
        
        // 导出图表数据
        function exportChartData() {
            if (chartData.length === 0) {
                alert('暂无数据可导出');
                return;
            }
            
            const csvContent = [
                ['实验序号', '已知关系数量', '策略', '时间戳'],
                ...chartData.map((item, index) => [
                    index + 1,
                    item.known_relations,
                    getStrategyName(item.strategy),
                    new Date(item.timestamp * 1000).toLocaleString('zh-CN')
                ])
            ].map(row => row.join(',')).join('\n');
            
            const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
            const link = document.createElement('a');
            const url = URL.createObjectURL(blob);
            link.setAttribute('href', url);
            link.setAttribute('download', `实验进度数据_${new Date().toISOString().slice(0, 19).replace(/:/g, '-')}.csv`);
            link.style.visibility = 'hidden';
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
        }
        
                 // 更新系统信息
        function updateSystemInfo(data) {
            console.log('更新系统信息:', data);
            
            if (!data) {
                console.error('系统信息数据为空');
                return;
            }
            
            if (data.success === false) {
                console.error('系统信息API返回失败:', data.error);
                return;
            }
            
            const totalPowerOns = data.total_power_on_operations ?? 0;
            const container = document.getElementById('systemInfo');
            
            if (container) {
                container.innerHTML = `
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 15px;">
                        <div><strong>总点位:</strong> ${(data.total_points || 0).toLocaleString()}</div>
                        <div><strong>继电器切换时间:</strong> ${((data.relay_switch_time || 0) * 1000).toFixed(1)}ms</div>
                        <div><strong>当前已确认的点位关系数:</strong> ${data.confirmed_points_count || 0}</div>
                        <div><strong>检测到的导通关系:</strong> ${data.detected_conductive_count || 0}</div>
                        <div><strong>总测试次数:</strong> ${data.total_tests || 0}</div>
                        <div><strong>继电器操作总次数:</strong> ${data.total_relay_operations || 0}</div>
                        <div><strong>通电次数总和:</strong> ${totalPowerOns}</div>
                        <div><strong>系统状态:</strong> <span style="color: #4CAF50;">运行中</span></div>
                        ${data.__topologyDone ? '<div style="grid-column:1 / span 2; color:#4CAF50; font-weight:600;">✅ 所有关系已确认完成</div>' : ''}
                    </div>
                `;
                console.log('系统信息更新完成');
            } else {
                console.error('找不到系统信息容器');
            }
        }
        
                 // 更新点对关系信息
        function updateClusterInfo(clusters) {
            console.log('更新集群信息:', clusters);
            
            const container = document.getElementById('clusterInfo');
            if (!container) {
                console.error('找不到集群信息容器');
                return;
            }
            
            if (!clusters || clusters.length === 0) {
                container.innerHTML = '<p style="color: #666;">暂无点对关系信息</p>';
                console.log('集群信息为空');
                return;
            }
            
            container.innerHTML = clusters.map(cluster => `
                <div style="background: #f0f8ff; padding: 10px; margin-bottom: 10px; border-radius: 5px;" title="${cluster.cluster_id || ''}">
                    <strong>${getShortClusterName(cluster.cluster_id)}</strong> | 
                    <strong>点位:</strong> [${cluster.points.join(', ')}] | 
                    <strong>点位数量:</strong> ${cluster.point_count} | 
                    <strong>状态:</strong> <span style="color: #4CAF50;">已确认</span>
                </div>
            `).join('');
            console.log('集群信息更新完成');
        }
        
                 // 更新点位状态
        function updatePointStatus(pointStates) {
            console.log('更新点位状态:', pointStates);
            
            const container = document.getElementById('pointStatus');
            if (!container) {
                console.error('找不到点位状态容器');
                return;
            }
            
            if (!pointStates || Object.keys(pointStates).length === 0) {
                container.innerHTML = '<p style="color: #666;">暂无点位状态信息</p>';
                console.log('点位状态为空');
                return;
            }
            
            const totalPoints = Object.keys(pointStates).length;
            const onPoints = Object.values(pointStates).filter(state => state === 1).length;
            const offPoints = totalPoints - onPoints;
            
            // 简化版本，先显示基本信息
            container.innerHTML = `
                <div style="margin-bottom: 15px;">
                    <strong>总点位:</strong> ${totalPoints.toLocaleString()} | 
                    <span style="color: #4CAF50;"><strong>开启:</strong> ${onPoints}</span> | 
                    <span style="color: #f44336;"><strong>关闭:</strong> ${offPoints}</span>
                </div>
                <div style="margin-bottom: 15px;">
                    <strong>状态详情:</strong> 已加载 ${totalPoints} 个点位的状态信息
                </div>
            `;
            console.log('点位状态更新完成');
        }
                     } else {
                         // 如果获取连接组信息失败，使用原来的显示方式
                         showOriginalPointStatus();
                     }
                 })
                 .catch(error => {
                     console.error('获取连接组可视化数据失败:', error);
                     // 使用原来的显示方式
                     showOriginalPointStatus();
                 });
             
             // 显示原始点位状态的函数
             function showOriginalPointStatus() {
                 container.innerHTML = `
                     <div style="margin-bottom: 15px;">
                         <strong>总点位:</strong> ${totalPoints.toLocaleString()} | 
                         <span style="color: #4CAF50;"><strong>开启:</strong> ${onPoints}</span> | 
                         <span style="color: #f44336;"><strong>关闭:</strong> ${offPoints}</span>
                     </div>
                     <div class="status-grid">
                         ${Object.entries(pointStates).slice(0, 100).map(([id, state]) => `
                             <div class="status-item ${state === 1 ? 'status-on' : 'status-off'}" 
                                  style="cursor: pointer;" 
                                  title="点位 ${id} - 点击查看导通关系" 
                                  onclick="showPointRelationships(${id})">
                                 ${id}
                             </div>
                         `).join('')}
                     </div>
                     ${totalPoints > 100 ? `<p style="text-align: center; color: #666; margin-top: 10px;">显示前100个点位，共${totalPoints}个</p>` : ''}
                 `;
             }
         }
        
        // 渲染测试历史（单页）
        function renderHistoryItems(items) {
             if (items && items.length > 0) {
                 const historyHtml = items.map(test => {
                     const date = new Date(test.timestamp * 1000);
                     const timeStr = date.toLocaleString('zh-CN');
                     const testPoints = test.test_points && test.test_points.length > 0 
                         ? test.test_points.join(', ') 
                         : '无';
                     
                     return `
                         <div class="test-record">
                             <div class="test-header">
                                 <strong>测试 #${test.test_id}</strong>
                                 <span class="test-time">${timeStr}</span>
                             </div>
                             <div class="test-details">
                                 <div><strong>电源点位:</strong> ${test.power_source}</div>
                                 <div><strong>测试点位:</strong> ${testPoints}</div>
                                 <div><strong>继电器操作:</strong> ${test.relay_operations || 0}</div>
                                 <div><strong>通电次数:</strong> ${test.power_on_operations || 0}</div>
                                 <div><strong>连接状态:</strong> <span class="${test.connections_found > 0 ? 'connected' : 'disconnected'}">${test.connections_found > 0 ? '已连接' : '未连接'}</span></div>
                                 <div><strong>耗时:</strong> ${(test.duration * 1000).toFixed(3)}s</div>
                             </div>
                         </div>
                     `;
                 }).join('');
                 
                 document.getElementById('testHistory').innerHTML = historyHtml + '<div id="historyPager"></div>';
             } else {
                 document.getElementById('testHistory').innerHTML = '<div class="no-data">暂无测试历史</div>';
             }
         }

         // 兼容旧函数名（外部仍调用 updateTestHistory）
        function updateTestHistory(data) {
            console.log('更新测试历史:', data);
            
            if (!data || !Array.isArray(data)) {
                console.log('测试历史数据为空或格式错误');
                const container = document.getElementById('testHistory');
                if (container) {
                    container.innerHTML = '<p style="color: #666;">暂无测试历史</p>';
                }
                return;
            }
            
            renderHistoryItems(data);
            console.log('测试历史更新完成');
        }

        // 加载指定页
        async function loadHistoryPage(page, pageSize) {
             try {
                 const resp = await fetch(`/api/test/history?page=${page}&page_size=${pageSize}`);
                 const json = await resp.json();
                 if (json.success && json.data) {
                     renderHistoryItems(json.data.items || []);
                     const pg = json.data.pagination || { page: 1, page_size: pageSize, total: 0 };
                     const totalPages = Math.max(1, Math.ceil((pg.total || 0) / (pg.page_size || 1)));
                     const pager = document.getElementById('historyPager');
                     if (pager) {
                         pager.innerHTML = `
                             <div style=\"text-align:center; margin-top:8px;\">
                                 <button id=\"prevPage\" ${pg.page<=1?'disabled':''}>上一页</button>
                                 <span style=\"margin:0 10px;\">第 ${pg.page} / ${totalPages} 页</span>
                                 <button id=\"nextPage\" ${pg.page>=totalPages?'disabled':''}>下一页</button>
                             </div>
                         `;
                         document.getElementById('prevPage') && document.getElementById('prevPage').addEventListener('click', ()=> loadHistoryPage(pg.page-1, pg.page_size));
                         document.getElementById('nextPage') && document.getElementById('nextPage').addEventListener('click', ()=> loadHistoryPage(pg.page+1, pg.page_size));
                     }
                 } else {
                     renderHistoryItems([]);
                 }
             } catch(e) {
                 renderHistoryItems([]);
             }
         }
        
        // 运行实验
        async function runExperiment() {
            const powerSource = document.getElementById('powerSource').value.trim();
            const testPoints = document.getElementById('testPoints').value.trim();
            
            if (!powerSource) {
                alert('请输入电源点位');
                return;
            }
            
            const powerSourceId = parseInt(powerSource);
            if (isNaN(powerSourceId) || powerSourceId < 0 || powerSourceId >= 100) {
                alert('电源点位ID必须在0-99之间');
                return;
            }
            
            // 解析测试点位，支持范围选择
            let testPointIds = [];
            if (testPoints) {
                const parts = testPoints.split(',').map(part => part.trim());
                for (const part of parts) {
                    if (part.indexOf('-') !== -1) {
                        // 处理范围选择，如 "5-15"
                        const range = part.split('-');
                        if (range.length === 2) {
                            const start = parseInt(range[0].trim());
                            const end = parseInt(range[1].trim());
                            if (!isNaN(start) && !isNaN(end) && start >= 0 && end >= 0 && start <= end && end < 100) {
                                for (let i = start; i <= end; i++) {
                                    if (i !== powerSourceId) { // 排除电源点位
                                        testPointIds.push(i);
                                    }
                                }
                            } else {
                                alert(`无效的范围选择: ${part}，范围必须在0-99之间且起始值小于等于结束值`);
                                return;
                            }
                        } else {
                            alert(`无效的范围格式: ${part}，请使用"起始-结束"格式`);
                            return;
                        }
                    } else {
                        // 处理单个点位
                        const pointId = parseInt(part);
                        if (!isNaN(pointId) && pointId >= 0 && pointId < 100) {
                            if (pointId !== powerSourceId) { // 排除电源点位
                                testPointIds.push(pointId);
                            }
                        } else {
                            alert(`无效的点位ID: ${part}，点位ID必须在0-99之间`);
                            return;
                        }
                    }
                }
            } else {
                // 如果没有指定测试点位，则测试除电源点位外的所有点位
                for (let i = 0; i < 100; i++) {
                    if (i !== powerSourceId) {
                        testPointIds.push(i);
                    }
                }
            }
            
            // 去重
            testPointIds = [...new Set(testPointIds)];
            
            if (testPointIds.length === 0) {
                alert('没有有效的测试点位');
                return;
            }
            
            console.log(`开始实验: 电源点位=${powerSourceId}, 测试点位=${testPointIds.join(',')}`);
            
            try {
                const response = await fetch('/api/experiment', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        power_source: powerSourceId,
                        test_points: testPointIds
                    }),
                });
                
                const result = await response.json();
                
                console.log('API响应:', result); // 添加调试信息
                
                if (result.success) {
                    // 检查数据结构
                    if (result.data && result.data.test_result) {
                        const connections = result.data.test_result.connections || [];
                        alert(`实验完成！检测到 ${connections.length} 个连接`);
                        updatePointStatus();
                        updateRelationshipSummary();
                    } else {
                        console.error('API响应数据结构异常:', result);
                        alert('实验完成，但响应数据结构异常，请检查控制台');
                    }
                } else {
                    alert('实验失败: ' + (result.error || '未知错误'));
                }
            } catch (error) {
                console.error('请求异常:', error);
                alert('请求失败: ' + error.message);
            }
        }
        
        // 运行随机实验
        async function runRandomExperiment() {
             try {
                 const powerSource = Math.floor(Math.random() * 100);
                 const testPoints = Array.from({length: Math.floor(Math.random() * 20) + 1}, () => Math.floor(Math.random() * 100));
                 
                 const response = await fetch('/api/experiment', {
                     method: 'POST',
                     headers: { 'Content-Type': 'application/json' },
                     body: JSON.stringify({
                         power_source: powerSource,
                         test_points: testPoints
                     })
                 });
                 
                 const result = await response.json();
                 if (result.success) {
                     alert(`随机实验开始！电源点位: ${powerSource}, 测试点位: ${testPoints.length}个`);
                     // 立即刷新数据
                     loadInitialData();
                 } else {
                     alert('随机实验执行失败: ' + result.error);
                 }
             } catch (error) {
                 alert('请求失败: ' + error.message);
             }
                 }
        
        // 🔧 新增：根据总点位数更新导通分布默认值
        function updateConductivityDefaults() {
            const totalPts = parseInt(document.getElementById('totalPoints').value || '100', 10);
            
            if (isNaN(totalPts) || totalPts < 2) {
                return;
            }
            
            // 计算新的默认分布（90%, 6%, 3%, 1%）
            const conductivity4 = Math.round(totalPts * 0.01);  // 1%
            const conductivity3 = Math.round(totalPts * 0.03);  // 3%
            const conductivity2 = Math.round(totalPts * 0.06);  // 6%
            const conductivity1 = totalPts - conductivity4 - conductivity3 - conductivity2;  // 剩余的
            
            // 更新输入框的值
            document.getElementById('conductivity1').value = conductivity1;
            document.getElementById('conductivity2').value = conductivity2;
            document.getElementById('conductivity3').value = conductivity3;
            document.getElementById('conductivity4').value = conductivity4;
            
            console.log(`总点位更新为${totalPts}，自动调整导通分布：1个(${conductivity1}), 2个(${conductivity2}), 3个(${conductivity3}), 4个(${conductivity4})`);
        }
        
                // 重置系统
        async function resetSystem() {
             if (!confirm('确定要重置系统吗？这将清除所有测试历史并重新生成随机连接关系。')) {
                 return;
             }
             
             try {
                 const totalPts = parseInt(document.getElementById('totalPoints').value || '100', 10);
                                 const conductivity1 = parseInt(document.getElementById('conductivity1').value || '90', 10);
                const conductivity2 = parseInt(document.getElementById('conductivity2').value || '6', 10);
                const conductivity3 = parseInt(document.getElementById('conductivity3').value || '3', 10);
                const conductivity4 = parseInt(document.getElementById('conductivity4').value || '1', 10);
                 
                 if (isNaN(totalPts) || totalPts < 2) {
                     alert('请输入合法的总点位（>=2）');
                     return;
                 }
                 
                 // 验证导通分布设置
                 const totalFromDistribution = conductivity1 + conductivity2 + conductivity3 + conductivity4;
                 if (totalFromDistribution !== totalPts) {
                     alert(`导通分布总数(${totalFromDistribution})与总点数(${totalPts})不匹配！\n请确保：1个+2个+3个+4个 = 总点数`);
                     return;
                 }
                 
                 if (conductivity1 < 0 || conductivity2 < 0 || conductivity3 < 0 || conductivity4 < 0) {
                     alert('导通分布数量不能为负数！');
                     return;
                 }
                 
                 const response = await fetch('/api/system/reset', {
                     method: 'POST',
                     headers: { 'Content-Type': 'application/json' },
                     body: JSON.stringify({ 
                         total_points: totalPts, 
                         conductivity_distribution: {
                             1: conductivity1,
                             2: conductivity2,
                             3: conductivity3,
                             4: conductivity4
                         }
                     })
                 });
                 
                 const result = await response.json();
                 if (result.success) {
                     const total = result.total_points ?? totalPts;
                     alert(`系统已重置！总点位=${total}\n导通分布：1个(${conductivity1}) + 2个(${conductivity2}) + 3个(${conductivity3}) + 4个(${conductivity4}) = ${total}`);
                     // 重新加载数据
                     loadInitialData();
                 } else {
                     alert('系统重置失败: ' + result.error);
                 }
             } catch (error) {
                 alert('请求失败: ' + error.message);
             }
         }
        
        // 显示详细点对信息
        async function showDetailedClusters() {
             try {
                 const response = await fetch('/api/clusters/detailed');
                 const result = await response.json();

                 if (!result || result.success !== true || !result.data) {
                     throw new Error(result && result.error ? result.error : '接口无数据');
                 }

                 const data = result.data || {};
                 const summary = data.summary || {};
                 const confirmed = Array.isArray(data.confirmed_clusters) ? data.confirmed_clusters : [];
                 const unconfirmedPoints = (data.unconfirmed_points && Array.isArray(data.unconfirmed_points.points))
                     ? data.unconfirmed_points
                     : { points: [], count: 0, description: '未确认连接组关系的点位: 0个' };

                 const totalClusters = summary.total_clusters ?? confirmed.length ?? 0;
                 const totalConfirmedPoints = summary.total_confirmed_points ?? confirmed.reduce((acc, c) => acc + (c.points?.length || 0), 0);
                 const totalUnconfirmedPoints = summary.total_unconfirmed_points ?? unconfirmedPoints.count ?? 0;
                 const totalPoints = summary.total_points ?? (totalConfirmedPoints + totalUnconfirmedPoints);

                 let message = `详细点对信息:\n\n`;
                 message += `总连接组数: ${totalClusters}\n`;
                 message += `已确认点位: ${totalConfirmedPoints}\n`;
                 message += `未确认点位: ${totalUnconfirmedPoints}\n`;
                 message += `总点位: ${totalPoints}\n\n`;

                 if (confirmed.length > 0) {
                     message += `已确认连接组:\n`;
                     confirmed.forEach((cluster, index) => {
                         const desc = cluster.description || `连接组 ${index + 1}: ${cluster.points?.length || 0}个点位`;
                         message += `${desc}\n`;
                         message += `  点位: [${(cluster.points || []).join(', ')}]\n`;
                         if (cluster.timestamp) {
                             message += `  确认时间: ${new Date(cluster.timestamp * 1000).toLocaleString()}\n`;
                         }
                         message += `\n`;
                     });
                 }

                 if ((unconfirmedPoints.count || 0) > 0) {
                     message += `${unconfirmedPoints.description}\n`;
                     message += `点位: [${unconfirmedPoints.points.join(', ')}]\n\n`;
                 }

                 alert(message);
             } catch (error) {
                 alert('请求失败: ' + error.message);
             }
         }
        
        // 显示未确认连接组关系
        async function showUnconfirmedRelationships() {
             try {
                 const response = await fetch('/api/clusters/unconfirmed_relationships');
                 const result = await response.json();

                 if (result && result.data) {
                     const data = result.data || {};
                     let message = `🔍 未确认点对关系分析\n\n`;
                     
                     // 显示摘要信息
                     message += `📊 摘要信息:\n`;
                     const summary = data.summary || {};
                     message += `已确认连接组: ${summary.total_confirmed_clusters || 0}个\n`;
                     message += `未确认点位: ${summary.total_unconfirmed_points || 0}个\n`;
                     message += `未确认连接组关系: ${summary.total_unconfirmed_cluster_relationships || 0}个\n`;
                     message += `未确认点位关系: ${summary.total_unconfirmed_point_relationships || 0}个\n`;
                     message += `未确认点位间关系: ${summary.total_unconfirmed_point_to_point_relationships || 0}个\n`;
                     message += `测试建议: ${summary.total_testing_suggestions || 0}个\n\n`;
                     
                     // 显示分析详情
                     if (data.analysis && data.analysis.details) {
                         message += `📋 分析详情:\n`;
                         data.analysis.details.forEach(detail => {
                             message += `• ${detail}\n`;
                         });
                         message += `\n`;
                     }

                     // 临时显示：服务端中间量（debug）
                     if (data.debug) {
                         const dbg = data.debug;
                         message += `🛠 调试信息:\n`;
                         message += `- 历史测试次数: ${dbg.num_tests || 0}\n`;
                         message += `- 已记录连接总数: ${dbg.num_detected_connections || 0}\n`;
                         const ncs = dbg.non_conductive_summary || {};
                         message += `- 已确不导通汇总: PP=${ncs.point_point_pairs||0}, PC=${ncs.point_cluster_pairs||0}, CC=${ncs.cluster_pairs||0}\n`;
                         const br = dbg.suggestions_breakdown || {};
                         message += `- 建议构成: 高优先未确认点=${br.high_unconfirmed_point_test||0}, 中优先未确认点=${br.medium_unconfirmed_point_test||0}, 点对点=${br.point_to_point_test||0}, 跨连接组=${br.cross_cluster_test||0}\n`;
                         message += `\n`;
                     }

                     // 显示测试建议
                     if (Array.isArray(data.testing_suggestions) && data.testing_suggestions.length > 0) {
                         message += `🧪 测试建议:\n`;
                         data.testing_suggestions.forEach((suggestion, index) => {
                             let typeLabel = '其他';
                             if (suggestion.type === 'cross_cluster_test') typeLabel = '跨连接组测试';
                             else if (suggestion.type === 'unconfirmed_point_test') typeLabel = '未确认点位测试';
                             else if (String(suggestion.type).includes('point_to_point')) typeLabel = '点对点测试';
                             message += `${index + 1}. 类型: ${typeLabel}\n`;
                             message += `   优先级: ${suggestion.priority === 'high' ? '高' : (suggestion.priority || '中')}\n`;
                             if (suggestion.test_config) {
                                 message += `   电源点位: ${suggestion.test_config.power_source}\n`;
                                 message += `   测试点位: ${suggestion.test_config.test_points.length > 10 ? 
                                     suggestion.test_config.test_points.slice(0, 10).join(', ') + '...' : 
                                     suggestion.test_config.test_points.join(', ')}\n`;
                             }
                             message += `\n`;
                         });
                     }
                     
                     // 显示未确认连接组关系（逐对列出）
                     if (Array.isArray(data.unconfirmed_cluster_relationships) && data.unconfirmed_cluster_relationships.length > 0) {
                         message += `🔗 未确认连接组关系:\n`;
                         data.unconfirmed_cluster_relationships.forEach((rel, index) => {
                             const c1 = rel.cluster1;
                             const c2 = rel.cluster2;
                             const c1Id = getShortClusterName(c1.cluster_id || `[#${index+1}-A]`);
                             const c2Id = getShortClusterName(c2.cluster_id || `[#${index+1}-B]`);
                             message += `${index + 1}. ${c1Id} ↔ ${c2Id}\n`;
                             message += `   ${c1.points.join(', ')} ✖ ${c2.points.join(', ')}\n`;
                             message += `   状态: ${rel.status}\n`;
                             message += `\n`;
                         });
                     }

                     // 显示未确认点位关系（列出前20个点位，每个点位展示前3个可能关系）
                     if (Array.isArray(data.unconfirmed_point_relationships) && data.unconfirmed_point_relationships.length > 0) {
                         message += `📍 未确认点位关系（部分）:\n`;
                         data.unconfirmed_point_relationships.slice(0, 20).forEach((pRel, idx) => {
                             message += `${idx + 1}. 点位 ${pRel.point_id} 可能关系: ${pRel.total_possibilities} 个\n`;
                             const examples = (pRel.possible_relationships || []).slice(0, 3);
                             examples.forEach((rel) => {
                                 const cid = rel.cluster && rel.cluster.cluster_id ? rel.cluster.cluster_id : '连接组?';
                                 const cpoints = rel.cluster && rel.cluster.points ? rel.cluster.points.join(', ') : '?';
                                 message += `   - ${cid}: [${cpoints}]\n`;
                             });
                         });
                         if (data.unconfirmed_point_relationships.length > 20) {
                             message += `... 共 ${data.unconfirmed_point_relationships.length} 个点位关系\n\n`;
                         } else {
                             message += `\n`;
                         }
                     }

                     // 显示未确认点位间关系（列出前50对）
                     if (Array.isArray(data.unconfirmed_point_to_point_relationships) && data.unconfirmed_point_to_point_relationships.length > 0) {
                         message += `🔁 未确认点位间关系（部分）:\n`;
                         data.unconfirmed_point_to_point_relationships.slice(0, 50).forEach((pp, i) => {
                             message += `${i + 1}. 点位 ${pp.point1} ↔ 点位 ${pp.point2}  状态: ${pp.status}\n`;
                         });
                         if (data.unconfirmed_point_to_point_relationships.length > 50) {
                             message += `... 共 ${data.unconfirmed_point_to_point_relationships.length} 对\n`;
                         }
                         message += `\n`;
                     }
                     
                     // 显示未确认点位关系
                     if (data.unconfirmed_point_relationships && data.unconfirmed_point_relationships.length > 0) {
                         message += `📍 未确认点位关系:\n`;
                         data.unconfirmed_point_relationships.forEach((pointRel, index) => {
                             message += `${index + 1}. 点位 ${pointRel.point_id} 的可能关系: ${pointRel.total_possibilities}个\n`;
                             message += `   建议: 进行导通测试确认归属\n\n`;
                         });
                     }

                     alert(message);
                 } else {
                     alert('获取未确认连接组关系失败: ' + result.error);
                 }
             } catch (error) {
                 alert('请求失败: ' + error.message);
                 console.error('Error:', error);
             }
        }

        // 显示已确认不导通关系
        async function showConfirmedNonConductive() {
             try {
                 const response = await fetch('/api/relationships/confirmed_non_conductive');
                 const result = await response.json();
                 if (result.success) {
                     const data = result.data || {};
                     const sum = data.summary || {};
                     let message = `✅ 已确认不导通关系\n\n`;
                     message += `连接组-连接组: ${sum.cluster_pairs || 0} 对\n`;
                     message += `点位-连接组: ${sum.point_cluster_pairs || 0} 对\n`;
                     message += `点位-点位: ${sum.point_point_pairs || 0} 对\n\n`;
                     if (Array.isArray(data.cluster_non_conductive_pairs) && data.cluster_non_conductive_pairs.length > 0) {
                         message += `连接组-连接组（示例）：\n`;
                         data.cluster_non_conductive_pairs.slice(0, 10).forEach((pair, idx) => {
                             const left = getShortClusterName(pair.cluster1.cluster_id || '')
                             const right = getShortClusterName(pair.cluster2.cluster_id || '')
                             message += `${idx + 1}. ${left} ✖ ${right}  [` +
                                 `${pair.cluster1.points.join(', ')}] ✖ [` +
                                 `${pair.cluster2.points.join(', ')}]\n`;
                         });
                         message += `\n`;
                     }
                     if (Array.isArray(data.point_cluster_non_conductive) && data.point_cluster_non_conductive.length > 0) {
                         message += `点位-连接组（示例）：\n`;
                         data.point_cluster_non_conductive.slice(0, 15).forEach((item, idx) => {
                             const cid = item.cluster ? getShortClusterName(item.cluster.cluster_id || '') : '连接组?';
                             message += `${idx + 1}. 点位 ${item.point_id} ✖ ${cid}\n`;
                         });
                         message += `\n`;
                     }
                     if (Array.isArray(data.point_point_non_conductive) && data.point_point_non_conductive.length > 0) {
                         message += `点位-点位（示例）：\n`;
                         data.point_point_non_conductive.slice(0, 20).forEach((item, idx) => {
                             message += `${idx + 1}. ${item.point1} ✖ ${item.point2}\n`;
                         });
                         message += `\n`;
                     }
                     alert(message);
                 } else {
                     alert('获取已确认不导通关系失败: ' + result.error);
                 }
             } catch (error) {
                 alert('请求失败: ' + error.message);
             }
        }

        // 显示指定点位的导通关系
        async function showPointRelationships(pointId) {
             try {
                 const response = await fetch(`/api/relationships/point/${pointId}`);
                 const result = await response.json();

                 if (result.success) {
                     const relationships = result.data;
                     let message = `点位 ${pointId} 作为通电点位的导通关系:\n\n`;
                     
                     // 显示导通关系
                     if (relationships.conductive_points && relationships.conductive_points.length > 0) {
                         message += `✅ 能导通的目标点位 (${relationships.conductive_points.length}个):\n`;
                         message += `   ${relationships.conductive_points.join(', ')}\n\n`;
                     } else {
                         message += `❌ 暂无能导通的目标点位\n\n`;
                     }
                     
                     // 显示不导通关系
                     if (relationships.non_conductive_points && relationships.non_conductive_points.length > 0) {
                         message += `❌ 不能导通的目标点位 (${relationships.non_conductive_points.length}个):\n`;
                         message += `   ${relationships.non_conductive_points.join(', ')}\n\n`;
                     } else {
                         message += `❓ 暂无确认不导通的目标点位\n\n`;
                     }
                     
                     // 显示未知关系
                     if (relationships.unknown_points && relationships.unknown_points.length > 0) {
                         message += `❓ 未知关系的目标点位 (${relationships.unknown_points.length}个):\n`;
                         message += `   ${relationships.unknown_points.join(', ')}\n\n`;
                     } else {
                         message += `✅ 所有目标点位关系已确认\n\n`;
                     }
                     
                     message += `总计: ${relationships.total_points} 个点位\n`;
                     message += `⚠️ 注意: 这些关系是单向的，表示点位 ${pointId} 作为通电点位时的导通能力`;
                     
                     // 添加查看真实导通关系的选项
                     message += `\n\n🔍 查看真实导通关系:\n`;
                     message += `点击确定后可以查看点位 ${pointId} 作为通电点位时的真实导通情况`;
                     
                     if (confirm(message)) {
                         // 用户确认后，显示真实导通关系
                         showRealConductiveForPoint(pointId);
                     }
                 } else {
                     alert('获取点位导通关系失败: ' + result.error);
                 }
             } catch (error) {
                 alert('请求失败: ' + error.message);
             }
         }
         
        // 页面加载完成后初始化（不再依赖WebSocket是否已连接）
        document.addEventListener('DOMContentLoaded', () => {
            loadInitialData();
            // 若短时间内仍未建立WS连接，启用兜底轮询
            setTimeout(() => {
                if (!socket.connected && !fallbackIntervalId) {
                    startFallbackPolling();
                }
            }, 1000);
        });

        // 显示关系矩阵
        async function showRelationshipMatrix() {
            try {
                const response = await fetch('/api/relationships/matrix');
                const result = await response.json();

                if (result.success) {
                    const matrix = result.data.matrix;
                    const totalPoints = result.data.total_points;
                    
                    // 创建矩阵显示窗口
                    const matrixWindow = window.open('', '_blank', 'width=800,height=600,scrollbars=yes');
                    matrixWindow.document.write(`
                        <!DOCTYPE html>
                        <html>
                        <head>
                            <title>关系矩阵 - ${totalPoints}x${totalPoints}</title>
                            <style>
                                body { font-family: Arial, sans-serif; margin: 20px; }
                                .matrix-container { overflow: auto; }
                                .matrix { border-collapse: collapse; font-size: 10px; }
                                .matrix td { 
                                    width: 20px; height: 20px; 
                                    text-align: center; border: 1px solid #ccc;
                                    cursor: pointer;
                                }
                                .matrix td:hover { background-color: #f0f0f0; }
                                .conductive { background-color: #4CAF50; color: white; }
                                .non_conductive { background-color: #f44336; color: white; }
                                .unknown { background-color: #9E9E9E; color: white; }
                                .legend { margin: 20px 0; }
                                .legend-item { display: inline-block; margin-right: 20px; }
                                .legend-color { 
                                    display: inline-block; width: 20px; height: 20px; 
                                    border: 1px solid #ccc; margin-right: 5px;
                                }
                            </style>
                        </head>
                        <body>
                            <h2>关系矩阵 (${totalPoints}x${totalPoints}) - 非对称关系</h2>
                            <div class="legend">
                                <div class="legend-item">
                                    <span class="legend-color conductive"></span>导通 (1)
                                </div>
                                <div class="legend-item">
                                    <span class="legend-color non_conductive"></span>不导通 (-1)
                                </div>
                                <div class="legend-item">
                                    <span class="legend-color unknown"></span>未知 (0)
                                </div>
                            </div>
                            <p style="background: #fff3cd; padding: 10px; border: 1px solid #ffeaa7; border-radius: 5px; margin: 10px 0;">
                                <strong>说明:</strong> 矩阵是非对称的，E(i,j) ≠ E(j,i)<br>
                                • 行索引 i 表示通电点位<br>
                                • 列索引 j 表示目标点位<br>
                                • E(i,j) = 1 表示点位 i 作为通电点位时，点位 j 能够导通<br>
                                • E(i,j) = -1 表示点位 i 作为通电点位时，点位 j 不能导通<br>
                                • E(i,j) = 0 表示点位 i 作为通电点位时，与点位 j 的关系未知
                            </p>
                            <div class="matrix-container">
                                <table class="matrix">
                                    <tr>
                                        <td></td>
                                        ${Array.from({length: totalPoints}, (_, i) => `<td style="font-weight: bold;">${i}</td>`).join('')}
                                    </tr>
                                    ${matrix.map((row, i) => `
                                        <tr>
                                            <td style="font-weight: bold;">${i}</td>
                                            ${row.map((cell, j) => {
                                                let className = '';
                                                if (i === j) {
                                                    className = 'conductive'; // 对角线始终为1，显示为导通状态
                                                    return `<td class="${className}" title="点位 ${i} 自身关系 (1)">1</td>`;
                                                } else if (cell === 1) {
                                                    className = 'conductive';
                                                    return `<td class="${className}" title="点位 ${i} 作为通电点位时，点位 ${j} 能导通 (1)">1</td>`;
                                                } else if (cell === -1) {
                                                    className = 'non_conductive';
                                                    return `<td class="${className}" title="点位 ${i} 作为通电点位时，点位 ${j} 不能导通 (-1)">-1</td>`;
                                                } else {
                                                    className = 'unknown';
                                                    return `<td class="${className}" title="点位 ${i} 作为通电点位时，与点位 ${j} 的关系未知 (0)"></td>`;
                                                }
                                            }).join('')}
                                        </tr>
                                    `).join('')}
                                </table>
                            </div>
                            <p><small>点击矩阵中的单元格可以查看详细信息</small></p>
                        </body>
                        </html>
                    `);
                    matrixWindow.document.close();
                } else {
                    alert('获取关系矩阵失败: ' + result.error);
                }
            } catch (error) {
                alert('请求失败: ' + error.message);
            }
        }

        // 显示真实导通点位信息
        async function showRealConductiveInfo() {
            try {
                const response = await fetch('/api/relationships/real_conductive/all');
                const result = await response.json();

                if (result.success) {
                    const data = result.data;
                    let message = `🔌 真实导通点位信息概览\n\n`;
                    
                    // 显示摘要信息
                    message += `📊 摘要信息:\n`;
                    message += `总点位: ${data.total_points}\n`;
                    message += `总导通对数: ${data.total_conductive_pairs}\n`;
                    message += `有导通关系的点位: ${data.summary.points_with_conductive_relations}个\n`;
                    message += `无导通关系的点位: ${data.summary.points_without_conductive_relations}个\n`;
                    message += `平均导通目标数: ${data.summary.average_conductive_targets.toFixed(2)}\n\n`;
                    
                    // 显示有导通关系的点位详情
                    const pointsWithRelations = data.points_info.filter(p => p.conductive_count > 0);
                    if (pointsWithRelations.length > 0) {
                        message += `🔗 有导通关系的点位 (前20个):\n`;
                        pointsWithRelations.slice(0, 20).forEach((point, index) => {
                            message += `${index + 1}. 点位 ${point.power_point}: 能导通 ${point.conductive_count} 个目标点位\n`;
                            if (point.conductive_targets.length <= 10) {
                                message += `   目标点位: [${point.conductive_targets.join(', ')}]\n`;
                            } else {
                                message += `   目标点位: [${point.conductive_targets.slice(0, 10).join(', ')}...等${point.conductive_count}个]\n`;
                            }
                            message += `\n`;
                        });
                        
                        if (pointsWithRelations.length > 20) {
                            message += `... 共 ${pointsWithRelations.length} 个有导通关系的点位\n\n`;
                        }
                    } else {
                        message += `❌ 暂无导通关系\n\n`;
                    }
                    
                    // 显示无导通关系的点位
                    const pointsWithoutRelations = data.points_info.filter(p => p.conductive_count === 0);
                    if (pointsWithoutRelations.length > 0) {
                        message += `❌ 无导通关系的点位 (前20个):\n`;
                        const pointIds = pointsWithoutRelations.slice(0, 20).map(p => p.power_point);
                        message += `[${pointIds.join(', ')}]\n`;
                        
                        if (pointsWithoutRelations.length > 20) {
                            message += `... 共 ${pointsWithoutRelations.length} 个无导通关系的点位\n\n`;
                        }
                    }
                    
                    alert(message);
                } else {
                    alert('获取真实导通点位信息失败: ' + result.error);
                }
            } catch (error) {
                alert('请求失败: ' + error.message);
            }
        }

        // 显示指定点位的真实导通关系
        async function showRealConductiveForPoint(pointId) {
            try {
                const response = await fetch(`/api/relationships/real_conductive/point/${pointId}`);
                const result = await response.json();

                if (result.success) {
                    const info = result.data;
                    let message = `🔌 点位 ${pointId} 的真实导通信息\n\n`;
                    
                    message += `📊 基本信息:\n`;
                    message += `电源点位: ${info.power_point}\n`;
                    message += `总点位数量: ${info.total_points}\n`;
                    message += `能导通的目标点位数量: ${info.conductive_count}\n\n`;
                    
                    if (info.conductive_count > 0) {
                        message += `✅ 能导通的目标点位:\n`;
                        if (info.conductive_targets.length <= 20) {
                            message += `[${info.conductive_targets.join(', ')}]\n\n`;
                        } else {
                            message += `[${info.conductive_targets.slice(0, 20).join(', ')}...等${info.conductive_count}个]\n\n`;
                        }
                        
                        message += `💡 说明: 当点位 ${pointId} 作为通电点位时，上述点位可以通过线缆导通连接。`;
                    } else {
                        message += `❌ 该点位作为通电点位时，无法导通任何其他点位。\n\n`;
                        message += `💡 说明: 点位 ${pointId} 是一个独立的点位，没有与其他点位的物理连接。`;
                    }
                    
                    alert(message);
                } else {
                    alert('获取真实导通信息失败: ' + result.error);
                }
            } catch (error) {
                alert('请求失败: ' + error.message);
            }
        }

        // 显示真实关系矩阵
        async function showTrueRelationshipMatrix() {
            try {
                const response = await fetch('/api/relationships/true_matrix');
                const result = await response.json();

                if (result.success) {
                    const matrix = result.data.matrix;
                    const totalPoints = result.data.total_points;
                    
                    // 创建矩阵显示窗口
                    const matrixWindow = window.open('', '_blank', 'width=800,height=600,scrollbars=yes');
                    matrixWindow.document.write(`
                        <!DOCTYPE html>
                        <html>
                        <head>
                            <title>真实关系矩阵 - ${totalPoints}x${totalPoints}</title>
                            <style>
                                body { font-family: Arial, sans-serif; margin: 20px; }
                                .matrix-container { overflow: auto; }
                                .matrix { border-collapse: collapse; font-size: 10px; }
                                .matrix td { 
                                    width: 20px; height: 20px; 
                                    text-align: center; border: 1px solid #ccc;
                                    cursor: pointer;
                                }
                                .matrix td:hover { background-color: #f0f0f0; }
                                .conductive { background-color: #4CAF50; color: white; }
                                .non_conductive { background-color: #f44336; color: white; }
                                .unknown { background-color: #9E9E9E; color: white; }
                                .legend { margin: 20px 0; }
                                .legend-item { display: inline-block; margin-right: 20px; }
                                .legend-color { 
                                    display: inline-block; width: 20px; height: 20px; 
                                    border: 1px solid #ccc; margin-right: 5px;
                                }
                            </style>
                        </head>
                        <body>
                            <h2>真实关系矩阵 (${totalPoints}x${totalPoints})</h2>
                            <div class="legend">
                                <div class="legend-item">
                                    <span class="legend-color conductive"></span>导通 (1)
                                </div>
                                <div class="legend-item">
                                    <span class="legend-color non_conductive"></span>不导通 (-1)
                                </div>
                                <div class="legend-item">
                                    <span class="legend-color unknown"></span>未知 (0)
                                </div>
                            </div>
                            <p style="background: #e8f5e8; padding: 10px; border: 1px solid #4CAF50; border-radius: 5px; margin: 10px 0;">
                                <strong>说明:</strong> 这是基于系统真实配置的关系矩阵<br>
                                • 行索引 i 表示通电点位<br>
                                • 列索引 j 表示目标点位<br>
                                • E(i,j) = 1 表示点位 i 作为通电点位时，点位 j 能够导通（真实配置）<br>
                                • E(i,j) = -1 表示点位 i 作为通电点位时，点位 j 不能导通（真实配置）
                            </p>
                            <div class="matrix-container">
                                <table class="matrix">
                                    <tr>
                                        <td></td>
                                        ${Array.from({length: totalPoints}, (_, i) => `<td style="font-weight: bold;">${i}</td>`).join('')}
                                    </tr>
                                    ${matrix.map((row, i) => `
                                        <tr>
                                            <td style="font-weight: bold;">${i}</td>
                                            ${row.map((cell, j) => {
                                                let className = '';
                                                if (i === j) {
                                                    className = 'conductive'; // 对角线始终为1
                                                    return `<td class="${className}" title="点位 ${i} 自身关系 (1)">1</td>`;
                                                } else if (cell === 1) {
                                                    className = 'conductive';
                                                    return `<td class="${className}" title="点位 ${i} 作为通电点位时，点位 ${j} 能导通 (1)">1</td>`;
                                                } else {
                                                    className = 'non_conductive';
                                                    return `<td class="${className}" title="点位 ${i} 作为通电点位时，点位 ${j} 不能导通 (-1)">-1</td>`;
                                                }
                                            }).join('')}
                                        </tr>
                                    `).join('')}
                                </table>
                            </div>
                            <p><small>这是系统的真实配置，用于对比检测结果的准确性</small></p>
                        </body>
                        </html>
                    `);
                    matrixWindow.document.close();
                } else {
                    alert('获取真实关系矩阵失败: ' + result.error);
                }
            } catch (error) {
                alert('请求失败: ' + error.message);
            }
        }
        
        // 显示矩阵对比
        async function showMatricesComparison() {
            try {
                const response = await fetch('/api/relationships/matrices_comparison');
                const result = await response.json();

                if (result.success) {
                    const data = result.data;
                    const comparison = data.comparison;
                    
                    let message = `🔍 检测到的关系矩阵 vs 真实关系矩阵对比\n\n`;
                    
                    // 显示基本信息
                    message += `📊 基本信息:\n`;
                    message += `总点位: ${comparison.total_points}\n`;
                    message += `非对角线单元格: ${comparison.off_diagonal_cells}\n\n`;
                    
                    // 显示检测到的关系统计
                    message += `📈 检测到的关系统计:\n`;
                    message += `导通关系: ${comparison.detected.conductive}个\n`;
                    message += `不导通关系: ${comparison.detected.non_conductive}个\n`;
                    message += `未知关系: ${comparison.detected.unknown}个\n\n`;
                    
                    // 显示真实关系统计
                    message += `🎯 真实关系统计:\n`;
                    message += `导通关系: ${comparison.true.conductive}个\n`;
                    message += `无关系: ${comparison.true.unknown}个\n\n`;
                    
                    // 显示匹配情况
                    message += `✅ 匹配情况:\n`;
                    message += `正确检测导通: ${comparison.matching.matched_conductive}个\n`;
                    message += `正确检测不导通: ${comparison.matching.matched_non_conductive}个\n`;
                    message += `误报（检测导通但实际不导通）: ${comparison.matching.false_positive}个\n`;
                    message += `漏报（实际导通但未检测到）: ${comparison.detected.false_negative}个\n\n`;
                    
                    // 显示准确率
                    message += `📊 准确率:\n`;
                    message += `总体准确率: ${comparison.matching.accuracy_percentage.toFixed(2)}%\n`;
                    
                    if (comparison.matching.accuracy_percentage < 100) {
                        message += `\n⚠️ 检测结果与真实配置存在差异，建议进行更多测试以提高准确性。`;
                    } else {
                        message += `\n🎉 检测结果与真实配置完全匹配！`;
                    }
                    
                    alert(message);
                } else {
                    alert('获取矩阵对比失败: ' + result.error);
                }
            } catch (error) {
                alert('请求失败: ' + error.message);
            }
        }
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    """主页 - 显示前端界面"""
    return HTML_TEMPLATE

@app.route('/api/health')
def health_check():
    """健康检查"""
    return jsonify({
        'status': 'healthy',
        'timestamp': time.time(),
        'service': 'Cable Test System Web Server'
    })

@app.route('/api/points/status')
def get_point_status():
    """获取点位状态"""
    point_id = request.args.get('point_id', type=int)
    return jsonify(server.get_point_status(point_id))

@app.route('/api/clusters')
def get_cluster_info():
    """获取点对关系信息（兼容保留，返回空连接组）"""
    return jsonify(server.get_cluster_info())

@app.route('/api/experiment', methods=['POST'])
def run_experiment():
    """运行实验"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': '无效的请求数据'}), 400
        
        result = server.run_experiment(data)
        return jsonify(result)
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/system/info')
def get_system_info():
    """获取系统信息"""
    return jsonify(server.get_system_info())

@app.route('/api/test/progress')
def get_test_progress():
    """获取实验进度数据"""
    return jsonify(server.get_test_progress())

# ============== 新增：点-点关系API ==============
@app.route('/api/relationships/summary')
def get_relationship_summary():
    return jsonify(server.get_relationship_summary())

@app.route('/api/relationships/conductive')
def get_conductive_pairs():
    return jsonify(server.get_conductive_pairs())

@app.route('/api/relationships/non_conductive')
def get_non_conductive_pairs():
    return jsonify(server.get_non_conductive_pairs())

@app.route('/api/relationships/unconfirmed')
def get_unconfirmed_pairs():
    return jsonify(server.get_unconfirmed_pairs())

@app.route('/api/relationships/point/<int:point_id>')
def get_point_relationships(point_id: int):
    """获取指定点位的导通关系"""
    return jsonify(server.get_point_relationships(point_id))

@app.route('/api/relationships/matrix')
def get_relationship_matrix():
    """获取完整的关系矩阵"""
    return jsonify(server.get_relationship_matrix())

@app.route('/api/relationships/true_matrix')
def get_true_relationship_matrix():
    """获取真实关系矩阵"""
    return jsonify(server.get_true_relationship_matrix())

@app.route('/api/relationships/matrices_comparison')
def get_relationship_matrices_comparison():
    """获取检测到的关系矩阵与真实关系矩阵的对比"""
    return jsonify(server.get_relationship_matrices_comparison())

@app.route('/api/relationships/real_conductive/point/<int:point_id>')
def get_real_conductive_points(point_id: int):
    """获取指定点位的真实导通点位信息"""
    return jsonify(server.get_real_conductive_points(point_id))

@app.route('/api/relationships/real_conductive/all')
def get_all_real_conductive_info():
    """获取所有点位的真实导通信息概览"""
    return jsonify(server.get_all_real_conductive_info())

@app.route('/api/test/history')
def get_test_history():
    """获取测试历史（分页）
    Query:
      - page: 第几页（从1开始，默认1）
      - page_size: 每页条数（默认50）
    兼容参数：limit（若提供则等价于 page=1,page_size=limit）
    """
    # 兼容旧参数
    limit = request.args.get('limit', type=int)
    if limit is not None:
        page = 1
        page_size = limit
    else:
        page = request.args.get('page', 1, type=int)
        page_size = request.args.get('page_size', 50, type=int)

    # 规范页码
    page = max(1, page)
    page_size = max(1, page_size)

    # 取最近优先
    items = list(server.test_system.test_history)[::-1]
    total = len(items)
    start = (page - 1) * page_size
    end = start + page_size
    page_items = items[start:end]

    return jsonify({
        'success': True,
        'data': {
            'items': page_items,
            'pagination': {
                'page': page,
                'page_size': page_size,
                'total': total,
            }
        }
    })

@app.route('/api/system/reset', methods=['POST'])
def reset_system():
    """重置系统"""
    return jsonify(server.reset_system())

@app.route('/api/clusters/real')
def get_real_clusters():
    """获取真实连接点对关系信息"""
    return jsonify(server.get_real_clusters())

@app.route('/api/clusters/comparison')
def get_cluster_comparison():
    """获取连接点位对比信息"""
    return jsonify(server.get_cluster_comparison())

@app.route('/api/clusters/detailed')
def get_detailed_cluster_info():
    """获取详细的点对关系信息"""
    try:
        data = server.get_detailed_cluster_info()
        # tests/test_web_api.py 直接走 _assert_json_success -> 需要 success+data
        return jsonify({'success': True, 'data': data})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/clusters/visualization')
def get_cluster_visualization():
    """获取连接组可视化数据"""
    return jsonify(server.get_cluster_visualization())

@app.route('/api/clusters/unconfirmed_relationships')
def get_unconfirmed_cluster_relationships():
    """获取未确认连接组关系信息"""
    try:
        data = server.get_unconfirmed_cluster_relationships()
        # 确保包含 summary 关键字段（即使为空也返回基本结构）
        if isinstance(data, dict):
            data.setdefault('summary', {
                'total_confirmed_clusters': 0,
                'total_unconfirmed_points': 0,
                'total_unconfirmed_cluster_relationships': 0,
                'total_unconfirmed_point_relationships': 0,
                'total_unconfirmed_point_to_point_relationships': 0,
                'total_testing_suggestions': 0
            })
        return jsonify({'success': True, 'data': data})
    except Exception as e:
        # 为了避免前端读取 undefined 报错，返回一个安全的默认结构
        safe_data = {
            'summary': {
                'total_confirmed_clusters': 0,
                'total_unconfirmed_points': 0,
                'total_unconfirmed_cluster_relationships': 0,
                'total_unconfirmed_point_relationships': 0,
                'total_unconfirmed_point_to_point_relationships': 0,
                'total_testing_suggestions': 0
            },
            'unconfirmed_cluster_relationships': [],
            'unconfirmed_point_relationships': [],
            'unconfirmed_point_to_point_relationships': [],
            'testing_suggestions': [],
            'error': str(e)
        }
        return jsonify({'success': False, 'data': safe_data})

@app.route('/api/relationships/confirmed_non_conductive')
def get_confirmed_non_conductive():
    """获取已确认不导通关系（分页）
    Query:
      - category: 过滤类别，可选 'point_point' | 'point_cluster' | 'cluster_cluster' | 'all'（默认all）
      - page: 第几页（从1开始，默认1）
      - page_size: 每页条数（默认50）
    返回：
      - summary: 总览
      - pagination: 针对所选category的分页信息
      - items: 分页后的列表（当category=all时，返回三类分页结果的字典）
    """
    try:
        category = request.args.get('category', 'all')
        page = request.args.get('page', 1, type=int)
        page_size = request.args.get('page_size', 50, type=int)
        page = max(1, page)
        page_size = max(1, page_size)

        data = server.test_system.get_confirmed_non_conductive_relationships()

        def do_paginate(lst):
            total = len(lst)
            s = (page - 1) * page_size
            e = s + page_size
            return {
                'items': lst[s:e],
                'pagination': {
                    'page': page,
                    'page_size': page_size,
                    'total': total
                }
            }

        # 构建分页结果
        if category == 'point_point':
            page_result = do_paginate(data.get('point_point_non_conductive', []))
        elif category == 'point_cluster':
            page_result = do_paginate(data.get('point_cluster_non_conductive', []))
        elif category == 'cluster_cluster':
            page_result = do_paginate(data.get('cluster_non_conductive_pairs', []))
        else:
            page_result = {
                'point_point': do_paginate(data.get('point_point_non_conductive', [])),
                'point_cluster': do_paginate(data.get('point_cluster_non_conductive', [])),
                'cluster_cluster': do_paginate(data.get('cluster_non_conductive_pairs', [])),
            }

        # 兼容旧结构：直接并入三类列表（不分页的全量），以便测试/旧客户端读取
        full_pp = data.get('point_point_non_conductive', [])
        full_pc = data.get('point_cluster_non_conductive', [])
        full_cc = data.get('cluster_non_conductive_pairs', [])

        return jsonify({
            'success': True,
            'data': {
                'summary': data.get('summary', {}),
                'category': category,
                'items': page_result.get('items') if isinstance(page_result, dict) and 'items' in page_result else page_result,
                'pagination': page_result.get('pagination') if isinstance(page_result, dict) and 'pagination' in page_result else None,
                'cluster_non_conductive_pairs': full_cc,
                'point_cluster_non_conductive': full_pc,
                'point_point_non_conductive': full_pp,
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/experiment/batch', methods=['POST'])
def run_batch_experiments():
    """批量运行实验"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': '无效的请求数据'}), 400
        
        test_count = data.get('test_count', 5)
        max_points_per_test = data.get('max_points_per_test', 100)
        
        results = []
        for i in range(test_count):
            power_source = i % server.test_system.total_points
            test_points = list(range(i * 10, min((i + 1) * 10, server.test_system.total_points)))
            
            result = server.run_experiment({
                'power_source': power_source,
                'test_points': test_points
            })
            results.append(result)
        
        return jsonify({
            'success': True,
            'batch_results': results,
            'total_tests': len(results)
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

if __name__ == '__main__':
    print("🚀 启动线缆测试系统Web服务器...")
    print("📱 前端界面: http://localhost:5000")
    print("🔌 API接口: http://localhost:5000/api/")
    # print("📡 WebSocket: ws://localhost:5000/socket.io/")  # 暂时禁用WebSocket
    
    # socketio.run(app, host='0.0.0.0', port=5000, debug=True)  # 暂时禁用WebSocket
    app.run(host='0.0.0.0', port=5000, debug=True, use_reloader=False)  # 使用简单Flask服务器
