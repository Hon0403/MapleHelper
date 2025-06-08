# modules/simple_gui_monster_display.py - 重構版：文字顯示匹配結果

import tkinter as tk
from tkinter import ttk
import threading
import time
from datetime import datetime
import json
import os
from PIL import Image, ImageTk
import cv2
import numpy as np
import sys

# 添加父目錄到 Python 路徑
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from includes.canvas_utils import CanvasUtils  # 添加 CanvasUtils 導入

class MonsterDetectionGUI:
    """怪物檢測GUI - 重構版：使用文字列表顯示匹配結果"""
    
    def __init__(self, ro_helper):
        self.ro_helper = ro_helper
        self.monster_detector = getattr(ro_helper, 'monster_detector', None)
        
        # GUI設定
        self.root = tk.Tk()
        self.root.title("Maple Helper - 怪物檢測")
        # 調整視窗大小和位置
        window_width = 800
        window_height = 600
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        x = (screen_width - window_width) // 2
        y = (screen_height - window_height) // 2
        self.root.geometry(f"{window_width}x{window_height}+{x}+{y}")
        self.root.resizable(True, True)
        
        # 設定主題樣式
        style = ttk.Style()
        style.configure("TLabel", padding=1)
        style.configure("TButton", padding=1)
        style.configure("TLabelframe", padding=2)
        
        # 執行控制
        self.is_running = False
        self.detection_enabled = tk.BooleanVar(value=True)
        self.detection_thread = None
        
        # 更新間隔設定
        self.update_interval = tk.StringVar(value="3000")
        
        # 檢測結果資料
        self.last_detection_results = []
        self.detection_history = []
        self.detection_stats = {'total_detections': 0, 'unique_monsters': set()}
        
        # 建立GUI介面
        self._create_gui()
        
        # 啟動檢測
        self._start_detection()
        
        print("🎮 怪物檢測GUI已啟動")
    
    def _create_gui(self):
        """建立完整GUI介面"""
        # 主要容器
        main_container = ttk.Frame(self.root)
        main_container.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)
        
        # 左側面板：控制和統計
        left_panel = ttk.Frame(main_container)
        left_panel.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 2))
        
        # 右側面板：檢測結果
        right_panel = ttk.Frame(main_container)
        right_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # 建立所有控制面板
        self._create_control_panel(left_panel)
        self._create_statistics_panel(left_panel)
        self._create_detection_results_display(right_panel)
        # 添加自動打怪控制面板
        self._create_auto_hunt_controls(left_panel)
    
    def _create_control_panel(self, parent):
        """✅ 改良版控制面板布局（存儲引用）"""
        self.control_frame = ttk.LabelFrame(parent, text="控制面板", padding=2)
        self.control_frame.pack(fill=tk.X, pady=(0, 2))
        
        # 第一行：基本控制
        self.control_row1 = ttk.Frame(self.control_frame)
        self.control_row1.pack(fill=tk.X, pady=1)
        
        # 左側：啟用檢測
        ttk.Checkbutton(self.control_row1, text="啟用檢測",
                    variable=self.detection_enabled).pack(side=tk.LEFT)
        
        # 右側：按鈕組
        button_frame = ttk.Frame(self.control_row1)
        button_frame.pack(side=tk.RIGHT)
        
        ttk.Button(button_frame, text="🔄 檢測",
                command=self._manual_detection).pack(side=tk.LEFT, padx=1)
        ttk.Button(button_frame, text="📸 保存",
                command=self._detect_and_save).pack(side=tk.LEFT, padx=1)
        ttk.Button(button_frame, text="💾 對比",
                command=self._save_comparison).pack(side=tk.LEFT, padx=1)
        ttk.Button(button_frame, text="📋 清除",
                command=self._clear_results).pack(side=tk.LEFT, padx=1)
        
        # 預留空間給動態添加的按鈕
        self.dynamic_button_area = ttk.Frame(self.control_row1)
        self.dynamic_button_area.pack(side=tk.LEFT, padx=(10, 0))
    
    def _create_detection_results_display(self, parent):
        """優化檢測結果顯示區域"""
        results_frame = ttk.LabelFrame(parent, text="檢測結果", padding=2)
        results_frame.pack(fill=tk.BOTH, expand=True)
        
        # 建立筆記本容器
        notebook = ttk.Notebook(results_frame)
        notebook.pack(fill=tk.BOTH, expand=True)
        
        # 設定筆記本樣式
        style = ttk.Style()
        style.configure("TNotebook", padding=1)
        style.configure("TNotebook.Tab", padding=[3, 1])
        
        # 頁籤1：即時檢測結果
        self._create_realtime_results_tab(notebook)
        
        # 頁籤2：詳細資訊
        self._create_detailed_info_tab(notebook)
        
        # 頁籤3：檢測歷史
        self._create_history_tab(notebook)
    
    def add_waypoint_button(self, button_text: str, command_function):
        """✅ 簡化版：直接添加到預留區域"""
        try:
            # 如果有預留的動態按鈕區域
            if hasattr(self, 'dynamic_button_area') and self.dynamic_button_area:
                self.waypoint_button = ttk.Button(self.dynamic_button_area, 
                                                text=button_text,
                                                command=command_function)
                self.waypoint_button.pack(side=tk.LEFT, padx=2)
                print(f"✅ 路徑編輯按鈕已添加到預留區域: {button_text}")
                return True
            
            # 備用方案：添加到主窗口
            if hasattr(self, 'root'):
                button_frame = ttk.Frame(self.root)
                button_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=5, pady=2)
                
                self.waypoint_button = ttk.Button(button_frame, text=button_text,
                                                command=command_function)
                self.waypoint_button.pack(side=tk.LEFT, padx=5)
                
                print(f"✅ 路徑編輯按鈕已添加到底部: {button_text}")
                return True
                
            return False
            
        except Exception as e:
            print(f"❌ 添加按鈕失敗: {e}")
            return False

    def _create_realtime_results_tab(self, parent):
        """創建即時檢測結果頁籤"""
        realtime_frame = ttk.Frame(parent)
        parent.add(realtime_frame, text="即時檢測")
        
        # 狀態列
        status_frame = ttk.Frame(realtime_frame)
        status_frame.pack(fill=tk.X, pady=2)
        
        self.status_label = ttk.Label(status_frame, text="🟡 檢測狀態：等待中")
        self.status_label.pack(side=tk.LEFT)
        
        self.fps_label = ttk.Label(status_frame, text="FPS: 0")
        self.fps_label.pack(side=tk.RIGHT)
        
        # 分割視窗：左側畫布，右側列表
        paned_window = ttk.PanedWindow(realtime_frame, orient=tk.HORIZONTAL)
        paned_window.pack(fill=tk.BOTH, expand=True)
        
        # 左側：檢測結果畫布
        canvas_frame = ttk.Frame(paned_window)
        paned_window.add(canvas_frame, weight=2)  # 畫布佔用更多空間
        
        self.detection_canvas = tk.Canvas(canvas_frame, bg="black", width=400, height=300)
        self.detection_canvas.pack(fill=tk.BOTH, expand=True)
        
        # 右側：怪物列表
        list_frame = ttk.Frame(paned_window)
        paned_window.add(list_frame, weight=1)
        
        ttk.Label(list_frame, text="檢測到的怪物：").pack(anchor=tk.W)
        
        # 創建樹狀列表
        columns = ('#', '名稱', '信心度', 'X', 'Y', '時間')
        self.monster_tree = ttk.Treeview(list_frame, columns=columns, show='headings', height=10)
        
        # 設定列寬
        self.monster_tree.column('#', width=30)
        self.monster_tree.column('名稱', width=100)
        self.monster_tree.column('信心度', width=80)
        self.monster_tree.column('X', width=60)
        self.monster_tree.column('Y', width=60)
        self.monster_tree.column('時間', width=80)
        
        # 設定列標題
        for col in columns:
            self.monster_tree.heading(col, text=col)
        
        # 添加滾動條
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.monster_tree.yview)
        self.monster_tree.configure(yscrollcommand=scrollbar.set)
        
        # 放置樹狀列表和滾動條
        self.monster_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    
    def _create_detailed_info_tab(self, notebook):
        """建立詳細資訊頁籤"""
        detail_frame = ttk.Frame(notebook)
        notebook.add(detail_frame, text="📋 詳細資訊")
        
        # 詳細資訊文字框
        self.detail_text = tk.Text(detail_frame, wrap=tk.WORD, font=("Consolas", 10))
        detail_scroll = ttk.Scrollbar(detail_frame, orient=tk.VERTICAL, command=self.detail_text.yview)
        self.detail_text.configure(yscrollcommand=detail_scroll.set)
        
        self.detail_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        detail_scroll.pack(side=tk.RIGHT, fill=tk.Y)
    
    def _create_history_tab(self, notebook):
        """建立檢測歷史頁籤"""
        history_frame = ttk.Frame(notebook)
        notebook.add(history_frame, text="📚 檢測歷史")
        
        # 歷史控制
        history_control = ttk.Frame(history_frame)
        history_control.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Button(history_control, text="🗑️ 清除歷史", 
                  command=self._clear_history).pack(side=tk.LEFT)
        
        ttk.Label(history_control, text="顯示最近：").pack(side=tk.LEFT, padx=(20, 5))
        self.history_limit = tk.StringVar(value="100")
        limit_combo = ttk.Combobox(history_control, textvariable=self.history_limit,
                                  values=["50", "100", "200", "500", "全部"],
                                  width=8, state="readonly")
        limit_combo.pack(side=tk.LEFT)
        
        # 歷史列表
        self.history_text = tk.Text(history_frame, wrap=tk.WORD, font=("Consolas", 9))
        history_scroll = ttk.Scrollbar(history_frame, orient=tk.VERTICAL, command=self.history_text.yview)
        self.history_text.configure(yscrollcommand=history_scroll.set)
        
        self.history_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        history_scroll.pack(side=tk.RIGHT, fill=tk.Y)
    
    def _create_statistics_panel(self, parent):
        """優化統計面板布局"""
        stats_frame = ttk.LabelFrame(parent, text="統計資訊", padding=2)
        stats_frame.pack(fill=tk.X, pady=(2, 0))
        
        # 使用Grid布局來更好地排列統計資訊
        stats_frame.columnconfigure(0, weight=1)
        stats_frame.columnconfigure(1, weight=1)
        
        # 第一行統計
        row1 = ttk.Frame(stats_frame)
        row1.grid(row=0, column=0, columnspan=2, sticky="ew", pady=1)
        
        self.total_detections_label = ttk.Label(row1, text="總檢測: 0", font=("Arial", 9, "bold"))
        self.total_detections_label.pack(side=tk.LEFT, padx=5)
        
        self.unique_monsters_label = ttk.Label(row1, text="怪物種類: 0", font=("Arial", 9, "bold"))
        self.unique_monsters_label.pack(side=tk.RIGHT, padx=5)
        
        # 第二行統計
        row2 = ttk.Frame(stats_frame)
        row2.grid(row=1, column=0, columnspan=2, sticky="ew", pady=1)
        
        self.avg_confidence_label = ttk.Label(row2, text="信心度: 0.00", font=("Arial", 9))
        self.avg_confidence_label.pack(side=tk.LEFT, padx=5)
        
        self.detection_rate_label = ttk.Label(row2, text="頻率: 0/分鐘", font=("Arial", 9))
        self.detection_rate_label.pack(side=tk.LEFT, padx=5)
        
        # 第三行統計
        row3 = ttk.Frame(stats_frame)
        row3.grid(row=2, column=0, columnspan=2, sticky="ew", pady=1)
        
        self.session_time_label = ttk.Label(row3, text="運行時間: 0秒", font=("Arial", 9))
        self.session_time_label.pack(side=tk.LEFT, padx=5)
    
    def _start_detection(self):
        """啟動檢測執行緒"""
        if not self.is_running:
            self.is_running = True
            self.detection_thread = threading.Thread(target=self._detection_loop, daemon=True)
            self.detection_thread.start()
            self.session_start_time = time.time()
    
    def _detection_loop(self):
        """檢測主迴圈"""
        last_update_time = time.time()
        
        while self.is_running:
            try:
                if self.detection_enabled.get():
                    # 執行檢測
                    monsters = self._perform_detection()
                    
                    # 更新GUI（主執行緒）
                    self.root.after(0, self._update_detection_results, monsters)
                    
                    # 計算FPS
                    current_time = time.time()
                    fps = 1.0 / (current_time - last_update_time) if current_time > last_update_time else 0
                    self.root.after(0, self._update_fps_display, fps)
                    last_update_time = current_time
                
                # 等待間隔
                interval = int(self.update_interval.get()) / 1000.0
                time.sleep(interval)
                
            except Exception as e:
                print(f"檢測迴圈錯誤: {e}")
                time.sleep(1)
    
    def _perform_detection(self):
        """執行怪物檢測"""
        try:
            if not self.ro_helper or not hasattr(self.ro_helper, 'capturer'):
                return []
            
            # 獲取遊戲畫面
            frame = self.ro_helper.capturer.grab_frame()
            if frame is None:
                return []
            
            # 執行怪物檢測
            if self.monster_detector:
                monsters = self.monster_detector.detect_monsters(frame)
                return monsters if monsters else []
            
            return []
            
        except Exception as e:
            print(f"檢測執行錯誤: {e}")
            return []
    
    def _update_detection_results(self, monsters):
        """更新檢測結果顯示"""
        try:
            # 清空畫布
            self.detection_canvas.delete("all")
            
            # 如果有遊戲畫面，顯示在畫布上
            if hasattr(self.ro_helper, 'capturer'):
                frame = self.ro_helper.capturer.grab_frame()
                if frame is not None:
                    # 使用共用工具類創建畫布圖片
                    CanvasUtils.create_canvas_image(
                        self.detection_canvas, frame,
                        scale_factor=1.0, fill_mode=True
                    )
            
            # 在畫布上標記檢測到的怪物
            for monster in monsters:
                # 獲取相對座標
                x = monster.get('x', 0)
                y = monster.get('y', 0)
                confidence = monster.get('confidence', 0)
                
                # 使用共用工具類繪製點標記
                CanvasUtils.draw_point_on_canvas(
                    self.detection_canvas, x, y,
                    radius=5, fill="red", outline="white",
                    text=f"{monster.get('name', 'Unknown')} ({confidence:.2f})",
                    text_color="white",
                    scale_factor=1.0
                )
            
            # 更新樹狀列表
            self.monster_tree.delete(*self.monster_tree.get_children())
            
            for i, monster in enumerate(monsters, 1):
                self.monster_tree.insert('', 'end', values=(
                    i,
                    monster.get('name', 'Unknown'),
                    f"{monster.get('confidence', 0):.2f}",
                    f"{monster.get('x', 0):.3f}",
                    f"{monster.get('y', 0):.3f}",
                    datetime.now().strftime("%H:%M:%S")
                ))
            
            # 更新統計資訊
            self._update_statistics(monsters)
            
        except Exception as e:
            print(f"更新檢測結果錯誤: {e}")
    
    def _update_detailed_info(self, monsters, current_time):
        """更新詳細資訊頁籤"""
        try:
            self.detail_text.delete('1.0', tk.END)
            
            info_lines = [
                f"🕐 檢測時間: {current_time}",
                f"🎯 檢測到 {len(monsters)} 隻怪物",
                "=" * 60
            ]
            
            if monsters:
                # 怪物統計
                monster_counts = {}
                for monster in monsters:
                    name = monster.get('name', 'Unknown')
                    monster_counts[name] = monster_counts.get(name, 0) + 1
                
                info_lines.append("📊 怪物分布統計:")
                for name, count in monster_counts.items():
                    info_lines.append(f"   {name}: {count} 隻")
                
                info_lines.append("")
                info_lines.append("🔍 詳細檢測資訊:")
                
                for i, monster in enumerate(monsters, 1):
                    name = monster.get('name', 'Unknown')
                    confidence = monster.get('confidence', 0)
                    pos = monster.get('position', (0, 0))
                    
                    info_lines.extend([
                        f"#{i} {name}",
                        f"   📍 位置: ({pos[0]}, {pos[1]})",
                        f"   📊 信心度: {confidence:.4f}",
                        f"   🎭 匹配類型: {monster.get('match_type', 'unknown')}"
                    ])
                    
                    # 顯示額外資訊
                    if 'template_size' in monster:
                        size = monster['template_size']
                        info_lines.append(f"   📏 模板大小: {size[0]}×{size[1]}")
                    
                    if 'frame_id' in monster:
                        frame_id = monster['frame_id']
                        scale = monster.get('scale', 1.0)
                        info_lines.append(f"   🎬 動畫: 幀{frame_id} 縮放{scale:.2f}x")
                    
                    info_lines.append("")
            else:
                info_lines.extend([
                    "❌ 未檢測到任何怪物",
                    "",
                    "💡 建議檢查事項:",
                    "   • 確認遊戲畫面中有怪物",
                    "   • 檢查模板檔案是否正確載入",
                    "   • 確認BlueStacks視窗可見"
                ])
            
            self.detail_text.insert('1.0', '\n'.join(info_lines))
            
        except Exception as e:
            print(f"詳細資訊更新錯誤: {e}")
    
    def _update_history(self, monsters, current_time):
        """更新檢測歷史"""
        try:
            if monsters:
                # 記錄到歷史
                history_entry = {
                    'time': current_time,
                    'monsters': monsters,
                    'count': len(monsters)
                }
                self.detection_history.append(history_entry)
                
                # 限制歷史記錄數量
                if len(self.detection_history) > 1000:
                    self.detection_history = self.detection_history[-500:]
                
                # 更新歷史顯示
                limit_str = self.history_limit.get()
                if limit_str == "全部":
                    display_history = self.detection_history
                else:
                    limit = int(limit_str)
                    display_history = self.detection_history[-limit:]
                
                # 更新歷史文字框
                self.history_text.delete('1.0', tk.END)
                
                history_lines = []
                for entry in reversed(display_history):  # 最新的在上面
                    monsters_summary = {}
                    for monster in entry['monsters']:
                        name = monster.get('name', 'Unknown')
                        monsters_summary[name] = monsters_summary.get(name, 0) + 1
                    
                    summary_text = ', '.join([f"{name}×{count}" for name, count in monsters_summary.items()])
                    history_lines.append(f"[{entry['time']}] {summary_text}")
                
                self.history_text.insert('1.0', '\n'.join(history_lines))
                
        except Exception as e:
            print(f"歷史更新錯誤: {e}")
    
    def _update_statistics(self, monsters):
        """更新統計資訊"""
        try:
            # 更新統計數據
            if monsters:
                self.detection_stats['total_detections'] += len(monsters)
                for monster in monsters:
                    name = monster.get('name', 'Unknown')
                    self.detection_stats['unique_monsters'].add(name)
            
            # 計算運行時間
            if hasattr(self, 'session_start_time'):
                session_time = int(time.time() - self.session_start_time)
                hours = session_time // 3600
                minutes = (session_time % 3600) // 60
                seconds = session_time % 60
                time_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
            else:
                time_str = "00:00:00"
            
            # 計算平均信心度
            if monsters:
                avg_confidence = sum(m.get('confidence', 0) for m in monsters) / len(monsters)
            else:
                avg_confidence = 0
            
            # 計算檢測頻率
            if hasattr(self, 'session_start_time') and session_time > 0:
                detection_rate = (self.detection_stats['total_detections'] / session_time) * 60
            else:
                detection_rate = 0
            
            # 更新標籤
            self.total_detections_label.config(
                text=f"總檢測次數: {self.detection_stats['total_detections']}")
            self.unique_monsters_label.config(
                text=f"發現怪物種類: {len(self.detection_stats['unique_monsters'])}")
            self.session_time_label.config(text=f"運行時間: {time_str}")
            self.avg_confidence_label.config(text=f"平均信心度: {avg_confidence:.2f}")
            self.detection_rate_label.config(text=f"檢測頻率: {detection_rate:.1f}/分鐘")
            
        except Exception as e:
            print(f"統計更新錯誤: {e}")
    
    def _update_fps_display(self, fps):
        """更新FPS顯示"""
        try:
            self.fps_label.config(text=f"FPS: {fps:.1f}")
        except Exception as e:
            print(f"FPS更新錯誤: {e}")
    
    def _toggle_detection(self):
        """切換檢測狀態"""
        if self.detection_enabled.get():
            self.status_label.config(text="🟡 檢測狀態：啟動中...")
        else:
            self.status_label.config(text="🔴 檢測狀態：已停止")
    
    def _manual_detection(self):
        """手動檢測 - 簡化版"""
        try:
            if not self.ro_helper or not hasattr(self.ro_helper, 'capturer'):
                print("❌ 無法獲取capturer")
                return
            
            frame = self.ro_helper.capturer.grab_frame()
            if frame is None:
                print("❌ 無法獲取畫面")
                return
            
            if self.monster_detector:
                # ✅ 直接檢測，不用線程
                monsters = self.monster_detector.detect_monsters(frame)
                self._update_detection_results(monsters)
                print(f"手動檢測完成: 發現 {len(monsters)} 隻怪物")
            
        except Exception as e:
            print(f"手動檢測錯誤: {e}")
    
    def _clear_results(self):
        """清除檢測結果"""
        try:
            # 清空樹狀列表
            for item in self.monster_tree.get_children():
                self.monster_tree.delete(item)
            
            # 清空詳細資訊
            self.detail_text.delete('1.0', tk.END)
            
            # 重置結果
            self.last_detection_results = []
            
            print("檢測結果已清除")
        except Exception as e:
            print(f"清除結果錯誤: {e}")
    
    def _clear_history(self):
        """清除檢測歷史"""
        try:
            self.detection_history = []
            self.history_text.delete('1.0', tk.END)
            print("檢測歷史已清除")
        except Exception as e:
            print(f"清除歷史錯誤: {e}")
    
    def _export_results(self):
        """匯出檢測結果"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"monster_detection_results_{timestamp}.json"
            
            export_data = {
                'timestamp': datetime.now().isoformat(),
                'detection_stats': {
                    'total_detections': self.detection_stats['total_detections'],
                    'unique_monsters': list(self.detection_stats['unique_monsters'])
                },
                'last_results': self.last_detection_results,
                'history': self.detection_history[-100:]  # 最近100筆記錄
            }
            
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False, default=str)
            
            print(f"檢測結果已匯出到: {filename}")
            
        except Exception as e:
            print(f"匯出結果錯誤: {e}")
    
    def _update_threshold(self, value):
        """更新檢測閾值"""
        try:
            threshold = float(value)
            self.threshold_label.config(text=f"{threshold:.2f}")
            if self.monster_detector:
                self.monster_detector.detection_threshold = threshold
        except Exception as e:
            print(f"閾值更新錯誤: {e}")            
    
    def run(self):
        """執行GUI主迴圈"""
        try:
            self.root.protocol("WM_DELETE_WINDOW", self._on_closing)
            self.root.mainloop()
        except Exception as e:
            print(f"GUI運行錯誤: {e}")
    
    def _on_closing(self):
        """關閉視窗時的處理"""
        try:
            print("正在關閉怪物檢測GUI...")
            self.is_running = False
            
            if self.detection_thread and self.detection_thread.is_alive():
                self.detection_thread.join(timeout=2)
            
            self.root.destroy()
            print("怪物檢測GUI已關閉")
            
        except Exception as e:
            print(f"關閉GUI錯誤: {e}")
    
    def stop(self):
        """停止檢測"""
        self.is_running = False
        if hasattr(self, 'root'):
            self.root.quit()

    def _handle_test_results(self, results):
        """處理測試結果（在主線程中執行）"""
        try:
            if results:
                self._update_detection_results(results)
                self.status_label.config(text=f"🎉 基礎測試成功: {len(results)} 個結果")
                print(f"🎉 基礎測試成功: {len(results)} 個結果")
            else:
                print("❌ 基礎測試失敗，嘗試保存調試圖片")
                self.status_label.config(text="❌ 基礎測試無結果")
        except Exception as e:
            print(f"❌ 處理結果錯誤: {e}")
            self.status_label.config(text=f"❌ 處理結果錯誤: {e}")       

    def _handle_real_test_results(self, results):
        """處理實際模板測試結果"""
        try:
            if results:
                self._update_detection_results(results)
                # 顯示檢測框
                frame = self.ro_helper.capturer.grab_frame()
                if frame is not None:
                    self.monster_detector.debug_show_detections_with_boxes(frame, results)
                
                print(f"🎉 實際模板測試成功: {len(results)} 個結果")
            else:
                print("❌ 實際模板測試無結果")
                
        except Exception as e:
            print(f"❌ 處理實際模板結果錯誤: {e}")            

    def _create_template(self):
        """製作模板"""
        try:
            if not self.ro_helper or not hasattr(self.ro_helper, 'capturer'):
                print("❌ 無法獲取capturer")
                return
            
            frame = self.ro_helper.capturer.grab_frame()
            if frame is None:
                print("❌ 無法獲取畫面")
                return
            
            if self.monster_detector:
                self.monster_detector.create_template_from_game(frame)
            
        except Exception as e:
            print(f"❌ 製作模板失敗: {e}")

    def _auto_detect_regions(self):
        """自動檢測怪物區域"""
        try:
            if not self.ro_helper or not hasattr(self.ro_helper, 'capturer'):
                return
            
            frame = self.ro_helper.capturer.grab_frame()
            if frame is None:
                return
            
            if self.monster_detector:
                regions = self.monster_detector.auto_detect_monster_regions(frame)
                print(f"🔍 自動檢測完成: {len(regions)} 個候選區域")
            
        except Exception as e:
            print(f"❌ 自動檢測失敗: {e}")            

    def _debug_auto_detection(self):
        """調試自動檢測功能"""
        try:
            if not self.ro_helper or not hasattr(self.ro_helper, 'capturer'):
                return
            
            frame = self.ro_helper.capturer.grab_frame()
            if frame is None:
                return
            
            if self.monster_detector:
                print("🔧 開始調試自動檢測...")
                
                # 執行自動檢測並保存詳細調試信息
                regions = self.monster_detector.auto_detect_monster_regions(frame)
                
                print(f"🔧 調試完成: 找到 {len(regions)} 個候選區域")
                
                if len(regions) > 0:
                    print("🔍 候選區域詳情:")
                    for i, region in enumerate(regions):
                        print(f"   區域{i}: 位置({region['x']}, {region['y']}) "
                            f"尺寸{region['w']}×{region['h']} 面積{region['area']}")
                else:
                    print("❌ 沒有找到候選區域，請檢查 debug_edges.png 查看邊緣檢測結果")
            
        except Exception as e:
            print(f"❌ 調試自動檢測失敗: {e}")            

    def _debug_pipeline(self):
        """調試檢測流程"""
        try:
            if not self.ro_helper or not hasattr(self.ro_helper, 'capturer'):
                return
            
            frame = self.ro_helper.capturer.grab_frame()
            if frame is None:
                return
            
            if self.monster_detector:
                print("🔍 開始調試檢測流程...")
                
                # 保存流程調試圖片
                self.monster_detector.save_debug_pipeline_images(frame)
                
                # 執行標準檢測
                results = self.monster_detector.detect_monsters(frame)
                
                if results:
                    self._update_detection_results(results)
                    print(f"🎯 流程調試完成: {len(results)} 個結果")
                else:
                    print("❌ 流程調試完成但無檢測結果")
            
        except Exception as e:
            print(f"❌ 流程調試失敗: {e}")            

    def _feature_matching_test(self):
        """特徵匹配測試"""
        try:
            if not self.ro_helper or not hasattr(self.ro_helper, 'capturer'):
                return
            
            frame = self.ro_helper.capturer.grab_frame()
            if frame is None:
                return
            
            if self.monster_detector:
                # 執行特徵匹配檢測
                results = self.monster_detector.detect_monsters_with_features(frame)
                
                if results:
                    self._update_detection_results(results)
                    print(f"🎯 特徵匹配完成: {len(results)} 個結果")
                else:
                    print("❌ 特徵匹配無結果")
            
        except Exception as e:
            print(f"❌ 特徵匹配測試失敗: {e}")

    def _hybrid_detection_test(self):
        """混合檢測測試"""
        try:
            if not self.ro_helper or not hasattr(self.ro_helper, 'capturer'):
                return
            
            frame = self.ro_helper.capturer.grab_frame()
            if frame is None:
                return
            
            if self.monster_detector:
                # 執行混合檢測
                results = self.monster_detector.detect_monsters_hybrid(frame)
                
                if results:
                    self._update_detection_results(results)
                    print(f"🔀 混合檢測完成: {len(results)} 個結果")
                else:
                    print("❌ 混合檢測無結果")
            
        except Exception as e:
            print(f"❌ 混合檢測測試失敗: {e}")            

    def _detect_and_save(self):
        """檢測並保存結果圖片"""
        try:
            if not self.ro_helper or not hasattr(self.ro_helper, 'capturer'):
                print("❌ 無法獲取capturer")
                return
            
            frame = self.ro_helper.capturer.grab_frame()
            if frame is None:
                print("❌ 無法獲取畫面")
                return
            
            if self.monster_detector:
                # 執行檢測並自動保存結果圖片
                results = self.monster_detector.detect_and_save_result(frame)
                
                if results:
                    self._update_detection_results(results)
                    print(f"📸 檢測+保存完成: {len(results)} 個結果")
                else:
                    print("📸 無檢測結果，已保存原始畫面供檢查")
            
        except Exception as e:
            print(f"❌ 檢測+保存失敗: {e}")

    def _save_comparison(self):
        """保存當前畫面和模板用於對比"""
        try:
            if not self.ro_helper or not hasattr(self.ro_helper, 'capturer'):
                return
            
            frame = self.ro_helper.capturer.grab_frame()
            if frame is None:
                return
            
            if self.monster_detector:
                self.monster_detector.save_current_frame_and_templates(frame)
                print("💾 當前畫面和模板已保存")
            
        except Exception as e:
            print(f"❌ 保存對比失敗: {e}")

    def _launch_test_mode(self):
        """✅ 啟動分離的測試模式"""
        try:
            print("🧪 啟動測試模式...")
            # 導入並啟動測試GUI（分離的）
            from tests.movement_test_gui import MovementTestGUI
            test_gui = MovementTestGUI(self.ro_helper)
            test_gui.run()
        except ImportError:
            print("❌ 測試模組不存在，請運行 python run_tests.py")
        except Exception as e:
            print(f"❌ 啟動測試模式失敗: {e}")

    def _create_auto_hunt_controls(self, parent_frame):
        """✅ 完整版：包含檔案管理和自動打怪功能"""
        try:
            # 檔案管理區域
            file_frame = ttk.LabelFrame(parent_frame, text="📁 地圖檔案管理")
            file_frame.pack(fill=tk.X, pady=5)
            
            # 檔案選擇和載入
            file_control_frame = ttk.Frame(file_frame)
            file_control_frame.pack(fill=tk.X, padx=5, pady=5)
            
            ttk.Label(file_control_frame, text="當前地圖:").pack(side=tk.LEFT)
            
            # 檔案下拉選單
            self.current_map_var = tk.StringVar()
            available_files = self.ro_helper.waypoint_system.get_available_map_files()
            self.map_combo = ttk.Combobox(file_control_frame, textvariable=self.current_map_var,
                                        values=available_files, width=20, state="readonly")
            self.map_combo.pack(side=tk.LEFT, padx=5)
            
            # 檔案操作按鈕
            ttk.Button(file_control_frame, text="📂 載入地圖", 
                    command=self._load_selected_map).pack(side=tk.LEFT, padx=2)
            ttk.Button(file_control_frame, text="💾 保存地圖", 
                    command=self._save_current_map).pack(side=tk.LEFT, padx=2)
            
            # 路徑編輯按鈕
            ttk.Button(file_control_frame, text="🗺️ 編輯路徑", 
                    command=self._open_waypoint_editor).pack(side=tk.LEFT, padx=2)
            
        except Exception as e:
            print(f"⚠️ 添加地圖管理功能失敗: {e}")

    def _open_waypoint_editor(self):
        """開啟路徑編輯器"""
        try:
            self.ro_helper.open_waypoint_editor()
        except Exception as e:
            print(f"⚠️ 開啟路徑編輯器失敗: {e}")

    def _load_selected_map(self):
        """主視窗載入地圖"""
        try:
            filename = getattr(self, 'current_map_var', tk.StringVar()).get()
            if not filename:
                print("❌ 請選擇要載入的地圖檔案")
                return
            
            # 載入到waypoint_system
            success = self.ro_helper.waypoint_system.load_specific_map(filename)
            if success:
                if hasattr(self, 'map_status_label'):
                    self.map_status_label.config(text=f"地圖: {filename}", foreground="green")
                print(f"✅ 主視窗載入地圖: {filename}")
                
                # 如果編輯器已開啟，同步更新
                if hasattr(self.ro_helper, 'waypoint_editor') and self.ro_helper.waypoint_editor:
                    if hasattr(self.ro_helper.waypoint_editor, 'editor_window') and self.ro_helper.waypoint_editor.editor_window:
                        self.ro_helper.waypoint_editor._draw()
                        print("🔄 同步更新編輯器顯示")
            else:
                if hasattr(self, 'map_status_label'):
                    self.map_status_label.config(text="載入失敗", foreground="red")
                
        except Exception as e:
            print(f"❌ 載入地圖失敗: {e}")   

    def _save_current_map(self):
        """主視窗保存地圖"""
        try:
            filename = getattr(self, 'current_map_var', tk.StringVar()).get()
            if not filename:
                print("❌ 請選擇要保存的檔案")
                return
            
            file_path = os.path.join("data", filename)
            self.ro_helper.waypoint_system.save_map_data(file_path)
            print(f"💾 地圖已保存: {filename}")
            
            if hasattr(self, 'map_status_label'):
                self.map_status_label.config(text=f"已保存: {filename}", foreground="blue")
            
        except Exception as e:
            print(f"❌ 保存地圖失敗: {e}")

    def _create_new_map(self):
        """創建新地圖檔案"""
        try:
            # 彈出對話框讓用戶輸入新地圖名稱
            from tkinter import simpledialog
            
            filename = simpledialog.askstring(
                "新建地圖", 
                "請輸入新地圖檔案名稱:",
                initialvalue="new_map"
            )
            
            if not filename:
                return
            
            # 確保檔案名有.json副檔名
            if not filename.endswith('.json'):
                filename += '.json'
            
            # 創建空的地圖數據
            empty_map_data = {
                "waypoints": [],
                "obstacles": [],
                "special_zones": [],
                "area_grid": {},
                "obstacle_types": {
                    'wall': {'name': '牆壁', 'color': 'red', 'passable': False},
                    'water': {'name': '水域', 'color': 'blue', 'passable': False},
                    'tree': {'name': '樹木', 'color': 'green', 'passable': False},
                    'building': {'name': '建築物', 'color': 'gray', 'passable': False}
                },
                "action_zones": {
                    'rope': {'name': '繩索', 'color': 'brown', 'action': 'climb_rope'},
                    'ladder': {'name': '階梯', 'color': 'yellow', 'action': 'climb_ladder'},
                    'door': {'name': '門', 'color': 'purple', 'action': 'open_door'},
                    'portal': {'name': '傳送點', 'color': 'cyan', 'action': 'use_portal'},
                    'npc': {'name': 'NPC', 'color': 'orange', 'action': 'talk_npc'}
                }
            }
            
            # 保存新地圖檔案
            import json
            import os
            
            file_path = os.path.join("data", filename)
            os.makedirs("data", exist_ok=True)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(empty_map_data, f, indent=2, ensure_ascii=False)
            
            # 載入新創建的地圖
            success = self.ro_helper.waypoint_system.load_specific_map(filename)
            if success:
                # 更新界面
                if hasattr(self, 'current_map_var'):
                    self.current_map_var.set(filename)
                
                if hasattr(self, 'map_status_label'):
                    self.map_status_label.config(text=f"地圖: {filename} (新建)", foreground="blue")
                
                # 重新整理檔案列表
                if hasattr(self, '_refresh_file_list'):
                    self._refresh_file_list()
                
                print(f"✅ 新地圖建立成功: {filename}")
            else:
                print(f"❌ 新地圖建立後載入失敗: {filename}")
                
        except Exception as e:
            print(f"❌ 建立新地圖失敗: {e}")
            if hasattr(self, 'map_status_label'):
                self.map_status_label.config(text="建立失敗", foreground="red")
        
    def _refresh_file_list(self):
        """重新整理檔案列表"""
        try:
            if hasattr(self, 'map_combo') and hasattr(self.ro_helper, 'waypoint_system'):
                available_files = self.ro_helper.waypoint_system.get_available_map_files()
                self.map_combo['values'] = available_files
                print(f"✅ 檔案列表已更新: {len(available_files)} 個檔案")
                
        except Exception as e:
            print(f"❌ 重新整理檔案列表失敗: {e}")
