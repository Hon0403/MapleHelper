#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
角色血條檢測器 - 專門檢測角色頭頂的血條
使用結構化單模板方案（只用Health100%.png的邊框結構）
"""

import cv2
import numpy as np
import os
from includes.log_utils import get_logger

class CharacterHealthDetector:
    """
    角色血條檢測器（結構化單模板版）
    專門檢測角色頭頂的血條，使用單一結構化模板匹配
    """
    
    def __init__(self, template_dir="templates/MainScreen", config=None):
        """初始化角色血條檢測器"""
        self.template_dir = template_dir
        self.config = config if config else {}
        self.logger = get_logger("CharacterHealthDetector")
        
        # 從設定檔讀取參數
        simple_config = self.config.get('simple_character_health', {})
        self.template_thresholds = simple_config.get('template_thresholds', {
            'structure': 0.5  # 結構化模板閾值（降低以提高檢測率）
        })
        self.fill_analysis_threshold = simple_config.get('fill_analysis_threshold', 0.1)  # 填充分析閾值（降低以提高檢測率）
        self.max_detections = simple_config.get('max_detections', 1)
        
        # HP顏色範圍（適應透明效果）
        hp_color_config = simple_config.get('hp_color_range', {})
        self.hp_color_lower = np.array(hp_color_config.get('lower', [0, 30, 30]))  # 紅色範圍下限（適應透明效果）
        self.hp_color_upper = np.array(hp_color_config.get('upper', [20, 255, 255]))  # 紅色範圍上限
        
        # 載入結構化單模板
        self.structure_template = None
        self._load_structure_template()
        
        self.logger.info(f"📊 使用單一結構化模板：Health100%.png")
    
    def _load_structure_template(self):
        """載入結構化單模板（只用Health100%.png）"""
        try:
            # 只使用滿血模板創建通用結構
            template_path = os.path.join(self.template_dir, 'Health100%.png')
            
            if os.path.exists(template_path):
                # 載入原始滿血模板
                original_template = cv2.imread(template_path, cv2.IMREAD_COLOR)
                if original_template is not None:
                    # 創建結構化模板（只保留邊框和基本結構）
                    structure_template = self._create_structure_template(original_template)
                    
                    # 只保存結構化模板
                    self.structure_template = structure_template
                    
                    h, w = structure_template.shape[:2]
                    self.logger.info(f"✅ 創建結構化模板: Health100%.png -> 結構模板 ({w}x{h})")
                    self.logger.info(f"✅ 結構化模板已優化：只保留邊框和基本結構")
                else:
                    self.logger.error("❌ 無法載入Health100%.png模板")
            else:
                self.logger.error(f"❌ 模板檔案不存在: {template_path}")
            
            if not self.structure_template:
                self.logger.error("❌ 沒有成功創建結構化模板！")
            else:
                self.logger.info(f"✅ 結構化單模板已準備就緒")
        except Exception as e:
            self.logger.error(f"創建結構化模板失敗: {e}")
    
    def _create_structure_template(self, original_template):
        """從滿血模板創建結構化模板（只保留邊框和基本結構）"""
        try:
            # 轉換為HSV色彩空間
            hsv = cv2.cvtColor(original_template, cv2.COLOR_BGR2HSV)
            
            # 創建更詳細的遮罩：保留更多邊緣細節
            detailed_mask = self._create_more_detailed_mask(original_template, hsv)
            
            # 應用詳細遮罩到原始模板
            structure_template = cv2.bitwise_and(original_template, original_template, mask=detailed_mask)
            
            # 進行邊緣檢測強化結構特徵
            gray_structure = cv2.cvtColor(structure_template, cv2.COLOR_BGR2GRAY)
            edges = cv2.Canny(gray_structure, 30, 100)  # 降低閾值保留更多細節
            
            # 如果邊緣過於簡化，可以增強處理
            kernel = np.ones((2, 2), np.uint8)
            enhanced_edges = cv2.dilate(edges, kernel, iterations=1)
            
            # 將增強邊緣轉換回彩色格式
            edges_colored = cv2.cvtColor(enhanced_edges, cv2.COLOR_GRAY2BGR)
            
            # 結合原始結構和增強邊緣特徵（調整權重保留更多細節）
            final_template = cv2.addWeighted(structure_template, 0.7, edges_colored, 0.3, 0)
            
            self.logger.info(f"✅ 結構化模板創建完成：保留詳細邊緣細節，強化邊框特徵（邊緣增強）")
            return final_template
            
        except Exception as e:
            self.logger.error(f"創建結構化模板失敗: {e}")
            return original_template
    
    def _create_more_detailed_mask(self, template, hsv):
        """創建更詳細的遮罩，保留更多邊緣細節"""
        try:
            # 1. 基本紅色遮罩（排除主要填充區域）
            lower_red = np.array([0, 30, 30])
            upper_red = np.array([20, 255, 255])
            red_mask = cv2.inRange(hsv, lower_red, upper_red)
            
            # 2. 創建邊緣檢測遮罩
            gray = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY)
            edges = cv2.Canny(gray, 30, 100)
            
            # 3. 創建梯度遮罩（保留漸變區域）
            grad_x = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
            grad_y = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)
            gradient_magnitude = np.sqrt(grad_x**2 + grad_y**2)
            gradient_mask = np.uint8(gradient_magnitude > 10)  # 梯度閾值
            
            # 4. 創建輪廓遮罩
            contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            contour_mask = np.zeros_like(edges)
            for contour in contours:
                if cv2.contourArea(contour) > 5:  # 過濾太小的輪廓
                    cv2.drawContours(contour_mask, [contour], -1, 255, 1)
            
            # 5. 結合多種遮罩
            # 排除紅色填充區域
            non_red_mask = cv2.bitwise_not(red_mask)
            
            # 結合邊緣、梯度和輪廓
            detail_mask = cv2.bitwise_or(edges, gradient_mask)
            detail_mask = cv2.bitwise_or(detail_mask, contour_mask)
            
            # 最終遮罩：非紅色區域 + 詳細邊緣
            final_mask = cv2.bitwise_or(non_red_mask, detail_mask)
            
            # 6. 形態學操作清理遮罩
            kernel = np.ones((2, 2), np.uint8)
            final_mask = cv2.morphologyEx(final_mask, cv2.MORPH_CLOSE, kernel)
            final_mask = cv2.morphologyEx(final_mask, cv2.MORPH_OPEN, kernel)
            
            self.logger.info(f"✅ 詳細遮罩創建完成：結合邊緣、梯度和輪廓特徵")
            return final_mask
            
        except Exception as e:
            self.logger.error(f"創建詳細遮罩失敗: {e}")
            # 回退到基本遮罩
            lower_red = np.array([0, 30, 30])
            upper_red = np.array([20, 255, 255])
            red_mask = cv2.inRange(hsv, lower_red, upper_red)
            return cv2.bitwise_not(red_mask)
    
    def detect_character_health_bars(self, frame):
        """主要檢測方法 - 結構化單模板檢測角色頭頂血條"""
        if frame is None or frame.size == 0:
            return []
            
        if self.structure_template is None:
            self.logger.warning("沒有載入任何模板")
            return []
            
        try:
            # 獲取字典格式的結果
            dict_results = self._detect_with_structure_template(frame)
            
            # 轉換為GUI期望的元組格式 (x, y, w, h, status)
            tuple_results = []
            for result in dict_results:
                x, y, w, h = result['x'], result['y'], result['w'], result['h']
                # 使用模板名稱而不是structure
                template_name = "Health100%"  # 結構化模板的原始模板名稱
                status = f"{template_name} {result['health_percentage']:.1f}%"
                tuple_results.append((x, y, w, h, status))
            
            return tuple_results
            
        except Exception as e:
            self.logger.error(f"角色血條檢測錯誤: {e}")
            return []

    def detect_character_overhead_health(self, frame):
        """兼容性方法：檢測角色上方血條"""
        return self.detect_character_health_bars(frame)
    
    def _detect_with_structure_template(self, frame):
        """結構化單模板檢測角色血條核心方法"""
        try:
            all_matches = []
            frame_h, frame_w = frame.shape[:2]
            
            # 轉換為HSV色彩空間用於填充分析
            hsv_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
            
            # 使用單一結構化模板進行匹配
            template = self.structure_template
            if template is None:
                self.logger.error("❌ 結構化模板未載入")
                return []
    
            # 獲取結構化模板的閾值（降低閾值提高檢測率）
            threshold = self.template_thresholds.get('structure', 0.4)  # 從 0.5 降到 0.4
            
            # 限制搜索區域（只搜索畫面中央區域，角色通常在中央）
            search_ratio = 0.6  # 搜索畫面中央 60% 的區域
            start_y = int(frame_h * (1 - search_ratio) / 2)
            end_y = int(frame_h * (1 + search_ratio) / 2)
            search_frame = frame[start_y:end_y, :]
            
            self.logger.debug(f"🔍 搜索區域: y={start_y}~{end_y}, 閾值={threshold}")
            
            # 階段1: 結構化模板匹配定位血條位置
            result = cv2.matchTemplate(search_frame, template, cv2.TM_CCOEFF_NORMED)
            locations = np.where(result >= threshold)
            
            h, w = template.shape[:2]
            for y, x in zip(locations[0], locations[1]):
                confidence = result[y, x]
                # 調整 y 座標（加上搜索區域的偏移）
                actual_y = y + start_y
                
                # 階段2: 填充分析計算血量
                fill_result = self._analyze_character_bar_fill(hsv_frame, x, actual_y, w, h)
                if fill_result is not None:
                    match = {
                        'x': int(x), 'y': int(actual_y), 'w': int(w), 'h': int(h),
                        'confidence': float(confidence),
                        'template': 'structure',
                        'threshold_used': threshold,
                        'fill_ratio': fill_result['fill_ratio'],
                        'health_percentage': fill_result['fill_ratio'] * 100
                    }
                    all_matches.append(match)
                    self.logger.debug(f"✅ 找到血條: 位置({x}, {actual_y}), 信心度{confidence:.3f}, 血量{fill_result['fill_ratio']*100:.1f}%")
            
            # 簡化處理：只保留前幾個最高信心度的結果
            if all_matches:
                # 按信心度排序
                all_matches.sort(key=lambda x: x['confidence'], reverse=True)
                # 只保留前幾個結果
                filtered_matches = all_matches[:self.max_detections]
                self.logger.info(f"🔍 結構化單模板檢測到 {len(filtered_matches)} 個角色血條")
                return filtered_matches
            else:
                self.logger.debug(f"❌ 未找到任何血條（閾值={threshold}）")
            
            return []
            
        except Exception as e:
            self.logger.error(f"結構化單模板檢測失敗: {e}")
            return []
    
    def _analyze_character_bar_fill(self, hsv_frame, x, y, w, h):
        """分析角色血條填充量"""
        try:
            # 提取血條區域
            bar_region = hsv_frame[y:y+h, x:x+w]
            if bar_region.size == 0:
                return None
            
            # 創建紅色血條的遮罩（適應透明效果）
            lower_red = self.hp_color_lower
            upper_red = self.hp_color_upper
            
            # 檢測紅色像素
            red_mask = cv2.inRange(bar_region, lower_red, upper_red)
            
            # 計算填充比例
            total_pixels = w * h
            red_pixels = np.count_nonzero(red_mask)
            fill_ratio = red_pixels / total_pixels if total_pixels > 0 else 0
            
            # 檢查是否達到最小填充閾值
            if fill_ratio < self.fill_analysis_threshold:
                return None
            
            return {
                'fill_ratio': fill_ratio,
                'red_pixels': red_pixels,
                'total_pixels': total_pixels
            }
            
        except Exception as e:
            self.logger.error(f"填充分析失敗: {e}")
            return None
    
    def update_config(self, config):
        """更新配置"""
        self.config = config
        # 重新載入模板
        self._load_structure_template()
    
    def get_detection_stats(self):
        """獲取檢測統計"""
        return {
            'template_count': 1,
            'template_names': ['Health100%'],
            'thresholds': self.template_thresholds,
            'fill_threshold': self.fill_analysis_threshold
        }

class SimpleHealthDetector(CharacterHealthDetector):
    """簡化版血條檢測器（兼容性）"""
    
    def __init__(self, template_dir="templates/MainScreen", config=None):
        super().__init__(template_dir, config)
    
    def detect(self, frame):
        """簡化檢測方法"""
        return self.detect_character_health_bars(frame)
    
    def _template_to_status(self, template_name):
        """模板名稱轉狀態"""
        return f"結構化模板: {template_name}" 