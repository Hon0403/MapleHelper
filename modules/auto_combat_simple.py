# modules/auto_combat_simple.py - 基於搜索結果[5]的AI移動整理版

import time
import random
import numpy as np
from includes.simple_template_utils import get_monster_detector
from includes.movement_utils import MovementUtils
from includes.grid_utils import GridUtils
from includes.log_utils import get_logger


class SimpleCombat:
    """基於搜索結果[5]的AI Bot移動系統"""
    
    def __init__(self, config=None, monster_detector=None):
        """初始化戰鬥系統 - 支援共用檢測器"""
        # 載入設定
        self.config = config or {}
        
        # 戰鬥狀態
        self.is_enabled = False
        self.auto_hunt_mode = False
        self.current_action = None
        self.action_start_time = 0
        self.action_duration = 0
        self.last_attack_time = 0
        
        # 怪物檢測器 - 優先使用傳入的實例
        self.monster_detector = monster_detector
        if not self.monster_detector:
            try:
                from includes.simple_template_utils import get_monster_detector
                self.monster_detector = get_monster_detector(config)
                if not self.monster_detector:
                    # 兼容舊版本：再次嘗試獲取檢測器
                    try:
                        self.monster_detector = get_monster_detector(self.config)
                    except:
                        self.monster_detector = None
            except Exception as e:
                self.logger = get_logger("SimpleCombat")
                self.logger.error(f"怪物檢測器初始化失敗: {e}")
        
        # 初始化日誌
        self.logger = get_logger("SimpleCombat")
        
        # 血條追蹤設定
        # ✅ 分離的血條檢測器
        self.hud_health_detector = None  # HUD血條檢測器
        self.character_health_detector = None  # 角色血條檢測器
        self.use_health_bar_tracking = config.get('use_health_bar_tracking', True)
        self.health_detection_interval = config.get('health_detection_interval', 0.1)
        self.last_health_detection_time = 0
        self.character_health_bar_pos = None
        
        # 向後兼容性
        self.health_detector = None
        self.last_health_detection_time = 0
        self.health_detection_interval = config.get('combat', {}).get('health_detection_interval', 0.1)
        
        # 從設定檔載入戰鬥參數
        combat_config = config.get('combat', {})
        self.hunt_settings = {
            'attack_range': combat_config.get('attack_range', 0.4),
            'approach_distance': combat_config.get('approach_distance', 0.1),
            'retreat_distance': combat_config.get('retreat_distance', 0.05),
            'attack_cooldown': combat_config.get('attack_cooldown', 1.5),
            'movement_speed': combat_config.get('movement_speed', 0.8),
            'max_chase_distance': combat_config.get('max_chase_distance', 0.15),
            'movement_interval': combat_config.get('movement_interval', 0.5),
            'action_timeout': combat_config.get('action_timeout', 2.0),
            'move_duration_min': combat_config.get('move_duration_min', 0.2),
            'move_duration_max': combat_config.get('move_duration_max', 0.5),
            'emergency_move_duration': combat_config.get('emergency_move_duration', 0.3),
            'forbidden_threshold': combat_config.get('forbidden_threshold', 0.02),
            'same_position_tolerance': combat_config.get('same_position_tolerance', 0.005)
        }
        
        # 控制器和路徑點系統
        self.controller = None
        self.waypoint_system = None

    def _initialize_controller(self):
        """控制器初始化已移除 - 專注楓之谷 Worlds 原生遊戲"""
        try:
            # ADB 控制器已移除，楓之谷 Worlds 使用原生 PC 控制
            self.controller = None
            self.logger.info("楓之谷 Worlds 原生遊戲 - 無需 ADB 控制器")
                
        except Exception as e:
            self.logger.error(f"控制器初始化處理失敗: {e}")

    def set_waypoint_system(self, waypoint_system):
        """設置路徑點系統"""
        try:
            self.waypoint_system = waypoint_system
            
        except Exception as e:
            self.logger.error(f"設置路徑點系統失敗: {e}")

    def set_health_detector(self, health_detector):
        """設置血條檢測器，用於角色定位（向後兼容）"""
        try:
            self.health_detector = health_detector
            # 向後兼容：將統一檢測器同時設置為角色血條檢測器
            if hasattr(health_detector, 'detect_character_overhead_health'):
                self.character_health_detector = health_detector
            
        except Exception as e:
            self.logger.error(f"設置血條檢測器失敗: {e}")
    
    def set_hud_health_detector(self, hud_health_detector):
        """設置HUD血條檢測器"""
        try:
            self.hud_health_detector = hud_health_detector
            self.logger.info("✅ HUD血條檢測器已設置")
            
        except Exception as e:
            self.logger.error(f"設置HUD血條檢測器失敗: {e}")
    
    def set_character_health_detector(self, character_health_detector):
        """設置角色血條檢測器，用於角色定位"""
        try:
            self.character_health_detector = character_health_detector
            # 向後兼容
            if not self.health_detector:
                self.health_detector = character_health_detector
            self.logger.info("✅ 角色血條檢測器已設置")
            
        except Exception as e:
            self.logger.error(f"設置角色血條檢測器失敗: {e}")

    def get_character_position_from_health_bar(self, frame):
        """✅ 使用血條檢測獲取角色位置"""
        if not self.use_health_bar_tracking or not self.health_detector or frame is None:
            return None
            
        try:
            current_time = time.time()
            
            # 限制檢測頻率以提升效能
            if current_time - self.last_health_detection_time < self.health_detection_interval:
                return self.character_health_bar_pos
            
            # 🔧 修復重複檢測：優先使用共享的角色血條檢測結果
            health_bars = []
            
            # 嘗試從GUI的共享結果獲取角色血條（如果可用）
            if hasattr(self, '_get_shared_health_detection'):
                try:
                    health_bars = self._get_shared_health_detection()
                except:
                    pass
            
            # 如果沒有共享結果，才執行檢測（備用方案）
            if not health_bars:
                health_bars = self.health_detector.detect(frame)
                self.logger.debug(f"戰鬥系統檢測: {len(health_bars)} 隻血條 (備用檢測)")
            else:
                self.logger.debug(f"使用共享檢測結果: {len(health_bars)} 隻血條")
            
            if health_bars:
                # 假設第一個檢測到的血條是角色的血條
                # 在實際應用中，可能需要更智能的篩選邏輯
                health_bar = health_bars[0]
                if len(health_bar) == 5:
                    # 新格式: (x, y, w, h, template_name)
                    x, y, w, h, _ = health_bar
                else:
                    # 舊格式: (x, y, w, h)
                    x, y, w, h = health_bar
                
                # 將血條中心點轉換為相對座標
                frame_height, frame_width = frame.shape[:2]
                center_x = (x + w/2) / frame_width
                center_y = (y + h/2) / frame_height
                
                # 角色通常在血條正下方，稍微調整Y座標
                character_y = center_y + (h * 1.5 / frame_height)  # 血條下方1.5倍血條高度處
                
                self.character_health_bar_pos = (center_x, character_y)
                self.last_health_detection_time = current_time
                

                return self.character_health_bar_pos
            
            # 如果沒有檢測到血條，保持上次的位置
            return self.character_health_bar_pos
            
        except Exception as e:
            self.logger.error(f"血條位置檢測失敗: {e}")
            return None

    def calculate_distance_to_monsters(self, frame, character_pos=None, frame_history=None):
        """✅ 計算角色與怪物的距離 - 使用共享檢測結果避免重複處理"""
        if frame is None:
            return []
            
        try:
            # 如果沒有提供角色位置，嘗試從血條檢測獲取
            if character_pos is None:
                character_pos = self.get_character_position_from_health_bar(frame)
            
            if character_pos is None:
                return []
            
            # ✅ 優先使用GUI檢測循環的共享結果
            monsters = []
            if hasattr(self, '_get_shared_monster_detection'):
                # 嘗試從主應用獲取共享檢測結果
                shared_results = self._get_shared_monster_detection()
                if shared_results and len(shared_results) > 0:
                    monsters = shared_results
                    self.logger.debug(f"使用共享檢測結果: {len(monsters)} 隻怪物")
            
            # ✅ 如果沒有共享結果，才執行檢測（降低頻率）
            if not monsters and self.monster_detector:
                if not hasattr(self, '_last_detection_time'):
                    self._last_detection_time = 0
                
                current_time = time.time()
                # 戰鬥系統檢測頻率降低到5FPS（0.2秒間隔）
                if current_time - self._last_detection_time >= 0.2:
                    if hasattr(self.monster_detector, 'detect_monsters'):
                        if frame_history and len(frame_history) > 0:
                            monsters = self.monster_detector.detect_monsters(frame, frame_history=frame_history)
                        else:
                            monsters = self.monster_detector.detect_monsters(frame)
                    else:
                        monsters = self.monster_detector.detect_monsters(frame)
                    
                    self._last_detection_time = current_time
                    self.logger.debug(f"戰鬥系統檢測: {len(monsters)} 隻怪物 (備用檢測)")
                else:
                    # 使用上次檢測結果
                    monsters = getattr(self, '_last_monsters', [])
            
            if not monsters:
                return []
            
            # 緩存檢測結果
            self._last_monsters = monsters
            
            # 計算每個怪物與角色的距離
            monster_distances = []
            frame_height, frame_width = frame.shape[:2]
            
            for monster in monsters:
                # 獲取怪物中心點
                if isinstance(monster, dict):
                    monster_x = monster.get('center_x', monster.get('x', 0))
                    monster_y = monster.get('center_y', monster.get('y', 0))
                    
                    # 如果使用position屬性
                    if 'position' in monster:
                        monster_x, monster_y = monster['position']
                        
                    confidence = monster.get('confidence', 0.0)
                    detection_method = monster.get('detection_method', 'shared_result')
                    
                elif isinstance(monster, (list, tuple)) and len(monster) >= 4:
                    x, y, w, h = monster[:4]
                    monster_x = x + w/2
                    monster_y = y + h/2
                    confidence = monster[4] if len(monster) > 4 else 0.0
                    detection_method = 'legacy'
                else:
                    continue
                
                # 轉換為相對座標
                monster_rel_x = monster_x / frame_width
                monster_rel_y = monster_y / frame_height
                
                # 計算歐式距離
                distance = self._calculate_distance(character_pos, (monster_rel_x, monster_rel_y))
                
                monster_distances.append({
                    'monster': monster,
                    'position': (monster_rel_x, monster_rel_y),
                    'distance': distance,
                    'confidence': confidence,
                    'detection_method': detection_method
                })
            
            # 按距離排序，最近的在前面
            monster_distances.sort(key=lambda x: x['distance'])
            
            return monster_distances
            
        except Exception as e:
            self.logger.error(f"計算怪物距離失敗: {e}")
            return []

    def start(self):
        """啟動戰鬥系統"""
        try:
            # 初始化控制器
            self._initialize_controller()
            
            # 檢查必要組件
            if not self.waypoint_system:
                self.logger.error("路徑點系統未設置")
                return False
            
            # 確定戰鬥模式
            combat_mode = self.hunt_settings.get('combat_mode', 'safe_area')
            
            if combat_mode == 'safe_area':
                walkable_areas = getattr(self.waypoint_system, 'area_grid', {})
                walkable_areas = {k: v for k, v in walkable_areas.items() if v == 'walkable'}
                
                if not walkable_areas:
                    self.logger.error("安全區域模式需要區域標記")
                    return False
                    
            elif combat_mode == 'waypoint':
                if not self.waypoint_system.waypoints:
                    self.logger.error("路徑點模式需要路徑點")
                    return False
                    
            # 楓之谷 Worlds 原生遊戲 - 無需 ADB 控制器檢查
            self.logger.info("楓之谷 Worlds 原生遊戲模式 - 跳過控制器檢查")
            
            # 啟動戰鬥系統
            self.is_enabled = True
            self.auto_hunt_mode = True
            self.last_attack_time = 0
            self.current_action = None
            self.action_start_time = 0
            self.action_duration = 0
            
            return True
            
        except Exception as e:
            self.logger.error(f"啟動戰鬥系統失敗: {e}")
            return False

    def stop(self):
        """停止戰鬥系統"""
        try:
            self.is_enabled = False
            self.auto_hunt_mode = False
            
        except Exception as e:
            self.logger.error(f"停止戰鬥系統失敗: {e}")

    def update(self, rel_pos, frame, frame_history=None):
        """✅ 整合血條檢測的戰鬥系統更新邏輯 - 支援歷史幀"""
        try:
            # ✅ 定期清理可能卡住的動作狀態
            if self._is_action_in_progress():
                current_time = time.time()
                if (current_time - self.action_start_time) > (self.action_duration + 2.0):
                    self._end_action()

            # 1. 基本狀態檢查
            if not self.is_enabled:
                return
            
            # ✅ 優先使用血條檢測獲取角色位置
            character_pos = None
            if self.use_health_bar_tracking and frame is not None:
                character_pos = self.get_character_position_from_health_bar(frame)
            
            # 如果血條檢測失敗，使用傳統方法
            if character_pos is None:
                character_pos = rel_pos
            
            if not character_pos:
                return

            # ✅ 關鍵修正：檢查是否有動作正在執行
            if self._is_action_in_progress():
                return  # 有動作執行中，跳過本次更新

            # ✅ 使用血條檢測計算與怪物的距離 - 支援歷史幀
            monster_distances = []
            if frame is not None:
                monster_distances = self.calculate_distance_to_monsters(frame, character_pos, frame_history)

            # 3. 根據戰鬥模式選擇不同的處理邏輯
            combat_mode = self.hunt_settings.get('combat_mode', 'waypoint')
            
            if combat_mode == 'safe_area':
                # 安全區域模式
                if self._is_near_forbidden(character_pos):
                    return self._execute_safe_return_movement(character_pos)

                if not self._is_in_safe_area(character_pos):
                    return self._execute_safe_return_movement(character_pos)

                # ✅ 使用距離資訊更新目標
                has_target = self._update_monster_targeting_with_distance(monster_distances, character_pos)

                # 安全區域內的戰鬥邏輯
                if has_target and self.auto_hunt_mode != "off":
                    current_time = time.time()
                    attack_interval = self.hunt_settings.get('attack_cooldown', 1.5)
                    
                    # ✅ 檢查是否需要接近怪物
                    if self.auto_hunt_target and self.auto_hunt_target.get('needs_approach', False):
                        if self._approach_monster(character_pos):
                            return  # 接近移動後結束本次更新
                    
                    # 在攻擊範圍內，可以攻擊
                    if current_time - self.last_attack_time >= attack_interval:
                        if self._execute_combat_sequence_with_state():
                            self.last_attack_time = current_time
                        return  # 攻擊後結束本次更新

                # 沒有目標或攻擊冷卻中，執行移動
                if self.auto_hunt_mode != "off":
                    self._execute_patrol_movement(character_pos)

            else:
                # 路徑點模式
                has_target = self._update_monster_targeting_with_distance(monster_distances, character_pos)
                
                if self.auto_hunt_mode != "off":
                    current_time = time.time()
                    hunt_attack_interval = self.hunt_settings.get('attack_cooldown', 0.5)
                    if current_time - self.last_attack_time >= hunt_attack_interval:
                        if has_target:
                            if self._execute_combat_sequence_with_state():
                                self.last_attack_time = current_time
                            return
                    # 沒有目標或攻擊冷卻中，執行移動
                    self._execute_patrol_movement(character_pos)

        except Exception as e:
            self.logger.error(f"戰鬥系統更新失敗: {e}")

    def _handle_waypoint_movement(self, current_pos):
        """修正版：根據戰鬥模式選擇移動邏輯"""
        try:
            combat_mode = self.hunt_settings.get('combat_mode', 'waypoint')
            
            if combat_mode == 'safe_area':
                # ✅ 1. 強制檢查是否在禁止區域
                if self._is_near_forbidden(current_pos):
                    return self._emergency_return_to_safe_area(current_pos)
                
                # ✅ 2. 檢查是否在安全區域內
                if not self._is_in_safe_area(current_pos):
                    return self._return_to_safe_area(current_pos)
                
                # ✅ 3. 如果有怪物目標，在安全區域內追擊
                if hasattr(self, 'auto_hunt_target') and self.auto_hunt_target:
                    return self._safe_area_chase_target(current_pos)
                
                # ✅ 4. 沒有目標時，在安全區域內巡邏
                return self._safe_area_patrol(current_pos)
                
            else:
                # 路徑點模式
                # 檢查 current_pos 是否接近 forbidden
                forbidden_pos = self._is_near_forbidden(current_pos, return_pos=True)
                if forbidden_pos and self._is_same_position(current_pos, forbidden_pos):
                    return False
                
                # 獲取下一個路徑點
                next_waypoint = self.waypoint_system.get_next_waypoint(current_pos)
                if not next_waypoint:
                    self.last_planned_path = None
                    return
                
                # 使用 A* 算法尋找路徑
                path = self.grid_utils.find_path(current_pos, next_waypoint['pos'])
                self.last_planned_path = path
                if not path:
                    return
                
                # 獲取下一個路徑點
                next_pos = path[1] if len(path) > 1 else next_waypoint['pos']
                
                direction = self._get_direction_to_target(current_pos, next_pos)
                if direction:
                    return self._move_in_direction(direction)
            
        except Exception as e:
            self.logger.error(f"移動處理失敗: {e}")
            return False

    def _return_to_safe_area(self, current_pos):
        """回歸安全區域"""
        try:
            # 尋找最近的安全位置
            nearest_safe = self._find_nearest_safe_position(current_pos)
            
            if nearest_safe:
                direction = self._get_direction_to_target(current_pos, nearest_safe)
                if direction:
                    return self._move_in_direction(direction, duration=0.5)
            
            # 如果找不到安全位置，使用預設方向
            return self._move_in_direction("left", duration=0.3)
            
        except Exception as e:
            self.logger.error(f"回歸安全區域失敗: {e}")
            return False

    def _find_nearest_safe_position(self, current_pos):
        """尋找最近的安全位置"""
        try:
            safe_positions = []
            
            # 收集所有安全區域位置
            for key, area_type in self.waypoint_system.area_grid.items():
                if area_type == "walkable":
                    try:
                        if isinstance(key, str) and ',' in key:
                            x_str, y_str = key.split(',')
                            safe_x, safe_y = float(x_str), float(y_str)
                        elif isinstance(key, tuple):
                            safe_x, safe_y = key
                        else:
                            continue
                        
                        safe_positions.append((safe_x, safe_y))
                    except:
                        continue
            
            if not safe_positions:
                return None
            
            # 尋找最近的安全位置
            return min(safe_positions, 
                      key=lambda p: self._calculate_distance(current_pos, p))
            
        except Exception as e:
            self.logger.error(f"尋找最近安全位置失敗: {e}")
            return None

    def _is_near_forbidden(self, pos, threshold=0.02, return_pos=False):
        """判斷座標是否接近 forbidden 區域，return_pos=True 則回傳 forbidden 座標"""
        if not hasattr(self.waypoint_system, 'area_grid'):
            return False
        for key, area_type in self.waypoint_system.area_grid.items():
            if area_type == "forbidden":
                if isinstance(key, str) and ',' in key:
                    x_str, y_str = key.split(',')
                    fx, fy = float(x_str), float(y_str)
                elif isinstance(key, tuple):
                    fx, fy = key
                else:
                    continue
                if abs(pos[0] - fx) < threshold and abs(pos[1] - fy) < threshold:
                    return (fx, fy) if return_pos else True
        return False

    def _is_same_position(self, pos1, pos2, tol=0.005):
        """判斷兩個座標是否幾乎相同（允許微小誤差）"""
        return abs(pos1[0] - pos2[0]) < tol and abs(pos1[1] - pos2[1]) < tol

    def _execute_combat_sequence_with_state(self):
        """帶狀態管理的戰鬥序列 - 楓之谷 Worlds 模擬版本"""
        try:
            if not self.auto_hunt_target:
                return False
            # ✅ 開始攻擊動作（預估1.2秒包含執行時間）
            self._start_action("attack", 1.2)
            # 楓之谷 Worlds 原生遊戲 - 模擬攻擊動作
            self.logger.info("🗡️ 模擬攻擊動作（楓之谷 Worlds 原生遊戲）")
            # 這裡可以添加鍵盤模擬（如 pyautogui.press('ctrl')）
            return True
        except Exception as e:
            self.logger.error(f"戰鬥序列錯誤: {e}")
            self._end_action()  # 異常時結束動作狀態
            return False

    def _execute_patrol_movement(self, current_pos):
        """執行巡邏移動 - 楓之谷 Worlds 模擬版本"""
        try:
            target_pos = self._find_next_patrol_target(current_pos)
            if not target_pos:
                return False
            direction = self._get_direction_to_target(current_pos, target_pos)
            if not direction:
                return False
            distance = self._calculate_distance(current_pos, target_pos)
            move_duration = min(0.5, max(0.2, distance * 2))  # 0.2-0.5秒範圍
            self._start_action("move", move_duration + 0.1)  # 加0.1秒緩衝
            # 楓之谷 Worlds 原生遊戲 - 模擬移動動作
            self.logger.info(f"🚶 模擬移動動作: {direction} ({move_duration:.2f}秒) - 楓之谷 Worlds")
            # 這裡可以添加鍵盤模擬（如 pyautogui.press('left')）
            return True
        except Exception as e:
            self.logger.error(f"移動執行失敗: {e}")
            self._end_action()
            return False

    def _execute_safe_return_movement(self, current_pos):
        """安全回歸移動 - 楓之谷 Worlds 模擬版本"""
        try:
            safe_pos = self._find_nearest_safe_position(current_pos)
            if not safe_pos:
                return False
            direction = self._get_direction_to_target(current_pos, safe_pos)
            if not direction:
                return False
            move_duration = 0.3
            self._start_action("emergency_move", move_duration + 0.1)
            # 楓之谷 Worlds 原生遊戲 - 模擬緊急回歸移動
            self.logger.info(f"🚨 模擬緊急回歸移動: {direction} ({move_duration:.2f}秒) - 楓之谷 Worlds")
            # 這裡可以添加鍵盤模擬（如 pyautogui.press('left')）
            return True
        except Exception as e:
            self.logger.error(f"緊急回歸失敗: {e}")
            self._end_action()
            return False

    # ✅ 動作狀態管理方法
    def _is_action_in_progress(self):
        """檢查是否有動作正在執行"""
        if self.current_action is None:
            return False
        current_time = time.time()
        return (current_time - self.action_start_time) < self.action_duration

    def _start_action(self, action_type, duration):
        """開始執行動作"""
        self.current_action = action_type
        self.action_start_time = time.time()
        self.action_duration = duration
        pass

    def _end_action(self):
        """結束動作"""
        if self.current_action:
            pass
        self.current_action = None
        self.action_start_time = 0
        self.action_duration = 0

    def _get_direction_to_target(self, current_pos, target_pos):
        """計算移動方向（只在必要時進行垂直移動）"""
        dx = target_pos[0] - current_pos[0]
        dy = target_pos[1] - current_pos[1]
        
        # 只在 y 軸差異大於 5% 時才進行垂直移動
        if abs(dy) > 0.05:  # 提高閾值到 5%
            return 'down' if dy > 0 else 'up'
        
        # 否則只進行水平移動
        return 'right' if dx > 0 else 'left'

    def _update_monster_targeting_with_distance(self, monster_distances, current_pos):
        """使用距離資訊更新怪物目標"""
        try:
            if not monster_distances:
                self.auto_hunt_target = None
                return False
            
            # 設定檢測範圍
            attack_range = self.hunt_settings.get('attack_range', 0.4)
            approach_range = self.hunt_settings.get('approach_distance', 0.1) + attack_range
            detection_range = self.hunt_settings.get('max_chase_distance', 0.15)
            
            # 獲取最近的怪物
            closest_monster = monster_distances[0]
            closest_distance = closest_monster['distance']
            
            if closest_distance <= attack_range:
                # 在攻擊範圍內
                monster_info = closest_monster.copy()
                monster_info['needs_approach'] = False
                monster_info['in_range'] = True
                self.auto_hunt_target = monster_info
                return True
                
            elif closest_distance <= approach_range:
                # 需要接近攻擊
                monster_info = closest_monster.copy()
                monster_info['needs_approach'] = True
                monster_info['in_range'] = False
                self.auto_hunt_target = monster_info
                return True
                
            elif closest_distance <= detection_range:
                # 在檢測範圍內，需要大幅接近
                monster_info = closest_monster.copy()
                monster_info['needs_approach'] = True
                monster_info['in_range'] = False
                self.auto_hunt_target = monster_info
                return True
            
            # 超出檢測範圍
            self.auto_hunt_target = None
            return False
            
        except Exception as e:
            self.logger.error(f"更新怪物目標失敗: {e}")
            return False

    def _update_monster_targeting(self, frame, current_pos):
        """修正版：支援安全區域模式的怪物檢測"""
        try:
            if not frame is not None:
                return False
            
            # 檢測怪物
            monsters = self.monster_detector.detect_monsters(frame)
            if not monsters:
                self.auto_hunt_target = None
                return False
            
            # 過濾在安全區域外的怪物
            safe_monsters = []
            for monster in monsters:
                monster_pos = monster.get('position', (0, 0))
                rel_pos = self._screen_to_relative(monster_pos, frame.shape)
                
                # 檢查怪物是否在安全區域內
                if self._is_in_safe_area(rel_pos):
                    safe_monsters.append(monster)
            
            if not safe_monsters:
                self.auto_hunt_target = None
                return False
            
            # 選擇最近的怪物
            nearest_monster = min(safe_monsters, 
                                key=lambda m: self._calculate_distance(
                                    current_pos, 
                                    self._screen_to_relative(m['position'], frame.shape)
                                ))
            
            self.auto_hunt_target = nearest_monster
            pass
            return True
            
        except Exception as e:
            pass
            return False

    def _update_monster_targeting_in_safe_area(self, frame, current_pos):
        """安全區域內的怪物檢測 - 修正版"""
        try:
            if not frame is not None:
                return False

            # 檢測怪物
            monsters = self.monster_detector.detect_monsters(frame)
            if not monsters:
                self.auto_hunt_target = None
                return False

            # ✅ 修正：降低信心度閾值並改進目標選擇
            valid_monsters = []
            for monster in monsters:
                # 降低最低信心度要求
                if monster.get('confidence', 0) >= 0.05:  # 降低閾值到 5%
                    valid_monsters.append(monster)

            if not valid_monsters:
                self.auto_hunt_target = None
                return False

            # 選擇最近的怪物而不是信心度最高的
            nearest_monster = min(valid_monsters, 
                                key=lambda m: self._calculate_distance(
                                    current_pos, 
                                    self._screen_to_relative(m['position'], frame.shape)
                                ))
            
            self.auto_hunt_target = nearest_monster
            pass
            return True

        except Exception as e:
            pass
            return False

    def _find_next_target(self, current_pos):
        """✅ 修正版：完整的巡邏目標尋找"""
        try:
            pass
            
            # 檢查是否有area_grid
            if not hasattr(self.waypoint_system, 'area_grid') or not self.waypoint_system.area_grid:
                pass
                return self._simple_patrol_target(current_pos)
            
            # ✅ 使用MovementUtils但添加巡邏邏輯
            area_target = MovementUtils.find_safe_target_in_walkable_area(
                current_pos, self.waypoint_system.area_grid, max_distance=0.05
            )
            
            if area_target:
                pass
                return area_target
            else:
                pass
                return self._simple_patrol_target(current_pos)
                
        except Exception as e:
            pass
            return self._simple_patrol_target(current_pos)

    def _get_movement_with_area_awareness(self, current_pos, target_pos):
        """✅ 修正版：區域感知移動"""
        try:
            pass
            
            # 檢查是否有區域數據
            if not hasattr(self.waypoint_system, 'area_grid') or not self.waypoint_system.area_grid:
                pass
                return self._simple_direction_calculation(current_pos, target_pos)
            
            # ✅ 使用MovementUtils
            direction = MovementUtils.compute_area_aware_movement(
                current_pos, target_pos, self.waypoint_system.area_grid
            )
            
            if direction:
                pass
                return direction
            else:
                pass
                return self._simple_direction_calculation(current_pos, target_pos)
                
        except Exception as e:
            pass
            return self._simple_direction_calculation(current_pos, target_pos)

    def _get_area_type(self, position):
        """✅ 使用MovementUtils"""
        return MovementUtils.get_area_type_at_position(
            position, self.waypoint_system.area_grid
        )

    def _has_obstacle_in_direction(self, current_pos, direction):
        """檢查方向上是否有障礙物"""
        if not hasattr(self.waypoint_system, 'obstacles'):
            return False
            
        for obstacle in self.waypoint_system.obstacles:
            obs_pos = obstacle['pos']
            if self._point_in_direction(current_pos, direction, obs_pos, 0.1):
                return True
        return False

    def _calculate_distance(self, pos1, pos2):
        """計算兩點距離"""
        dx = pos1[0] - pos2[0]
        dy = pos1[1] - pos2[1]
        return (dx**2 + dy**2)**0.5

    def _point_in_direction(self, current_pos, direction, point, threshold):
        """檢查點是否在方向上"""
        vec_to_point = (point[0] - current_pos[0], point[1] - current_pos[1])
        dist_to_point = (vec_to_point[0]**2 + vec_to_point[1]**2)**0.5
        
        if dist_to_point > threshold:
            return False
        
        # 正規化向量
        if dist_to_point > 0:
            vec_to_point = (vec_to_point[0] / dist_to_point, vec_to_point[1] / dist_to_point)
            dot = vec_to_point[0] * direction[0] + vec_to_point[1] * direction[1]
            return dot > 0.7  # 方向相似度閾值
        
        return False

    def _execute_movement(self, current_pos, target_pos=None, movement_type="intelligent"):
        """統一的移動執行方法"""
        if movement_type == "intelligent":
            # 把原來 _update_intelligent_movement 的邏輯搬到這裡
            return self._handle_intelligent_movement(current_pos)
        elif movement_type == "direct" and target_pos:
            direction = self._get_direction_to_target(current_pos, target_pos)
            return self._handle_direct_movement(direction)
        elif movement_type == "patrol":
            return self._handle_patrol_movement(current_pos)
        
        return False

    def _face_monster(self, monster_info):
        """面向怪物"""
        pass

    # ✅ 保留的功能方法
    def set_skill_rotation(self, skills: list):
        """設定技能輪替"""
        if skills:
            self.skill_rotation = skills
            self.current_skill_index = 0
            pass

    def toggle_auto_pickup(self):
        """切換自動撿取"""
        self.auto_pickup = not self.auto_pickup
        status = "開啟" if self.auto_pickup else "關閉"
        pass
        return self.auto_pickup

    def _test_horizontal_line_tracking(self):
        """✅ 基於搜索結果[6]的水平線追蹤測試"""
        try:
            pass
            
            # 記錄起始位置
            frame = self.ro_helper.capturer.grab_frame()
            start_pos = self.ro_helper.tracker.track_player(frame)
            if not start_pos:
                start_pos = (0.5, 0.5)
            
            pass
            pass
            
            # 設定水平線追蹤
            self.horizontal_tracking = True
            self.horizontal_baseline = start_pos[1]
            self.horizontal_history = []
            self.horizontal_test_start = time.time()
            
            # 設定測試目標到同一水平線上
            combat_system = self.ro_helper.auto_combat
            if start_pos[0] < 0.5:
                target = (0.7, start_pos[1])  # 往右移動
            else:
                target = (0.3, start_pos[1])  # 往左移動
            
            combat_system.current_target = target
            combat_system.start()
            
            pass
            pass
            
            # 啟動追蹤
            self._track_horizontal_movement()
            
            self.movement_status.config(text="狀態: 水平線追蹤中")
            
        except Exception as e:
            pass

    def _track_horizontal_movement(self):
        """追蹤水平移動"""
        if not hasattr(self, 'horizontal_tracking') or not self.horizontal_tracking:
            return
        
        try:
            frame = self.ro_helper.capturer.grab_frame()
            current_pos = self.ro_helper.tracker.track_player(frame)
            
            if current_pos:
                timestamp = time.time() - self.horizontal_test_start
                
                # 計算垂直偏差
                vertical_deviation = abs(current_pos[1] - self.horizontal_baseline)
                
                # 記錄移動歷史
                self.horizontal_history.append({
                    'time': timestamp,
                    'pos': current_pos,
                    'deviation': vertical_deviation
                })
                
                # ✅ 基於搜索結果[6]的即時反饋
                if vertical_deviation < 0.01:
                    pass
                elif vertical_deviation < 0.02:
                    pass
                else:
                    pass
                
                # 檢查區域類型
                area_type = self.ro_helper.auto_combat._get_area_type(current_pos)
                if area_type == "walkable":
                    pass
                else:
                    pass
            
            # 測試15秒
            if time.time() - self.horizontal_test_start < 15:
                self.root.after(500, self._track_horizontal_movement)
            else:
                self._analyze_horizontal_movement()
                
        except Exception as e:
            pass

    def _analyze_horizontal_movement(self):
        """分析水平移動結果"""
        self.horizontal_tracking = False
        
        if not hasattr(self, 'horizontal_history') or not self.horizontal_history:
            return
        
        pass
        
        # 分析垂直偏差
        deviations = [record['deviation'] for record in self.horizontal_history]
        max_deviation = max(deviations)
        avg_deviation = sum(deviations) / len(deviations)
        
        pass
        pass
        pass
        
        # 分析水平移動範圍
        x_positions = [record['pos'][0] for record in self.horizontal_history]
        x_range = max(x_positions) - min(x_positions)
        
        pass
        
        # 評估結果
        if avg_deviation < 0.01 and x_range > 0.1:
            pass
        elif avg_deviation < 0.02 and x_range > 0.05:
            pass
        elif x_range > 0.02:
            pass
        else:
            pass
        
        self.movement_status.config(text="狀態: 水平線分析完成")

    def diagnose_waypoint_system(self):
        """診斷waypoint系統狀態 - 簡化版"""
        try:
            if not self.waypoint_system:
                self.logger.warning("waypoint_system為None")
                return
            
            # 檢查基本屬性
            attributes = ['waypoints', 'area_grid', 'current_target_index']
            for attr_name in attributes:
                if hasattr(self.waypoint_system, attr_name):
                    attr_value = getattr(self.waypoint_system, attr_name)
                    if isinstance(attr_value, (list, dict)):
                        count = len(attr_value)
                        self.logger.info(f"{attr_name}: {count} 項目")
                    else:
                        self.logger.info(f"{attr_name}: {type(attr_value)}")
                else:
                    self.logger.warning(f"{attr_name}: 不存在")
                    
        except Exception as e:
            self.logger.error(f"診斷waypoint系統失敗: {e}")

    def _check_fall_detection(self, pre_move_pos):
        """✅ 掉落檢測"""
        try:
            if not pre_move_pos:
                return False
            
            # 獲取移動後位置
            if hasattr(self, 'ro_helper') and hasattr(self.ro_helper, 'capturer'):
                frame = self.ro_helper.capturer.grab_frame()
                if frame and hasattr(self.ro_helper, 'tracker'):
                    current_pos = self.ro_helper.tracker.track_player(frame)
                    if current_pos:
                        # 檢查垂直位置變化
                        vertical_change = abs(current_pos[1] - pre_move_pos[1])
                        
                        pass
                        pass
                        
                        # 如果垂直位置變化超過0.1（10%），視為掉落
                        if vertical_change > 0.1:
                            pass
                            return True
            
            return False
            
        except Exception as e:
            pass
            return False
        
    def _has_nearby_walkable_area(self, position, radius=0.1):
        """✅ 檢查周圍是否有可行走區域"""
        try:
            if not hasattr(self.waypoint_system, 'area_grid'):
                return False
            
            area_grid = self.waypoint_system.area_grid
            if not area_grid:
                return False
            
            # 檢查周圍半徑內的區域
            for grid_key, area_type in area_grid.items():
                if area_type == "walkable":
                    try:
                        if isinstance(grid_key, tuple):
                            gx, gy = grid_key
                        elif isinstance(grid_key, str) and ',' in grid_key:
                            gx_str, gy_str = grid_key.split(',')
                            gx, gy = float(gx_str), float(gy_str)
                        else:
                            continue
                        
                        # 計算距離
                        distance = ((gx - position[0])**2 + (gy - position[1])**2)**0.5
                        if distance <= radius:
                            return True
                            
                    except Exception:
                        continue
            
            return False
            
        except Exception as e:
            pass
            return False

    def _get_movement_with_smart_fallback(self, current_pos, target_pos):
        """✅ 智能後備移動策略"""
        # 先嘗試正常的區域感知移動
        direction = self._get_movement_with_area_awareness(current_pos, target_pos)
        
        if direction:
            return direction
        
        # 如果無法移動，檢查是否因為過度保守
        pass
        
        # 檢查周圍是否有可行走區域
        if self._has_nearby_walkable_area(current_pos, radius=0.15):
            pass
            
            # 使用簡單的朝向目標移動
            dx = target_pos[0] - current_pos[0]
            dy = target_pos[1] - current_pos[1]
            
            # 歸一化
            distance = (dx**2 + dy**2)**0.5
            if distance > 0:
                return (dx / distance, dy / distance)
        
        pass
        return None
        
    def _find_next_patrol_target(self, current_pos):
        """尋找下一個巡邏目標"""
        try:
            if not hasattr(self.waypoint_system, 'area_grid') or not self.waypoint_system.area_grid:
                # 沒有區域數據，使用簡單巡邏
                return self._simple_patrol_target(current_pos)
            
            # 使用MovementUtils尋找安全移動目標
            from includes.movement_utils import MovementUtils
            movement_utils = MovementUtils(self.waypoint_system)
            area_target = movement_utils.find_safe_movement_target(current_pos)
            
            if area_target:
                return area_target
            else:
                # MovementUtils沒找到目標，使用後備巡邏
                return self._simple_patrol_target(current_pos)
                
        except Exception as e:
            self.logger.error(f"目標尋找失敗: {e}")
            return self._simple_patrol_target(current_pos)

    def _safe_area_chase_target(self, current_pos):
        """在安全區域內追擊目標（帶狀態管理）"""
        try:
            target = self.auto_hunt_target
            if not target:
                return False
            target_pos = target.get('position', (0, 0))
            # 轉換螢幕座標為相對座標
            if hasattr(self, 'tracker') and self.tracker:
                frame = self.tracker.capturer.grab_frame()
                if frame:
                    rel_target_pos = self._screen_to_relative(target_pos, frame.shape)
                else:
                    return False
            else:
                return False
            # ✅ 檢查目標是否在安全攻擊範圍內
            distance = self._calculate_distance(current_pos, rel_target_pos)
            max_chase = self.hunt_settings.get('max_chase_distance', 0.15)
            if distance > max_chase:
                pass
                self.auto_hunt_target = None
                return self._execute_patrol_movement(current_pos)
            # ✅ 計算安全的移動位置
            safe_move_pos = self._calculate_safe_approach_position(current_pos, rel_target_pos)
            if safe_move_pos and self._is_in_safe_area(safe_move_pos):
                direction = self._get_direction_to_target(current_pos, safe_move_pos)
                if direction:
                    pass
                    # 改為呼叫狀態管理移動
                    return self._execute_patrol_movement(current_pos)
            # 無法安全接近，原地攻擊
            pass
            return True
        except Exception as e:
            pass
            return False

    def _safe_area_patrol(self, current_pos):
        """在安全區域內巡邏（帶狀態管理）"""
        try:
            return self._execute_patrol_movement(current_pos)
        except Exception as e:
            pass
            return False

    def _screen_to_relative(self, screen_pos, frame_shape):
        """螢幕座標轉相對座標"""
        try:
            frame_height, frame_width = frame_shape[:2]
            rel_x = screen_pos[0] / frame_width
            rel_y = screen_pos[1] / frame_height
            return (rel_x, rel_y)
        except:
            return (0.5, 0.5)

    def _is_in_safe_area(self, position):
        """修正版：使用動態容忍度的安全區域檢查"""
        try:
            if not hasattr(self.waypoint_system, 'area_grid') or not self.waypoint_system.area_grid:
                return False

            current_x, current_y = position
            pass
            
            # ✅ 動態容忍度：基於座標精度調整
            base_tolerance_x = 0.015  # 基礎X軸容忍度
            base_tolerance_y = 0.035  # 增加Y軸容忍度到3.5%
            
            # 根據座標值動態調整（邊緣區域容忍度更大）
            edge_factor = 1.0
            if current_x < 0.1 or current_x > 0.9 or current_y < 0.1 or current_y > 0.9:
                edge_factor = 1.5  # 邊緣區域容忍度增加50%
            
            tolerance_x = base_tolerance_x * edge_factor
            tolerance_y = base_tolerance_y * edge_factor
            
            pass
            
            # 檢查所有可行走區域
            for pos_key, area_type in self.waypoint_system.area_grid.items():
                if area_type == "walkable":
                    try:
                        if isinstance(pos_key, str) and ',' in pos_key:
                            x_str, y_str = pos_key.split(',')
                            target_x, target_y = float(x_str), float(y_str)
                        elif isinstance(pos_key, tuple):
                            target_x, target_y = pos_key
                        else:
                            continue
                        
                        # ✅ 高精度距離計算
                        x_diff = abs(current_x - target_x)
                        y_diff = abs(current_y - target_y)
                        
                        pass
                        pass
                        pass
                        
                        # ✅ 分別檢查X和Y軸
                        if x_diff <= tolerance_x and y_diff <= tolerance_y:
                            pass
                            return True
                            
                    except Exception as e:
                        pass
                        continue
            
            pass
            return False
            
        except Exception as e:
            pass
            return False

    def _calculate_safe_approach_position(self, current_pos, target_pos):
        """✅ 高精度安全接近位置計算"""
        try:
            if not self.waypoint_system or not hasattr(self.waypoint_system, 'area_grid'):
                return None
                
            # 計算方向向量
            dx = target_pos[0] - current_pos[0]
            dy = target_pos[1] - current_pos[1]
            distance = (dx * dx + dy * dy) ** 0.5
            
            if distance < 0.001:  # 太近就不需要移動
                return current_pos
                
            # 標準化方向向量
            dx /= distance
            dy /= distance
            
            # 計算安全接近距離
            approach_distance = min(
                self.hunt_settings.get('approach_distance', 0.1),
                distance * 0.8  # 最多接近到目標的80%
            )
            
            # 計算目標位置
            target_x = current_pos[0] + dx * approach_distance
            target_y = current_pos[1] + dy * approach_distance
            
            # 使用高精度區域檢查
            if MovementUtils.is_within_walkable_bounds_enhanced(
                (target_x, target_y),
                self.waypoint_system.area_grid,
                tolerance_x=0.01,
                tolerance_y=0.02
            ):
                return (target_x, target_y)
                
            # 如果目標位置不安全，嘗試找到最近的安全位置
            return self._find_nearest_safe_position((target_x, target_y))
            
        except Exception as e:
            pass
            return None

    def _approach_monster(self, current_pos):
        """✅ 新增：接近怪物的方法"""
        try:
            if not self.auto_hunt_target:
                return False
            
            # 獲取怪物位置
            monster_pos = self.auto_hunt_target.get('position', (0, 0))
            monster_distance = self.auto_hunt_target.get('distance', 1.0)
            
            # 計算朝向怪物的方向
            dx = monster_pos[0] - current_pos[0]
            dy = monster_pos[1] - current_pos[1]
            
            # 正規化方向向量
            distance = (dx**2 + dy**2)**0.5
            if distance < 0.01:
                pass
                # 移除接近標記，可以開始攻擊
                if 'needs_approach' in self.auto_hunt_target:
                    del self.auto_hunt_target['needs_approach']
                return False
            
            dx /= distance
            dy /= distance
            
            # ✅ 計算安全的接近距離
            approach_distance = min(0.1, monster_distance * 0.3)  # 接近30%的距離
            target_x = current_pos[0] + dx * approach_distance
            target_y = current_pos[1] + dy * approach_distance
            target_pos = (target_x, target_y)
            
            # ✅ 檢查目標位置是否安全
            if not self._is_in_safe_area(target_pos):
                pass
                # 找到朝向怪物方向的安全位置
                target_pos = self._find_safe_position_towards_target(current_pos, monster_pos)
                if not target_pos:
                    pass
                    return False
            
            # 計算移動方向
            direction = self._get_direction_to_target(current_pos, target_pos)
            if direction:
                pass
                pass
                pass
                pass
                
                # 執行移動
                self._start_action("approach", 0.3)
                # 楓之谷 Worlds 原生遊戲 - 模擬接近移動
                move_key = direction.upper()
                self.logger.info(f"🎯 模擬接近怪物移動: {move_key} (0.3秒) - 楓之谷 Worlds")
                success = True  # 模擬成功
                if success:
                    # 檢查是否已經足夠接近，可以開始攻擊
                    new_distance = self._calculate_distance(current_pos, monster_pos)
                    attack_range = self.hunt_settings.get('attack_range', 0.4)
                    if new_distance <= attack_range * 1.2:  # 允許20%的誤差
                        pass
                        if 'needs_approach' in self.auto_hunt_target:
                            del self.auto_hunt_target['needs_approach']
                    return True
                return False
            
            return False
            
        except Exception as e:
            pass
            return False

    def _find_safe_position_towards_target(self, current_pos, target_pos):
        """✅ 新增：找到朝向目標的安全位置"""
        try:
            if not hasattr(self.waypoint_system, 'area_grid'):
                return None
                
            # 計算方向向量
            dx = target_pos[0] - current_pos[0]
            dy = target_pos[1] - current_pos[1]
            distance = (dx**2 + dy**2)**0.5
            
            if distance < 0.01:
                return None
                
            dx /= distance
            dy /= distance
            
            # 在安全區域內尋找朝向目標的位置
            area_grid = self.waypoint_system.area_grid
            best_pos = None
            best_score = -1
            
            for pos_key, area_type in area_grid.items():
                if area_type == "walkable":
                    try:
                        if isinstance(pos_key, str) and ',' in pos_key:
                            x_str, y_str = pos_key.split(',')
                            gx, gy = float(x_str), float(y_str)
                        elif isinstance(pos_key, tuple):
                            gx, gy = pos_key
                        else:
                            continue
                        
                        # 計算該位置與當前位置的方向
                        pos_dx = gx - current_pos[0]
                        pos_dy = gy - current_pos[1]
                        pos_distance = (pos_dx**2 + pos_dy**2)**0.5
                        
                        if pos_distance < 0.01:
                            continue
                            
                        pos_dx /= pos_distance
                        pos_dy /= pos_distance
                        
                        # 計算與目標方向的相似度
                        similarity = dx * pos_dx + dy * pos_dy
                        
                        # 偏好較近的位置，但要朝向目標方向
                        score = similarity * 0.7 - pos_distance * 0.3
                        
                        if score > best_score and pos_distance < 0.1:  # 限制距離
                            best_score = score
                            best_pos = (gx, gy)
                            
                    except Exception:
                        continue
            
            return best_pos
            
        except Exception as e:
            pass
            return None

    def _direction_to_key(self, direction):
        """方向轉換為按鍵名稱"""
        direction_map = {
            'up': 'UP',
            'down': 'DOWN', 
            'left': 'LEFT',
            'right': 'RIGHT'
        }
        return direction_map.get(direction, direction)

    def _simple_patrol_target(self, current_pos):
        """簡單巡邏目標 - 當沒有區域數據時使用"""
        # 簡單的左右移動
        if not hasattr(self, '_patrol_direction'):
            self._patrol_direction = 1  # 1 = 右, -1 = 左
            
        # 計算目標位置
        move_distance = 0.05  # 5%的移動距離
        target_x = current_pos[0] + (self._patrol_direction * move_distance)
        
        # 邊界檢查，防止超出畫面
        if target_x > 0.9:
            self._patrol_direction = -1
            target_x = 0.9
        elif target_x < 0.1:
            self._patrol_direction = 1
            target_x = 0.1
            
        return (target_x, current_pos[1])

    def set_shared_detection_callback(self, callback):
        """設置共享怪物檢測結果回調函數"""
        self._get_shared_monster_detection = callback
        self.logger.info("戰鬥系統已連接共享怪物檢測服務")
    
    def set_shared_health_detection_callback(self, callback):
        """設置共享角色血條檢測結果回調函數"""
        self._get_shared_health_detection = callback
        self.logger.info("戰鬥系統已連接共享血條檢測服務")

def check_auto_combat_status(ro_helper):
    """檢查自動戰鬥狀態"""
    if hasattr(ro_helper, 'auto_combat'):
        combat = ro_helper.auto_combat
        pass
        pass
        pass
        # 檢查控制器
        if combat.controller:
            pass
            pass
        else:
            pass
            # ADB 控制器已移除 - 楓之谷 Worlds 原生遊戲
            pass
    else:
        pass


def reinitialize_control_system(ro_helper):
    """重新初始化控制系統"""
    try:
        pass
        # ADB 控制器已移除 - 楓之谷 Worlds 原生遊戲
        if hasattr(ro_helper, 'auto_combat'):
            ro_helper.auto_combat.controller = None
            # ADB 初始化已移除
            if ro_helper.auto_combat.controller and ro_helper.auto_combat.controller.is_connected:
                pass
                return True
            else:
                pass
        else:
            pass
        return False
    except Exception as e:
        pass
        return False