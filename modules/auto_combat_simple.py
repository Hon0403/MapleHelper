# modules/auto_combat_simple.py - 基於搜索結果[5]的AI移動整理版

import time
import random
import numpy as np
from includes.simple_template_utils import monster_detector
from includes.movement_utils import MovementUtils


class SimpleCombat:
    """基於搜索結果[5]的AI Bot移動系統"""
    
    def __init__(self):
        self.controller = None
        self.is_enabled = False
        self.monster_detector = monster_detector
        self.last_attack_time = 0
        self.last_combat_check = 0
        self.attack_interval = 0.5
        
        # ✅ 基於搜索結果[5]的技能輪替
        self.skill_rotation = ['attack', 'skill1', 'attack', 'skill2']
        self.current_skill_index = 0
        self.auto_pickup = True
        self.auto_target_enabled = True
        
        # ✅ 基於搜索結果[3][4]的區域移動系統
        self.waypoint_system = None  # 將由main.py注入
        self.current_target = None
        self.last_movement_time = 0
        self.movement_interval = 3  # 移動更新間隔
        self.patrol_direction = 'right'

        self.auto_hunt_mode = "off"  # off, attack, defend, smart
        self.hunt_settings = {
            'search_radius': 200,
            'move_interval': 3,
            'use_waypoints': True
        }
        self.auto_hunt_target = None
        self.last_move_time = 0

        print("🐲 戰鬥系統已整合怪物檢測和區域移動")
        self._init_adb()

    def _init_adb(self):
        """初始化ADB控制器"""
        from modules.simple_adb import SimpleADB
        self.controller = SimpleADB()

    def set_waypoint_system(self, waypoint_system):
        """✅ 注入waypoint系統"""
        self.waypoint_system = waypoint_system
        print("🗺️ 已整合waypoint系統")

    def start(self):
        """開始戰鬥"""
        self.is_enabled = True
        print("⚔️ 簡單戰鬥模式已啟動")
        return True

    def stop(self):
        """停止戰鬥"""
        self.is_enabled = False
        print("⚔️ 簡單戰鬥模式已停止")

    def update(self, current_pos=None, game_frame=None):
        """✅ 修正版：確保攻擊邏輯正確執行"""
        if not current_pos:
            return

        print(f"🔄 調用auto_combat.update - 位置: {current_pos}")

        # ✅ 1. 檢測怪物並更新目標
        has_target = False
        if game_frame is not None:
            has_target = self._update_monster_targeting(game_frame, current_pos)
        
        # ✅ 2. 自動打怪邏輯 - 如果有目標就攻擊
        if self.auto_hunt_mode != "off":
            current_time = time.time()
            hunt_attack_interval = 0.5  # 攻擊間隔
            
            if current_time - self.last_attack_time >= hunt_attack_interval:
                if has_target or len(getattr(self, 'last_detected_monsters', [])) > 0:
                    # 有目標時執行攻擊
                    if self._execute_combat_sequence():
                        self.last_attack_time = current_time
                        print(f"🤖 自動打怪攻擊執行")
                    else:
                        print(f"❌ 自動打怪攻擊失敗")
                else:
                    print(f"🔍 自動打怪：無目標，等待中...")
        
        # ✅ 3. 基本戰鬥邏輯（手動模式）
        if self.auto_hunt_mode == "off":
            self._handle_combat(current_pos, game_frame)
        
        # ✅ 4. 移動邏輯
        self._handle_manual_movement(current_pos)

    def _execute_combat_sequence(self):
        """✅ 修正版：確保攻擊執行"""
        if not self.controller or not self.controller.is_connected:
            print("❌ 控制器未連接，無法攻擊")
            return False
        
        try:
            current_skill = self.skill_rotation[self.current_skill_index]
            success = self._perform_attack(current_skill)
            
            if success:
                self.current_skill_index = (self.current_skill_index + 1) % len(self.skill_rotation)
                print(f"✅ 戰鬥: {current_skill}")
                return True
            else:
                print(f"❌ 攻擊失敗: {current_skill}")
                return False
                
        except Exception as e:
            print(f"❌ 戰鬥序列錯誤: {e}")
            return False

    def _perform_attack(self, skill_type: str):
        """✅ 修正版：確保攻擊執行"""
        try:
            if skill_type == 'attack':
                success = self.controller.attack()
                if success:
                    print("⚔️ 執行攻擊")
                return success
            elif skill_type.startswith('skill'):
                skill_number = int(skill_type[-1])
                success = self.controller.use_skill(skill_number)
                if success:
                    print(f"✨ 使用技能{skill_number}")
                return success
            else:
                return self.controller.attack()
                
        except Exception as e:
            print(f"❌ 攻擊執行錯誤: {e}")
            return False

    def _update_monster_targeting(self, game_frame, player_pos):
        """✅ 修正版：完全使用simple_template_utils的monster_detector"""
        try:
            if game_frame is None:
                return

            frame_height, frame_width = game_frame.shape[:2]
            if frame_width < 500 or frame_height < 500:
                return

            # ✅ 使用simple_template_utils.py的全域monster_detector
            detected_monsters = self.monster_detector.detect_monsters(game_frame)

            if detected_monsters:
                print(f"🐲 自動打怪檢測到 {len(detected_monsters)} 隻怪物")
                
                # ✅ 使用simple_template_utils.py的find_target_monster方法
                if player_pos:
                    screen_pos = (int(player_pos[0] * game_frame.shape[1]),
                                int(player_pos[1] * game_frame.shape[0]))
                    
                    target_monster = self.monster_detector.find_target_monster(
                        game_frame, screen_pos
                    )
                    
                    if target_monster:
                        print(f"🎯 自動打怪鎖定目標: {target_monster['name']}")
                        self._face_monster(target_monster)
                        return True
            else:
                print("🔍 自動打怪：尋找目標中...")
                
        except Exception as e:
            print(f"❌ 怪物目標更新錯誤: {e}")
            
        return False

    def _find_next_target(self, current_pos):
        """✅ 修正版：完整的巡邏目標尋找"""
        try:
            print(f"🔍 尋找移動目標 - 當前位置: {current_pos}")
            
            # 檢查是否有area_grid
            if not hasattr(self.waypoint_system, 'area_grid') or not self.waypoint_system.area_grid:
                print("❌ 沒有area_grid數據，使用簡單巡邏")
                return self._simple_patrol_target(current_pos)
            
            # ✅ 使用MovementUtils但添加巡邏邏輯
            area_target = MovementUtils.find_safe_target_in_walkable_area(
                current_pos, self.waypoint_system.area_grid, max_distance=0.05
            )
            
            if area_target:
                print(f"✅ 找到安全目標: {area_target}")
                return area_target
            else:
                print("⚠️ MovementUtils沒找到目標，使用後備巡邏")
                return self._simple_patrol_target(current_pos)
                
        except Exception as e:
            print(f"❌ 目標尋找失敗: {e}")
            return self._simple_patrol_target(current_pos)

    def _get_movement_with_area_awareness(self, current_pos, target_pos):
        """✅ 修正版：區域感知移動"""
        try:
            print(f"🧭 計算移動方向: {current_pos} -> {target_pos}")
            
            # 檢查是否有區域數據
            if not hasattr(self.waypoint_system, 'area_grid') or not self.waypoint_system.area_grid:
                print("⚠️ 沒有區域數據，使用簡單方向計算")
                return self._simple_direction_calculation(current_pos, target_pos)
            
            # ✅ 使用MovementUtils
            direction = MovementUtils.compute_area_aware_movement(
                current_pos, target_pos, self.waypoint_system.area_grid
            )
            
            if direction:
                print(f"✅ 區域感知方向: {direction}")
                return direction
            else:
                print("⚠️ 區域感知失敗，使用簡單計算")
                return self._simple_direction_calculation(current_pos, target_pos)
                
        except Exception as e:
            print(f"❌ 移動方向計算失敗: {e}")
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

    def _get_direction_to_target(self, current_pos, target_pos):
        """✅ 使用MovementUtils"""
        return MovementUtils.compute_direction_to_target(current_pos, target_pos)

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
        print(f"👀 面向怪物: {monster_info['name']}")

    # ✅ 保留的功能方法
    def set_skill_rotation(self, skills: list):
        """設定技能輪替"""
        if skills:
            self.skill_rotation = skills
            self.current_skill_index = 0
            print(f"✅ 技能輪替已設定: {skills}")

    def toggle_auto_pickup(self):
        """切換自動撿取"""
        self.auto_pickup = not self.auto_pickup
        status = "開啟" if self.auto_pickup else "關閉"
        print(f"📦 自動撿取: {status}")
        return self.auto_pickup

    def _test_horizontal_line_tracking(self):
        """✅ 基於搜索結果[6]的水平線追蹤測試"""
        try:
            print("📏 開始水平線追蹤測試...")
            
            # 記錄起始位置
            frame = self.ro_helper.capturer.grab_frame()
            start_pos = self.ro_helper.tracker.track_player(frame)
            if not start_pos:
                start_pos = (0.5, 0.5)
            
            print(f"📍 起始位置: {start_pos}")
            print(f"📏 基準水平線 Y座標: {start_pos[1]:.3f}")
            
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
            
            print(f"🎯 設定水平目標: {target}")
            print("📏 開始追蹤是否保持在水平線上...")
            
            # 啟動追蹤
            self._track_horizontal_movement()
            
            self.movement_status.config(text="狀態: 水平線追蹤中")
            
        except Exception as e:
            print(f"❌ 水平線追蹤測試失敗: {e}")

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
                    print(f"✅ {timestamp:.1f}s: 完美保持水平線 - 位置{current_pos} 偏差{vertical_deviation:.4f}")
                elif vertical_deviation < 0.02:
                    print(f"👍 {timestamp:.1f}s: 良好保持水平線 - 位置{current_pos} 偏差{vertical_deviation:.4f}")
                else:
                    print(f"⚠️ {timestamp:.1f}s: 偏離水平線 - 位置{current_pos} 偏差{vertical_deviation:.4f}")
                
                # 檢查區域類型
                area_type = self.ro_helper.auto_combat._get_area_type(current_pos)
                if area_type == "walkable":
                    print(f"🟢 在可行走區域")
                else:
                    print(f"❌ 不在可行走區域 (類型: {area_type})")
            
            # 測試15秒
            if time.time() - self.horizontal_test_start < 15:
                self.root.after(500, self._track_horizontal_movement)
            else:
                self._analyze_horizontal_movement()
                
        except Exception as e:
            print(f"❌ 水平追蹤錯誤: {e}")

    def _analyze_horizontal_movement(self):
        """分析水平移動結果"""
        self.horizontal_tracking = False
        
        if not hasattr(self, 'horizontal_history') or not self.horizontal_history:
            return
        
        print("\n📊 水平線移動分析報告:")
        
        # 分析垂直偏差
        deviations = [record['deviation'] for record in self.horizontal_history]
        max_deviation = max(deviations)
        avg_deviation = sum(deviations) / len(deviations)
        
        print(f"📏 基準水平線: Y = {self.horizontal_baseline:.3f}")
        print(f"📏 最大偏差: {max_deviation:.4f}")
        print(f"📏 平均偏差: {avg_deviation:.4f}")
        
        # 分析水平移動範圍
        x_positions = [record['pos'][0] for record in self.horizontal_history]
        x_range = max(x_positions) - min(x_positions)
        
        print(f"📏 水平移動範圍: {x_range:.3f}")
        
        # 評估結果
        if avg_deviation < 0.01 and x_range > 0.1:
            print("🏆 優秀！角色完美沿水平線移動")
        elif avg_deviation < 0.02 and x_range > 0.05:
            print("👍 良好！角色基本沿水平線移動")
        elif x_range > 0.02:
            print("⚠️ 可接受！角色有移動但偏離水平線較多")
        else:
            print("❌ 需要改進！角色移動不明顯或嚴重偏離")
        
        self.movement_status.config(text="狀態: 水平線分析完成")

    def diagnose_waypoint_system(self):
        """✅ 基於搜索結果[1][2]的waypoint系統診斷"""
        try:
            print("🔍 診斷waypoint系統...")
            
            # 檢查waypoint_system
            if not self.waypoint_system:
                print("❌ waypoint_system為None")
                return
            
            print(f"✅ waypoint_system存在，類型: {type(self.waypoint_system)}")
            
            # 檢查各種屬性
            attrs_to_check = ['waypoints', 'obstacles', 'area_grid', 'obstacle_types']
            
            for attr_name in attrs_to_check:
                if hasattr(self.waypoint_system, attr_name):
                    attr_value = getattr(self.waypoint_system, attr_name)
                    attr_type = type(attr_value).__name__
                    
                    if isinstance(attr_value, (list, dict)):
                        count = len(attr_value)
                        print(f"✅ {attr_name}: {attr_type}, 數量: {count}")
                        
                        # 顯示內容樣本
                        if attr_name == 'area_grid' and attr_value:
                            sample_items = list(attr_value.items())[:3]
                            print(f"  樣本: {sample_items}")
                    else:
                        print(f"✅ {attr_name}: {attr_type}")
                else:
                    print(f"❌ {attr_name}: 不存在")
            
            # 檢查area_grid的鍵值格式
            if hasattr(self.waypoint_system, 'area_grid') and self.waypoint_system.area_grid:
                area_grid = self.waypoint_system.area_grid
                print("🔍 分析area_grid鍵值格式:")
                
                key_types = {}
                for key in list(area_grid.keys())[:5]:  # 檢查前5個鍵值
                    key_type = type(key).__name__
                    key_types[key_type] = key_types.get(key_type, 0) + 1
                    print(f"  鍵值 {key} (類型: {key_type}) -> {area_grid[key]}")
                
                print(f"🔍 鍵值類型統計: {key_types}")
            
        except Exception as e:
            print(f"❌ 診斷失敗: {e}")
            import traceback
            traceback.print_exc()

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
                        
                        print(f"📏 移動前後位置: {pre_move_pos} → {current_pos}")
                        print(f"📏 垂直變化: {vertical_change:.3f}")
                        
                        # 如果垂直位置變化超過0.1（10%），視為掉落
                        if vertical_change > 0.1:
                            print(f"🚨 檢測到掉落！垂直變化: {vertical_change:.3f}")
                            return True
            
            return False
            
        except Exception as e:
            print(f"❌ 掉落檢測失敗: {e}")
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
            print(f"❌ 周圍區域檢測失敗: {e}")
            return False

    def _get_movement_with_smart_fallback(self, current_pos, target_pos):
        """✅ 智能後備移動策略"""
        # 先嘗試正常的區域感知移動
        direction = self._get_movement_with_area_awareness(current_pos, target_pos)
        
        if direction:
            return direction
        
        # 如果無法移動，檢查是否因為過度保守
        print("🔍 嘗試智能後備策略...")
        
        # 檢查周圍是否有可行走區域
        if self._has_nearby_walkable_area(current_pos, radius=0.15):
            print("🟢 周圍有可行走區域，使用簡單朝向目標移動")
            
            # 使用簡單的朝向目標移動
            dx = target_pos[0] - current_pos[0]
            dy = target_pos[1] - current_pos[1]
            
            # 歸一化
            distance = (dx**2 + dy**2)**0.5
            if distance > 0:
                return (dx / distance, dy / distance)
        
        print("❌ 無法找到安全移動方向")
        return None
        
    def _find_next_patrol_target(self, current_pos):
        """✅ 修正版巡邏目標尋找 - 絕對強制在可行走範圍內"""
        print(f"🔍 尋找巡邏目標 - 當前位置: {current_pos}")
        
        if hasattr(self.waypoint_system, 'area_grid') and self.waypoint_system.area_grid:
            current_y = current_pos[1]
            
            # 收集當前水平線的可行走位置
            walkable_x_positions = []
            
            for pos_key, area_type in self.waypoint_system.area_grid.items():
                if area_type == "walkable":
                    try:
                        if isinstance(pos_key, tuple):
                            target_x, target_y = pos_key
                        elif isinstance(pos_key, str) and ',' in pos_key:
                            x_str, y_str = pos_key.split(',')
                            target_x, target_y = float(x_str), float(y_str)
                        else:
                            continue
                        
                        # 同一水平線上的可行走點
                        if abs(target_y - current_y) < 0.05:
                            walkable_x_positions.append(target_x)
                            
                    except Exception:
                        continue
            
            if walkable_x_positions:
                # ✅ 絕對強制邊界限制
                min_safe_x = min(walkable_x_positions)
                max_safe_x = max(walkable_x_positions)
                current_x = current_pos[0]
                
                print(f"🛡️ 強制可行走範圍: [{min_safe_x:.3f}, {max_safe_x:.3f}]")
                print(f"📍 當前位置X: {current_x:.3f}")
                
                # ✅ 絕對不允許目標超出可行走範圍 - 基於搜索結果【2】
                if current_x <= min_safe_x:
                    # 在左邊緣或超出，目標設定在安全範圍最左邊
                    target_x = min_safe_x + 0.01
                    target_pos = (target_x, current_pos[1])
                    print(f"🏃 強制修正：從左邊移動到安全範圍: {target_pos}")
                elif current_x >= max_safe_x:
                    # 在右邊緣或超出，目標設定在安全範圍最右邊
                    target_x = max_safe_x - 0.01
                    target_pos = (target_x, current_pos[1])
                    print(f"🏃 強制修正：從右邊移動到安全範圍: {target_pos}")
                else:
                    # ✅ 在可行走範圍內，目標必須也在範圍內
                    center_x = (min_safe_x + max_safe_x) / 2
                    
                    # 計算安全的目標位置
                    if current_x < center_x:
                        # 往右邊移動，但不超出範圍
                        target_x = min(current_x + 0.02, max_safe_x - 0.01)
                    else:
                        # 往左邊移動，但不超出範圍
                        target_x = max(current_x - 0.02, min_safe_x + 0.01)
                    
                    target_pos = (target_x, current_pos[1])
                    print(f"🏃 安全範圍內巡邏: {target_pos}")
                
                # ✅ 最終驗證：確保目標絕對在可行走範圍內
                final_x = max(min_safe_x + 0.005, min(target_pos[0], max_safe_x - 0.005))
                final_target = (final_x, current_pos[1])
                
                print(f"✅ 最終安全目標: {final_target}")
                print(f"🔒 目標驗證: {min_safe_x:.3f} <= {final_x:.3f} <= {max_safe_x:.3f}")
                
                return final_target
        
        print("❌ 沒有找到可行走區域")
        return None
    
        
    def _is_within_walkable_bounds(self, position):
        """✅ 檢查位置是否在可行走範圍內"""
        try:
            if not hasattr(self.waypoint_system, 'area_grid') or not self.waypoint_system.area_grid:
                return False
            
            current_y = position[1]
            walkable_x_positions = []
            
            for pos_key, area_type in self.waypoint_system.area_grid.items():
                if area_type == "walkable":
                    try:
                        if isinstance(pos_key, tuple):
                            target_x, target_y = pos_key
                        elif isinstance(pos_key, str) and ',' in pos_key:
                            x_str, y_str = pos_key.split(',')
                            target_x, target_y = float(x_str), float(y_str)
                        else:
                            continue
                        
                        if abs(target_y - current_y) < 0.05:
                            walkable_x_positions.append(target_x)
                    except Exception:
                        continue
            
            if walkable_x_positions:
                min_safe_x = min(walkable_x_positions)
                max_safe_x = max(walkable_x_positions)
                pos_x = position[0]
                
                return min_safe_x <= pos_x <= max_safe_x
            
            return False
            
        except Exception as e:
            print(f"❌ 可行走範圍檢查失敗: {e}")
            return False        
        
    def _unified_safety_check(self, position, check_type="area"):
        """✅ 統一的安全檢查方法"""
        if check_type == "area":
            return self._get_area_type(position)
        elif check_type == "bounds":
            return self._is_within_walkable_bounds(position)
        elif check_type == "target":
            return self._verify_target_safety(position)
        else:
            # 綜合檢查
            area_safe = self._get_area_type(position) != "forbidden"
            bounds_safe = self._is_within_walkable_bounds(position)
            return area_safe and bounds_safe        
        
    def _handle_intelligent_movement(self, current_pos):
        """✅ 完全基於搜索結果[16]的MovementUtils"""
        try:
            print(f"🤖 智能移動開始 - 位置: {current_pos}")
            
            # ✅ 1. 優先檢查緊急修正
            if hasattr(self.waypoint_system, 'area_grid') and self.waypoint_system.area_grid:
                emergency_target = self._check_emergency_boundary_correction(current_pos)
                if emergency_target:
                    print(f"🚨 執行緊急邊界修正")
                    return self._execute_emergency_movement(current_pos, emergency_target)
            
            # ✅ 2. 完全使用MovementUtils尋找目標
            if hasattr(self.waypoint_system, 'area_grid') and self.waypoint_system.area_grid:
                target = MovementUtils.find_safe_target_in_walkable_area(
                    current_pos, self.waypoint_system.area_grid, max_distance=0.03
                )
                
                if target:
                    print(f"✅ MovementUtils找到安全目標: {target}")
                else:
                    print("❌ MovementUtils沒找到目標")
                    # ✅ 不使用簡單巡邏，而是強制停留在當前位置
                    print("🔒 強制停留在當前位置，避免超出範圍")
                    return True
            else:
                print("❌ 沒有area_grid，無法移動")
                return False
            
            if not target:
                return False
            
            # ✅ 3. 使用MovementUtils驗證安全性
            is_safe = MovementUtils.validate_movement_safety(
                current_pos, target, self.waypoint_system.area_grid
            )
            
            if not is_safe:
                print("⚠️ 目標位置不安全，取消移動")
                return False
            
            # ✅ 4. 計算移動距離和時間
            distance = MovementUtils.calculate_distance(current_pos, target)
            print(f"🎯 安全移動目標: {current_pos} -> {target} 距離:{distance:.3f}")
            
            # 根據距離計算移動時間
            if distance <= 0.02:
                move_duration = 0.3
            elif distance <= 0.05:
                move_duration = 0.5
            elif distance <= 0.1:
                move_duration = 0.8
            else:
                move_duration = 1.2
            
            print(f"⏱️ 根據距離{distance:.3f}設定移動時間: {move_duration}秒")
            
            # ✅ 5. 使用MovementUtils計算方向
            direction = MovementUtils.compute_area_aware_movement(
                current_pos, target, self.waypoint_system.area_grid
            )
            
            if not direction or (direction[0] == 0 and direction[1] == 0):
                print("⚠️ MovementUtils無法計算有效方向")
                return False
            
            # ✅ 6. 使用MovementUtils轉換命令
            move_command = MovementUtils.convert_direction_to_movement_command(direction)
            
            if move_command == "none":
                return True
            
            # ✅ 7. 執行移動
            if self.controller and self.controller.is_connected:
                success = self.controller.move(move_command, duration=move_duration)
                if success:
                    print(f"✅ 安全移動成功: {move_command} ({move_duration}秒)")
                else:
                    print(f"❌ 移動失敗: {move_command}")
                    return self._attempt_emergency_recovery(current_pos)
                return success
            
            return False
            
        except Exception as e:
            print(f"❌ 智能移動失敗: {e}")
            return False
        
    def _handle_direct_movement(self, direction):
        """✅ 直接移動處理"""
        try:
            if not direction:
                return False
            
            return self._move_in_direction(direction)
            
        except Exception as e:
            print(f"❌ 直接移動失敗: {e}")
            return False        
        
    def _handle_patrol_movement(self, current_pos):
        """✅ 巡邏移動處理"""
        try:
            # 使用現有的巡邏邏輯
            target = self._find_next_patrol_target(current_pos)
            if not target:
                print("❌ 沒有巡邏目標")
                return False
            
            direction = self._get_direction_to_target(current_pos, target)
            return self._move_in_direction(direction)
            
        except Exception as e:
            print(f"❌ 巡邏移動失敗: {e}")
            return False        
        
    def _move_in_direction(self, direction, duration=2.0):  # ✅ 預設移動時間增加到2秒
        """✅ 修正版：更長的移動時間"""
        try:
            if not self.controller or not self.controller.is_connected:
                print("❌ 控制器未連接")
                return False
            
            # ✅ 使用MovementUtils進行方向轉換
            move_command = MovementUtils.convert_direction_to_movement_command(direction)
            
            if move_command == "none":
                print("⚠️ 無需移動")
                return True
            
            print(f"🏃 執行移動命令: {move_command} (持續{duration:.1f}秒)")
            
            # ✅ 執行更長時間的移動
            success = self.controller.move(move_command, duration=duration)
            
            if success:
                print(f"✅ 移動成功: {move_command}")
            else:
                print(f"❌ 移動失敗: {move_command}")
            
            return success
            
        except Exception as e:
            print(f"❌ 移動執行錯誤: {e}")
            return False
        
    def _simple_direction_calculation(self, current_pos, target_pos):
        """✅ 簡單的方向計算（後備方案）"""
        try:
            dx = target_pos[0] - current_pos[0]
            dy = target_pos[1] - current_pos[1]
            
            # 歸一化
            distance = (dx**2 + dy**2)**0.5
            if distance > 0:
                direction = (dx / distance, dy / distance)
                print(f"🧭 簡單方向: {direction}")
                return direction
            else:
                print("⚠️ 目標位置相同，不移動")
                return (0, 0)
                
        except Exception as e:
            print(f"❌ 簡單方向計算失敗: {e}")
            return (0, 0)        
        
    def set_auto_hunt_mode(self, mode):
        """設置自動打怪模式"""
        self.auto_hunt_mode = mode
        print(f"🤖 自動打怪模式: {mode}")
        
        # ✅ 關鍵：重置攻擊時間讓攻擊立即開始
        if mode != "off":
            self.last_attack_time = 0
            self.attack_interval = 0.5  # 確保攻擊間隔
            print(f"✅ 自動打怪已啟動，準備攻擊")

    def set_hunt_settings(self, settings):
        """設置打怪參數"""
        self.hunt_settings.update(settings)
        print(f"⚙️ 打怪設定已更新: {settings}")

    def _handle_combat(self, current_pos, game_frame):
        """✅ 保持原有戰鬥邏輯"""
        try:
            current_time = time.time()
            
            # 檢查攻擊間隔
            if current_time - self.last_attack_time < self.attack_interval:
                return
            
            # 更新怪物檢測和目標選擇
            if game_frame is not None:
                self._update_monster_targeting(game_frame, current_pos)
            
            # 執行戰鬥序列
            if self._execute_combat_sequence():
                self.last_attack_time = current_time
                
        except Exception as e:
            print(f"❌ 戰鬥處理失敗: {e}")

    def _handle_manual_movement(self, current_pos):
        """✅ 使用原有移動邏輯，不重複寫"""
        current_time = time.time()
        if current_time - self.last_movement_time >= self.movement_interval:
            print(f"🔄 強制移動更新 - 位置: {current_pos}")
            self._handle_intelligent_movement(current_pos)
            self.last_movement_time = current_time

    def _check_emergency_boundary_correction(self, current_pos):
        """檢查是否需要緊急邊界修正"""
        try:
            current_y = current_pos[1]
            walkable_x_positions = []
            
            # 收集可行走的X座標
            for pos_key, area_type in self.waypoint_system.area_grid.items():
                if area_type == "walkable":
                    try:
                        if isinstance(pos_key, tuple):
                            target_x, target_y = pos_key
                        elif isinstance(pos_key, str) and ',' in pos_key:
                            x_str, y_str = pos_key.split(',')
                            target_x, target_y = float(x_str), float(y_str)
                        else:
                            continue
                        
                        if abs(target_y - current_y) < 0.02:
                            walkable_x_positions.append(target_x)
                    except Exception:
                        continue
            
            if walkable_x_positions:
                min_safe_x = min(walkable_x_positions)
                max_safe_x = max(walkable_x_positions)
                current_x = current_pos[0]
                
                # 檢查是否在範圍外
                if current_x < min_safe_x or current_x > max_safe_x:
                    # 計算最近的安全位置
                    if current_x < min_safe_x:
                        safe_x = min_safe_x + 0.005
                    else:
                        safe_x = max_safe_x - 0.005
                    
                    return (safe_x, current_pos[1])
            
            return None
            
        except Exception as e:
            print(f"❌ 緊急邊界檢查失敗: {e}")
            return None            
        
    def _execute_emergency_movement(self, current_pos, target):
        """執行緊急移動"""
        try:
            direction = MovementUtils.compute_direction_to_target(current_pos, target)
            if direction:
                move_command = MovementUtils.convert_direction_to_movement_command(direction)
                distance = MovementUtils.calculate_distance(current_pos, target)
                
                # 緊急移動使用較短時間但多次執行
                emergency_duration = min(0.5, distance * 5)  # 控制移動時間
                
                print(f"🚨 緊急移動: {move_command} 持續 {emergency_duration:.2f}秒")
                
                if self.controller and self.controller.is_connected:
                    success = self.controller.move(move_command, duration=emergency_duration)
                    if success:
                        print(f"✅ 緊急移動成功")
                    return success
            
            return False
            
        except Exception as e:
            print(f"❌ 緊急移動失敗: {e}")
            return False

    def _attempt_emergency_recovery(self, current_pos):
        """移動失敗時的緊急恢復"""
        try:
            print("🔧 移動失敗，嘗試緊急恢復...")
            
            # 嘗試小幅度的移動回到安全範圍
            emergency_target = self._check_emergency_boundary_correction(current_pos)
            if emergency_target:
                return self._execute_emergency_movement(current_pos, emergency_target)
            
            return False
            
        except Exception as e:
            print(f"❌ 緊急恢復失敗: {e}")
            return False