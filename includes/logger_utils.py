# includes/logger_utils.py

import time
from typing import Any
from enum import Enum

class LogLevel(Enum):
    DEBUG = "🔧"
    INFO = "ℹ️"
    SUCCESS = "✅"
    WARNING = "⚠️"
    ERROR = "❌"
    COMBAT = "⚔️"
    ADB = "🎮"

class Logger:
    """統一的日誌處理工具"""
    
    @staticmethod
    def log(level: LogLevel, message: str, details: Any = None):
        """統一日誌輸出格式"""
        timestamp = time.strftime("%H:%M:%S")
        log_msg = f"[{timestamp}] {level.value} {message}"
        
        if details:
            log_msg += f": {details}"
        
        print(log_msg)
    
    @staticmethod
    def debug(message: str, details: Any = None):
        Logger.log(LogLevel.DEBUG, message, details)
    
    @staticmethod
    def info(message: str, details: Any = None):
        Logger.log(LogLevel.INFO, message, details)
    
    @staticmethod
    def success(message: str, details: Any = None):
        Logger.log(LogLevel.SUCCESS, message, details)
    
    @staticmethod
    def warning(message: str, details: Any = None):
        Logger.log(LogLevel.WARNING, message, details)
    
    @staticmethod
    def error(message: str, details: Any = None):
        Logger.log(LogLevel.ERROR, message, details)
    
    @staticmethod
    def combat(message: str, details: Any = None):
        Logger.log(LogLevel.COMBAT, message, details)
    
    @staticmethod
    def adb(message: str, details: Any = None):
        Logger.log(LogLevel.ADB, message, details)
