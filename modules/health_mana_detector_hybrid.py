#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HUD血魔條檢測器 - 混合版
結合模板匹配定位和填充分析，提供更穩健的檢測
增加OCR功能讀取HP數字
"""

import cv2
import numpy as np
import os
import re
try:
    import pytesseract
    TESSERACT_AVAILABLE = True
except ImportError:
    TESSERACT_AVAILABLE = False
    
from includes.log_utils import get_logger

class HealthManaDetectorHybrid:
    """
    HUD血魔條檢測器（混合版）
    結合模板匹配定位和填充分析，增加OCR數字識別
    """
    
    def __init__(self, template_dir="templates/MainScreen", config=None):
        """
        初始化HUD血條檢測器 - 單模板匹配版本
        """
        self.logger = get_logger("HealthManaDetectorHybrid")
        self.logger.info("🔧 初始化HUD血條檢測器 - 單模板匹配版本")
        
        # 基本設定
        self.template_dir = template_dir
        self.config = config or {}
        
        # 檢測開關
        self.enable_hud_health = self.config.get('hud_health', {}).get('enabled', True)
        self.enable_hud_mana = self.config.get('hud_mana', {}).get('enabled', True)
        self.enable_hud_exp = self.config.get('hud_exp', {}).get('enabled', True)
        
        # 搜索區域設定
        self.search_region_ratio = self.config.get('hud_detection', {}).get('search_region_ratio', 0.3)
        
        # 模板匹配設定
        self.match_threshold = self.config.get('hud_detection', {}).get('match_threshold', 0.7)
        self.scale_range = self.config.get('hud_detection', {}).get('scale_range', (0.8, 1.2))
        self.scale_steps = self.config.get('hud_detection', {}).get('scale_steps', 5)
        
        # OCR設定
        self.enable_ocr = self.config.get('hud_ocr', {}).get('enabled', True)
        self.ocr_config = self.config.get('hud_ocr', {})
        
        # 檢查Tesseract可用性
        self.tesseract_path = self.ocr_config.get('tesseract_path', 'tessdataOCR/tesseract.exe')
        self.tesseract_available = self._check_tesseract_availability()
        
        if self.tesseract_available:
            # 設置pytesseract路徑
            try:
                pytesseract.pytesseract.tesseract_cmd = self.tesseract_path
                self.logger.info(f"✅ Tesseract OCR已啟用: {self.tesseract_path}")
            except ImportError:
                self.logger.warning("⚠️ pytesseract模組未安裝，無法使用OCR功能")
                self.tesseract_available = False
        else:
            self.logger.warning("⚠️ Tesseract OCR未啟用，將跳過數字識別")
        
        # 載入模板
        self.templates = self._load_templates()
        
        # 統計資訊
        self.detection_stats = {
            'total_detections': 0,
            'successful_detections': 0,
            'hp_detections': 0,
            'mp_detections': 0,
            'exp_detections': 0,
            'ocr_success_count': 0,
            'ocr_failure_count': 0
        }
        
        self.logger.info("✅ HUD血條檢測器初始化完成")
        self.logger.info(f"   - HP檢測: {'啟用' if self.enable_hud_health else '停用'}")
        self.logger.info(f"   - MP檢測: {'啟用' if self.enable_hud_mana else '停用'}")
        self.logger.info(f"   - EXP檢測: {'啟用' if self.enable_hud_exp else '停用'}")
        self.logger.info(f"   - OCR檢測: {'啟用' if self.enable_ocr and self.tesseract_available else '停用'}")
        self.logger.info(f"   - 模板數量: {len(self.templates)}")
    
    def _load_templates(self):
        """載入單模板"""
        try:
            if not os.path.exists(self.template_dir):
                self.logger.warning(f"⚠️ 模板目錄不存在: {self.template_dir}")
                return {}
            
            # 定義單模板結構 - 每種類型只使用一個模板
            template_structure = {
                'HP': ['HUD_HP100%.png'],  # 只使用100%模板
                'MP': ['HUD_MP.png'],
            }
            
            templates = {}
            
            for bar_type, filenames in template_structure.items():
                templates[bar_type] = []
                
                for filename in filenames:
                    file_path = os.path.join(self.template_dir, filename)
                    
                    if os.path.exists(file_path):
                        template_img = self._safe_imread(file_path, cv2.IMREAD_COLOR)
                        if template_img is not None:
                            # 轉為灰階用於匹配
                            template_gray = cv2.cvtColor(template_img, cv2.COLOR_BGR2GRAY)
                            
                            template_info = {
                                'name': filename,
                                'original_name': filename,
                                'image': template_gray,
                                'color_image': template_img,
                                'size': template_gray.shape,
                                'bar_type': bar_type
                            }
                            
                            templates[bar_type].append(template_info)
                            self.logger.info(f"✅ 載入{bar_type}單模板: {filename} ({template_gray.shape[1]}x{template_gray.shape[0]})")
                        else:
                            self.logger.warning(f"⚠️ 無法載入模板: {filename}")
                    else:
                        self.logger.warning(f"⚠️ 模板檔案不存在: {filename}")
            
            # 統計載入的模板
            total_templates = sum(len(templates) for templates in templates.values())
            self.logger.info(f"📊 總共載入 {total_templates} 個單模板")
            
            return templates
        
        except Exception as e:
            self.logger.error(f"❌ 載入單模板失敗: {e}")
            import traceback
            traceback.print_exc()
            return {}
    
    def _safe_imread(self, image_path, flags=cv2.IMREAD_COLOR):
        """安全讀取圖像"""
        try:
            if isinstance(image_path, bytes):
                image_path = image_path.decode('utf-8', errors='ignore')
            
            if not os.path.exists(image_path):
                return None
            
            image = cv2.imread(image_path, flags)
            return image
        except Exception as e:
            self.logger.error(f"❌ 讀取圖像失敗 {image_path}: {e}")
            return None
    
    def detect_hud_bars(self, frame):
        """
        單模板匹配檢測HUD血條
        1. 單模板匹配定位血條位置
        2. HP/MP 條皆進行OCR
        """
        try:
            if not self.enable_hud_health and not self.enable_hud_mana and not self.enable_hud_exp:
                return {'detected': False}
            
            results = {'detected': False, 'detection_method': 'single_template_matching'}
            h, w = frame.shape[:2]
            search_y = int(h * (1 - self.search_region_ratio))
            search_area = frame[search_y:, :]
            offset_y = search_y
            detected_bars = []
            total_confidence = 0.0
            for bar_type in ['HP', 'MP', 'EXP']:
                if not self._is_bar_enabled(bar_type):
                    continue
                template_result = self._detect_with_template_matching(search_area, bar_type, offset_y)
                if template_result:
                    results[f'{bar_type.lower()}_rect'] = [
                        template_result['pos'][0],
                        template_result['pos'][1],
                        template_result['size'][0],
                        template_result['size'][1]
                    ]
                    results[f'{bar_type.lower()}_confidence'] = template_result['score']
                    # HP/MP都進行OCR
                    if bar_type in ['HP', 'MP'] and self.enable_ocr and self.tesseract_available:
                        self.logger.info(f"🔍 開始對{bar_type}進行OCR檢測...")
                        ocr_result = self._extract_hp_numbers(frame, template_result)
                        if ocr_result:
                            results[f'{bar_type.lower()}_current'] = ocr_result['current']
                            results[f'{bar_type.lower()}_max'] = ocr_result['max']
                            results[f'{bar_type.lower()}_text'] = ocr_result['text']
                            results[f'{bar_type.lower()}_raw_text'] = ocr_result['raw_text']
                            results[f'{bar_type.lower()}_ocr_region'] = ocr_result.get('ocr_region')
                            self.logger.info(f"🔢 OCR檢測到{bar_type}數字: {ocr_result['text']}")
                        else:
                            self.logger.info(f"❌ OCR未能識別{bar_type}數字")
                    else:
                        self.logger.info(f"⚠️ {bar_type} OCR跳過 - enable_ocr={self.enable_ocr}, tesseract_available={self.tesseract_available}")
                    detected_bars.append(bar_type)
                    total_confidence += template_result['score']
                    self.logger.info(f"✅ 單模板檢測到{bar_type}血條: 位置{template_result['pos']}, 信心度{template_result['score']:.3f}")
            if detected_bars:
                results['detected'] = True
                results['confidence'] = total_confidence / len(detected_bars)
                all_rects = []
                for bar_type in ['hp_rect', 'mp_rect', 'exp_rect']:
                    if bar_type in results:
                        all_rects.append(results[bar_type])
                if all_rects:
                    min_x = min(rect[0] for rect in all_rects)
                    min_y = min(rect[1] for rect in all_rects)
                    max_x = max(rect[0] + rect[2] for rect in all_rects)
                    max_y = max(rect[1] + rect[3] for rect in all_rects)
                    results['hud_rect'] = [min_x, min_y, max_x - min_x, max_y - min_y]
                self.logger.info(f"🎯 單模板HUD檢測成功: 找到 {len(detected_bars)} 個血條，平均信心度: {results['confidence']:.3f}")
                for bar_type in detected_bars:
                    self.logger.info(f"   {bar_type}: 信心度{results[f'{bar_type.lower()}_confidence']:.3f}")
            else:
                self.logger.debug("❌ 單模板HUD檢測: 未找到任何血條")
            return results
        except Exception as e:
            self.logger.error(f"HUD血條檢測錯誤: {e}")
            return {'detected': False}
    
    def _detect_with_template_matching(self, search_area, bar_type, offset_y):
        """單模板匹配定位血條位置"""
        if bar_type not in self.templates or not self.templates[bar_type]:
            return None
        
        # 單模板匹配 - 只使用第一個模板
        template_info = self.templates[bar_type][0]
        template = template_info['image']
        
        # 轉灰階
        gray_search_area = cv2.cvtColor(search_area, cv2.COLOR_BGR2GRAY) if len(search_area.shape) == 3 else search_area
        
        # 模板匹配
        result = cv2.matchTemplate(gray_search_area, template, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, max_loc = cv2.minMaxLoc(result)
        
        self.logger.info(f"🔍 {bar_type}單模板匹配分數: {max_val:.3f}")
        
        # 檢查是否超過閾值
        if max_val >= self.match_threshold:
            h, w = template.shape
            x, y = max_loc[0], max_loc[1] + offset_y
            
            return {
                'pos': (x, y),
                'size': (w, h),
                'score': max_val,
                'type': bar_type,
                'template_name': template_info['name']
            }
        
        return None
    
    def _is_bar_enabled(self, bar_type):
        """檢查血條類型是否啟用"""
        if bar_type == 'HP':
            return self.enable_hud_health
        elif bar_type == 'MP':
            return self.enable_hud_mana
        elif bar_type == 'EXP':
            return self.enable_hud_exp
        return False
    
    def detect(self, frame):
        """檢測HUD血條"""
        return self.detect_hud_bars(frame)
    
    def get_detection_stats(self):
        """獲取檢測統計"""
        try:
            # 計算模板數量
            template_counts = {}
            for bar_type, templates in self.templates.items():
                template_counts[bar_type] = len(templates)
            
            return {
                'hud_health_enabled': self.enable_hud_health,
                'hud_mana_enabled': self.enable_hud_mana,
                'hud_exp_enabled': self.enable_hud_exp,
                'match_threshold': self.match_threshold,
                'scale_range': self.scale_range,
                'scale_steps': self.scale_steps,
                'template_counts': template_counts,
                'total_templates': sum(template_counts.values()),
                'detection_method': 'single_template_matching',
                'status': 'hud_detection_ready',
                'ocr_enabled': self.enable_ocr and self.tesseract_available,
                'detection_stats': self.detection_stats
            }
        except Exception as e:
            self.logger.error(f"獲取檢測統計失敗: {e}")
            return {}
    
    def _extract_hp_numbers(self, frame, template_result):
        """
        🆕 使用OCR提取HP數字（僅在血條區域內）
        Args:
            frame: 原始畫面
            template_result: 血條模板匹配結果
        Returns:
            dict: {'current': int, 'max': int, 'text': str} 或 None
        """
        if not self.tesseract_available:
            self.logger.warning("Tesseract OCR 不可用，無法讀取HP數字")
            return None
        
        try:
            x, y = template_result['pos']
            w, h = template_result['size']
            bar_type = template_result.get('type', 'UNKNOWN')
            
            # 🎯 直接使用檢測到的血條區域，不擴展
            # MP血條和HP血條都使用相同的OCR區域邏輯
            search_x = x
            search_y = y
            search_w = w
            search_h = h
            
            # 確保不超出畫面邊界
            frame_h, frame_w = frame.shape[:2]
            search_x = max(0, search_x)
            search_y = max(0, search_y)
            search_w = min(search_w, frame_w - search_x)
            search_h = min(search_h, frame_h - search_y)
            
            # 提取血條區域
            search_region = frame[search_y:search_y+search_h, search_x:search_x+search_w]
            
            # 🎨 圖像預處理增強OCR效果
            enhanced_region = self._preprocess_for_ocr(search_region)
            
            # 🔤 根據血條類型配置Tesseract參數和使用的圖像
            if bar_type == 'MP':
                # MP專用OCR配置，使用原始圖像（效果更好）
                custom_config = r'--oem 3 --psm 7 -c tessedit_char_whitelist=0123456789MP/[]'
                ocr_image = cv2.cvtColor(search_region, cv2.COLOR_BGR2GRAY) if len(search_region.shape) == 3 else search_region
                self.logger.info(f"🔍 使用MP專用OCR配置: 支持MP字母和方括號，使用原始圖像")
            else:
                # HP保持原配置，使用預處理圖像
                custom_config = r'--oem 3 --psm 6 -c tessedit_char_whitelist=0123456789/'
                ocr_image = enhanced_region
            
            # 🔍 執行OCR
            text = pytesseract.image_to_string(ocr_image, config=custom_config).strip()
            
            # 📝 輸出原始OCR文字（調試用）
            if text:
                self.logger.info(f"🔍 {bar_type} OCR原始識別文字: '{text}'")
            else:
                self.logger.info(f"🔍 {bar_type} OCR未識別到任何文字")
            
            if text:
                # 🧮 根據血條類型解析不同格式
                if bar_type == 'MP':
                    # MP血條可能的格式: "MP[123/456]", "MP1123/456]", "MP 123/456"
                    
                    # 處理 "MP1362/362]" 格式（左方括號被誤識別為1）
                    mp_bracket_fix_match = re.search(r'MP1(\d+)/(\d+)\]', text)
                    if mp_bracket_fix_match:
                        current_hp = int(mp_bracket_fix_match.group(1))
                        max_hp = int(mp_bracket_fix_match.group(2))
                        self.logger.info(f"🎯 {bar_type} OCR解析修正格式: {current_hp}/{max_hp} (原文: {text})")
                        return {
                            'current': current_hp,
                            'max': max_hp,
                            'text': f"{current_hp}/{max_hp}",
                            'raw_text': text,
                            'ocr_region': (search_x, search_y, search_w, search_h)
                        }
                    
                    # 先嘗試提取方括號內的內容 "MP[123/456]"
                    bracket_match = re.search(r'MP\[(\d+)/(\d+)\]', text)
                    if bracket_match:
                        current_hp = int(bracket_match.group(1))
                        max_hp = int(bracket_match.group(2))
                        self.logger.info(f"🎯 {bar_type} OCR解析方括號格式: {current_hp}/{max_hp}")
                        return {
                            'current': current_hp,
                            'max': max_hp,
                            'text': f"{current_hp}/{max_hp}",
                            'raw_text': text,
                            'ocr_region': (search_x, search_y, search_w, search_h)
                        }
                    
                    # 嘗試 "MP 123/456" 格式
                    mp_match = re.search(r'MP\s*(\d+)/(\d+)', text)
                    if mp_match:
                        current_hp = int(mp_match.group(1))
                        max_hp = int(mp_match.group(2))
                        self.logger.info(f"🎯 {bar_type} OCR解析MP格式: {current_hp}/{max_hp}")
                        return {
                            'current': current_hp,
                            'max': max_hp,
                            'text': f"{current_hp}/{max_hp}",
                            'raw_text': text,
                            'ocr_region': (search_x, search_y, search_w, search_h)
                        }
                
                # 通用解析: "123/456" 或 "123 / 456"
                hp_match = re.search(r'(\d+)\s*/\s*(\d+)', text)
                if hp_match:
                    current_hp = int(hp_match.group(1))
                    max_hp = int(hp_match.group(2))
                    
                    self.logger.info(f"🎯 {bar_type} OCR成功解析: {current_hp}/{max_hp}")
                    
                    return {
                        'current': current_hp,
                        'max': max_hp,
                        'text': f"{current_hp}/{max_hp}",
                        'raw_text': text,
                        'ocr_region': (search_x, search_y, search_w, search_h)  # 血條區域信息
                    }
                else:
                    # 嘗試只提取單個數字
                    numbers = re.findall(r'\d+', text)
                    if len(numbers) >= 2:
                        current_hp = int(numbers[0])
                        max_hp = int(numbers[1])
                        
                        self.logger.info(f"🎯 {bar_type} OCR提取多個數字: {current_hp}/{max_hp}")
                        
                        return {
                            'current': current_hp,
                            'max': max_hp,
                            'text': f"{current_hp}/{max_hp}",
                            'raw_text': text,
                            'ocr_region': (search_x, search_y, search_w, search_h)  # 血條區域信息
                        }
                    elif len(numbers) == 1:
                        # 只有一個數字，可能是當前HP
                        current_hp = int(numbers[0])
                        self.logger.info(f"🎯 {bar_type} OCR提取單個數字: {current_hp}")
                        
                        return {
                            'current': current_hp,
                            'max': None,
                            'text': str(current_hp),
                            'raw_text': text,
                            'ocr_region': (search_x, search_y, search_w, search_h)  # 血條區域信息
                        }
            
            self.logger.info(f"❌ {bar_type} OCR無法解析文字: '{text}'")
            return None
            
        except Exception as e:
            self.logger.error(f"{bar_type} OCR提取數字失敗: {e}")
            return None
    
    def _preprocess_for_ocr(self, image):
        """
        🎨 圖像預處理以提高OCR準確性
        """
        try:
            # 轉換為灰度
            if len(image.shape) == 3:
                gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            else:
                gray = image.copy()
            
            # 🔍 放大圖像以提高OCR準確性
            scale_factor = 3
            enlarged = cv2.resize(gray, None, fx=scale_factor, fy=scale_factor, interpolation=cv2.INTER_CUBIC)
            
            # 🎭 二值化處理
            # 使用自適應閾值處理不同光照條件
            binary = cv2.adaptiveThreshold(enlarged, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)
            
            # 🧹 形態學操作去除噪點
            kernel = np.ones((2, 2), np.uint8)
            cleaned = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)
            
            # 🔄 反轉顏色（黑底白字更適合OCR）
            inverted = cv2.bitwise_not(cleaned)
            
            return inverted
            
        except Exception as e:
            self.logger.error(f"圖像預處理失敗: {e}")
            return image
    
    def detect_hud_bars_with_ocr(self, frame):
        """
        🆕 單模板匹配檢測HUD血條（包含OCR數字讀取）
        """
        # 先執行常規檢測
        results = self.detect_hud_bars(frame)
        
        # 如果檢測到HP血條且OCR可用，嘗試讀取數字
        if (results.get('detected') and 'hp_rect' in results and 
            self.enable_ocr and self.tesseract_available):
            
            # 模擬template_result格式
            hp_rect = results['hp_rect']
            template_result = {
                'pos': (hp_rect[0], hp_rect[1]),
                'size': (hp_rect[2], hp_rect[3])
            }
            
            ocr_result = self._extract_hp_numbers(frame, template_result)
            if ocr_result:
                results.update({
                    'hp_current': ocr_result['current'],
                    'hp_max': ocr_result['max'],
                    'hp_text': ocr_result['text'],
                    'hp_raw_text': ocr_result['raw_text'],
                    'hp_ocr_region': ocr_result.get('ocr_region')  # 添加OCR區域信息
                })
                self.logger.info(f"🔢 OCR檢測到HP數字: {ocr_result['text']}")
        
        return results
    
    def _check_tesseract_availability(self):
        """檢查Tesseract可用性"""
        if not os.path.exists(self.tesseract_path):
            self.logger.warning(f"⚠️ Tesseract OCR路徑不存在: {self.tesseract_path}")
            return False
        return True
    
    def update_tesseract_path(self, new_path):
        """更新Tesseract路徑"""
        self.tesseract_path = new_path
        self.ocr_config['tesseract_path'] = new_path
        self.tesseract_available = self._check_tesseract_availability()
        if self.tesseract_available:
            self.logger.info(f"✅ Tesseract OCR已更新路徑: {new_path}")
        else:
            self.logger.warning("⚠️ Tesseract OCR未啟用，將跳過數字識別")
        return self.tesseract_available 