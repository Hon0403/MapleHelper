# modules/coordinate.py - 整合座標系統版本

import cv2
import numpy as np
import os
from PIL import Image

def simple_coordinate_conversion(canvas_x, canvas_y, canvas_size, minimap_size):
    """AutoMaple風格：極簡座標轉換"""
    # 計算居中偏移
    offset_x = (canvas_size[0] - minimap_size[0]) // 2
    offset_y = (canvas_size[1] - minimap_size[1]) // 2
    
    # 轉換為圖片內座標
    img_x = canvas_x - offset_x
    img_y = canvas_y - offset_y
    
    # 直接除法
    rel_x = img_x / minimap_size[0]
    rel_y = img_y / minimap_size[1]
    
    return (max(0.0, min(1.0, rel_x)), max(0.0, min(1.0, rel_y)))

class TemplateMatcherTracker:
    """純AutoMaple風格角色追蹤"""
    
    def __init__(self, config, capturer=None):
        tcfg = config['template_matcher']
        template_dir = "templates"
        
        # 保存 capturer 引用
        self.capturer = capturer
        
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
        
        print("🎯 純AutoMaple風格角色追蹤器已初始化")
    
    def track_player(self, frame):
        """✅ 修正版：考慮小地圖縮放的角色追蹤"""
        if frame is None:
            return self.last_player_pos_rel

        # 1. 找小地圖
        gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        minimap_rect = self._find_minimap_simple(gray_frame)
        
        if minimap_rect:
            # self.coordinate_system.set_minimap_bounds(minimap_rect)  # 已移除，不再需要
            pass
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

    def find_minimap(self):
        """修正版：完全移除超解析度處理"""
        try:
            frame = self.capturer.grab_frame()
            if frame is None:
                print("❌ 無法獲取畫面")
                return False
            # 四角模板匹配
            gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            minimap_rect = self._find_minimap_simple(gray_frame)
            if minimap_rect is None:
                print("❌ 無法找到小地圖")
                return False
            x1, y1, x2, y2 = minimap_rect
            minimap_img = frame[y1:y2, x1:x2].copy()
            print(f"✅ 四角模板匹配小地圖: {minimap_img.shape}")
            # ✅ 完全移除waifu2x處理，直接使用原圖
            self.cropped_minimap_img = minimap_img
            # ✅ 記錄真實的原始尺寸
            original_minimap_size = (x2 - x1, y2 - y1)
            self._minimap_scale_info = {
                'original_size': original_minimap_size,
                'coordinate_source': 'original_minimap_no_processing'
            }
            return True
        except Exception as e:
            print(f"❌ 小地圖處理失敗: {e}")
            return False

    @property
    def minimap_img(self):
        return self.cropped_minimap_img

    def get_player_main_screen_pos(self, frame=None):
        """
        根據小地圖相對座標與 minimap_rect 推算主畫面像素座標
        回傳 (main_x, main_y) 或 None
        """
        if frame is None and self.capturer:
            frame = self.capturer.grab_frame()
        if frame is None:
            return None
        # 取得小地圖範圍
        gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        minimap_rect = self._find_minimap_simple(gray_frame)
        if minimap_rect is None:
            return None
        x1, y1, x2, y2 = minimap_rect
        # 取得角色在小地圖的相對座標
        rel_x, rel_y = self.track_player(frame)
        # 推算主畫面像素座標
        main_x = int(x1 + rel_x * (x2 - x1))
        main_y = int(y1 + rel_y * (y2 - y1))
        return (main_x, main_y)
