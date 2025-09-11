#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
缓存管理器 - 提供高性能缓存机制
"""

import time
import threading
from typing import Any, Dict, Optional, Callable
from functools import wraps

class CacheManager:
    """高性能缓存管理器"""
    
    def __init__(self, default_ttl: int = 300):
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.default_ttl = default_ttl
        self.lock = threading.RLock()
    
    def get(self, key: str) -> Optional[Any]:
        """获取缓存值"""
        with self.lock:
            if key in self.cache:
                entry = self.cache[key]
                if time.time() < entry['expires_at']:
                    return entry['value']
                else:
                    # 过期，删除
                    del self.cache[key]
            return None
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """设置缓存值"""
        with self.lock:
            ttl = ttl or self.default_ttl
            self.cache[key] = {
                'value': value,
                'expires_at': time.time() + ttl,
                'created_at': time.time()
            }
    
    def invalidate(self, key: str) -> None:
        """使缓存失效"""
        with self.lock:
            if key in self.cache:
                del self.cache[key]
    
    def clear(self) -> None:
        """清空所有缓存"""
        with self.lock:
            self.cache.clear()
    
    def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息"""
        with self.lock:
            now = time.time()
            active_count = sum(1 for entry in self.cache.values() if now < entry['expires_at'])
            expired_count = len(self.cache) - active_count
            
            return {
                'total_entries': len(self.cache),
                'active_entries': active_count,
                'expired_entries': expired_count,
                'cache_hit_rate': getattr(self, '_hit_count', 0) / max(getattr(self, '_access_count', 1), 1)
            }

# 全局缓存实例
_cache_manager = CacheManager()

def cached(ttl: int = 300, key_func: Optional[Callable] = None):
    """缓存装饰器"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # 生成缓存键
            if key_func:
                cache_key = key_func(*args, **kwargs)
            else:
                cache_key = f"{func.__name__}:{hash(str(args) + str(sorted(kwargs.items())))}"
            
            # 尝试从缓存获取
            cached_result = _cache_manager.get(cache_key)
            if cached_result is not None:
                return cached_result
            
            # 执行函数并缓存结果
            result = func(*args, **kwargs)
            _cache_manager.set(cache_key, result, ttl)
            return result
        
        return wrapper
    return decorator

def get_cache_manager() -> CacheManager:
    """获取缓存管理器实例"""
    return _cache_manager

def clear_cache():
    """清空所有缓存"""
    _cache_manager.clear()

def get_cache_stats() -> Dict[str, Any]:
    """获取缓存统计信息"""
    return _cache_manager.get_stats()
