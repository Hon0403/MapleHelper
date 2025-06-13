# includes/config_utils.py

import yaml
import json
import os
from typing import Dict, Any

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
            print(f"❌ 載入配置失敗 {config_path}: {e}")
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
            print(f"❌ 保存配置失敗 {config_path}: {e}")
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
            print(f"❌ 載入 JSON 配置失敗 {config_path}: {e}")
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
            print(f"❌ 保存 JSON 配置失敗 {config_path}: {e}")
            return False
    
    @staticmethod
    def merge_configs(base_config: Dict[str, Any], override_config: Dict[str, Any]) -> Dict[str, Any]:
        """合併配置（override_config 覆蓋 base_config）"""
        merged = base_config.copy()
        merged.update(override_config)
        return merged
