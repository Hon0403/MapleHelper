# modules/simple_gui_monster_display.py - PyQt5版本：文字顯示匹配結果

import sys
import threading
import time
from datetime import datetime
import json
import os
import cv2
import numpy as np
import queue
import subprocess
import socket
import struct
from pathlib import Path

from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *

from modules.coordinate import TemplateMatcherTracker   # 已經在 ro_helper.tracker
from includes.simple_template_utils import UITemplateHelper

# 添加父目錄到 Python 路徑
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class QSwitch(QCheckBox):
    """自定義開關按鈕類別"""
    def __init__(self, text="", parent=None):
        super().__init__(text, parent)
        self.setStyleSheet("""
            QCheckBox {
                spacing: 5px;
                color: #333;
            }
            QCheckBox::indicator {
                width: 50px;
                height: 25px;
                border-radius: 12px;
                background-color: #ccc;
            }
            QCheckBox::indicator:unchecked {
                background-color: #ccc;
            }
            QCheckBox::indicator:checked {
                background-color: #4CAF50;
            }
            QCheckBox::indicator:unchecked:hover {
                background-color: #bbb;
            }
            QCheckBox::indicator:checked:hover {
                background-color: #45a049;
            }
        """)

def get_available_map_files():
    """✅ 共用函數：獲取可用的地圖檔案列表"""
    try:
        # 使用絕對路徑或確保相對路徑正確
        current_dir = Path.cwd()
        data_dir = current_dir / "data"
        
        print(f"🔍 掃描目錄: {data_dir.absolute()}")
        
        # 確保 data 目錄存在
        if not data_dir.exists():
            print("⚠️ data 目錄不存在，嘗試建立...")
            data_dir.mkdir(exist_ok=True)
            return []
        
        # 掃描所有 JSON 檔案
        json_files = []
        for file_path in data_dir.glob("*.json"):
            if file_path.is_file():
                json_files.append(file_path.name)
        
        # 按檔案名稱排序
        json_files.sort()
        
        print(f"✅ 掃描到 {len(json_files)} 個地圖檔案")
        if json_files:
            print(f"📋 檔案列表: {json_files}")
        
        return json_files
        
    except Exception as e:
        print(f"❌ 獲取地圖檔案列表失敗: {e}")
        import traceback
        traceback.print_exc()
        return []

class MonsterDetectionGUI(QMainWindow):
    """怪物檢測GUI - PyQt5版本：使用文字列表顯示匹配結果"""
    
    def __init__(self, ro_helper, config=None):
        """初始化 GUI"""
        super().__init__()
        
        # 保存 RO Helper 引用
        self.ro_helper = ro_helper
        
        # ✅ 從設定檔讀取參數
        if config:
            gui_config = config.get('gui', {})
            self.detection_interval = gui_config.get('detection_interval', 0.1)
            self.gui_update_interval = gui_config.get('gui_update_interval', 200)
            self.cooldown_interval = gui_config.get('cooldown_interval', 0.7)
            self.display_timeout = gui_config.get('display_timeout', 3)
            self.sleep_time = gui_config.get('sleep_time', 0.001)
            self.error_sleep_time = gui_config.get('error_sleep_time', 0.01)
            self.wait_time = gui_config.get('wait_time', 0.2)
        else:
            # 預設值
            self.detection_interval = 0.1
            self.gui_update_interval = 200
            self.cooldown_interval = 0.7
            self.display_timeout = 3
            self.sleep_time = 0.001
            self.error_sleep_time = 0.01
            self.wait_time = 0.2
        
        # 初始化變數
        self.is_running = False
        self.last_frame = None
        self.last_detection_time = 0
        self.monster_positions = []
        self.current_map = None
        self.map_data = None
        self.map_scale = 1.0
        self.map_offset = (0, 0)
        self.is_dragging = False
        self.last_pos = None
        self.drag_start_pos = None
        self.drawing_line = False
        self.current_mode = "waypoint"
        self.edit_mode = "waypoint"
        self.auto_hunt_enabled = False
        self.auto_hunt_mode = "off"
        self.combat_mode = "safe_area"
        self.attack_range = 0.4
        self.approach_distance = 0.1
        self.retreat_distance = 0.05
        self.attack_cooldown = 1.5
        self.movement_speed = 0.8
        self.use_waypoints = False
        self.patrol_mode = "safe_area"
        self.max_chase_distance = 0.15
        self.return_to_safe = True
        
        # 初始化血條檢測器
        self._initialize_health_detector()
        
        # 確保 monster_detector 被正確初始化
        if not hasattr(ro_helper, 'monster_detector'):
            from includes.simple_template_utils import monster_detector
            self.monster_detector = monster_detector
            ro_helper.monster_detector = monster_detector
        else:
            self.monster_detector = ro_helper.monster_detector
        
        # 確保 waypoint_system 被正確初始化
        if not hasattr(ro_helper, 'waypoint_system'):
            from modules.simple_waypoint_system import SimpleWaypointSystem
            self.waypoint_system = SimpleWaypointSystem()
            ro_helper.waypoint_system = self.waypoint_system
        else:
            self.waypoint_system = ro_helper.waypoint_system
        
        # GUI設定
        self.setWindowTitle("Maple Helper - 怪物檢測")
        self.setGeometry(300, 300, 800, 600)
        
        # 執行控制
        self.detection_enabled = False  # 預設關閉
        self.detection_thread = None
        
        # OpenCV顯示控制
        self._opencv_display_running = False
        self._opencv_display_thread = None
        
        # 更新間隔設定
        self.update_interval = "3000"
        
        # 檢測結果資料
        self.last_detection_results = []
        self.detection_history = []
        self.detection_stats = {'total_detections': 0, 'unique_monsters': set()}
        
        # OpenCV相關
        self._opencv_running = False
        self.opencv_threads = []
        self._frame_queue = None
        self._result_queue = None
        
        # ✅ 新增：效能優化相關
        self.last_gui_update = 0
        self.detection_queue = queue.Queue(maxsize=2)
        self.result_queue = queue.Queue(maxsize=5)
        
        # 啟動異步處理
        self._start_async_processing()
        
        # 建立GUI介面
        self._create_gui()
        
        # 初始化模板資料夾列表
        self._refresh_template_folders()
        
        # ✅ 確保自動狩獵開關預設為關閉
        if hasattr(self, 'auto_hunt_switch'):
            self.auto_hunt_switch.setChecked(False)  # 預設關閉
        
        # ✅ 確保戰鬥系統預設為關閉
        if hasattr(ro_helper, 'auto_combat'):
            ro_helper.auto_combat.is_enabled = False
            ro_helper.auto_combat.auto_hunt_mode = "off"
        
        self.ui_helper = UITemplateHelper(adb=self.ro_helper.adb, cooldown_interval=self.cooldown_interval)
        
        print("✅ GUI 已初始化")
        if config:
            print(f"✅ 已從設定檔載入 GUI 參數: detection_interval={self.detection_interval}")
    
    def _initialize_health_detector(self):
        """初始化血條檢測器"""
        try:
            from modules.health_mana_detector import HealthManaDetector
            self.health_detector = HealthManaDetector()
            print("✅ 血條檢測器已初始化")
        except Exception as e:
            print(f"❌ 血條檢測器初始化失敗: {e}")
            self.health_detector = None

    def _process_frame(self):
        """擴展的畫面處理（包含血條檢測）"""
        frame, monsters = super()._process_frame()
        
        health_info = {}
        if self.health_detector and frame is not None:
            health_info = self.health_detector.detect_hud_health_mana(frame)
            
            # 在畫面上顯示血條和魔力條資訊
            if health_info.get('success', False):
                hp_percent = health_info.get('hp_percentage', 0)
                mp_percent = health_info.get('mp_percentage', 0)
                
                # 在畫面上顯示血條和魔力條資訊
                cv2.putText(frame, f"HP: {hp_percent:.1f}%", (10, 30), 
                          cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
                cv2.putText(frame, f"MP: {mp_percent:.1f}%", (10, 60), 
                          cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 0, 0), 2)
        
        return frame, monsters, health_info

    def _update_gui(self, frame, monsters):
        """更新GUI顯示（包含血條資訊）"""
        if frame is not None:
            # 處理血條資訊
            health_info = {}
            if self.health_detector:
                health_info = self.health_detector.detect_hud_health_mana(frame)
                
                if health_info.get('success', False):
                    hp_percent = health_info.get('hp_percentage', 0)
                    mp_percent = health_info.get('mp_percentage', 0)
                    
                    # 更新狀態列
                    self.statusBar().showMessage(
                        f"HP: {hp_percent:.1f}% | MP: {mp_percent:.1f}% | "
                        f"怪物數量: {len(monsters)}"
                    )
            
            # 更新怪物列表
            self._update_monster_list(monsters)
            
            # 更新畫面
            self._update_frame(frame)
            
            # 更新狀態
            self._update_status()
    
    def _create_gui(self):
        """建立完整GUI介面"""
        try:
            # 中央小部件
            central_widget = QWidget()
            self.setCentralWidget(central_widget)
            
            # 主要布局
            main_layout = QHBoxLayout(central_widget)
            main_layout.setContentsMargins(2, 2, 2, 2)
            
            # 左側面板：控制和統計
            left_panel = QWidget()
            left_panel.setFixedWidth(300)
            left_layout = QVBoxLayout(left_panel)
            
            # 右側面板：檢測結果
            right_panel = QWidget()
            
            main_layout.addWidget(left_panel)
            main_layout.addWidget(right_panel)
            
            # 建立所有控制面板
            self._create_control_panel(left_layout)
            self._create_statistics_panel(left_layout)
            self._create_auto_hunt_controls(left_layout)
            
            # 右側檢測結果
            self._create_detection_results_display(right_panel)
            
            # 狀態欄
            self.status_bar = self.statusBar()
            self.status_bar.showMessage("準備就緒")
            
            # 加入除錯資訊
            print(f"✅ GUI 已初始化")
            print(f"  - dynamic_button_area 存在: {hasattr(self, 'dynamic_button_area')}")
            if hasattr(self, 'dynamic_button_area'):
                print(f"  - dynamic_button_area 類型: {type(self.dynamic_button_area)}")
                print(f"  - dynamic_button_layout 存在: {hasattr(self, 'dynamic_button_layout')}")
            
        except Exception as e:
            print(f"❌ GUI 創建失敗: {e}")
            import traceback
            traceback.print_exc()
    
    def _create_control_panel(self, parent_layout):
        """✅ 混合布局：主要按鈕垂直，小按鈕水平"""
        self.control_frame = QGroupBox("控制面板")
        parent_layout.addWidget(self.control_frame)
        
        control_layout = QVBoxLayout(self.control_frame)
        
        # 怪物模板選擇
        template_group = QGroupBox("怪物模板")
        template_layout = QVBoxLayout(template_group)
        control_layout.addWidget(template_group)
        
        # 模板資料夾選擇
        folder_layout = QHBoxLayout()
        folder_layout.addWidget(QLabel("選擇資料夾:"))
        
        self.template_folder_combo = QComboBox()
        self.template_folder_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.template_folder_combo.currentIndexChanged.connect(self._on_template_folder_changed)
        folder_layout.addWidget(self.template_folder_combo)
        
        template_layout.addLayout(folder_layout)
        
        # 重新整理按鈕
        refresh_btn = QPushButton("🔄 重新整理")
        refresh_btn.clicked.connect(self._refresh_template_folders)
        template_layout.addWidget(refresh_btn)
        
        # 檢測控制（垂直）
        self.detection_enabled_switch = QCheckBox("即時檢測 (切換)")
        self.detection_enabled_switch.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.detection_enabled_switch.stateChanged.connect(self._toggle_detection)
        control_layout.addWidget(self.detection_enabled_switch)
        
        # ✅ 小按鈕組用水平布局
        button_group = QGroupBox("操作按鈕")
        control_layout.addWidget(button_group)
        
        button_layout = QHBoxLayout(button_group)
        
        buttons = [
            ("📸 保存", self._detect_and_save),
            ("📋 清除", self._clear_results)
        ]
        
        for text, command in buttons:
            btn = QPushButton(text)
            btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            btn.clicked.connect(command)
            button_layout.addWidget(btn)
        
        # ✅ 添加動態按鈕區域
        self.dynamic_button_area = QGroupBox("路徑編輯")
        control_layout.addWidget(self.dynamic_button_area)
        
        self.dynamic_button_layout = QHBoxLayout(self.dynamic_button_area)
        
        # ✅ 添加預設提示標籤，讓區域更明顯
        self.waypoint_hint_label = QLabel("點擊下方按鈕開啟路徑編輯器")
        self.waypoint_hint_label.setStyleSheet("color: gray; font-style: italic;")
        self.dynamic_button_layout.addWidget(self.waypoint_hint_label)
        self.dynamic_button_layout.addStretch()  # 右對齊
    
    def _create_detection_results_display(self, parent):
        """優化檢測結果顯示區域（移除即時檢測頁籤，只保留詳細資訊與歷史）"""
        layout = QVBoxLayout(parent)
        
        results_frame = QGroupBox("檢測結果")
        layout.addWidget(results_frame)
        
        results_layout = QVBoxLayout(results_frame)
        
        # 建立頁籤容器
        self.notebook = QTabWidget()
        results_layout.addWidget(self.notebook)
        
        # 只保留詳細資訊與歷史頁籤
        self._create_detailed_info_tab()
        self._create_history_tab()
    
    def add_waypoint_button(self, button_text: str, command_function):
        """✅ 修正版：動態按鈕添加"""
        try:
            print(f"🔧 開始添加按鈕: {button_text}")
            print(f"  - dynamic_button_area 存在: {hasattr(self, 'dynamic_button_area')}")
            
            if hasattr(self, 'dynamic_button_area') and self.dynamic_button_area:
                print(f"  - 創建按鈕物件...")
                self.waypoint_button = QPushButton(button_text)
                
                # ✅ 關鍵修改6：動態按鈕也要Expanding
                self.waypoint_button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
                self.waypoint_button.setMinimumWidth(70)  # 降低最小寬度
                
                print(f"  - 設置按鈕點擊事件...")
                # 包裝 command_function 以加入除錯資訊
                def wrapped_command():
                    try:
                        print(f"🖱️ 按鈕被點擊: {button_text}")
                        print(f"🔧 執行函數: {command_function}")
                        command_function()
                        print(f"✅ 函數執行完成: {button_text}")
                    except Exception as e:
                        print(f"❌ 按鈕點擊時發生錯誤: {e}")
                        import traceback
                        traceback.print_exc()
                
                self.waypoint_button.clicked.connect(wrapped_command)
                
                print(f"  - 隱藏提示標籤...")
                # ✅ 隱藏提示標籤
                if hasattr(self, 'waypoint_hint_label'):
                    self.waypoint_hint_label.hide()
                
                print(f"  - 將按鈕添加到佈局...")
                # ✅ 清除現有佈局並重新添加按鈕
                while self.dynamic_button_layout.count():
                    child = self.dynamic_button_layout.takeAt(0)
                    if child.widget():
                        child.widget().setParent(None)
                
                # ✅ 重新添加按鈕到佈局
                self.dynamic_button_layout.addWidget(self.waypoint_button)
                self.dynamic_button_layout.addStretch()  # 右對齊
                
                print(f"✅ 路徑編輯按鈕已添加: {button_text}")
                print(f"  - 按鈕物件: {self.waypoint_button}")
                print(f"  - 按鈕可見: {self.waypoint_button.isVisible()}")
                print(f"  - 按鈕大小: {self.waypoint_button.size()}")
                print(f"  - 佈局項目數: {self.dynamic_button_layout.count()}")
                return True
            else:
                print(f"❌ dynamic_button_area 不存在或為空")
                print(f"  - dynamic_button_area: {getattr(self, 'dynamic_button_area', '不存在')}")
                return False
                
        except Exception as e:
            print(f"❌ 添加按鈕失敗: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def _create_detailed_info_tab(self):
        """建立詳細資訊頁籤"""
        detail_widget = QWidget()
        self.notebook.addTab(detail_widget, "📋 詳細資訊")
        
        layout = QVBoxLayout(detail_widget)
        
        # 詳細資訊文字框
        self.detail_text = QTextEdit()
        self.detail_text.setFont(QFont("Consolas", 10))
        layout.addWidget(self.detail_text)
    
    def _create_history_tab(self):
        """建立檢測歷史頁籤"""
        history_widget = QWidget()
        self.notebook.addTab(history_widget, "📚 檢測歷史")
        
        layout = QVBoxLayout(history_widget)
        
        # 歷史控制
        history_control = QWidget()
        control_layout = QHBoxLayout(history_control)
        layout.addWidget(history_control)
        
        clear_history_btn = QPushButton("🗑️ 清除歷史")
        clear_history_btn.clicked.connect(self._clear_history)
        control_layout.addWidget(clear_history_btn)
        
        control_layout.addWidget(QLabel("顯示最近："))
        
        self.history_limit_combo = QComboBox()
        self.history_limit_combo.addItems(["50", "100", "200", "500", "全部"])
        self.history_limit_combo.setCurrentText("100")
        control_layout.addWidget(self.history_limit_combo)
        
        control_layout.addStretch()
        
        # 歷史列表
        self.history_text = QTextEdit()
        self.history_text.setFont(QFont("Consolas", 9))
        layout.addWidget(self.history_text)
    
    def _create_statistics_panel(self, parent_layout):
        """優化統計面板布局"""
        stats_frame = QGroupBox("統計資訊")
        parent_layout.addWidget(stats_frame)
        
        stats_layout = QVBoxLayout(stats_frame)
        
        # 第一行統計
        row1 = QWidget()
        row1_layout = QHBoxLayout(row1)
        stats_layout.addWidget(row1)
        
        self.total_detections_label = QLabel("總檢測: 0")
        self.total_detections_label.setStyleSheet("font-weight: bold;")
        row1_layout.addWidget(self.total_detections_label)
        
        self.unique_monsters_label = QLabel("怪物種類: 0")
        self.unique_monsters_label.setStyleSheet("font-weight: bold;")
        row1_layout.addWidget(self.unique_monsters_label)
        
        # 第二行統計
        row2 = QWidget()
        row2_layout = QHBoxLayout(row2)
        stats_layout.addWidget(row2)
        
        self.avg_confidence_label = QLabel("信心度: 0.00")
        row2_layout.addWidget(self.avg_confidence_label)
        
        self.detection_rate_label = QLabel("頻率: 0/分鐘")
        row2_layout.addWidget(self.detection_rate_label)
        
        # 第三行統計
        row3 = QWidget()
        row3_layout = QHBoxLayout(row3)
        stats_layout.addWidget(row3)
        
        self.session_time_label = QLabel("運行時間: 0秒")
        row3_layout.addWidget(self.session_time_label)
    
    def _start_detection(self):
        """啟動檢測執行緒"""
        if not self.is_running:
            self.is_running = True
            self.detection_thread = threading.Thread(target=self._detection_loop, daemon=True)
            self.detection_thread.start()
            self.session_start_time = time.time()
    
    def _detection_loop(self):
        """✅ 修改後的檢測主迴圈 - 超高頻率版本"""
        last_fps_time = time.time()
        frame_count = 0
        
        while self.is_running:
            try:
                if self.detection_enabled:
                    # 使用基礎處理函數
                    _, monsters, health_info = self._process_frame()
                    
                    # 更新GUI（主執行緒）
                    QMetaObject.invokeMethod(self, "_update_detection_results", 
                                           Qt.QueuedConnection, 
                                           Q_ARG('PyQt_PyObject', (monsters, health_info)))
                    
                    # 計算FPS
                    frame_count += 1
                    current_time = time.time()
                    if current_time - last_fps_time >= 1.0:
                        fps = frame_count / (current_time - last_fps_time)
                        print(f"📊 檢測FPS: {fps:.1f}")
                        frame_count = 0
                        last_fps_time = current_time
                
                # 使用極短的等待時間以提高頻率
                time.sleep(0.001)  # 約1000FPS
                
            except Exception as e:
                print(f"❌ 檢測迴圈錯誤: {e}")
                time.sleep(0.01)  # 錯誤時稍微等待
    
    @pyqtSlot('PyQt_PyObject')
    def _update_detection_results(self, data):
        """更新檢測結果顯示（移除畫布與FPS相關）"""
        try:
            current_time = datetime.now().strftime("%H:%M:%S.%f")[:-3]
            
            # 更新詳細資訊
            self._update_detailed_info(data[0], current_time)
            
            # 更新歷史記錄
            self._update_history(data[0], current_time)
            
            # 更新統計
            self._update_statistics(data[0])
            
            # 保存結果
            self.last_detection_results = data[0]
            
            # 更新血條資訊
            self._update_health_info(data[1])
            
        except Exception as e:
            print(f"結果更新錯誤: {e}")
    
    def _process_frame(self):
        """✅ 基礎畫面處理函數"""
        try:
            if not self.ro_helper or not hasattr(self.ro_helper, 'capturer'):
                return None, [], {}
            
            # 獲取遊戲畫面
            frame = self.ro_helper.capturer.grab_frame()
            if frame is None:
                return None, [], {}
            
            # 執行怪物檢測
            monsters = []
            if self.monster_detector:
                monsters = self.monster_detector.detect_monsters(frame)
                monsters = monsters if monsters else []
            
            return frame, monsters, {}
            
        except Exception as e:
            print(f"❌ 畫面處理錯誤: {e}")
            return None, [], {}
    
    def _update_detailed_info(self, monsters, current_time):
        """更新詳細資訊頁籤"""
        try:
            self.detail_text.clear()
            
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
            
            self.detail_text.setPlainText('\n'.join(info_lines))
            
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
                limit_str = self.history_limit_combo.currentText()
                if limit_str == "全部":
                    display_history = self.detection_history
                else:
                    limit = int(limit_str)
                    display_history = self.detection_history[-limit:]
                
                # 更新歷史文字框
                self.history_text.clear()
                
                history_lines = []
                for entry in reversed(display_history):  # 最新的在上面
                    monsters_summary = {}
                    for monster in entry['monsters']:
                        name = monster.get('name', 'Unknown')
                        monsters_summary[name] = monsters_summary.get(name, 0) + 1
                    
                    summary_text = ', '.join([f"{name}×{count}" for name, count in monsters_summary.items()])
                    history_lines.append(f"[{entry['time']}] {summary_text}")
                
                self.history_text.setPlainText('\n'.join(history_lines))
                
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
            self.total_detections_label.setText(
                f"總檢測次數: {self.detection_stats['total_detections']}")
            self.unique_monsters_label.setText(
                f"發現怪物種類: {len(self.detection_stats['unique_monsters'])}")
            self.session_time_label.setText(f"運行時間: {time_str}")
            self.avg_confidence_label.setText(f"平均信心度: {avg_confidence:.2f}")
            self.detection_rate_label.setText(f"檢測頻率: {detection_rate:.1f}/分鐘")
            
        except Exception as e:
            print(f"統計更新錯誤: {e}")
    
    def _toggle_detection(self, state):
        """切換檢測狀態"""
        self.detection_enabled = bool(state)
        if self.detection_enabled:
            if not self.is_running:
                self._start_detection()
            self.status_bar.showMessage("🟡 檢測狀態：啟動中...")
        else:
            self.status_bar.showMessage("🔴 檢測狀態：已停止")
    
    def _clear_results(self):
        """清除檢測結果"""
        try:
            # 清空詳細資訊
            self.detail_text.clear()
            
            # 重置結果
            self.last_detection_results = []
            
            print("檢測結果已清除")
        except Exception as e:
            print(f"清除結果錯誤: {e}")
    
    def _clear_history(self):
        """清除檢測歷史"""
        try:
            self.detection_history = []
            self.history_text.clear()
            print("檢測歷史已清除")
        except Exception as e:
            print(f"清除歷史錯誤: {e}")
    
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
                    self._update_detection_results((results, {}))
                    print(f"📸 檢測+保存完成: {len(results)} 個結果")
                else:
                    print("📸 無檢測結果，已保存原始畫面供檢查")
            
        except Exception as e:
            print(f"❌ 檢測+保存失敗: {e}")

    def _create_auto_hunt_controls(self, parent_layout):
        """✅ 修正版：地圖檔案管理按鈕"""
        try:
            # 檔案管理區域
            file_frame = QGroupBox("📁 地圖檔案管理")
            parent_layout.addWidget(file_frame)
            
            file_layout = QVBoxLayout(file_frame)
            
            # 檔案選擇和載入
            file_control_widget = QWidget()
            file_control_layout = QHBoxLayout(file_control_widget)
            file_layout.addWidget(file_control_widget)
            
            file_control_layout.addWidget(QLabel("當前地圖:"))
            
            # ✅ 關鍵修改4：下拉選單
            self.map_combo = QComboBox()
            self.map_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)  # 改為Expanding
            if hasattr(self.ro_helper, 'waypoint_system'):
                available_files = self.ro_helper.waypoint_system.get_files()
                self.map_combo.addItems(available_files)
            file_control_layout.addWidget(self.map_combo)
            
            # ✅ 關鍵修改5：檔案操作按鈕 - 使用網格布局
            buttons_widget = QWidget()
            buttons_layout = QGridLayout(buttons_widget)
            file_layout.addWidget(buttons_widget)
            
            # 按鈕配置
            load_btn = QPushButton("📂 載入地圖")
            load_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)  # 改為Expanding
            load_btn.clicked.connect(self._load_selected_map)
            buttons_layout.addWidget(load_btn, 0, 0)
            
            save_btn = QPushButton("💾 保存地圖")
            save_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)  # 改為Expanding
            save_btn.clicked.connect(self._save_current_map)
            buttons_layout.addWidget(save_btn, 0, 1)
            
            edit_btn = QPushButton("🗺️ 編輯路徑")
            edit_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)  # 改為Expanding
            edit_btn.clicked.connect(self._open_editor)
            buttons_layout.addWidget(edit_btn, 1, 0, 1, 2)  # 跨兩列
            
            # 自動狩獵控制區域
            auto_hunt_group = QGroupBox("自動狩獵控制")
            parent_layout.addWidget(auto_hunt_group)
            
            auto_hunt_layout = QVBoxLayout()
            
            # 戰鬥模式選擇
            mode_layout = QHBoxLayout()
            mode_layout.addWidget(QLabel("戰鬥模式:"))
            
            self.melee_radio = QRadioButton("近戰")
            self.ranged_radio = QRadioButton("遠程")
            self.stationary_ranged_radio = QRadioButton("定點遠程")
            
            mode_layout.addWidget(self.melee_radio)
            mode_layout.addWidget(self.ranged_radio)
            mode_layout.addWidget(self.stationary_ranged_radio)
            mode_layout.addStretch()
            
            auto_hunt_layout.addLayout(mode_layout)
            
            # 自動狩獵開關
            self.auto_hunt_switch = QSwitch("自動狩獵")
            self.auto_hunt_switch.toggled.connect(self._toggle_auto_hunt)
            auto_hunt_layout.addWidget(self.auto_hunt_switch)
            
            # 即時顯示按鈕（整合路徑可視化）
            self.realtime_display_button = QPushButton("📺 即時顯示")
            self.realtime_display_button.clicked.connect(self._toggle_realtime_display)
            auto_hunt_layout.addWidget(self.realtime_display_button)
            
            auto_hunt_group.setLayout(auto_hunt_layout)
            
        except Exception as e:
            print(f"⚠️ 添加地圖管理功能失敗: {e}")

    def _open_editor(self):
        """開啟路徑編輯器"""
        try:
            self.ro_helper.open_editor()
        except Exception as e:
            print(f"⚠️ 開啟路徑編輯器失敗: {e}")

    def _load_selected_map(self):
        """主視窗載入地圖"""
        try:
            filename = self.map_combo.currentText()
            if not filename:
                print("❌ 請選擇要載入的地圖檔案")
                return
            
            # 載入到waypoint_system
            success = self.ro_helper.waypoint_system.load_map(filename)
            if success:
                self.status_bar.showMessage(f"✅ 主視窗載入地圖: {filename}")
                print(f"✅ 主視窗載入地圖: {filename}")
                
                # 如果編輯器已開啟，同步更新
                if hasattr(self.ro_helper, 'waypoint_editor') and self.ro_helper.waypoint_editor:
                    if hasattr(self.ro_helper.waypoint_editor, 'editor_window') and self.ro_helper.waypoint_editor.editor_window:
                        self.ro_helper.waypoint_editor._draw()
                        print("🔄 同步更新編輯器顯示")
            else:
                self.status_bar.showMessage("❌ 載入失敗")
                
        except Exception as e:
            print(f"❌ 載入地圖失敗: {e}")   

    def _save_current_map(self):
        """主視窗保存地圖"""
        try:
            filename = self.map_combo.currentText()
            if not filename:
                print("❌ 請選擇要保存的檔案")
                return
            
            file_path = os.path.join("data", filename)
            self.ro_helper.waypoint_system.save_data(file_path)
            print(f"💾 地圖已保存: {filename}")
            self.status_bar.showMessage(f"💾 地圖已保存: {filename}")
            
        except Exception as e:
            print(f"❌ 保存地圖失敗: {e}")

    def _toggle_realtime_display(self):
        """切換即時顯示（整合路徑可視化）"""
        if not hasattr(self, '_opencv_display_running'):
            self._opencv_display_running = False
            
        if not self._opencv_display_running:
            self._start_realtime_display()
        else:
            self._stop_realtime_display()

    def _start_realtime_display(self):
        """開始即時顯示"""
        if not self._opencv_display_running:
            self._opencv_display_running = True
            self.realtime_display_button.setText("🛑 停止顯示")
            self._opencv_display_thread = threading.Thread(target=self._opencv_display_loop, daemon=True)
            self._opencv_display_thread.daemon = True
            self._opencv_display_thread.start()

    def _stop_realtime_display(self):
        """停止即時顯示"""
        try:
            print("🔄 正在停止即時顯示...")
            self._opencv_display_running = False
            if hasattr(self, '_opencv_display_thread') and self._opencv_display_thread:
                if self._opencv_display_thread.is_alive():
                    self._opencv_display_thread.join(timeout=3)
            QTimer.singleShot(500, self._delayed_opencv_cleanup)
            # ✅ 重置按鈕文字
            self.realtime_display_button.setText("📺 即時顯示")
            print("✅ 即時顯示已停止")
        except Exception as e:
            print(f"❌ 停止即時顯示失敗: {e}")
            self._force_opencv_cleanup()

    def _force_opencv_cleanup(self):
        """強制清理 OpenCV 資源"""
        try:
            # 強制關閉所有 OpenCV 視窗
            cv2.destroyAllWindows()
            # 重置狀態
            self._opencv_display_running = False
            self._opencv_display_thread = None
            # ✅ 重置按鈕文字
            self.realtime_display_button.setText("📺 即時顯示")
            print("✅ 已強制清理 OpenCV 資源")
        except Exception as e:
            print(f"⚠️ 強制清理時發生警告: {e}")

    def _delayed_opencv_cleanup(self):
        """延遲清理 OpenCV 資源"""
        try:
            cv2.destroyAllWindows()
            # ✅ 重置按鈕文字
            self.realtime_display_button.setText("📺 即時顯示")
            print("✅ 已清理 OpenCV 資源")
        except Exception as e:
            print(f"⚠️ 清理 OpenCV 資源時發生警告: {e}")

    def _opencv_display_loop(self):
        """OpenCV 即時顯示循環 - 增加HUD辨識框顯示"""
        try:
            window_name = "Maple Helper - 怪物檢測"
            cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
            cv2.resizeWindow(window_name, 1280, 720)
            
            consecutive_failures = 0
            max_failures = 5
            
            while self._opencv_display_running:
                try:
                    # 獲取最新畫面
                    frame = self.ro_helper.capturer.grab_frame()
                    if frame is None:
                        consecutive_failures += 1
                        if consecutive_failures >= max_failures:
                            print("⚠️ 連續捕捉失敗次數過多，嘗試重新連接...")
                            self.ro_helper.capturer.force_reconnect()
                            consecutive_failures = 0
                        time.sleep(0.2)  # 增加等待時間
                        continue
                    
                    # 重置失敗計數
                    consecutive_failures = 0
                    
                    # 複製畫面以避免修改原始資料
                    display_frame = frame.copy()
                    
                    # 執行HUD檢測並繪製辨識框
                    display_frame = self._draw_hud_health_mana_detection(display_frame)
                    
                    # 執行血條檢測
                    display_frame = self.detect_character_overhead_health(display_frame)
                    
                    # 繪製小地圖（使用 tracker 的灰階圖）
                    minimap_rect = self.ro_helper.tracker._find_minimap_with_subpixel_accuracy(frame)
                    if minimap_rect:
                        display_frame = self._draw_minimap_visualization(display_frame, minimap_rect)
                    
                    # 顯示畫面
                    cv2.imshow(window_name, display_frame)
                    
                    # 控制顯示頻率
                    key = cv2.waitKey(1)
                    
                except Exception as e:
                    print(f"❌ 顯示循環錯誤: {e}")
                    time.sleep(0.1)
                    
        except Exception as e:
            print(f"❌ 顯示循環初始化失敗: {e}")
        finally:
            cv2.destroyAllWindows()

    def _draw_minimap_visualization(self, frame, minimap_rect):
        """繪製小地圖可視化（移除角色位置顯示）"""
        try:
            x1, y1, x2, y2 = minimap_rect
            # ✅ 繪製小地圖邊框
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
            cv2.putText(frame, "Minimap", (x1, y1-10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
            
            # ✅ 繪製其他小地圖元素（路徑點、區域等）
            if hasattr(self.ro_helper, 'waypoint_system') and self.ro_helper.waypoint_system:
                try:
                    self._draw_waypoints_on_minimap(frame, minimap_rect)
                    self._draw_areas_on_minimap(frame, minimap_rect)
                except Exception as e:
                    print(f"❌ 小地圖可視化失敗: {e}")
            return frame
        except Exception as e:
            print(f"❌ 小地圖可視化失敗: {e}")
            return frame

    def _draw_waypoints_on_minimap(self, frame, minimap_rect):
        """在小地圖上繪製路徑點"""
        try:
            x1, y1, x2, y2 = minimap_rect
            waypoints = self.ro_helper.waypoint_system.waypoints
            for i in range(len(waypoints) - 1):
                wp1 = waypoints[i]
                wp2 = waypoints[i + 1]
                px1 = int(x1 + wp1['pos'][0] * (x2 - x1))
                py1 = int(y1 + wp1['pos'][1] * (y2 - y1))
                px2 = int(x1 + wp2['pos'][0] * (x2 - x1))
                py2 = int(y1 + wp2['pos'][1] * (y2 - y1))
                cv2.line(frame, (px1, py1), (px2, py2), (255, 0, 0), 2)
                cv2.circle(frame, (px1, py1), 5, (0, 0, 255), -1)
                cv2.circle(frame, (px1, py1), 7, (255, 255, 255), 1)
                cv2.putText(frame, str(i), (px1 + 8, py1 + 8), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
            if waypoints:
                last_wp = waypoints[-1]
                px = int(x1 + last_wp['pos'][0] * (x2 - x1))
                py = int(y1 + last_wp['pos'][1] * (y2 - y1))
                cv2.circle(frame, (px, py), 5, (0, 0, 255), -1)
                cv2.circle(frame, (px, py), 7, (255, 255, 255), 1)
                cv2.putText(frame, str(len(waypoints)-1), (px + 8, py + 8), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        except Exception as e:
            print(f"❌ 路徑點繪製失敗: {e}")

    def _draw_areas_on_minimap(self, frame, minimap_rect):
        """在小地圖上繪製區域"""
        try:
            x1, y1, x2, y2 = minimap_rect
            area_grid = self.ro_helper.waypoint_system.area_grid
            area_colors = {
                'walkable': (0, 255, 0, 128),
                'forbidden': (0, 0, 255, 128),
                'rope': (255, 255, 0, 128)
            }
            overlay = frame.copy()
            for grid_key, area_type in area_grid.items():
                try:
                    rel_x, rel_y = map(float, grid_key.split(','))
                    px = int(x1 + rel_x * (x2 - x1))
                    py = int(y1 + rel_y * (y2 - y1))
                    color = area_colors.get(area_type, (128, 128, 128, 128))
                    cv2.circle(overlay, (px, py), 3, color[:3], -1)
                except Exception as e:
                    print(f"⚠️ 區域點繪製失敗: {e}")
                    continue
            cv2.addWeighted(overlay, 0.3, frame, 0.7, 0, frame)
        except Exception as e:
            print(f"❌ 區域繪製失敗: {e}")

    def _draw_hud_health_mana_detection(self, frame):
        """繪製HUD血魔條辨識框（左下角UI）"""
        try:
            if not hasattr(self, 'health_detector') or self.health_detector is None:
                return frame
            
            # 執行HUD檢測
            detection_result = self.health_detector.detect_hud_health_mana(frame)
            
            # 繪製HUD主框
            if detection_result.get('hud_rect'):
                x, y, w, h = detection_result['hud_rect']
                # 繪製HUD主框 - 藍色
                cv2.rectangle(frame, (x, y), (x+w, y+h), (255, 0, 0), 2)
                cv2.putText(frame, 'HUD', (x, y-10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 0, 0), 2)
                
                # 顯示匹配度信息
                if detection_result.get('success'):
                    hp_pct = detection_result.get('hp_percentage', 0)
                    mp_pct = detection_result.get('mp_percentage', 0)
                    status_text = f"HP: {hp_pct:.1f}% MP: {mp_pct:.1f}%"
                    cv2.putText(frame, status_text, (x, y+h+20), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 0, 0), 2)
            
            # 繪製HP條框
            if detection_result.get('hp_rect'):
                x, y, w, h = detection_result['hp_rect']
                # 繪製HP條框 - 紅色
                cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 0, 255), 2)
                cv2.putText(frame, 'HP', (x, y-5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)
            
            # 繪製MP條框
            if detection_result.get('mp_rect'):
                x, y, w, h = detection_result['mp_rect']
                # 繪製MP條框 - 藍色
                cv2.rectangle(frame, (x, y), (x+w, y+h), (255, 0, 0), 2)
                cv2.putText(frame, 'MP', (x, y-5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 1)
            
            return frame
            
        except Exception as e:
            print(f"❌ HUD血魔條辨識框繪製失敗: {e}")
            return frame

    def detect_character_overhead_health(self, frame):
        """
        調用 HealthManaDetector 中的方法來檢測角色頭頂血條，並在畫面上繪製結果。
        """
        if not hasattr(self, 'health_detector') or self.health_detector is None:
            return frame

        try:
            # 呼叫外部檢測器
            health_bars = self.health_detector.detect_character_overhead_health(frame)

            # 在畫面上繪製所有找到的血條
            if health_bars:
                # 創建一個副本以避免修改原始幀
                overlay_frame = frame.copy()
                for i, (x, y, w, h) in enumerate(health_bars):
                    # 繪製綠色矩形
                    cv2.rectangle(overlay_frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
                    # 繪製標籤
                    cv2.putText(overlay_frame, f'HP_{i}', (x, y - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
                return overlay_frame
            else:
                return frame # 如果沒有找到，返回原來的幀

        except Exception as e:
            print(f"❌ 在 GUI 中繪製頭頂血條時發生錯誤: {e}")
            return frame

    def _match_template(self, img, template_path, threshold=0.7):
        """模板匹配輔助函數"""
        try:
            template = cv2.imread(template_path, cv2.IMREAD_GRAYSCALE)
            if template is None:
                print(f"❌ 模板讀取失敗: {template_path}")
                return None
            img_gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            result = cv2.matchTemplate(img_gray, template, cv2.TM_CCOEFF_NORMED)
            min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
            if max_val >= threshold:
                h, w = template.shape[:2]
                return (max_loc[0], max_loc[1], w, h)
            return None
        except Exception as e:
            print(f"❌ 模板匹配失敗: {e}")
            return None

    def _toggle_auto_hunt(self, state):
        """切換自動狩獵狀態"""
        try:
            if not hasattr(self.ro_helper, 'auto_combat'):
                print("❌ 戰鬥系統未初始化")
                return

            # 確保路徑點系統已設置
            if not self.ro_helper.auto_combat.waypoint_system:
                self.ro_helper.auto_combat.set_waypoint_system(self.ro_helper.waypoint_system)

            if state:
                # 開啟自動狩獵
                print("🔄 嘗試開啟自動狩獵...")
                
                # 檢查戰鬥模式
                combat_mode = self.combat_mode
                if not combat_mode:
                    print("❌ 請先選擇戰鬥模式")
                    return

                # 設置戰鬥設定
                self.ro_helper.auto_combat.hunt_settings = {
                    'combat_mode': combat_mode,
                    'attack_range': self.attack_range,
                    'approach_distance': self.approach_distance,
                    'retreat_distance': self.retreat_distance,
                    'attack_cooldown': self.attack_cooldown,
                    'movement_speed': self.movement_speed,
                    'use_waypoints': self.use_waypoints,
                    'patrol_mode': self.patrol_mode,
                    'max_chase_distance': self.max_chase_distance,
                    'return_to_safe': self.return_to_safe
                }

                # 啟動戰鬥系統
                if self.ro_helper.auto_combat.start():
                    self.auto_hunt_enabled = True
                    self.auto_hunt_mode = "attack"
                    print("✅ 自動狩獵已開啟")
                    print(f"🎯 戰鬥模式: {combat_mode}")
                    print(f"🔍 戰鬥系統狀態: is_enabled={self.ro_helper.auto_combat.is_enabled}")
                else:
                    print("❌ 啟動戰鬥系統失敗")
                    self.auto_hunt_switch.setChecked(False)
                    self.auto_hunt_enabled = False
                    self.auto_hunt_mode = "off"

            else:
                # 關閉自動狩獵
                print("🔄 關閉自動狩獵...")
                self.ro_helper.auto_combat.stop()
                self.auto_hunt_enabled = False
                self.auto_hunt_mode = "off"
                print("✅ 自動狩獵已關閉")
                print(f"🔍 戰鬥系統狀態: is_enabled={self.ro_helper.auto_combat.is_enabled}")

        except Exception as e:
            print(f"❌ 切換自動狩獵狀態失敗: {e}")
            import traceback
            traceback.print_exc()
            # 確保狀態重置
            self.auto_hunt_switch.setChecked(False)
            self.auto_hunt_enabled = False
            self.auto_hunt_mode = "off"
            if hasattr(self.ro_helper, 'auto_combat'):
                self.ro_helper.auto_combat.is_enabled = False
                self.ro_helper.auto_combat.auto_hunt_mode = "off"

    def _setup_melee_combat(self):
        """設置近戰戰鬥模式"""
        self.combat_settings = {
            'combat_mode': 'waypoint',  # 近戰使用路徑點模式
            'attack_cooldown': 0.5,
            'use_waypoints': True,
            'search_radius': 0.1
        }
        print("⚔️ 已設置近戰模式")

    def _setup_ranged_combat(self):
        """設置遠程戰鬥模式"""
        self.combat_settings = {
            'combat_mode': 'waypoint',  # 遠程也使用路徑點模式
            'attack_cooldown': 1.0,
            'use_waypoints': True,
            'search_radius': 0.15
        }
        print("🏹 已設置遠程模式")

    def _setup_stationary_ranged_combat(self):
        """修正版：確保正確設置安全區域模式"""
        try:
            # ✅ 關鍵修正：設置為安全區域模式
            self.combat_settings = {
                'combat_mode': 'safe_area',   # ✅ 明確設置為安全區域模式
                'attack_range': 0.4,
                'approach_distance': 0.1,
                'retreat_distance': 0.05,
                'attack_cooldown': 1.5,
                'movement_speed': 0.8,
                'use_waypoints': False,       # ✅ 不使用路徑點
                'patrol_mode': 'safe_area',
                'max_chase_distance': 0.15,
                'return_to_safe': True
            }
            
            print("🎯 已設置安全區域巡邏遠程模式")
            print(f"🔍 戰鬥模式: {self.combat_settings['combat_mode']}")
            
        except Exception as e:
            print(f"❌ 設置巡邏遠程模式失敗: {e}")

    def _on_combat_mode_changed(self, mode):
        """處理戰鬥模式切換"""
        try:
            print(f"🎯 已切換到{mode}模式")
            
            # 根據不同模式設置不同的戰鬥策略
            if mode == "melee":
                self._setup_melee_combat()
            elif mode == "ranged":
                self._setup_ranged_combat()
            elif mode == "stationary_ranged":
                self._setup_stationary_ranged_combat()
            
            # 啟動戰鬥系統
            if hasattr(self, 'ro_helper') and hasattr(self.ro_helper, 'auto_combat'):
                # 確保戰鬥系統已設置路徑系統
                self.ro_helper.auto_combat.set_waypoint_system(self.ro_helper.waypoint_system)
                self.ro_helper.auto_combat.set_auto_hunt_mode("attack")
                self.ro_helper.auto_combat.set_hunt_settings(self.combat_settings)
                self.ro_helper.auto_combat.start()  # 確保啟用戰鬥系統
                print("⚔️ 戰鬥系統已啟動")
                print(f"🔍 自動打怪模式: {self.ro_helper.auto_combat.auto_hunt_mode}")
                print(f"🔍 路徑點系統狀態: {self.ro_helper.waypoint_system is not None}")
                print(f"🔍 戰鬥模式: {self.combat_settings['combat_mode']}")
            
        except Exception as e:
            print(f"❌ 切換戰鬥模式失敗: {e}")
            QMessageBox.warning(self, "錯誤", f"切換戰鬥模式失敗: {e}")
    
    def _refresh_template_folders(self):
        """重新整理怪物模板資料夾列表"""
        try:
            # 清空現有項目
            self.template_folder_combo.clear()
            
            # 獲取怪物模板資料夾路徑
            template_path = os.path.join("templates", "monsters")
            if not os.path.exists(template_path):
                print(f"❌ 找不到怪物模板資料夾: {template_path}")
                return
            
            # 獲取所有資料夾
            folders = [f for f in os.listdir(template_path) 
                      if os.path.isdir(os.path.join(template_path, f))]
            
            if not folders:
                print("⚠️ 沒有找到任何怪物模板資料夾")
                return
            
            # 添加到下拉選單
            self.template_folder_combo.addItems(folders)
            print(f"✅ 已載入 {len(folders)} 個怪物模板資料夾")
            
        except Exception as e:
            print(f"❌ 重新整理模板資料夾失敗: {e}")

    def _on_template_folder_changed(self, index):
        """當選擇的模板資料夾改變時"""
        try:
            if index < 0:
                return
                
            folder_name = self.template_folder_combo.currentText()
            if not folder_name:
                return
            
            # 構建完整路徑
            template_path = os.path.join("templates", "monsters", folder_name)
            
            # 通知 monster_detector 載入新模板
            if self.monster_detector:
                success = self.monster_detector.load_templates_from_folder(template_path)
                if success:
                    print(f"✅ 已載入模板資料夾: {folder_name}")
                    self.status_bar.showMessage(f"✅ 已載入模板: {folder_name}")
                else:
                    print(f"❌ 載入模板失敗: {folder_name}")
                    self.status_bar.showMessage(f"❌ 載入模板失敗: {folder_name}")
            
        except Exception as e:
            print(f"❌ 切換模板資料夾失敗: {e}")

    def _refresh_map_files(self):
        """重新整理地圖檔案列表"""
        try:
            # 清空現有項目
            self.map_combo.clear()
            
            # 獲取可用的地圖檔案
            map_files = get_available_map_files()
            
            if not map_files:
                print("⚠️ 沒有找到地圖檔案")
                return
            
            # 添加到下拉選單
            for file_name in map_files:
                self.map_combo.addItem(file_name)
            
            print(f"✅ 已載入 {len(map_files)} 個地圖檔案")
            
        except Exception as e:
            print(f"❌ 更新地圖檔案列表失敗: {e}")
            import traceback
            traceback.print_exc()

    def _draw_monsters_on_frame(self, display_frame):
        """在畫面上繪製怪物檢測結果"""
        try:
            if self.monster_detector:
                monsters = self.monster_detector.detect_monsters(display_frame)
                
                for monster in monsters:
                    center = self._get_monster_center(monster)
                    if center:
                        # 繪製怪物邊界框
                        if 'corners' in monster:
                            corners = monster['corners']
                            if isinstance(corners, np.ndarray):
                                cv2.polylines(display_frame, [np.int32(corners)], 
                                            True, (0, 255, 255), 2)
                        
                        # 繪製中心點
                        cv2.circle(display_frame, center, 6, (0, 255, 255), -1)
                        
                        # 顯示怪物資訊
                        name = monster.get('name', 'Unknown')
                        confidence = monster.get('confidence', 0)
                        text = f"{name} ({confidence:.2f})"
                        
                        cv2.putText(display_frame, text, (center[0]-20, center[1]-30),
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)
        except Exception as e:
            print(f"⚠️ 怪物繪製失敗: {e}")
        
        return display_frame

    def _get_monster_center(self, monster):
        """獲取怪物中心點"""
        try:
            # 優先使用 corners 屬性
            if 'corners' in monster:
                corners = monster['corners']
                if isinstance(corners, np.ndarray):
                    # 處理 (4, 1, 2) 形狀的陣列
                    if len(corners.shape) == 3 and corners.shape[0] == 4 and corners.shape[2] == 2:
                        corners = corners.reshape(4, 2)
                    # 處理 (4, 2) 形狀的陣列
                    if len(corners.shape) == 2 and corners.shape[1] == 2:
                        center = np.mean(corners, axis=0)
                        if len(center) >= 2:
                            return (int(center[0]), int(center[1]))
            
            # 備用方案：使用 position 屬性
            if 'position' in monster:
                position = monster['position']
                if isinstance(position, (tuple, list)) and len(position) >= 2:
                    return (int(position[0]), int(position[1]))
                elif isinstance(position, np.ndarray) and position.size >= 2:
                    return (int(position[0]), int(position[1]))
            
            return None
        except Exception as e:
            print(f"⚠️ 獲取怪物中心點失敗: {e}")
            return None

    def _draw_monsters_on_full_frame(self, frame):
        """在全畫面上繪製怪物檢測結果"""
        try:
            display_frame = frame.copy()
            if self.monster_detector:
                monsters = self.monster_detector.detect_monsters(frame)
                
                for monster in monsters:
                    center = self._get_monster_center(monster)
                    if center:
                        # 繪製怪物邊界框
                        if 'corners' in monster:
                            corners = monster['corners']
                            if isinstance(corners, np.ndarray):
                                cv2.polylines(display_frame, [np.int32(corners)], 
                                            True, (0, 255, 255), 2)
                        
                        # 繪製中心點
                        cv2.circle(display_frame, center, 6, (0, 255, 255), -1)
                        
                        # 顯示怪物資訊
                        name = monster.get('name', 'Unknown')
                        confidence = monster.get('confidence', 0)
                        text = f"{name} ({confidence:.2f})"
                        
                        cv2.putText(display_frame, text, (center[0]-20, center[1]-30),
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)
        except Exception as e:
            print(f"⚠️ 全畫面怪物繪製失敗: {e}")
        
        return display_frame

    def _start_async_processing(self):
        """啟動異步處理"""
        self.processing_thread = threading.Thread(
            target=self._async_processing_worker,
            daemon=True
        )
        self.processing_thread.start()
    
    def _async_processing_worker(self):
        """異步處理工作執行緒"""
        while True:
            try:
                frame = self.detection_queue.get(timeout=1)
                if frame is not None:
                    # 處理畫面
                    monsters, health_info = self.monster_detector.detect_monsters(frame)
                    
                    # 放入結果佇列
                    try:
                        self.result_queue.put((frame, monsters, health_info), block=False)
                    except queue.Full:
                        pass
            except queue.Empty:
                continue
            except Exception as e:
                print(f"❌ 異步處理失敗: {e}")
    
    def _detection_loop(self):
        """✅ 優化版：控制檢測和更新頻率"""
        try:
            while self.is_running:
                if self.detection_enabled:
                    # 獲取畫面
                    frame = self.ro_helper.capturer.grab_frame()
                    if frame is not None:
                        # 放入檢測佇列
                        try:
                            self.detection_queue.put(frame, block=False)
                        except queue.Full:
                            pass
                    
                    # 檢查結果佇列
                    try:
                        frame, monsters, health_info = self.result_queue.get_nowait()
                        
                        # 控制 GUI 更新頻率
                        current_time = time.time() * 1000
                        if current_time - self.last_gui_update > self.gui_update_interval:
                            self._update_gui(frame, monsters)
                            self.last_gui_update = current_time
                            
                    except queue.Empty:
                        pass
                
                time.sleep(0.05)  # 降低到 20 FPS
                
        except Exception as e:
            print(f"❌ 檢測循環失敗: {e}")
    
    def _update_gui(self, frame, monsters):
        """✅ 優化版：更新 GUI"""
        try:
            # 處理血條資訊
            health_info = {}
            if self.health_detector:
                health_info = self.health_detector.detect_hud_health_mana(frame)
                
                if health_info.get('success', False):
                    hp_percent = health_info.get('hp_percentage', 0)
                    mp_percent = health_info.get('mp_percentage', 0)
                    
                    # 更新狀態列
                    self.statusBar().showMessage(
                        f"HP: {hp_percent:.1f}% | MP: {mp_percent:.1f}% | "
                        f"怪物數量: {len(monsters)}"
                    )
            
            # 更新怪物列表
            self._update_monster_list(monsters)
            
            # 更新畫面
            self._update_frame(frame)
            
            # 更新狀態
            self._update_status()
            
        except Exception as e:
            print(f"❌ GUI 更新失敗: {e}")
    
    def _update_monster_list(self, monsters):
        """更新怪物列表"""
        try:
            self.monster_list.clear()
            for monster in monsters:
                item = QListWidgetItem(
                    f"{monster['type']} - 信心度: {monster['confidence']:.2f}"
                )
                self.monster_list.addItem(item)
                
        except Exception as e:
            print(f"❌ 更新怪物列表失敗: {e}")
    
    def _update_frame(self, frame):
        """更新畫面"""
        try:
            if frame is not None:
                # 轉換為 QImage
                height, width, channel = frame.shape
                bytes_per_line = 3 * width
                q_image = QImage(
                    frame.data, width, height,
                    bytes_per_line, QImage.Format_RGB888
                )
                
                # 更新標籤
                self.frame_label.setPixmap(
                    QPixmap.fromImage(q_image).scaled(
                        self.frame_label.size(),
                        Qt.KeepAspectRatio,
                        Qt.FastTransformation
                    )
                )
                
        except Exception as e:
            print(f"❌ 更新畫面失敗: {e}")
    
    def _update_status(self):
        """更新狀態"""
        try:
            status = self.ro_helper.get_status()
            self.status_label.setText(
                f"追蹤: {'啟用' if status['tracking_enabled'] else '停用'} | "
                f"戰鬥: {'啟用' if status['combat_enabled'] else '停用'} | "
                f"ADB: {'已連接' if status['adb_connected'] else '未連接'}"
            )
            
        except Exception as e:
            print(f"❌ 更新狀態失敗: {e}")

    def run(self):
        """啟動 GUI 事件循環"""
        self.show()
        return QApplication.instance().exec_()

# 如果直接運行此檔案，提供測試入口
if __name__ == '__main__':
    app = QApplication(sys.argv)
    
    # 創建一個模擬的 ro_helper 用於測試
    class MockRoHelper:
        def __init__(self):
            self.monster_detector = None
            self.capturer = None
    
    mock_helper = MockRoHelper()
    gui = MonsterDetectionGUI(mock_helper)
    
    sys.exit(gui.run())
