"""
組件適配器 - 讓現有組件與新架構相容
"""

from typing import Dict, Any, Optional
from includes.base_classes import BaseComponent
from includes.log_utils import get_logger


class ComponentAdapter(BaseComponent):
    """組件適配器 - 讓現有組件與新架構相容"""
    
    def __init__(self, name: str, component: Any, config: Optional[Dict] = None):
        super().__init__(name, config)
        self.component = component
        self.logger = get_logger(f"ComponentAdapter.{name}")
        
        # 檢查組件是否有必要的屬性
        self._check_component_interface()
    
    def _check_component_interface(self):
        """檢查組件介面"""
        required_attrs = ['is_enabled', 'is_running']
        optional_attrs = ['initialize', 'start', 'stop', 'cleanup', 'get_status']
        
        for attr in required_attrs:
            if not hasattr(self.component, attr):
                self.logger.warning(f"組件缺少必要屬性: {attr}")
        
        for attr in optional_attrs:
            if not hasattr(self.component, attr):
                self.logger.info(f"組件缺少可選方法: {attr}")
    
    def _do_initialize(self) -> bool:
        """初始化組件"""
        try:
            if hasattr(self.component, 'initialize'):
                return self.component.initialize()
            else:
                # 如果組件沒有 initialize 方法，假設已經初始化
                self.logger.info(f"組件 {self.name} 沒有 initialize 方法，假設已初始化")
                return True
        except Exception as e:
            self.logger.error(f"初始化組件 {self.name} 失敗: {e}")
            return False
    
    def _do_start(self) -> bool:
        """啟動組件"""
        try:
            if hasattr(self.component, 'start'):
                return self.component.start()
            else:
                # 如果組件沒有 start 方法，假設已經啟動
                self.logger.info(f"組件 {self.name} 沒有 start 方法，假設已啟動")
                return True
        except Exception as e:
            self.logger.error(f"啟動組件 {self.name} 失敗: {e}")
            return False
    
    def _do_stop(self) -> bool:
        """停止組件"""
        try:
            if hasattr(self.component, 'stop'):
                return self.component.stop()
            else:
                # 如果組件沒有 stop 方法，假設已經停止
                self.logger.info(f"組件 {self.name} 沒有 stop 方法，假設已停止")
                return True
        except Exception as e:
            self.logger.error(f"停止組件 {self.name} 失敗: {e}")
            return False
    
    def _do_cleanup(self) -> None:
        """清理組件"""
        try:
            if hasattr(self.component, 'cleanup'):
                self.component.cleanup()
            else:
                self.logger.info(f"組件 {self.name} 沒有 cleanup 方法")
        except Exception as e:
            self.logger.error(f"清理組件 {self.name} 失敗: {e}")
    
    def get_status(self) -> Dict[str, Any]:
        """獲取組件狀態"""
        try:
            if hasattr(self.component, 'get_status'):
                status = self.component.get_status()
                status['name'] = self.name
                return status
            else:
                # 基本狀態
                return {
                    'name': self.name,
                    'initialized': getattr(self.component, 'is_initialized', False),
                    'running': getattr(self.component, 'is_running', False),
                    'enabled': getattr(self.component, 'is_enabled', False)
                }
        except Exception as e:
            self.logger.error(f"獲取組件 {self.name} 狀態失敗: {e}")
            return {
                'name': self.name,
                'error': str(e)
            }
    
    def __getattr__(self, name):
        """代理其他屬性到原始組件"""
        if hasattr(self.component, name):
            return getattr(self.component, name)
        else:
            raise AttributeError(f"'{self.__class__.__name__}' object has no attribute '{name}'")
    
    def __call__(self, *args, **kwargs):
        """如果組件是可調用的，代理調用"""
        if callable(self.component):
            return self.component(*args, **kwargs)
        else:
            raise TypeError(f"'{self.__class__.__name__}' object is not callable")


class AppAdapter:
    """應用程式適配器 - 讓舊的 GUI 與新的應用程式架構相容"""
    
    def __init__(self, app, capturer, tracker, waypoint_system, health_detector, combat):
        self.app = app
        self.capturer = capturer
        self.tracker = tracker
        self.waypoint_system = waypoint_system
        self.health_detector = health_detector
        self.combat = combat
        
        # 為了向後相容，添加 adb 屬性
        self.adb = capturer.adb if hasattr(capturer, 'adb') else None
        
        # 添加 monster_detector
        from includes.simple_template_utils import monster_detector
        self.monster_detector = monster_detector
        
        # 添加其他必要的屬性
        self.is_enabled = False
        self._running = False
    
    def get_component(self, name):
        """獲取組件"""
        return self.app.get_component(name)
    
    def get_config(self):
        """獲取設定檔"""
        return self.app.get_config()
    
    def get_status(self):
        """獲取狀態"""
        return self.app.get_status()
    
    def start(self):
        """啟動應用程式"""
        return self.app.start()
    
    def stop(self):
        """停止應用程式"""
        return self.app.stop()
    
    def toggle_tracking(self):
        """切換追蹤"""
        self.is_enabled = not self.is_enabled
        return self.is_enabled
    
    def toggle_combat(self):
        """切換戰鬥"""
        if hasattr(self.combat, 'is_enabled'):
            if self.combat.is_enabled:
                self.combat.stop()
                return False
            else:
                self.combat.start()
                return True
        return False
    
    def open_editor(self):
        """開啟編輯器"""
        # 這個方法會在 main_new.py 中實現
        pass


def create_component_adapter(name: str, component: Any, config: Optional[Dict] = None) -> ComponentAdapter:
    """創建組件適配器"""
    return ComponentAdapter(name, component, config) 