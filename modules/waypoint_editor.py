# modules/waypoint_editor.py - 修復版

import os
import time
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import json
import cv2
import numpy as np
from PIL import Image, ImageTk, ImageDraw
import math
from pathlib import Path

class WaypointEditor:
    """路徑點編輯器 - 修復版"""
    
    def __init__(self, waypoint_system, tracker=None):
        self.waypoint_system = waypoint_system
        self.tracker = tracker
        self.editor_window = None
        self.canvas = None
        self.minimap_photo = None
        
        # 界面相關
        self.canvas_width = 800
        self.canvas_height = 600
        self.scale_factor = 1.0
        
        # ✅ 修復：統一編輯狀態管理
        self.edit_mode = tk.StringVar(value="waypoint")
        self.current_mode = "waypoint"  # 同步 current_mode
        self.selected_type = tk.StringVar(value="wall")
        
        # 拖曳相關
        self.is_dragging = False
        self.drawing_line = False
        self.drag_start_pos = None
        self.preview_line_id = None
        self.offset_x = 0
        self.offset_y = 0
        
        # 圖層顯示控制
        self.show_waypoints = tk.BooleanVar(value=True)
        self.show_areas = tk.BooleanVar(value=True)
        self.show_obstacles = tk.BooleanVar(value=True)
        
        # 網格控制
        self.snap_to_grid = tk.BooleanVar(value=True)
        self.show_grid = tk.BooleanVar(value=False)
        self.brush_size = tk.IntVar(value=20)  # 筆刷大小
        
        # GUI 元件
        self.coord_label = None
        self.status_label = None
        self.info_label = None
        
        # ✅ 歷史記錄系統
        self.undo_history = {
            'past': [],
            'present': None,
            'future': []
        }
        
        # ✅ 檔案管理
        self.file_var = tk.StringVar()
        self.file_combo = None
        
        print("✅ 路徑編輯器已初始化（修復版）")
    
    def create_editor_window(self):
        """✅ 改良的編輯器視窗創建"""
        if self.editor_window is not None:
            self.editor_window.lift()
            self.editor_window.focus()
            self._draw()
            return

        # 自動偵測小地圖
        if self.tracker and hasattr(self.tracker, 'find_minimap'):
            try:
                self.tracker.find_minimap()
                print("✅ 已自動偵測小地圖")
            except Exception as e:
                print(f"❌ 自動偵測小地圖失敗: {e}")

        # 創建視窗
        self.editor_window = tk.Toplevel()
        self.editor_window.title("路徑點編輯器 - 修復版")
        self.editor_window.geometry("1200x800")
        self.editor_window.protocol("WM_DELETE_WINDOW", self._on_window_close)
        
        # ✅ 先創建介面
        self._create_editor_interface()
        
        # ✅ 延遲初始化小地圖，確保畫布完全準備好
        self.editor_window.after(100, self._initialize_minimap_and_draw)

    def _initialize_minimap_and_draw(self):
        """✅ 初始化小地圖並繪製"""
        try:
            # 強制更新畫布以確保尺寸正確
            self.canvas.update_idletasks()
            
            # 載入小地圖
            success = self._load_minimap()
            
            # 無論是否成功，都進行繪製
            self._draw()
            
            if not success:
                # 如果首次載入失敗，設置重試
                self._schedule_minimap_retry()
                
        except Exception as e:
            print(f"❌ 初始化小地圖失敗: {e}")
            self._draw()  # 即使失敗也要繪製基本介面

    def _schedule_minimap_retry(self, max_retries=3):
        """✅ 排程小地圖重試載入"""
        if not hasattr(self, '_minimap_retry_count'):
            self._minimap_retry_count = 0
        
        if self._minimap_retry_count < max_retries:
            self._minimap_retry_count += 1
            print(f"🔄 排程小地圖重試 ({self._minimap_retry_count}/{max_retries})")
            
            # 延遲重試
            self.canvas.after(500, self._retry_load_minimap)

    def _retry_load_minimap(self):
        """✅ 重試載入小地圖"""
        try:
            if hasattr(self, 'minimap_photo') and self.minimap_photo:
                return  # 已經載入成功
            
            success = self._load_minimap()
            if success:
                print("✅ 小地圖重試載入成功")
                self._draw()  # 重新繪製
            else:
                # 繼續重試
                self._schedule_minimap_retry()
                
        except Exception as e:
            print(f"❌ 小地圖重試失敗: {e}")
            self._schedule_minimap_retry()

    def _create_editor_interface(self):
        """創建編輯器介面"""
        try:
            # 主容器
            main_frame = ttk.Frame(self.editor_window)
            main_frame.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)

            # 左側：畫布區域
            canvas_frame = ttk.LabelFrame(main_frame, text="地圖編輯區域")
            canvas_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 2))
            self._create_canvas_area(canvas_frame)

            # 右側：控制面板
            control_frame = ttk.LabelFrame(main_frame, text="控制面板")
            control_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=(2, 0))
            
            # 檔案管理
            self._create_file_management(control_frame)
            
            # 編輯模式選擇
            self._create_mode_selection(control_frame)
            
            # 編輯工具
            self._create_editing_tools(control_frame)
            
            # 圖層控制
            self._create_layer_controls(control_frame)
            
            # 快捷操作
            self._create_quick_actions(control_frame)

            # 底部：狀態欄
            self.status_label = ttk.Label(main_frame, text="就緒", relief=tk.SUNKEN)
            self.status_label.pack(side=tk.BOTTOM, fill=tk.X, pady=(2, 0))
            
            print("✅ 編輯器介面已創建")
            
        except Exception as e:
            print(f"❌ 創建編輯器介面失敗: {e}")
            import traceback
            traceback.print_exc()

    def _create_canvas_area(self, parent):
        """創建畫布區域"""
        try:
            # 畫布和滾軸
            canvas_container = ttk.Frame(parent)
            canvas_container.pack(fill=tk.BOTH, expand=True)
            
            # 創建畫布
            self.canvas = tk.Canvas(
                canvas_container,
                width=self.canvas_width,
                height=self.canvas_height,
                bg="white",
                scrollregion=(0, 0, self.canvas_width, self.canvas_height)
            )
            
            # 滾軸
            v_scrollbar = ttk.Scrollbar(canvas_container, orient=tk.VERTICAL, command=self.canvas.yview)
            h_scrollbar = ttk.Scrollbar(canvas_container, orient=tk.HORIZONTAL, command=self.canvas.xview)
            self.canvas.configure(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)
            
            # 佈局
            self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            v_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
            h_scrollbar.pack(side=tk.BOTTOM, fill=tk.X)
            
            # ✅ 修復：綁定事件並同步編輯模式
            self.canvas.bind("<Button-1>", self._on_canvas_click)
            self.canvas.bind("<B1-Motion>", self._on_canvas_drag)
            self.canvas.bind("<ButtonRelease-1>", self._on_canvas_release)
            self.canvas.bind("<Motion>", self._update_coord_label)
            self.canvas.bind("<Configure>", self._on_canvas_resize)
            
            # 編輯模式同步
            self.edit_mode.trace('w', self._sync_edit_mode)
            
            print("✅ 畫布區域已創建")
            
        except Exception as e:
            print(f"❌ 創建畫布區域失敗: {e}")

    def _create_file_management(self, parent):
        """創建檔案管理區域"""
        file_frame = ttk.LabelFrame(parent, text="檔案管理")
        file_frame.pack(fill=tk.X, pady=(0, 2))
        
        # 檔案選擇
        ttk.Label(file_frame, text="地圖檔案:").pack(anchor=tk.W, padx=2)
        
        file_control = ttk.Frame(file_frame)
        file_control.pack(fill=tk.X, padx=2, pady=2)
        
        # 檔案下拉選單
        self.file_combo = ttk.Combobox(file_control, textvariable=self.file_var, 
                                      width=20, state="readonly")
        self.file_combo.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # 檔案操作按鈕
        file_buttons = ttk.Frame(file_frame)
        file_buttons.pack(fill=tk.X, padx=2, pady=2)
        
        ttk.Button(file_buttons, text="📂載入", command=self._load_selected_file).pack(side=tk.LEFT, padx=1)
        ttk.Button(file_buttons, text="💾保存", command=self._save_waypoints).pack(side=tk.LEFT, padx=1)
        ttk.Button(file_buttons, text="📄新建", command=self._create_new_path_file).pack(side=tk.LEFT, padx=1)
        ttk.Button(file_buttons, text="🔄刷新", command=self._refresh_file_list).pack(side=tk.LEFT, padx=1)
        
        # 初始化檔案列表
        self._refresh_file_list()

    def _create_mode_selection(self, parent):
        """創建編輯模式選擇"""
        mode_frame = ttk.LabelFrame(parent, text="編輯模式")
        mode_frame.pack(fill=tk.X, pady=(0, 2))
        
        modes = [
            ("➕ 路徑點", "waypoint"),
            ("🟢 可行走", "walkable"),
            ("🔴 禁止", "forbidden"),
            ("🟤 繩索", "rope"),
            ("❌ 刪除", "delete")
        ]
        
        for text, value in modes:
            ttk.Radiobutton(mode_frame, text=text, variable=self.edit_mode,
                          value=value).pack(anchor=tk.W, padx=2, pady=1)

    def _create_editing_tools(self, parent):
        """創建編輯工具"""
        tools_frame = ttk.LabelFrame(parent, text="編輯工具")
        tools_frame.pack(fill=tk.X, pady=(0, 2))
        
        # 筆刷大小
        brush_frame = ttk.Frame(tools_frame)
        brush_frame.pack(fill=tk.X, padx=2, pady=2)
        
        ttk.Label(brush_frame, text="筆刷大小:").pack(side=tk.LEFT)
        brush_scale = ttk.Scale(brush_frame, from_=5, to=50, variable=self.brush_size,
                               orient=tk.HORIZONTAL, length=100)
        brush_scale.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=2)
        
        self.brush_label = ttk.Label(brush_frame, text="20")
        self.brush_label.pack(side=tk.LEFT)
        
        # 更新筆刷標籤
        self.brush_size.trace('w', lambda *args: self.brush_label.config(text=str(self.brush_size.get())))
        
        # 編輯選項
        options_frame = ttk.Frame(tools_frame)
        options_frame.pack(fill=tk.X, padx=2, pady=2)
        
        ttk.Checkbutton(options_frame, text="吸附網格", 
                       variable=self.snap_to_grid).pack(anchor=tk.W)
        ttk.Checkbutton(options_frame, text="顯示網格", 
                       variable=self.show_grid).pack(anchor=tk.W)

    def _create_layer_controls(self, parent):
        """創建圖層控制"""
        layers_frame = ttk.LabelFrame(parent, text="圖層顯示")
        layers_frame.pack(fill=tk.X, pady=(0, 2))
        
        layers = [
            ("顯示路徑點", "show_waypoints"),
            ("顯示區域標記", "show_areas"),
            ("顯示障礙物", "show_obstacles")
        ]
        
        for text, var_name in layers:
            var = getattr(self, var_name)
            ttk.Checkbutton(layers_frame, text=text, 
                          variable=var, 
                          command=self._draw).pack(anchor=tk.W, padx=2, pady=1)

    def _create_quick_actions(self, parent):
        """創建快捷操作"""
        # 編輯資訊
        info_frame = ttk.LabelFrame(parent, text="編輯資訊")
        info_frame.pack(fill=tk.X, pady=(0, 2))
        
        self.info_label = ttk.Label(info_frame, text="0路徑點, 0障礙物, 0區域", 
                                   font=("Arial", 9))
        self.info_label.pack(pady=2)
        
        # 座標顯示
        self.coord_label = ttk.Label(info_frame, text="座標: (0.000, 0.000)")
        self.coord_label.pack(pady=2)
        
        # 快速工具
        tools_frame = ttk.LabelFrame(parent, text="快速操作")
        tools_frame.pack(fill=tk.X, pady=(0, 2))
        
        actions = [
            ("🔄 重繪", self._draw),
            ("🗑️ 清除", self._clear_all_confirm),
            ("↶ 撤消", self._undo),
            ("↷ 重做", self._redo)
        ]
        
        for text, command in actions:
            ttk.Button(tools_frame, text=text, command=command).pack(fill=tk.X, padx=2, pady=1)

    # =============== 事件處理 ===============

    def _sync_edit_mode(self, *args):
        """✅ 同步編輯模式"""
        self.current_mode = self.edit_mode.get()
        
        # 根據模式調整游標
        cursor_map = {
            "waypoint": "plus",
            "delete": "X_cursor",
            "walkable": "pencil",
            "forbidden": "pencil",
            "rope": "pencil"
        }
        
        cursor = cursor_map.get(self.current_mode, "arrow")
        if hasattr(self, 'canvas') and self.canvas:
            self.canvas.config(cursor=cursor)

    def _on_canvas_click(self, event):
        """✅ 修復：處理畫布點擊事件"""
        try:
            # 使用統一的座標轉換
            rel_x, rel_y = self._canvas_to_relative(event.x, event.y)
            
            # 保存當前狀態（用於撤消）
            self._save_current_state()
            
            mode = self.edit_mode.get()
            
            if mode == "waypoint":
                self._add_waypoint(rel_x, rel_y)
            elif mode == "delete":
                self._delete_nearest_element(rel_x, rel_y)
            elif mode in ["walkable", "forbidden", "rope"]:
                # 開始線條繪製
                self.is_dragging = True
                self.drawing_line = True
                self.drag_start_pos = (rel_x, rel_y)
                
            # 重繪
            self._draw()
            
        except Exception as e:
            print(f"❌ 處理畫布點擊失敗: {e}")

    def _on_canvas_drag(self, event):
        """✅ 處理畫布拖曳事件"""
        try:
            if not self.is_dragging:
                return
                
            rel_x, rel_y = self._canvas_to_relative(event.x, event.y)
            
            mode = self.edit_mode.get()
            
            if mode in ["walkable", "forbidden", "rope"] and self.drawing_line:
                # 更新預覽線條
                if self.preview_line_id:
                    self.canvas.delete(self.preview_line_id)
                
                # 繪製預覽線條
                start_canvas = self._relative_to_canvas(*self.drag_start_pos)
                end_canvas = self._relative_to_canvas(rel_x, rel_y)
                
                color_map = {
                    "walkable": "green",
                    "forbidden": "red",
                    "rope": "orange"
                }
                
                color = color_map.get(mode, "gray")
                self.preview_line_id = self.canvas.create_line(
                    start_canvas[0], start_canvas[1],
                    end_canvas[0], end_canvas[1],
                    fill=color, width=3, dash=(5, 5), tags="preview"
                )
                
        except Exception as e:
            print(f"❌ 處理拖曳失敗: {e}")

    def _on_canvas_release(self, event):
        """✅ 處理按鈕釋放事件"""
        try:
            if not self.is_dragging:
                return
            
            rel_x, rel_y = self._canvas_to_relative(event.x, event.y)
            mode = self.edit_mode.get()
            
            if mode in ["walkable", "forbidden", "rope"] and self.drawing_line:
                # 繪製線條上的所有點
                self._draw_line_area(self.drag_start_pos, (rel_x, rel_y), mode)
            
            # 清理
            if self.preview_line_id:
                self.canvas.delete(self.preview_line_id)
                self.preview_line_id = None
            
            self.is_dragging = False
            self.drawing_line = False
            self.drag_start_pos = None
            
            # 重繪
            self._draw()
            
        except Exception as e:
            print(f"❌ 處理按鈕釋放失敗: {e}")

    def _update_coord_label(self, event):
        """更新座標標籤"""
        try:
            rel_x, rel_y = self._canvas_to_relative(event.x, event.y)
            if hasattr(self, 'coord_label') and self.coord_label:
                self.coord_label.config(text=f"座標: ({rel_x:.3f}, {rel_y:.3f})")
        except Exception as e:
            pass  # 忽略座標更新錯誤

    def _on_canvas_resize(self, event):
        """畫布大小改變事件"""
        try:
            if event.widget == self.canvas:
                print(f"🔄 畫布大小改變: {event.width}x{event.height}")
                # 延遲重繪以確保尺寸已更新
                self.canvas.after(100, self._draw)
        except Exception as e:
            print(f"❌ 畫布大小改變處理失敗: {e}")

    # =============== 座標轉換 ===============

    def _canvas_to_relative(self, canvas_x, canvas_y):
        """✅ 統一的畫布座標到相對座標轉換"""
        try:
            if hasattr(self, '_editor_scale_info'):
                # 使用縮放資訊進行精確轉換
                offset = self._editor_scale_info.get('offset', (0, 0))
                display_size = self._editor_scale_info['display_size']
                
                rel_x = (canvas_x - offset[0]) / display_size[0]
                rel_y = (canvas_y - offset[1]) / display_size[1]
            else:
                # 備用方案
                canvas_width = self.canvas.winfo_width() or self.canvas_width
                canvas_height = self.canvas.winfo_height() or self.canvas_height
                
                rel_x = canvas_x / canvas_width
                rel_y = canvas_y / canvas_height
            
            # 確保在有效範圍內
            rel_x = max(0.0, min(1.0, rel_x))
            rel_y = max(0.0, min(1.0, rel_y))
            
            return rel_x, rel_y
            
        except Exception as e:
            print(f"❌ 座標轉換失敗: {e}")
            return 0.0, 0.0

    def _relative_to_canvas(self, rel_x, rel_y):
        """相對座標到畫布座標轉換"""
        try:
            if hasattr(self, '_editor_scale_info'):
                offset = self._editor_scale_info.get('offset', (0, 0))
                display_size = self._editor_scale_info['display_size']
                
                canvas_x = rel_x * display_size[0] + offset[0]
                canvas_y = rel_y * display_size[1] + offset[1]
            else:
                canvas_width = self.canvas.winfo_width() or self.canvas_width
                canvas_height = self.canvas.winfo_height() or self.canvas_height
                
                canvas_x = rel_x * canvas_width
                canvas_y = rel_y * canvas_height
            
            return canvas_x, canvas_y
            
        except Exception as e:
            print(f"❌ 座標轉換失敗: {e}")
            return 0, 0

    # =============== 編輯操作 ===============

    def _add_waypoint(self, rel_x, rel_y):
        """添加路徑點"""
        try:
            waypoint = {
                'id': len(self.waypoint_system.waypoints),
                'pos': (rel_x, rel_y),
                'name': f'路徑點_{len(self.waypoint_system.waypoints) + 1}'
            }
            self.waypoint_system.waypoints.append(waypoint)
            print(f"✅ 添加路徑點: {waypoint['name']} at ({rel_x:.3f}, {rel_y:.3f})")
            
            self._update_info_labels()
            
        except Exception as e:
            print(f"❌ 添加路徑點失敗: {e}")

    def _draw_line_area(self, start_pos, end_pos, area_type):
        """在線條路徑上繪製區域標記"""
        try:
            # 計算線條上的點
            line_points = self._get_line_points(start_pos, end_pos)
            
            brush_size = self.brush_size.get() / 1000.0  # 轉換為相對大小
            
            for point in line_points:
                # 在每個點周圍繪製區域
                grid_key = f"{point[0]:.3f},{point[1]:.3f}"
                self.waypoint_system.area_grid[grid_key] = area_type
            
            print(f"✅ 繪製{area_type}線條: {len(line_points)}個點")
            
        except Exception as e:
            print(f"❌ 繪製線條區域失敗: {e}")

    def _get_line_points(self, start_pos, end_pos, step=0.01):
        """獲取線條上的點"""
        points = []
        
        dx = end_pos[0] - start_pos[0]
        dy = end_pos[1] - start_pos[1]
        distance = (dx**2 + dy**2)**0.5
        
        if distance == 0:
            return [start_pos]
        
        num_steps = max(1, int(distance / step))
        
        for i in range(num_steps + 1):
            t = i / num_steps
            x = start_pos[0] + t * dx
            y = start_pos[1] + t * dy
            points.append((x, y))
        
        return points

    def _delete_nearest_element(self, rel_x, rel_y):
        """刪除最近的元素"""
        try:
            min_distance = float('inf')
            to_delete = None
            delete_type = None
            
            # 檢查路徑點
            for i, waypoint in enumerate(self.waypoint_system.waypoints):
                pos = waypoint['pos']
                distance = ((pos[0] - rel_x)**2 + (pos[1] - rel_y)**2)**0.5
                if distance < min_distance and distance < 0.05:  # 5%的範圍
                    min_distance = distance
                    to_delete = i
                    delete_type = "waypoint"
            
            # 檢查區域標記
            for grid_key in list(self.waypoint_system.area_grid.keys()):
                if isinstance(grid_key, str) and ',' in grid_key:
                    x_str, y_str = grid_key.split(',')
                    pos_x, pos_y = float(x_str), float(y_str)
                    distance = ((pos_x - rel_x)**2 + (pos_y - rel_y)**2)**0.5
                    if distance < min_distance and distance < 0.03:  # 3%的範圍
                        min_distance = distance
                        to_delete = grid_key
                        delete_type = "area"
            
            # 執行刪除
            if to_delete is not None:
                if delete_type == "waypoint":
                    deleted = self.waypoint_system.waypoints.pop(to_delete)
                    print(f"🗑️ 刪除路徑點: {deleted['name']}")
                elif delete_type == "area":
                    area_type = self.waypoint_system.area_grid.pop(to_delete)
                    print(f"🗑️ 刪除區域標記: {to_delete} ({area_type})")
                
                self._update_info_labels()
            
        except Exception as e:
            print(f"❌ 刪除操作失敗: {e}")

    # =============== 小地圖處理 ===============

    def _load_minimap(self):
        """✅ 改良的小地圖載入"""
        try:
            # 方法1：從tracker載入
            if self.tracker and hasattr(self.tracker, 'minimap_img'):
                minimap_img = self.tracker.minimap_img
                if minimap_img is not None:
                    return self._process_minimap_image(minimap_img)
            
            # 方法2：從檔案載入
            if hasattr(self.waypoint_system, 'minimap_path') and self.waypoint_system.minimap_path:
                if os.path.exists(self.waypoint_system.minimap_path):
                    image = Image.open(self.waypoint_system.minimap_path)
                    return self._process_pil_image(image)
            
            # 方法3：尋找預設小地圖檔案
            minimap_paths = [
                "data/minimap.png",
                "minimap.png",
                "assets/minimap.png",
                "images/minimap.png"
            ]
            
            for path in minimap_paths:
                if os.path.exists(path):
                    image = Image.open(path)
                    return self._process_pil_image(image)
            
            # 方法4：創建預設背景
            print("⚠️ 沒有找到小地圖，創建預設背景")
            self._create_default_background()
            return True
            
        except Exception as e:
            print(f"❌ 載入小地圖失敗: {e}")
            self._create_default_background()
            return False

    def _process_minimap_image(self, minimap_img):
        """處理OpenCV格式的小地圖"""
        try:
            # 轉換為RGB
            minimap_rgb = cv2.cvtColor(minimap_img, cv2.COLOR_BGR2RGB)
            
            # 轉換為PIL圖片
            image = Image.fromarray(minimap_rgb)
            
            return self._process_pil_image(image)
            
        except Exception as e:
            print(f"❌ 處理小地圖圖片失敗: {e}")
            return False

    def _process_pil_image(self, image):
        """處理PIL圖片"""
        try:
            # 強制更新畫布尺寸
            self.canvas.update_idletasks()
            
            canvas_width = self.canvas.winfo_width()
            canvas_height = self.canvas.winfo_height()
            
            # 處理初始化時畫布大小為1的問題
            if canvas_width <= 1 or canvas_height <= 1:
                canvas_width = self.canvas_width
                canvas_height = self.canvas_height
                # 延遲重新載入
                self.canvas.after(200, self._load_minimap)
                return False
            
            print(f"🖼️ 畫布大小: {canvas_width}x{canvas_height}")
            print(f"🖼️ 原始圖片: {image.size}")
            
            # 縮放圖片以適應畫布
            resized_image = self._resize_image_to_canvas(image, canvas_width, canvas_height)
            self.minimap_photo = ImageTk.PhotoImage(resized_image)
            
            # 保存縮放資訊
            self._editor_scale_info = {
                'display_size': resized_image.size,
                'original_size': image.size,
                'scale_factor': min(canvas_width/image.width, canvas_height/image.height)
            }
            
            print(f"✅ 小地圖處理完成: {resized_image.size}")
            return True
            
        except Exception as e:
            print(f"❌ 處理PIL圖片失敗: {e}")
            return False

    def _resize_image_to_canvas(self, image, canvas_width, canvas_height):
        """縮放圖片以適應畫布"""
        try:
            img_width, img_height = image.size
            
            # 計算縮放比例（保持寬高比）
            scale_x = canvas_width / img_width
            scale_y = canvas_height / img_height
            scale_factor = min(scale_x, scale_y)  # 使用較小的比例確保完全顯示
            
            # 計算新的尺寸
            new_width = int(img_width * scale_factor)
            new_height = int(img_height * scale_factor)
            
            print(f"🔄 縮放比例: {scale_factor:.3f}, 新尺寸: {new_width}x{new_height}")
            
            # 高品質縮放
            resized_image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
            
            return resized_image
            
        except Exception as e:
            print(f"❌ 圖片縮放失敗: {e}")
            return image

    def _create_default_background(self):
        """創建預設背景"""
        try:
            canvas_width = max(100, self.canvas.winfo_width() or self.canvas_width)
            canvas_height = max(100, self.canvas.winfo_height() or self.canvas_height)
            
            # 創建格子背景
            bg = Image.new('RGB', (canvas_width, canvas_height), 'lightgray')
            draw = ImageDraw.Draw(bg)
            
            # 繪製網格
            grid_size = 50
            for i in range(0, canvas_width, grid_size):
                draw.line([(i, 0), (i, canvas_height)], fill='gray', width=1)
            for i in range(0, canvas_height, grid_size):
                draw.line([(0, i), (canvas_width, i)], fill='gray', width=1)
            
            # 添加文字
            try:
                from PIL import ImageFont
                font = ImageFont.load_default()
                draw.text((10, 10), "預設背景", fill='black', font=font)
            except:
                draw.text((10, 10), "Default Background", fill='black')
            
            self.minimap_photo = ImageTk.PhotoImage(bg)
            
            self._editor_scale_info = {
                'display_size': (canvas_width, canvas_height),
                'original_size': (canvas_width, canvas_height),
                'scale_factor': 1.0
            }
            
            print(f"✅ 建立預設背景: {canvas_width}x{canvas_height}")
            
        except Exception as e:
            print(f"❌ 建立預設背景失敗: {e}")

    # =============== 繪製方法 ===============

    def _draw(self):
        """✅ 主要繪製方法"""
        try:
            # 清除除了背景之外的所有元素
            self.canvas.delete("waypoint")
            self.canvas.delete("obstacle")
            self.canvas.delete("area")
            self.canvas.delete("preview")
            
            # 確保小地圖載入
            if not hasattr(self, 'minimap_photo') or not self.minimap_photo:
                self._load_minimap()
            
            # 渲染背景
            self._update_canvas_background()
            
            # 繪製各種元素
            if self.show_areas.get():
                self._draw_areas()
            
            if self.show_waypoints.get():
                self._draw_waypoints()
                self._draw_waypoint_connections()
            
            if self.show_obstacles.get():
                self._draw_obstacles()
            
            # 顯示網格
            if self.show_grid.get():
                self._draw_grid()
            
            # 更新資訊
            self._update_info_labels()
            
            if hasattr(self, 'status_label') and self.status_label:
                self.status_label.config(text="繪製完成")
                
        except Exception as e:
            print(f"❌ 繪製失敗: {e}")
            if hasattr(self, 'status_label') and self.status_label:
                self.status_label.config(text=f"繪製失敗: {e}")

    def _update_canvas_background(self):
        """更新畫布背景"""
        try:
            # 清除舊背景
            self.canvas.delete("background")
            
            if not hasattr(self, 'minimap_photo') or not self.minimap_photo:
                return
            
            # 強制更新canvas尺寸
            self.canvas.update_idletasks()
            
            canvas_width = self.canvas.winfo_width()
            canvas_height = self.canvas.winfo_height()
            
            # 處理初始化問題
            if canvas_width <= 1 or canvas_height <= 1:
                canvas_width = self.canvas_width
                canvas_height = self.canvas_height
            
            # 計算居中位置
            if hasattr(self, '_editor_scale_info'):
                display_size = self._editor_scale_info['display_size']
                
                offset_x = max(0, (canvas_width - display_size[0]) // 2)
                offset_y = max(0, (canvas_height - display_size[1]) // 2)
                
                # 渲染小地圖
                self.canvas.create_image(
                    offset_x, offset_y,
                    anchor=tk.NW,
                    image=self.minimap_photo,
                    tags="background"
                )
                
                # 確保背景在最底層
                self.canvas.tag_lower("background")
                
                # 更新偏移資訊
                self._editor_scale_info['offset'] = (offset_x, offset_y)
                
                print(f"✅ 背景已渲染: 位置({offset_x}, {offset_y}), 尺寸{display_size}")
            
        except Exception as e:
            print(f"❌ 更新背景失敗: {e}")

    def _draw_areas(self):
        """繪製區域標記"""
        try:
            area_grid = self.waypoint_system.area_grid
            if not area_grid:
                return

            if not hasattr(self, '_editor_scale_info'):
                return

            scale_info = self._editor_scale_info
            
            for grid_key, area_type in area_grid.items():
                # 解析座標
                if isinstance(grid_key, str) and ',' in grid_key:
                    x_str, y_str = grid_key.split(',')
                    rel_x, rel_y = float(x_str), float(y_str)
                elif isinstance(grid_key, tuple):
                    rel_x, rel_y = grid_key
                else:
                    continue

                # 轉換為畫布座標
                canvas_x, canvas_y = self._relative_to_canvas(rel_x, rel_y)

                # 顏色映射
                area_colors = {
                    "walkable": {"fill": "lightgreen", "outline": "green"},
                    "forbidden": {"fill": "red", "outline": "darkred"},
                    "rope": {"fill": "orange", "outline": "darkorange"}
                }
                colors = area_colors.get(area_type, {"fill": "gray", "outline": "darkgray"})

                # 標記大小
                size = max(2, self.brush_size.get() // 4)

                if area_type == "rope":
                    self.canvas.create_oval(
                        canvas_x-size, canvas_y-size,
                        canvas_x+size, canvas_y+size,
                        fill=colors["fill"], outline=colors["outline"], 
                        width=1, tags="area"
                    )
                else:
                    self.canvas.create_rectangle(
                        canvas_x-size, canvas_y-size,
                        canvas_x+size, canvas_y+size,
                        fill=colors["fill"], outline=colors["outline"], 
                        width=1, tags="area"
                    )
                    
        except Exception as e:
            print(f"❌ 繪製區域標記失敗: {e}")

    def _draw_waypoints(self):
        """繪製路徑點"""
        try:
            for i, waypoint in enumerate(self.waypoint_system.waypoints):
                rel_x, rel_y = waypoint['pos']
                canvas_x, canvas_y = self._relative_to_canvas(rel_x, rel_y)
                
                # 繪製路徑點
                radius = 8
                self.canvas.create_oval(
                    canvas_x - radius, canvas_y - radius,
                    canvas_x + radius, canvas_y + radius,
                    fill="red", outline="darkred", width=2,
                    tags="waypoint"
                )
                
                # 繪製編號
                self.canvas.create_text(
                    canvas_x, canvas_y - radius - 15,
                    text=str(i + 1),
                    fill="black", font=("Arial", 10, "bold"),
                    tags="waypoint"
                )
                
        except Exception as e:
            print(f"❌ 繪製路徑點失敗: {e}")

    def _draw_waypoint_connections(self):
        """繪製路徑點連接線"""
        try:
            waypoints = self.waypoint_system.waypoints
            if len(waypoints) < 2:
                return
            
            for i in range(len(waypoints) - 1):
                current_pos = waypoints[i]['pos']
                next_pos = waypoints[i + 1]['pos']
                
                current_canvas = self._relative_to_canvas(*current_pos)
                next_canvas = self._relative_to_canvas(*next_pos)
                
                # 繪製箭頭線
                self._draw_arrow(
                    current_canvas[0], current_canvas[1],
                    next_canvas[0], next_canvas[1],
                    color="blue", width=3
                )
                
        except Exception as e:
            print(f"❌ 繪製路徑連接線失敗: {e}")

    def _draw_arrow(self, x1, y1, x2, y2, color="blue", width=2):
        """繪製箭頭"""
        try:
            # 主線
            self.canvas.create_line(x1, y1, x2, y2, 
                                   fill=color, width=width, 
                                   tags="waypoint")
            
            # 計算箭頭
            dx = x2 - x1
            dy = y2 - y1
            length = (dx**2 + dy**2)**0.5
            
            if length > 0:
                angle = math.atan2(dy, dx)
                arrow_size = 15
                
                # 箭頭兩側點
                arrow_x1 = x2 - arrow_size * math.cos(angle - math.pi/6)
                arrow_y1 = y2 - arrow_size * math.sin(angle - math.pi/6)
                arrow_x2 = x2 - arrow_size * math.cos(angle + math.pi/6)
                arrow_y2 = y2 - arrow_size * math.sin(angle + math.pi/6)
                
                # 繪製箭頭
                self.canvas.create_polygon(
                    x2, y2, arrow_x1, arrow_y1, arrow_x2, arrow_y2,
                    fill=color, outline=color,
                    tags="waypoint"
                )
                
        except Exception as e:
            print(f"❌ 繪製箭頭失敗: {e}")

    def _draw_obstacles(self):
        """繪製障礙物"""
        try:
            for obstacle in self.waypoint_system.obstacles:
                rel_x, rel_y = obstacle['pos']
                canvas_x, canvas_y = self._relative_to_canvas(rel_x, rel_y)
                
                size = obstacle.get('size', 0.05) * 500  # 相對大小轉換為像素
                
                # 繪製障礙物
                self.canvas.create_oval(
                    canvas_x - size/2, canvas_y - size/2,
                    canvas_x + size/2, canvas_y + size/2,
                    fill="brown", outline="black", width=2,
                    tags="obstacle"
                )
                
                # 繪製類型標籤
                self.canvas.create_text(
                    canvas_x, canvas_y,
                    text=obstacle.get('type', '?'),
                    fill="white", font=("Arial", 8, "bold"),
                    tags="obstacle"
                )
                
        except Exception as e:
            print(f"❌ 繪製障礙物失敗: {e}")

    def _draw_grid(self):
        """繪製網格"""
        try:
            canvas_width = self.canvas.winfo_width() or self.canvas_width
            canvas_height = self.canvas.winfo_height() or self.canvas_height
            
            grid_size = 50  # 網格大小
            
            # 垂直線
            for x in range(0, canvas_width, grid_size):
                self.canvas.create_line(x, 0, x, canvas_height, 
                                       fill="lightgray", width=1, tags="grid")
            
            # 水平線
            for y in range(0, canvas_height, grid_size):
                self.canvas.create_line(0, y, canvas_width, y, 
                                       fill="lightgray", width=1, tags="grid")
                
        except Exception as e:
            print(f"❌ 繪製網格失敗: {e}")

    # =============== 檔案操作 ===============

    def _refresh_file_list(self):
        """重新整理檔案列表"""
        try:
            if hasattr(self.waypoint_system, 'get_available_map_files'):
                available_files = self.waypoint_system.get_available_map_files()
            else:
                # 備用方案：直接掃描data目錄
                data_dir = Path("data")
                if data_dir.exists():
                    available_files = [f.name for f in data_dir.glob("*.json")]
                else:
                    available_files = []
            
            if hasattr(self, 'file_combo') and self.file_combo:
                self.file_combo['values'] = available_files
                
                if available_files and not self.file_var.get():
                    self.file_var.set(available_files[0])
            
            print(f"📁 發現 {len(available_files)} 個地圖檔案")
            
        except Exception as e:
            print(f"❌ 重新整理檔案列表失敗: {e}")

    def _load_selected_file(self):
        """載入選中的檔案"""
        try:
            filename = self.file_var.get()
            if not filename:
                print("❌ 請選擇要載入的檔案")
                return
            
            file_path = os.path.join("data", filename)
            
            if hasattr(self.waypoint_system, 'load_specific_map'):
                success = self.waypoint_system.load_specific_map(filename)
            else:
                # 備用載入方法
                success = self._load_map_data_direct(file_path)
            
            if success:
                self._draw()
                self.status_label.config(text=f"已載入: {filename}")
                print(f"✅ 載入檔案成功: {filename}")
            else:
                self.status_label.config(text=f"載入失敗: {filename}")
                
        except Exception as e:
            print(f"❌ 載入檔案失敗: {e}")
            self.status_label.config(text=f"載入錯誤: {e}")

    def _load_map_data_direct(self, file_path):
        """直接載入地圖數據"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 載入各種數據
            self.waypoint_system.waypoints = data.get('waypoints', [])
            self.waypoint_system.obstacles = data.get('obstacles', [])
            self.waypoint_system.area_grid = data.get('area_grid', {})
            
            return True
            
        except Exception as e:
            print(f"❌ 直接載入地圖數據失敗: {e}")
            return False

    def _save_waypoints(self):
        """保存路徑點"""
        try:
            filename = self.file_var.get()
            if not filename:
                filename = "map_data.json"
                self.file_var.set(filename)
            
            file_path = os.path.join("data", filename)
            
            if hasattr(self.waypoint_system, 'save_map_data'):
                self.waypoint_system.save_map_data(file_path)
            else:
                # 備用保存方法
                self._save_map_data_direct(file_path)
            
            self.status_label.config(text=f"已保存: {filename}")
            print(f"💾 保存檔案成功: {filename}")
            
        except Exception as e:
            self.status_label.config(text=f"保存失敗: {e}")
            print(f"❌ 保存失敗: {e}")

    def _save_map_data_direct(self, file_path):
        """直接保存地圖數據"""
        try:
            # 確保目錄存在
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            
            # 準備數據
            data = {
                'waypoints': self.waypoint_system.waypoints,
                'obstacles': getattr(self.waypoint_system, 'obstacles', []),
                'area_grid': getattr(self.waypoint_system, 'area_grid', {}),
                'metadata': {
                    'created_time': time.time(),
                    'editor_version': 'fixed_1.0'
                }
            }
            
            # 保存檔案
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            print(f"❌ 直接保存地圖數據失敗: {e}")
            raise

    def _create_new_path_file(self):
        """建立新路徑檔"""
        try:
            filename = simpledialog.askstring("建立路徑檔", "請輸入檔案名稱:")
            if not filename:
                return
            
            if not filename.endswith('.json'):
                filename += '.json'
            
            # 確保data目錄存在
            data_dir = Path("data")
            data_dir.mkdir(exist_ok=True)
            
            file_path = data_dir / filename
            
            # 建立空的路徑檔
            empty_data = {
                'waypoints': [],
                'obstacles': [],
                'area_grid': {},
                'metadata': {
                    'created_time': time.time(),
                    'editor_version': 'fixed_1.0'
                }
            }
            
            # 保存檔案
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(empty_data, f, indent=2, ensure_ascii=False)
            
            print(f"✅ 已建立路徑檔: {filename}")
            self.status_label.config(text=f"已建立: {filename}")
            
            # 設置為當前檔案並重新整理列表
            self.file_var.set(filename)
            self._refresh_file_list()
            
        except Exception as e:
            print(f"❌ 建立路徑檔失敗: {e}")
            self.status_label.config(text=f"建立失敗: {e}")

    # =============== 撤消/重做系統 ===============

    def _save_current_state(self):
        """保存當前狀態到歷史"""
        try:
            current_state = {
                'area_grid': getattr(self.waypoint_system, 'area_grid', {}).copy(),
                'waypoints': self.waypoint_system.waypoints.copy(),
                'obstacles': getattr(self.waypoint_system, 'obstacles', []).copy(),
                'timestamp': time.time()
            }
            
            # 限制歷史記錄數量
            if len(self.undo_history['past']) >= 20:
                self.undo_history['past'] = self.undo_history['past'][-19:]
            
            if self.undo_history['present'] is not None:
                self.undo_history['past'].append(self.undo_history['present'])
            
            self.undo_history['present'] = current_state
            self.undo_history['future'] = []  # 清空future
            
        except Exception as e:
            print(f"❌ 保存狀態失敗: {e}")

    def _undo(self):
        """撤消操作"""
        try:
            if not self.undo_history['past']:
                print("❌ 沒有可撤消的操作")
                return
            
            # 保存當前狀態到future
            if self.undo_history['present'] is not None:
                self.undo_history['future'].insert(0, self.undo_history['present'])
            
            # 恢復上一個狀態
            prev_state = self.undo_history['past'].pop()
            self.undo_history['present'] = prev_state
            
            # 恢復數據
            self.waypoint_system.area_grid = prev_state['area_grid'].copy()
            self.waypoint_system.waypoints = prev_state['waypoints'].copy()
            if hasattr(self.waypoint_system, 'obstacles'):
                self.waypoint_system.obstacles = prev_state.get('obstacles', []).copy()
            
            self._draw()
            print("↶ 撤消完成")
            
        except Exception as e:
            print(f"❌ 撤消操作失敗: {e}")

    def _redo(self):
        """重做操作"""
        try:
            if not self.undo_history['future']:
                print("❌ 沒有可重做的操作")
                return
            
            # 保存當前狀態到past
            if self.undo_history['present'] is not None:
                self.undo_history['past'].append(self.undo_history['present'])
            
            # 恢復future狀態
            next_state = self.undo_history['future'].pop(0)
            self.undo_history['present'] = next_state
            
            # 恢復數據
            self.waypoint_system.area_grid = next_state['area_grid'].copy()
            self.waypoint_system.waypoints = next_state['waypoints'].copy()
            if hasattr(self.waypoint_system, 'obstacles'):
                self.waypoint_system.obstacles = next_state.get('obstacles', []).copy()
            
            self._draw()
            print("↷ 重做完成")
            
        except Exception as e:
            print(f"❌ 重做操作失敗: {e}")

    # =============== 其他工具方法 ===============

    def _clear_all_confirm(self):
        """清除全部確認對話框"""
        try:
            result = messagebox.askyesno(
                "確認清除", 
                "確定要清除所有路徑點和區域標記嗎？\n此操作可以撤消。"
            )
            
            if result:
                # 保存當前狀態到歷史
                self._save_current_state()
                
                # 清除所有數據
                if hasattr(self.waypoint_system, 'area_grid'):
                    self.waypoint_system.area_grid.clear()
                self.waypoint_system.waypoints.clear()
                if hasattr(self.waypoint_system, 'obstacles'):
                    self.waypoint_system.obstacles.clear()
                
                # 重新繪製
                self._draw()
                print("🗑️ 已清除所有數據")
                self.status_label.config(text="已清除所有內容")
                
        except Exception as e:
            print(f"❌ 清除操作失敗: {e}")

    def _update_info_labels(self):
        """更新資訊標籤"""
        try:
            waypoint_count = len(self.waypoint_system.waypoints)
            obstacle_count = len(getattr(self.waypoint_system, 'obstacles', []))
            area_count = len(getattr(self.waypoint_system, 'area_grid', {}))
            
            info_text = f"{waypoint_count}路徑點, {obstacle_count}障礙物, {area_count}區域"
            
            if hasattr(self, 'info_label') and self.info_label:
                self.info_label.config(text=info_text)
                
        except Exception as e:
            print(f"❌ 更新資訊失敗: {e}")

    def _on_window_close(self):
        """關閉視窗處理"""
        try:
            # 簡單關閉，數據保留在waypoint_system中
            self.editor_window.destroy()
            self.editor_window = None
            print("✅ 路徑點編輯器已關閉（數據保留）")
            
        except Exception as e:
            print(f"❌ 關閉編輯器失敗: {e}")
            if self.editor_window:
                self.editor_window.destroy()
                self.editor_window = None
