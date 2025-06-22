"""
應用程式主類別 - 負責整體架構和協調
"""

import sys
import time
from typing import Dict, Any, Optional
from PyQt5.QtWidgets import QApplication

from includes.log_utils import get_logger
from includes.config_utils import ConfigUtils
from .component_manager import ComponentManager
from .lifecycle_manager import LifecycleManager


class MapleStoryApplication:
    """MapleStory Helper 應用程式主類別"""
    
    def __init__(self, config_path: str = "configs/bluestacks.yaml"):
        self.logger = get_logger("MapleStoryApplication")
        self.config_path = config_path
        
        # 初始化核心組件
        self.config = self._load_config()
        self.component_manager = ComponentManager(self.config)
        self.lifecycle_manager = LifecycleManager(self.component_manager)
        
        # 應用程式狀態
        self.is_initialized = False
        self.is_running = False
        
        self.logger.info("MapleStory Application 已創建")
    
    def _load_config(self) -> Dict[str, Any]:
        """載入設定檔"""
        try:
            config = ConfigUtils.load_yaml_config(self.config_path)
            if config:
                self.logger.info(f"已載入設定檔: {self.config_path}")
                return config
            else:
                self.logger.warning("設定檔為空，使用預設設定")
                return self._get_default_config()
        except Exception as e:
            self.logger.error(f"載入設定檔失敗: {e}")
            return self._get_default_config()
    
    def _get_default_config(self) -> Dict[str, Any]:
        """獲取預設設定"""
        return {
            "app": {
                "window_title": "BlueStacks App Player",
                "capture_region": [0, 0, 1920, 1080],
                "detection_threshold": 0.3,
                "update_interval": 3000,
                "auto_save": True
            }
        }
    
    def initialize(self) -> bool:
        """初始化應用程式"""
        if self.is_initialized:
            return True
        
        try:
            self.logger.info("開始初始化應用程式...")
            
            # 初始化組件管理器
            if not self.component_manager.initialize():
                self.logger.error("組件管理器初始化失敗")
                return False
            
            # 初始化生命週期管理器
            if not self.lifecycle_manager.initialize():
                self.logger.error("生命週期管理器初始化失敗")
                return False
            
            self.is_initialized = True
            self.logger.info("✅ 應用程式初始化完成")
            return True
            
        except Exception as e:
            self.logger.error(f"應用程式初始化失敗: {e}")
            return False
    
    def start(self) -> bool:
        """啟動應用程式"""
        if not self.is_initialized:
            if not self.initialize():
                return False
        
        if self.is_running:
            return True
        
        try:
            self.logger.info("開始啟動應用程式...")
            
            # 啟動生命週期管理器
            if not self.lifecycle_manager.start():
                self.logger.error("生命週期管理器啟動失敗")
                return False
            
            self.is_running = True
            self.logger.info("✅ 應用程式已啟動")
            return True
            
        except Exception as e:
            self.logger.error(f"應用程式啟動失敗: {e}")
            return False
    
    def stop(self) -> bool:
        """停止應用程式"""
        if not self.is_running:
            return True
        
        try:
            self.logger.info("開始停止應用程式...")
            
            # 停止生命週期管理器
            if not self.lifecycle_manager.stop():
                self.logger.error("生命週期管理器停止失敗")
                return False
            
            self.is_running = False
            self.logger.info("✅ 應用程式已停止")
            return True
            
        except Exception as e:
            self.logger.error(f"應用程式停止失敗: {e}")
            return False
    
    def cleanup(self):
        """清理應用程式資源"""
        try:
            self.logger.info("開始清理應用程式資源...")
            
            # 清理生命週期管理器
            self.lifecycle_manager.cleanup()
            
            # 清理組件管理器
            self.component_manager.cleanup()
            
            self.logger.info("✅ 應用程式資源清理完成")
            
        except Exception as e:
            self.logger.error(f"應用程式清理失敗: {e}")
    
    def get_status(self) -> Dict[str, Any]:
        """獲取應用程式狀態"""
        return {
            'initialized': self.is_initialized,
            'running': self.is_running,
            'components': self.component_manager.get_status(),
            'lifecycle': self.lifecycle_manager.get_status()
        }
    
    def get_component(self, component_name: str):
        """獲取指定組件"""
        return self.component_manager.get_component(component_name)
    
    def get_config(self) -> Dict[str, Any]:
        """獲取設定檔"""
        return self.config


def create_application(config_path: str = "configs/bluestacks.yaml") -> MapleStoryApplication:
    """創建應用程式實例"""
    return MapleStoryApplication(config_path) 