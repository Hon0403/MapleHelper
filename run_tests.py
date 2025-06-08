# run_tests.py - 修正版：支持路徑載入
"""
測試執行器 - 支持路徑載入
"""

import sys
import os
import glob
import time

def main():
    """測試模式主程式 - 支持路徑載入"""
    print("🧪 ROClassic Helper - 測試模式")
    print("基於軟體工程最佳實踐的分離測試環境")
    
    try:
        # 導入生產代碼
        from main import MapleStoryHelper
        
        # 創建應用實例
        app = MapleStoryHelper()
        
        # ✅ 添加路徑載入功能
        print("\n🗺️ 檢查可用路徑檔案...")
        _load_available_paths(app)
        
        # 啟動測試GUI
        from tests.movement_test_gui import MovementTestGUI
        test_gui = MovementTestGUI(app)
        
        # 啟動應用
        app.start()
        
        # 運行測試GUI
        test_gui.run()
        
    except Exception as e:
        print(f"❌ 測試模式啟動失敗: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if 'app' in locals():
            app.stop()

def _load_available_paths(app):
    """✅ 載入可用的路徑檔案"""
    try:
        data_dir = "data"
        if not os.path.exists(data_dir):
            print(f"❌ 路徑目錄不存在: {data_dir}")
            return
        
        # 尋找所有JSON路徑檔案
        json_files = glob.glob(os.path.join(data_dir, "*.json"))
        
        if not json_files:
            print(f"❌ 沒有找到路徑檔案")
            return
        
        print(f"📂 找到 {len(json_files)} 個路徑檔案:")
        for i, file_path in enumerate(json_files):
            filename = os.path.basename(file_path)
            print(f"  {i+1}. {filename}")
        
        # ✅ 自動載入第一個檔案，或讓用戶選擇
        if len(json_files) == 1:
            # 只有一個檔案，自動載入
            selected_file = json_files[0]
            print(f"🔄 自動載入: {os.path.basename(selected_file)}")
        else:
            # 多個檔案，載入最新的
            selected_file = max(json_files, key=os.path.getmtime)
            print(f"🔄 載入最新檔案: {os.path.basename(selected_file)}")
        
        # 載入選中的路徑檔案
        app.waypoint_system.load_map_data(selected_file)
        
        # 顯示載入結果
        waypoint_count = len(app.waypoint_system.waypoints)
        obstacle_count = len(getattr(app.waypoint_system, 'obstacles', []))
        area_count = len(getattr(app.waypoint_system, 'area_grid', {}))
        
        print(f"✅ 路徑載入成功:")
        print(f"   📍 路徑點: {waypoint_count} 個")
        print(f"   🚧 障礙物: {obstacle_count} 個") 
        print(f"   🎨 區域標記: {area_count} 個")
        
        return True
        
    except Exception as e:
        print(f"❌ 載入路徑失敗: {e}")
        return False

def _interactive_path_selection(json_files):
    """✅ 互動式路徑選擇（可選功能）"""
    try:
        print("\n請選擇要載入的路徑檔案:")
        for i, file_path in enumerate(json_files):
            filename = os.path.basename(file_path)
            # 顯示檔案修改時間
            mtime = os.path.getmtime(file_path)
            mtime_str = time.strftime("%Y-%m-%d %H:%M", time.localtime(mtime))
            print(f"  {i+1}. {filename} ({mtime_str})")
        
        print(f"  0. 不載入任何檔案")
        
        while True:
            try:
                choice = input(f"\n請輸入選擇 (0-{len(json_files)}): ").strip()
                choice_num = int(choice)
                
                if choice_num == 0:
                    print("⚠️ 跳過路徑載入")
                    return None
                elif 1 <= choice_num <= len(json_files):
                    selected_file = json_files[choice_num - 1]
                    print(f"✅ 選擇: {os.path.basename(selected_file)}")
                    return selected_file
                else:
                    print(f"❌ 請輸入 0-{len(json_files)} 之間的數字")
            except ValueError:
                print("❌ 請輸入有效數字")
            except KeyboardInterrupt:
                print("\n⚠️ 取消選擇")
                return None
                
    except Exception as e:
        print(f"❌ 路徑選擇失敗: {e}")
        return None

if __name__ == "__main__":
    main()
