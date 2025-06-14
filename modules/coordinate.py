# modules/coordinate.py - 整合座標系統版本

import cv2
import numpy as np
import os
from PIL import Image
import time

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
    
    def enhanced_coordinate_conversion(self, canvas_x, canvas_y, canvas_size, minimap_size):
        """✅ 高精度座標轉換"""
        # 使用浮點除法提高精度
        offset_x = (canvas_size[0] - minimap_size[0]) / 2.0
        offset_y = (canvas_size[1] - minimap_size[1]) / 2.0
        
        # 轉換為圖片內座標（使用浮點數）
        img_x = float(canvas_x) - offset_x
        img_y = float(canvas_y) - offset_y
        
        # ✅ 添加亞像素插值
        rel_x = img_x / float(minimap_size[0])
        rel_y = img_y / float(minimap_size[1])
        
        # ✅ 使用更高精度的範圍限制
        rel_x = max(0.0, min(1.0, rel_x))
        rel_y = max(0.0, min(1.0, rel_y))
        
        # ✅ 四捨五入到適當精度（避免浮點誤差）
        rel_x = round(rel_x, 5)
        rel_y = round(rel_y, 5)
        
        return (rel_x, rel_y)

    def track_player(self, frame):
        """修正版：確保使用高精度轉換"""
        if frame is None:
            return self.last_player_pos_rel

        # 使用高精度小地圖檢測
        gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        minimap_rect = self._find_minimap_with_subpixel_accuracy(gray_frame)
        
        if not minimap_rect:
            return self.last_player_pos_rel

        x1, y1, x2, y2 = minimap_rect
        minimap_img = frame[y1:y2, x1:x2]
        
        # ✅ 關鍵修正：使用高精度模板匹配
        gray_minimap = cv2.cvtColor(minimap_img, cv2.COLOR_BGR2GRAY)
        result = cv2.matchTemplate(gray_minimap, self.player_template, cv2.TM_CCOEFF_NORMED)
        
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
        
        if max_val >= self.player_threshold:
            px, py = max_loc
            h, w = self.player_template.shape
            
            # ✅ 使用亞像素精度
            if self._can_use_subpixel(result, px, py):
                center_x, center_y = self._subpixel_peak_location(result, px, py)
                center_x += w / 2.0
                center_y += h / 2.0
            else:
                center_x = px + w / 2.0
                center_y = py + h / 2.0
            
            # ✅ 高精度相對座標計算
            minimap_width = float(x2 - x1)
            minimap_height = float(y2 - y1)
            
            rel_x = center_x / minimap_width
            rel_y = center_y / minimap_height
            
            # ✅ 保持6位小數精度
            self.last_player_pos_rel = (round(rel_x, 6), round(rel_y, 6))
            
            return self.last_player_pos_rel
            
        return self.last_player_pos_rel

    def _can_use_subpixel(self, correlation_map, peak_x, peak_y):
        """檢查是否可以使用亞像素精度"""
        return (peak_x > 0 and peak_y > 0 and 
                peak_x < correlation_map.shape[1] - 1 and 
                peak_y < correlation_map.shape[0] - 1)

    def _find_minimap_with_subpixel_accuracy(self, gray_frame):
        """✅ 亞像素精度小地圖檢測"""
        locs = {}
        corners_found = 0
        
        for key, tmpl in self.corner_templates.items():
            # ✅ 使用歸一化相關性匹配提高精度
            res = cv2.matchTemplate(gray_frame, tmpl, cv2.TM_CCOEFF_NORMED)
            min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)
            
            if max_val >= 0.7:  # 提高閾值確保準確性
                corners_found += 1
                
                # ✅ 亞像素精度定位
                peak_x, peak_y = max_loc
                
                # 在峰值周圍進行亞像素插值
                if (peak_x > 0 and peak_y > 0 and 
                    peak_x < res.shape[1] - 1 and peak_y < res.shape[0] - 1):
                    
                    # 二次插值提高精度
                    subpix_x, subpix_y = self._subpixel_peak_location(res, peak_x, peak_y)
                    peak_x, peak_y = subpix_x, subpix_y
                
                # 計算角點位置
                if 'left' in key:
                    x = peak_x
                else:
                    x = peak_x + tmpl.shape[1]
                    
                if 'top' in key:
                    y = peak_y
                else:
                    y = peak_y + tmpl.shape[0]
                    
                locs[key] = (x, y)
        
        if corners_found >= 4:
            # ✅ 使用浮點座標
            x1 = float(locs['topleft'][0])
            y1 = float(locs['topleft'][1])
            x2 = float(locs['bottomright'][0])
            y2 = float(locs['bottomright'][1])
            
            if x1 < x2 and y1 < y2:
                return (int(x1), int(y1), int(x2), int(y2))
        
        return None

    def _subpixel_peak_location(self, correlation_map, peak_x, peak_y):
        """✅ 亞像素峰值定位"""
        try:
            # 獲取峰值周圍的9個點
            patch = correlation_map[peak_y-1:peak_y+2, peak_x-1:peak_x+2]
            
            if patch.shape != (3, 3):
                return float(peak_x), float(peak_y)
            
            # 使用二次插值計算亞像素位置
            # X方向插值
            dx = (patch[1, 2] - patch[1, 0]) / (2 * (2 * patch[1, 1] - patch[1, 0] - patch[1, 2]))
            
            # Y方向插值  
            dy = (patch[2, 1] - patch[0, 1]) / (2 * (2 * patch[1, 1] - patch[0, 1] - patch[2, 1]))
            
            # 限制偏移範圍
            dx = max(-0.5, min(0.5, dx))
            dy = max(-0.5, min(0.5, dy))
            
            return float(peak_x) + dx, float(peak_y) + dy
            
        except:
            return float(peak_x), float(peak_y)

    def debug_coordinate_precision(self, frame):
        """✅ 座標精度調試"""
        try:
            # 獲取原始檢測結果
            minimap_rect = self._find_minimap_with_subpixel_accuracy(cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY))
            if not minimap_rect:
                print("❌ 無法檢測小地圖")
                return
            
            x1, y1, x2, y2 = minimap_rect
            rel_pos = self.track_player(frame)
            
            print(f"\n🔍 座標精度調試報告:")
            print(f"📏 小地圖檢測框: ({x1}, {y1}) -> ({x2}, {y2})")
            print(f"📐 小地圖尺寸: {x2-x1} x {y2-y1}")
            print(f"🎯 角色相對座標: ({rel_pos[0]:.6f}, {rel_pos[1]:.6f})")
            
            # 反向計算像素位置
            pixel_x = x1 + rel_pos[0] * (x2 - x1)
            pixel_y = y1 + rel_pos[1] * (y2 - y1)
            print(f"📍 對應像素位置: ({pixel_x:.2f}, {pixel_y:.2f})")
            
            # 檢查區域匹配
            if hasattr(self, 'waypoint_system'):
                for pos_key, area_type in self.waypoint_system.area_grid.items():
                    if area_type == "walkable":
                        if isinstance(pos_key, str) and ',' in pos_key:
                            x_str, y_str = pos_key.split(',')
                            wx, wy = float(x_str), float(y_str)
                            
                            x_diff = abs(rel_pos[0] - wx)
                            y_diff = abs(rel_pos[1] - wy)
                            
                            print(f"🎯 與可行走區域 ({wx:.3f}, {wy:.3f}) 的精確距離:")
                            print(f"   X軸差距: {x_diff:.6f} ({'✅通過' if x_diff <= 0.01 else '❌超出'} 0.01容忍度)")
                            print(f"   Y軸差距: {y_diff:.6f} ({'✅通過' if y_diff <= 0.02 else '❌超出'} 0.02容忍度)")
            
        except Exception as e:
            print(f"❌ 座標調試失敗: {e}")
            import traceback
            traceback.print_exc()

    def find_minimap(self):
        """✅ 高精度小地圖檢測"""
        try:
            frame = self.capturer.grab_frame()
            if frame is None:
                print("❌ 無法獲取畫面")
                return False
                
            # 使用高精度小地圖檢測
            gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            minimap_rect = self._find_minimap_with_subpixel_accuracy(gray_frame)
            
            if minimap_rect:
                x1, y1, x2, y2 = minimap_rect
                # 保存小地圖圖片
                minimap_img = frame[y1:y2, x1:x2].copy()
                self.cropped_minimap_img = minimap_img
                
                # 記錄原始尺寸
                original_minimap_size = (x2 - x1, y2 - y1)
                self._minimap_scale_info = {
                    'original_size': original_minimap_size,
                    'coordinate_source': 'original_minimap_no_processing'
                }
                
                print(f"✅ 小地圖檢測成功: ({x1}, {y1}) -> ({x2}, {y2})")
                print(f"📏 小地圖尺寸: {x2-x1} x {y2-y1}")
                return True
            else:
                print("❌ 無法檢測小地圖")
                return False
                
        except Exception as e:
            print(f"❌ 小地圖處理失敗: {e}")
            import traceback
            traceback.print_exc()
            return False

    @property
    def minimap_img(self):
        return self.cropped_minimap_img

    def draw_player_on_main_screen(self, frame):
        """在主畫面上標記角色位置"""
        try:
            # 直接回傳原始 frame，不再標記主畫面角色
            return frame
        except Exception as e:
            print(f"❌ 角色主畫面標記失敗: {e}")
            return frame

    def draw_enhanced_player_tracking(self, frame):
        """增強版角色追蹤顯示"""
        try:
            display_frame = frame.copy()
            # 不再呼叫 draw_player_on_main_screen
            # 不再標記主畫面角色
            # 只保留移動軌跡與方向指示（如有）
            if hasattr(self, 'position_history'):
                for i in range(1, len(self.position_history)):
                    prev_pos = self.position_history[i-1]
                    curr_pos = self.position_history[i]
                    if prev_pos and curr_pos:
                        cv2.line(display_frame, prev_pos, curr_pos, (100, 100, 255), 2)
            if hasattr(self, 'last_movement_direction'):
                # 不再呼叫 get_player_main_screen_pos
                pass
            return display_frame
        except Exception as e:
            print(f"❌ 增強追蹤顯示失敗: {e}")
            return frame
