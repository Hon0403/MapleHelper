import cv2
import numpy as np
import time
from typing import Tuple, Optional, Dict
import os
import re
import subprocess
from includes.config_utils import create_config_section
from includes.log_utils import get_logger

class HealthManaDetector:
    def __init__(self, template_dir="templates/MainScreen", tesseract_dir="tessdataOCR", config=None):
        # ✅ 使用共用工具初始化
        self.logger = get_logger("HealthManaDetector")
        
        # 載入模板並處理
        self.template_dir = template_dir
        self.tesseract_dir = tesseract_dir
        
        # ✅ 保存原始 config 以保持向後相容
        self.config = config or {}
        
        # ✅ 使用 ConfigSection 簡化配置讀取
        if config:
            config_section = create_config_section(config, 'health_detector')
            self.hud_threshold = config_section.get_float('hud_threshold', 0.3)
            self.bar_threshold = config_section.get_float('bar_threshold', 0.2)
            self.cache_timeout = config_section.get_float('cache_timeout', 1.0)
            self.debug_mode = config_section.get_bool('debug_mode', False)
            
            # ✅ 新增：從設定檔讀取所有血條檢測相關參數
            self.border_template_path = config_section.get_string('border_template', "templates/MainScreen/HealthBar.png")
            self.threshold = config_section.get_float('threshold', 0.6)
            self.canny_low = config_section.get_int('canny_low', 30)
            self.canny_high = config_section.get_int('canny_high', 100)
            self.color_ratio_threshold = config_section.get_float('color_ratio_threshold', 0.1)
            self.min_color_pixels = config_section.get_int('min_color_pixels', 20)
            self.overlap_threshold = config_section.get_float('overlap_threshold', 0.3)
            
            # ✅ 新增：從設定檔讀取顏色範圍
            colors_config = config.get('colors', {})
            self.green_lower = np.array(colors_config.get('green_lower', [35, 100, 50]))
            self.green_upper = np.array(colors_config.get('green_upper', [85, 255, 255]))
            self.red_lower1 = np.array(colors_config.get('red_lower1', [0, 120, 70]))
            self.red_upper1 = np.array(colors_config.get('red_upper1', [10, 255, 255]))
            self.red_lower2 = np.array(colors_config.get('red_lower2', [170, 120, 70]))
            self.red_upper2 = np.array(colors_config.get('red_upper2', [180, 255, 255]))
            
        else:
            # 預設值
            self.hud_threshold = 0.3
            self.bar_threshold = 0.2
            self.cache_timeout = 1.0
            self.debug_mode = False
            
            # 血條檢測預設值
            self.border_template_path = "templates/MainScreen/HealthBar.png"
            self.threshold = 0.6
            self.canny_low = 30
            self.canny_high = 100
            self.color_ratio_threshold = 0.1
            self.min_color_pixels = 20
            self.overlap_threshold = 0.3
            
            # 顏色範圍預設值
            self.green_lower = np.array([35, 100, 50])
            self.green_upper = np.array([85, 255, 255])
            self.red_lower1 = np.array([0, 120, 70])
            self.red_upper1 = np.array([10, 255, 255])
            self.red_lower2 = np.array([170, 120, 70])
            self.red_upper2 = np.array([180, 255, 255])
        
        # 設置Tesseract路徑
        self.tesseract_exe = os.path.join(tesseract_dir, "tesseract.exe")
        self.tessdata_dir = os.path.join(tesseract_dir, "tessdata")
        
        # 檢查OCR文件是否存在和有效
        if not os.path.exists(self.tesseract_exe):
            self.logger.warning(f"Tesseract執行文件不存在: {self.tesseract_exe}")
        if not os.path.exists(self.tessdata_dir):
            self.logger.warning(f"Tessdata目錄不存在: {self.tessdata_dir}")
        
        # 檢查Tesseract是否可用
        self.tesseract_available = self._check_tesseract_availability()
        
        try:
            # 載入HUD模板
            template = cv2.imread(os.path.join(template_dir, "HUD.png"), cv2.IMREAD_COLOR)
            if template is None:
                raise ValueError("無法載入HUD模板文件")
                
            # 載入HP和MP模板
            self.hp_template = cv2.imread(os.path.join(template_dir, "HP.png"), cv2.IMREAD_COLOR)
            self.mp_template = cv2.imread(os.path.join(template_dir, "MP.png"), cv2.IMREAD_COLOR)
            
            if self.hp_template is None or self.mp_template is None:
                raise ValueError("無法載入HP或MP模板文件")
            
            # 處理HUD模板
            gray = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY)
            self.hud_template = gray
            
            # 驗證模板格式
            if len(self.hud_template.shape) != 2:
                raise ValueError("HUD模板必須是灰度圖")
            if len(self.hp_template.shape) != 3 or self.hp_template.shape[2] != 3:
                raise ValueError("HP模板必須是3通道BGR圖像")
            if len(self.mp_template.shape) != 3 or self.mp_template.shape[2] != 3:
                raise ValueError("MP模板必須是3通道BGR圖像")
            
        except Exception as e:
            self.logger.error("模板初始化錯誤", e)
            raise
            
        # 其他參數
        self.min_match_count = 3
        
        # 快取機制
        self.hud_cache = None
        self.hp_roi_cache = None
        self.mp_roi_cache = None
        self.last_hud_time = 0
        self.match_history = []
        
        # OCR設置 - 根據Tesseract可用性動態設置
        if self.tesseract_available:
            self.use_ocr = True  # 啟用OCR，使用改進的預處理
            self.logger.info("OCR功能已啟用")
        else:
            self.use_ocr = False  # 禁用OCR，使用顏色檢測
            self.logger.warning("OCR功能已禁用，使用顏色檢測")

        # 模板匹配相關
        self.templates = {}
        self._load_templates()

        # ✅ 為頭頂血條新增單一邊框模板
        self.health_border_template = None
        self._initialize_border_templates()
        
        self.logger.init_success("血條檢測器")

    def _check_tesseract_availability(self):
        """檢查Tesseract是否可用 - 簡化版"""
        try:
            cmd = [self.tesseract_exe, "--version"]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0 and result.stdout.strip():
                return True
            else:
                return False
                
        except Exception:
            return False

    def _is_rgb_format(self, image):
        """檢測圖像是否為RGB格式"""
        try:
            # 簡單的RGB檢測邏輯
            # 檢查圖像的顏色分佈特徵
            if len(image.shape) != 3:
                return False
            
            # 檢查是否有明顯的顏色偏差（RGB vs BGR）
            # 這是一個簡化的檢測，實際使用時可能需要更複雜的邏輯
            b_channel = image[:, :, 0]
            r_channel = image[:, :, 2]
            
            # 如果紅色通道的平均值明顯大於藍色通道，可能是RGB格式
            r_mean = np.mean(r_channel)
            b_mean = np.mean(b_channel)
            
            # 這個閾值可能需要根據實際情況調整
            return r_mean > b_mean * 1.5
        except:
            return False

    def _extract_text_region(self, bar_region):
        """直接使用整個血條區域，不做額外切割"""
        try:
            # 直接返回整個血條區域，讓Tesseract自己找數字
            return bar_region
            
        except Exception as e:
            return bar_region

    def _run_simple_ocr(self, image):
        """基於OpenCV的簡單OCR替代方案"""
        try:
            # 轉換為灰度圖
            if len(image.shape) == 3:
                gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            else:
                gray = image.copy()
            
            # 放大圖像
            scale_factor = 3
            height, width = gray.shape
            enlarged = cv2.resize(gray, (width * scale_factor, height * scale_factor), 
                                 interpolation=cv2.INTER_CUBIC)
            
            # 增強對比度
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
            enhanced = clahe.apply(enlarged)
            
            # 二值化
            _, binary = cv2.threshold(enhanced, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            
            # 形態學操作
            kernel = np.ones((2, 2), np.uint8)
            cleaned = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)
            
            # 這裡可以添加更複雜的數字識別邏輯
            # 目前返回空字符串，表示需要進一步處理
            return ""
            
        except Exception as e:
            return ""

    def _run_tesseract_ocr(self, image, config=None):
        """針對方括號格式優化的OCR"""
        try:
            temp_image_path = "temp_ocr_image.png"
            cv2.imwrite(temp_image_path, image, [cv2.IMWRITE_PNG_COMPRESSION, 0])
            best_text = ""
            best_score = 0
            
            # 針對方括號格式的參數組合
            psm_configs = [
                (8, "單字元模式"),   # 最適合數字
                (7, "單行文字"),     # 適合 564/564 格式
                (6, "假設統一文字塊"), # 適合方括號包圍
                (13, "單行數字")     # 純數字模式
            ]
            
            for psm, desc in psm_configs:
                cmd = [
                    self.tesseract_exe,
                    temp_image_path,
                    "stdout",
                    "--tessdata-dir", self.tessdata_dir,
                    "-l", "eng",
                    "--psm", str(psm),
                    "-c", "tessedit_char_whitelist=0123456789/[]",  # 加入方括號
                    "-c", "tessedit_char_blacklist=ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz",  # 排除字母
                    "-c", "tessedit_do_invert=0"  # 不反轉顏色
                ]
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
                text = result.stdout.strip() if result.returncode == 0 else ""
                
                # 評分：優先選擇包含斜線的結果
                score = 0
                if '/' in text:
                    score += 10  # 斜線很重要
                if '[' in text and ']' in text:
                    score += 5   # 方括號加分
                score += len(re.sub(r"[^0-9]", "", text))  # 數字長度
                
                if score > best_score:
                    best_score = score
                    best_text = text
            
            if os.path.exists(temp_image_path):
                os.remove(temp_image_path)
            return best_text
        except Exception as e:
            return ""

    def _preprocess_for_ocr(self, roi):
        """針對方括號格式優化的OCR預處理"""
        try:
            text_roi = self._extract_text_region(roi)
            if len(text_roi.shape) == 3:
                gray = cv2.cvtColor(text_roi, cv2.COLOR_BGR2GRAY)
            else:
                gray = text_roi.copy()
            
            # 放大8倍（比之前更大）
            scale_factor = 8
            height, width = gray.shape
            enlarged = cv2.resize(gray, (width * scale_factor, height * scale_factor), interpolation=cv2.INTER_CUBIC)
            
            # 強力去雜訊
            median = cv2.medianBlur(enlarged, 5)  # 更強的中值濾波
            blurred = cv2.GaussianBlur(median, (5, 5), 0)  # 更大的高斯模糊
            
            # 對比度增強
            clahe = cv2.createCLAHE(clipLimit=8.0, tileGridSize=(8,8))  # 更強的對比度
            enhanced = clahe.apply(blurred)
            
            # 嘗試多種二值化方法
            # 方法1：自適應二值化
            binary1 = cv2.adaptiveThreshold(enhanced, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)
            
            # 方法2：OTSU二值化
            _, binary2 = cv2.threshold(enhanced, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            
            # 方法3：固定閾值（針對白色數字）
            _, binary3 = cv2.threshold(enhanced, 200, 255, cv2.THRESH_BINARY)
            
            # 選擇最佳的二值化結果（保留最清晰的數字）
            # 計算每個二值化圖的連通區域數量，選擇最合理的
            def count_connected_components(binary_img):
                num_labels, labels = cv2.connectedComponents(binary_img)
                return num_labels
            
            binary_results = [binary1, binary2, binary3]
            best_binary = max(binary_results, key=count_connected_components)
            
            # 形態學操作：去除小雜訊，保留數字
            kernel = np.ones((3, 3), np.uint8)
            cleaned = cv2.morphologyEx(best_binary, cv2.MORPH_CLOSE, kernel)
            cleaned = cv2.morphologyEx(cleaned, cv2.MORPH_OPEN, kernel)
            
            return cleaned
        except Exception as e:
            return roi

    def _extract_numbers_from_text(self, text):
        """針對方括號格式優化的數字提取"""
        try:
            # 清理文本
            text = text.strip().replace(" ", "").replace("\n", "")
            
            # 針對方括號格式的模式
            patterns = [
                r'\[(\d+)/(\d+)\]',  # 格式: [123/456]
                r'(\d+)/(\d+)',      # 格式: 123/456
                r'\[(\d+)\]',        # 格式: [123]
                r'(\d+)',            # 格式: 123
            ]
            
            for pattern in patterns:
                match = re.search(pattern, text)
                if match:
                    if len(match.groups()) == 2:
                        # current/max 格式
                        current = int(match.group(1))
                        maximum = int(match.group(2))
                        if maximum > 0:
                            percentage = (current / maximum) * 100
                            return min(100.0, max(0.0, percentage))
                    else:
                        # 只有一個數字
                        number = int(match.group(1))
                        if 0 <= number <= 100:
                            return float(number)
                        elif number > 100:
                            # 可能是血量數值，假設最大血量為1000
                            percentage = (number / 1000) * 100
                            return min(100.0, max(0.0, percentage))
            
                return 0.0
            
        except Exception as e:
            return 0.0

    def _detect_bar_percentage_by_ocr(self, bar_region, bar_type) -> float:
        """使用OCR檢測血條或魔力條的百分比 - 改進版"""
        if not self.use_ocr or bar_region is None or bar_region.size == 0:
            return 0.0

        try:
            # 預處理圖像
            processed_image = self._preprocess_for_ocr(bar_region)
            
            # 首先嘗試Tesseract OCR
            ocr_text = self._run_tesseract_ocr(processed_image)
            
            if ocr_text:
                # 從文本中提取百分比
                percentage = self._extract_numbers_from_text(ocr_text)
                return percentage
            
            # 如果Tesseract失敗，嘗試簡單OCR
            simple_text = self._run_simple_ocr(processed_image)
            if simple_text:
                percentage = self._extract_numbers_from_text(simple_text)
                return percentage
            
            return 0.0
            
        except Exception as e:
            return 0.0

    def _calculate_bar_percentage(self, bar_region, bar_type) -> float:
        """只用OCR，不再有顏色法備用"""
        if bar_region is None or bar_region.size == 0:
            return 0.0
        return self._detect_bar_percentage_by_ocr(bar_region, bar_type)

    def detect_hud_health_mana(self, frame) -> dict:
        """檢測HUD血量和魔力值（左下角UI）"""
        if frame is None:
            return {
                "success": False,
                "hp": 0,
                "mp": 0,
                "hp_percentage": 0.0,
                "mp_percentage": 0.0,
                "hud_rect": None,
                "hp_rect": None,
                "mp_rect": None
            }
        
        try:
            # 檢測HUD位置
            hud_result = self._locate_hud_with_position(frame)
            if hud_result is None:
                return {
                    "success": False,
                    "hp": 0,
                    "mp": 0,
                    "hp_percentage": 0.0,
                    "mp_percentage": 0.0,
                    "hud_rect": None,
                    "hp_rect": None,
                    "mp_rect": None
                }
            
            hud_region, hud_rect = hud_result
            
            # 檢測HP和MP條
            hp_result = self._detect_bar_with_position(hud_region, "HP", hud_rect)
            mp_result = self._detect_bar_with_position(hud_region, "MP", hud_rect)
            
            hp_percentage = 0.0
            mp_percentage = 0.0
            hp_rect = None
            mp_rect = None
            
            if hp_result:
                hp_roi, hp_rect = hp_result
                hp_percentage = self._calculate_bar_percentage(hp_roi, "HP")
            
            if mp_result:
                mp_roi, mp_rect = mp_result
                mp_percentage = self._calculate_bar_percentage(mp_roi, "MP")
            
            return {
                "success": True,
                "hp": int(hp_percentage),
                "mp": int(mp_percentage),
                "hp_percentage": hp_percentage,
                "mp_percentage": mp_percentage,
                "hud_rect": hud_rect,
                "hp_rect": hp_rect,
                "mp_rect": mp_rect
            }
            
        except Exception as e:
            return {
                "success": False,
                "hp": 0,
                "mp": 0,
                "hp_percentage": 0.0,
                "mp_percentage": 0.0,
                "hud_rect": None,
                "hp_rect": None,
                "mp_rect": None
            }

    def _locate_hud_with_position(self, frame):
        """定位HUD並返回位置信息"""
        if frame is None:
            return None

        try:
            # 轉換為灰度圖
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            
            # 模板匹配
            result = cv2.matchTemplate(gray, self.hud_template, cv2.TM_CCOEFF_NORMED)
            min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
            
            # 檢查匹配度
            if max_val >= 0.15:
                x, y = max_loc
                h, w = self.hud_template.shape
                
                # 確保區域在圖像範圍內
                x = max(0, min(x, frame.shape[1] - w))
                y = max(0, min(y, frame.shape[0] - h))
                
                hud_roi = frame[y:y+h, x:x+w]
                hud_rect = (x, y, w, h)
                
                return hud_roi, hud_rect
            else:
                # 嘗試備用匹配方法
                result2 = cv2.matchTemplate(gray, self.hud_template, cv2.TM_CCORR_NORMED)
                min_val2, max_val2, min_loc2, max_loc2 = cv2.minMaxLoc(result2)
                
                if max_val2 >= 0.1:
                    x, y = max_loc2
                    h, w = self.hud_template.shape
                    
                    x = max(0, min(x, frame.shape[1] - w))
                    y = max(0, min(y, frame.shape[0] - h))
                    
                    hud_roi = frame[y:y+h, x:x+w]
                    hud_rect = (x, y, w, h)
            
                    return hud_roi, hud_rect
                
                return None
            
        except Exception as e:
            return None
        
    def _detect_bar_with_position(self, frame, bar_type, hud_rect):
        """檢測血條或魔力條並返回位置信息 - 擴大ROI"""
        if frame is None:
            return None

        try:
            template = self.hp_template if bar_type == "HP" else self.mp_template
            result = cv2.matchTemplate(frame, template, cv2.TM_CCOEFF_NORMED)
            min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)

            if max_val >= self.bar_threshold:
                x, y = max_loc
                h, w = template.shape[:2]
                
                # 擴大ROI區域，包含數字區域
                expand_right = int(w * 0.5)  # 向右擴大50%
                expand_left = int(w * 0.1)   # 向左擴大10%
                expand_top = int(h * 0.1)    # 向上擴大10%
                expand_bottom = int(h * 0.1) # 向下擴大10%
                
                # 計算擴大後的座標
                expanded_x = max(0, x - expand_left)
                expanded_y = max(0, y - expand_top)
                expanded_w = min(frame.shape[1] - expanded_x, w + expand_left + expand_right)
                expanded_h = min(frame.shape[0] - expanded_y, h + expand_top + expand_bottom)
                
                bar_roi = frame[expanded_y:expanded_y+expanded_h, expanded_x:expanded_x+expanded_w]
                
                # 轉換為全域座標
                global_x = hud_rect[0] + expanded_x
                global_y = hud_rect[1] + expanded_y
                bar_rect = (global_x, global_y, expanded_w, expanded_h)
                
                return bar_roi, bar_rect
            
            return None
            
        except Exception as e:
            return None

    def _load_templates(self):
        """載入所有HUD模板"""
        try:
            # 遍歷模板目錄
            for filename in os.listdir(self.template_dir):
                if filename.endswith(".png"):
                    template_path = os.path.join(self.template_dir, filename)
                    template = cv2.imread(template_path, cv2.IMREAD_GRAYSCALE)
                    if template is not None:
                        self.templates[filename] = template
                        self.logger.info(f"已載入模板: {filename}")
                    else:
                        self.logger.warning(f"讀取模板失敗: {filename}")

            self.logger.info(f"已載入 {len(self.templates)} 個 HUD 模板")

        except Exception as e:
            self.logger.error(f"載入模板時發生錯誤: {e}")

    def _initialize_border_templates(self):
        """初始化頭頂血條的單一邊框模板"""
        try:
            # ✅ 使用從設定檔讀取的模板路徑
            border_template = self.border_template_path
            
            if os.path.exists(border_template):
                self.health_border_template = cv2.imread(border_template, cv2.IMREAD_GRAYSCALE)
                if self.health_border_template is not None:
                    self.logger.info(f"成功載入血條邊框模板: {border_template}")
                    return
                else:
                    self.logger.warning(f"讀取血條邊框模板失敗: {border_template}")
            else:
                self.logger.warning(f"血條邊框模板檔案不存在: {border_template}")

        except Exception as e:
            self.logger.error(f"初始化邊框模板時發生錯誤: {e}")

    def find_template_matches(self, frame, template_name, threshold=0.8):
        """
        在給定的圖像中查找指定模板的匹配位置。

        Args:
            frame (np.array): 輸入圖像。
            template_name (str): 模板的名稱。
            threshold (float): 匹配閾值。

        Returns:
            list: 匹配位置的列表，每個位置是一個元組 (x, y, w, h)。
        """
        if frame is None or frame.size == 0:
            return []

        template = self.templates.get(template_name)
        if template is None:
            self.logger.warning(f"模板 '{template_name}' 未載入")
            return []
        
        try:
            result = cv2.matchTemplate(frame, template, cv2.TM_CCOEFF_NORMED)
            locations = np.where(result >= threshold)

            matches = []
            for pt in zip(*locations[::-1]):
                matches.append((pt[0], pt[1], template.shape[1], template.shape[0]))

            return matches

        except Exception as e:
            self.logger.error(f"查找模板匹配時發生錯誤: {e}")
            return []

    def detect_character_overhead_health(self, frame, threshold=None):
        """
        使用改進的Canny邊緣模板檢測角色頭頂的血條。

        Args:
            frame (np.array): 遊戲畫面。
            threshold (float): 模板匹配的閾值，預設提高到0.5以減少誤檢。

        Returns:
            list: 一個包含所有找到的血條矩形 (x, y, w, h) 的列表。
        """
        if self.health_border_template is None:
            self.logger.warning("未載入頭頂血條邊框模板，無法進行檢測。")
            return []

        if frame is None or frame.size == 0:
            return []

        try:
            # ✅ 使用從設定檔讀取的參數
            if threshold is None:
                threshold = self.threshold
            canny_low = self.canny_low
            canny_high = self.canny_high

            # 1. 對遊戲畫面進行邊緣檢測，使用與模板相同的參數
            gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            edged_frame = cv2.Canny(gray_frame, canny_low, canny_high)  # 使用設定檔中的 Canny 參數

            # 2. 獲取模板的尺寸
            h, w = self.health_border_template.shape

            # 3. 使用模板匹配
            result = cv2.matchTemplate(edged_frame, self.health_border_template, cv2.TM_CCOEFF_NORMED)

            # 4. 找到所有高於閾值的匹配位置
            locations = np.where(result >= threshold)
            
            matches = []
            for pt in zip(*locations[::-1]):  # 交換 x 和 y
                matches.append((pt[0], pt[1], w, h))

            if not matches:
                return []

            # 5. 使用非極大值抑制（NMS）來合併重疊的矩形
            rects = np.array([[x, y, x + w, y + h] for (x, y, w, h) in matches])
            scores = np.array([result[pt[1], pt[0]] for pt in zip(*locations[::-1])])
            
            overlap_threshold = self.overlap_threshold
            final_boxes = self._non_max_suppression(rects, scores, overlapThresh=overlap_threshold)
            
            # 將結果轉回 (x, y, w, h) 格式
            final_matches = [(box[0], box[1], box[2] - box[0], box[3] - box[1]) for box in final_boxes]
            
            # ✅ 新增：根據顏色過濾匹配結果
            color_filtered_matches = self._filter_matches_by_color(frame, final_matches)

            if color_filtered_matches:
                self.logger.info(f"檢測到 {len(final_matches)} 個模板匹配, 顏色過濾後剩下 {len(color_filtered_matches)} 個 (閾值: {threshold})")
            
            return color_filtered_matches

        except Exception as e:
            self.logger.error(f"檢測頭頂血條時發生錯誤: {e}")
            return []

    def _filter_matches_by_color(self, frame, matches, color_ratio_threshold=None, min_color_pixels=None):
        """
        根據顏色（紅色或綠色）過濾檢測到的矩形。
        使用雙重驗證：顏色像素比例和絕對像素數量。
        """
        filtered_matches = []
        if not matches:
            return []

        # ✅ 使用從設定檔讀取的顏色過濾參數
        if color_ratio_threshold is None:
            color_ratio_threshold = self.color_ratio_threshold
        if min_color_pixels is None:
            min_color_pixels = self.min_color_pixels

        hsv_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

        # ✅ 使用從設定檔讀取的顏色範圍
        # 定義綠色和紅色的HSV範圍
        # 綠色 (玩家血條)
        green_lower = self.green_lower
        green_upper = self.green_upper
        # 紅色 (怪物血條) - 包含兩個範圍以環繞HSV色輪
        red_lower1 = self.red_lower1
        red_upper1 = self.red_upper1
        red_lower2 = self.red_lower2
        red_upper2 = self.red_upper2

        for (x, y, w, h) in matches:
            roi_hsv = hsv_frame[y:y+h, x:x+w]
            if roi_hsv.size == 0:
                continue

            # 創建顏色遮罩
            green_mask = cv2.inRange(roi_hsv, green_lower, green_upper)
            red_mask1 = cv2.inRange(roi_hsv, red_lower1, red_upper1)
            red_mask2 = cv2.inRange(roi_hsv, red_lower2, red_upper2)
            color_mask = cv2.bitwise_or(green_mask, cv2.bitwise_or(red_mask1, red_mask2))

            # 計算顏色像素的絕對數量和比例
            pixel_count = np.count_nonzero(color_mask)
            total_pixels = w * h
            color_ratio = pixel_count / total_pixels if total_pixels > 0 else 0

            # ✅ 雙重驗證
            if color_ratio >= color_ratio_threshold and pixel_count >= min_color_pixels:
                filtered_matches.append((x, y, w, h))
        
        return filtered_matches

    def _non_max_suppression(self, boxes, scores, overlapThresh):
        """非極大值抑制，用於合併重疊的檢測框"""
        if len(boxes) == 0:
            return []

        # 根據得分對邊界框進行排序
        if boxes.dtype.kind == "i":
            boxes = boxes.astype("float")

        pick = []
        x1 = boxes[:, 0]
        y1 = boxes[:, 1]
        x2 = boxes[:, 2]
        y2 = boxes[:, 3]

        area = (x2 - x1 + 1) * (y2 - y1 + 1)
        idxs = np.argsort(scores)

        while len(idxs) > 0:
            last = len(idxs) - 1
            i = idxs[last]
            pick.append(i)

            # 找到與當前框重疊最大的框
            xx1 = np.maximum(x1[i], x1[idxs[:last]])
            yy1 = np.maximum(y1[i], y1[idxs[:last]])
            xx2 = np.minimum(x2[i], x2[idxs[:last]])
            yy2 = np.minimum(y2[i], y2[idxs[:last]])

            w = np.maximum(0, xx2 - xx1 + 1)
            h = np.maximum(0, yy2 - yy1 + 1)

            overlap = (w * h) / area[idxs[:last]]

            # 刪除所有重疊超過閾值的框
            idxs = np.delete(idxs, np.concatenate(([last], np.where(overlap > overlapThresh)[0])))

        return boxes[pick].astype("int")

    def _find_best_match(self, frame, template, threshold):
        """
        在給定的圖像中查找最佳匹配的模板位置。

        Args:
            frame (np.array): 輸入圖像。
            template (np.array): 模板圖像。
            threshold (float): 匹配閾值。

        Returns:
            tuple: 最佳匹配位置的矩形 (x, y, w, h)。
        """
        if frame is None or frame.size == 0 or template is None or template.size == 0:
            return None

        try:
            result = cv2.matchTemplate(frame, template, cv2.TM_CCOEFF_NORMED)
            min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)

            if max_val >= threshold:
                h, w = template.shape[:2]
                return (max_loc[0], max_loc[1], w, h)
            else:
                return None

        except Exception as e:
            self.logger.error(f"查找最佳匹配時發生錯誤: {e}")
            return None

# === 備用顏色法/HSV法區塊已徹底刪除 ===
