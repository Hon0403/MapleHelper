# simple_template_utils.py - 極簡版檢測器

import cv2
import numpy as np
import os
import time
from typing import List, Dict
from includes.log_utils import get_logger


class SimpleMonsterDetector:
    """🚀 極簡化怪物檢測器 - 純模板匹配，無額外處理"""
    
    def __init__(self, template_dir="templates/monsters", config=None):
        """初始化極簡檢測器"""
        self.template_dir = template_dir
        self.templates = []
        self.confidence_threshold = 0.6
        self.max_detections = 20
        self.scale_factor = 0.7
        self.max_processing_time = 1.0
        
        # 從設定檔載入參數
        if config:
            monster_config = config.get('monster_detection', {})
            self.confidence_threshold = monster_config.get('confidence_threshold', 0.6)
            self.max_detections = monster_config.get('max_detections_per_frame', 20)
            self.scale_factor = monster_config.get('scale_factor', 0.7)
            self.max_processing_time = monster_config.get('max_processing_time', 1.0)
        
        self.logger = get_logger("SimpleTemplateUtils")
        self.logger.info(f"設定檔參數: 閾值={self.confidence_threshold}, 最大檢測={self.max_detections}, 縮放={self.scale_factor}, 超時={self.max_processing_time}秒")
        
        self.logger.info(f"初始化極簡檢測器，模板目錄: {template_dir}")
        self._load_templates()
        self.logger.info(f"極簡檢測器就緒: {len(self.templates)} 個模板")
    
    def detect_monsters(self, game_frame: np.ndarray, frame_history=None) -> List[Dict]:
        """🚀 極簡化檢測器 - 純模板匹配，加效能優化"""
        if game_frame is None or not self.templates:
            return []
        
        try:
            start_time = time.time()
            
            # 轉灰階
            gray = cv2.cvtColor(game_frame, cv2.COLOR_BGR2GRAY) if len(game_frame.shape) == 3 else game_frame
            
            # 🚀 效能優化：縮小圖像進行快速檢測（從設定檔讀取）
            small_gray = cv2.resize(gray, None, fx=self.scale_factor, fy=self.scale_factor)
            
            results = []
            
            # 直接模板匹配 - 使用所有模板但加入早停機制
            for i, template_info in enumerate(self.templates):
                template = template_info['image']
                
                # 🚀 效能優化：同樣縮小模板（從設定檔讀取）
                small_template = cv2.resize(template, None, fx=self.scale_factor, fy=self.scale_factor)
                
                # 🚀 效能優化：超時檢查（從設定檔讀取）
                if time.time() - start_time > self.max_processing_time:
                    self.logger.warning(f"⚠️ 檢測超時，已處理 {i+1}/{len(self.templates)} 個模板")
                    break
                
                # 單一尺度匹配（使用縮小的圖像）
                result = cv2.matchTemplate(small_gray, small_template, cv2.TM_CCOEFF_NORMED)
                min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
                
                if max_val >= self.confidence_threshold:
                    # 🚀 將座標還原到原始尺寸
                    x, y = max_loc
                    h, w = small_template.shape
                    
                    # 還原到原始座標（從設定檔讀取縮放係數）
                    orig_x = int(x / self.scale_factor)
                    orig_y = int(y / self.scale_factor)
                    orig_w = int(w / self.scale_factor)
                    orig_h = int(h / self.scale_factor)
                    
                    results.append({
                        'bbox': (orig_x, orig_y, orig_w, orig_h),
                        'confidence': float(max_val),
                        'template_name': template_info['name'],
                        'name': template_info['name'],
                        'position': (orig_x + orig_w//2, orig_y + orig_h//2),
                        'x': orig_x, 'y': orig_y, 'width': orig_w, 'height': orig_h,
                        'detection_level': 'fast'
                    })
                
                # 🚀 早停機制：找到足夠的結果就停止
                if len(results) >= self.max_detections:
                    self.logger.warning(f"🎯 已找到 {len(results)} 個目標，提前停止檢測")
                    break
            
            # 簡單去重：只保留信心度最高的前5個
            if len(results) > self.max_detections:
                results.sort(key=lambda x: x['confidence'], reverse=True)
                results = results[:self.max_detections]
            
            detection_time = time.time() - start_time
            if results:
                self.logger.info(f"🎯 快速檢測到 {len(results)} 個怪物 (耗時: {detection_time:.3f}秒)")
            
            return results
            
        except Exception as e:
            self.logger.error(f"❌ 簡單檢測失敗: {e}")
            return []
    
    def _load_templates(self):
        """載入模板 - 修復版，支援UTF-8編碼"""
        try:
            if not os.path.exists(self.template_dir):
                self.logger.warning(f"⚠️ 模板目錄不存在: {self.template_dir}")
                return
            
            # 確保正確處理編碼
            for item in os.listdir(self.template_dir):
                # 確保item是正確的字符串
                if isinstance(item, bytes):
                    item = item.decode('utf-8', errors='ignore')
                    
                item_path = os.path.join(self.template_dir, item)
                
                if os.path.isdir(item_path):
                    for filename in os.listdir(item_path):
                        # 確保filename是正確的字符串
                        if isinstance(filename, bytes):
                            filename = filename.decode('utf-8', errors='ignore')
                            
                        if filename.lower().endswith(('.png', '.jpg', '.jpeg')):
                            file_path = os.path.join(item_path, filename)
                            full_name = f"{item}/{filename}"
                            self.logger.info(f"🔍 載入模板: {full_name}")  # 調試輸出
                            self._process_template(file_path, full_name)
                
                elif item.lower().endswith(('.png', '.jpg', '.jpeg')):
                    file_path = os.path.join(self.template_dir, item)
                    self.logger.info(f"🔍 載入模板: {item}")  # 調試輸出
                    self._process_template(file_path, item)
            
            self.logger.info(f"📁 已載入 {len(self.templates)} 個模板")
            
            # 調試：顯示載入的模板名稱
            for i, template in enumerate(self.templates[:5]):  # 只顯示前5個
                self.logger.info(f"  #{i+1}: {template['name']}")
            
        except Exception as e:
            self.logger.error(f"❌ 載入模板失敗: {e}")
            import traceback
            traceback.print_exc()
    
    def _process_template(self, file_path, template_name):
        """處理單個模板 - 修復版，支援UTF-8編碼"""
        try:
            template_img = self._safe_imread(file_path, cv2.IMREAD_UNCHANGED)
            if template_img is None:
                return

            # 處理透明圖
            if len(template_img.shape) == 3 and template_img.shape[2] == 4:
                alpha = template_img[:, :, 3]
                bgr = template_img[:, :, :3]
                bg = np.full(bgr.shape, 200, dtype=np.uint8)
                template_bgr = np.where(alpha[..., None] == 0, bg, bgr)
            else:
                template_bgr = template_img

            # 轉為灰階用於匹配
            if len(template_bgr.shape) == 3:
                template_gray = cv2.cvtColor(template_bgr, cv2.COLOR_BGR2GRAY)
            else:
                template_gray = template_bgr

            # 簡單存儲模板
            self.templates.append({
                'name': template_name,
                'original_name': template_name,
                'image': template_gray,
                'size': template_gray.shape
            })
        
        except Exception as e:
            self.logger.error(f"❌ 處理模板失敗 {template_name}: {e}")
    
    def _get_display_name(self, template_name):
        """獲取清晰的顯示名稱，直接顯示原檔案名"""
        try:
            if not template_name:
                return "Unknown"
            
            # 移除路徑和副檔名
            display_name = template_name
            if '/' in display_name:
                display_name = display_name.split('/')[-1]
            if '\\' in display_name:
                display_name = display_name.split('\\')[-1]
            
            # 移除副檔名
            if '.' in display_name:
                display_name = display_name.rsplit('.', 1)[0]
            
            # 直接返回處理後的檔案名，不進行硬編碼替換
            return display_name
            
        except Exception as e:
            self.logger.warning(f"⚠️ 名稱處理失敗: {e}")
            return "Unknown"
    
    def _safe_imread(self, image_path, flags=cv2.IMREAD_COLOR):
        """安全讀取圖片，支援UTF-8編碼路徑"""
        try:
            # 確保路徑是正確的字符串格式
            if isinstance(image_path, bytes):
                image_path = image_path.decode('utf-8', errors='ignore')
            
            # 使用np.fromfile來支援UTF-8路徑
            img_array = np.fromfile(image_path, dtype=np.uint8)
            if img_array.size == 0:
                self.logger.warning(f"⚠️ 檔案為空或無法讀取: {image_path}")
                return None
            
            img = cv2.imdecode(img_array, flags)
            if img is None:
                self.logger.warning(f"⚠️ OpenCV無法解碼圖片: {image_path}")
                return None
            
            return img
        except Exception as e:
            self.logger.warning(f"⚠️ 讀取圖片失敗: {image_path}, 錯誤: {e}")
            return None
            
    def load_templates_from_folder(self, folder_path: str) -> bool:
        """從指定資料夾載入怪物模板 - 修復版，支援UTF-8編碼"""
        try:
            if not os.path.exists(folder_path):
                self.logger.error(f"❌ 找不到模板資料夾: {folder_path}")
                return False
            
            # 清空現有模板
            self.templates = []
            
            # 載入新模板，確保正確處理編碼
            template_files = []
            for f in os.listdir(folder_path):
                # 確保檔案名稱是正確的字符串
                if isinstance(f, bytes):
                    f = f.decode('utf-8', errors='ignore')
                if f.lower().endswith(('.png', '.jpg', '.jpeg')):
                    template_files.append(f)
            
            if not template_files:
                self.logger.warning(f"⚠️ 資料夾中沒有找到模板圖片: {folder_path}")
                return False
            
            self.logger.info(f"📁 載入模板資料夾: {folder_path}")
            self.logger.info(f"🔍 找到 {len(template_files)} 個模板檔案")
            
            # 載入每個模板
            for template_file in template_files:
                template_path = os.path.join(folder_path, template_file)
                self.logger.info(f"🔍 載入模板: {template_file}")  # 調試輸出
                self._process_template(template_path, template_file)
            
            self.logger.info(f"✅ 成功載入 {len(self.templates)} 個模板")
            
            # 調試：顯示載入的模板名稱
            for i, template in enumerate(self.templates[:5]):  # 只顯示前5個
                self.logger.info(f"  #{i+1}: {template['name']}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"❌ 載入模板失敗: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def load_template_folder(self, folder_path: str) -> bool:
        """載入模板資料夾的別名方法（相容性）"""
        return self.load_templates_from_folder(folder_path)
    
    # === 保持相容性的方法 ===
    
    def get_animation_info(self):
        """保持原有介面相容性"""
        return {
            'total_templates': len(self.templates),
            'single_templates': len(self.templates),
            'animated_templates': len(self.templates),
            'detection_method': 'simple_template_matching',
            'confidence_threshold': self.confidence_threshold
        }
    
    def get_monster_info(self):
        """保持原有介面相容性"""
        monster_names = set()
        for t in self.templates:
            name = t['name']
            base_name = name.split('/')[0] if '/' in name else name.split('_')[0]
            monster_names.add(base_name)
        
        return {
            'loaded_monsters': len(monster_names),
            'total_templates': len(self.templates),
            'single_templates': len(self.templates),
            'animated_templates': len(self.templates),
            'detection_threshold': self.confidence_threshold,
            'detection_method': 'simple_template_matching'
        }
    
    def get_single_template_info(self):
        """獲取單一模板信息（相容性方法）"""
        return {
            'total_single_templates': len(self.templates),
            'template_names': [t['name'] for t in self.templates],
            'detection_method': 'simple_template_matching'
        }
    
    def find_target_monster(self, game_frame, player_screen_pos):
        """簡化的怪物目標選擇邏輯"""
        try:
            detected_monsters = self.detect_monsters(game_frame)
            
            if not detected_monsters:
                return None
            
            # 按信心度選擇最佳目標
            best_target = max(detected_monsters, key=lambda x: x['confidence'])
            
            if best_target:
                self.logger.info(f"🎯 選擇目標: {best_target['name']} 信心度:{best_target['confidence']:.3f}")
            
            return best_target
            
        except Exception as e:
            self.logger.error(f"❌ 怪物目標選擇失敗: {e}")
            return None
    
    def detect_and_save_result(self, game_frame: np.ndarray) -> List[Dict]:
        """檢測並保存結果"""
        detections = self.detect_monsters(game_frame)
        
        if detections:
            self.logger.info(f"🎯 檢測完成: {len(detections)} 個結果")
        else:
            self.logger.info("📸 無檢測結果")
        
        return detections
    
    def create_detection_visualization(self, game_frame, detections):
        """創建檢測可視化 - 方形框版本"""
        try:
            result_image = game_frame.copy()
            
            for i, detection in enumerate(detections):
                confidence = detection['confidence']
                
                # 根據信心度選擇顏色
                if confidence >= 0.15:
                    color = (0, 255, 0)      # 綠色：高信心度
                elif confidence >= 0.08:
                    color = (0, 255, 255)    # 黃色：中信心度
                else:
                    color = (255, 0, 255)    # 紫色：低信心度
                
                # 🟦 計算方形邊界框
                x, y, w, h = detection['bbox']
                center_x = x + w//2
                center_y = y + h//2
                
                # 取較大的邊長作為方形尺寸，並稍微放大一點
                square_size = max(w, h) + 10  # 增加10像素的邊距
                half_size = square_size // 2
                
                # 計算方形的左上角座標
                square_x = center_x - half_size
                square_y = center_y - half_size
                
                # 確保方形框不超出畫面邊界
                frame_h, frame_w = result_image.shape[:2]
                square_x = max(0, min(square_x, frame_w - square_size))
                square_y = max(0, min(square_y, frame_h - square_size))
                
                # 畫方形邊界框
                cv2.rectangle(result_image, (square_x, square_y), 
                            (square_x + square_size, square_y + square_size), color, 2)
                
                # 計算中心點
                center = (center_x, center_y)
                cv2.circle(result_image, center, 6, color, -1)
                
                # 標籤信息
                template_name = detection.get('template_name', 'Unknown')
                monster_name = self._get_display_name(template_name)
                label = f"{i+1}.{monster_name}"
                confidence_label = f"{confidence:.3f}"
                
                # 主標籤
                cv2.putText(result_image, label, (center[0]-40, center[1]-20),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
                
                # 信心度標籤
                cv2.putText(result_image, confidence_label, (center[0]-15, center[1]+15),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1)
            
            return result_image
            
        except Exception as e:
            self.logger.error(f"❌ 可視化失敗: {e}")
            return None
    

# === 全域函數保持相容性 ===

# 創建單一實例
_monster_detector_instance = None

def get_monster_detector(config=None):
    """獲取怪物檢測器實例"""
    try:
        detector_logger = get_logger("MonsterDetector")
        detector_logger.info("創建極簡怪物檢測器...")
        detector = SimpleMonsterDetector(config=config)
        
        # 獲取初始化資訊
        info = detector.get_monster_info()
        detector_logger.info(f"極簡檢測器已初始化：{info['loaded_monsters']} 種怪物，{info['total_templates']} 個模板，閾值：{info['detection_threshold']}")
        
        return detector
    except Exception as e:
        detector_logger = get_logger("MonsterDetector")
        detector_logger.error(f"創建怪物檢測器失敗: {e}")
        return None

def init_monster_detector(config=None):
    """初始化怪物檢測器"""
    return get_monster_detector(config)


# === UI模板輔助類別（保持相容性）===

class UITemplateHelper:
    """UI模板輔助工具 - 楓之谷 Worlds 原生遊戲"""
    
    def __init__(self, adb=None, cooldown_interval=0.7):
        # ADB 控制器已移除 - 楓之谷 Worlds 原生遊戲
        self.cooldown_interval = cooldown_interval
        self.last_click_time = 0
        self.logger = get_logger("UITemplateHelper")
    
    def detect_and_click(self, frame, template_path, label, color, key, now, threshold=0.7):
        """檢測並模擬點擊 - 楓之谷 Worlds 原生遊戲"""
        try:
            # 檢查冷卻時間
            if now - self.last_click_time < self.cooldown_interval:
                return False
            
            # 模板匹配
            result = self.match_template(frame, template_path, threshold)
            if result:
                x, y, confidence = result
                
                self.logger.info(f"模擬點擊 {label}: ({x}, {y}) 信心度: {confidence:.3f} - 楓之谷 Worlds")
                
                # 楓之谷 Worlds 原生遊戲 - 模擬點擊
                success = True  # 模擬成功
                
                if success:
                    self.last_click_time = now
                    return True
                    
            return False
            
        except Exception as e:
            self.logger.error(f"{label} 檢測點擊失敗: {e}")
            return False
    
    def match_template(self, frame, template_path, threshold=0.7):
        """模板匹配"""
        try:
            template = cv2.imread(template_path, cv2.IMREAD_COLOR)
            if template is None:
                return None
            
            result = cv2.matchTemplate(frame, template, cv2.TM_CCOEFF_NORMED)
            min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
            
            if max_val >= threshold:
                h, w = template.shape[:2]
                center_x = max_loc[0] + w // 2
                center_y = max_loc[1] + h // 2
                return (center_x, center_y, max_val)
            
            return None
            
        except Exception as e:
            self.logger.error(f"模板匹配失敗: {e}")
            return None 