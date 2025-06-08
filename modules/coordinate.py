# modules/coordinate.py - 整合座標系統版本

import cv2
import numpy as np
import os
from modules.coordinate_system import coordinate_system, CoordinateType

class TemplateMatcherTracker:
    """簡化版角色追蹤 - AutoMaple 風格 + 座標系統整合"""
    
    def __init__(self, config):
        tcfg = config['template_matcher']
        template_dir = "templates"
        
        # 只保留基本模板
        self.corner_templates = {}
        for key in ['topleft', 'topright', 'bottomleft', 'bottomright']:
            path = os.path.join(template_dir, tcfg['corner_templates'][key])
            img = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
            if img is None:
                raise FileNotFoundError(f"找不到模板: {path}")
            self.corner_templates[key] = img
        
        # 角色模板
        player_path = os.path.join(template_dir, tcfg['player_template_name'])
        self.player_template = cv2.imread(player_path, cv2.IMREAD_GRAYSCALE)
        if self.player_template is None:
            raise FileNotFoundError(f"找不到角色模板: {player_path}")
        
        # 基本參數
        self.player_threshold = tcfg.get('player_threshold', 0.7)
        self.last_player_pos_rel = (0.5, 0.5)
        self.cropped_minimap_img = None
        
        # ✅ 整合座標系統
        self.coordinate_system = coordinate_system
        
        # ✅ 多種座標格式儲存
        self.last_player_pos_screen = None
        self.last_player_pos_world = None
        self.last_player_pos_tile = None
        
        print("🎯 角色追蹤器已整合座標系統")
    
    def track_player(self, frame):
        """✅ 修正版：考慮小地圖縮放的角色追蹤"""
        if frame is None:
            return self.last_player_pos_rel

        # 1. 找小地圖
        gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        minimap_rect = self._find_minimap_simple(gray_frame)
        
        if minimap_rect:
            self.coordinate_system.set_minimap_bounds(minimap_rect)
        else:
            return self.last_player_pos_rel

        # 2. 裁切小地圖
        x1, y1, x2, y2 = minimap_rect
        minimap_img = frame[y1:y2, x1:x2]
        self.cropped_minimap_img = minimap_img.copy()
        
        # ✅ 記錄原始小地圖尺寸
        original_minimap_size = (x2 - x1, y2 - y1)
        
        # 3. 簡單模板匹配
        gray_minimap = cv2.cvtColor(minimap_img, cv2.COLOR_BGR2GRAY)
        result = cv2.matchTemplate(gray_minimap, self.player_template, cv2.TM_CCOEFF_NORMED)
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)

        if max_val >= self.player_threshold:
            px, py = max_loc
            h, w = self.player_template.shape
            center_x = px + w // 2
            center_y = py + h // 2
            
            # ✅ 基於原始小地圖尺寸計算相對座標
            rel_x = center_x / original_minimap_size[0]
            rel_y = center_y / original_minimap_size[1]
            
            # ✅ 重要：標記這是基於原始小地圖的座標
            self.last_player_pos_rel = (round(rel_x, 3), round(rel_y, 3))
            self._minimap_scale_info = {
                'original_size': original_minimap_size,
                'template_match_pos': (center_x, center_y),
                'coordinate_source': 'original_minimap'
            }
            
            if self._position_changed_significantly():
                print(f"🎯 角色位置: {self.last_player_pos_rel}")

        return self.last_player_pos_rel
    
    def _position_changed_significantly(self):
        """簡化的變化檢測"""
        if not hasattr(self, '_last_output_pos'):
            self._last_output_pos = self.last_player_pos_rel
            return True
        
        old_pos = self._last_output_pos
        new_pos = self.last_player_pos_rel
        
        # 簡化計算
        if abs(old_pos[0] - new_pos[0]) > 0.02 or abs(old_pos[1] - new_pos[1]) > 0.02:
            self._last_output_pos = new_pos
            return True
        
        return False

    def _find_minimap_simple(self, gray_frame):
        """簡化的小地圖定位"""
        locs = {}
        corners_found = 0
        
        for key, tmpl in self.corner_templates.items():
            res = cv2.matchTemplate(gray_frame, tmpl, cv2.TM_CCOEFF_NORMED)
            min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)
            
            if max_val >= 0.6:
                corners_found += 1
                if 'left' in key:
                    x = max_loc[0]
                else:
                    x = max_loc[0] + tmpl.shape[1]
                if 'top' in key:
                    y = max_loc[1]
                else:
                    y = max_loc[1] + tmpl.shape[0]
                locs[key] = (x, y)
        
        if corners_found >= 4:
            x1 = locs['topleft'][0]
            y1 = locs['topleft'][1]
            x2 = locs['bottomright'][0]
            y2 = locs['bottomright'][1]
            
            if x1 < x2 and y1 < y2:
                return (x1, y1, x2, y2)
        
        return None
    
    def get_position_in_coordinate_type(self, coord_type: CoordinateType):
        """獲取指定座標系統的位置"""
        if coord_type == CoordinateType.MINIMAP:
            return self.last_player_pos_rel
        elif coord_type == CoordinateType.SCREEN:
            return self.last_player_pos_screen
        elif coord_type == CoordinateType.WORLD:
            return self.last_player_pos_world
        elif coord_type == CoordinateType.TILE:
            return self.last_player_pos_tile
        else:
            return None
    
    def get_coordinate_debug_info(self):
        """獲取座標除錯資訊"""
        return {
            'minimap_pos': self.last_player_pos_rel,
            'screen_pos': self.last_player_pos_screen,
            'world_pos': self.last_player_pos_world,
            'tile_pos': self.last_player_pos_tile,
            'coordinate_system_info': self.coordinate_system.get_debug_info()
        }
    
    @property
    def minimap_img(self):
        return self.cropped_minimap_img
