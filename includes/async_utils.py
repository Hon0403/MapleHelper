# includes/async_utils.py - 異步和緩存管理工具

import threading
import queue
import time
from typing import Any, Callable, Optional, Dict, List
from dataclasses import dataclass
from includes.log_utils import get_logger

@dataclass
class CacheItem:
    """緩存項目"""
    data: Any
    timestamp: float
    ttl: float  # 存活時間

class CacheManager:
    """緩存管理器"""
    
    def __init__(self, default_ttl: float = 1.0):
        self.cache: Dict[str, CacheItem] = {}
        self.default_ttl = default_ttl
        self.logger = get_logger("CacheManager")
    
    def set(self, key: str, data: Any, ttl: Optional[float] = None) -> None:
        """設置緩存"""
        if ttl is None:
            ttl = self.default_ttl
        
        self.cache[key] = CacheItem(
            data=data,
            timestamp=time.time(),
            ttl=ttl
        )
    
    def get(self, key: str) -> Optional[Any]:
        """獲取緩存"""
        if key not in self.cache:
            return None
        
        item = self.cache[key]
        if time.time() - item.timestamp > item.ttl:
            # 過期，刪除
            del self.cache[key]
            return None
        
        return item.data
    
    def clear(self) -> None:
        """清空緩存"""
        self.cache.clear()
        self.logger.info("緩存已清空")
    
    def cleanup_expired(self) -> None:
        """清理過期項目"""
        current_time = time.time()
        expired_keys = [
            key for key, item in self.cache.items()
            if current_time - item.timestamp > item.ttl
        ]
        
        for key in expired_keys:
            del self.cache[key]
        
        if expired_keys:
            self.logger.debug(f"清理了 {len(expired_keys)} 個過期緩存項目")

class AsyncTaskManager:
    """異步任務管理器"""
    
    def __init__(self, max_workers: int = 5):
        self.max_workers = max_workers
        self.tasks: Dict[str, threading.Thread] = {}
        self.task_queues: Dict[str, queue.Queue] = {}
        self.running = False
        self.logger = get_logger("AsyncTaskManager")
    
    def create_task(self, task_name: str, target_func: Callable, 
                   daemon: bool = True, **kwargs) -> threading.Thread:
        """創建異步任務"""
        if task_name in self.tasks and self.tasks[task_name].is_alive():
            self.logger.warning(f"任務 {task_name} 已在運行中")
            return self.tasks[task_name]
        
        thread = threading.Thread(
            target=target_func,
            name=task_name,
            daemon=daemon,
            kwargs=kwargs
        )
        
        self.tasks[task_name] = thread
        self.logger.info(f"創建異步任務: {task_name}")
        return thread
    
    def start_task(self, task_name: str) -> bool:
        """啟動任務"""
        if task_name not in self.tasks:
            self.logger.error(f"任務 {task_name} 不存在")
            return False
        
        thread = self.tasks[task_name]
        if thread.is_alive():
            self.logger.warning(f"任務 {task_name} 已在運行中")
            return True
        
        thread.start()
        self.logger.info(f"啟動任務: {task_name}")
        return True
    
    def stop_task(self, task_name: str, timeout: float = 5.0) -> bool:
        """停止任務"""
        if task_name not in self.tasks:
            return False
        
        thread = self.tasks[task_name]
        if not thread.is_alive():
            return True
        
        # 設置停止標誌（如果任務支援）
        if hasattr(thread, '_stop_event'):
            thread._stop_event.set()
        
        thread.join(timeout=timeout)
        
        if thread.is_alive():
            self.logger.warning(f"任務 {task_name} 停止超時")
            return False
        
        self.logger.info(f"停止任務: {task_name}")
        return True
    
    def stop_all_tasks(self) -> None:
        """停止所有任務"""
        for task_name in list(self.tasks.keys()):
            self.stop_task(task_name)
        self.logger.info("所有任務已停止")
    
    def get_task_status(self) -> Dict[str, bool]:
        """獲取所有任務狀態"""
        return {
            name: thread.is_alive() 
            for name, thread in self.tasks.items()
        }

class QueueManager:
    """佇列管理器"""
    
    def __init__(self, max_size: int = 10):
        self.max_size = max_size
        self.queues: Dict[str, queue.Queue] = {}
        self.logger = get_logger("QueueManager")
    
    def create_queue(self, queue_name: str, max_size: Optional[int] = None) -> queue.Queue:
        """創建佇列"""
        if max_size is None:
            max_size = self.max_size
        
        if queue_name in self.queues:
            self.logger.warning(f"佇列 {queue_name} 已存在")
            return self.queues[queue_name]
        
        q = queue.Queue(maxsize=max_size)
        self.queues[queue_name] = q
        self.logger.info(f"創建佇列: {queue_name} (max_size={max_size})")
        return q
    
    def get_queue(self, queue_name: str) -> Optional[queue.Queue]:
        """獲取佇列"""
        return self.queues.get(queue_name)
    
    def clear_queue(self, queue_name: str) -> bool:
        """清空佇列"""
        if queue_name not in self.queues:
            return False
        
        q = self.queues[queue_name]
        while not q.empty():
            try:
                q.get_nowait()
            except queue.Empty:
                break
        
        self.logger.info(f"清空佇列: {queue_name}")
        return True
    
    def clear_all_queues(self) -> None:
        """清空所有佇列"""
        for queue_name in list(self.queues.keys()):
            self.clear_queue(queue_name)
        self.logger.info("所有佇列已清空")

class AsyncWorker:
    """異步工作器基類"""
    
    def __init__(self, name: str, config: Optional[Dict] = None):
        self.name = name
        self.config = config or {}
        self.logger = get_logger(name)
        self.task_manager = AsyncTaskManager()
        self.queue_manager = QueueManager()
        self.cache_manager = CacheManager()
        self.running = False
    
    def start(self) -> bool:
        """啟動工作器"""
        if self.running:
            self.logger.warning("工作器已在運行中")
            return True
        
        self.running = True
        self.logger.info("工作器已啟動")
        return True
    
    def stop(self) -> bool:
        """停止工作器"""
        if not self.running:
            return True
        
        self.running = False
        self.task_manager.stop_all_tasks()
        self.queue_manager.clear_all_queues()
        self.cache_manager.clear()
        self.logger.info("工作器已停止")
        return True
    
    def is_running(self) -> bool:
        """檢查是否運行中"""
        return self.running

# 全域管理器實例
cache_manager = CacheManager()
task_manager = AsyncTaskManager()
queue_manager = QueueManager()

def get_cache_manager() -> CacheManager:
    """獲取全域緩存管理器"""
    return cache_manager

def get_task_manager() -> AsyncTaskManager:
    """獲取全域任務管理器"""
    return task_manager

def get_queue_manager() -> QueueManager:
    """獲取全域佇列管理器"""
    return queue_manager 