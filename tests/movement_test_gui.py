# tests/movement_test_gui.py
"""
基於搜索結果[16][17]的分離測試模組
專門用於AI移動和區域檢測測試，不污染生產代碼
"""

import tkinter as tk
from tkinter import ttk
import time
import sys
import os

# ✅ 基於搜索結果[17]的模組引用
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class MovementTestGUI:
    """✅ 基於搜索結果[16]的分離測試GUI"""
    
    def __init__(self, ro_helper):
        self.ro_helper = ro_helper
        self.root = tk.Tk()
        self.root.title("🧪 AI移動測試模式")
        self.root.geometry("800x600")
        
        # 測試狀態
        self.tracking_movement = False
        self.test_results = []
        
        self._create_test_interface()
    
    def _create_test_interface(self):
        """創建測試介面"""
        # 標題
        title_label = ttk.Label(self.root, text="🧪 AI移動系統測試", 
                               font=("Arial", 16, "bold"))
        title_label.pack(pady=10)
        
        # 測試控制面板
        self._create_test_controls()
        
        # 測試結果顯示
        self._create_test_results_display()
        
        # 測試狀態
        self.status_label = ttk.Label(self.root, text="狀態: 待機中", 
                                     foreground="blue")
        self.status_label.pack(pady=10)
    
    def _create_test_controls(self):
        """創建測試控制"""
        control_frame = ttk.LabelFrame(self.root, text="移動測試控制", padding=10)
        control_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # 第一行：基本測試
        row1 = ttk.Frame(control_frame)
        row1.pack(fill=tk.X, pady=2)
        
        ttk.Button(row1, text="🧪 區域檢測測試", 
                  command=self._test_area_detection).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(row1, text="🎯 目標設定測試", 
                  command=self._test_target_setting).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(row1, text="🏃 移動執行測試", 
                  command=self._test_movement_execution).pack(side=tk.LEFT, padx=5)
        
        # 第二行：進階測試
        row2 = ttk.Frame(control_frame)
        row2.pack(fill=tk.X, pady=2)
        
        ttk.Button(row2, text="📏 水平線追蹤", 
                  command=self._test_horizontal_line_tracking).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(row2, text="🛤️ 路徑巡邏", 
                  command=self._test_patrol_movement).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(row2, text="⏹️ 停止測試", 
                  command=self._stop_all_tests).pack(side=tk.LEFT, padx=5)
        
        # 第三行：系統測試
        row3 = ttk.Frame(control_frame)
        row3.pack(fill=tk.X, pady=2)
        
        ttk.Button(row3, text="🔧 系統診斷", 
                  command=self._run_system_diagnostics).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(row3, text="📊 生成報告", 
                  command=self._generate_test_report).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(row3, text="❌ 關閉測試", 
                  command=self.root.destroy).pack(side=tk.RIGHT, padx=5)
    
    def _create_test_results_display(self):
        """創建測試結果顯示"""
        results_frame = ttk.LabelFrame(self.root, text="測試結果", padding=10)
        results_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # 結果文字框
        self.results_text = tk.Text(results_frame, wrap=tk.WORD, 
                                   font=("Consolas", 10))
        scrollbar = ttk.Scrollbar(results_frame, orient=tk.VERTICAL, 
                                 command=self.results_text.yview)
        self.results_text.configure(yscrollcommand=scrollbar.set)
        
        self.results_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    
    def _log_test_result(self, message):
        """記錄測試結果"""
        timestamp = time.strftime("%H:%M:%S")
        log_message = f"[{timestamp}] {message}\n"
        self.results_text.insert(tk.END, log_message)
        self.results_text.see(tk.END)
        self.test_results.append(log_message)
    
    def _test_area_detection(self):
        """測試區域檢測"""
        self._log_test_result("🧪 開始區域檢測測試...")
        
        try:
            if not self.ro_helper or not hasattr(self.ro_helper, 'auto_combat'):
                self._log_test_result("❌ 無法獲取auto_combat系統")
                return
            
            # 獲取當前位置
            frame = self.ro_helper.capturer.grab_frame()
            current_pos = self.ro_helper.tracker.track_player(frame)
            
            if not current_pos:
                current_pos = (0.5, 0.5)
            
            self._log_test_result(f"📍 當前位置: {current_pos}")
            
            # 檢查區域標記
            combat_system = self.ro_helper.auto_combat
            if hasattr(combat_system, '_get_area_type'):
                area_type = combat_system._get_area_type(current_pos)
                self._log_test_result(f"🎨 當前區域類型: {area_type}")
                
                # 測試周圍8個方向
                directions = [
                    (-0.05, 0, "左"), (0.05, 0, "右"), 
                    (0, -0.05, "上"), (0, 0.05, "下"),
                    (-0.05, -0.05, "左上"), (0.05, 0.05, "右下"), 
                    (-0.05, 0.05, "左下"), (0.05, -0.05, "右上")
                ]
                
                for dx, dy, name in directions:
                    test_pos = (current_pos[0] + dx, current_pos[1] + dy)
                    test_area = combat_system._get_area_type(test_pos)
                    self._log_test_result(f"  {name}: {test_area}")
            
            self._log_test_result("✅ 區域檢測測試完成")
            
        except Exception as e:
            self._log_test_result(f"❌ 區域檢測測試失敗: {e}")
    
    def _test_horizontal_line_tracking(self):
        """✅ 水平線追蹤測試 - 完整實現"""
        self._log_test_result("📏 開始水平線追蹤測試...")
        
        try:
            # 記錄起始位置
            frame = self.ro_helper.capturer.grab_frame()
            start_pos = self.ro_helper.tracker.track_player(frame)
            if not start_pos:
                start_pos = (0.5, 0.5)
            
            self._log_test_result(f"📍 起始位置: {start_pos}")
            self._log_test_result(f"📏 基準水平線 Y座標: {start_pos[1]:.3f}")
            
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
            
            self._log_test_result(f"🎯 設定水平目標: {target}")
            self._log_test_result("📏 開始追蹤是否保持在水平線上...")
            
            # 啟動追蹤
            self.status_label.config(text="狀態: 水平線追蹤中")
            self._track_horizontal_movement()
            
        except Exception as e:
            self._log_test_result(f"❌ 水平線追蹤測試失敗: {e}")
    
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
                
                # 即時反饋
                if vertical_deviation < 0.01:
                    self._log_test_result(f"✅ {timestamp:.1f}s: 完美保持水平線 - 偏差{vertical_deviation:.4f}")
                elif vertical_deviation < 0.02:
                    self._log_test_result(f"👍 {timestamp:.1f}s: 良好保持水平線 - 偏差{vertical_deviation:.4f}")
                else:
                    self._log_test_result(f"⚠️ {timestamp:.1f}s: 偏離水平線 - 偏差{vertical_deviation:.4f}")
            
            # 測試15秒
            if time.time() - self.horizontal_test_start < 15:
                self.root.after(500, self._track_horizontal_movement)
            else:
                self._analyze_horizontal_movement()
                
        except Exception as e:
            self._log_test_result(f"❌ 水平追蹤錯誤: {e}")
    
    def _analyze_horizontal_movement(self):
        """分析水平移動結果"""
        self.horizontal_tracking = False
        
        if not hasattr(self, 'horizontal_history') or not self.horizontal_history:
            return
        
        self._log_test_result("\n📊 水平線移動分析報告:")
        
        # 分析垂直偏差
        deviations = [record['deviation'] for record in self.horizontal_history]
        max_deviation = max(deviations)
        avg_deviation = sum(deviations) / len(deviations)
        
        self._log_test_result(f"📏 基準水平線: Y = {self.horizontal_baseline:.3f}")
        self._log_test_result(f"📏 最大偏差: {max_deviation:.4f}")
        self._log_test_result(f"📏 平均偏差: {avg_deviation:.4f}")
        
        # 分析水平移動範圍
        x_positions = [record['pos'][0] for record in self.horizontal_history]
        x_range = max(x_positions) - min(x_positions)
        
        self._log_test_result(f"📏 水平移動範圍: {x_range:.3f}")
        
        # 評估結果
        if avg_deviation < 0.01 and x_range > 0.1:
            self._log_test_result("🏆 優秀！角色完美沿水平線移動")
        elif avg_deviation < 0.02 and x_range > 0.05:
            self._log_test_result("👍 良好！角色基本沿水平線移動")
        elif x_range > 0.02:
            self._log_test_result("⚠️ 可接受！角色有移動但偏離水平線較多")
        else:
            self._log_test_result("❌ 需要改進！角色移動不明顯或嚴重偏離")
        
        self.status_label.config(text="狀態: 水平線分析完成")
    
    # 其他測試方法...
    def _test_target_setting(self):
        self._log_test_result("🎯 目標設定測試...")
        # 實現目標設定測試
    
    def _test_movement_execution(self):
        self._log_test_result("🏃 移動執行測試...")
        # 實現移動執行測試
    
    def _test_patrol_movement(self):
        self._log_test_result("🛤️ 巡邏移動測試...")
        # 實現巡邏測試
    
    def _stop_all_tests(self):
        self._log_test_result("⏹️ 停止所有測試")
        self.tracking_movement = False
        if hasattr(self, 'horizontal_tracking'):
            self.horizontal_tracking = False
    
    def _run_system_diagnostics(self):
        self._log_test_result("🔧 運行系統診斷...")
        # 實現系統診斷
    
    def _generate_test_report(self):
        self._log_test_result("📊 生成測試報告...")
        # 實現報告生成
    
    def run(self):
        """運行測試GUI"""
        self.root.mainloop()

    def _test_long_press_movement(self):
        """✅ 測試長按移動效果"""
        self._log_test_result("🕹️ 開始長按移動測試...")
        
        try:
            if not self.ro_helper or not hasattr(self.ro_helper, 'auto_combat'):
                self._log_test_result("❌ 無法獲取auto_combat系統")
                return
            
            controller = self.ro_helper.auto_combat.controller
            
            # 記錄初始位置
            frame = self.ro_helper.capturer.grab_frame()
            start_pos = self.ro_helper.tracker.track_player(frame)
            if not start_pos:
                start_pos = (0.5, 0.5)
            
            self._log_test_result(f"📍 測試開始位置: {start_pos}")
            
            # 測試不同長度的按鍵
            test_durations = [1.0, 2.0, 3.0]
            
            for duration in test_durations:
                self._log_test_result(f"🕹️ 測試 {duration} 秒長按...")
                
                # 執行長按移動
                success = controller.move('right', duration)
                
                if success:
                    # 等待移動完成
                    time.sleep(duration + 0.5)
                    
                    # 檢查位置變化
                    frame = self.ro_helper.capturer.grab_frame()
                    new_pos = self.ro_helper.tracker.track_player(frame)
                    
                    if new_pos:
                        distance_moved = abs(new_pos[0] - start_pos[0])
                        self._log_test_result(f"📏 {duration}秒移動距離: {distance_moved:.4f}")
                        
                        if distance_moved > 0.02:
                            self._log_test_result(f"✅ {duration}秒長按有效果")
                        else:
                            self._log_test_result(f"❌ {duration}秒長按無明顯效果")
                        
                        start_pos = new_pos  # 更新起始位置
                    else:
                        self._log_test_result(f"❌ 無法獲取移動後位置")
                else:
                    self._log_test_result(f"❌ {duration}秒長按執行失敗")
                
                # 間隔等待
                time.sleep(1)
            
            self._log_test_result("✅ 長按移動測試完成")
            
        except Exception as e:
            self._log_test_result(f"❌ 長按移動測試失敗: {e}")

