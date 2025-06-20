# modules/simple_adb.py - 純粹的角色操作邏輯

import time
import os
import cv2
from includes.adb_utils import ADBUtils

class SimpleADB:
    """✅ 楓之谷專用角色操作控制器 - 專注於遊戲邏輯"""
    
    def __init__(self, config=None):
        # ✅ 只保存設備ID，所有ADB操作都通過ADBUtils
        self.device_id = None
        self.is_connected = False
        
        # ✅ 楓之谷專用按鍵映射（遊戲邏輯）
        self.movement_keys = {
            'left': 'KEYCODE_DPAD_LEFT',
            'right': 'KEYCODE_DPAD_RIGHT',
            'up': 'KEYCODE_DPAD_UP',
            'down': 'KEYCODE_DPAD_DOWN',
            'jump': 'KEYCODE_ALT_LEFT',
        }
        
        # ✅ 簡化攻擊按鍵映射
        self.attack_key = 'KEYCODE_CTRL_LEFT'  # 左Ctrl鍵
        
        # ✅ 技能按鍵映射
        self.skill_keys = {
            'skill1': 'KEYCODE_1',
        }
        
        # ✅ 楓之谷專用組合技能
        self.combo_actions = {
            'jump_left': ['KEYCODE_DPAD_LEFT', 'KEYCODE_ALT_LEFT'],
            'jump_right': ['KEYCODE_DPAD_RIGHT', 'KEYCODE_ALT_LEFT'],
            'rope_climb_up': ['KEYCODE_DPAD_UP', 'KEYCODE_ALT_LEFT'],
            'rope_climb_down': ['KEYCODE_DPAD_DOWN', 'KEYCODE_ALT_LEFT'],
        }
        
        # 初始化連接
        self._init_connection()
        
        # 初始化畫面捕獲器
        try:
            from modules.simple_capturer import SimpleCapturer
            self.capturer = SimpleCapturer(config)
        except Exception as e:
            print(f"❌ 初始化畫面捕獲器失敗: {e}")
            self.capturer = None
        
        print("🍁 楓之谷角色操作控制器已初始化")

    def _init_connection(self):
        """簡化版：完全依賴ADBUtils"""
        self.device_id = ADBUtils.ensure_connection()
        self.is_connected = bool(self.device_id)

    def move(self, direction: str, duration: float = None) -> bool:
        """改進版移動方法"""
        if not self.is_connected:
            self.reconnect()
            if not self.is_connected:
                return False

        if direction not in self.movement_keys:
            return False

        if duration is None:
            duration = 0.5

        keycode = self.movement_keys[direction]

        try:
            if duration >= 0.8:
                # 長距離移動：使用長按
                success = ADBUtils.send_longpress_keyevent(self.device_id, keycode)
            else:
                # 短距離移動：連續短按
                click_count = max(1, int(duration / 0.1))
                success = True

                for i in range(click_count):
                    if not ADBUtils.send_keyevent(self.device_id, keycode):
                        success = False
                        break
                    time.sleep(0.1)

            return success

        except Exception as e:
            print(f"❌ 移動失敗: {e}")
            return False

    def attack(self) -> bool:
        """✅ 改進版：長按攻擊"""
        if not self.is_connected:
            print("❌ 設備未連接，無法攻擊")
            return False
        
        try:
            # 使用 A 鍵作為攻擊鍵
            print("🎯 發送長按攻擊...")
            
            # 長按按鍵
            success = ADBUtils.send_longpress_keyevent(self.device_id, 'KEYCODE_A')
            if not success:
                print("❌ 長按攻擊失敗")
                return False
                
            # 等待按鍵持續時間
            time.sleep(1.0)  # 增加長按時間到 1 秒
            
            print("✅ 長按攻擊完成")
            return True
            
        except Exception as e:
            print(f"❌ 攻擊失敗: {e}")
            return False

    def use_skill(self, skill_number: int) -> bool:
        """✅ 使用技能"""
        skill_key = f'skill{skill_number}'
        
        if skill_key not in self.skill_keys:
            print(f"❌ 技能{skill_number}未定義")
            return False
        
        if not self.is_connected:
            print("❌ 設備未連接，無法使用技能")
            return False
        
        success = ADBUtils.send_keyevent(self.device_id, self.skill_keys[skill_key])
        
        if success:
            print(f"✨ 使用技能{skill_number}")
        else:
            print(f"❌ 技能{skill_number}使用失敗")
        
        return success

    def jump(self, direction: str = None) -> bool:
        """✅ 角色跳躍"""
        if not self.is_connected:
            print("❌ 設備未連接，無法跳躍")
            return False
        
        if direction is None:
            # 原地跳躍
            success = ADBUtils.send_keyevent(self.device_id, self.movement_keys['jump'])
            print("🦘 原地跳躍")
        elif direction in ['left', 'right']:
            # 方向跳躍
            combo_key = f'jump_{direction}'
            success = self._execute_combo_action(combo_key)
            print(f"🦘 {direction}方向跳躍")
        else:
            print(f"❌ 無效的跳躍方向: {direction}")
            return False
        
        return success

    def rope_climb(self, direction: str) -> bool:
        """✅ 繩索攀爬"""
        if not self.is_connected:
            print("❌ 設備未連接，無法攀爬")
            return False
        
        if direction == 'up':
            combo_key = 'rope_climb_up'
            print("🧗 攀爬繩索向上")
        elif direction == 'down':
            combo_key = 'rope_climb_down'
            print("🧗 順繩索向下")
        else:
            print(f"❌ 無效的攀爬方向: {direction}")
            return False
        
        return self._execute_combo_action(combo_key)

    def _execute_combo_action(self, combo_key: str) -> bool:
        """✅ 執行組合動作"""
        if combo_key not in self.combo_actions:
            print(f"❌ 未定義的組合動作: {combo_key}")
            return False
        
        keycodes = self.combo_actions[combo_key]
        
        try:
            # 依序執行組合按鍵
            success = True
            for i, keycode in enumerate(keycodes):
                if not ADBUtils.send_keyevent(self.device_id, keycode):
                    success = False
                    break
                
                # 組合鍵之間的短暫延遲
                if i < len(keycodes) - 1:
                    time.sleep(0.05)
            
            if success:
                print(f"✅ 組合動作成功: {combo_key}")
            else:
                print(f"❌ 組合動作失敗: {combo_key}")
            
            return success
            
        except Exception as e:
            print(f"❌ 組合動作執行錯誤: {e}")
            return False

    def reconnect(self) -> bool:
        """✅ 重新連接"""
        print("🔄 重新連接角色控制器...")
        self.device_id = ADBUtils.ensure_connection()
        self.is_connected = bool(self.device_id)
        
        if self.is_connected:
            print(f"✅ 重新連接成功: {self.device_id}")
        else:
            print("❌ 重新連接失敗")
        
        return self.is_connected

    def get_status(self) -> dict:
        """✅ 獲取控制器狀態"""
        connection_info = ADBUtils.get_connection_info()
        
        return {
            'device_id': self.device_id,
            'is_connected': self.is_connected,
            'adb_path': connection_info['adb_path'],
            'adb_exists': connection_info['adb_exists'],
            'movement_keys_count': len(self.movement_keys),
            'skill_keys_count': len(self.skill_keys),
            'combo_actions_count': len(self.combo_actions)
        }

    def click_ui_sequence(self):
        """依序點擊MenuUi->TeamUi->NewUi"""
        if not self.is_connected:
            print("❌ ADB未連接")
            return False
            
        try:
            # 獲取螢幕截圖
            frame = self.capturer.grab_frame()
            if frame is None:
                print("❌ 無法獲取螢幕截圖")
                return False
                
            # 定義模板路徑
            templates_dir = "templates/MainScreen"
            menu_path = os.path.join(templates_dir, "MenuUi.png")
            team_path = os.path.join(templates_dir, "TeamUi.png")
            newui_path = os.path.join(templates_dir, "NewUi.png")
            
            # 點擊MenuUi
            print("🖱️ 尋找MenuUi...")
            menu_loc = self._find_template_location(frame, menu_path)
            if menu_loc:
                x, y = menu_loc
                print(f"✅ 找到MenuUi，點擊位置: ({x}, {y})")
                ADBUtils.tap_screen(self.device_id, x, y)
                time.sleep(1)
            else:
                print("❌ 未找到MenuUi")
                return False
                
            # 更新螢幕截圖
            frame = self.capturer.grab_frame()
            if frame is None:
                return False
                
            # 點擊TeamUi
            print("🖱️ 尋找TeamUi...")
            team_loc = self._find_template_location(frame, team_path)
            if team_loc:
                x, y = team_loc
                print(f"✅ 找到TeamUi，點擊位置: ({x}, {y})")
                ADBUtils.tap_screen(self.device_id, x, y)
                time.sleep(1)
            else:
                print("❌ 未找到TeamUi")
                return False
                
            # 更新螢幕截圖
            frame = self.capturer.grab_frame()
            if frame is None:
                return False
                
            # 點擊NewUi
            print("🖱️ 尋找NewUi...")
            newui_loc = self._find_template_location(frame, newui_path)
            if newui_loc:
                x, y = newui_loc
                print(f"✅ 找到NewUi，點擊位置: ({x}, {y})")
                ADBUtils.tap_screen(self.device_id, x, y)
                time.sleep(1)
            else:
                print("❌ 未找到NewUi")
                return False
                
            print("✅ UI序列點擊完成")
            return True
            
        except Exception as e:
            print(f"❌ UI序列點擊失敗: {e}")
            return False
            
    def _find_template_location(self, frame, template_path, threshold=0.7):
        """使用模板匹配找到UI元素位置"""
        try:
            template = cv2.imread(template_path, cv2.IMREAD_GRAYSCALE)
            if template is None:
                print(f"❌ 無法讀取模板: {template_path}")
                return None
                
            frame_gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            result = cv2.matchTemplate(frame_gray, template, cv2.TM_CCOEFF_NORMED)
            min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
            
            if max_val >= threshold:
                h, w = template.shape[:2]
                center_x = max_loc[0] + w // 2
                center_y = max_loc[1] + h // 2
                return (center_x, center_y)
            return None
            
        except Exception as e:
            print(f"❌ 模板匹配失敗: {e}")
            return None

    def click_ui(self, x, y, w=None, h=None):
        """直接點擊指定座標，可選寬高，會點擊中心點"""
        if not self.is_connected:
            print("❌ ADB未連接")
            return False
        cx = x + (w // 2 if w else 0)
        cy = y + (h // 2 if h else 0)
        print(f"🖱️ 點擊座標: ({cx}, {cy})")
        return ADBUtils.tap_screen(self.device_id, int(cx), int(cy))
