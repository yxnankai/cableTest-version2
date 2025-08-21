#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
已确认点位数量测试脚本
用于验证新增的"已确认点位数量"字段功能
"""

import requests
from typing import Dict, Any

class ConfirmedPointsTester:
    """已确认点位数量测试器"""
    
    def __init__(self, base_url: str = "http://localhost:5000"):
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update({'Content-Type': 'application/json'})
    
    def get_system_info(self) -> Dict[str, Any]:
        """获取系统信息"""
        try:
            response = self.session.get(f"{self.base_url}/api/system/info")
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            print(f"获取系统信息失败: {e}")
        return {}
    
    def run_test(self, power_source: int, test_points: list) -> Dict[str, Any]:
        """运行单个测试"""
        try:
            payload = {
                "power_source": power_source,
                "test_points": test_points
            }
            response = self.session.post(f"{self.base_url}/api/experiment", json=payload)
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            print(f"运行测试失败: {e}")
        return {}
    
    def test_confirmed_points_count(self):
        """测试已确认点位数量功能"""
        print("=== 已确认点位数量功能测试 ===")
        
        # 1. 获取初始状态
        print("\n1. 获取初始状态...")
        initial_info = self.get_system_info()
        if not initial_info.get('success'):
            print("❌ 无法获取初始系统信息")
            return
        
        initial_data = initial_info['data']
        initial_confirmed = initial_data.get('confirmed_points_count', 0)
        total_points = initial_data['total_points']
        
        print(f"总点位: {total_points}")
        print(f"初始已确认点位数量: {initial_confirmed}")
        
        # 计算理论上的最大关系数
        max_relations = total_points * (total_points - 1) // 2
        print(f"理论最大关系数: {max_relations}")
        
        # 2. 运行一些测试来增加已确认的点位数量
        print("\n2. 运行测试增加已确认点位数量...")
        
        test_configs = [
            (0, [1, 2, 3, 4]),      # 测试点位0与其他4个点位的关系
            (5, [6, 7, 8, 9]),      # 测试点位5与其他4个点位的关系
            (10, [11, 12, 13, 14]), # 测试点位10与其他4个点位的关系
        ]
        
        for i, (power_source, test_points) in enumerate(test_configs):
            print(f"\n--- 测试 {i+1}: 电源点{power_source} -> {len(test_points)}个目标点 ---")
            
            result = self.run_test(power_source, test_points)
            if result.get('success'):
                print(f"✅ 测试成功")
                
                # 获取测试后的系统信息
                current_info = self.get_system_info()
                if current_info.get('success'):
                    current_data = current_info['data']
                    current_confirmed = current_data.get('confirmed_points_count', 0)
                    print(f"当前已确认点位数量: {current_confirmed}")
                    
                    # 计算新增的确认数量
                    new_confirmed = current_confirmed - initial_confirmed
                    if new_confirmed > 0:
                        print(f"新增确认数量: {new_confirmed}")
                    else:
                        print("未新增确认数量")
            else:
                print(f"❌ 测试失败: {result.get('error', '未知错误')}")
        
        # 3. 最终统计
        print("\n3. 最终统计...")
        final_info = self.get_system_info()
        if final_info.get('success'):
            final_data = final_info['data']
            final_confirmed = final_data.get('confirmed_points_count', 0)
            
            print(f"\n=== 测试结果总结 ===")
            print(f"初始已确认点位数量: {initial_confirmed}")
            print(f"最终已确认点位数量: {final_confirmed}")
            print(f"总增加数量: {final_confirmed - initial_confirmed}")
            
            # 计算确认率
            if max_relations > 0:
                confirmation_rate = final_confirmed / max_relations * 100
                print(f"点位关系确认率: {confirmation_rate:.1f}%")
            
            # 验证字段是否正确显示
            if 'confirmed_points_count' in final_data:
                print("✅ '已确认点位数量'字段正常显示")
            else:
                print("❌ '已确认点位数量'字段缺失")
            
            return {
                'initial_count': initial_confirmed,
                'final_count': final_confirmed,
                'increase': final_confirmed - initial_confirmed,
                'success': True
            }
        
        return {'success': False}

def main():
    """主函数"""
    print("已确认点位数量功能测试开始...\n")
    
    tester = ConfirmedPointsTester()
    
    try:
        result = tester.test_confirmed_points_count()
        if result and result.get('success'):
            print(f"\n✅ 测试完成！")
            print(f"已确认点位数量从 {result['initial_count']} 增加到 {result['final_count']}")
            print(f"总共增加了 {result['increase']} 个确认关系")
        else:
            print("\n❌ 测试失败")
    except Exception as e:
        print(f"\n❌ 测试异常: {e}")

if __name__ == "__main__":
    main()
