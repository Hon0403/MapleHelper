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
import threading
from modules.simple_waypoint_system import SimpleWaypointSystem
from modules.coordinate import simple_coordinate_conversion, unified_coordinate_conversion, unified_relative_to_canvas

from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtGui import QCloseEvent, QResizeEvent, QShowEvent
from PyQt5.QtCore import QEvent
from PyQt5.QtCore import pyqtSlot

class CanvasWidget(QWidget):
    """✅ 改進版畫布小部件 - 優化性能"""
    
    # PyQt5 信號
    canvas_clicked = pyqtSignal(QMouseEvent)
    canvas_dragged = pyqtSignal(QMouseEvent)
    canvas_released = pyqtSignal(QMouseEvent)
    mouse_moved = pyqtSignal(QMouseEvent)
    # ✅ 新增：大小調整信號
    resized = pyqtSignal()
    
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
        """✅ 優化版繪製事件 - 修正清除問題"""
        # 優化：僅在需要時重繪緩存
        if self.needs_redraw or self.cached_pixmap is None or self.cached_pixmap.size() != self.size():
            # 創建新的緩存
            self.cached_pixmap = QPixmap(self.size())
            
            # ✅ 修正：使用不透明背景色填充，避免穿透
            self.cached_pixmap.fill(Qt.white)
            
            painter = QPainter(self.cached_pixmap)
            painter.setRenderHint(QPainter.Antialiasing)
            
            # 繪製背景圖片
            if self.background_image:
                widget_rect = self.rect()
                
                # ✅ 優化：保持寬高比縮放
                scaled_pixmap = self.background_image.scaled(
                    widget_rect.size(),
                    Qt.KeepAspectRatio,
                    Qt.SmoothTransformation
                )
                
                # ✅ 修正：正確計算居中位置
                image_rect = scaled_pixmap.rect()
                x = (widget_rect.width() - image_rect.width()) // 2
                y = (widget_rect.height() - image_rect.height()) // 2
                
                painter.drawPixmap(x, y, scaled_pixmap)
            
            # 繪製所有項目
            for item in self.drawing_items + self.preview_items:
                self._draw_item(painter, item)
            
            painter.end()
            self.needs_redraw = False
        
        # 從緩存繪製到畫布
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
        points = [QPoint(int(item['coords'][i]), int(item['coords'][i+1])) for i in range(0, len(item['coords']), 2)]
        polygon = QPolygon(points)
        
        pen = QPen(QColor(item.get('outline', 'black')))
        pen.setWidth(item.get('outline_width', 1))
        painter.setPen(pen)
        
        brush = QBrush(QColor(item.get('fill', 'transparent')))
        painter.setBrush(brush)
        
        painter.drawPolygon(polygon)

    def mouseMoveEvent(self, event):
        """✅ 改進版滑鼠移動事件"""
        # 優化：減少事件觸發頻率
        if self.last_mouse_pos and (event.pos() - self.last_mouse_pos).manhattanLength() < self.mouse_move_threshold:
            return
            
        self.last_mouse_pos = event.pos()
        
        # 發送信號
        self.mouse_moved.emit(event)
        
        if self.is_dragging:
            self.canvas_dragged.emit(event)

    def mousePressEvent(self, event):
        """滑鼠點擊事件"""
        self.is_dragging = True
        self.drag_start_pos = event.pos()
        self.canvas_clicked.emit(event)

    def mouseReleaseEvent(self, event):
        """滑鼠釋放事件"""
        self.is_dragging = False
        self.canvas_released.emit(event)

    def resizeEvent(self, event: QResizeEvent):
        """✅ 改進版視窗大小調整事件，使用信號"""
        super().resizeEvent(event)
        self.cached_pixmap = None
        self.needs_redraw = True
        self.update()
        self.resized.emit() # 發送信號


class WaypointEditor(QMainWindow):
    """✅ 重構版：WaypointEditor 作為一個獨立的 QMainWindow"""
    
    def __init__(self, waypoint_system, tracker=None, config=None):
        super().__init__()
        
        # ✅ 添加 logger 初始化
        from includes.log_utils import get_logger
        self.logger = get_logger("WaypointEditor")
        
        # 基本設定
        self.waypoint_system = waypoint_system
        self.tracker = tracker
        self.config = config or {}
        
        # 編輯狀態
        self.edit_mode = "waypoint"
        self.current_mode = "waypoint"
        self.is_dragging = False
        self.drawing_line = False
        self.drag_start_pos = None
        
        # 畫布設定
        self.canvas_width = 800
        self.canvas_height = 600
        self.brush_size = 5
        self.brush_size_range = (1, 20)
        
        # 優化：設定預設的 checkbox 狀態
        self.show_grid = True
        self.show_waypoints = True
        self.show_areas = True
        self.grid_size = 50
        
        # 刪除距離設定
        self.delete_distance = 0.03
        
        # 異步與UI狀態
        self.minimap_loading = False
        self.first_show = True
        self.canvas = None
        self.file_combo = None
        self.status_label = None
        
        # 小地圖相關
        self.minimap_photo = None
        self._minimap_display_info = None
        self._minimap_size = None
        
        # 狀態管理
        self.undo_stack = []
        self.redo_stack = []
        self.max_undo_steps = 20
        
        # 檔案管理
        self.file_var = None
        
        # 初始化UI
        self._setup_ui()

    def _setup_ui(self):
        """初始化並設定UI介面"""
        self.setWindowTitle("路徑點編輯器 - PyQt5版本")
        self.setGeometry(100, 100, self.canvas_width + 300, self.canvas_height + 50)
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QHBoxLayout(central_widget)
        
        self._create_editor_interface(main_layout)

    def showEvent(self, event):
        super().showEvent(event)
        # 每次顯示時自動嘗試載入小地圖
        self._show_loading_and_start_async_load()

    def closeEvent(self, event: QCloseEvent):
        """覆寫 closeEvent，改為隱藏視窗以保留狀態"""
        try:
            self.hide()
            event.ignore()
        except Exception as e:
            event.accept()

    def _show_loading_and_start_async_load(self):
        """顯示載入中提示，並啟動異步小地圖載入"""
        if self.minimap_loading:
            return
            
        self.status_label.setText("小地圖載入中...")
        self.minimap_loading = True
        self._draw() # 繪製初始狀態（如載入提示）
        
        QTimer.singleShot(100, self._start_minimap_load_thread)

    def _start_minimap_load_thread(self):
        """啟動背景執行緒來載入小地圖"""
        load_thread = threading.Thread(target=self._initialize_minimap_and_draw, daemon=True)
        load_thread.start()

    def _initialize_minimap_and_draw(self):
        """✅ 異步版：在背景執行緒中載入小地圖和資料"""
        try:
            success = self._load_minimap()
            
            # ✅ 防禦性檢查：確保視窗仍然存在且可見
            if not self.isVisible():
                self.minimap_loading = False
                return

            self.minimap_loading = False
            
            # ✅ 使用 QTimer 確保UI更新在主執行緒中進行
            if success:
                QTimer.singleShot(0, lambda: self.status_label.setText("小地圖載入成功"))
                QTimer.singleShot(0, self._finalize_ui_after_load)
            else:
                QTimer.singleShot(0, lambda: self.status_label.setText("小地圖載入失敗，請手動重試"))
            
        except Exception as e:
            self.minimap_loading = False
            QTimer.singleShot(0, lambda: self.status_label.setText(f"載入錯誤: {str(e)}"))
            self.logger.error(f"小地圖載入錯誤: {e}")
            import traceback
            traceback.print_exc()

    @pyqtSlot()
    def _finalize_ui_after_load(self):
        self._refresh_file_list()
        self._draw()
        self._update_info_labels()

    def _create_editor_interface(self, main_layout):
        """創建編輯器介面（PyQt5版本）"""
        
        # 創建畫布區域
        self._create_canvas_area(main_layout)
        
        # 創建右側控制面板
        control_panel = QFrame()
        control_panel.setFixedWidth(280)
        control_panel_layout = QVBoxLayout(control_panel)
        main_layout.addWidget(control_panel)
        
        # 添加各個控制部分
        self._create_file_management(control_panel_layout)
        self._create_mode_selection(control_panel_layout)
        self._create_editing_tools(control_panel_layout)
        self._create_layer_controls(control_panel_layout)
        self._create_quick_actions(control_panel_layout)
        
        # 添加狀態欄
        control_panel_layout.addStretch()
        self.status_label = QLabel("準備就緒")
        control_panel_layout.addWidget(self.status_label)
        
    def _create_quick_actions(self, parent_layout):
        """創建快捷操作（PyQt5版本）"""
        tools_frame = QGroupBox("快速操作")
        parent_layout.addWidget(tools_frame)
        
        tools_layout = QVBoxLayout(tools_frame)
        
        # ✅ 新增：手動重新載入按鈕
        reload_btn = QPushButton("🔄 重新載入小地圖")
        reload_btn.clicked.connect(self._show_loading_and_start_async_load)
        tools_layout.addWidget(reload_btn)

        actions = [
            ("🗑️ 清除", self._clear_all_confirm),
            ("↶ 撤消", self._undo),
            ("↷ 重做", self._redo)
        ]
        
        for text, command in actions:
            btn = QPushButton(text)
            btn.clicked.connect(command)
            tools_layout.addWidget(btn)
            
    def _load_minimap(self):
        """載入小地圖資訊 - 修復版"""
        try:
            self.logger.debug("開始載入小地圖...")
            # 檢查必要條件
            if not self._check_minimap_requirements():
                self.logger.error("必要條件檢查失敗")
                return False
            
            self.logger.debug("必要條件檢查通過")
            
            # 偵測小地圖位置
            self.logger.debug("嘗試偵測小地圖...")
            current_frame = self.tracker.capturer.grab_frame()
            if current_frame is None:
                self.logger.error("無法獲取當前畫面")
                return False
                
            minimap_rect = self.tracker._find_minimap_with_subpixel_accuracy(current_frame)
            
            if not minimap_rect:
                self.logger.error("小地圖偵測失敗")
                return False
            
            self.logger.debug("小地圖偵測成功")
            
            # 獲取小地圖圖片
            self.logger.debug("獲取小地圖圖片...")
            x1, y1, x2, y2 = minimap_rect
            minimap_img = current_frame[y1:y2, x1:x2]
            
            if minimap_img is None:
                self.logger.error("小地圖圖片為空")
                return False
            
            self.logger.debug(f"小地圖圖片尺寸: {minimap_img.shape}")
            
            # 轉換圖片格式
            self.logger.debug("轉換圖片格式...")
            pil_image = Image.fromarray(cv2.cvtColor(minimap_img, cv2.COLOR_BGR2RGB))
            
            self.logger.debug(f"PIL圖片尺寸: {pil_image.size}")
            
            # 處理圖片
            self.logger.debug("處理圖片...")
            self.minimap_image = pil_image  # 修正：使用 minimap_image 而不是 minimap_pil
            self.minimap_rect = minimap_rect
            self.minimap_size = pil_image.size
            
            self.logger.info("小地圖載入完成")
            return True
            
        except Exception as e:
            self.logger.error("圖片處理失敗")
            import traceback
            traceback.print_exc()
            
            self.logger.error(f"小地圖載入失敗: {e}")
            return False

    def _check_minimap_requirements(self):
        """檢查必要條件"""
        try:
            # 檢查tracker是否存在
            if not self.tracker:
                self.logger.error("Tracker未設置")
                return False
            self.logger.info("✅ Tracker檢查通過")
            
            # 檢查capturer是否存在
            if not hasattr(self.tracker, 'capturer') or not self.tracker.capturer:
                self.logger.error("Capturer未設置")
                return False
            self.logger.info("✅ Capturer檢查通過")
            
            # 檢查視窗連接狀態
            capture_info = self.tracker.capturer.get_capture_info()
            if not capture_info.get('is_connected', False):
                self.logger.error("視窗未連接")
                return False
            self.logger.info("✅ 視窗連接檢查通過")
            
            # 測試畫面捕捉
            test_frame = self.tracker.capturer.grab_frame()
            if test_frame is None:
                self.logger.error("無法捕獲畫面")
                return False
            self.logger.info(f"✅ 畫面捕捉檢查通過，尺寸: {test_frame.shape}")
            
            return True
        except Exception as e:
            self.logger.error(f"檢查必要條件時發生錯誤: {e}")
            import traceback
            traceback.print_exc()
            return False

    def _process_pil_image(self, image):
        """修正版：確保背景完全替換"""
        try:
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
            return True
        except Exception as e:
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
            return QImage(400, 300, QImage.Format_RGB888)

    def _canvas_to_relative(self, canvas_x, canvas_y):
        """✅ 統一座標轉換：畫布座標轉相對座標"""
        if not self._minimap_display_info or not self._minimap_size:
            return None
        
        canvas_size = (self.canvas.width() or 800, self.canvas.height() or 600)
        minimap_size = (
            self._minimap_display_info['display_width'],
            self._minimap_display_info['display_height']
        )
        
        # 使用統一座標轉換函式
        return unified_coordinate_conversion(
            canvas_x, canvas_y, 
            canvas_size, minimap_size, 
            precision=5
        )

    def _relative_to_canvas(self, rel_x, rel_y):
        """✅ 統一座標轉換：相對座標轉畫布座標"""
        if not self._minimap_display_info or not self._minimap_size:
            return None
        
        canvas_size = (self.canvas.width() or 800, self.canvas.height() or 600)
        minimap_size = (
            self._minimap_display_info['display_width'],
            self._minimap_display_info['display_height']
        )
        
        # 使用統一座標轉換函式
        return unified_relative_to_canvas(
            rel_x, rel_y, 
            canvas_size, minimap_size, 
            precision=1
        )


    def _create_canvas_area(self, parent):
        """創建畫布區域（PyQt5版本）"""
        canvas_frame = QFrame()
        canvas_layout = QVBoxLayout(canvas_frame)
        
        self.canvas = CanvasWidget(self.canvas_width, self.canvas_height)
        canvas_layout.addWidget(self.canvas)
        
        # 連接信號
        self.canvas.canvas_clicked.connect(self._on_canvas_click)
        self.canvas.canvas_dragged.connect(self._on_canvas_drag)
        self.canvas.canvas_released.connect(self._on_canvas_release)
        self.canvas.mouse_moved.connect(self._update_coord_label)
        # ✅ 修正：使用信號與槽處理 resize，而不是猴子補丁
        self.canvas.resized.connect(self._on_canvas_resize)
        
        parent.addWidget(canvas_frame)

    def _on_canvas_resize(self):
        """✅ 修正：處理畫布大小變動的槽函數"""
        self.canvas.needs_redraw = True # 標記需要重繪
        self._draw()

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
            self._set_edit_mode(mode)
        except Exception as e:
            pass

    def _set_edit_mode(self, mode):
        """修正版：設置編輯模式並完全清除前一模式狀態"""
        try:
            self._clear_current_mode_state()
            old_mode = getattr(self, 'edit_mode', None)
            self.edit_mode = mode
            self.current_mode = mode
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
        except Exception as e:
            pass

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
        except Exception as e:
            pass

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
        except Exception as e:
            pass

    def _create_editing_tools(self, parent_layout):
        """創建編輯工具（PyQt5版本）"""
        tools_frame = QGroupBox("編輯工具")
        parent_layout.addWidget(tools_frame)
        
        tools_layout = QVBoxLayout(tools_frame)
        
        # 筆刷大小
        brush_layout = QHBoxLayout()
        brush_layout.addWidget(QLabel("筆刷大小:"))
        
        self.brush_slider = QSlider(Qt.Horizontal)
        self.brush_slider.setRange(1, 20)
        self.brush_slider.setValue(self.brush_size)
        self.brush_slider.valueChanged.connect(self._update_brush_size)
        brush_layout.addWidget(self.brush_slider)
        
        self.brush_label = QLabel(str(self.brush_size))
        brush_layout.addWidget(self.brush_label)
        tools_layout.addLayout(brush_layout)
        
        # ✅ 優化：只保留有用的 checkbox
        self.show_grid_cb = QCheckBox("顯示網格")
        self.show_grid_cb.setChecked(self.show_grid)
        self.show_grid_cb.stateChanged.connect(self._toggle_show_grid)
        tools_layout.addWidget(self.show_grid_cb)
        
        # ✅ 新增：網格大小控制
        grid_layout = QHBoxLayout()
        grid_layout.addWidget(QLabel("網格大小:"))
        self.grid_size_slider = QSlider(Qt.Horizontal)
        self.grid_size_slider.setRange(20, 100)
        self.grid_size_slider.setValue(50)
        self.grid_size_slider.valueChanged.connect(self._update_grid_size)
        grid_layout.addWidget(self.grid_size_slider)
        self.grid_size_label = QLabel("50")
        grid_layout.addWidget(self.grid_size_label)
        tools_layout.addLayout(grid_layout)

    def _update_brush_size(self, value):
        """更新筆刷大小"""
        self.brush_size = value
        self.brush_label.setText(str(value))

    def _update_grid_size(self, value):
        """更新網格大小"""
        self.grid_size = value
        self.grid_size_label.setText(str(value))
        if self.show_grid:
            self._draw()

    def _toggle_show_grid(self, state):
        """切換顯示網格"""
        self.show_grid = state == Qt.Checked
        self._draw()

    def _create_layer_controls(self, parent_layout):
        """創建圖層控制（優化版）"""
        layers_frame = QGroupBox("圖層顯示")
        parent_layout.addWidget(layers_frame)
        
        layers_layout = QVBoxLayout(layers_frame)
        
        # ✅ 優化：只保留實際有用的圖層
        layers = [
            ("顯示路徑點", "show_waypoints"),
            ("顯示區域標記", "show_areas")
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
        
        # ✅ 新增：手動重新載入按鈕
        reload_btn = QPushButton("🔄 重新載入小地圖")
        reload_btn.clicked.connect(self._show_loading_and_start_async_load)
        tools_layout.addWidget(reload_btn)

        actions = [
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
            result = self._canvas_to_relative(canvas_x, canvas_y)
            if result is None:
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
                pass
            self._draw()
        except Exception as e:
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
            pass

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
            pass

    def _update_coord_label(self, event):
        """更新座標標籤（PyQt5版本）"""
        try:
            rel_x, rel_y = self._canvas_to_relative(event.x(), event.y())
            if hasattr(self, 'coord_label') and self.coord_label:
                self.coord_label.setText(f"座標: ({rel_x:.3f}, {rel_y:.3f})")
        except Exception as e:
            pass  # 忽略座標更新錯誤

    # =============== 座標轉換 ===============

    def _load_minimap_image(self):
        """載入小地圖圖片"""
        try:
            self.logger.info("開始載入小地圖...")
            
            # 檢查必要條件
            if not hasattr(self, 'tracker') or not self.tracker:
                self.logger.error("Tracker未設置")
                return False
            
            if not hasattr(self.tracker, 'capturer') or not self.tracker.capturer:
                self.logger.error("Capturer未設置")
                return False
            
            self.logger.info("必要條件檢查通過")
            
            # 偵測小地圖
            self.logger.info("嘗試偵測小地圖...")
            current_frame = self.tracker.capturer.grab_frame()
            if current_frame is None:
                self.logger.error("無法獲取當前畫面")
                return False
            
            self.logger.info("小地圖偵測成功")
            
            # 獲取小地圖圖片
            self.logger.info("獲取小地圖圖片...")
            minimap_rect = self.tracker._find_minimap_with_subpixel_accuracy(current_frame)
            if not minimap_rect:
                self.logger.error("小地圖偵測失敗")
                return False
                
            x1, y1, x2, y2 = minimap_rect
            minimap_img = current_frame[y1:y2, x1:x2]
            
            if minimap_img is None:
                self.logger.error("小地圖圖片為空")
                return False
            
            self.logger.info(f"小地圖圖片尺寸: {minimap_img.shape}")
            
            # 轉換為PIL圖片
            self.logger.info("轉換圖片格式...")
            pil_image = Image.fromarray(cv2.cvtColor(minimap_img, cv2.COLOR_BGR2RGB))
            self.logger.info(f"PIL圖片尺寸: {pil_image.size}")
            
            # 處理圖片
            self.logger.info("處理圖片...")
            self.minimap_image = pil_image
            self.logger.info("小地圖載入完成")
            return True
            
        except Exception as e:
            self.logger.error(f"圖片處理失敗: {e}")
            self.logger.error(f"小地圖載入失敗: {e}")
            return False

    def _set_minimap_background(self):
        """設置小地圖背景圖片"""
        try:
            if not hasattr(self, 'minimap_image') or not self.minimap_image:
                return
                
            # 處理小地圖圖片
            processed_image = self._process_pil_image(self.minimap_image)
            
            # 轉換為QPixmap並設置為背景
            qimage = self._pil_to_qimage(processed_image)
            qpixmap = QPixmap.fromImage(qimage)
            self.canvas.set_background_image(qpixmap)
            
            self.logger.debug("小地圖背景設置完成")
            
        except Exception as e:
            self.logger.error(f"設置小地圖背景失敗: {e}")
            import traceback
            traceback.print_exc()

    # =============== 繪製方法 ===============

    def _draw(self):
        """✅ 優化版：根據 checkbox 和載入狀態控制繪製"""
        try:
            if not hasattr(self, 'canvas') or not self.canvas:
                return
                
            # ✅ 1. 清除所有繪製項目（但保留背景圖片）
            self.canvas.clear_all_items()
            
            # ✅ 2. 確保背景圖片存在或顯示載入中
            if self.minimap_loading:
                loading_item = {
                    'type': 'text',
                    'x': self.canvas.width() / 2 - 50,
                    'y': self.canvas.height() / 2,
                    'text': '小地圖載入中...',
                    'color': 'white',
                    'font_size': 16
                }
                self.canvas.add_drawing_item(loading_item)
                return

            # ✅ 檢查小地圖圖片是否存在
            if not hasattr(self, 'minimap_image') or not self.minimap_image:
                # 顯示載入失敗提示
                no_map_item = {
                    'type': 'text',
                    'x': self.canvas.width() / 2 - 100,
                    'y': self.canvas.height() / 2,
                    'text': '小地圖載入失敗，請點擊右側重新載入',
                    'color': 'white',
                    'font_size': 12
                }
                self.canvas.add_drawing_item(no_map_item)
                return
            
            # ✅ 3. 設置小地圖背景圖片
            if hasattr(self, 'minimap_image') and self.minimap_image:
                self._process_pil_image(self.minimap_image)
            
            # ✅ 4. 按順序繪製所有元素（根據 checkbox 狀態）
            
            # 繪製網格（如果啟用）
            if self.show_grid:
                self._draw_grid()
            
            # 繪製路徑點（如果啟用）
            if self.show_waypoints:
                self._draw_waypoints()
                self._draw_waypoint_connections()
            
            # 繪製區域標記（如果啟用）
            if self.show_areas:
                self._draw_areas()
            
        except Exception as e:
            import traceback
            traceback.print_exc()

    def _draw_grid(self):
        """✅ 優化版：繪製網格（使用可調整大小）"""
        try:
            canvas_width = self.canvas.width() or self.canvas_width
            canvas_height = self.canvas.height() or self.canvas_height
            
            # ✅ 使用可調整的網格大小
            grid_size = getattr(self, 'grid_size', 50)
            
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
            pass

    def _draw_waypoints(self):
        """✅ 優化版：繪製路徑點（只在啟用時繪製）"""
        try:
            if not self.show_waypoints:
                return
                
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
            pass

    def _draw_areas(self):
        """✅ 優化版：繪製區域標記（只在啟用時繪製）"""
        try:
            if not self.show_areas:
                return
                
            area_grid = self.waypoint_system.area_grid
            if not area_grid:
                return
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
        except Exception as e:
            import traceback
            traceback.print_exc()

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
            pass

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
            pass

    def _draw_obstacles(self):
        """❌ 移除：障礙物繪製功能（不再使用）"""
        pass

    # =============== 檔案操作 ===============

    def _refresh_file_list(self):
        """刷新檔案列表（修正版）"""
        try:
            # ✅ 確保 file_combo 存在
            if not hasattr(self, 'file_combo') or self.file_combo is None:
                QTimer.singleShot(500, self._refresh_file_list)
                return
            
            # ✅ 使用 waypoint_system 的方法獲取檔案列表
            available_files = self.waypoint_system.get_files()
            
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
            
        except Exception as e:
            import traceback
            traceback.print_exc()

    def _load_selected_file(self):
        """載入選中的檔案 - 修正版：防止小地圖重疊"""
        try:
            if not hasattr(self, 'file_combo') or not self.file_combo:
                return
            selected_file = self.file_combo.currentText()
            if not selected_file:
                return
            
            # ✅ 1. 完全重置畫布（關鍵修正）
            if hasattr(self, 'canvas') and self.canvas:
                self.canvas.reset_canvas()
            
            # ✅ 2. 清除小地圖相關狀態
            self.minimap_photo = None
            self._minimap_display_info = None
            self._minimap_size = None
            
            # ✅ 3. 使用 load_specific_map 載入路徑檔
            if self.waypoint_system.load_map(selected_file):
                # ✅ 4. 重新載入小地圖（確保不重疊）
                self._load_minimap_for_new_file()
            else:
                pass
                
        except Exception as e:
            import traceback
            traceback.print_exc()

    def _load_minimap_for_new_file(self):
        """為新載入的檔案重新載入小地圖"""
        try:
            QTimer.singleShot(100, self._initialize_minimap_and_draw)
        except Exception as e:
            pass

    def _save_waypoints(self):
        """保存路徑點（PyQt5版本）"""
        try:
            filename, ok = QFileDialog.getSaveFileName(
                self,
                "保存路徑檔",
                "data/",
                "JSON Files (*.json)"
            )
            
            if not filename:
                return
            
            # 確保副檔名
            if not filename.endswith('.json'):
                filename += '.json'
            
            # ✅ 修正：使用相對路徑
            if filename.startswith('data/'):
                relative_filename = filename[5:]  # 移除 "data/" 前綴
            elif filename.startswith('data\\'):
                relative_filename = filename[5:]  # 移除 "data\" 前綴
            else:
                relative_filename = filename
            
            success = self.waypoint_system.save_data(relative_filename)
            
            if success:
                self.status_label.setText(f"已保存: {relative_filename}")
            else:
                self.status_label.setText("保存失敗")
        except Exception as e:
            self.status_label.setText(f"保存失敗: {e}")

    def _create_new_path_file(self):
        """建立新路徑檔（PyQt5版本）"""
        try:
            filename, ok = QInputDialog.getText(self, "建立路徑檔", "請輸入檔案名稱:")
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
            
            self.status_label.setText(f"已建立: {filename}")
            
            # 重新整理列表
            self._refresh_file_list()
            
        except Exception as e:
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
            if len(self.undo_stack) >= self.max_undo_steps:
                self.undo_stack = self.undo_stack[-self.max_undo_steps+1:]
            
            if self.undo_stack:
                self.redo_stack.append(self.undo_stack[-1])
            
            self.undo_stack.append(current_state)
            self.redo_stack = []  # 清空redo stack
            
        except Exception as e:
            pass

    def _undo(self):
        """撤消操作"""
        try:
            if not self.undo_stack:
                return
            
            # 保存當前狀態到redo stack
            if self.undo_stack:
                self.redo_stack.append(self.undo_stack[-1])
            
            # 恢復上一個狀態
            prev_state = self.undo_stack.pop()
            self.undo_stack.append(prev_state)
            
            # 恢復數據
            self.waypoint_system.area_grid = prev_state['area_grid'].copy()
            self.waypoint_system.waypoints = prev_state['waypoints'].copy()
            if hasattr(self.waypoint_system, 'obstacles'):
                self.waypoint_system.obstacles = prev_state.get('obstacles', []).copy()
            
            self._draw()
            
        except Exception as e:
            pass

    def _redo(self):
        """重做操作"""
        try:
            if not self.redo_stack:
                return
            
            # 保存當前狀態到undo stack
            if self.redo_stack:
                self.undo_stack.append(self.redo_stack[-1])
            
            # 恢復future狀態
            next_state = self.redo_stack.pop()
            self.redo_stack.append(next_state)
            
            # 恢復數據
            self.waypoint_system.area_grid = next_state['area_grid'].copy()
            self.waypoint_system.waypoints = next_state['waypoints'].copy()
            if hasattr(self.waypoint_system, 'obstacles'):
                self.waypoint_system.obstacles = next_state.get('obstacles', []).copy()
            
            self._draw()
            
        except Exception as e:
            pass

    # =============== 其他工具方法 ===============

    def _clear_all_confirm(self):
        """清除全部確認對話框（PyQt5版本）"""
        try:
            reply = QMessageBox.question(
                self,
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
                self.status_label.setText("已清除所有內容")
                
        except Exception as e:
            pass

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
            pass

    def _on_window_close(self):
        """關閉視窗處理（PyQt5版本）"""
        try:
            # 簡單關閉，數據保留在waypoint_system中
            if hasattr(self, 'editor_window') and self.editor_window:
                self.editor_window.close()
                self.editor_window = None
            
        except Exception as e:
            if hasattr(self, 'editor_window') and self.editor_window:
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
        except Exception as e:
            pass

    def _delete_nearest_element(self, rel_x, rel_y):
        """刪除最近的元素"""
        try:
            min_distance = float('inf')
            nearest_waypoint = None
            for i, waypoint in enumerate(self.waypoint_system.waypoints):
                wp_x, wp_y = waypoint['pos']
                distance = ((rel_x - wp_x)**2 + (rel_y - wp_y)**2)**0.5
                if distance < min_distance and distance < self.delete_distance:
                    min_distance = distance
                    nearest_waypoint = i
            if nearest_waypoint is not None:
                removed = self.waypoint_system.waypoints.pop(nearest_waypoint)
                self._draw()
                return
            grid_key = f"{rel_x:.3f},{rel_y:.3f}"
            deleted_keys = []
            for key in list(self.waypoint_system.area_grid.keys()):
                if isinstance(key, str) and ',' in key:
                    try:
                        key_x, key_y = map(float, key.split(','))
                        distance = ((rel_x - key_x)**2 + (rel_y - key_y)**2)**0.5
                        if distance < self.delete_distance:
                            del self.waypoint_system.area_grid[key]
                            deleted_keys.append(key)
                    except:
                        continue
            if deleted_keys:
                self._draw()
        except Exception as e:
            pass

    def _mark_area_point(self, rel_pos, area_type):
        """標記單個區域點"""
        try:
            grid_key = f"{rel_pos[0]:.3f},{rel_pos[1]:.3f}"
            self.waypoint_system.area_grid[grid_key] = area_type
            self._draw()
        except Exception as e:
            pass

    def init_minimap(self):
        """初始化小地圖"""
        try:
            self._check_prerequisites()
            self._load_minimap()
            self._draw()
        except Exception as e:
            self._schedule_minimap_retry()

    def create_ui(self):
        """創建編輯器介面"""
        try:
            # 創建主佈局
            main_layout = QVBoxLayout()
            
            # 創建各個區域
            self._create_canvas_area(main_layout)
            self._create_file_management(main_layout)
            self._create_mode_selection(main_layout)
            self._create_editing_tools(main_layout)
            self._create_layer_controls(main_layout)
            self._create_quick_actions(main_layout)
            
            # 設置主佈局
            central_widget = QWidget()
            central_widget.setLayout(main_layout)
            self.setCentralWidget(central_widget)
            
            # 同步編輯模式
            self._sync_edit_mode()
            
        except Exception as e:
            import traceback
            traceback.print_exc()

    def refresh_files(self):
        """刷新檔案列表"""
        try:
            # 獲取可用檔案
            available_files = self.waypoint_system.get_files()
            
            # 更新下拉選單
            if hasattr(self, 'file_combo') and self.file_combo:
                self.file_combo.clear()
                for file in available_files:
                    self.file_combo.addItem(file)
            
        except Exception as e:
            pass

    def load_file(self):
        """載入選中的檔案"""
        try:
            if not hasattr(self, 'file_combo') or not self.file_combo:
                return
            selected_file = self.file_combo.currentText()
            if not selected_file:
                return
            
            # 重置畫布
            if hasattr(self, 'canvas') and self.canvas:
                self.canvas.reset_canvas()
            
            # 清除小地圖狀態
            self.minimap_photo = None
            self._minimap_display_info = None
            self._minimap_size = None
            
            # 載入檔案
            if self.waypoint_system.load_map(selected_file):
                self._load_minimap_for_new_file()
            else:
                pass
                
        except Exception as e:
            import traceback
            traceback.print_exc()

    def save_file(self):
        """保存路徑點"""
        try:
            filename, ok = QFileDialog.getSaveFileName(
                self,
                "保存路徑檔",
                "data/",
                "JSON Files (*.json)"
            )
            
            if not filename:
                return
            
            # 確保副檔名
            if not filename.endswith('.json'):
                filename += '.json'
            
            # 修正：使用相對路徑
            if filename.startswith('data/'):
                relative_filename = filename[5:]  # 移除 "data/" 前綴
            elif filename.startswith('data\\'):
                relative_filename = filename[5:]  # 移除 "data\" 前綴
            else:
                relative_filename = filename
            
            success = self.waypoint_system.save_data(relative_filename)
            
            if success:
                self.status_label.setText(f"已保存: {relative_filename}")
            else:
                self.status_label.setText("保存失敗")
        except Exception as e:
            self.status_label.setText(f"保存失敗: {e}")