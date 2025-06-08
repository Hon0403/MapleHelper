# includes/timer_utils.py

import time
from typing import Dict

class TimerUtils:
    """時間相關的共用工具"""
    
    def __init__(self):
        self.timers: Dict[str, float] = {}
    
    def set_timer(self, name: str):
        """設定計時器"""
        self.timers[name] = time.time()
    
    def check_timer(self, name: str, interval: float) -> bool:
        """檢查計時器是否達到間隔時間"""
        if name not in self.timers:
            self.set_timer(name)
            return True
        
        elapsed = time.time() - self.timers[name]
        if elapsed >= interval:
            self.set_timer(name)  # 重置計時器
            return True
        
        return False
    
    def get_elapsed(self, name: str) -> float:
        """獲取計時器經過的時間"""
        if name not in self.timers:
            return 0.0
        return time.time() - self.timers[name]
    
    @staticmethod
    def sleep_with_log(duration: float, message: str = "等待"):
        """帶日誌的延遲"""
        print(f"ℹ️ {message} {duration} 秒")
        time.sleep(duration)
