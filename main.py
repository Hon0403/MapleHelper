# main.py - 效能優化版

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
# ADB 支援已移除 - 專注楓之谷 Worlds 原生遊戲
from modules.health_mana_detector_hybrid import HealthManaDetectorHybrid  # HUD血條檢測（多模板匹配+填充分析）
from modules.character_health_detector import CharacterHealthDetector  # 角色血條檢測
from includes.config_utils import ConfigUtils
from includes.log_utils import get_logger


class MapleStoryHelper:
    """效能優化版 MapleStory Helper - AutoMaple 風格"""
    
    def __init__(self, config_path="configs/config.yaml"):
        # ✅ 使用共用工具初始化
        self.logger = get_logger("MapleStoryHelper")
        
        self.logger.info("啟動效能優化版 MapleStory Helper...")
        
        # 先載入設定
        self.config = self.load_config(config_path)
        
        # ADB 控制器已移除 - 專注楓之谷 Worlds 原生遊戲
        
        # 基本狀態
        self.is_enabled = False
        self._running = False
        
        # ✅ 效能優化：從設定檔讀取更新頻率控制
        main_loop_config = self.config.get('main_loop', {})
        self.update_intervals = {
            'frame_capture': main_loop_config.get('frame_capture', 0.05),    # 20 FPS (原10ms)
            'position_tracking': main_loop_config.get('position_tracking', 0.1),  # 10 FPS
            'combat_update': main_loop_config.get('combat_update', 0.2),      # 5 FPS
            'health_check': main_loop_config.get('health_check', 1.0),       # 1 FPS
            'status_update': main_loop_config.get('status_update', 0.5)       # 2 FPS
        }
        
        # ✅ 效能優化：添加時間追蹤
        self.last_update_times = {
            'frame_capture': 0,
            'position_tracking': 0,
            'combat_update': 0,
            'health_check': 0,
            'status_update': 0
        }
        
        # ✅ 效能優化：從設定檔讀取緩存設定
        capturer_config = self.config.get('capturer', {})
        self.frame_cache = None
        self.position_cache = None
        self.cache_duration = capturer_config.get('cache_duration', 0.1)  # 100ms緩存
        
        # 怪物檢測器 - 簡化版
        from includes.simple_template_utils import get_monster_detector
        self.monster_detector = get_monster_detector(self.config)
        
        # ✅ 分離的血條檢測器（多模板匹配+填充分析）
        self.hud_health_detector = HealthManaDetectorHybrid(
            template_dir="templates/MainScreen",
            config=self.config
        )
        self.character_health_detector = CharacterHealthDetector(
            template_dir="templates/MainScreen", 
            config=self.config
        )
        self.last_health_check = 0
        self.health_check_interval = 0.5  # 每0.5秒檢查一次
        
        self.logger.info("✅ 血條檢測系統已分離：HUD檢測器（多模板匹配+填充分析）+ 角色血條檢測器")
        
        # ✅ 添加路徑點系統 - 傳入對應的 config
        waypoint_config = self.config.get('waypoint_system', {})
        self.waypoint_system = SimpleWaypointSystem(config=waypoint_config)
        self.init_waypoints()
        self.logger.info("路徑點系統已初始化")
        
        # ✅ 添加歷史幀管理（運動檢測需要）
        self.frame_history = []
        self.max_history_frames = 3  # 保留最近3幀
        self.frame_history_enabled = True
        
        # 初始化核心組件
        self.init_components()
        
        # ✅ 初始化編輯器（但不立即顯示）
        self.waypoint_editor = None
        
        # ✅ 效能優化：添加統計資訊
        self.performance_stats = {
            'fps': 0,
            'frame_count': 0,
            'last_fps_time': time.time(),
            'avg_loop_time': 0,
            'max_loop_time': 0
        }
    
    def init_components(self):
        """只初始化核心組件 - 效能優化版"""
        try:
            # 畫面捕獲 - 傳入完整的 config
            self.logger.info("初始化畫面捕獲...")
            self.capturer = SimpleCapturer(config=self.config)
            
            # 角色追蹤 - 傳入對應的 config
            self.logger.info("初始化角色追蹤...")
            self.tracker = TemplateMatcherTracker(config=self.config, capturer=self.capturer)
            
            # 簡單戰鬥 - 傳入對應的 config 並共用檢測器
            self.logger.info("初始化戰鬥系統...")
            combat_config = self.config.get('combat', {})
            self.auto_combat = SimpleCombat(config=combat_config, monster_detector=self.monster_detector)
            
            # ✅ 更詳細的錯誤檢查
            if not self.waypoint_system:
                raise RuntimeError("路徑點系統未正確初始化")
                
            # 戰鬥系統
            self.logger.info("設置戰鬥系統...")
            self.auto_combat.set_waypoint_system(self.waypoint_system)
            
            # ✅ 設置分離的血條檢測器
            self.auto_combat.set_hud_health_detector(self.hud_health_detector)  # HUD檢測器
            self.auto_combat.set_character_health_detector(self.character_health_detector)  # 角色血條檢測器
            self.auto_combat.diagnose_waypoint_system()
            
            # ✅ 從設定檔讀取戰鬥設定
            combat_config = self.config.get('combat', {})
            self.auto_combat.hunt_settings = {
                'combat_mode': 'safe_area',
                'attack_range': combat_config.get('attack_range', 0.4),
                'approach_distance': combat_config.get('approach_distance', 0.1),
                'retreat_distance': combat_config.get('retreat_distance', 0.05),
                'attack_cooldown': combat_config.get('attack_cooldown', 1.5),
                'movement_speed': combat_config.get('movement_speed', 0.8),
                'use_waypoints': False,
                'patrol_mode': 'safe_area',
                'max_chase_distance': combat_config.get('max_chase_distance', 0.15),
                'return_to_safe': True
            }
            
            # ✅ 檢查系統狀態
            self.logger.info("\n戰鬥系統狀態檢查:")
            self.logger.info(f"  - 路徑點系統: {'已設置' if self.auto_combat.waypoint_system else '未設置'}")
            self.logger.info(f"  - 控制器: {'已連接' if self.auto_combat.controller and self.auto_combat.controller.is_connected else '未連接'}")
            self.logger.info(f"  - HUD血條檢測器: {'已設置' if hasattr(self.auto_combat, 'hud_health_detector') else '未設置'}")
            self.logger.info(f"  - 角色血條檢測器: {'已設置' if hasattr(self.auto_combat, 'character_health_detector') else '未設置'}")
            self.logger.info(f"  - 戰鬥模式: {self.auto_combat.hunt_settings.get('combat_mode', '未設定')}")
            self.logger.info(f"  - is_enabled: {self.auto_combat.is_enabled}")
            self.logger.info(f"  - auto_hunt_mode: {self.auto_combat.auto_hunt_mode}")
            
            self.logger.info("✅ 核心組件初始化完成")
            
        except Exception as e:
            self.logger.error(f"初始化失敗: {e}")
            # ✅ 提供更多診斷資訊
            self.logger.info("診斷資訊:")
            self.logger.info(f"   - 設定檔: {getattr(self, 'config', 'None')}")
            self.logger.info(f"   - 路徑系統: {getattr(self, 'waypoint_system', 'None')}")
            self.logger.info(f"   - 戰鬥系統: {getattr(self, 'auto_combat', 'None')}")
            if hasattr(self, 'auto_combat'):
                self.logger.info(f"   - 戰鬥系統狀態: is_enabled={self.auto_combat.is_enabled}")
            raise
    
    def connect_shared_detection_service(self, gui):
        """連接共享檢測服務，避免重複處理"""
        try:
            if hasattr(self, 'auto_combat') and hasattr(gui, '_shared_results'):
                # 設置戰鬥系統的共享怪物檢測回調
                def get_shared_monsters():
                    """獲取GUI檢測循環的共享怪物結果"""
                    with gui._detection_lock:
                        shared_data = gui._shared_results.copy()
                        return shared_data.get('monsters', [])
                
                # 設置戰鬥系統的共享角色血條檢測回調
                def get_shared_health_bars():
                    """獲取GUI檢測循環的共享角色血條結果"""
                    with gui._detection_lock:
                        shared_data = gui._shared_results.copy()
                        return shared_data.get('character_health_bars', [])
                
                self.auto_combat.set_shared_detection_callback(get_shared_monsters)
                self.auto_combat.set_shared_health_detection_callback(get_shared_health_bars)
                self.logger.info("✅ 已連接共享檢測服務（怪物+血條），避免重複處理")
                return True
            else:
                self.logger.warning("⚠️ 無法連接共享檢測服務")
                return False
        except Exception as e:
            self.logger.error(f"連接共享檢測服務失敗: {e}")
            return False
    
    def open_editor(self):
        """✅ 重構版：開啟或顯示已存在的編輯器實例"""
        try:
            # 如果編輯器從未創建，則初始化一個
            if self.waypoint_editor is None:
                self.logger.info("🛠️ 首次創建路徑編輯器實例...")
                editor_config = self.config.get('waypoint_editor', {})
                self.waypoint_editor = WaypointEditor(
                    waypoint_system=self.waypoint_system,
                    tracker=self.tracker,
                    config=editor_config
                )
            
            # 顯示編輯器視窗
            self.logger.info("🖥️ 顯示路徑編輯器...")
            self.waypoint_editor.show()
            self.waypoint_editor.raise_()
            self.waypoint_editor.activateWindow()
            
        except Exception as e:
            self.logger.error(f"開啟編輯器失敗: {e}")
            import traceback
            traceback.print_exc()

    def load_config(self, config_path):
        """載入設定 - 使用 ConfigUtils"""
        try:
            # 使用 ConfigUtils 載入設定檔
            config = ConfigUtils.load_yaml_config(config_path)
            
            if config:
                self.logger.info(f"已載入配置檔: {config_path}")
                return config
            else:
                self.logger.error(f"設定檔為空或載入失敗: {config_path}")
                raise RuntimeError(f"無法載入設定檔: {config_path}")
                
        except Exception as e:
            self.logger.error(f"載入配置失敗: {e}")
            raise RuntimeError(f"設定檔載入失敗: {e}")

    
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
        self._thread = threading.Thread(target=self.main_loop, daemon=True)
        self._thread.start()
        self.logger.info("效能優化版主循環已啟動")
        # 主循環已啟動

    def main_loop(self):
        """✅ 效能優化版主循環"""
        self.logger.info("效能優化主循環開始")
        
        frame_count = 0
        last_fps_time = time.time()
        
        # 從設定檔讀取睡眠時間
        main_loop_config = self.config.get('main_loop', {})
        sleep_time = main_loop_config.get('sleep_time', 0.02)
        
        while self._running:
            loop_start_time = time.time()
            
            try:
                current_time = time.time()
                
                # ✅ 效能優化：智能畫面捕捉
                if self.should_update('frame_capture'):
                    frame = self.capturer.grab_frame()
                    if frame is not None:
                        self.frame_cache = frame
                        self.cache_timestamp = current_time
                        
                        # ✅ 添加歷史幀管理（運動檢測需要）
                        if self.frame_history_enabled:
                            self.frame_history.append(frame.copy())
                            # 保持歷史幀數量限制
                            if len(self.frame_history) > self.max_history_frames:
                                self.frame_history.pop(0)
                
                # 使用緩存的畫面
                frame = self.frame_cache
                if frame is None:
                    time.sleep(0.01)
                    continue
                
                # ✅ 效能優化：智能位置追蹤
                rel_pos = None
                if self.is_enabled and self.should_update('position_tracking'):
                    rel_pos = self.tracker.track_player(frame)
                    if rel_pos:
                        self.position_cache = rel_pos
                else:
                    rel_pos = self.position_cache
                
                # ✅ 效能優化：智能戰鬥更新
                if (self.auto_combat and self.auto_combat.is_enabled and 
                    self.should_update('combat_update')):
                    # 傳遞歷史幀給戰鬥系統（用於運動檢測）
                    history_frames = self.frame_history if self.frame_history_enabled else None
                    self.auto_combat.update(rel_pos, frame, frame_history=history_frames)
                
                # ✅ 效能優化：降低血條檢查頻率
                if self.should_update('health_check'):
                    # 血條檢測已註解，目前不使用
                    pass
                
                # ✅ 效能優化：智能狀態更新
                if self.should_update('status_update'):
                    # 更新效能統計
                    self.update_stats()
                
                # 計算FPS
                frame_count += 1
                if current_time - last_fps_time >= 1.0:
                    fps = frame_count / (current_time - last_fps_time)
                    self.performance_stats['fps'] = fps
                    frame_count = 0
                    last_fps_time = current_time
                    
                    # 顯示效能資訊
                    # 效能統計更新
                
                # ✅ 效能優化：動態睡眠時間
                loop_time = time.time() - loop_start_time
                actual_sleep_time = max(0.001, sleep_time - loop_time)  # 最小1ms
                time.sleep(actual_sleep_time)
                
            except Exception as e:
                self.logger.error(f"主循環錯誤: {e}")
                time.sleep(0.1)
        
        self.logger.info("主循環已停止")
    
    def should_update(self, update_type):
        """✅ 效能優化：智能更新檢查"""
        current_time = time.time()
        last_update = self.last_update_times.get(update_type, 0)
        interval = self.update_intervals.get(update_type, 0.1)
        
        if current_time - last_update >= interval:
            self.last_update_times[update_type] = current_time
            return True
        return False
    
    def update_stats(self):
        """✅ 效能優化：更新效能統計"""
        current_time = time.time()
        loop_time = current_time - self.last_update_times.get('status_update', current_time)
        
        # 更新平均循環時間
        if self.performance_stats['avg_loop_time'] == 0:
            self.performance_stats['avg_loop_time'] = loop_time
        else:
            self.performance_stats['avg_loop_time'] = (
                self.performance_stats['avg_loop_time'] * 0.9 + loop_time * 0.1
            )
        
        # 更新最大循環時間
        if loop_time > self.performance_stats['max_loop_time']:
            self.performance_stats['max_loop_time'] = loop_time
    
    def stop(self):
        """停止程式"""
        self.is_enabled = False
        self._running = False
        
        if hasattr(self, 'auto_combat'):
            self.auto_combat.stop()
        
        # ✅ 效能優化：清理緩存
        self.frame_cache = None
        self.position_cache = None
        
        self.logger.info("程式已停止")
    
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
            'performance': self.performance_stats
        }

    def start_area_test(self):
        """開始區域移動測試"""
        if not self.auto_combat.waypoint_system:
            self.logger.error("waypoint_system未整合")
            return
        
        self.logger.info("開始區域移動測試...")
        self.logger.info(f"當前area_grid數量: {len(getattr(self.auto_combat.waypoint_system, 'area_grid', {}))}")
        
        # 啟動自動戰鬥（包含移動邏輯）
        self.auto_combat.start()
        
        # 設定測試目標
        if self.auto_combat.waypoint_system.waypoints:
            target = self.auto_combat.waypoint_system.waypoints[0]['pos']
            self.auto_combat.current_target = target
            self.logger.info(f"設定測試目標: {target}")

    def init_waypoints(self):
        """✅ 改善的路徑系統初始化"""
        try:
            # 獲取可用的地圖檔案
            initial_file = self.waypoint_system.get_initial()
            
            if initial_file:
                self.logger.info(f"自動載入初始地圖: {initial_file}")
                success = self.waypoint_system.load_map(initial_file)
                
                if success:
                    self.logger.info("初始地圖載入成功")
                else:
                    self.logger.error("初始地圖載入失敗")
            else:
                self.logger.warning("沒有找到可用的地圖檔案，使用預設設定")
                
        except Exception as e:
            self.logger.error(f"路徑系統初始化失敗: {e}")

    def mark_area(self, start_pos, end_pos, area_type, step=0.01):
        """統一區域標記（點或線），支援 step"""
        try:
            self.logger.info(f"開始標記區域: {area_type}, 起點: {start_pos}, 終點: {end_pos}")  # 加入日誌
            line_points = self._get_line_points(start_pos, end_pos, step=step)
            for point in line_points:
                grid_key = f"{point[0]:.3f},{point[1]:.3f}"
                self.waypoint_system.area_grid[grid_key] = area_type
            self.logger.info(f"區域標記: {area_type}, 點數: {len(line_points)} (step={step})")
        except Exception as e:
            self.logger.error(f"區域標記失敗: {e}")
            import traceback
            traceback.print_exc()

    def canvas_to_relative(self, canvas_x, canvas_y):
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
            
            self.logger.info(f"座標轉換: 畫布({canvas_x}, {canvas_y}) -> 相對({rel_x:.3f}, {rel_y:.3f})")  # 加入日誌
            return rel_x, rel_y
            
        except Exception as e:
            self.logger.error(f"座標轉換失敗: {e}")
            return 0.0, 0.0

    def on_canvas_click(self, event):
        """統一處理畫布點擊事件（PyQt5版本）"""
        try:
            rel_x, rel_y = self.canvas_to_relative(event.x(), event.y())
            self.logger.info(f"點擊座標: ({rel_x:.3f}, {rel_y:.3f}), 模式: {self.edit_mode}")  # 加入日誌
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
                self.mark_area(self.drag_start_pos, (rel_x, rel_y), mode)
            
            self._draw()
        except Exception as e:
            self.logger.error(f"處理畫布點擊失敗: {e}")
            import traceback
            traceback.print_exc()

    def set_mode(self, mode):
        """設置編輯模式"""
        self.edit_mode = mode
        self.current_mode = mode
        self._sync_edit_mode()
        self.logger.info(f"切換編輯模式: {mode}")  # 加入日誌

    def sync_mode(self):
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
            # 游標已切換

def main():
    """主程式 - PyQt5版本"""
    logger = get_logger("Main")
    logger.info("🎮 MapleStory Helper - 效能優化版 (PyQt5)")
    
    # ✅ 創建 QApplication
    app_qt = QApplication(sys.argv)
    
    try:
        # 創建應用
        app = MapleStoryHelper()
        
        # 檢查路徑點系統
        logger.info("檢查路徑點系統...")
        waypoint_info = app.get_waypoint_info()
        logger.info(f"路徑點數量: {waypoint_info['waypoint_count']}")
        
        # ✅ 創建 PyQt5 GUI
        from modules.simple_gui_monster_display import MonsterDetectionGUI
        gui = MonsterDetectionGUI(app, config=app.config)
        
        # ✅ 連接共享檢測服務，避免重複處理
        shared_connected = app.connect_shared_detection_service(gui)
        if shared_connected:
            logger.info("🔄 共享檢測服務已連接 - 戰鬥系統將使用GUI檢測結果，避免重複血條檢測")
        else:
            logger.warning("⚠️ 共享檢測服務連接失敗 - 將使用獨立檢測（可能有重複處理）")
        
        # ✅ 路徑編輯功能已整合到自動打怪區塊中，無需額外添加按鈕
        # 路徑編輯功能已整合到自動打怪區塊中
        logger.info("💡 請使用自動打怪區塊中的「🗺️ 編輯路徑」按鈕")
        
        # 啟動應用
        app.start()
        
        # ✅ 運行 PyQt5 事件循環
        sys.exit(gui.run())
        
    except Exception as e:
        logger.error(f"程式錯誤: {e}")
        import traceback
        traceback.print_exc()
    finally:
        try:
            app.stop()
        except:
            pass

if __name__ == "__main__":
    main()