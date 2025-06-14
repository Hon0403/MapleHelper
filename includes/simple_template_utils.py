# includes/simple_template_utils.py - 完整修正版本

from collections import deque
import cv2
import numpy as np
import os
import time
from typing import List, Dict

class MapleStoryMonsterDetector:
    """RO怪物檢測器 - 基於成功測試的平衡參數"""
    
    def __init__(self, template_dir='templates\\monsters'):
        self.template_dir = template_dir
        self.templates = []
        
        # ✅ 添加缺失的屬性
        self.single_templates = []
        self.animated_templates = {}  # 動畫模板字典
        
        # 成功的檢測參數
        self.confidence_threshold = 0.08
        self.spatial_distance_threshold = 100
        self.detection_history = deque(maxlen=3)
        # 簡化設定
        self.enable_roi_templates = False
        self.enable_background_removal = True
        self.bg_removal_method = 'gentle_enhancement'
        
        # 初始化檢測器
        self.use_sift = self._init_detector()
        self._setup_matcher()
        self._load_templates()
        self._init_animated_templates()
    
    def _init_detector(self):
        try:
            self.detector = cv2.SIFT_create(
                nfeatures=1000,
                contrastThreshold=0.04,
                edgeThreshold=10,
                sigma=1.6
            )
            self.use_sift = True   # 改回True
            print("✅ 使用SIFT檢測器")
            return True            # 改回True
        except AttributeError:
            self.detector = cv2.ORB_create(nfeatures=800)
            return False
    
    def _setup_matcher(self):
        """✅ 基於搜索結果[4][9]的FLANN性能優化"""
        if self.use_sift:
            FLANN_INDEX_KDTREE = 1
            index_params = dict(algorithm=FLANN_INDEX_KDTREE, trees=3)  # 從5降到3
            search_params = dict(checks=30)                            # 從50降到30
            self.matcher = cv2.FlannBasedMatcher(index_params, search_params)
            print("✅ 使用性能優化FLANN匹配器")
        else:
            # ORB配置保持不變
            FLANN_INDEX_LSH = 6
            index_params = dict(
                algorithm=FLANN_INDEX_LSH,
                table_number=4,     # 從6降到4
                key_size=12,
                multi_probe_level=1
            )
            search_params = dict(checks=30)  # 從50降到30
            self.matcher = cv2.FlannBasedMatcher(index_params, search_params)
    
    def _load_templates(self):
        """載入模板"""
        print("📁 載入平衡版模板...")
        
        try:
            for item in os.listdir(self.template_dir):
                item_path = os.path.join(self.template_dir, item)
                
                if os.path.isdir(item_path):
                    for filename in os.listdir(item_path):
                        if filename.lower().endswith(('.png', '.jpg', '.jpeg')):
                            if not self.enable_roi_templates and '_roi' in filename.lower():
                                continue
                            file_path = os.path.join(item_path, filename)
                            full_name = f"{item}/{filename}"
                            self._process_template(file_path, full_name)
                
                elif item.lower().endswith(('.png', '.jpg', '.jpeg')):
                    if not self.enable_roi_templates and '_roi' in item.lower():
                        continue
                    file_path = os.path.join(self.template_dir, item)
                    self._process_template(file_path, item)
            
            # ✅ 同時填充single_templates以確保相容性
            self.single_templates = self.templates.copy()
            
            original_count = sum(1 for t in self.templates if not self._is_flipped_template(t['name']))
            flipped_count = sum(1 for t in self.templates if self._is_flipped_template(t['name']))
            
            print(f"✅ 成功載入 {len(self.templates)} 個平衡模板")
            print(f"   原始模板: {original_count} 個")
            print(f"   翻轉模板: {flipped_count} 個")
            
        except Exception as e:
            print(f"❌ 載入模板失敗: {e}")
    
    def _init_animated_templates(self):
        """✅ 初始化動畫模板字典"""
        # 根據載入的模板生成動畫模板映射
        self.animated_templates = {}
        
        # 按怪物名稱分組模板
        monster_groups = {}
        for template in self.templates:
            name = template['name']
            # 提取怪物基礎名稱（去除動作和方向）
            base_name = name.split('/')[0] if '/' in name else name.split('_')[0]
            
            if base_name not in monster_groups:
                monster_groups[base_name] = []
            monster_groups[base_name].append(template)
        
        # 為每個怪物創建動畫幀列表
        for monster_name, templates in monster_groups.items():
            self.animated_templates[monster_name] = templates
        
        print(f"✅ 生成動畫模板映射: {len(self.animated_templates)} 個怪物類型")
    
    def _process_template(self, file_path, template_name):
        """✅ 處理單個模板 - 使用高級灰階轉換"""
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

        # ✅ 使用高級灰階轉換
        if len(template_bgr.shape) == 3:
            # ✅ 直接使用高級灰階轉換
            template_gray = self._advanced_grayscale_conversion(template_bgr)
        else:
            template_gray = template_bgr

        # 提取特徵
        kp, des = self.detector.detectAndCompute(template_gray, None)

        if des is not None and len(kp) >= 10:
            is_flipped = self._is_flipped_template(template_name)

            self.templates.append({
                'name': template_name,
                'original_name': template_name,
                'keypoints': kp,
                'descriptors': des,
                'image': template_gray,
                'size': template_gray.shape,
                'is_flipped': is_flipped
            })
    
    def _is_flipped_template(self, template_name):
        """判斷是否為翻轉模板"""
        flipped_indicators = ['_flipped', '_flip', '_翻轉', '_left', '_L']
        return any(indicator in template_name.lower() for indicator in flipped_indicators)
    
    def detect_monsters(self, game_frame: np.ndarray) -> List[Dict]:
        """✅ 簡化版檢測策略"""
        if game_frame is None:
            return []
        
        scene_gray = self._advanced_grayscale_conversion(game_frame)
        
        # 特徵檢測
        scene_kp, scene_des = self.detector.detectAndCompute(scene_gray, None)
        
        if scene_des is None:
            return []
        
        # 檢測流程
        all_detections = self._detect_with_filtering(scene_kp, scene_des, scene_gray)
        
        # 空間聚類
        final_detections = self._overlap_aware_clustering(all_detections)
        
        return final_detections
    
    def _overlap_aware_clustering(self, detections):
        """改進的重疊感知聚類"""
        if not detections:
            return []
        
        # ✅ 更嚴格的品質過濾
        quality_filtered = [d for d in detections if 
                        d['confidence'] >= 0.08 and          # 提高最低門檻
                        d['inlier_ratio'] >= 0.5 and         # 提高內點比例
                        d['match_count'] >= 5]               # 提高匹配要求
        
        # 按信心度排序
        quality_filtered.sort(key=lambda x: x['confidence'], reverse=True)
        
        clustered = []
        used_positions = []
        
        for detection in quality_filtered:
            pos = detection['position']
            too_close = False
            
            for used_pos in used_positions:
                distance = np.sqrt((pos[0] - used_pos[0])**2 + (pos[1] - used_pos[1])**2)
                
                if distance < 80:  # 適中的聚類距離
                    too_close = True
                    break
            
            if not too_close:
                clustered.append(detection)
                used_positions.append(pos)
        
        return clustered[:12]  # 限制最大檢測數量

    def _advanced_grayscale_conversion(self, scene_img):
        """✅ 直接返回灰階圖像，不轉回BGR"""
        try:
            if len(scene_img.shape) != 3:
                return scene_img
            
            # 標準加權平均
            weights = np.array([0.114, 0.587, 0.299])
            gray_result = np.dot(scene_img, weights)
            
            # ✅ 直接返回灰階圖，不轉回BGR
            gray_result = np.clip(gray_result, 0, 255).astype(np.uint8)
            
            return gray_result  # 直接返回灰階圖
            
        except Exception as e:
            return cv2.cvtColor(scene_img, cv2.COLOR_BGR2GRAY)
    
    def _detect_with_filtering(self, scene_kp, scene_des, scene_gray):
        """檢測並過濾"""
        all_detections = []
        
        for template in self.templates:
            detection = self._match_template(template, scene_kp, scene_des, scene_gray)
            if detection:
                all_detections.append(detection)
        
        # 按信心度排序
        all_detections.sort(key=lambda x: x['confidence'], reverse=True)
        return all_detections
    
    def _match_template(self, template, scene_kp, scene_des, scene_gray):
        """✅ 基於搜索結果[3]的遮擋感知模板匹配"""
        
        # ✅ 添加缺少的變數定義
        template_name = template['name']
        template_kp = template['keypoints']
        template_des = template['descriptors']
        is_flipped = template['is_flipped']
        
        try:
            # FLANN匹配
            if self.use_sift:
                matches = self.matcher.knnMatch(template_des, scene_des, k=2)
            else:
                template_des_float = np.float32(template_des)
                scene_des_float = np.float32(scene_des)
                matches = self.matcher.knnMatch(template_des_float, scene_des_float, k=2)
            
            # ✅ 基於搜索結果[3]的改進SIFT匹配
            # 使用更寬鬆的Lowe's ratio test
            good_matches = []
            for match_pair in matches:
                if len(match_pair) == 2:
                    m, n = match_pair
                    # ✅ 遮擋場景使用更寬鬆的比例
                    ratio_threshold = 0.75 if self.use_sift else 0.8
                    if m.distance < ratio_threshold * n.distance:
                        good_matches.append(m)
            
            # ✅ 降低最小匹配要求（適應遮擋）
            MIN_MATCH_COUNT = 3
            if len(good_matches) < MIN_MATCH_COUNT:
                return None
            
            # ✅ 基於搜索結果[1]的多重RANSAC嘗試
            best_homography = None
            best_inliers = 0
            best_mask = None
            
            # 嘗試不同的RANSAC參數
            ransac_configs = [
                (2.0, 0.99),  # 嚴格
                (3.0, 0.95),  # 標準
                (4.0, 0.90),  # 寬鬆（適合遮擋）
                (5.0, 0.85),  # 非常寬鬆
            ]
            
            src_pts = np.float32([template_kp[m.queryIdx].pt for m in good_matches]).reshape(-1, 1, 2)
            dst_pts = np.float32([scene_kp[m.trainIdx].pt for m in good_matches]).reshape(-1, 1, 2)
            
            for threshold, confidence in ransac_configs:
                try:
                    M, mask = cv2.findHomography(src_pts, dst_pts,
                                            cv2.RANSAC, threshold, confidence)
                    
                    if M is not None:
                        inliers = np.sum(mask)
                        if inliers > best_inliers:
                            best_homography = M
                            best_inliers = inliers
                            best_mask = mask
                            
                except Exception:
                    continue
            
            if best_homography is None:
                return None
            
            inlier_ratio = best_inliers / len(good_matches)
            
            # ✅ 遮擋感知的內點要求
            min_inlier_ratio = 0.3
            min_inliers = 3
            
            if inlier_ratio < min_inlier_ratio or best_inliers < min_inliers:
                return None
            
            # ✅ 計算檢測位置（使用最佳單應性矩陣）
            h, w = template['size']
            pts = np.float32([[0, 0], [0, h-1], [w-1, h-1], [w-1, 0]]).reshape(-1, 1, 2)
            dst_corners = cv2.perspectiveTransform(pts, best_homography)
            
            # ✅ 遮擋感知的檢測框驗證
            if not self._occlusion_aware_validate_box(dst_corners, scene_gray.shape):
                return None
            
            center_x = int(np.mean(dst_corners[:, 0, 0]))
            center_y = int(np.mean(dst_corners[:, 0, 1]))
            
            if not self._is_valid_position(center_x, center_y, scene_gray.shape):
                return None
            
            # ✅ 遮擋感知的信心度計算
            avg_distance = np.mean([good_matches[i].distance for i in range(len(good_matches)) if best_mask[i]])
            
            # 基於可見特徵點的比例調整信心度
            visible_ratio = best_inliers / len(template['keypoints'])  # 可見特徵點比例
            occlusion_penalty = max(0.5, visible_ratio)  # 遮擋懲罰因子
            
            base_confidence = (inlier_ratio * best_inliers * 0.1) / (avg_distance * 0.01 + 1)
            confidence = base_confidence * occlusion_penalty
            
            # 翻轉版本降低信心度
            flip_penalty = 0.95 if is_flipped else 1.0
            confidence *= flip_penalty
            
            # ✅ 遮擋場景的信心度門檻更低
            occlusion_threshold = self.confidence_threshold
            if confidence < occlusion_threshold:
                return None
            
            detection = {
                'name': template['original_name'],
                'full_name': template_name,
                'position': (center_x, center_y),
                'confidence': confidence,
                'matches': len(good_matches),
                'inliers': int(best_inliers),
                'inlier_ratio': inlier_ratio,
                'corners': dst_corners,
                'is_flipped': is_flipped,
                'direction': "翻轉" if is_flipped else "原始",
                'avg_distance': avg_distance,
                'template_name': template['original_name'],
                'match_count': len(good_matches),
                'timestamp': time.time(),
                'occlusion_aware': True,  # ✅ 標記為遮擋感知檢測
                'visible_ratio': visible_ratio
            }
            
            return detection
            
        except Exception as e:
            return None
    
    def _occlusion_aware_validate_box(self, corners, scene_shape):
        """✅ 基於搜索結果[4]的遮擋感知檢測框驗證"""
        try:
            height, width = scene_shape
            points = corners.reshape(-1, 2)
            
            # ✅ 遮擋場景的更寬鬆範圍檢查
            margin = 150  # 增加容忍度
            for point in points:
                x, y = point
                if x < -margin or x > width + margin or y < -margin or y > height + margin:
                    return False
            
            # ✅ 遮擋場景的面積檢查
            box_area = cv2.contourArea(points)
            scene_area = height * width
            
            # 允許更大的檢測框（可能包含遮擋物）
            if box_area > scene_area * 0.5 or box_area < 100:  # 更寬鬆
                return False
            
            # ✅ 遮擋場景的長寬比檢查
            rect = cv2.minAreaRect(points)
            (center, (w, h), angle) = rect
            
            if w > 0 and h > 0:
                aspect_ratio = max(w, h) / min(w, h)
                if aspect_ratio > 8.0:  # 更寬鬆的長寬比（遮擋可能造成變形）
                    return False
            
            return True
            
        except Exception as e:
            return False
    
    def _is_valid_position(self, x, y, shape):
        """位置有效性檢查"""
        height, width = shape
        return not (x < 40 or x > width - 40 or y < 40 or y > height - 40)
    
    def _safe_imread(self, image_path, flags=cv2.IMREAD_COLOR):
        """安全讀取"""
        try:
            img_array = np.fromfile(image_path, dtype=np.uint8)
            return cv2.imdecode(img_array, flags)
        except Exception:
            return None
    
    def detect_and_save_result(self, game_frame: np.ndarray) -> List[Dict]:
        """檢測並保存結果"""
        detections = self.detect_monsters(game_frame)
        
        if detections:
            result_img = self.debug_show_detections_with_boxes(game_frame, detections)
            if result_img is not None:
                timestamp = int(time.time())
                cv2.imwrite(f"detection_result_{timestamp}.png", result_img)
                print(f"🎯 檢測完成: {len(detections)} 個結果，已保存圖片")
        else:
            timestamp = int(time.time())
            cv2.imwrite(f"no_detection_{timestamp}.png", game_frame)
            print("📸 無檢測結果，已保存原始畫面")
        
        return detections
    
    def debug_show_detections_with_boxes(self, game_frame: np.ndarray, detections: List[Dict], save_image: bool = True):
        """可視化檢測結果"""
        return self.create_detection_visualization(game_frame, detections)
    
    def create_detection_visualization(self, game_frame, detections):
        """創建檢測可視化"""
        try:
            result_image = game_frame.copy()
            
            for i, detection in enumerate(detections):
                # 根據信心度選擇顏色
                confidence = detection['confidence']
                if confidence >= 0.15:
                    color = (0, 255, 0)      # 綠色：高信心度
                elif confidence >= 0.08:
                    color = (0, 255, 255)    # 黃色：中信心度
                else:
                    color = (255, 0, 255)    # 紫色：低信心度
                
                # 畫邊界框
                corners = detection['corners']
                cv2.polylines(result_image, [np.int32(corners)], True, color, 2)
                
                # 畫中心點
                center = detection['position']
                cv2.circle(result_image, center, 6, color, -1)
                
                # 標籤信息
                direction = "翻" if detection['is_flipped'] else "原"
                monster_name = detection['name'].split('/')[-1].replace('.png', '')
                label = f"{i+1}.{monster_name}({direction})"
                confidence_label = f"{confidence:.3f}"
                
                # 顯示距離（如果有）
                if 'distance' in detection:
                    distance_label = f"距離:{detection['distance']:.1f}"
                    cv2.putText(result_image, distance_label, (center[0]-20, center[1]+30),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.3, color, 1)
                
                # 主標籤
                cv2.putText(result_image, label, (center[0]-40, center[1]-20),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
                
                # 信心度標籤
                cv2.putText(result_image, confidence_label, (center[0]-15, center[1]+15),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1)
            
            return result_image
            
        except Exception as e:
            return None
    
    # ✅ 保持相容性的方法
    def get_animation_info(self):
        """保持原有介面相容性"""
        return {
            'total_templates': len(self.templates),
            'single_templates': len(self.single_templates),
            'animated_templates': len(self.animated_templates),  # ✅ 添加動畫模板計數
            'detection_method': 'balanced_sift_flann',
            'confidence_threshold': self.confidence_threshold
        }
    
    def get_monster_info(self):
        """保持原有介面相容性"""
        return {
            'loaded_monsters': len(set(t['name'].split('/')[0] for t in self.templates if '/' in t['name'])),
            'total_templates': len(self.templates),
            'single_templates': len(self.single_templates),
            'animated_templates': len(self.animated_templates),  # ✅ 添加動畫模板計數
            'detection_threshold': self.confidence_threshold,
            'detection_method': 'balanced'
        }
    
    def get_single_template_info(self):
        """獲取單一模板信息（相容性方法）"""
        return {
            'total_single_templates': len(self.single_templates),
            'template_names': [t['name'] for t in self.single_templates],
            'detection_method': 'balanced_sift_flann'
        }
    
    def save_current_frame_and_templates(self, game_frame: np.ndarray):
        """保存當前畫面和模板"""
        try:
            timestamp = int(time.time())
            cv2.imwrite(f"current_frame_{timestamp}.png", game_frame)
            print(f"📸 保存當前畫面")
        except Exception as e:
            print(f"❌ 保存失敗: {e}")

    def find_target_monster(self, game_frame, player_screen_pos):
        """✅ 怪物目標選擇邏輯"""
        try:
            # 執行怪物檢測
            detected_monsters = self.detect_monsters(game_frame)
            
            if not detected_monsters:
                return None
            
            # 按信心度選擇最佳目標
            best_target = None
            best_score = 0
            
            for monster in detected_monsters:
                # 信心度分數
                confidence_score = monster['confidence']
                
                # 綜合分數（暫時只用信心度，距離計算複雜）
                total_score = confidence_score
                
                if total_score > best_score:
                    best_score = total_score
                    best_target = monster
            
            if best_target:
                print(f"🎯 選擇目標: {best_target['name']} 分數:{best_score:.3f}")
            
            return best_target
            
        except Exception as e:
            print(f"❌ 怪物目標選擇失敗: {e}")
            return None

    def load_templates_from_folder(self, folder_path: str) -> bool:
        """從指定資料夾載入怪物模板"""
        try:
            if not os.path.exists(folder_path):
                print(f"❌ 找不到模板資料夾: {folder_path}")
                return False
            
            # 清空現有模板
            self.templates = []
            self.animated_templates = {}
            
            # 載入新模板
            template_files = [f for f in os.listdir(folder_path) 
                            if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
            
            if not template_files:
                print(f"⚠️ 資料夾中沒有找到模板圖片: {folder_path}")
                return False
            
            print(f"📁 載入模板資料夾: {folder_path}")
            print(f"🔍 找到 {len(template_files)} 個模板檔案")
            
            # 載入每個模板
            for template_file in template_files:
                template_path = os.path.join(folder_path, template_file)
                template_img = self._safe_imread(template_path)
                
                if template_img is None:
                    print(f"⚠️ 無法載入模板: {template_file}")
                    continue
                
                # 提取怪物名稱（去除副檔名）
                monster_name = os.path.splitext(template_file)[0]
                
                # 計算特徵點
                gray = cv2.cvtColor(template_img, cv2.COLOR_BGR2GRAY)
                keypoints, descriptors = self.detector.detectAndCompute(gray, None)
                
                if descriptors is None:
                    print(f"⚠️ 無法提取特徵點: {template_file}")
                    continue
                
                # 添加到模板列表
                template = {
                    'name': monster_name,
                    'original_name': monster_name,
                    'image': template_img,
                    'keypoints': keypoints,
                    'descriptors': descriptors,
                    'size': template_img.shape[:2][::-1],  # (width, height)
                    'is_flipped': False  # 添加 is_flipped 屬性
                }
                
                self.templates.append(template)
            
            # 初始化動畫模板
            self._init_animated_templates()
            
            print(f"✅ 成功載入 {len(self.templates)} 個模板")
            return True
            
        except Exception as e:
            print(f"❌ 載入模板失敗: {e}")
            return False

class UITemplateHelper:
    def __init__(self, adb, cooldown_interval=0.7):
        self.adb = adb
        self.cooldown = {}
        self.cooldown_interval = cooldown_interval

    def detect_and_click(self, frame, template_path, label, color, key, now, threshold=0.7):
        import os
        import cv2
        if key not in self.cooldown:
            self.cooldown[key] = 0
        if now - self.cooldown[key] > self.cooldown_interval:
            if frame is not None and os.path.exists(template_path):
                match = self.match_template(frame, template_path, threshold=threshold)
                if match:
                    x, y, w, h = match
                    cv2.rectangle(frame, (x, y), (x+w, y+h), color, 2)
                    cv2.putText(frame, label, (x, y-10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
                    if self.adb:
                        self.adb.click_ui(x, y, w, h)
                    self.cooldown[key] = now
                    return True
        return False

    def match_template(self, frame, template_path, threshold=0.7):
        import cv2
        import numpy as np
        template = cv2.imread(template_path, cv2.IMREAD_COLOR)
        if template is None or frame is None:
            return None
        # 轉灰階
        frame_gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY) if len(frame.shape) == 3 else frame
        template_gray = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY) if len(template.shape) == 3 else template
        res = cv2.matchTemplate(frame_gray, template_gray, cv2.TM_CCOEFF_NORMED)
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)
        if max_val >= threshold:
            h, w = template_gray.shape[:2]
            return (max_loc[0], max_loc[1], w, h)
        return None

# 創建並導出怪物檢測器實例
monster_detector = MapleStoryMonsterDetector()
print("✅ 怪物檢測器已初始化")
