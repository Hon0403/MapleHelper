# main_new.py - 分層架構重構版

import sys
import os
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt

from core.application import MapleStoryApplication
from core.component_adapter import AppAdapter, create_component_adapter
from includes.log_utils import get_logger


def setup_components(app: MapleStoryApplication):
    """設置所有組件"""
    logger = get_logger("ComponentSetup")
    
    try:
        # 導入組件
        from modules.simple_capturer import SimpleCapturer
        from modules.coordinate import TemplateMatcherTracker
        from modules.auto_combat_simple import SimpleCombat
        from modules.waypoint_editor import WaypointEditor
        from modules.simple_waypoint_system import SimpleWaypointSystem
        from modules.simple_adb import SimpleADB
        from modules.health_mana_detector import HealthManaDetector
        from modules.simple_gui_monster_display import MonsterDetectionGUI
        
        # 註冊組件
        component_manager = app.component_manager
        
        # 1. 畫面捕捉器
        capturer = SimpleCapturer(config=app.get_config())
        capturer_adapter = create_component_adapter('capturer', capturer, app.get_config())
        component_manager.register_component('capturer', capturer_adapter, 'capturer')
        
        # 2. 路徑點系統
        waypoint_system = SimpleWaypointSystem(config=app.get_config())
        waypoint_adapter = create_component_adapter('waypoint_system', waypoint_system, app.get_config())
        component_manager.register_component('waypoint_system', waypoint_adapter, 'waypoint_system')
        
        # 3. 角色追蹤器
        tracker = TemplateMatcherTracker(config=app.get_config(), capturer=capturer)
        tracker_adapter = create_component_adapter('tracker', tracker, app.get_config())
        component_manager.register_component('tracker', tracker_adapter)
        
        # 4. 血條檢測器
        health_detector = HealthManaDetector(config=app.get_config())
        health_adapter = create_component_adapter('health_detector', health_detector, app.get_config())
        component_manager.register_component('health_detector', health_adapter, 'health_detector')
        
        # 5. 戰鬥系統
        combat = SimpleCombat(config=app.get_config())
        combat_adapter = create_component_adapter('combat', combat, app.get_config())
        component_manager.register_component('combat', combat_adapter, 'combat')
        
        # 6. 創建應用程式適配器
        app_adapter = AppAdapter(app, capturer, tracker, waypoint_system, health_detector, combat)
        
        # 7. GUI
        gui = MonsterDetectionGUI(app_adapter, config=app.get_config())
        gui_adapter = create_component_adapter('gui', gui, app.get_config())
        component_manager.register_component('gui', gui_adapter, 'gui')
        
        # 8. 路徑點編輯器（延遲初始化）
        component_manager.register_component('editor', None, 'waypoint_editor')
        
        # 設置組件間的依賴關係
        combat.set_waypoint_system(waypoint_system)
        
        logger.info("✅ 所有組件設置完成")
        return True
        
    except Exception as e:
        logger.error(f"組件設置失敗: {e}")
        import traceback
        traceback.print_exc()
        return False


def create_editor(app: MapleStoryApplication):
    """創建路徑點編輯器"""
    try:
        from modules.waypoint_editor import WaypointEditor
        
        waypoint_system = app.get_component('waypoint_system').component
        tracker = app.get_component('tracker').component
        editor_config = app.get_config().get('waypoint_editor', {})
        
        app.logger.info("🛠️ 開始創建路徑點編輯器...")
        app.logger.info(f"  - waypoint_system: {type(waypoint_system)}")
        app.logger.info(f"  - tracker: {type(tracker)}")
        app.logger.info(f"  - editor_config: {editor_config}")
        
        editor = WaypointEditor(
            waypoint_system=waypoint_system,
            tracker=tracker,
            config=editor_config
        )
        
        app.logger.info("✅ 路徑點編輯器創建成功")
        
        # 創建編輯器適配器並更新組件管理器
        editor_adapter = create_component_adapter('editor', editor, app.get_config())
        app.component_manager.components['editor'] = editor_adapter
        
        return editor
        
    except Exception as e:
        import traceback
        app.logger.error(f"❌ 創建編輯器失敗: {e}")
        app.logger.error("詳細錯誤:")
        traceback.print_exc()
        return None


def main():
    """主程式 - 分層架構重構版"""
    logger = get_logger("Main")
    logger.info("🎮 MapleStory Helper - 分層架構重構版")
    
    # 創建 QApplication
    app_qt = QApplication(sys.argv)
    
    try:
        # 創建應用程式
        app = MapleStoryApplication("configs/bluestacks.yaml")
        
        # 設置組件
        if not setup_components(app):
            logger.error("組件設置失敗")
            return 1
        
        # 初始化應用程式
        if not app.initialize():
            logger.error("應用程式初始化失敗")
            return 1
        
        # 啟動應用程式
        if not app.start():
            logger.error("應用程式啟動失敗")
            return 1
        
        # 自動載入初始地圖（如果有 get_initial 和 load_map 方法）
        waypoint_system = app.get_component('waypoint_system').component
        if hasattr(waypoint_system, 'get_initial') and hasattr(waypoint_system, 'load_map'):
            initial_file = waypoint_system.get_initial()
            if initial_file:
                waypoint_system.load_map(initial_file)
        
        # 設置編輯器創建函數
        def open_editor():
            logger.info("🖱️ 用戶點擊編輯路徑按鈕")
            try:
                editor = create_editor(app)
                if editor:
                    logger.info("🖥️ 顯示路徑編輯器視窗")
                    editor.show()
                    editor.raise_()
                    editor.activateWindow()
                    logger.info("✅ 路徑編輯器視窗已顯示")
                else:
                    logger.error("❌ 路徑編輯器創建失敗，無法顯示")
            except Exception as e:
                logger.error(f"❌ 開啟編輯器時發生錯誤: {e}")
                import traceback
                traceback.print_exc()
        
        # 為 GUI 添加編輯器按鈕
        gui = app.get_component('gui').component
        if gui and hasattr(gui, 'add_waypoint_button'):
            logger.info("🔘 添加編輯路徑按鈕到 GUI")
            gui.add_waypoint_button("🗺️ 編輯路徑", open_editor)
        else:
            logger.warning("⚠️ GUI 沒有 add_waypoint_button 方法")
        
        logger.info("✅ 應用程式啟動完成")
        
        # 運行 PyQt5 事件循環
        sys.exit(gui.run())
        
    except Exception as e:
        logger.error(f"程式錯誤: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    finally:
        try:
            if 'app' in locals():
                app.stop()
                app.cleanup()
        except:
            pass


if __name__ == "__main__":
    main() 