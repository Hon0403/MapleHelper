# modules/auto_combat_simple.py - 基於搜索結果[5]的AI移動整理版

import time
import random
import numpy as np
from includes.simple_template_utils import monster_detector
from includes.movement_utils import MovementUtils
from includes.grid_utils import GridUtils


class SimpleCombat:
    """基於搜索結果[5]的AI Bot移動系統"""
    
    def __init__(self):
        """初始化戰鬥系統"""
        self.is_enabled = False
        self.auto_hunt_mode = "off"
        self.auto_hunt_target = None
        self.last_attack_time = 0
        self.controller = None
        self.waypoint_system = None
        
        # 初始化攻擊間隔
        self.attack_interval = 1.0  # 預設1秒
        self.movement_interval = 0.5  # 預設0.5秒
        
        # 初始化怪物檢測器
        try:
            from includes.simple_template_utils import monster_detector
            self.monster_detector = monster_detector
            if not self.monster_detector:
                raise RuntimeError("怪物檢測器初始化失敗")
            print("✅ 怪物檢測器已成功載入")
        except Exception as e:
            print(f"❌ 怪物檢測器初始化失敗: {e}")
            self.monster_detector = None
        
        # 初始化技能輪換
        self.skill_rotation = ['attack']  # 預設只有普通攻擊
        self.current_skill_index = 0
        
        # 初始化戰鬥設定
        self.hunt_settings = {
            'combat_mode': 'safe_area',
            'attack_range': 0.4,
            'approach_distance': 0.1,
            'retreat_distance': 0.05,
            'attack_cooldown': 1.5,
            'movement_speed': 0.8,
            'use_waypoints': False,
            'patrol_mode': 'safe_area',
            'max_chase_distance': 0.15,
            'return_to_safe': True
        }
        
        # 初始化控制器
        self._init_adb()
        
        print("⚔️ 戰鬥系統已初始化")
        print(f"🔍 怪物檢測器狀態: {'已初始化' if self.monster_detector else '未初始化'}")

    def _init_adb(self):
        """初始化ADB控制器"""
        try:
            from modules.simple_adb import SimpleADB
            self.controller = SimpleADB()
            
            # 確保ADB連接
            if not self.controller.is_connected:
                print("🔄 嘗試重新連接ADB...")
                self.controller.reconnect()
            
            if self.controller.is_connected:
                print("✅ ADB控制器已連接")
            else:
                print("❌ ADB控制器連接失敗")
                
        except Exception as e:
            print(f"❌ 初始化ADB控制器失敗: {e}")
            self.controller = None

    def set_waypoint_system(self, waypoint_system):
        """設置路徑點系統"""
        try:
            self.waypoint_system = waypoint_system
            print("✅ 路徑點系統已設置")
            return True
            
        except Exception as e:
            print(f"❌ 設置路徑點系統失敗: {e}")
            return False

    def start(self):
        """修正版：只有在明確調用時才啟動"""
        try:
            print("🔄 嘗試啟動戰鬥系統...")
            
            # 檢查路徑點系統
            if not self.waypoint_system:
                print("❌ 路徑點系統未設置")
                return False

            # 獲取戰鬥模式
            combat_mode = self.hunt_settings.get('combat_mode', 'waypoint')

            if combat_mode == 'safe_area':
                # 安全區域模式：檢查區域標記
                if not hasattr(self.waypoint_system, 'area_grid') or not self.waypoint_system.area_grid:
                    print("❌ 安全區域模式需要區域標記")
                    return False

                walkable_areas = [k for k, v in self.waypoint_system.area_grid.items() if v == "walkable"]
                if not walkable_areas:
                    print("❌ 沒有找到可行走區域")
                    return False

                print(f"✅ 安全區域模式準備完成，找到 {len(walkable_areas)} 個可行走區域")

            else:
                # 路徑點模式：需要路徑點
                if not hasattr(self.waypoint_system, 'waypoints') or not self.waypoint_system.waypoints:
                    print("❌ 路徑點模式需要路徑點")
                    return False

                print(f"✅ 路徑點模式準備完成，路徑點數量: {len(self.waypoint_system.waypoints)}")

            # 檢查控制器
            if not self.controller or not self.controller.is_connected:
                print("❌ 控制器未連接，嘗試重新初始化...")
                self._init_adb()
                
                if not self.controller or not self.controller.is_connected:
                    print("❌ 控制器初始化失敗")
                    return False

            # ✅ 關鍵修正：確保狀態被正確設置
            self.auto_hunt_mode = "attack"
            self.is_enabled = True
            
            # 重置所有計時器
            current_time = time.time()
            self.last_attack_time = current_time
            self.last_combat_check = current_time
            self.last_movement_time = current_time

            # 輸出詳細狀態
            print("\n✅ 戰鬥系統已啟動")
            print(f"🔍 戰鬥模式: {combat_mode}")
            print(f"🔍 自動打怪模式: {self.auto_hunt_mode}")
            print(f"🔍 控制器連接: {self.controller.is_connected}")
            print(f"🔍 is_enabled: {self.is_enabled}")
            print(f"🔍 攻擊冷卻: {self.hunt_settings.get('attack_cooldown', '未設定')}")
            print(f"🔍 移動速度: {self.hunt_settings.get('movement_speed', '未設定')}")

            return True

        except Exception as e:
            print(f"❌ 啟動戰鬥系統失敗: {e}")
            import traceback
            traceback.print_exc()
            # ✅ 確保失敗時重置狀態
            self.is_enabled = False
            self.auto_hunt_mode = "off"
            return False

    def stop(self):
        """停止戰鬥系統"""
        try:
            self.is_enabled = False
            self.auto_hunt_mode = "off"
            print("⏹️ 戰鬥系統已停止")
            return True
            
        except Exception as e:
            print(f"❌ 停止戰鬥系統失敗: {e}")
            return False

    def update(self, rel_pos, frame):
        """修正版：支援多種戰鬥模式的更新邏輯"""
        try:
            # 1. 基本狀態檢查
            if not self.is_enabled:
                print("❌ 戰鬥系統未啟用")
                return
            if not rel_pos:
                print("❌ 無法獲取角色位置")
                return

            # 2. 輸出當前狀態
            print("\n🔍 戰鬥系統狀態:")
            print(f"  - is_enabled: {self.is_enabled}")
            print(f"  - auto_hunt_mode: {self.auto_hunt_mode}")
            print(f"  - 角色位置: {rel_pos}")
            print(f"  - 攻擊冷卻: {time.time() - self.last_attack_time:.1f}秒")

            # 3. 根據戰鬥模式選擇不同的處理邏輯
            combat_mode = self.hunt_settings.get('combat_mode', 'waypoint')
            print(f"  - 戰鬥模式: {combat_mode}")
            
            if combat_mode == 'safe_area':
                # 安全區域模式
                if self._is_near_forbidden(rel_pos):
                    print("🚫 在禁止區域，緊急回歸")
                    return self._emergency_return_to_safe_area(rel_pos)

                if not self._is_in_safe_area(rel_pos):
                    print("⚠️ 不在安全區域，回歸中...")
                    return self._return_to_safe_area(rel_pos)

                # 在安全區域內檢測怪物
                has_target = False
                if frame is not None:
                    has_target = self._update_monster_targeting_in_safe_area(frame, rel_pos)
                    print(f"  - 是否有目標: {has_target}")

                # 安全區域內的戰鬥邏輯
                if self.auto_hunt_mode != "off" and self._is_in_safe_area(rel_pos):
                    current_time = time.time()
                    attack_interval = self.hunt_settings.get('attack_cooldown', 1.5)
                    
                    if current_time - self.last_attack_time >= attack_interval:
                        if has_target:
                            print("🎯 嘗試攻擊目標")
                            if self._execute_combat_sequence():
                                self.last_attack_time = current_time
                                print("⚔️ 安全區域內攻擊成功")
                        else:
                            print("❌ 沒有可攻擊的目標")
                    else:
                        print(f"⏳ 攻擊冷卻中: {attack_interval - (current_time - self.last_attack_time):.1f}秒")

                # 安全區域內移動邏輯
                if self.auto_hunt_mode != "off":
                    if has_target:
                        print("🏃 追擊目標")
                        return self._safe_area_chase_target(rel_pos)
                    else:
                        print("🚶 巡邏中")
                        return self._safe_area_patrol(rel_pos)
                
            else:
                # 路徑點模式
                has_target = False
                if frame is not None:
                    has_target = self._update_monster_targeting(frame, rel_pos)
                    print(f"  - 是否有目標: {has_target}")
                
                if self.auto_hunt_mode != "off":
                    current_time = time.time()
                    hunt_attack_interval = self.hunt_settings.get('attack_cooldown', 0.5)
                    
                    if current_time - self.last_attack_time >= hunt_attack_interval:
                        if has_target:
                            print("🎯 嘗試攻擊目標")
                            if self._execute_combat_sequence():
                                self.last_attack_time = current_time
                                print("⚔️ 執行攻擊")
                        else:
                            print("❌ 沒有可攻擊的目標")
                    else:
                        print(f"⏳ 攻擊冷卻中: {hunt_attack_interval - (current_time - self.last_attack_time):.1f}秒")
                    
                    if self.waypoint_system:
                        return self._handle_waypoint_movement(rel_pos)

        except Exception as e:
            print(f"⚠️ 戰鬥系統更新失敗: {e}")
            import traceback
            traceback.print_exc()

    def _handle_waypoint_movement(self, current_pos):
        """修正版：根據戰鬥模式選擇移動邏輯"""
        try:
            combat_mode = self.hunt_settings.get('combat_mode', 'waypoint')
            
            if combat_mode == 'safe_area':
                # ✅ 1. 強制檢查是否在禁止區域
                if self._is_near_forbidden(current_pos):
                    print(f"🚫 角色在禁止區域，執行緊急回歸")
                    return self._emergency_return_to_safe_area(current_pos)
                
                # ✅ 2. 檢查是否在安全區域內
                if not self._is_in_safe_area(current_pos):
                    print(f"⚠️ 角色不在安全區域，回歸安全區域")
                    return self._return_to_safe_area(current_pos)
                
                # ✅ 3. 如果有怪物目標，在安全區域內追擊
                if hasattr(self, 'auto_hunt_target') and self.auto_hunt_target:
                    return self._safe_area_chase_target(current_pos)
                
                # ✅ 4. 沒有目標時，在安全區域內巡邏
                return self._safe_area_patrol(current_pos)
                
            else:
                # 路徑點模式
                print("執行路徑移動")
                # 檢查 current_pos 是否接近 forbidden
                forbidden_pos = self._is_near_forbidden(current_pos, return_pos=True)
                if forbidden_pos:
                    if self._is_same_position(current_pos, forbidden_pos):
                        print(f"🚫 已到禁止區域: {current_pos} (forbidden: {forbidden_pos})")
                    else:
                        print(f"⚠️ 角色接近 forbidden 區域: {current_pos} (forbidden: {forbidden_pos})")
                
                # 獲取下一個路徑點
                next_waypoint = self.waypoint_system.get_next_waypoint(current_pos)
                if not next_waypoint:
                    print("❌ 沒有可用的路徑點")
                    self.last_planned_path = None
                    return
                
                # 使用 A* 算法尋找路徑
                path = self.grid_utils.find_path(current_pos, next_waypoint['pos'])
                self.last_planned_path = path
                if not path:
                    print("❌ 無法找到可行路徑")
                    return
                
                # 獲取下一個路徑點
                next_pos = path[1] if len(path) > 1 else next_waypoint['pos']
                forbidden_next = self._is_near_forbidden(next_pos, return_pos=True)
                if forbidden_next:
                    if self._is_same_position(next_pos, forbidden_next):
                        print(f"🚫 下一步已到禁止區域: {next_pos} (forbidden: {forbidden_next})")
                    else:
                        print(f"⚠️ 下一步接近 forbidden 區域: {next_pos} (forbidden: {forbidden_next})")
                
                direction = self._get_direction_to_target(current_pos, next_pos)
                if direction:
                    print(f"🧭 移動方向: {direction}")
                    return self._move_in_direction(direction)
            
        except Exception as e:
            print(f"❌ 移動處理失敗: {e}")
            return False

    def _return_to_safe_area(self, current_pos):
        """回歸安全區域"""
        try:
            print(f"🔄 開始回歸安全區域")
            
            # 尋找最近的安全位置
            nearest_safe = self._find_nearest_safe_position(current_pos)
            
            if nearest_safe:
                direction = self._get_direction_to_target(current_pos, nearest_safe)
                if direction:
                    print(f"🚶 回歸方向: {direction}")
                    return self._move_in_direction(direction, duration=0.5)
            
            # 如果找不到安全位置，使用預設方向
            print(f"⚠️ 找不到安全位置，使用預設方向")
            return self._move_in_direction("left", duration=0.3)
            
        except Exception as e:
            print(f"❌ 回歸安全區域失敗: {e}")
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
            print(f"❌ 尋找最近安全位置失敗: {e}")
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

    def _execute_combat_sequence(self):
        """✅ 改進版戰鬥序列"""
        print("⚔️ 開始執行戰鬥序列")
        
        if not self.controller:
            print("❌ 控制器未初始化")
            self._init_adb()
            return False
            
        if not self.controller.is_connected:
            print("❌ 控制器未連接")
            self.controller.reconnect()
            if not self.controller.is_connected:
                return False
        
        print(f"🔍 控制器狀態: {self.controller is not None}, 連接狀態: {self.controller.is_connected}")
        
        try:
            # 檢查是否有目標
            if not self.auto_hunt_target:
                print("❌ 沒有攻擊目標")
                return False
                
            # 檢查目標資訊
            target_info = self.auto_hunt_target
            if not isinstance(target_info, dict):
                print(f"❌ 無效的目標資訊: {target_info}")
                return False
                
            print(f"🎯 目標資訊: {target_info.get('name', '未知')}, 信心度: {target_info.get('confidence', 0):.3f}")
            
            # 獲取當前技能
            current_skill = self.skill_rotation[self.current_skill_index]
            print(f"🎯 使用技能: {current_skill}")
            
            # 執行攻擊
            if current_skill == 'attack':
                print("⚔️ 執行普通攻擊")
                success = self.controller.attack()
            else:
                # 使用技能
                print(f"✨ 執行技能: {current_skill}")
                success = self.controller.use_skill(current_skill)
            
            if success:
                print(f"✅ {current_skill} 執行成功")
                # 更新技能索引
                self.current_skill_index = (self.current_skill_index + 1) % len(self.skill_rotation)
                return True
            else:
                print(f"❌ {current_skill} 執行失敗")
                return False
                
        except Exception as e:
            print(f"❌ 戰鬥序列錯誤: {e}")
            import traceback
            traceback.print_exc()
            return False

    def _move_in_direction(self, direction, duration=0.5):
        """✅ 修正版：使用正確的移動方法"""
        try:
            if not self.controller or not self.controller.is_connected:
                print("❌ 控制器未連接")
                return False
            
            # 使用 move 方法而不是 press_key
            success = self.controller.move(direction, duration)
            
            if success:
                print(f"✅ 移動成功: {direction} ({duration}秒)")
            else:
                print(f"❌ 移動失敗: {direction}")
            
            return success
            
        except Exception as e:
            print(f"❌ 移動執行失敗: {e}")
            return False

    def _get_direction_to_target(self, current_pos, target_pos):
        """計算移動方向（只在必要時進行垂直移動）"""
        dx = target_pos[0] - current_pos[0]
        dy = target_pos[1] - current_pos[1]
        
        # 只在 y 軸差異大於 5% 時才進行垂直移動
        if abs(dy) > 0.05:  # 提高閾值到 5%
            return 'down' if dy > 0 else 'up'
        
        # 否則只進行水平移動
        return 'right' if dx > 0 else 'left'

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
            print(f"🎯 已選擇目標: {nearest_monster.get('name', '未知')}")
            return True
            
        except Exception as e:
            print(f"❌ 怪物檢測失敗: {e}")
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

            # ✅ 修正：不檢查怪物是否在安全區域，只檢查攻擊距離
            valid_monsters = []
            for monster in monsters:
                # 只需要基本的怪物資訊驗證
                if monster.get('confidence', 0) >= 0.08:  # 最低信心度
                    valid_monsters.append(monster)

            if not valid_monsters:
                self.auto_hunt_target = None
                return False

            # 選擇信心度最高的怪物
            best_monster = max(valid_monsters, key=lambda m: m.get('confidence', 0))
            
            self.auto_hunt_target = best_monster
            print(f"🎯 已選擇目標: {best_monster.get('name', '未知')} 信心度:{best_monster.get('confidence', 0):.3f}")
            return True

        except Exception as e:
            print(f"❌ 安全區域怪物檢測失敗: {e}")
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
        """設置自動狩獵模式"""
        try:
            self.auto_hunt_mode = mode
            print(f"✅ 已設置自動狩獵模式: {mode}")
            return True
        except Exception as e:
            print(f"❌ 設置自動狩獵模式失敗: {e}")
            return False

    def set_hunt_settings(self, settings):
        """設置狩獵設定"""
        try:
            self.hunt_settings.update(settings)
            print(f"✅ 已更新狩獵設定: {settings}")
            return True
            
        except Exception as e:
            print(f"❌ 更新狩獵設定失敗: {e}")
            return False

    def _handle_combat(self, current_pos, game_frame):
        """✅ 保持原有戰鬥邏輯"""
        try:
            current_time = time.time()
            
            # 檢查攻擊間隔
            if current_time - self.last_attack_time < self.attack_interval:
                print(f"⏳ 攻擊冷卻中: {self.attack_interval - (current_time - self.last_attack_time):.1f}秒")
                return
            
            print("🔍 檢查戰鬥狀態...")
            
            # 更新怪物檢測和目標選擇
            if game_frame is not None:
                print("🔍 更新怪物目標...")
                self._update_monster_targeting(game_frame, current_pos)
            
            # 執行戰鬥序列
            if self.auto_hunt_target:
                print("🎯 發現目標，開始攻擊")
                if self._execute_combat_sequence():
                    self.last_attack_time = current_time
                    print("✅ 攻擊序列執行完成")
                else:
                    print("❌ 攻擊序列執行失敗")
            else:
                print("⚠️ 沒有發現目標")
                
        except Exception as e:
            print(f"❌ 戰鬥處理失敗: {e}")
            import traceback
            traceback.print_exc()

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

    def _is_in_safe_area(self, position):
        """檢查是否在安全區域內"""
        try:
            if not hasattr(self.waypoint_system, 'area_grid'):
                return True
            
            # 檢查當前位置是否在walkable區域內
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
                        
                        # 檢查是否在安全區域範圍內（增加容許範圍）
                        if (abs(position[0] - safe_x) < 0.05 and 
                            abs(position[1] - safe_y) < 0.05):
                            print(f"✅ 在安全區域內: 位置({position[0]:.3f}, {position[1]:.3f}) 安全點({safe_x:.3f}, {safe_y:.3f})")
                            return True
                    except:
                        continue
            
            print(f"⚠️ 不在安全區域內: 位置({position[0]:.3f}, {position[1]:.3f})")
            return False
            
        except Exception as e:
            print(f"❌ 安全區域檢查失敗: {e}")
            return True

    def _safe_area_chase_target(self, current_pos):
        """在安全區域內追擊目標"""
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
                print(f"🎯 目標超出安全追擊範圍，放棄追擊")
                self.auto_hunt_target = None
                return self._safe_area_patrol(current_pos)
            
            # ✅ 計算安全的移動位置
            safe_move_pos = self._calculate_safe_approach_position(current_pos, rel_target_pos)
            
            if safe_move_pos and self._is_in_safe_area(safe_move_pos):
                direction = self._get_direction_to_target(current_pos, safe_move_pos)
                if direction:
                    print(f"🎯 安全追擊移動: {direction}")
                    return self._move_in_direction(direction, duration=0.3)
            
            # 無法安全接近，原地攻擊
            print(f"🎯 目標在範圍內，原地攻擊")
            return True
            
        except Exception as e:
            print(f"❌ 安全追擊失敗: {e}")
            return False

    def _safe_area_patrol(self, current_pos):
        """在安全區域內巡邏"""
        try:
            # ✅ 尋找安全區域內的巡邏目標
            patrol_target = self._find_safe_patrol_target(current_pos)
            
            if patrol_target:
                direction = self._get_direction_to_target(current_pos, patrol_target)
                if direction:
                    print(f"🚶 安全區域巡邏: {direction}")
                    return self._move_in_direction(direction, duration=0.5)
            
            # 沒有巡邏目標，保持原位
            print(f"🛡️ 安全區域待命")
            return True
            
        except Exception as e:
            print(f"❌ 安全巡邏失敗: {e}")
            return False

    def _find_safe_patrol_target(self, current_pos):
        """尋找安全的巡邏目標"""
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
            
            # 尋找適中距離的巡邏點
            suitable_targets = []
            for pos in safe_positions:
                distance = self._calculate_distance(current_pos, pos)
                if 0.02 < distance < 0.08:  # 適中的巡邏距離
                    suitable_targets.append(pos)
            
            if suitable_targets:
                # 選擇最接近的適合目標
                return min(suitable_targets, 
                          key=lambda p: self._calculate_distance(current_pos, p))
            
            return None
            
        except Exception as e:
            print(f"❌ 巡邏目標搜尋失敗: {e}")
            return None

    def _emergency_return_to_safe_area(self, current_pos):
        """緊急回歸安全區域"""
        try:
            print(f"🚨 執行緊急回歸安全區域")
            
            # 尋找最近的安全位置
            nearest_safe = self._find_nearest_safe_position(current_pos)
            
            if nearest_safe:
                direction = self._get_direction_to_target(current_pos, nearest_safe)
                if direction:
                    print(f"🏃 緊急回歸方向: {direction}")
                    return self._move_in_direction(direction, duration=0.8)
            
            # 如果找不到安全位置，向預設方向移動
            print(f"🔄 使用預設安全方向")
            return self._move_in_direction("left", duration=0.5)
            
        except Exception as e:
            print(f"❌ 緊急回歸失敗: {e}")
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

def check_auto_combat_status(ro_helper):
    """檢查自動戰鬥狀態"""
    if hasattr(ro_helper, 'auto_combat'):
        combat = ro_helper.auto_combat
        print(f"⚔️ 自動戰鬥啟用: {combat.is_enabled}")
        print(f"🎯 自動瞄準: {combat.auto_target_enabled}")
        print(f"🔍 打怪模式: {combat.auto_hunt_mode}")
        # 檢查控制器
        if combat.controller:
            print(f"🎮 控制器連接: {combat.controller.is_connected}")
            print(f"📱 設備ID: {getattr(combat.controller, 'device_id', None)}")
        else:
            print("❌ 戰鬥系統沒有控制器")
            # 嘗試重新初始化
            combat._init_adb()
    else:
        print("❌ 自動戰鬥系統不存在")


def reinitialize_control_system(ro_helper):
    """重新初始化控制系統"""
    try:
        print("🔄 重新初始化控制系統...")
        # 1. 確保ADB連接
        if hasattr(ro_helper, 'auto_combat'):
            ro_helper.auto_combat.controller = None
            ro_helper.auto_combat._init_adb()
            if ro_helper.auto_combat.controller and ro_helper.auto_combat.controller.is_connected:
                print("✅ 控制器重新初始化成功")
                return True
            else:
                print("❌ 控制器重新初始化失敗")
        else:
            print("❌ ro_helper 沒有 auto_combat")
        return False
    except Exception as e:
        print(f"❌ 重新初始化失敗: {e}")
        return False