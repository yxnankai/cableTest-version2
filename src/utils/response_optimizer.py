#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
API响应优化器 - 提供高性能API响应机制
"""

import time
import json
from typing import Any, Dict, List, Optional
from functools import wraps
from flask import jsonify, request
from .cache_manager import cached, get_cache_manager

class ResponseOptimizer:
    """API响应优化器"""
    
    def __init__(self):
        self.cache = get_cache_manager()
        self.response_times = []
        self.max_response_time = 0.1  # 100ms目标响应时间
    
    def optimize_json_response(self, data: Any, status_code: int = 200) -> tuple:
        """优化JSON响应"""
        start_time = time.time()
        
        # 如果数据是字典，添加性能信息
        if isinstance(data, dict):
            data['_performance'] = {
                'response_time': 0,  # 将在最后更新
                'cached': False,
                'timestamp': time.time()
            }
        
        # 序列化JSON
        try:
            json_data = json.dumps(data, ensure_ascii=False, separators=(',', ':'))
            response_time = time.time() - start_time
            
            # 更新性能信息
            if isinstance(data, dict) and '_performance' in data:
                data['_performance']['response_time'] = response_time
            
            # 记录响应时间
            self.response_times.append(response_time)
            if len(self.response_times) > 100:  # 只保留最近100次
                self.response_times.pop(0)
            
            return json_data, status_code
            
        except Exception as e:
            error_response = {
                'success': False,
                'error': f'JSON序列化失败: {str(e)}',
                '_performance': {
                    'response_time': time.time() - start_time,
                    'cached': False,
                    'timestamp': time.time()
                }
            }
            return json.dumps(error_response, ensure_ascii=False), 500
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """获取性能统计"""
        if not self.response_times:
            return {'avg_response_time': 0, 'max_response_time': 0, 'total_requests': 0}
        
        return {
            'avg_response_time': sum(self.response_times) / len(self.response_times),
            'max_response_time': max(self.response_times),
            'min_response_time': min(self.response_times),
            'total_requests': len(self.response_times),
            'slow_requests': sum(1 for t in self.response_times if t > self.max_response_time)
        }

# 全局优化器实例
_optimizer = ResponseOptimizer()

def optimized_response(data: Any, status_code: int = 200) -> tuple:
    """优化的响应函数"""
    return _optimizer.optimize_json_response(data, status_code)

def api_cache(ttl: int = 60, key_func: Optional[callable] = None):
    """API缓存装饰器"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # 生成缓存键
            if key_func:
                cache_key = key_func(*args, **kwargs)
            else:
                # 基于请求参数生成缓存键
                cache_key = f"{func.__name__}:{request.method}:{request.path}:{hash(str(request.args) + str(request.get_json(silent=True) or {}))}"
            
            # 尝试从缓存获取
            cached_result = _optimizer.cache.get(cache_key)
            if cached_result is not None:
                # 标记为缓存响应
                if isinstance(cached_result, dict):
                    cached_result['_performance'] = cached_result.get('_performance', {})
                    cached_result['_performance']['cached'] = True
                return jsonify(cached_result)
            
            # 执行函数
            result = func(*args, **kwargs)
            
            # 缓存结果
            if isinstance(result, tuple) and len(result) == 2:
                data, status_code = result
                if status_code == 200:  # 只缓存成功响应
                    _optimizer.cache.set(cache_key, data, ttl)
                return jsonify(data), status_code
            else:
                if isinstance(result, dict) and result.get('success', True):
                    _optimizer.cache.set(cache_key, result, ttl)
                return jsonify(result)
        
        return wrapper
    return decorator

def get_performance_stats() -> Dict[str, Any]:
    """获取性能统计信息"""
    return _optimizer.get_performance_stats()

def clear_api_cache():
    """清空API缓存"""
    _optimizer.cache.clear()
