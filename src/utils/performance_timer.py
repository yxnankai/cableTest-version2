#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
性能计时器工具
用于记录测试系统各个步骤的执行时间，帮助定位性能瓶颈
"""

import time
import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from contextlib import contextmanager
import json
import threading

# 配置日志
logger = logging.getLogger(__name__)

@dataclass
class TimeRecord:
    """时间记录数据结构"""
    step_name: str
    start_time: float
    end_time: float
    duration: float
    parent_step: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

class PerformanceTimer:
    """性能计时器"""
    
    def __init__(self, enable_logging: bool = True):
        self.enable_logging = enable_logging
        self.records: List[TimeRecord] = []
        self.current_steps: Dict[str, float] = {}  # 当前正在执行的步骤
        self.step_stack: List[str] = []  # 步骤调用栈
        self._lock = threading.Lock()
        
        # 性能统计
        self.total_time = 0.0
        self.step_times: Dict[str, List[float]] = {}
        self.step_counts: Dict[str, int] = {}
        
    def start_step(self, step_name: str, metadata: Dict[str, Any] = None) -> str:
        """开始记录一个步骤"""
        with self._lock:
            start_time = time.time()
            self.current_steps[step_name] = start_time
            self.step_stack.append(step_name)
            
            if metadata is None:
                metadata = {}
            
            if self.enable_logging:
                indent = "  " * (len(self.step_stack) - 1)
                logger.info(f"{indent}⏱️  START: {step_name}")
                if metadata:
                    logger.info(f"{indent}📊 元数据: {metadata}")
            
            return step_name
    
    def end_step(self, step_name: str, metadata: Dict[str, Any] = None) -> Optional[TimeRecord]:
        """结束记录一个步骤"""
        with self._lock:
            if step_name not in self.current_steps:
                logger.warning(f"⚠️  步骤 '{step_name}' 未找到，可能已经结束或未开始")
                return None
            
            start_time = self.current_steps[step_name]
            end_time = time.time()
            duration = end_time - start_time
            
            # 从当前步骤中移除
            del self.current_steps[step_name]
            
            # 从调用栈中移除
            if step_name in self.step_stack:
                self.step_stack.remove(step_name)
            
            # 创建时间记录
            parent_step = self.step_stack[-1] if self.step_stack else None
            record = TimeRecord(
                step_name=step_name,
                start_time=start_time,
                end_time=end_time,
                duration=duration,
                parent_step=parent_step,
                metadata=metadata or {}
            )
            
            self.records.append(record)
            
            # 更新统计信息
            if step_name not in self.step_times:
                self.step_times[step_name] = []
                self.step_counts[step_name] = 0
            
            self.step_times[step_name].append(duration)
            self.step_counts[step_name] += 1
            self.total_time += duration
            
            if self.enable_logging:
                indent = "  " * len(self.step_stack)
                logger.info(f"{indent}⏱️  END: {step_name} - {duration*1000:.2f}ms")
                if metadata:
                    logger.info(f"{indent}📊 结果: {metadata}")
            
            return record
    
    @contextmanager
    def time_step(self, step_name: str, metadata: Dict[str, Any] = None):
        """上下文管理器，自动记录步骤时间"""
        self.start_step(step_name, metadata)
        try:
            yield
        finally:
            self.end_step(step_name)
    
    def get_step_summary(self) -> Dict[str, Any]:
        """获取步骤执行摘要"""
        with self._lock:
            summary = {}
            
            for step_name, times in self.step_times.items():
                if times:
                    summary[step_name] = {
                        'count': self.step_counts[step_name],
                        'total_time': sum(times),
                        'avg_time': sum(times) / len(times),
                        'min_time': min(times),
                        'max_time': max(times),
                        'last_time': times[-1] if times else 0
                    }
            
            return summary
    
    def get_performance_report(self) -> Dict[str, Any]:
        """获取性能报告"""
        with self._lock:
            summary = self.get_step_summary()
            
            # 按总时间排序
            sorted_steps = sorted(
                summary.items(), 
                key=lambda x: x[1]['total_time'], 
                reverse=True
            )
            
            report = {
                'total_time': self.total_time,
                'step_count': len(self.records),
                'unique_steps': len(summary),
                'top_slow_steps': sorted_steps[:10],  # 最慢的10个步骤
                'step_summary': summary,
                'recent_records': self.records[-20:] if self.records else []  # 最近20条记录
            }
            
            return report
    
    def print_performance_report(self):
        """打印性能报告"""
        report = self.get_performance_report()
        
        print("\n" + "="*80)
        print("📊 性能分析报告")
        print("="*80)
        
        print(f"⏱️  总执行时间: {report['total_time']:.3f}秒")
        print(f"📈 总步骤数: {report['step_count']}")
        print(f"🔢 唯一步骤数: {report['unique_steps']}")
        
        print(f"\n🐌 最慢的步骤 (Top 10):")
        print("-" * 60)
        print(f"{'步骤名称':<30} {'次数':<8} {'总时间(ms)':<12} {'平均(ms)':<12} {'最大(ms)':<12}")
        print("-" * 60)
        
        for step_name, stats in report['top_slow_steps']:
            print(f"{step_name:<30} {stats['count']:<8} {stats['total_time']*1000:<12.2f} {stats['avg_time']*1000:<12.2f} {stats['max_time']*1000:<12.2f}")
        
        print(f"\n📋 最近执行的步骤:")
        print("-" * 60)
        for record in report['recent_records']:
            indent = "  " * (len(record.step_name.split('.')) - 1)
            print(f"{indent}⏱️  {record.step_name}: {record.duration*1000:.2f}ms")
        
        print("="*80)
    
    def clear_records(self):
        """清空所有记录"""
        with self._lock:
            self.records.clear()
            self.current_steps.clear()
            self.step_stack.clear()
            self.step_times.clear()
            self.step_counts.clear()
            self.total_time = 0.0
    
    def export_to_json(self, filename: str):
        """导出记录到JSON文件"""
        with self._lock:
            data = {
                'records': [
                    {
                        'step_name': record.step_name,
                        'start_time': record.start_time,
                        'end_time': record.end_time,
                        'duration': record.duration,
                        'parent_step': record.parent_step,
                        'metadata': record.metadata
                    }
                    for record in self.records
                ],
                'summary': self.get_step_summary(),
                'performance_report': self.get_performance_report()
            }
            
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"📁 性能记录已导出到: {filename}")

# 全局性能计时器实例
global_timer = PerformanceTimer(enable_logging=True)

def get_timer() -> PerformanceTimer:
    """获取全局性能计时器实例"""
    return global_timer

def start_timing(step_name: str, metadata: Dict[str, Any] = None) -> str:
    """开始计时（便捷函数）"""
    return global_timer.start_step(step_name, metadata)

def end_timing(step_name: str, metadata: Dict[str, Any] = None) -> Optional[TimeRecord]:
    """结束计时（便捷函数）"""
    return global_timer.end_step(step_name, metadata)

def time_step(step_name: str, metadata: Dict[str, Any] = None):
    """计时上下文管理器（便捷函数）"""
    return global_timer.time_step(step_name, metadata)

def print_performance_report():
    """打印性能报告（便捷函数）"""
    global_timer.print_performance_report()

def export_performance_data(filename: str = None):
    """导出性能数据（便捷函数）"""
    if filename is None:
        filename = f"performance_data_{int(time.time())}.json"
    global_timer.export_to_json(filename)
