# includes/base_classes.py - 基底類別

from typing import Dict, Optional, Any
from includes.config_utils import ConfigSection
from includes.log_utils import get_logger
from includes.async_utils import AsyncWorker, CacheManager
from includes.data_utils import get_data_manager

class BaseComponent:
    """元件基底類別"""
    
    def __init__(self, name: str, config: Optional[Dict] = None):
        self.name = name
        self.config = config or {}
        self.logger = get_logger(name)
        self.data_manager = get_data_manager()
        self.cache_manager = CacheManager()
        
        # 初始化配置區段
        self._init_config_sections()
        
        # 初始化狀態
        self._initialized = False
        self._running = False
    
    def _init_config_sections(self):
        """初始化配置區段 - 子類別可覆寫"""
        pass
    
    def initialize(self) -> bool:
        """初始化元件"""
        if self._initialized:
            return True
        
        try:
            success = self._do_initialize()
            if success:
                self._initialized = True
                self.logger.init_success(self.name)
            return success
        except Exception as e:
            self.logger.init_error(self.name, e)
            return False
    
    def _do_initialize(self) -> bool:
        """實際初始化邏輯 - 子類別必須實作"""
        raise NotImplementedError("子類別必須實作 _do_initialize")
    
    def start(self) -> bool:
        """啟動元件"""
        if not self._initialized:
            if not self.initialize():
                return False
        
        if self._running:
            self.logger.warning("元件已在運行中")
            return True
        
        try:
            success = self._do_start()
            if success:
                self._running = True
                self.logger.info(f"{self.name}已啟動")
            return success
        except Exception as e:
            self.logger.error(f"啟動{self.name}失敗", e)
            return False
    
    def _do_start(self) -> bool:
        """實際啟動邏輯 - 子類別可覆寫"""
        return True
    
    def stop(self) -> bool:
        """停止元件"""
        if not self._running:
            return True
        
        try:
            success = self._do_stop()
            if success:
                self._running = False
                self.logger.info(f"{self.name}已停止")
            return success
        except Exception as e:
            self.logger.error(f"停止{self.name}失敗", e)
            return False
    
    def _do_stop(self) -> bool:
        """實際停止邏輯 - 子類別可覆寫"""
        return True
    
    def cleanup(self) -> None:
        """清理資源"""
        try:
            self.stop()
            self.cache_manager.clear()
            self._do_cleanup()
            self.logger.info(f"{self.name}已清理")
        except Exception as e:
            self.logger.error(f"清理{self.name}失敗", e)
    
    def _do_cleanup(self) -> None:
        """實際清理邏輯 - 子類別可覆寫"""
        pass
    
    def is_initialized(self) -> bool:
        """檢查是否已初始化"""
        return self._initialized
    
    def is_running(self) -> bool:
        """檢查是否運行中"""
        return self._running
    
    def get_status(self) -> Dict[str, Any]:
        """獲取元件狀態"""
        return {
            'name': self.name,
            'initialized': self._initialized,
            'running': self._running
        }

class ConfigurableComponent(BaseComponent):
    """可配置元件基底類別"""
    
    def __init__(self, name: str, config: Optional[Dict] = None, config_section: str = ""):
        super().__init__(name, config)
        self.config_section = config_section
        self.config_data = config.get(config_section, {}) if config else {}
    
    def get_config(self, key: str, default: Any = None) -> Any:
        """獲取配置值"""
        return self.config_data.get(key, default)
    
    def get_config_int(self, key: str, default: int = 0) -> int:
        """獲取整數配置值"""
        value = self.config_data.get(key, default)
        try:
            return int(value)
        except (ValueError, TypeError):
            return default
    
    def get_config_float(self, key: str, default: float = 0.0) -> float:
        """獲取浮點數配置值"""
        value = self.config_data.get(key, default)
        try:
            return float(value)
        except (ValueError, TypeError):
            return default
    
    def get_config_bool(self, key: str, default: bool = False) -> bool:
        """獲取布林值配置值"""
        value = self.config_data.get(key, default)
        if isinstance(value, bool):
            return value
        return str(value).lower() in ('true', '1', 'yes', 'on')
    
    def get_config_list(self, key: str, default: list = None) -> list:
        """獲取列表配置值"""
        if default is None:
            default = []
        value = self.config_data.get(key, default)
        return list(value) if isinstance(value, (list, tuple)) else default
    
    def get_config_dict(self, key: str, default: dict = None) -> dict:
        """獲取字典配置值"""
        if default is None:
            default = {}
        value = self.config_data.get(key, default)
        return dict(value) if isinstance(value, dict) else default

class AsyncComponent(ConfigurableComponent, AsyncWorker):
    """異步元件基底類別"""
    
    def __init__(self, name: str, config: Optional[Dict] = None, config_section: str = ""):
        ConfigurableComponent.__init__(self, name, config, config_section)
        AsyncWorker.__init__(self, name, config)
    
    def _do_start(self) -> bool:
        """啟動異步元件"""
        return AsyncWorker.start(self)
    
    def _do_stop(self) -> bool:
        """停止異步元件"""
        return AsyncWorker.stop(self)
    
    def _do_cleanup(self) -> None:
        """清理異步元件"""
        AsyncWorker.stop(self)

class GUIMixin:
    """GUI 混入類別"""
    
    def __init__(self):
        self.gui_elements = {}
        self.gui_callbacks = {}
    
    def create_button(self, name: str, text: str, callback: callable, **kwargs):
        """創建按鈕"""
        from PyQt5.QtWidgets import QPushButton
        
        button = QPushButton(text)
        button.clicked.connect(callback)
        
        # 設置額外屬性
        for key, value in kwargs.items():
            if hasattr(button, key):
                setattr(button, key, value)
        
        self.gui_elements[name] = button
        self.gui_callbacks[name] = callback
        return button
    
    def create_label(self, name: str, text: str = "", **kwargs):
        """創建標籤"""
        from PyQt5.QtWidgets import QLabel
        
        label = QLabel(text)
        
        # 設置額外屬性
        for key, value in kwargs.items():
            if hasattr(label, key):
                setattr(label, key, value)
        
        self.gui_elements[name] = label
        return label
    
    def create_checkbox(self, name: str, text: str, callback: callable = None, **kwargs):
        """創建複選框"""
        from PyQt5.QtWidgets import QCheckBox
        
        checkbox = QCheckBox(text)
        if callback:
            checkbox.stateChanged.connect(callback)
        
        # 設置額外屬性
        for key, value in kwargs.items():
            if hasattr(checkbox, key):
                setattr(checkbox, key, value)
        
        self.gui_elements[name] = checkbox
        if callback:
            self.gui_callbacks[name] = callback
        return checkbox
    
    def get_gui_element(self, name: str):
        """獲取 GUI 元素"""
        return self.gui_elements.get(name)
    
    def update_gui_element(self, name: str, **kwargs):
        """更新 GUI 元素"""
        element = self.gui_elements.get(name)
        if element:
            for key, value in kwargs.items():
                if hasattr(element, key):
                    setattr(element, key, value)

class PerformanceMixin:
    """效能監控混入類別"""
    
    def __init__(self):
        self.performance_stats = {
            'operation_count': 0,
            'total_time': 0.0,
            'avg_time': 0.0,
            'max_time': 0.0,
            'min_time': float('inf')
        }
        self.operation_timers = {}
    
    def start_timer(self, operation: str):
        """開始計時"""
        import time
        self.operation_timers[operation] = time.time()
    
    def end_timer(self, operation: str):
        """結束計時並更新統計"""
        import time
        if operation in self.operation_timers:
            duration = time.time() - self.operation_timers[operation]
            self._update_performance_stats(duration)
            del self.operation_timers[operation]
    
    def _update_performance_stats(self, duration: float):
        """更新效能統計"""
        stats = self.performance_stats
        stats['operation_count'] += 1
        stats['total_time'] += duration
        stats['avg_time'] = stats['total_time'] / stats['operation_count']
        stats['max_time'] = max(stats['max_time'], duration)
        stats['min_time'] = min(stats['min_time'], duration)
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """獲取效能統計"""
        return self.performance_stats.copy()
    
    def reset_performance_stats(self):
        """重置效能統計"""
        self.performance_stats = {
            'operation_count': 0,
            'total_time': 0.0,
            'avg_time': 0.0,
            'max_time': 0.0,
            'min_time': float('inf')
        } 