"""
組件管理器 - 負責管理所有系統組件的生命週期
"""

import time
from typing import Dict, Any, Optional, List
from includes.log_utils import get_logger
from includes.base_classes import ConfigurableComponent


class ComponentManager:
    """組件管理器 - 統一管理所有系統組件"""
    
    def __init__(self, config: Dict[str, Any]):
        self.logger = get_logger("ComponentManager")
        self.config = config
        
        # 組件註冊表
        self.components: Dict[str, Any] = {}
        self.component_configs: Dict[str, Dict[str, Any]] = {}
        
        # 組件依賴關係
        self.dependencies: Dict[str, List[str]] = {
            'capturer': [],
            'tracker': ['capturer'],
            'combat': ['tracker', 'waypoint_system'],
            'waypoint_system': [],
            'health_detector': [],
            'gui': ['capturer', 'tracker', 'combat', 'waypoint_system'],
            'editor': ['waypoint_system', 'tracker']
        }
        
        # 組件初始化順序
        self.init_order = [
            'capturer',
            'waypoint_system', 
            'tracker',
            'health_detector',
            'combat',
            'gui',
            'editor'
        ]
        
        self.is_initialized = False
        self.logger.info("組件管理器已創建")
    
    def register_component(self, name: str, component: Any, config_section: str = None):
        """註冊組件"""
        try:
            self.components[name] = component
            if config_section:
                self.component_configs[name] = self.config.get(config_section, {})
            else:
                self.component_configs[name] = {}
            
            self.logger.info(f"✅ 組件已註冊: {name}")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ 註冊組件失敗 {name}: {e}")
            return False
    
    def get_component(self, name: str):
        """獲取組件"""
        return self.components.get(name)
    
    def initialize(self) -> bool:
        """初始化所有組件"""
        if self.is_initialized:
            return True
        
        try:
            self.logger.info("開始初始化組件...")
            
            # 按順序初始化組件
            for component_name in self.init_order:
                if component_name in self.components:
                    if not self._initialize_component(component_name):
                        self.logger.error(f"組件初始化失敗: {component_name}")
                        return False
            
            self.is_initialized = True
            self.logger.info("✅ 所有組件初始化完成")
            return True
            
        except Exception as e:
            self.logger.error(f"組件初始化失敗: {e}")
            return False
    
    def _initialize_component(self, component_name: str) -> bool:
        """初始化單個組件"""
        try:
            component = self.components[component_name]
            self.logger.info(f"初始化組件: {component_name}")
            
            # 檢查依賴
            if not self._check_dependencies(component_name):
                self.logger.error(f"組件依賴檢查失敗: {component_name}")
                return False
            
            # 初始化組件
            if hasattr(component, 'initialize'):
                if not component.initialize():
                    self.logger.error(f"組件初始化失敗: {component_name}")
                    return False
            
            self.logger.info(f"✅ 組件初始化成功: {component_name}")
            return True
            
        except Exception as e:
            self.logger.error(f"初始化組件失敗 {component_name}: {e}")
            return False
    
    def _check_dependencies(self, component_name: str) -> bool:
        """檢查組件依賴"""
        if component_name not in self.dependencies:
            return True
        
        required_deps = self.dependencies[component_name]
        for dep in required_deps:
            if dep not in self.components:
                self.logger.error(f"缺少依賴組件: {component_name} -> {dep}")
                return False
            
            # 檢查依賴組件是否已初始化
            dep_component = self.components[dep]
            if hasattr(dep_component, 'is_initialized') and not dep_component.is_initialized:
                self.logger.error(f"依賴組件未初始化: {component_name} -> {dep}")
                return False
        
        return True
    
    def start(self) -> bool:
        """啟動所有組件"""
        try:
            self.logger.info("開始啟動組件...")
            
            for component_name in self.init_order:
                if component_name in self.components:
                    if not self._start_component(component_name):
                        self.logger.error(f"組件啟動失敗: {component_name}")
                        return False
            
            self.logger.info("✅ 所有組件啟動完成")
            return True
            
        except Exception as e:
            self.logger.error(f"組件啟動失敗: {e}")
            return False
    
    def _start_component(self, component_name: str) -> bool:
        """啟動單個組件"""
        try:
            component = self.components[component_name]
            
            if hasattr(component, 'start'):
                if not component.start():
                    self.logger.error(f"組件啟動失敗: {component_name}")
                    return False
            
            self.logger.info(f"✅ 組件啟動成功: {component_name}")
            return True
            
        except Exception as e:
            self.logger.error(f"啟動組件失敗 {component_name}: {e}")
            return False
    
    def stop(self) -> bool:
        """停止所有組件"""
        try:
            self.logger.info("開始停止組件...")
            
            # 反向停止組件
            for component_name in reversed(self.init_order):
                if component_name in self.components:
                    self._stop_component(component_name)
            
            self.logger.info("✅ 所有組件停止完成")
            return True
            
        except Exception as e:
            self.logger.error(f"組件停止失敗: {e}")
            return False
    
    def _stop_component(self, component_name: str):
        """停止單個組件"""
        try:
            component = self.components[component_name]
            
            if hasattr(component, 'stop'):
                component.stop()
            
            self.logger.info(f"✅ 組件停止成功: {component_name}")
            
        except Exception as e:
            self.logger.error(f"停止組件失敗 {component_name}: {e}")
    
    def cleanup(self):
        """清理所有組件"""
        try:
            self.logger.info("開始清理組件...")
            
            # 反向清理組件
            for component_name in reversed(self.init_order):
                if component_name in self.components:
                    self._cleanup_component(component_name)
            
            self.components.clear()
            self.component_configs.clear()
            self.is_initialized = False
            
            self.logger.info("✅ 所有組件清理完成")
            
        except Exception as e:
            self.logger.error(f"組件清理失敗: {e}")
    
    def _cleanup_component(self, component_name: str):
        """清理單個組件"""
        try:
            component = self.components[component_name]
            
            if hasattr(component, 'cleanup'):
                component.cleanup()
            
            self.logger.info(f"✅ 組件清理成功: {component_name}")
            
        except Exception as e:
            self.logger.error(f"清理組件失敗 {component_name}: {e}")
    
    def get_status(self) -> Dict[str, Any]:
        """獲取組件狀態"""
        status = {}
        for name, component in self.components.items():
            if hasattr(component, 'get_status'):
                status[name] = component.get_status()
            else:
                status[name] = {
                    'name': name,
                    'initialized': getattr(component, 'is_initialized', False),
                    'running': getattr(component, 'is_running', False)
                }
        return status
    
    def get_component_config(self, component_name: str) -> Dict[str, Any]:
        """獲取組件設定"""
        return self.component_configs.get(component_name, {}) 