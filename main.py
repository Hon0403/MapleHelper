# main.py - 修正版

import sys
import os
import time
import threading
import yaml
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt
# 只導入必要模組
from modules.simple_capturer import SimpleCapturer
from modules.coordinate import TemplateMatcherTracker
from modules.auto_combat_simple import SimpleCombat
from modules.waypoint_editor import WaypointEditor
from modules.simple_waypoint_system import SimpleWaypointSystem
from modules.simple_adb import SimpleADB
from modules.health_mana_detector import HealthManaDetector


class MapleStoryHelper:
    """簡化版 MapleStory Helper - AutoMaple 風格"""
    
    def __init__(self, config_path="configs/bluestacks.yaml"):
        print("🚀 啟動簡化版 MapleStory Helper...")
        
        # 先載入設定
        self.config = self._load_config(config_path)
        
        # 初始化 ADB 控制器，傳入 config
        self.adb = SimpleADB(self.config)
        
        # 基本狀態
        self.is_enabled = False
        self._running = False
        
        # 怪物檢測器
        from includes.simple_template_utils import monster_detector
        self.monster_detector = monster_detector
        
        # 血條檢測器
        self.health_detector = HealthManaDetector()
        self.last_health_check = 0
        self.health_check_interval = 0.5  # 每0.5秒檢查一次
        
        # ✅ 添加路徑點系統
        self.waypoint_system = SimpleWaypointSystem()
        self._init_waypoint_system_with_auto_load()
        print("🗺️ 路徑點系統已初始化")
        
        # 初始化核心組件
        self._init_core_components()
        
        # ✅ 初始化編輯器（但不立即顯示）
        self.waypoint_editor = None
    
    def _init_core_components(self):
        """只初始化核心組件 - 改進版"""
        try:
            # 畫面捕獲
            print("🔄 初始化畫面捕獲...")
            self.capturer = SimpleCapturer(self.config)
            
            # 角色追蹤
            print("🔄 初始化角色追蹤...")
            self.tracker = TemplateMatcherTracker(self.config, capturer=self.capturer)
            
            # 簡單戰鬥
            print("🔄 初始化戰鬥系統...")
            self.auto_combat = SimpleCombat()
            
            # ✅ 更詳細的錯誤檢查
            if not self.waypoint_system:
                raise RuntimeError("路徑點系統未正確初始化")
                
            # 戰鬥系統
            print("🔄 設置戰鬥系統...")
            self.auto_combat.set_waypoint_system(self.waypoint_system)
            self.auto_combat.diagnose_waypoint_system()
            
            # ✅ 設置預設戰鬥設定但不啟用
            self.auto_combat.hunt_settings = {
                'combat_mode': 'safe_area',
                'attack_range': 200,
                'approach_distance': 0.1,
                'retreat_distance': 0.05,
                'attack_cooldown': 1.5,
                'movement_speed': 0.8,
                'use_waypoints': False,
                'patrol_mode': 'safe_area',
                'max_chase_distance': 0.15,
                'return_to_safe': True
            }
            
            # ✅ 檢查系統狀態
            print("\n🔍 戰鬥系統狀態檢查:")
            print(f"  - 路徑點系統: {'已設置' if self.auto_combat.waypoint_system else '未設置'}")
            print(f"  - 控制器: {'已連接' if self.auto_combat.controller and self.auto_combat.controller.is_connected else '未連接'}")
            print(f"  - 戰鬥模式: {self.auto_combat.hunt_settings.get('combat_mode', '未設定')}")
            print(f"  - is_enabled: {self.auto_combat.is_enabled}")
            print(f"  - auto_hunt_mode: {self.auto_combat.auto_hunt_mode}")
            
            print("✅ 核心組件初始化完成")
            
        except Exception as e:
            print(f"❌ 初始化失敗: {e}")
            # ✅ 提供更多診斷資訊
            print("🔍 診斷資訊:")
            print(f"   - 設定檔: {getattr(self, 'config', 'None')}")
            print(f"   - 路徑系統: {getattr(self, 'waypoint_system', 'None')}")
            print(f"   - 戰鬥系統: {getattr(self, 'auto_combat', 'None')}")
            if hasattr(self, 'auto_combat'):
                print(f"   - 戰鬥系統狀態: is_enabled={self.auto_combat.is_enabled}")
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
            
            # 自動偵測小地圖
            if self.tracker and hasattr(self.tracker, 'find_minimap'):
                try:
                    self.tracker.find_minimap()
                    print("✅ 已自動偵測小地圖")
                except Exception as e:
                    print(f"❌ 自動偵測小地圖失敗: {e}")
            
        except Exception as e:
            print(f"❌ 開啟編輯器失敗: {e}")

    def _load_config(self, config_path):
        """載入設定 - 改進版"""
        try:
            if not os.path.exists(config_path):
                print(f"⚠️ 設定檔不存在: {config_path}")
                # ✅ 創建預設配置
                default_config = {
                    "window_name": "BlueStacks App Player",
                    "detection_threshold": 0.3,
                    "update_interval": 3000,
                    "auto_save": True
                }
                
                # 嘗試創建預設配置檔
                try:
                    os.makedirs(os.path.dirname(config_path), exist_ok=True)
                    with open(config_path, "w", encoding="utf-8") as f:
                        yaml.dump(default_config, f, default_flow_style=False, allow_unicode=True)
                    print(f"✅ 已創建預設配置檔: {config_path}")
                except Exception as e:
                    print(f"⚠️ 無法創建配置檔: {e}")
                
                return default_config
                
            with open(config_path, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f)
                print(f"✅ 已載入配置檔: {config_path}")
                return config
                
        except Exception as e:
            print(f"❌ 載入配置失敗: {e}")
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
        
        # ✅ 確保戰鬥系統已初始化
        if hasattr(self, 'auto_combat'):
            # 確保路徑點系統已設置
            if not self.auto_combat.waypoint_system:
                self.auto_combat.set_waypoint_system(self.waypoint_system)
        
        self.is_enabled = True
        self._running = True
        self._thread = threading.Thread(target=self._simple_main_loop, daemon=True)
        self._thread.start()
        print("✅ 簡化版主循環已啟動")
        print(f"🔍 主循環狀態: is_enabled={self.is_enabled}")
        print(f"🔍 戰鬥系統狀態: is_enabled={getattr(self.auto_combat, 'is_enabled', False)}")
    
    def _simple_main_loop(self):
        """簡化的主循環 - 改進版"""
        print("▶️ 簡化主循環開始")
        
        frame_count = 0
        last_fps_time = time.time()
        
        while self._running:
            try:
                # 獲取當前幀
                frame = self.capturer.grab_frame()
                if frame is None:
                    continue
                    
                current_time = time.time()
                
                # 檢測血條和魔力條 - 已註解，目前不使用
                # if current_time - self.last_health_check >= self.health_check_interval:
                #     health_info = self.health_detector.detect_health_mana(frame)
                #     if health_info['success']:
                #         hp = health_info.get('hp_percentage', 0)
                #         mp = health_info.get('mp_percentage', 0)
                #         print(f"❤️ HP: {hp:.1f}% | 💙 MP: {mp:.1f}%")
                #     else:
                #         print("❌ 血魔檢測失敗")
                #     self.last_health_check = current_time
                
                # 更新角色位置
                rel_pos = None
                if self.is_enabled:
                    rel_pos = self.tracker.track_player(frame)
                
                # 更新戰鬥系統
                if self.auto_combat and self.auto_combat.is_enabled:
                    self.auto_combat.update(rel_pos, frame)
                
                # 計算FPS
                frame_count += 1
                if current_time - last_fps_time >= 1.0:
                    fps = frame_count / (current_time - last_fps_time)
                    frame_count = 0
                    last_fps_time = current_time
                
                # 控制循環速度
                time.sleep(0.01)
                
            except Exception as e:
                print(f"❌ 主循環錯誤: {e}")
                time.sleep(0.1)
        
        print("⏹️ 主循環已停止")
    
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

    def _mark_area_line(self, start_pos, end_pos, area_type, step=0.01):
        """統一區域標記（點或線），支援 step"""
        try:
            print(f"🔍 開始標記區域: {area_type}, 起點: {start_pos}, 終點: {end_pos}")  # 加入日誌
            line_points = self._get_line_points(start_pos, end_pos, step=step)
            for point in line_points:
                grid_key = f"{point[0]:.3f},{point[1]:.3f}"
                self.waypoint_system.area_grid[grid_key] = area_type
            print(f"✅ 區域標記: {area_type}, 點數: {len(line_points)} (step={step})")
        except Exception as e:
            print(f"❌ 區域標記失敗: {e}")
            import traceback
            traceback.print_exc()

    def _canvas_to_relative(self, canvas_x, canvas_y):
        """統一的畫布座標到相對座標轉換（PyQt5版本）"""
        try:
            if hasattr(self, '_editor_scale_info'):
                # 使用縮放資訊進行精確轉換
                offset = self._editor_scale_info.get('offset', (0, 0))
                display_size = self._editor_scale_info['display_size']
                
                rel_x = (canvas_x - offset[0]) / display_size[0]
                rel_y = (canvas_y - offset[1]) / display_size[1]
            else:
                # 備用方案
                canvas_width = self.canvas.width() or self.canvas_width
                canvas_height = self.canvas.height() or self.canvas_height
                
                rel_x = canvas_x / canvas_width
                rel_y = canvas_y / canvas_height
            
            # 確保在有效範圍內
            rel_x = max(0.0, min(1.0, rel_x))
            rel_y = max(0.0, min(1.0, rel_y))
            
            print(f"🔄 座標轉換: 畫布({canvas_x}, {canvas_y}) -> 相對({rel_x:.3f}, {rel_y:.3f})")  # 加入日誌
            return rel_x, rel_y
            
        except Exception as e:
            print(f"❌ 座標轉換失敗: {e}")
            return 0.0, 0.0

    def _on_canvas_click(self, event):
        """統一處理畫布點擊事件（PyQt5版本）"""
        try:
            rel_x, rel_y = self._canvas_to_relative(event.x(), event.y())
            print(f"🔍 點擊座標: ({rel_x:.3f}, {rel_y:.3f}), 模式: {self.edit_mode}")  # 加入日誌
            self._save_current_state()
            mode = self.edit_mode
            
            if mode == "waypoint":
                self._add_waypoint(rel_x, rel_y)
            elif mode == "delete":
                self._delete_nearest_element(rel_x, rel_y)
            elif mode in ["walkable", "forbidden", "rope"]:
                # 統一區域標記起點
                self.is_dragging = True
                self.drawing_line = True
                self.drag_start_pos = (rel_x, rel_y)
                # 立即標記起點
                self._mark_area_line(self.drag_start_pos, (rel_x, rel_y), mode)
            
            self._draw()
        except Exception as e:
            print(f"❌ 處理畫布點擊失敗: {e}")
            import traceback
            traceback.print_exc()

    def _set_edit_mode(self, mode):
        """設置編輯模式"""
        self.edit_mode = mode
        self.current_mode = mode
        self._sync_edit_mode()
        print(f"✅ 切換編輯模式: {mode}")  # 加入日誌

    def _sync_edit_mode(self):
        """同步編輯模式（PyQt5版本）"""
        # 根據模式調整游標
        cursor_map = {
            "waypoint": Qt.CrossCursor,
            "delete": Qt.ForbiddenCursor,
            "walkable": Qt.PointingHandCursor,
            "forbidden": Qt.PointingHandCursor,
            "rope": Qt.PointingHandCursor
        }
        
        cursor = cursor_map.get(self.current_mode, Qt.ArrowCursor)
        if hasattr(self, 'canvas') and self.canvas:
            self.canvas.setCursor(cursor)
            print(f"✅ 游標已切換: {self.current_mode}")  # 加入日誌

def main():
    """主程式 - PyQt5版本"""
    print("🎮 MapleStory Helper - 怪物檢測 + 路徑編輯版本 (PyQt5)")
    
    # ✅ 創建 QApplication
    app_qt = QApplication(sys.argv)
    
    try:
        # 創建應用
        app = MapleStoryHelper()
        
        # 檢查路徑點系統
        print("\n🗺️ 檢查路徑點系統...")
        waypoint_info = app.get_waypoint_info()
        print(f"📍 路徑點數量: {waypoint_info['waypoint_count']}")
        
        # ✅ 創建 PyQt5 GUI
        from modules.simple_gui_monster_display import MonsterDetectionGUI
        gui = MonsterDetectionGUI(app)
        
        # ✅ PyQt5 按鈕添加方式
        try:
            if hasattr(gui, 'add_waypoint_button'):
                gui.add_waypoint_button("🗺️ 編輯路徑", app.open_waypoint_editor)
            else:
                print("💡 可使用快捷鍵 Ctrl+W 開啟路徑編輯器")
                
        except Exception as e:
            print(f"⚠️ 添加編輯按鈕失敗: {e}")
        
        # 啟動應用
        app.start()
        
        # ✅ 運行 PyQt5 事件循環
        sys.exit(gui.run())
        
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