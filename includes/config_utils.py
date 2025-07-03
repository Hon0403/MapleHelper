# includes/config_utils.py

import yaml
import json
import os
from typing import Dict, Any, Optional, Union
import logging

logger = logging.getLogger(__name__)

class ConfigUtils:
    """配置檔案處理共用工具"""
    
    @staticmethod
    def load_yaml_config(config_path: str, default_config: Dict[str, Any] = None) -> Dict[str, Any]:
        """載入 YAML 配置檔，失敗時返回預設配置"""
        try:
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = yaml.safe_load(f)
                    if config:
                        return config
            
            # 檔案不存在或為空，使用預設配置
            if default_config:
                ConfigUtils.save_yaml_config(config_path, default_config)
                return default_config
            
            return {}
            
        except Exception as e:
            logger.error(f"載入配置失敗 {config_path}: {e}")
            return default_config or {}
    
    @staticmethod
    def save_yaml_config(config_path: str, config: Dict[str, Any]) -> bool:
        """保存 YAML 配置檔"""
        try:
            os.makedirs(os.path.dirname(config_path), exist_ok=True)
            with open(config_path, 'w', encoding='utf-8') as f:
                yaml.dump(config, f, default_flow_style=False, allow_unicode=True)
            return True
        except Exception as e:
            logger.error(f"保存配置失敗 {config_path}: {e}")
            return False
    
    @staticmethod
    def load_json_config(config_path: str, default_config: Dict[str, Any] = None) -> Dict[str, Any]:
        """載入 JSON 配置檔"""
        try:
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    return config
            
            if default_config:
                ConfigUtils.save_json_config(config_path, default_config)
                return default_config
            
            return {}
            
        except Exception as e:
            logger.error(f"載入 JSON 配置失敗 {config_path}: {e}")
            return default_config or {}
    
    @staticmethod
    def save_json_config(config_path: str, config: Dict[str, Any]) -> bool:
        """保存 JSON 配置檔"""
        try:
            os.makedirs(os.path.dirname(config_path), exist_ok=True)
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            logger.error(f"保存 JSON 配置失敗 {config_path}: {e}")
            return False
    
    @staticmethod
    def merge_configs(base_config: Dict[str, Any], override_config: Dict[str, Any]) -> Dict[str, Any]:
        """合併配置（override_config 覆蓋 base_config）"""
        merged = base_config.copy()
        merged.update(override_config)
        return merged

class ConfigSection:
    """配置區段讀取工具 - 簡化參數讀取"""
    
    def __init__(self, config: Dict, section_name: str):
        self.config = config
        self.section_name = section_name
        self.section = config.get(section_name, {}) if config else {}
    
    def get(self, key: str, default: Any = None) -> Any:
        """從配置區段讀取參數"""
        return self.section.get(key, default)
    
    def get_int(self, key: str, default: int = 0) -> int:
        """讀取整數參數"""
        value = self.section.get(key, default)
        try:
            return int(value)
        except (ValueError, TypeError):
            return default
    
    def get_float(self, key: str, default: float = 0.0) -> float:
        """讀取浮點數參數"""
        value = self.section.get(key, default)
        try:
            return float(value)
        except (ValueError, TypeError):
            return default
    
    def get_bool(self, key: str, default: bool = False) -> bool:
        """讀取布林值參數"""
        value = self.section.get(key, default)
        if isinstance(value, bool):
            return value
        return str(value).lower() in ('true', '1', 'yes', 'on')
    
    def get_list(self, key: str, default: list = None) -> list:
        """讀取列表參數"""
        if default is None:
            default = []
        value = self.section.get(key, default)
        return list(value) if isinstance(value, (list, tuple)) else default
    
    def get_dict(self, key: str, default: dict = None) -> dict:
        """讀取字典參數"""
        if default is None:
            default = {}
        value = self.section.get(key, default)
        return dict(value) if isinstance(value, dict) else default
    
    def get_string(self, key: str, default: str = "") -> str:
        """讀取字串參數"""
        value = self.section.get(key, default)
        return str(value) if value is not None else default

def create_config_section(config: Dict, section_name: str) -> ConfigSection:
    """創建配置區段讀取器"""
    return ConfigSection(config, section_name)

def load_config(config_path: str) -> Dict[str, Any]:
    """載入配置檔的簡化函數"""
    return ConfigUtils.load_yaml_config(config_path)
