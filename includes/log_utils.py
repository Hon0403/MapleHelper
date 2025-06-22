# includes/log_utils.py - 日誌和錯誤處理工具

import time
import traceback
from typing import Optional, Any, Callable
from functools import wraps

class Logger:
    """統一日誌處理工具"""
    
    def __init__(self, module_name: str = "Unknown"):
        self.module_name = module_name
    
    def info(self, message: str):
        """信息日誌"""
        timestamp = time.strftime("%H:%M:%S")
        print(f"[{timestamp}] ℹ️ {self.module_name}: {message}")
    
    def success(self, message: str):
        """成功日誌"""
        timestamp = time.strftime("%H:%M:%S")
        print(f"[{timestamp}] ✅ {self.module_name}: {message}")
    
    def warning(self, message: str):
        """警告日誌"""
        timestamp = time.strftime("%H:%M:%S")
        print(f"[{timestamp}] ⚠️ {self.module_name}: {message}")
    
    def error(self, message: str, exception: Optional[Exception] = None):
        """錯誤日誌"""
        timestamp = time.strftime("%H:%M:%S")
        print(f"[{timestamp}] ❌ {self.module_name}: {message}")
        if exception:
            print(f"    └─ 異常: {exception}")
    
    def debug(self, message: str):
        """調試日誌"""
        timestamp = time.strftime("%H:%M:%S")
        print(f"[{timestamp}] 🔍 {self.module_name}: {message}")
    
    def init_success(self, component_name: str):
        """初始化成功日誌"""
        self.success(f"{component_name}已初始化")
    
    def init_error(self, component_name: str, error: Exception):
        """初始化失敗日誌"""
        self.error(f"{component_name}初始化失敗", error)
    
    def operation_success(self, operation: str):
        """操作成功日誌"""
        self.success(f"{operation}成功")
    
    def operation_error(self, operation: str, error: Exception):
        """操作失敗日誌"""
        self.error(f"{operation}失敗", error)

def create_logger(module_name: str) -> Logger:
    """創建模組專用日誌器"""
    return Logger(module_name)

def error_handler(operation: str = "操作"):
    """錯誤處理裝飾器"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                # 嘗試從第一個參數獲取 logger
                logger = None
                if args and hasattr(args[0], 'logger'):
                    logger = args[0].logger
                elif args and hasattr(args[0], '__class__'):
                    logger = create_logger(args[0].__class__.__name__)
                else:
                    logger = create_logger("Unknown")
                
                logger.operation_error(operation, e)
                return None
        return wrapper
    return decorator

def safe_execute(func: Callable, *args, logger: Optional[Logger] = None, 
                operation: str = "操作", **kwargs) -> Optional[Any]:
    """安全執行函數"""
    try:
        result = func(*args, **kwargs)
        if logger:
            logger.operation_success(operation)
        return result
    except Exception as e:
        if logger:
            logger.operation_error(operation, e)
        else:
            print(f"❌ {operation}失敗: {e}")
        return None

class PerformanceLogger:
    """效能日誌工具"""
    
    def __init__(self, logger: Logger):
        self.logger = logger
        self.start_times = {}
    
    def start_timer(self, operation: str):
        """開始計時"""
        self.start_times[operation] = time.time()
    
    def end_timer(self, operation: str, threshold: float = 1.0):
        """結束計時並記錄"""
        if operation in self.start_times:
            duration = time.time() - self.start_times[operation]
            if duration > threshold:
                self.logger.warning(f"{operation}耗時: {duration:.3f}秒")
            else:
                self.logger.debug(f"{operation}耗時: {duration:.3f}秒")
            del self.start_times[operation]
    
    def time_operation(self, operation: str, func: Callable, *args, **kwargs):
        """計時執行操作"""
        self.start_timer(operation)
        try:
            result = func(*args, **kwargs)
            self.end_timer(operation)
            return result
        except Exception as e:
            self.end_timer(operation)
            raise e

# 全域日誌器
def get_logger(module_name: str) -> Logger:
    """獲取模組日誌器"""
    return create_logger(module_name) 