# main.py - 修正版

import sys
import os
import time
import threading
import yaml

# 只導入必要模組
from modules.simple_capturer import SimpleCapturer
from modules.coordinate import TemplateMatcherTracker
from modules.auto_combat_simple import SimpleCombat
from modules.waypoint_editor import WaypointEditor
from modules.simple_waypoint_system import SimpleWaypointSystem

class MapleStoryHelper:
    """簡化版 MapleStory Helper - AutoMaple 風格"""
    
    def __init__(self, config_path="configs/bluestacks.yaml"):
        print("🚀 啟動簡化版 MapleStory Helper...")
        
        # 載入設定
        self.config = self._load_config(config_path)
        
        # 基本狀態
        self.is_enabled = False
        self._running = False
        
        # 怪物檢測器
        from includes.simple_template_utils import monster_detector
        self.monster_detector = monster_detector
        
        # ✅ 添加路徑點系統
        self.waypoint_system = SimpleWaypointSystem()
        self._init_waypoint_system_with_auto_load()
        print("🗺️ 路徑點系統已初始化")
        
        # 初始化核心組件
        self._init_core_components()
        
        # ✅ 初始化編輯器（但不立即顯示）
        self.waypoint_editor = None
    
    def _init_core_components(self):
        """只初始化核心組件"""
        try:
            # 畫面捕獲
            self.capturer = SimpleCapturer(self.config)
            
            # 角色追蹤
            self.tracker = TemplateMatcherTracker(self.config)
            
            # 簡單戰鬥
            self.auto_combat = SimpleCombat()
            
            # 戰鬥系統
            self.auto_combat.set_waypoint_system(self.waypoint_system)

            self.auto_combat.diagnose_waypoint_system()
            
            print("✅ 核心組件初始化完成")
            
        except Exception as e:
            print(f"❌ 初始化失敗: {e}")
            raise
    
    def open_waypoint_editor(self):
        """✅ 修正版：添加關閉回調確保數據同步"""
        try:
            if self.waypoint_editor is None:
                self.waypoint_editor = WaypointEditor(
                    waypoint_system=self.waypoint_system,
                    tracker=self.tracker
                )
            
            self.waypoint_editor.create_editor_window()
            print("✅ 路徑點編輯器已開啟（數據已同步）")
            
        except Exception as e:
            print(f"❌ 開啟編輯器失敗: {e}")

    def _load_config(self, config_path):
        """載入設定"""
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f)
        except Exception:
            return {"window_name": "BlueStacks App Player"}
    
    def get_waypoint_info(self):
        """獲取路徑點資訊"""
        return {
            'waypoint_count': len(self.waypoint_system.waypoints),
            'current_target': self.waypoint_system.current_target_index,
            'waypoint_system': self.waypoint_system
        }

    def start(self):
        """啟動主循環"""
        if self._running:
            return
        
        self.is_enabled = True
        self._running = True
        self._thread = threading.Thread(target=self._simple_main_loop, daemon=True)
        self._thread.start()
        print("✅ 簡化版主循環已啟動")
    
    def _simple_main_loop(self):
        """簡化的主循環"""
        print("▶️ 簡化主循環開始")
        
        while self._running:
            try:
                # 1. 捕獲完整畫面
                frame = self.capturer.grab_frame()
                if frame is None:
                    time.sleep(0.1)
                    continue

                # 2. 角色追蹤
                if self.is_enabled:
                    rel_pos = self.tracker.track_player(frame)

                # 3. ✅ 添加戰鬥系統調試
                if self.auto_combat.is_enabled:
                    print(f"🔄 調用auto_combat.update - 位置: {rel_pos}")
                    self.auto_combat.update(rel_pos, frame)

                # 4. 控制頻率
                time.sleep(0.05)
                
            except Exception as e:
                print(f"主循環錯誤: {e}")
                time.sleep(1.0)
    
    def stop(self):
        """停止程式"""
        self.is_enabled = False
        self._running = False
        
        if hasattr(self, 'auto_combat'):
            self.auto_combat.stop()
        
        print("✅ 程式已停止")
    
    def toggle_tracking(self):
        """切換追蹤"""
        self.is_enabled = not self.is_enabled
        return self.is_enabled
    
    def toggle_combat(self):
        """切換戰鬥"""
        if hasattr(self, 'auto_combat'):
            if self.auto_combat.is_enabled:
                self.auto_combat.stop()
                return False
            else:
                self.auto_combat.start()
                return True
        return False
    
    def get_status(self):
        """獲取狀態"""
        return {
            'tracking_enabled': self.is_enabled,
            'combat_enabled': getattr(self.auto_combat, 'is_enabled', False),
            'adb_connected': (
                self.auto_combat.controller.is_connected
                if hasattr(self.auto_combat, 'controller') and self.auto_combat.controller
                else False
            )
        }

    def start_area_movement_test(self):
        """開始區域移動測試"""
        if not self.auto_combat.waypoint_system:
            print("❌ waypoint_system未整合")
            return
        
        print("🧪 開始區域移動測試...")
        print(f"📍 當前area_grid數量: {len(getattr(self.auto_combat.waypoint_system, 'area_grid', {}))}")
        
        # 啟動自動戰鬥（包含移動邏輯）
        self.auto_combat.start()
        
        # 設定測試目標
        if self.auto_combat.waypoint_system.waypoints:
            target = self.auto_combat.waypoint_system.waypoints[0]['pos']
            self.auto_combat.current_target = target
            print(f"🎯 設定測試目標: {target}")

    def _init_waypoint_system_with_auto_load(self):
        """✅ 改善的路徑系統初始化"""
        try:
            # 獲取可用的地圖檔案
            initial_file = self.waypoint_system.get_initial_map_file()
            
            if initial_file:
                print(f"🔄 自動載入初始地圖: {initial_file}")
                success = self.waypoint_system.load_specific_map(initial_file)
                
                if success:
                    print(f"✅ 初始地圖載入成功")
                else:
                    print(f"❌ 初始地圖載入失敗")
            else:
                print("⚠️ 沒有找到可用的地圖檔案，使用預設設定")
                
        except Exception as e:
            print(f"❌ 路徑系統初始化失敗: {e}")

def main():
    """主程式 - 添加編輯路徑功能"""
    print("🎮 MapleStory Helper - 怪物檢測 + 路徑編輯版本")
    
    try:
        # 創建應用
        app = MapleStoryHelper()
        
        # ✅ 檢查路徑點系統
        print("\n🗺️ 檢查路徑點系統...")
        waypoint_info = app.get_waypoint_info()
        print(f"📍 路徑點數量: {waypoint_info['waypoint_count']}")
        
        # ✅ 創建主要GUI，並傳入app供編輯器使用
        from modules.simple_gui_monster_display import MonsterDetectionGUI
        gui = MonsterDetectionGUI(app)
        
        # ✅ 添加編輯路徑按鈕到GUI（如果GUI支援）
        try:
            # 檢查GUI是否有添加按鈕的方法
            if hasattr(gui, 'add_waypoint_button'):
                gui.add_waypoint_button("🗺️ 編輯路徑", app.open_waypoint_editor)
            else:
                print("💡 可使用快捷鍵 Ctrl+W 開啟路徑編輯器")
                
                # ✅ 添加鍵盤快捷鍵
                def on_key_press(event):
                    if event.keysym == 'w' and event.state & 4:  # Ctrl+W
                        app.open_waypoint_editor()
                
                if hasattr(gui, 'root'):
                    gui.root.bind('<Key>', on_key_press)
                    gui.root.focus_set()
                    
        except Exception as e:
            print(f"⚠️ 添加編輯按鈕失敗: {e}")
        
        # 啟動應用
        app.start()
        
        # 運行GUI
        gui.run()
        
    except Exception as e:
        print(f"❌ 程式錯誤: {e}")
        import traceback
        traceback.print_exc()
    finally:
        try:
            app.stop()
        except:
            pass

if __name__ == "__main__":
    main()