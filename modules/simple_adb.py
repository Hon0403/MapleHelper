# modules/simple_adb.py - 純粹的角色操作邏輯

import time
from includes.adb_utils import ADBUtils

class SimpleADB:
    """✅ 楓之谷專用角色操作控制器 - 專注於遊戲邏輯"""
    
    def __init__(self):
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
        
        self.skill_keys = {
            'attack': 'KEYCODE_CTRL_LEFT',
            'skill1': 'KEYCODE_CTRL_LEFT',
            'skill2': 'KEYCODE_CTRL_LEFT',
            'skill3': 'KEYCODE_CTRL_LEFT',
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
        
        print("🍁 楓之谷角色操作控制器已初始化")

    def _init_connection(self):
        """簡化版：完全依賴ADBUtils"""
        self.device_id = ADBUtils.ensure_connection()
        self.is_connected = bool(self.device_id)

    def move(self, direction: str, duration: float = None) -> bool:
        """✅ 基於搜索結果[7]的動態移動時間"""
        if not self.is_connected:
            print("❌ 設備未連接，無法移動")
            return False

        if direction not in self.movement_keys:
            print(f"❌ 不支援的移動方向: {direction}")
            return False

        # ✅ 如果沒有指定duration，使用預設短時間
        if duration is None:
            duration = 0.5  # 預設短移動

        keycode = self.movement_keys[direction]
        print(f"🏃 角色移動: {direction} (持續{duration:.2f}秒)")

        # ✅ 基於搜索結果[7]的精確移動控制
        if duration >= 0.8:
            success = ADBUtils.send_longpress_keyevent(self.device_id, keycode)
            if success:
                print(f"⏰ 長按移動開始: {direction}")
                time.sleep(duration)
                print(f"✅ 長按移動結束: {direction}")
            else:
                print(f"❌ 長按移動失敗: {direction}")
        else:
            # ✅ 短距離移動：多次短按
            click_count = max(1, int(duration / 0.1))
            success = True
            for i in range(click_count):
                if not ADBUtils.send_keyevent(self.device_id, keycode):
                    success = False
                    break
                time.sleep(0.1)
            
            if success:
                print(f"✅ 短距移動成功: {direction} ({duration:.2f}秒)")
            else:
                print(f"❌ 短距移動失敗: {direction}")

        return success

    def attack(self) -> bool:
        """✅ 角色攻擊"""
        if not self.is_connected:
            print("❌ 設備未連接，無法攻擊")
            return False
        
        success = ADBUtils.send_keyevent(self.device_id, self.skill_keys['attack'])
        
        if success:
            print("⚔️ 執行攻擊")
        else:
            print("❌ 攻擊失敗")
        
        return success

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
