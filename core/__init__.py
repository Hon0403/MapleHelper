"""
核心模組 - 提供應用程式的主要架構和生命週期管理
"""

from .application import MapleStoryApplication
from .component_manager import ComponentManager
from .lifecycle_manager import LifecycleManager

__all__ = [
    'MapleStoryApplication',
    'ComponentManager', 
    'LifecycleManager'
] 