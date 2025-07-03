# modules/coordinate.py - 整合座標系統版本

import cv2
import numpy as np
import os
from PIL import Image
import time
from collections import deque
from includes.log_utils import get_logger

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
        self.logger = get_logger(__name__)
        tcfg = config['template_matcher']
        template_dir = "templates"
        self.capturer = capturer
        self.corner_templates = {}
        for key in ['topleft', 'topright', 'bottomleft', 'bottomright']:
            path = os.path.join(template_dir, tcfg['corner_templates'][key])
            img = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
            if img is None:
                raise FileNotFoundError(f"找不到模板: {path}")
            self.corner_templates[key] = img
        player_path = os.path.join(template_dir, tcfg['player_template_name'])
        self.player_template = cv2.imread(player_path, cv2.IMREAD_GRAYSCALE)
        if self.player_template is None:
            raise FileNotFoundError(f"找不到角色模板: {player_path}")
        self.player_threshold = tcfg.get('player_threshold', 0.7)
        self.minimap_corner_threshold = tcfg.get('minimap_corner_threshold', 0.7)
        self.use_gray_only_for_corners = True
        self.use_edge_templates = False
        self.use_enhanced_preprocessing = False
        self.use_hybrid_templates = False
        self.last_player_pos_rel = (0.5, 0.5)
        self.cropped_minimap_img = None
        self.threshold_stats = {
            'successful_thresholds': {},
            'total_attempts': 0,
            'successful_detections': 0
        }
    
    def enhanced_coordinate_conversion(self, canvas_x, canvas_y, canvas_size, minimap_size):
        """✅ 統一座標轉換：使用統一的座標轉換函式"""
        return unified_coordinate_conversion(
            canvas_x, canvas_y, 
            canvas_size, minimap_size, 
            precision=5
        )

    def track_player(self, frame):
        """追蹤玩家位置"""
        try:
            if frame is None:
                return None
            
            # 檢測小地圖區域
            minimap_rect = self._find_minimap_with_subpixel_accuracy(frame)
            if minimap_rect is None:
                return None
            
            # 提取小地圖圖像
            x1, y1, x2, y2 = minimap_rect
            minimap_img = frame[y1:y2, x1:x2]
            
            # 檢測玩家標記
            player_pos = self._detect_player_marker(minimap_img)
            if player_pos is None:
                return None
            
            # 轉換為相對座標
            rel_pos = self._minimap_to_relative(player_pos, minimap_img.shape)
            
            # 平滑處理
            if hasattr(self, 'last_position') and self.last_position:
                rel_pos = self._smooth_position(rel_pos)
            
            self.last_position = rel_pos
            return rel_pos
            
        except Exception as e:
            self.logger.error(f"玩家追蹤失敗: {e}")
            return None

    def _can_use_subpixel(self, correlation_map, peak_x, peak_y):
        """檢查是否可以使用亞像素精度"""
        return (peak_x > 0 and peak_y > 0 and 
                peak_x < correlation_map.shape[1] - 1 and 
                peak_y < correlation_map.shape[0] - 1)

    def _find_minimap_with_subpixel_accuracy(self, frame):
        """✅ 簡化版：固定高閾值小地圖檢測"""
        # 只在需要時轉換灰階
        if len(frame.shape) == 3:
            gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        else:
            gray_frame = frame
            
        # ✅ 圖像預處理提升準確率
        gray_frame = self._preprocess_gray_image(gray_frame)
        
        # ✅ 使用固定高閾值 0.8
        result = self._try_detect_minimap(gray_frame, self.minimap_corner_threshold)
        if result:
            return result
        
        return None
    
    def _try_detect_minimap(self, gray_frame, threshold):
        locs = {}
        corners_found = 0
        use_gray_only = getattr(self, 'use_gray_only_for_corners', True)
        for key, tmpl in self.corner_templates.items():
            best_match_val = 0
            best_match_loc = None
            best_template_type = "none"
            if use_gray_only:
                res = cv2.matchTemplate(gray_frame, tmpl, cv2.TM_CCOEFF_NORMED)
                min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)
                best_match_val = max_val
                best_match_loc = max_loc
                best_template_type = "gray"
            else:
                if self.use_edge_templates:
                    processed_tmpl = self._preprocess_gray_image(tmpl)
                    res = cv2.matchTemplate(gray_frame, processed_tmpl, cv2.TM_CCOEFF_NORMED)
                    min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)
                    if max_val > best_match_val:
                        best_match_val = max_val
                        best_match_loc = max_loc
                        best_template_type = "edge"
                if self.use_hybrid_templates and hasattr(self, 'original_templates'):
                    original_tmpl = self.original_templates[key]
                    processed_original = self._preprocess_gray_image(original_tmpl)
                    res_original = cv2.matchTemplate(gray_frame, processed_original, cv2.TM_CCOEFF_NORMED)
                    min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res_original)
                    if max_val > best_match_val:
                        best_match_val = max_val
                        best_match_loc = max_loc
                        best_template_type = "original"
                if self.use_hybrid_templates:
                    res_gray = cv2.matchTemplate(gray_frame, tmpl, cv2.TM_CCOEFF_NORMED)
                    min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res_gray)
                    if max_val > best_match_val:
                        best_match_val = max_val
                        best_match_loc = max_loc
                        best_template_type = "gray"
            if best_match_val >= threshold:
                corners_found += 1
                peak_x, peak_y = best_match_loc
                if (peak_x > 0 and peak_y > 0 and 
                    peak_x < gray_frame.shape[1] - 1 and peak_y < gray_frame.shape[0] - 1):
                    subpix_x, subpix_y = self._subpixel_peak_location(
                        cv2.matchTemplate(gray_frame, tmpl, cv2.TM_CCOEFF_NORMED), 
                        peak_x, peak_y
                    )
                    peak_x, peak_y = subpix_x, subpix_y
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
            x1 = float(locs['topleft'][0])
            y1 = float(locs['topleft'][1])
            x2 = float(locs['bottomright'][0])
            y2 = float(locs['bottomright'][1])
            if x1 < x2 and y1 < y2:
                return (int(x1), int(y1), int(x2), int(y2))
        return None

    def _preprocess_gray_image(self, gray_img):
        """✅ 增強版：多種預處理方法提升模板獨特性"""
        try:
            if self.use_enhanced_preprocessing:
                # ✅ 方案1：邊緣檢測預處理 (適合邊緣模板)
                if self.use_edge_templates:
                    # 1. 輕微高斯模糊
                    blurred = cv2.GaussianBlur(gray_img, (3, 3), 0.5)
                    
                    # 2. 邊緣檢測 - 使用更溫和的參數
                    edges = cv2.Canny(blurred, 30, 80)  # 降低閾值
                    
                    # 3. 形態學操作增強邊緣
                    kernel = np.ones((1, 1), np.uint8)  # 更小的核心
                    enhanced_edges = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel)
                    
                    # 4. 輕微膨脹連接斷開的邊緣
                    kernel_dilate = np.ones((1, 1), np.uint8)
                    final_edges = cv2.dilate(enhanced_edges, kernel_dilate, iterations=1)
                    
                    return final_edges
                
                # ✅ 方案2：對比度增強預處理 (適合原始模板)
                else:
                    # 1. 強對比度增強
                    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))  # 降低clipLimit
                    enhanced = clahe.apply(gray_img)
                    
                    # 2. 銳化處理 - 使用更溫和的核
                    kernel = np.array([[-0.5,-0.5,-0.5],
                                     [-0.5, 5.0,-0.5],
                                     [-0.5,-0.5,-0.5]])
                    sharpened = cv2.filter2D(enhanced, -1, kernel)
                    
                    # 3. 正規化
                    normalized = cv2.normalize(sharpened, None, 0, 255, cv2.NORM_MINMAX)
                    
                    return normalized
            
            else:
                # ✅ 方案3：原始溫和預處理
                # 1. 輕微高斯模糊減少雜訊
                blurred = cv2.GaussianBlur(gray_img, (3, 3), 0.5)
                
                # 2. 輕微直方圖均衡化
                clahe = cv2.createCLAHE(clipLimit=1.5, tileGridSize=(8,8))  # 更溫和的參數
                equalized = clahe.apply(blurred)
                
                # 3. 溫和銳化
                kernel = np.array([[-0.3,-0.3,-0.3],
                                 [-0.3, 3.4,-0.3],
                                 [-0.3,-0.3,-0.3]])
                sharpened = cv2.filter2D(equalized, -1, kernel)
                
                # 4. 正規化
                normalized = cv2.normalize(sharpened, None, 0, 255, cv2.NORM_MINMAX)
                
                return normalized
            
        except Exception as e:
            self.logger.warning(f"圖像預處理失敗，使用原始圖像: {e}")
            return gray_img

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
        """座標精度調試"""
        try:
            # 獲取原始檢測結果
            minimap_rect = self._find_minimap_with_subpixel_accuracy(
                cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            )
            
            if not minimap_rect:
                return
                
            x1, y1, x2, y2 = minimap_rect
            rel_pos = self.track_player(frame)
            
            # 反向計算像素位置
            pixel_x = x1 + rel_pos[0] * (x2 - x1)
            pixel_y = y1 + rel_pos[1] * (y2 - y1)
            
        except Exception as e:
            self.logger.error(f"座標調試失敗: {e}")
            import traceback
            traceback.print_exc()

    def find_minimap(self):
        """✅ 高精度小地圖檢測"""
        try:
            frame = self.capturer.grab_frame()
            if frame is None:
                return False
            
            # ✅ 保存當前畫面以便調試（可選）
            # cv2.imwrite('debug_current_frame.png', frame)
                
            # 使用高精度小地圖檢測
            minimap_rect = self._find_minimap_with_subpixel_accuracy(frame)
            
            if minimap_rect:
                x1, y1, x2, y2 = minimap_rect
                # 保存小地圖圖片
                minimap_img = frame[y1:y2, x1:x2].copy()
                self.cropped_minimap_img = minimap_img
                
                # 保存檢測到的小地圖區域（可選）
                # cv2.imwrite('debug_detected_minimap.png', minimap_img)
                
                # 記錄原始尺寸
                original_minimap_size = (x2 - x1, y2 - y1)
                self._minimap_scale_info = {
                    'original_size': original_minimap_size,
                    'coordinate_source': 'original_minimap_no_processing'
                }
                
                return True
            else:
                return False
                
        except Exception as e:
            self.logger.error(f"小地圖處理失敗: {e}")
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
            return frame

    def draw_enhanced_player_tracking(self, frame):
        """✅ 增強版角色追蹤視覺化"""
        try:
            rel_pos = self.track_player(frame)
            if rel_pos:
                # 在小地圖上繪製角色位置
                minimap_rect = self._find_minimap_with_subpixel_accuracy(
                    cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                )
                if minimap_rect:
                    x1, y1, x2, y2 = minimap_rect
                    minimap_width = x2 - x1
                    minimap_height = y2 - y1
                    
                    # 計算角色在小地圖中的像素位置
                    player_x = int(x1 + rel_pos[0] * minimap_width)
                    player_y = int(y1 + rel_pos[1] * minimap_height)
                    
                    # 繪製角色標記
                    cv2.circle(frame, (player_x, player_y), 5, (0, 255, 0), -1)
                    cv2.circle(frame, (player_x, player_y), 8, (0, 255, 0), 2)
                    
                    # 添加座標文字
                    text = f"({rel_pos[0]:.3f}, {rel_pos[1]:.3f})"
                    cv2.putText(frame, text, (player_x + 10, player_y - 10),
                              cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
                    
                    # 繪製小地圖邊框
                    cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
            
            return frame
            
        except Exception as e:
            return frame
    
    def get_threshold_statistics(self):
        """✅ 獲取閾值統計資訊"""
        stats = self.threshold_stats.copy()
        
        # 計算成功率
        if stats['total_attempts'] > 0:
            stats['success_rate'] = stats['successful_detections'] / stats['total_attempts'] * 100
        else:
            stats['success_rate'] = 0.0
        
        # 找出最常用的成功閾值
        if stats['successful_thresholds']:
            most_used_threshold = max(stats['successful_thresholds'].items(), 
                                    key=lambda x: x[1])
            stats['most_used_threshold'] = {
                'threshold': most_used_threshold[0],
                'count': most_used_threshold[1]
            }
        else:
            stats['most_used_threshold'] = None
        
        return stats
    
    def print_threshold_statistics(self):
        """✅ 打印閾值統計資訊"""
        stats = self.get_threshold_statistics()
        
        self.logger.info("\n📊 閾值統計報告:")
        self.logger.info(f"   總檢測次數: {stats['total_attempts']}")
        self.logger.info(f"   成功檢測次數: {stats['successful_detections']}")
        self.logger.info(f"   整體成功率: {stats['success_rate']:.1f}%")
        
        if stats['successful_thresholds']:
            self.logger.info(f"\n🔍 成功閾值統計:")
            for threshold, count in stats['successful_thresholds'].items():
                percentage = count / stats['successful_detections'] * 100
                self.logger.info(f"   閾值 {threshold}: {count} 次 ({percentage:.1f}%)")
        
        if stats['most_used_threshold']:
            most_used = stats['most_used_threshold']
            self.logger.info(f"\n🏆 最常用成功閾值: {most_used['threshold']} ({most_used['count']} 次)")
        
        return stats

    # 新增：允許外部切換小地圖角點檢測模式
    def set_gray_only_for_corners(self, value: bool):
        self.use_gray_only_for_corners = value

    def _detect_player_marker(self, minimap_img):
        """檢測玩家標記"""
        try:
            if minimap_img is None:
                return None
            
            # 轉換為灰階
            if len(minimap_img.shape) == 3:
                gray_minimap = cv2.cvtColor(minimap_img, cv2.COLOR_BGR2GRAY)
            else:
                gray_minimap = minimap_img
            
            # 模板匹配
            result = cv2.matchTemplate(gray_minimap, self.player_template, cv2.TM_CCOEFF_NORMED)
            min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
            
            if max_val >= self.player_threshold:
                h, w = self.player_template.shape
                center_x = max_loc[0] + w // 2
                center_y = max_loc[1] + h // 2
                return (center_x, center_y)
            
            return None
            
        except Exception as e:
            self.logger.error(f"玩家標記檢測失敗: {e}")
            return None

    def _minimap_to_relative(self, player_pos, minimap_shape):
        """將小地圖座標轉換為相對座標"""
        try:
            if player_pos is None:
                return None
            
            x, y = player_pos
            h, w = minimap_shape[:2]
            
            # 轉換為相對座標 (0-1)
            rel_x = x / w
            rel_y = y / h
            
            # 確保在有效範圍內
            rel_x = max(0.0, min(1.0, rel_x))
            rel_y = max(0.0, min(1.0, rel_y))
            
            return (rel_x, rel_y)
            
        except Exception as e:
            self.logger.error(f"座標轉換失敗: {e}")
            return None

    def _smooth_position(self, new_pos, smooth_factor=0.8):
        """平滑位置更新"""
        try:
            if not hasattr(self, 'last_player_pos_rel'):
                self.last_player_pos_rel = new_pos
                return new_pos
            
            # 平滑處理
            smoothed_x = self.last_player_pos_rel[0] * smooth_factor + new_pos[0] * (1 - smooth_factor)
            smoothed_y = self.last_player_pos_rel[1] * smooth_factor + new_pos[1] * (1 - smooth_factor)
            
            self.last_player_pos_rel = (smoothed_x, smoothed_y)
            return (smoothed_x, smoothed_y)
            
        except Exception as e:
            self.logger.error(f"位置平滑處理失敗: {e}")
            return new_pos


# =============== 統一座標轉換函式 ===============

def unified_coordinate_conversion(
        canvas_x: float, canvas_y: float,
        canvas_size: tuple,  # (canvas_w, canvas_h)
        minimap_size: tuple, # (mini_w, mini_h)
        precision: int = 5) -> tuple:
    """
    高精度（浮點）+ 四捨五入座標轉換
    - 先扣掉居中偏移
    - 以浮點運算計算相對位置
    - 統一用 round(…, precision) 控制精度
    
    Args:
        canvas_x: 畫布 X 座標
        canvas_y: 畫布 Y 座標
        canvas_size: 畫布尺寸 (width, height)
        minimap_size: 小地圖尺寸 (width, height)
        precision: 精度位數，預設 5 位小數
        
    Returns:
        tuple: (rel_x, rel_y) 相對座標 (0.0-1.0)
    """
    # 計算居中偏移
    offset_x = (canvas_size[0] - minimap_size[0]) / 2.0
    offset_y = (canvas_size[1] - minimap_size[1]) / 2.0

    # 轉換為圖片內座標（使用浮點數）
    img_x = float(canvas_x) - offset_x
    img_y = float(canvas_y) - offset_y

    # 計算相對位置
    rel_x = img_x / float(minimap_size[0])
    rel_y = img_y / float(minimap_size[1])

    # 夾在 0~1 並四捨五入到指定精度
    rel_x = round(max(0.0, min(1.0, rel_x)), precision)
    rel_y = round(max(0.0, min(1.0, rel_y)), precision)
    
    return (rel_x, rel_y)


def unified_relative_to_canvas(
        rel_x: float, rel_y: float,
        canvas_size: tuple,  # (canvas_w, canvas_h)
        minimap_size: tuple, # (mini_w, mini_h)
        precision: int = 1) -> tuple:
    """
    相對座標轉畫布座標（反向轉換）
    
    Args:
        rel_x: 相對 X 座標 (0.0-1.0)
        rel_y: 相對 Y 座標 (0.0-1.0)
        canvas_size: 畫布尺寸 (width, height)
        minimap_size: 小地圖尺寸 (width, height)
        precision: 精度位數，預設 1 位小數（像素級）
        
    Returns:
        tuple: (canvas_x, canvas_y) 畫布座標
    """
    # 計算居中偏移
    offset_x = (canvas_size[0] - minimap_size[0]) / 2.0
    offset_y = (canvas_size[1] - minimap_size[1]) / 2.0
    
    # 從相對座標轉換為小地圖內座標
    img_x = rel_x * float(minimap_size[0])
    img_y = rel_y * float(minimap_size[1])
    
    # 加上偏移得到畫布座標
    canvas_x = img_x + offset_x
    canvas_y = img_y + offset_y
    
    # 四捨五入到像素級精度
    canvas_x = round(canvas_x, precision)
    canvas_y = round(canvas_y, precision)
    
    return (canvas_x, canvas_y)
