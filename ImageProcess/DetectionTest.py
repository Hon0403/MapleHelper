# ImageProcess/DetectionTest.py - 平衡版本

import os
import sys
import cv2
import numpy as np
import time
import random
from collections import deque
from ImageProcess.ScreenCapture import capture_bluestacks

class BalancedDetector:
    """平衡版檢測器 - 避免過度嚴格或過度寬鬆"""
    
    def __init__(self, template_dir='templates\\monsters'):
        self.template_dir = template_dir
        self.templates = []
        
        # 保存設定
        self.save_detection_images = True
        self.save_directory = "detection_results"
        self.create_save_directory()
        
        # ✅ 基於搜索結果[1]的平衡參數
        self.confidence_threshold = 0.04        # 從0.12降到0.06
        self.spatial_distance_threshold = 80   # 適中的聚類距離
        
        # ✅ 適度的模板過濾
        self.enable_roi_templates = True        # 保持停用ROI模板
        self.enable_detection_history = True
        self.detection_history = deque(maxlen=3)
        
        # 背景處理設定
        self.enable_background_removal = True
        self.bg_removal_method = 'gentle_enhancement'
        
        # 初始化檢測器
        self.use_sift = self._init_detector()
        self._setup_matcher()
        self._load_balanced_templates()
    
    def create_save_directory(self):
        """創建保存目錄"""
        try:
            if not os.path.exists(self.save_directory):
                os.makedirs(self.save_directory)
                print(f"✅ 創建保存目錄: {self.save_directory}")
        except Exception as e:
            print(f"❌ 創建保存目錄失敗: {e}")
            self.save_directory = "."
    
    def _init_detector(self):
        """初始化特徵檢測器 - 平衡參數"""
        try:
            # ✅ 基於搜索結果[1]的適中SIFT參數
            self.detector = cv2.SIFT_create(
                nfeatures=1000,               # 適中的特徵點數量
                contrastThreshold=0.04,       # 適中的對比度門檻
                edgeThreshold=10,             # 標準邊緣門檻
                sigma=1.6                     # 標準sigma值
            )
            print("✅ 使用平衡SIFT檢測器")
            return True
        except AttributeError:
            self.detector = cv2.ORB_create(nfeatures=1000)
            print("✅ 使用ORB檢測器")
            return False
    
    def _setup_matcher(self):
        """設定FLANN匹配器"""
        if self.use_sift:
            FLANN_INDEX_KDTREE = 1
            index_params = dict(algorithm=FLANN_INDEX_KDTREE, trees=5)
            search_params = dict(checks=50)
            self.matcher = cv2.FlannBasedMatcher(index_params, search_params)
            print("✅ SIFT + FLANN KD-Tree 匹配器")
        else:
            FLANN_INDEX_LSH = 6
            index_params = dict(
                algorithm=FLANN_INDEX_LSH,
                table_number=6,
                key_size=12,
                multi_probe_level=1
            )
            search_params = dict(checks=50)
            self.matcher = cv2.FlannBasedMatcher(index_params, search_params)
            print("✅ ORB + FLANN LSH 匹配器")
    
    def _load_balanced_templates(self):
        """載入平衡版模板"""
        print("📁 載入平衡版模板...")
        
        try:
            for item in os.listdir(self.template_dir):
                item_path = os.path.join(self.template_dir, item)
                
                if os.path.isdir(item_path):
                    for filename in os.listdir(item_path):
                        if filename.lower().endswith(('.png', '.jpg', '.jpeg')):
                            # 過濾掉ROI模板
                            if not self.enable_roi_templates and '_roi' in filename.lower():
                                continue
                                
                            file_path = os.path.join(item_path, filename)
                            full_name = f"{item}/{filename}"
                            self._process_single_template(file_path, full_name)
                
                elif item.lower().endswith(('.png', '.jpg', '.jpeg')):
                    # 過濾掉ROI模板
                    if not self.enable_roi_templates and '_roi' in item.lower():
                        continue
                        
                    file_path = os.path.join(self.template_dir, item)
                    self._process_single_template(file_path, item)
            
            original_count = sum(1 for t in self.templates if not self._is_flipped_template(t['name']))
            flipped_count = sum(1 for t in self.templates if self._is_flipped_template(t['name']))
            
            print(f"✅ 成功載入 {len(self.templates)} 個平衡模板")
            print(f"   原始模板: {original_count} 個")
            print(f"   翻轉模板: {flipped_count} 個")
            print(f"   ❌ ROI模板: {'停用' if not self.enable_roi_templates else '啟用'}")
            
        except Exception as e:
            print(f"❌ 載入模板失敗: {e}")
    
    def _process_single_template(self, file_path, template_name):
        """處理單個模板 - 適中的品質要求"""
        template_img = self.safe_imread(file_path, cv2.IMREAD_UNCHANGED)
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
        
        # 轉灰度
        if len(template_bgr.shape) == 3:
            template_gray = cv2.cvtColor(template_bgr, cv2.COLOR_BGR2GRAY)
        else:
            template_gray = template_bgr
        
        # 提取特徵
        kp, des = self.detector.detectAndCompute(template_gray, None)
        
        # ✅ 適中的特徵點要求
        if des is not None and len(kp) >= 10:  # 從15降到10
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
            
            direction = "翻轉" if is_flipped else "原始"
            print(f"   ✅ {template_name}({direction}): {len(kp)} 個特徵點")
    
    def _is_flipped_template(self, template_name):
        """判斷是否為翻轉模板"""
        flipped_indicators = ['_flipped', '_flip', '_翻轉', '_left', '_L']
        return any(indicator in template_name.lower() for indicator in flipped_indicators)
    
    def detect_monsters(self):
        """主要檢測方法 - 平衡版"""
        start_time = time.time()
        # 載入場景圖
        scene_img = capture_bluestacks()
        if scene_img is None:
            print("❌ 無法載入場景圖")
            return []
        
        # 背景處理
        if self.enable_background_removal:
            print(f"🎨 開始平衡背景處理 ({self.bg_removal_method})...")
            scene_img = self._gentle_background_enhancement(scene_img)
        
        # 場景預處理
        scene_gray = cv2.cvtColor(scene_img, cv2.COLOR_BGR2GRAY)
        
        print(f"🔍 開始平衡怪物檢測...")
        print(f"場景圖尺寸: {scene_img.shape}")
        
        # 特徵檢測
        scene_kp, scene_des = self.detector.detectAndCompute(scene_gray, None)
        
        if scene_des is None:
            print("❌ 場景圖無特徵點")
            return []
        
        print(f"場景圖特徵點: {len(scene_kp)} 個")
        
        # ✅ 平衡的檢測流程
        all_detections = self._detect_with_balanced_filtering(scene_kp, scene_des, scene_gray)
        
        # ✅ 平衡的空間聚類
        final_detections = self._balanced_spatial_clustering(all_detections)
        detection_time = time.time() - start_time
        print(f"⏱️ 檢測耗時: {detection_time:.2f}秒")
        # 保存檢測結果
        if self.save_detection_images:
            prefix = "balanced_detection"
            self.save_detection_image(scene_img, final_detections, prefix)
        
        return final_detections
    
    def _gentle_background_enhancement(self, scene_img):
        """修正版背景增強"""
        try:
            if self.bg_removal_method == 'gentle_enhancement':
                # 輕微的高斯模糊減少噪聲
                blurred = cv2.GaussianBlur(scene_img, (3, 3), 0)
                
                # 修正的CLAHE
                lab = cv2.cvtColor(blurred, cv2.COLOR_BGR2LAB)
                lab_planes = list(cv2.split(lab))
                
                clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
                lab_planes[0] = clahe.apply(lab_planes[0])
                
                enhanced = cv2.merge(lab_planes)
                result = cv2.cvtColor(enhanced, cv2.COLOR_LAB2BGR)
                
                print("🎨 平衡背景增強完成")
                return result
            else:
                return scene_img
                
        except Exception as e:
            print(f"❌ 背景處理失敗: {e}")
            return scene_img
    
    def _detect_with_balanced_filtering(self, scene_kp, scene_des, scene_gray):
        """✅ 平衡過濾的檢測流程"""
        all_detections = []
        
        for template in self.templates:
            detection = self._balanced_template_matching(
                template, scene_kp, scene_des, scene_gray
            )
            
            if detection:
                all_detections.append(detection)
        
        # 按信心度排序
        all_detections.sort(key=lambda x: x['confidence'], reverse=True)
        
        print(f"🔍 平衡檢測結果: {len(all_detections)} 個")
        return all_detections
    
    def _balanced_template_matching(self, template, scene_kp, scene_des, scene_gray):
        """✅ 基於搜索結果[1]的平衡模板匹配"""
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
            
            # ✅ 基於搜索結果[1]的適中Lowe's ratio test
            good_matches = []
            for match_pair in matches:
                if len(match_pair) == 2:
                    m, n = match_pair
                    ratio_threshold = 0.7 if self.use_sift else 0.75  # 適中
                    if m.distance < ratio_threshold * n.distance:
                        good_matches.append(m)
            
            # ✅ 基於搜索結果[1]的適中匹配要求
            MIN_MATCH_COUNT = 5  # 從8降到5
            if len(good_matches) < MIN_MATCH_COUNT:
                return None
            
            # RANSAC驗證
            src_pts = np.float32([template_kp[m.queryIdx].pt for m in good_matches]).reshape(-1, 1, 2)
            dst_pts = np.float32([scene_kp[m.trainIdx].pt for m in good_matches]).reshape(-1, 1, 2)
            
            # ✅ 基於搜索結果[1]的放寬RANSAC參數
            M, mask = cv2.findHomography(src_pts, dst_pts, cv2.RANSAC, 3.0, 0.95)
            
            if M is None:
                return None
            
            inliers = np.sum(mask)
            inlier_ratio = inliers / len(good_matches)
            
            # ✅ 基於搜索結果[1]的適中內點要求
            if inlier_ratio < 0.4 or inliers < 4:  # 從0.6/6降到0.4/4
                return None
            
            # 計算檢測位置
            h, w = template['size']
            pts = np.float32([[0, 0], [0, h-1], [w-1, h-1], [w-1, 0]]).reshape(-1, 1, 2)
            dst_corners = cv2.perspectiveTransform(pts, M)
            
            # ✅ 適中的檢測框驗證
            if not self._balanced_validate_detection_box(dst_corners, scene_gray.shape):
                return None
            
            center_x = int(np.mean(dst_corners[:, 0, 0]))
            center_y = int(np.mean(dst_corners[:, 0, 1]))
            
            # 位置有效性檢查
            if not self._is_valid_position(center_x, center_y, scene_gray.shape):
                return None
            
            # ✅ 適中的信心度計算
            avg_distance = np.mean([m.distance for m in good_matches])
            base_confidence = (inlier_ratio * len(good_matches) * 0.08) / (avg_distance * 0.01 + 1)
            
            # 翻轉版本降低信心度
            flip_penalty = 0.95 if is_flipped else 1.0
            confidence = base_confidence * flip_penalty
            
            # ✅ 適中的信心度門檻
            if confidence < self.confidence_threshold:
                return None
            
            detection = {
                'name': template['original_name'],
                'full_name': template_name,
                'position': (center_x, center_y),
                'confidence': confidence,
                'matches': len(good_matches),
                'inliers': int(inliers),
                'inlier_ratio': inlier_ratio,
                'corners': dst_corners,
                'is_flipped': is_flipped,
                'direction': "翻轉" if is_flipped else "原始",
                'avg_distance': avg_distance,
                'template_name': template['original_name'],
                'match_count': len(good_matches),
                'timestamp': time.time()
            }
            
            direction = "翻轉" if is_flipped else "原始"
            print(f"   ✅ {template['original_name']}({direction}): 信心度 {confidence:.3f}")
            return detection
            
        except Exception as e:
            return None
    
    def _balanced_spatial_clustering(self, detections):
        """✅ 平衡的空間聚類"""
        if not detections:
            return []
        
        # ✅ 適中的品質過濾
        quality_filtered = [d for d in detections if 
                           d['confidence'] >= self.confidence_threshold and
                           d['inlier_ratio'] >= 0.35 and
                           d['match_count'] >= 4]
        
        # ✅ 適中的空間聚類
        clustered_detections = []
        used_positions = []
        
        for detection in quality_filtered:
            position = detection['position']
            is_near_existing = False
            
            for used_pos in used_positions:
                distance = np.sqrt((position[0] - used_pos[0])**2 + (position[1] - used_pos[1])**2)
                
                if distance < self.spatial_distance_threshold:
                    is_near_existing = True
                    break
            
            if not is_near_existing:
                clustered_detections.append(detection)
                used_positions.append(position)
        
        print(f"🔍 平衡過濾: {len(detections)} → {len(quality_filtered)} → {len(clustered_detections)} 個")
        return clustered_detections[:4]  # 最多4個結果
    
    def _balanced_validate_detection_box(self, corners, scene_shape):
        """✅ 平衡的檢測框驗證"""
        try:
            height, width = scene_shape
            points = corners.reshape(-1, 2)
            
            # ✅ 適中的範圍檢查
            margin = 100  # 適中的容忍度
            for point in points:
                x, y = point
                if x < -margin or x > width + margin or y < -margin or y > height + margin:
                    return False
            
            # ✅ 適中的面積檢查
            box_area = cv2.contourArea(points)
            scene_area = height * width
            
            # 檢測框不能太大或太小
            if box_area > scene_area * 0.3 or box_area < 200:  # 適中
                return False
            
            # ✅ 適中的長寬比檢查
            rect = cv2.minAreaRect(points)
            (center, (w, h), angle) = rect
            
            if w > 0 and h > 0:
                aspect_ratio = max(w, h) / min(w, h)
                if aspect_ratio > 5.0:  # 適中的長寬比
                    return False
            
            return True
            
        except Exception as e:
            return False
    
    def _is_valid_position(self, x, y, shape):
        """位置有效性檢查"""
        height, width = shape
        return not (x < 40 or x > width - 40 or y < 40 or y > height - 40)
    
    def save_detection_image(self, game_frame, detections, prefix="detection_result"):
        """保存檢測結果圖片"""
        try:
            timestamp = int(time.time())
            
            # 保存原始截圖
            original_filename = os.path.join(self.save_directory, f"original_{timestamp}.png")
            cv2.imwrite(original_filename, game_frame)
            print(f"📸 原始截圖已保存: {original_filename}")
            
            if not detections:
                print("⚠️ 沒有檢測結果")
                return
            
            # 生成帶檢測框的圖片
            result_image = self.create_detection_visualization(game_frame, detections)
            
            if result_image is not None:
                result_filename = os.path.join(self.save_directory, f"{prefix}_{timestamp}.png")
                cv2.imwrite(result_filename, result_image)
                print(f"🎯 檢測結果已保存: {result_filename}")
            
        except Exception as e:
            print(f"❌ 保存檢測圖片失敗: {e}")
    
    def create_detection_visualization(self, game_frame, detections):
        """創建平衡版檢測可視化"""
        try:
            result_image = game_frame.copy()
            
            for i, detection in enumerate(detections):
                # ✅ 根據信心度選擇顏色（適中標準）
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
                
                # 主標籤
                cv2.putText(result_image, label, (center[0]-40, center[1]-20),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
                
                # 信心度標籤
                cv2.putText(result_image, confidence_label, (center[0]-15, center[1]+15),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1)
            
            # 添加檢測統計信息
            stats_text = f"平衡檢測: {len(detections)} 隻 | {time.strftime('%H:%M:%S')}"
            cv2.putText(result_image, stats_text, (10, 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            
            return result_image
            
        except Exception as e:
            print(f"❌ 創建可視化圖片失敗: {e}")
            return None
    
    def safe_imread(self, image_path, flags=cv2.IMREAD_COLOR):
        """安全讀取"""
        try:
            img_array = np.fromfile(image_path, dtype=np.uint8)
            return cv2.imdecode(img_array, flags)
        except Exception:
            return None

# 執行平衡檢測
if __name__ == '__main__':
    detector = BalancedDetector()
    
    print(f"✅ 平衡檢測參數:")
    print(f"   背景處理: {'啟用' if detector.enable_background_removal else '停用'}")
    print(f"   處理方法: {detector.bg_removal_method}")
    print(f"   信心度門檻: {detector.confidence_threshold}")
    print(f"   空間聚類距離: {detector.spatial_distance_threshold}")
    print(f"   ROI模板: {'啟用' if detector.enable_roi_templates else '停用'}")
    
    while True:
        print("🔄 擷取並辨識 BlueStacks 畫面...")
        results = detector.detect_monsters()
        
        if results:
            print(f"🎉 檢測到 {len(results)} 隻怪物:")
            for i, match in enumerate(results):
                direction = "翻轉" if match['is_flipped'] else "原始"
                print(f"   [{i+1}] {match['template_name']} ({direction})")
                print(f"       位置: {match['position']}")
                print(f"       信心度: {match['confidence']:.3f}")
                print(f"       匹配點數: {match['match_count']}")
                print(f"       內點比例: {match['inlier_ratio']:.2f}")
        else:
            print("😴 無檢測結果")
        
        print("-" * 60)
        time.sleep(2)
