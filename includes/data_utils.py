# includes/data_utils.py - 資料存取工具

import json
import os
import time
import cv2
import numpy as np
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from includes.log_utils import get_logger

class DataManager:
    """資料管理器"""
    
    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
        self.logger = get_logger("DataManager")
    
    def save_json(self, filename: str, data: Dict) -> bool:
        """保存 JSON 資料"""
        try:
            file_path = self.data_dir / filename
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            self.logger.info(f"已保存 JSON: {filename}")
            return True
        except Exception as e:
            self.logger.error(f"保存 JSON 失敗: {filename}", e)
            return False
    
    def load_json(self, filename: str) -> Optional[Dict]:
        """載入 JSON 資料"""
        try:
            file_path = self.data_dir / filename
            if not file_path.exists():
                self.logger.warning(f"JSON 檔案不存在: {filename}")
                return None
            
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            self.logger.info(f"已載入 JSON: {filename}")
            return data
        except Exception as e:
            self.logger.error(f"載入 JSON 失敗: {filename}", e)
            return None
    
    def list_json_files(self, pattern: str = "*.json") -> List[str]:
        """列出 JSON 檔案"""
        try:
            files = list(self.data_dir.glob(pattern))
            return [f.name for f in files if f.is_file()]
        except Exception as e:
            self.logger.error("列出 JSON 檔案失敗", e)
            return []
    
    def delete_json(self, filename: str) -> bool:
        """刪除 JSON 檔案"""
        try:
            file_path = self.data_dir / filename
            if file_path.exists():
                file_path.unlink()
                self.logger.info(f"已刪除 JSON: {filename}")
                return True
            return False
        except Exception as e:
            self.logger.error(f"刪除 JSON 失敗: {filename}", e)
            return False
    
    def get_data_dir(self) -> str:
        """獲取資料目錄路徑"""
        return str(self.data_dir)
    
    def data_dir_exists(self) -> bool:
        """檢查資料目錄是否存在"""
        return self.data_dir.exists()
    
    def ensure_data_dir(self) -> bool:
        """確保資料目錄存在"""
        try:
            self.data_dir.mkdir(exist_ok=True)
            return True
        except Exception as e:
            self.logger.error("創建資料目錄失敗", e)
            return False
    
    def list_all_files(self) -> List[str]:
        """列出所有檔案"""
        try:
            files = list(self.data_dir.iterdir())
            return [f.name for f in files if f.is_file()]
        except Exception as e:
            self.logger.error("列出所有檔案失敗", e)
            return []

class ImageManager:
    """圖片管理器"""
    
    def __init__(self, image_dir: str = "templates"):
        self.image_dir = Path(image_dir)
        self.image_dir.mkdir(exist_ok=True)
        self.logger = get_logger("ImageManager")
    
    def save_image(self, filename: str, image: np.ndarray) -> bool:
        """保存圖片"""
        try:
            file_path = self.image_dir / filename
            success = cv2.imwrite(str(file_path), image)
            if success:
                self.logger.info(f"已保存圖片: {filename}")
            return success
        except Exception as e:
            self.logger.error(f"保存圖片失敗: {filename}", e)
            return False
    
    def load_image(self, filename: str, flags: int = cv2.IMREAD_COLOR) -> Optional[np.ndarray]:
        """載入圖片"""
        try:
            file_path = self.image_dir / filename
            if not file_path.exists():
                self.logger.warning(f"圖片檔案不存在: {filename}")
                return None
            
            image = cv2.imread(str(file_path), flags)
            if image is not None:
                self.logger.info(f"已載入圖片: {filename}")
            return image
        except Exception as e:
            self.logger.error(f"載入圖片失敗: {filename}", e)
            return None
    
    def list_image_files(self, pattern: str = "*.png") -> List[str]:
        """列出圖片檔案"""
        try:
            files = list(self.image_dir.glob(pattern))
            return [f.name for f in files if f.is_file()]
        except Exception as e:
            self.logger.error("列出圖片檔案失敗", e)
            return []
    
    def resize_image(self, image: np.ndarray, width: int, height: int) -> np.ndarray:
        """調整圖片大小"""
        return cv2.resize(image, (width, height), interpolation=cv2.INTER_AREA)
    
    def crop_image(self, image: np.ndarray, x: int, y: int, w: int, h: int) -> np.ndarray:
        """裁剪圖片"""
        return image[y:y+h, x:x+w]

class TemplateManager:
    """模板管理器"""
    
    def __init__(self, template_dir: str = "templates"):
        self.template_dir = Path(template_dir)
        self.templates: Dict[str, np.ndarray] = {}
        self.logger = get_logger("TemplateManager")
    
    def load_template(self, template_name: str, subdir: str = "") -> Optional[np.ndarray]:
        """載入模板"""
        try:
            if template_name in self.templates:
                return self.templates[template_name]
            
            if subdir:
                file_path = self.template_dir / subdir / template_name
            else:
                file_path = self.template_dir / template_name
            
            if not file_path.exists():
                self.logger.warning(f"模板檔案不存在: {template_name}")
                return None
            
            template = cv2.imread(str(file_path), cv2.IMREAD_GRAYSCALE)
            if template is not None:
                self.templates[template_name] = template
                self.logger.info(f"已載入模板: {template_name}")
            
            return template
        except Exception as e:
            self.logger.error(f"載入模板失敗: {template_name}", e)
            return None
    
    def load_templates(self, template_names: List[str], subdir: str = "") -> Dict[str, np.ndarray]:
        """批量載入模板"""
        templates = {}
        for name in template_names:
            template = self.load_template(name, subdir)
            if template is not None:
                templates[name] = template
        return templates
    
    def clear_cache(self) -> None:
        """清空模板緩存"""
        self.templates.clear()
        self.logger.info("模板緩存已清空")

class MapDataManager:
    """地圖資料管理器"""
    
    def __init__(self, data_dir: str = "data"):
        self.data_manager = DataManager(data_dir)
        self.logger = get_logger("MapDataManager")
    
    def save_map_data(self, map_name: str, waypoints: List[Dict], 
                     areas: Dict, obstacles: List[Dict] = None) -> bool:
        """保存地圖資料"""
        try:
            map_data = {
                'name': map_name,
                'waypoints': waypoints,
                'areas': areas,
                'obstacles': obstacles or [],
                'timestamp': time.time()
            }
            
            filename = f"{map_name}.json"
            return self.data_manager.save_json(filename, map_data)
        except Exception as e:
            self.logger.error(f"保存地圖資料失敗: {map_name}", e)
            return False
    
    def load_map_data(self, map_name: str) -> Optional[Dict]:
        """載入地圖資料"""
        try:
            filename = f"{map_name}.json"
            return self.data_manager.load_json(filename)
        except Exception as e:
            self.logger.error(f"載入地圖資料失敗: {map_name}", e)
            return None
    
    def list_maps(self) -> List[str]:
        """列出所有地圖"""
        files = self.data_manager.list_json_files("*.json")
        return [f.replace('.json', '') for f in files]
    
    def delete_map(self, map_name: str) -> bool:
        """刪除地圖"""
        filename = f"{map_name}.json"
        return self.data_manager.delete_json(filename)

# 全域管理器實例
data_manager = DataManager()
image_manager = ImageManager()
template_manager = TemplateManager()
map_data_manager = MapDataManager()

def get_data_manager() -> DataManager:
    """獲取全域資料管理器"""
    return data_manager

def get_image_manager() -> ImageManager:
    """獲取全域圖片管理器"""
    return image_manager

def get_template_manager() -> TemplateManager:
    """獲取全域模板管理器"""
    return template_manager

def get_map_data_manager() -> MapDataManager:
    """獲取全域地圖資料管理器"""
    return map_data_manager 