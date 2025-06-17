# modules/waypoint_editor.py - PyQt5版本

import os
import time
import sys
import json
import cv2
import numpy as np
from PIL import Image, ImageDraw
import math
from pathlib import Path
import subprocess
import hashlib
from modules.simple_waypoint_system import SimpleWaypointSystem
from modules.coordinate import simple_coordinate_conversion

from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *

class CanvasWidget(QWidget):
    """✅ 改進版畫布小部件 - 優化性能"""
    
    # PyQt5 信號
    canvas_clicked = pyqtSignal(QMouseEvent)
    canvas_dragged = pyqtSignal(QMouseEvent)
    canvas_released = pyqtSignal(QMouseEvent)
    mouse_moved = pyqtSignal(QMouseEvent)
    
    def __init__(self, width=800, height=600):
        super().__init__()
        self.setMinimumSize(width, height)
        self.setMouseTracking(True)
        
        # 畫布數據
        self.background_image = None
        self.drawing_items = []
        self.preview_items = []
        
        # 拖拽狀態
        self.is_dragging = False
        self.drag_start_pos = None
        
        # 性能優化
        self.cached_pixmap = None
        self.needs_redraw = True
        self.last_mouse_pos = None
        self.mouse_move_threshold = 5  # 像素
        
        # 設置背景色
        self.setStyleSheet("background-color: white;")
        
        # 啟用雙緩衝
        self.setAttribute(Qt.WA_OpaquePaintEvent)
        
    def reset_canvas(self):
        """完全重置畫布"""
        self.background_image = None
        self.drawing_items.clear()
        self.preview_items.clear()
        self.is_dragging = False
        self.drag_start_pos = None
        self.cached_pixmap = None
        self.needs_redraw = True
        self.update()
    
    def set_background_image(self, qpixmap):
        """設置背景圖片（完全替換）"""
        self.background_image = qpixmap
        self.cached_pixmap = None
        self.needs_redraw = True
        self.update()
    
    def add_drawing_item(self, item):
        """添加繪製項目"""
        self.drawing_items.append(item)
        self.needs_redraw = True
        self.update()
    
    def clear_items_by_tag(self, tag):
        """根據標籤清除項目"""
        self.drawing_items = [item for item in self.drawing_items if item.get('tag') != tag]
        if tag == "preview":
            self.preview_items.clear()
        self.needs_redraw = True
        self.update()
    
    def clear_all_items(self):
        """清除所有繪製項目但保留背景"""
        self.drawing_items.clear()
        self.preview_items.clear()
        self.needs_redraw = True
        self.update()
    
    def paintEvent(self, event):
        """✅ 改進版繪製事件"""
        if self.needs_redraw or self.cached_pixmap is None:
            # 創建新的緩存
            self.cached_pixmap = QPixmap(self.size())
            self.cached_pixmap.fill(Qt.transparent)
            
            painter = QPainter(self.cached_pixmap)
            painter.setRenderHint(QPainter.Antialiasing)
            
            # 繪製背景圖片
            if self.background_image:
                # 計算居中位置
                widget_rect = self.rect()
                image_rect = self.background_image.rect()
                
                x = (widget_rect.width() - image_rect.width()) // 2
                y = (widget_rect.height() - image_rect.height()) // 2
                
                # 使用 QPixmap 的 scaled 方法進行縮放
                scaled_pixmap = self.background_image.scaled(
                    widget_rect.size(),
                    Qt.KeepAspectRatio,
                    Qt.SmoothTransformation
                )
                
                painter.drawPixmap(x, y, scaled_pixmap)
            
            # 繪製所有項目
            for item in self.drawing_items + self.preview_items:
                self._draw_item(painter, item)
            
            painter.end()
            self.needs_redraw = False
        
        # 繪製緩存
        painter = QPainter(self)
        painter.drawPixmap(0, 0, self.cached_pixmap)
        painter.end()
    
    def _draw_item(self, painter, item):
        """繪製單個項目"""
        item_type = item.get('type')
        
        if item_type == 'oval':
            self._draw_oval(painter, item)
        elif item_type == 'rectangle':
            self._draw_rectangle(painter, item)
        elif item_type == 'line':
            self._draw_line(painter, item)
        elif item_type == 'text':
            self._draw_text(painter, item)
        elif item_type == 'polygon':
            self._draw_polygon(painter, item)
    
    def _draw_oval(self, painter, item):
        """繪製橢圓"""
        x, y, w, h = item['x'], item['y'], item['width'], item['height']
        
        # 設置畫筆和畫刷
        pen = QPen(QColor(item.get('outline', 'black')))
        pen.setWidth(item.get('outline_width', 1))
        painter.setPen(pen)
        
        brush = QBrush(QColor(item.get('fill', 'transparent')))
        painter.setBrush(brush)
        
        painter.drawEllipse(int(x), int(y), int(w), int(h))
    
    def _draw_rectangle(self, painter, item):
        """繪製矩形"""
        x, y, w, h = item['x'], item['y'], item['width'], item['height']
        
        # 設置畫筆和畫刷
        pen = QPen(QColor(item.get('outline', 'black')))
        pen.setWidth(item.get('outline_width', 1))
        painter.setPen(pen)
        
        brush = QBrush(QColor(item.get('fill', 'transparent')))
        painter.setBrush(brush)
        
        painter.drawRect(int(x), int(y), int(w), int(h))
    
    def _draw_line(self, painter, item):
        """繪製線條"""
        pen = QPen(QColor(item.get('color', 'black')))
        pen.setWidth(item.get('width', 1))
        
        if item.get('dash'):
            pen.setStyle(Qt.DashLine)
        
        painter.setPen(pen)
        
        if 'coords' in item:
            coords = item['coords']
            for i in range(0, len(coords)-2, 2):
                painter.drawLine(int(coords[i]), int(coords[i+1]), int(coords[i+2]), int(coords[i+3]))
        else:
            painter.drawLine(int(item['x1']), int(item['y1']), int(item['x2']), int(item['y2']))
    
    def _draw_text(self, painter, item):
        """繪製文字"""
        pen = QPen(QColor(item.get('color', 'black')))
        painter.setPen(pen)
        
        font = QFont(item.get('font_family', 'Arial'), item.get('font_size', 10))
        if item.get('font_weight') == 'bold':
            font.setBold(True)
        painter.setFont(font)
        
        painter.drawText(int(item['x']), int(item['y']), item['text'])
    
    def _draw_polygon(self, painter, item):
        """繪製多邊形"""
        points = []
        coords = item['coords']
        for i in range(0, len(coords), 2):
            points.append(QPoint(int(coords[i]), int(coords[i+1])))
        polygon = QPolygon(points)
        pen = QPen(QColor(item.get('outline', 'black')))
        painter.setPen(pen)
        brush = QBrush(QColor(item.get('fill', 'transparent')))
        painter.setBrush(brush)
        painter.drawPolygon(polygon)
    
    def mouseMoveEvent(self, event):
        """✅ 改進版鼠標移動事件"""
        if self.last_mouse_pos is None:
            self.last_mouse_pos = event.pos()
            return
            
        # 計算移動距離
        dx = event.pos().x() - self.last_mouse_pos.x()
        dy = event.pos().y() - self.last_mouse_pos.y()
        distance = math.sqrt(dx*dx + dy*dy)
        
        # 只有移動距離超過閾值才觸發事件
        if distance >= self.mouse_move_threshold:
            self.last_mouse_pos = event.pos()
            self.mouse_moved.emit(event)
            
            if self.is_dragging:
                self.canvas_dragged.emit(event)
    
    def mousePressEvent(self, event):
        """鼠標按下事件"""
        self.is_dragging = True
        self.drag_start_pos = event.pos()
        self.last_mouse_pos = event.pos()
        self.canvas_clicked.emit(event)
    
    def mouseReleaseEvent(self, event):
        """鼠標釋放事件"""
        self.is_dragging = False
        self.drag_start_pos = None
        self.last_mouse_pos = None
        self.canvas_released.emit(event)
    
    def resizeEvent(self, event):
        """✅ 改進版大小改變事件"""
        super().resizeEvent(event)
        self.cached_pixmap = None
        self.needs_redraw = True

class WaypointEditor(QMainWindow):
    """路徑點編輯器 - PyQt5版本"""
    
    def __init__(self, waypoint_system, tracker=None):
        super().__init__()
        self.waypoint_system = waypoint_system
        self.tracker = tracker
        self.editor_window = None
        self.canvas = None
        self.minimap_photo = None
        
        # 界面相關
        self.canvas_width = 800
        self.canvas_height = 600
        self.scale_factor = 1.0
        
        # ✅ 修復：統一編輯狀態管理（PyQt5版本）
        self.edit_mode = "waypoint"
        self.current_mode = "waypoint"
        self.selected_type = "wall"
        
        # 拖曳相關
        self.is_dragging = False
        self.drawing_line = False
        self.drag_start_pos = None
        self.preview_line_id = None
        self.offset_x = 0
        self.offset_y = 0
        
        # 圖層顯示控制
        self.show_waypoints = True
        self.show_areas = True
        self.show_obstacles = True
        
        # 網格控制
        self.snap_to_grid = True
        self.show_grid = False
        self.brush_size = 20
        
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
        self.file_var = ""
        self.file_combo = None
        
        self._minimap_display_info = None  # 記錄顯示資訊
        self._minimap_size = None          # 記錄原始小地圖尺寸
        
        print("✅ 路徑編輯器已初始化")
    
    def create_editor_window(self):
        """✅ 優化版：減少延遲和重複檢查"""
        if self.editor_window is not None:
            self.editor_window.raise_()
            self.editor_window.activateWindow()
            self._draw()
            return

        # 創建視窗
        self.editor_window = QMainWindow()
        self.editor_window.setWindowTitle("路徑點編輯器 - PyQt5版本")
        self.editor_window.setGeometry(100, 100, 1200, 800)
        
        # ✅ 重要：設置關閉事件處理
        self.editor_window.closeEvent = self._on_window_close_event
        
        # ✅ 先創建介面
        self._create_editor_interface()
        
        # ✅ 立即初始化小地圖，不再延遲
        self._initialize_minimap_and_draw()
        
        # 顯示視窗
        self.editor_window.show()

    def _on_window_close_event(self, event):
        """✅ PyQt5標準的關閉事件處理"""
        try:
            print("✅ 路徑點編輯器正在關閉...")
            
            # 清理資源
            if hasattr(self, 'canvas'):
                self.canvas = None
            
            if hasattr(self, 'minimap_photo'):
                self.minimap_photo = None
            
            # ✅ 重要：重置窗口引用
            self.editor_window = None
            
            # 接受關閉事件
            event.accept()
            
            print("✅ 路徑點編輯器已關閉（數據保留）")
            
        except Exception as e:
            print(f"❌ 關閉編輯器失敗: {e}")
            # ✅ 即使出錯也要清理和關閉
            self.editor_window = None
            event.accept()

    def _check_prerequisites(self):
        """檢查必要條件"""
        try:
            # 檢查tracker是否存在
            if not self.tracker:
                print("❌ 追蹤器未初始化")
                return False
            # 檢查capturer是否存在
            if not hasattr(self.tracker, 'capturer') or not self.tracker.capturer:
                print("❌ 畫面捕捉器未初始化")
                return False
            # 檢查ADB連接
            if not self.tracker.capturer.is_connected:
                print("❌ ADB未連接")
                return False
            # 測試畫面捕捉
            test_frame = self.tracker.capturer.grab_frame()
            if test_frame is None:
                print("❌ 無法獲取遊戲畫面")
                return False
            print(f"✅ 前置條件檢查通過，畫面尺寸: {test_frame.shape}")
            return True
        except Exception as e:
            print(f"❌ 前置條件檢查失敗: {e}")
            return False

    def _process_pil_image(self, image):
        """修正版：確保背景完全替換"""
        try:
            print("✅ 使用AutoMaple風格處理")
            # ✅ 先清除舊的小地圖狀態
            if hasattr(self, 'canvas') and self.canvas:
                self.canvas.clear_all_items()
            processed_image = image
            self._minimap_size = processed_image.size
            canvas_width = self.canvas.width() or 800
            canvas_height = self.canvas.height() or 600
            scale_x = canvas_width / processed_image.width
            scale_y = canvas_height / processed_image.height
            scale = min(scale_x, scale_y)
            new_width = int(processed_image.width * scale)
            new_height = int(processed_image.height * scale)
            resized_image = processed_image.resize((new_width, new_height), Image.Resampling.LANCZOS)
            display_info = {
                'display_width': resized_image.size[0],
                'display_height': resized_image.size[1],
                'offset_x': (canvas_width - resized_image.size[0]) // 2,
                'offset_y': (canvas_height - resized_image.size[1]) // 2
            }
            self._minimap_display_info = display_info
            # ✅ 轉換並設置背景圖片
            qimage = self._pil_to_qimage(resized_image)
            new_pixmap = QPixmap.fromImage(qimage)
            if hasattr(self, 'canvas') and self.canvas:
                self.canvas.set_background_image(new_pixmap)
            self.minimap_photo = new_pixmap
            print("✅ AutoMaple風格處理完成，背景已更新")
            return True
        except Exception as e:
            print(f"❌ 處理失敗: {e}")
            import traceback
            traceback.print_exc()
            return False

    def _pil_to_qimage(self, pil_image):
        """PIL圖片轉QImage"""
        try:
            if pil_image.mode != 'RGB':
                pil_image = pil_image.convert('RGB')
            np_array = np.array(pil_image)
            height, width, channel = np_array.shape
            qimage = QImage(np_array.data, width, height, width * channel, QImage.Format_RGB888)
            return qimage
        except Exception as e:
            print(f"❌ PIL轉QImage失敗: {e}")
            return QImage(400, 300, QImage.Format_RGB888)

    def _canvas_to_relative(self, canvas_x, canvas_y):
        """AutoMaple風格：畫布座標轉相對座標"""
        if not self._minimap_display_info or not self._minimap_size:
            return None
        canvas_size = (self.canvas.width() or 800, self.canvas.height() or 600)
        minimap_size = (
            self._minimap_display_info['display_width'],
            self._minimap_display_info['display_height']
        )
        return simple_coordinate_conversion(canvas_x, canvas_y, canvas_size, minimap_size)

    def _relative_to_canvas(self, rel_x, rel_y):
        """AutoMaple風格：相對座標轉畫布座標"""
        if not self._minimap_display_info or not self._minimap_size:
            return None
        display_info = self._minimap_display_info
        canvas_x = rel_x * display_info['display_width'] + display_info['offset_x']
        canvas_y = rel_y * display_info['display_height'] + display_info['offset_y']
        return int(canvas_x), int(canvas_y)

    def _initialize_minimap_and_draw(self):
        """✅ 優化版：減少重複檢查"""
        try:
            print("🔄 開始初始化小地圖...")
            
            # 1. 檢查前置條件（簡化版）
            if not self.tracker or not hasattr(self.tracker, 'capturer') or not self.tracker.capturer.is_connected:
                print("❌ 前置條件檢查失敗")
                return
                
            # 2. 自動偵測小地圖（與載入合併）
            if hasattr(self.tracker, 'find_minimap'):
                try:
                    if not self.tracker.find_minimap():
                        print("❌ 小地圖偵測失敗")
                        return
                    print("✅ 已自動偵測小地圖")
                except Exception as e:
                    print(f"❌ 自動偵測小地圖失敗: {e}")
                    return
            
            # 3. 獲取並處理小地圖
            minimap_img = self.tracker.minimap_img
            if minimap_img is None:
                print("❌ 小地圖圖片為空")
                return
                
            # 4. 轉換為PIL格式並處理
            minimap_rgb = cv2.cvtColor(minimap_img, cv2.COLOR_BGR2RGB)
            pil_image = Image.fromarray(minimap_rgb)
            
            # 5. 使用統一處理
            if self._process_pil_image(pil_image):
                print("✅ 小地圖載入成功")
                self._draw()
            else:
                print("❌ 小地圖處理失敗")
                
        except Exception as e:
            print(f"❌ 初始化失敗: {e}")
            import traceback
            traceback.print_exc()

    def _schedule_minimap_retry(self, max_retries=3):
        """✅ 排程小地圖重試載入"""
        if not hasattr(self, '_minimap_retry_count'):
            self._minimap_retry_count = 0
        
        if self._minimap_retry_count < max_retries:
            self._minimap_retry_count += 1
            print(f"🔄 排程小地圖重試 ({self._minimap_retry_count}/{max_retries})")
            
            # 延遲重試
            QTimer.singleShot(500, self._retry_load_minimap)

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
        """創建編輯器介面（PyQt5版本）"""
        try:
            # 主容器
            central_widget = QWidget()
            self.editor_window.setCentralWidget(central_widget)
            
            main_layout = QHBoxLayout(central_widget)
            main_layout.setContentsMargins(2, 2, 2, 2)

            # 左側：畫布區域
            canvas_frame = QGroupBox("地圖編輯區域")
            main_layout.addWidget(canvas_frame, 3)  # 佔用更多空間
            self._create_canvas_area(canvas_frame)

            # 右側：控制面板
            control_frame = QGroupBox("控制面板")
            control_frame.setFixedWidth(300)
            main_layout.addWidget(control_frame)
            
            control_layout = QVBoxLayout(control_frame)
            
            # 檔案管理
            self._create_file_management(control_layout)
            
            # 編輯模式選擇
            self._create_mode_selection(control_layout)
            
            # 編輯工具
            self._create_editing_tools(control_layout)
            
            # 圖層控制
            self._create_layer_controls(control_layout)
            
            # 快捷操作
            self._create_quick_actions(control_layout)

            # 底部：狀態欄
            self.status_label = QLabel("就緒")
            self.editor_window.statusBar().addWidget(self.status_label)
            
            print("✅ 編輯器介面已創建（PyQt5版本）")
            
        except Exception as e:
            print(f"❌ 創建編輯器介面失敗: {e}")
            import traceback
            traceback.print_exc()

    def _create_canvas_area(self, parent):
        """創建畫布區域（PyQt5版本）"""
        try:
            layout = QVBoxLayout(parent)
            # 創建自定義畫布
            self.canvas = CanvasWidget(self.canvas_width, self.canvas_height)
            # 綁定 resize 事件
            self.canvas.resizeEvent = self._on_canvas_resize
            # 創建滾動區域
            scroll_area = QScrollArea()
            scroll_area.setWidget(self.canvas)
            scroll_area.setWidgetResizable(True)
            layout.addWidget(scroll_area)
            # ✅ 修復：綁定事件並同步編輯模式
            self.canvas.canvas_clicked.connect(self._on_canvas_click)
            self.canvas.canvas_dragged.connect(self._on_canvas_drag)
            self.canvas.canvas_released.connect(self._on_canvas_release)
            self.canvas.mouse_moved.connect(self._update_coord_label)
            print("✅ 畫布區域已創建（PyQt5版本）")
        except Exception as e:
            print(f"❌ 創建畫布區域失敗: {e}")

    def _on_canvas_resize(self, event):
        """畫布大小變動時自動重新載入小地圖"""
        print(f"[DEBUG] 畫布resize: {self.canvas.width()}x{self.canvas.height()}")
        self._load_minimap()
        event.accept()

    def _create_file_management(self, parent_layout):
        """創建檔案管理區域（PyQt5版本）- 優化版"""
        file_frame = QGroupBox("檔案管理")
        parent_layout.addWidget(file_frame)
        file_layout = QVBoxLayout(file_frame)

        # 檔案選擇
        file_layout.addWidget(QLabel("地圖檔案:"))
        
        # ✅ 先創建下拉選單
        self.file_combo = QComboBox()
        file_layout.addWidget(self.file_combo)
        
        # 檔案操作按鈕
        file_buttons = QWidget()
        file_buttons_layout = QHBoxLayout(file_buttons)
        file_buttons_layout.setContentsMargins(0, 0, 0, 0)
        file_layout.addWidget(file_buttons)

        load_btn = QPushButton("📂載入")
        load_btn.clicked.connect(self._load_selected_file)
        file_buttons_layout.addWidget(load_btn)

        save_btn = QPushButton("💾保存")
        save_btn.clicked.connect(self._save_waypoints)
        file_buttons_layout.addWidget(save_btn)

        new_btn = QPushButton("📄新建")
        new_btn.clicked.connect(self._create_new_path_file)
        file_buttons_layout.addWidget(new_btn)

        refresh_btn = QPushButton("🔄刷新")
        refresh_btn.clicked.connect(self._refresh_file_list)
        file_buttons_layout.addWidget(refresh_btn)

        # ✅ 立即刷新檔案列表，不再延遲
        self._refresh_file_list()

    def _create_mode_selection(self, parent_layout):
        """修正版：模式選擇按鈕組"""
        mode_frame = QGroupBox("編輯模式")
        parent_layout.addWidget(mode_frame)
        mode_layout = QVBoxLayout(mode_frame)
        self.mode_label = QLabel("當前模式: 路徑點")
        self.mode_label.setStyleSheet("font-weight: bold; color: blue;")
        mode_layout.addWidget(self.mode_label)
        self.mode_button_group = QButtonGroup()
        self.mode_buttons = {}
        modes = [
            ("📍 路徑點", "waypoint"),
            ("🟢 安全區域", "walkable"),
            ("🔴 禁止區域", "forbidden"),
            ("🧗 繩索區域", "rope"),
            ("🗑️ 刪除模式", "delete")
        ]
        for text, mode in modes:
            button = QPushButton(text)
            button.setCheckable(True)
            button.clicked.connect(lambda checked, m=mode: self._on_mode_button_clicked(m))
            self.mode_button_group.addButton(button)
            mode_layout.addWidget(button)
            self.mode_buttons[mode] = button
        self.mode_buttons["waypoint"].setChecked(True)
        self._set_edit_mode("waypoint")

    def _on_mode_button_clicked(self, mode):
        """處理模式按鈕點擊"""
        try:
            print(f"🖱️ 點擊模式按鈕: {mode}")
            self._set_edit_mode(mode)
        except Exception as e:
            print(f"❌ 模式按鈕點擊處理失敗: {e}")

    def _set_edit_mode(self, mode):
        """修正版：設置編輯模式並完全清除前一模式狀態"""
        try:
            self._clear_current_mode_state()
            old_mode = getattr(self, 'edit_mode', None)
            self.edit_mode = mode
            self.current_mode = mode
            print(f"🔄 模式切換: {old_mode} -> {mode}")
            self._update_mode_buttons(mode)
            if hasattr(self, 'mode_label'):
                mode_names = {
                    "waypoint": "路徑點",
                    "walkable": "安全區域",
                    "forbidden": "禁止區域", 
                    "rope": "繩索區域",
                    "delete": "刪除模式"
                }
                self.mode_label.setText(f"當前模式: {mode_names.get(mode, mode)}")
            cursor_map = {
                "waypoint": Qt.CrossCursor,
                "delete": Qt.ForbiddenCursor,
                "walkable": Qt.PointingHandCursor,
                "forbidden": Qt.PointingHandCursor,
                "rope": Qt.PointingHandCursor
            }
            cursor = cursor_map.get(mode, Qt.ArrowCursor)
            if hasattr(self, 'canvas') and self.canvas:
                self.canvas.setCursor(cursor)
            if hasattr(self, 'canvas') and self.canvas:
                self.canvas.clear_items_by_tag("preview")
                self.canvas.clear_items_by_tag("temp")
            print(f"✅ 編輯模式已切換: {mode}")
        except Exception as e:
            print(f"❌ 設置編輯模式失敗: {e}")

    def _clear_current_mode_state(self):
        """清除當前模式的所有狀態"""
        try:
            self.is_dragging = False
            self.drawing_line = False
            self.drag_start_pos = None
            if hasattr(self, 'preview_line_id'):
                self.preview_line_id = None
            if hasattr(self, 'canvas') and self.canvas:
                self.canvas.is_dragging = False
                self.canvas.drag_start_pos = None
                self.canvas.clear_items_by_tag("preview")
                self.canvas.clear_items_by_tag("temp")
                self.canvas.clear_items_by_tag("drawing")
            print("🧹 已清除前一模式狀態")
        except Exception as e:
            print(f"❌ 清除模式狀態失敗: {e}")

    def _update_mode_buttons(self, active_mode):
        """更新模式按鈕的選中狀態"""
        try:
            if hasattr(self, 'mode_buttons'):
                for mode, button in self.mode_buttons.items():
                    is_active = (mode == active_mode)
                    button.setChecked(is_active)
                    if is_active:
                        button.setStyleSheet("""
                            QPushButton:checked {
                                background-color: #4CAF50;
                                color: white;
                                font-weight: bold;
                            }
                        """)
                    else:
                        button.setStyleSheet("")
            print(f"🎛️ 模式按鈕已更新: {active_mode}")
        except Exception as e:
            print(f"❌ 更新模式按鈕失敗: {e}")

    def _create_editing_tools(self, parent_layout):
        """創建編輯工具（PyQt5版本）"""
        tools_frame = QGroupBox("編輯工具")
        parent_layout.addWidget(tools_frame)
        
        tools_layout = QVBoxLayout(tools_frame)
        
        # 筆刷大小
        brush_widget = QWidget()
        brush_layout = QHBoxLayout(brush_widget)
        tools_layout.addWidget(brush_widget)
        
        brush_layout.addWidget(QLabel("筆刷大小:"))
        
        self.brush_slider = QSlider(Qt.Horizontal)
        self.brush_slider.setRange(5, 50)
        self.brush_slider.setValue(20)
        self.brush_slider.valueChanged.connect(self._update_brush_size)
        brush_layout.addWidget(self.brush_slider)
        
        self.brush_label = QLabel("20")
        brush_layout.addWidget(self.brush_label)
        
        # 編輯選項
        self.snap_grid_cb = QCheckBox("吸附網格")
        self.snap_grid_cb.setChecked(True)
        self.snap_grid_cb.stateChanged.connect(self._toggle_snap_grid)
        tools_layout.addWidget(self.snap_grid_cb)
        
        self.show_grid_cb = QCheckBox("顯示網格")
        self.show_grid_cb.stateChanged.connect(self._toggle_show_grid)
        tools_layout.addWidget(self.show_grid_cb)

    def _update_brush_size(self, value):
        """更新筆刷大小"""
        self.brush_size = value
        self.brush_label.setText(str(value))

    def _toggle_snap_grid(self, state):
        """切換吸附網格"""
        self.snap_to_grid = state == Qt.Checked

    def _toggle_show_grid(self, state):
        """切換顯示網格"""
        self.show_grid = state == Qt.Checked
        self._draw()

    def _create_layer_controls(self, parent_layout):
        """創建圖層控制（PyQt5版本）"""
        layers_frame = QGroupBox("圖層顯示")
        parent_layout.addWidget(layers_frame)
        
        layers_layout = QVBoxLayout(layers_frame)
        
        layers = [
            ("顯示路徑點", "show_waypoints"),
            ("顯示區域標記", "show_areas"),
            ("顯示障礙物", "show_obstacles")
        ]
        
        for text, attr_name in layers:
            checkbox = QCheckBox(text)
            checkbox.setChecked(getattr(self, attr_name))
            checkbox.stateChanged.connect(lambda state, attr=attr_name: self._toggle_layer(attr, state))
            layers_layout.addWidget(checkbox)

    def _toggle_layer(self, attr_name, state):
        """切換圖層顯示"""
        setattr(self, attr_name, state == Qt.Checked)
        self._draw()

    def _create_quick_actions(self, parent_layout):
        """創建快捷操作（PyQt5版本）"""
        # 編輯資訊
        info_frame = QGroupBox("編輯資訊")
        parent_layout.addWidget(info_frame)
        
        info_layout = QVBoxLayout(info_frame)
        
        self.info_label = QLabel("0路徑點, 0障礙物, 0區域")
        self.info_label.setStyleSheet("font-size: 9pt;")
        info_layout.addWidget(self.info_label)
        
        # 座標顯示
        self.coord_label = QLabel("座標: (0.000, 0.000)")
        info_layout.addWidget(self.coord_label)
        
        # 快速工具
        tools_frame = QGroupBox("快速操作")
        parent_layout.addWidget(tools_frame)
        
        tools_layout = QVBoxLayout(tools_frame)
        
        actions = [
            ("🔄 重繪", self._draw),
            ("🗑️ 清除", self._clear_all_confirm),
            ("↶ 撤消", self._undo),
            ("↷ 重做", self._redo)
        ]
        
        for text, command in actions:
            btn = QPushButton(text)
            btn.clicked.connect(command)
            tools_layout.addWidget(btn)

    # =============== 事件處理 ===============

    def _sync_edit_mode(self):
        """✅ 同步編輯模式（PyQt5版本）"""
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

    def _on_canvas_click(self, event):
        """修正版：根據當前模式處理點擊"""
        try:
            canvas_x = event.pos().x()
            canvas_y = event.pos().y()
            print(f"🖱️ 畫布點擊: ({canvas_x}, {canvas_y}) 模式: {self.edit_mode}")
            result = self._canvas_to_relative(canvas_x, canvas_y)
            if result is None:
                print("❌ 座標轉換失敗")
                return
            rel_x, rel_y = result
            if self.edit_mode == "waypoint":
                self._add_waypoint(rel_x, rel_y)
            elif self.edit_mode in ["walkable", "forbidden", "rope"]:
                # 支援拖曳標記線段
                self.is_dragging = True
                self.drawing_line = True
                self.drag_start_pos = (rel_x, rel_y)
                self._mark_area_point((rel_x, rel_y), self.edit_mode)
            elif self.edit_mode == "delete":
                self._delete_nearest_element(rel_x, rel_y)
            else:
                print(f"⚠️ 未知模式: {self.edit_mode}")
            self._draw()
        except Exception as e:
            print(f"❌ 點擊事件處理失敗: {e}")
            import traceback
            traceback.print_exc()

    def _on_canvas_drag(self, event):
        """修正版：拖曳時預覽線段"""
        try:
            if not self.is_dragging:
                return
            rel_x, rel_y = self._canvas_to_relative(event.x(), event.y())
            mode = self.edit_mode
            if mode in ["walkable", "forbidden", "rope"] and self.drawing_line:
                self.canvas.clear_items_by_tag("preview")
                start_canvas = self._relative_to_canvas(*self.drag_start_pos)
                end_canvas = self._relative_to_canvas(rel_x, rel_y)
                color_map = {
                    "walkable": "green",
                    "forbidden": "red",
                    "rope": "orange"
                }
                color = color_map.get(mode, "gray")
                preview_item = {
                    'type': 'line',
                    'x1': start_canvas[0],
                    'y1': start_canvas[1],
                    'x2': end_canvas[0],
                    'y2': end_canvas[1],
                    'color': color,
                    'width': 3,
                    'dash': True,
                    'tag': 'preview'
                }
                self.canvas.preview_items.append(preview_item)
                self.canvas.update()
        except Exception as e:
            print(f"❌ 處理拖曳失敗: {e}")

    def _on_canvas_release(self, event):
        """修正版：拖曳結束時自動補線"""
        try:
            if not self.is_dragging or not self.drawing_line:
                return
            rel_x, rel_y = self._canvas_to_relative(event.x(), event.y())
            mode = self.edit_mode
            if mode in ["walkable", "forbidden", "rope"]:
                self._mark_area_line(self.drag_start_pos, (rel_x, rel_y), mode)
            self.is_dragging = False
            self.drawing_line = False
            self.drag_start_pos = None
            self.canvas.clear_items_by_tag("preview")
            self._draw()
        except Exception as e:
            print(f"❌ 處理拖曳結束失敗: {e}")

    def _update_coord_label(self, event):
        """更新座標標籤（PyQt5版本）"""
        try:
            rel_x, rel_y = self._canvas_to_relative(event.x(), event.y())
            if hasattr(self, 'coord_label') and self.coord_label:
                self.coord_label.setText(f"座標: ({rel_x:.3f}, {rel_y:.3f})")
        except Exception as e:
            pass  # 忽略座標更新錯誤

    # =============== 座標轉換 ===============

    def _load_minimap(self):
        """修正版：確保統一處理流程"""
        try:
            if not self._check_prerequisites():
                return False
            # 嘗試偵測小地圖
            success = self.tracker.find_minimap()
            if not success:
                print("❌ 小地圖偵測失敗")
                return False
            # 獲取小地圖圖片
            minimap_img = self.tracker.minimap_img
            if minimap_img is None:
                print("❌ 小地圖圖片為空")
                return False
            # ✅ 轉換為PIL格式並處理
            minimap_rgb = cv2.cvtColor(minimap_img, cv2.COLOR_BGR2RGB)
            pil_image = Image.fromarray(minimap_rgb)
            # 使用統一處理
            return self._process_pil_image(pil_image)
        except Exception as e:
            print(f"❌ 小地圖載入失敗: {e}")
            return False

    # =============== 繪製方法 ===============

    def _draw(self):
        """修正版：確保正確的重繪順序"""
        try:
            if not hasattr(self, 'canvas') or not self.canvas:
                print("❌ 畫布不存在")
                return
            print("🎨 開始重新繪製...")
            # ✅ 1. 清除所有繪製項目（但保留背景圖片）
            self.canvas.clear_all_items()
            # ✅ 2. 確保背景圖片存在
            if not hasattr(self, 'minimap_photo') or not self.minimap_photo:
                print("⚠️ 沒有背景圖片")
                return
            # ✅ 3. 按順序繪製所有元素
            print("🔵 繪製路徑點...")
            self._draw_waypoints()
            print("🔗 繪製路徑連接...")
            self._draw_waypoint_connections()
            print("🟢 繪製區域標記...")
            self._draw_areas()
            print("🚧 繪製障礙物...")
            self._draw_obstacles()
            print("✅ 繪製完成")
        except Exception as e:
            print(f"❌ 繪製失敗: {e}")
            import traceback
            traceback.print_exc()

    def _draw_areas(self):
        """修正版：繪製區域標記"""
        try:
            area_grid = self.waypoint_system.area_grid
            if not area_grid:
                print("📋 沒有區域標記需要繪製")
                return
            print(f"🎨 開始繪製 {len(area_grid)} 個區域標記")
            for grid_key, area_type in area_grid.items():
                try:
                    if isinstance(grid_key, str) and ',' in grid_key:
                        x_str, y_str = grid_key.split(',')
                        rel_x, rel_y = float(x_str), float(y_str)
                    elif isinstance(grid_key, tuple):
                        rel_x, rel_y = grid_key
                    else:
                        continue
                except Exception as e:
                    print(f"❌ 解析座標失敗: {grid_key} - {e}")
                    continue
                canvas_pos = self._relative_to_canvas(rel_x, rel_y)
                if canvas_pos is None:
                    continue
                canvas_x, canvas_y = canvas_pos
                area_styles = {
                    "walkable": {
                        "type": "rectangle",
                        "fill": "lightgreen", 
                        "outline": "green",
                        "size": 4
                    },
                    "forbidden": {
                        "type": "rectangle",
                        "fill": "red", 
                        "outline": "darkred",
                        "size": 4
                    },
                    "rope": {
                        "type": "oval",
                        "fill": "orange", 
                        "outline": "darkorange",
                        "size": 6
                    }
                }
                style = area_styles.get(area_type, {
                    "type": "rectangle",
                    "fill": "gray", 
                    "outline": "darkgray",
                    "size": 3
                })
                size = style["size"]
                if style["type"] == "oval":
                    item = {
                        'type': 'oval',
                        'x': canvas_x - size,
                        'y': canvas_y - size,
                        'width': size * 2,
                        'height': size * 2,
                        'fill': style["fill"],
                        'outline': style["outline"],
                        'outline_width': 2,
                        'tag': 'area'
                    }
                else:
                    item = {
                        'type': 'rectangle',
                        'x': canvas_x - size,
                        'y': canvas_y - size,
                        'width': size * 2,
                        'height': size * 2,
                        'fill': style["fill"],
                        'outline': style["outline"],
                        'outline_width': 2,
                        'tag': 'area'
                    }
                self.canvas.add_drawing_item(item)
            print(f"✅ 區域標記繪製完成")
        except Exception as e:
            print(f"❌ 繪製區域標記失敗: {e}")
            import traceback
            traceback.print_exc()

    def _draw_waypoints(self):
        """繪製路徑點（PyQt5版本）"""
        try:
            for i, waypoint in enumerate(self.waypoint_system.waypoints):
                rel_x, rel_y = waypoint['pos']
                canvas_x, canvas_y = self._relative_to_canvas(rel_x, rel_y)
                
                # 繪製路徑點
                radius = 8
                waypoint_item = {
                    'type': 'oval',
                    'x': canvas_x - radius,
                    'y': canvas_y - radius,
                    'width': radius * 2,
                    'height': radius * 2,
                    'fill': 'red',
                    'outline': 'darkred',
                    'outline_width': 2,
                    'tag': 'waypoint'
                }
                self.canvas.add_drawing_item(waypoint_item)
                
                # 繪製編號
                text_item = {
                    'type': 'text',
                    'x': canvas_x,
                    'y': canvas_y - radius - 15,
                    'text': str(i + 1),
                    'color': 'black',
                    'font_family': 'Arial',
                    'font_size': 10,
                    'font_weight': 'bold',
                    'tag': 'waypoint'
                }
                self.canvas.add_drawing_item(text_item)
                
        except Exception as e:
            print(f"❌ 繪製路徑點失敗: {e}")

    def _draw_waypoint_connections(self):
        """繪製路徑點連接線（PyQt5版本）"""
        try:
            waypoints = self.waypoint_system.waypoints
            if len(waypoints) < 2:
                return
            
            for i in range(len(waypoints) - 1):
                current_pos = waypoints[i]['pos']
                next_pos = waypoints[i + 1]['pos']
                
                current_canvas = self._relative_to_canvas(*current_pos)
                next_canvas = self._relative_to_canvas(*next_pos)
                
                # 繪製主線
                line_item = {
                    'type': 'line',
                    'x1': current_canvas[0],
                    'y1': current_canvas[1],
                    'x2': next_canvas[0],
                    'y2': next_canvas[1],
                    'color': 'blue',
                    'width': 3,
                    'tag': 'waypoint'
                }
                self.canvas.add_drawing_item(line_item)
                
                # 繪製箭頭
                self._draw_arrow_item(current_canvas[0], current_canvas[1],
                                     next_canvas[0], next_canvas[1], "blue")
                
        except Exception as e:
            print(f"❌ 繪製路徑連接線失敗: {e}")

    def _draw_arrow_item(self, x1, y1, x2, y2, color="blue"):
        """繪製箭頭項目"""
        try:
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
                
                # 繪製箭頭多邊形
                arrow_item = {
                    'type': 'polygon',
                    'coords': [x2, y2, arrow_x1, arrow_y1, arrow_x2, arrow_y2],
                    'fill': color,
                    'outline': color,
                    'tag': 'waypoint'
                }
                self.canvas.add_drawing_item(arrow_item)
                
        except Exception as e:
            print(f"❌ 繪製箭頭失敗: {e}")

    def _draw_obstacles(self):
        """繪製障礙物（PyQt5版本）"""
        try:
            for obstacle in self.waypoint_system.obstacles:
                rel_x, rel_y = obstacle['pos']
                canvas_x, canvas_y = self._relative_to_canvas(rel_x, rel_y)
                
                size = obstacle.get('size', 0.05) * 500  # 相對大小轉換為像素
                
                # 繪製障礙物
                obstacle_item = {
                    'type': 'oval',
                    'x': canvas_x - size/2,
                    'y': canvas_y - size/2,
                    'width': size,
                    'height': size,
                    'fill': 'brown',
                    'outline': 'black',
                    'outline_width': 2,
                    'tag': 'obstacle'
                }
                self.canvas.add_drawing_item(obstacle_item)
                
                # 繪製類型標籤
                text_item = {
                    'type': 'text',
                    'x': canvas_x,
                    'y': canvas_y,
                    'text': obstacle.get('type', '?'),
                    'color': 'white',
                    'font_family': 'Arial',
                    'font_size': 8,
                    'font_weight': 'bold',
                    'tag': 'obstacle'
                }
                self.canvas.add_drawing_item(text_item)
                
        except Exception as e:
            print(f"❌ 繪製障礙物失敗: {e}")

    def _draw_grid(self):
        """繪製網格（PyQt5版本）"""
        try:
            canvas_width = self.canvas.width() or self.canvas_width
            canvas_height = self.canvas.height() or self.canvas_height
            
            grid_size = 50  # 網格大小
            
            # 垂直線
            for x in range(0, canvas_width, grid_size):
                grid_item = {
                    'type': 'line',
                    'x1': x,
                    'y1': 0,
                    'x2': x,
                    'y2': canvas_height,
                    'color': 'lightgray',
                    'width': 1,
                    'tag': 'grid'
                }
                self.canvas.add_drawing_item(grid_item)
            
            # 水平線
            for y in range(0, canvas_height, grid_size):
                grid_item = {
                    'type': 'line',
                    'x1': 0,
                    'y1': y,
                    'x2': canvas_width,
                    'y2': y,
                    'color': 'lightgray',
                    'width': 1,
                    'tag': 'grid'
                }
                self.canvas.add_drawing_item(grid_item)
                
        except Exception as e:
            print(f"❌ 繪製網格失敗: {e}")

    # =============== 檔案操作 ===============

    def _refresh_file_list(self):
        """重新整理檔案列表（修正版）"""
        try:
            print("🔄 開始刷新檔案列表...")
            
            # ✅ 確保 file_combo 存在
            if not hasattr(self, 'file_combo') or self.file_combo is None:
                print("❌ file_combo 不存在，延遲重試")
                QTimer.singleShot(500, self._refresh_file_list)
                return
            
            # ✅ 使用 waypoint_system 的方法獲取檔案列表
            available_files = self.waypoint_system.get_available_map_files()
            
            print(f"📁 發現 {len(available_files)} 個地圖檔案: {available_files}")
            
            # ✅ 更新下拉選單
            self.file_combo.clear()
            if available_files:
                self.file_combo.addItems(available_files)
                
                # 設置預設選擇
                if not hasattr(self, 'file_var') or not self.file_var:
                    self.file_var = available_files[0]
                    self.file_combo.setCurrentText(self.file_var)
            else:
                self.file_combo.addItem("無可用檔案")
            
            print("✅ 檔案列表刷新完成")
            
        except Exception as e:
            print(f"❌ 重新整理檔案列表失敗: {e}")
            import traceback
            traceback.print_exc()

    def _load_selected_file(self):
        """載入選中的檔案 - 修正版：防止小地圖重疊"""
        try:
            if not hasattr(self, 'file_combo') or not self.file_combo:
                print("❌ 檔案選擇框不存在")
                return
            selected_file = self.file_combo.currentText()
            if not selected_file:
                print("❌ 沒有選擇檔案")
                return
            file_path = os.path.join("data", selected_file)
            print(f"🔄 開始載入地圖檔: {selected_file}")
            # ✅ 1. 完全重置畫布（關鍵修正）
            if hasattr(self, 'canvas') and self.canvas:
                print("🧹 重置畫布...")
                self.canvas.reset_canvas()
            # ✅ 2. 清除小地圖相關狀態
            self.minimap_photo = None
            self._minimap_display_info = None
            self._minimap_size = None
            # ✅ 3. 載入路徑檔
            if self.waypoint_system.load_map_data(file_path):
                print(f"✅ 成功載入路徑檔: {selected_file}")
                # ✅ 4. 重新載入小地圖（確保不重疊）
                print("🔄 重新載入小地圖...")
                self._load_minimap_for_new_file()
            else:
                print(f"❌ 載入路徑檔失敗: {selected_file}")
        except Exception as e:
            print(f"❌ 載入檔案時發生錯誤: {e}")
            import traceback
            traceback.print_exc()

    def _load_minimap_for_new_file(self):
        """為新載入的檔案重新載入小地圖"""
        try:
            QTimer.singleShot(100, self._initialize_minimap_and_draw)
        except Exception as e:
            print(f"❌ 重新載入小地圖失敗: {e}")

    def _save_waypoints(self):
        """修正版：保存路徑點到檔案"""
        try:
            filename = self.file_combo.currentText() if self.file_combo else ""
            if not filename:
                filename = "路徑_0點.json"
            if not filename.endswith('.json'):
                filename += '.json'
            data_dir = Path("data")
            data_dir.mkdir(exist_ok=True)
            file_path = data_dir / filename
            full_path_str = str(file_path)
            print(f"💾 準備保存到: {full_path_str}")
            success = self.waypoint_system.save_map_data(full_path_str)
            if success:
                self.status_label.setText(f"已保存: {filename}")
                print(f"✅ 保存檔案成功: {filename}")
            else:
                self.status_label.setText("保存失敗")
                print("❌ 保存檔案失敗")
        except Exception as e:
            self.status_label.setText(f"保存失敗: {e}")
            print(f"❌ 保存失敗: {e}")
            import traceback
            traceback.print_exc()

    def _create_new_path_file(self):
        """建立新路徑檔（PyQt5版本）"""
        try:
            filename, ok = QInputDialog.getText(self.editor_window, "建立路徑檔", "請輸入檔案名稱:")
            if not ok or not filename:
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
                    'editor_version': 'pyqt5_1.0'
                }
            }
            
            # 保存檔案
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(empty_data, f, indent=2, ensure_ascii=False)
            
            print(f"✅ 已建立路徑檔: {filename}")
            self.status_label.setText(f"已建立: {filename}")
            
            # 重新整理列表
            self._refresh_file_list()
            
        except Exception as e:
            print(f"❌ 建立路徑檔失敗: {e}")
            self.status_label.setText(f"建立失敗: {e}")

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
        """清除全部確認對話框（PyQt5版本）"""
        try:
            reply = QMessageBox.question(
                self.editor_window,
                "確認清除",
                "確定要清除所有路徑點和區域標記嗎？\n此操作可以撤消。",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
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
                self.status_label.setText("已清除所有內容")
                
        except Exception as e:
            print(f"❌ 清除操作失敗: {e}")

    def _update_info_labels(self):
        """更新資訊標籤（PyQt5版本）"""
        try:
            waypoint_count = len(self.waypoint_system.waypoints)
            obstacle_count = len(getattr(self.waypoint_system, 'obstacles', []))
            area_count = len(getattr(self.waypoint_system, 'area_grid', {}))
            
            info_text = f"{waypoint_count}路徑點, {obstacle_count}障礙物, {area_count}區域"
            
            if hasattr(self, 'info_label') and self.info_label:
                self.info_label.setText(info_text)
                
        except Exception as e:
            print(f"❌ 更新資訊失敗: {e}")

    def _on_window_close(self):
        """關閉視窗處理（PyQt5版本）"""
        try:
            # 簡單關閉，數據保留在waypoint_system中
            if self.editor_window:
                self.editor_window.close()
                self.editor_window = None
            print("✅ 路徑點編輯器已關閉（數據保留）（PyQt5版本）")
            
        except Exception as e:
            print(f"❌ 關閉編輯器失敗: {e}")
            if self.editor_window:
                self.editor_window.close()
                self.editor_window = None

    def _add_waypoint(self, rel_x, rel_y):
        """新增一個路徑點到 waypoint_system"""
        waypoint = {'pos': (rel_x, rel_y)}
        self.waypoint_system.waypoints.append(waypoint)
        self._draw()

    def _mark_area_line(self, start_pos, end_pos, area_type, step=0.01):
        """標記區域線段"""
        try:
            start_x, start_y = start_pos
            end_x, end_y = end_pos
            distance = ((end_x - start_x)**2 + (end_y - start_y)**2)**0.5
            if distance == 0:
                self._mark_area_point(start_pos, area_type)
                return
            steps = max(1, int(distance / step))
            for i in range(steps + 1):
                t = i / steps if steps > 0 else 0
                x = start_x + t * (end_x - start_x)
                y = start_y + t * (end_y - start_y)
                grid_key = f"{x:.3f},{y:.3f}"
                self.waypoint_system.area_grid[grid_key] = area_type
            print(f"✅ 標記{area_type}線段: {len(range(steps + 1))}個點")
        except Exception as e:
            print(f"❌ 標記區域線段失敗: {e}")

    def _delete_nearest_element(self, rel_x, rel_y):
        """刪除最近的元素"""
        try:
            min_distance = float('inf')
            nearest_waypoint = None
            for i, waypoint in enumerate(self.waypoint_system.waypoints):
                wp_x, wp_y = waypoint['pos']
                distance = ((rel_x - wp_x)**2 + (rel_y - wp_y)**2)**0.5
                if distance < min_distance and distance < 0.05:
                    min_distance = distance
                    nearest_waypoint = i
            if nearest_waypoint is not None:
                removed = self.waypoint_system.waypoints.pop(nearest_waypoint)
                print(f"🗑️ 刪除路徑點: {removed['name']}")
                self._draw()
                return
            grid_key = f"{rel_x:.3f},{rel_y:.3f}"
            deleted_keys = []
            for key in list(self.waypoint_system.area_grid.keys()):
                if isinstance(key, str) and ',' in key:
                    try:
                        key_x, key_y = map(float, key.split(','))
                        distance = ((rel_x - key_x)**2 + (rel_y - key_y)**2)**0.5
                        if distance < 0.03:
                            del self.waypoint_system.area_grid[key]
                            deleted_keys.append(key)
                    except:
                        continue
            if deleted_keys:
                print(f"🗑️ 刪除區域標記: {len(deleted_keys)}個點")
                self._draw()
            else:
                print("❌ 附近沒有找到可刪除的元素")
        except Exception as e:
            print(f"❌ 刪除元素失敗: {e}")

    def _mark_area_point(self, rel_pos, area_type):
        """標記單個區域點"""
        try:
            grid_key = f"{rel_pos[0]:.3f},{rel_pos[1]:.3f}"
            self.waypoint_system.area_grid[grid_key] = area_type
            print(f"✅ 標記{area_type}區域: {grid_key}")
            self._draw()
        except Exception as e:
            print(f"❌ 標記區域點失敗: {e}")
