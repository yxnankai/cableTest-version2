#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Flask客户端 - 线缆测试系统双向测试接口
用于查询继电器状态、集群信息，以及设置和执行实验
"""

import requests
import json
import time
import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class ExperimentConfig:
    """实验配置数据类"""
    power_source: int
    test_points: List[int] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        config = {'power_source': self.power_source}
        if self.test_points:
            config['test_points'] = self.test_points
        return config

class FlaskTestClient:
    """Flask测试客户端"""
    
    def __init__(self, server_url: str = "http://localhost:5000"):
        self.server_url = server_url
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json',
            'User-Agent': 'CableTestClient/1.0'
        })
    
    def _make_request(self, method: str, endpoint: str, data: Dict = None) -> Dict[str, Any]:
        """发送HTTP请求"""
        url = f"{self.server_url}{endpoint}"
        try:
            if method.upper() == 'GET':
                response = self.session.get(url, params=data)
            elif method.upper() == 'POST':
                response = self.session.post(url, json=data)
            else:
                raise ValueError(f"不支持的HTTP方法: {method}")
            
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            logger.error(f"请求失败: {str(e)}")
            return {
                'success': False,
                'error': f'网络请求失败: {str(e)}'
            }
        except json.JSONDecodeError as e:
            logger.error(f"JSON解析失败: {str(e)}")
            return {
                'success': False,
                'error': f'响应解析失败: {str(e)}'
            }
    
    def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        logger.info("执行健康检查...")
        return self._make_request('GET', '/api/health')
    
    def get_point_status(self, point_id: int = None) -> Dict[str, Any]:
        """获取点位状态"""
        if point_id is not None:
            logger.info(f"查询点位 {point_id} 的状态...")
            params = {'point_id': point_id}
        else:
            logger.info("查询所有点位状态...")
            params = {}
        
        return self._make_request('GET', '/api/points/status', params)
    
    def get_cluster_info(self) -> Dict[str, Any]:
        """获取集群信息（兼容保留，仅用于旧演示）。"""
        logger.info("查询集群信息(兼容保留)...")
        return self._make_request('GET', '/api/clusters')

    # ===== 新增：点-点关系API 封装 =====
    def get_relationship_summary(self) -> Dict[str, Any]:
        return self._make_request('GET', '/api/relationships/summary')

    def get_conductive_pairs(self) -> Dict[str, Any]:
        return self._make_request('GET', '/api/relationships/conductive')

    def get_non_conductive_pairs(self) -> Dict[str, Any]:
        return self._make_request('GET', '/api/relationships/non_conductive')

    def get_unconfirmed_pairs(self) -> Dict[str, Any]:
        return self._make_request('GET', '/api/relationships/unconfirmed')
    
    def run_experiment(self, experiment_config: ExperimentConfig) -> Dict[str, Any]:
        """运行单个实验"""
        logger.info(f"设置实验: 电源点位 {experiment_config.power_source}")
        if experiment_config.test_points:
            logger.info(f"测试点位: {experiment_config.test_points}")
        
        return self._make_request('POST', '/api/experiment', experiment_config.to_dict())
    
    def run_batch_experiments(self, test_count: int = 5, max_points_per_test: int = 100) -> Dict[str, Any]:
        """运行批量实验"""
        logger.info(f"运行批量实验: {test_count} 个测试，每个最多 {max_points_per_test} 个点位")
        
        batch_config = {
            'test_count': test_count,
            'max_points_per_test': max_points_per_test
        }
        
        return self._make_request('POST', '/api/experiment/batch', batch_config)
    
    def get_system_info(self) -> Dict[str, Any]:
        """获取系统信息"""
        logger.info("查询系统信息...")
        return self._make_request('GET', '/api/system/info')
    
    def monitor_point_status(self, point_ids: List[int], interval: float = 1.0, duration: float = 60.0):
        """监控指定点位的状态变化"""
        logger.info(f"开始监控点位 {point_ids}，间隔 {interval} 秒，持续 {duration} 秒")
        
        start_time = time.time()
        previous_states = {}
        
        while time.time() - start_time < duration:
            current_time = time.time()
            logger.info(f"监控检查 - {time.strftime('%H:%M:%S', time.localtime(current_time))}")
            
            for point_id in point_ids:
                result = self.get_point_status(point_id)
                if result.get('success'):
                    current_state = result['data']
                    point_key = f"point_{point_id}"
                    
                    if point_key not in previous_states:
                        previous_states[point_key] = current_state
                        logger.info(f"点位 {point_id} 初始状态: {current_state['relay_state']}")
                    elif previous_states[point_key]['relay_state'] != current_state['relay_state']:
                        logger.info(f"点位 {point_id} 状态变化: {previous_states[point_key]['relay_state']} -> {current_state['relay_state']}")
                        previous_states[point_key] = current_state
                else:
                    logger.error(f"查询点位 {point_id} 状态失败: {result.get('error')}")
            
            time.sleep(interval)
        
        logger.info("监控结束")
    
    def interactive_test(self):
        """交互式测试界面"""
        print("\n=== 线缆测试系统客户端 ===")
        print("1. 健康检查")
        print("2. 查询点位状态")
        print("3. 查询集群信息")
        print("4. 运行单个实验")
        print("5. 运行批量实验")
        print("6. 获取系统信息")
        print("7. 监控点位状态")
        print("0. 退出")
        
        while True:
            try:
                choice = input("\n请选择操作 (0-7): ").strip()
                
                if choice == '0':
                    print("退出客户端")
                    break
                elif choice == '1':
                    result = self.health_check()
                    print(f"健康检查结果: {json.dumps(result, indent=2, ensure_ascii=False)}")
                
                elif choice == '2':
                    point_input = input("请输入点位ID (留空查询所有): ").strip()
                    if point_input:
                        point_id = int(point_input)
                        result = self.get_point_status(point_id)
                    else:
                        result = self.get_point_status()
                    print(f"点位状态查询结果: {json.dumps(result, indent=2, ensure_ascii=False)}")
                
                elif choice == '3':
                    result = self.get_cluster_info()
                    print(f"集群信息查询结果: {json.dumps(result, indent=2, ensure_ascii=False)}")
                
                elif choice == '4':
                    power_source = int(input("请输入电源点位ID: "))
                    test_points_input = input("请输入测试点位ID (用逗号分隔，留空为随机): ").strip()
                    
                    if test_points_input:
                        test_points = [int(x.strip()) for x in test_points_input.split(',')]
                    else:
                        test_points = None
                    
                    config = ExperimentConfig(power_source=power_source, test_points=test_points)
                    result = self.run_experiment(config)
                    print(f"实验执行结果: {json.dumps(result, indent=2, ensure_ascii=False)}")
                
                elif choice == '5':
                    test_count = int(input("请输入测试数量 (默认5): ") or "5")
                    max_points = int(input("请输入每个测试最大点位数量 (默认100): ") or "100")
                    
                    result = self.run_batch_experiments(test_count, max_points)
                    print(f"批量实验结果: {json.dumps(result, indent=2, ensure_ascii=False)}")
                
                elif choice == '6':
                    result = self.get_system_info()
                    print(f"系统信息: {json.dumps(result, indent=2, ensure_ascii=False)}")
                
                elif choice == '7':
                    point_input = input("请输入要监控的点位ID (用逗号分隔): ").strip()
                    point_ids = [int(x.strip()) for x in point_input.split(',')]
                    interval = float(input("请输入监控间隔秒数 (默认1.0): ") or "1.0")
                    duration = float(input("请输入监控持续时间秒数 (默认60.0): ") or "60.0")
                    
                    self.monitor_point_status(point_ids, interval, duration)
                
                else:
                    print("无效选择，请重新输入")
                    
            except KeyboardInterrupt:
                print("\n\n用户中断，退出客户端")
                break
            except Exception as e:
                print(f"操作失败: {str(e)}")

def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='线缆测试系统Flask客户端')
    parser.add_argument('--server', default='http://localhost:5000', 
                       help='服务端URL (默认: http://localhost:5000)')
    parser.add_argument('--interactive', action='store_true',
                       help='启动交互式测试界面')
    
    args = parser.parse_args()
    
    client = FlaskTestClient(args.server)
    
    if args.interactive:
        client.interactive_test()
    else:
        # 演示基本功能
        print("=== 线缆测试系统客户端演示 ===")
        
        # 健康检查
        print("\n1. 健康检查:")
        result = client.health_check()
        print(json.dumps(result, indent=2, ensure_ascii=False))
        
        # 查询系统信息
        print("\n2. 系统信息:")
        result = client.get_system_info()
        print(json.dumps(result, indent=2, ensure_ascii=False))
        
        # 运行一个简单实验
        print("\n3. 运行实验:")
        config = ExperimentConfig(power_source=1, test_points=[2, 3, 4])
        result = client.run_experiment(config)
        print(json.dumps(result, indent=2, ensure_ascii=False))
        
        # 查询集群信息
        print("\n4. 集群信息:")
        result = client.get_cluster_info()
        print(json.dumps(result, indent=2, ensure_ascii=False))

if __name__ == '__main__':
    main()
