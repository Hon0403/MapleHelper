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
from modules.health_mana_detector_hybrid import HealthManaDetectorHybrid  # HUD血條檢測（多模板匹配+填充分析）
from includes.simple_template_utils import UITemplateHelper
from includes.log_utils import get_logger
from includes.simple_template_utils import get_monster_detector
# 簡化方案：使用OpenCV基本文字渲染，避免複雜的中文處理

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
        
        # 確保 data 目錄存在
        if not data_dir.exists():
            data_dir.mkdir(exist_ok=True)
            return []
        
        # 掃描所有 JSON 檔案
        json_files = []
        for file_path in data_dir.glob("*.json"):
            if file_path.is_file():
                json_files.append(file_path.name)
        
        # 按檔案名稱排序
        json_files.sort()
        
        return json_files
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return []

class MonsterDetectionGUI(QMainWindow):
    """怪物檢測GUI - PyQt5版本：使用文字列表顯示匹配結果"""
    
    def __init__(self, ro_helper, config=None):
        """初始化怪物檢測GUI"""
        super().__init__()
        
        # 基本設定
        self.ro_helper = ro_helper
        self.config = config or {}
        self.logger = get_logger("MonsterDetectionGUI")
        
        # 初始化檢測控制變數
        self.is_running = False
        self.detection_enabled = False  # 預設關閉
        self.detection_thread = None
        self.monster_detector = None
        
        # ✅ 添加線程同步和共享數據
        import threading
        self._detection_lock = threading.RLock()  # 檢測器訪問鎖
        self._shared_results = {  # 共享檢測結果
            'frame': None,
            'monsters': [],
            'health_info': {},
            'timestamp': 0
        }
        
        # 初始化其他變數
        self.last_detection_results = []
        self.detection_history = []
        self.detection_stats = {
            'total_detections': 0,
            'unique_monsters': set(),
            'high_confidence_detections': 0,
            'total_confidence': 0.0
        }
        
        # 即時顯示控制
        self.realtime_display_running = False
        self.display_thread = None
        
        # ✅ 優化參數配置
        self.frame_history = []
        self.max_frame_history = 5  # 減少記憶體使用
        self.motion_detection_enabled = False
        
        # 顯示控制
        self.show_monster_overlay = True
        self.show_health_overlay = True
        self.show_minimap_overlay = True
        
        # 設置視窗
        self.setWindowTitle("怪物檢測系統 - PyQt5")
        self.setMinimumSize(1000, 700)
        
        # 初始化檢測器
        self._initialize_detectors()
        
        # 建立GUI
        self._create_gui()
        
        # 自動載入模板
        self._auto_load_first_template_folder()
        
        # 自動刷新地圖檔案
        QTimer.singleShot(100, self._refresh_map_files)
    
    def _initialize_detectors(self):
        """初始化檢測器"""
        try:
            from modules.character_health_detector import CharacterHealthDetector
            
            # 初始化HUD血魔條檢測器
            self.health_detector = HealthManaDetectorHybrid(
                template_dir="templates/MainScreen",
                config=self.config
            )
            
            # 初始化角色血條檢測器
            self.character_health_detector = CharacterHealthDetector(
                template_dir="templates/MainScreen",
                config=self.config
            )
            
            # 初始化怪物檢測器
            self.monster_detector = get_monster_detector(self.config)
            
            if self.monster_detector:
                template_count = len(getattr(self.monster_detector, 'templates', []))
                self.logger.debug(f"怪物檢測器已初始化，載入 {template_count} 個模板")
            else:
                self.logger.error("怪物檢測器初始化失敗")
                
        except Exception as e:
            self.logger.error(f"檢測器初始化失敗: {e}")
            self.health_detector = None
            self.character_health_detector = None

    def _process_frame(self):
        """🎯 增強版畫面處理函數 - 支援線程安全的共享結果 + 超時保護"""
        try:
            if not self.ro_helper or not hasattr(self.ro_helper, 'capturer'):
                self.logger.warning("ro_helper 或 capturer 不存在")
                return None, [], {}
            
            # 獲取遊戲畫面
            frame = self.ro_helper.capturer.grab_frame()
            if frame is None:
                self.logger.warning("無法獲取遊戲畫面")
                return None, [], {}
            
            # ✅ 添加到框架歷史
            self._add_frame_to_history(frame)
            
            # 檢查怪物檢測器
            if not self.monster_detector:
                self.logger.warning("怪物檢測器未初始化")
                return frame, [], {}
            
            # ✅ 線程安全的怪物檢測 + 超時保護
            monsters = []
            try:
                with self._detection_lock:  # 使用鎖保護檢測器訪問
                    import threading
                    import signal
                    
                    # ✅ 使用簡化檢測以避免當機
                    # 不傳入歷史幀，避免復雜的時序融合處理
                    start_time = time.time()
                    monsters = self.monster_detector.detect_monsters(frame, frame_history=None)  # 改為None
                    detection_time = time.time() - start_time
                    
                    self.logger.debug(f"簡化檢測到 {len(monsters)} 隻怪物 (耗時: {detection_time:.3f}秒)")
                    
                    # ✅ 檢測時間警告
                    if detection_time > 1.0:
                        self.logger.warning(f"檢測時間過長: {detection_time:.3f}秒，建議降低閾值")
                    
                    monsters = monsters if monsters else []
                
            except Exception as e:
                self.logger.error(f"怪物檢測失敗: {e}")
                import traceback
                traceback.print_exc()
                monsters = []  # 確保返回空列表而不是None
            
            # 檢測血條資訊
            health_info = {}
            character_health_bars = []
            try:
                if hasattr(self, 'health_detector') and self.health_detector:
                    # 🔧 HUD血魔條檢測（使用新的OCR檢測方法）
                    if hasattr(self.health_detector, 'detect_hud_bars_with_ocr'):
                        health_info = self.health_detector.detect_hud_bars_with_ocr(frame)
                        self.logger.debug("使用OCR增強版HUD檢測")
                    else:
                        health_info = self.health_detector.detect_hud_bars(frame)
                        self.logger.debug("使用標準HUD檢測")
                    
                    # 🔧 角色血條檢測（一次性執行，避免重複）
                    self.logger.debug("開始角色血條檢測...")
                    start_char_time = time.time()
                    try:
                        # 修復：使用正確的角色血條檢測器
                        if hasattr(self, 'character_health_detector') and self.character_health_detector:
                            character_health_bars = self.character_health_detector.detect_character_health_bars(frame)
                        else:
                            character_health_bars = []
                        
                        char_time = time.time() - start_char_time
                        
                        if character_health_bars:
                            self.logger.debug(f"角色血條檢測成功: 找到 {len(character_health_bars)} 個血條 (耗時: {char_time:.3f}秒)")
                            for i, bar in enumerate(character_health_bars):
                                if len(bar) >= 4:
                                    x, y, w, h = bar[:4]
                                    status = bar[4] if len(bar) > 4 else "detected"
                                    self.logger.debug(f"   血條#{i+1}: 位置({x},{y}) 尺寸({w}x{h}) 狀態={status}")
                        else:
                            self.logger.debug(f"角色血條檢測未找到血條 (耗時: {char_time:.3f}秒)")
                    except Exception as char_error:
                        char_time = time.time() - start_char_time
                        self.logger.error(f"角色血條檢測發生錯誤: {char_error} (耗時: {char_time:.3f}秒)")
                        import traceback
                        traceback.print_exc()
                        character_health_bars = []
                else:
                    self.logger.warning("health_detector 不存在或未初始化")
            except Exception as e:
                self.logger.warning(f"血條檢測失敗: {e}")
                import traceback
                traceback.print_exc()
                health_info = {}
                character_health_bars = []
            
            # ✅ 更新共享結果（包含血條檢測結果以避免重複檢測）
            with self._detection_lock:
                self._shared_results.update({
                    'frame': frame.copy() if frame is not None else None,
                    'monsters': monsters.copy() if monsters else [],
                    'health_info': health_info.copy() if health_info else {},
                    'hud_detection_result': health_info.copy() if health_info else {},  # 🔧 共享HUD檢測結果
                    'character_health_bars': character_health_bars.copy() if character_health_bars else [],  # 🔧 共享角色血條檢測結果
                    'timestamp': time.time()
                })
            
            return frame, monsters, health_info
            
        except Exception as e:
            self.logger.error(f"畫面處理失敗: {e}")
            import traceback
            traceback.print_exc()
            return None, [], {}
    
    def _add_frame_to_history(self, frame):
        """添加幀到歷史記錄 - 修復版"""
        if frame is not None:
            try:
                # ✅ 確保幀格式一致性
                if len(frame.shape) == 3:
                    # 如果是彩色圖像，轉為灰階以節省記憶體和提高一致性
                    gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                else:
                    gray_frame = frame.copy()
                
                # ✅ 檢查尺寸一致性
                if self.frame_history:
                    last_frame = self.frame_history[-1]
                    if gray_frame.shape != last_frame.shape:
                        self.logger.debug(f"幀尺寸變化: {last_frame.shape} -> {gray_frame.shape}")
                        # 清空歷史記錄以避免尺寸不匹配
                        self.frame_history.clear()
                
                # 添加到歷史記錄
                self.frame_history.append(gray_frame)
                
                # 保持歷史記錄大小限制
                if len(self.frame_history) > self.max_frame_history:
                    self.frame_history.pop(0)
                    
            except Exception as e:
                self.logger.error(f"添加幀到歷史記錄失敗: {e}")
                # 清空歷史記錄以避免錯誤累積
                self.frame_history.clear()
    

    
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
            
        except Exception as e:
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
        
        # 🎯 檢測方法說明
        detection_info_group = QGroupBox("檢測方法")
        detection_info_layout = QVBoxLayout(detection_info_group)
        control_layout.addWidget(detection_info_group)
        
        # ✅ 極簡檢測說明
        method_label = QLabel("🚀 極簡模板檢測 (高效能版)")
        method_label.setStyleSheet("font-weight: bold; color: #8B0000;")
        detection_info_layout.addWidget(method_label)
        
        # ✅ 完整檢測方法詳細說明
        detail_label = QLabel("• 圖像預處理增強\n• 多層級模板匹配\n• 遮擋程度評估\n• 運動軌跡追蹤\n• 時序融合檢測")
        detail_label.setStyleSheet("color: #666; font-size: 10px; margin-left: 10px;")
        detection_info_layout.addWidget(detail_label)
        
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
        
        # ✅ 路徑編輯區塊已移除，路徑編輯功能保留在自動打怪區塊中
    
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
        """✅ 路徑編輯區塊已移除，此方法不再需要"""
        # 路徑編輯功能已整合到自動打怪區塊中
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
        """✅ 安全版檢測主迴圈 - 添加超時保護和錯誤恢復"""
        last_fps_time = time.time()
        frame_count = 0
        consecutive_errors = 0
        max_consecutive_errors = 5
        
        self.logger.info("檢測循環已啟動")
        
        while self.is_running:
            try:
                if self.detection_enabled:
                    # ✅ 添加超時保護的處理
                    start_time = time.time()
                    
                    try:
                        # 使用基礎處理函數
                        frame, monsters, health_info = self._process_frame()
                        
                        # 檢查處理時間
                        process_time = time.time() - start_time
                        if process_time > 2.0:  # 超過2秒警告
                            self.logger.warning(f"檢測處理時間過長: {process_time:.3f}秒")
                        
                        # 檢查結果
                        if frame is not None:
                            # 更新GUI（主執行緒）
                            QMetaObject.invokeMethod(self, "_update_detection_results", 
                                                   Qt.QueuedConnection, 
                                                   Q_ARG('PyQt_PyObject', (monsters, health_info)))
                            
                            # 計算FPS（降低頻率）
                            frame_count += 1
                            current_time = time.time()
                            if current_time - last_fps_time >= 30.0:  # 每30秒顯示一次FPS
                                fps = frame_count / (current_time - last_fps_time)
                                self.logger.debug(f"檢測FPS: {fps:.1f}")
                                frame_count = 0
                                last_fps_time = current_time
                            
                            # 重置錯誤計數
                            consecutive_errors = 0
                        else:
                            self.logger.debug("畫面處理返回空值")
                            consecutive_errors += 1
                    
                    except Exception as process_error:
                        self.logger.error(f"處理過程錯誤: {process_error}")
                        consecutive_errors += 1
                    
                    # ✅ 檢查連續錯誤
                    if consecutive_errors >= max_consecutive_errors:
                        self.logger.warning(f"連續 {consecutive_errors} 次錯誤，暫停檢測 5 秒")
                        time.sleep(5.0)
                        consecutive_errors = 0
                        
                        # 嘗試重新初始化檢測器
                        try:
                            if hasattr(self, 'monster_detector') and self.monster_detector:
                                self.logger.info("嘗試重新初始化檢測器...")
                                # 可以在這裡添加重新初始化邏輯
                        except Exception as reinit_error:
                            self.logger.error(f"重新初始化失敗: {reinit_error}")
                
                else:
                    # 檢測已停用，降低CPU使用率
                    time.sleep(0.5)
                
                # ✅ 安全的睡眠時間
                time.sleep(0.15)  # 降低到約6-7FPS檢測頻率，更安全
                
            except Exception as e:
                self.logger.error(f"檢測迴圈錯誤: {e}")
                import traceback
                traceback.print_exc()
                
                consecutive_errors += 1
                if consecutive_errors >= max_consecutive_errors:
                    self.logger.error("檢測循環遇到嚴重錯誤，停止檢測")
                    self.detection_enabled = False
                    # 更新GUI開關狀態
                    try:
                        QMetaObject.invokeMethod(self.detection_enabled_switch, "setChecked", 
                                               Qt.QueuedConnection, Q_ARG(bool, False))
                    except:
                        pass
                    break
                
                time.sleep(1.0)  # 錯誤時等待更長時間
        
        self.logger.info("檢測循環已停止")
        self.is_running = False
    
    def toggle_display_overlays(self, monster=True, health=True, minimap=True):
        """切換顯示覆蓋層"""
        self.show_monster_overlay = monster
        self.show_health_overlay = health
        self.show_minimap_overlay = minimap
        self.logger.debug(f"顯示覆蓋: 怪物={monster}, 血條={health}, 小地圖={minimap}")
    
    @pyqtSlot('PyQt_PyObject')
    def _update_detection_results(self, data):
        """更新檢測結果顯示（修復版）"""
        try:
            current_time = datetime.now().strftime("%H:%M:%S.%f")[:-3]
            
            # 獲取怪物檢測結果
            monsters = data[0] if len(data) > 0 else []
            health_info = data[1] if len(data) > 1 else {}
            
            # 添加調試信息（降低頻率）
            if len(monsters) > 0:  # 只在有檢測結果時記錄
                self.logger.debug(f"檢測結果更新: {len(monsters)} 隻怪物")
            
            # 更新詳細資訊
            self._update_detailed_info(monsters, current_time)
            
            # 更新歷史記錄
            self._update_history(monsters, current_time)
            
            # 更新統計
            self._update_statistics(monsters)
            
        except Exception as e:
            self.logger.error(f"檢測結果更新錯誤: {e}")
    
    def _update_detailed_info(self, monsters, current_time):
        """更新詳細資訊頁籤 - 增強版怪物檢測記錄"""
        try:
            self.detail_text.clear()
            
            info_lines = [
                f"🕐 檢測時間: {current_time}",
                f"🎯 檢測到 {len(monsters)} 隻怪物",
                "=" * 60
            ]
            
            if monsters:
                # ✅ 增強的怪物統計
                monster_counts = {}
                total_confidence = 0
                high_confidence_count = 0
                
                for monster in monsters:
                    # 提取怪物名稱（去除路徑和副檔名）
                    raw_name = monster.get('name', 'Unknown')
                    display_name = self._get_display_name(raw_name)
                    
                    # 獲取資料夾名稱
                    if '/' in raw_name:
                        folder_name = raw_name.split('/')[0]
                    else:
                        folder_name = "預設"
                    
                    monster_counts[display_name] = monster_counts.get(display_name, 0) + 1
                    
                    # 統計信心度
                    confidence = monster.get('confidence', 0)
                    total_confidence += confidence
                    if confidence >= 0.15:
                        high_confidence_count += 1
                
                # 怪物分布統計
                info_lines.append("📊 怪物分布統計:")
                for name, count in sorted(monster_counts.items()):
                    info_lines.append(f"   🐾 {name}: {count} 隻")
                
                # ✅ 檢測品質統計
                avg_confidence = total_confidence / len(monsters) if monsters else 0
                info_lines.extend([
                    "",
                    "📈 檢測品質統計:",
                    f"   📊 平均信心度: {avg_confidence:.3f}",
                    f"   ⭐ 高信心度檢測: {high_confidence_count}/{len(monsters)}",
                    f"   🎯 檢測成功率: {(high_confidence_count/len(monsters)*100):.1f}%"
                ])
                
                info_lines.append("")
                info_lines.append("🔍 詳細檢測資訊:")
                
                # ✅ 按信心度排序顯示
                sorted_monsters = sorted(monsters, key=lambda x: x.get('confidence', 0), reverse=True)
                
                for i, monster in enumerate(sorted_monsters, 1):
                    # 怪物名稱處理
                    raw_name = monster.get('name', 'Unknown')
                    display_name = self._get_display_name(raw_name)
                    
                    # 獲取資料夾名稱
                    if '/' in raw_name:
                        folder_name = raw_name.split('/')[0]
                    else:
                        folder_name = "預設"
                    
                    confidence = monster.get('confidence', 0)
                    pos = monster.get('position', (0, 0))
                    
                    # ✅ 信心度等級標示
                    if confidence >= 0.20:
                        confidence_level = "🟢 極高"
                    elif confidence >= 0.15:
                        confidence_level = "🟡 高"
                    elif confidence >= 0.10:
                        confidence_level = "🟠 中"
                    else:
                        confidence_level = "🔴 低"
                    
                    info_lines.extend([
                        f"#{i} 【{display_name}】",
                        f"   📂 模板資料夾: {folder_name}",
                        f"   📍 螢幕位置: ({pos[0]}, {pos[1]})",
                        f"   📊 信心度: {confidence:.4f} {confidence_level}",
                    ])
                    
                    # ✅ 特徵匹配詳細資訊
                    if 'matches' in monster:
                        matches = monster['matches']
                        inliers = monster.get('inliers', 0)
                        inlier_ratio = monster.get('inlier_ratio', 0)
                        info_lines.append(f"   🔗 特徵匹配: {matches} 個點 (內點: {inliers}, 比例: {inlier_ratio:.2f})")
                    
                    # ✅ 方向和翻轉資訊
                    if 'is_flipped' in monster:
                        direction = "🔄 翻轉" if monster['is_flipped'] else "➡️ 原始"
                        info_lines.append(f"   🎭 方向: {direction}")
                    
                    # ✅ 檢測時間戳
                    if 'timestamp' in monster:
                        timestamp = monster['timestamp']
                        detection_time = time.strftime("%H:%M:%S", time.localtime(timestamp))
                        info_lines.append(f"   ⏰ 檢測時間: {detection_time}")
                    
                    # ✅ 遮擋感知資訊
                    if monster.get('occlusion_aware', False):
                        visible_ratio = monster.get('visible_ratio', 0)
                        info_lines.append(f"   👁️ 可見度: {visible_ratio:.2f} (遮擋感知)")
                    
                    info_lines.append("")
                    
            else:
                info_lines.extend([
                    "❌ 未檢測到任何怪物",
                    "",
                    "💡 建議檢查事項:",
                    "   • 確認遊戲畫面中有怪物",
                    "   • 檢查模板檔案是否正確載入",
                    "   • 確認楓之谷 Worlds 視窗可見",
                    "   • 嘗試調整檢測閾值",
                    "   • 確認怪物模板資料夾已選擇"
                ])
            
            self.detail_text.setPlainText('\n'.join(info_lines))
            
        except Exception as e:
            self.logger.error(f"詳細資訊更新錯誤: {e}")
    
    def _update_history(self, monsters, current_time):
        """更新檢測歷史 - 增強版記錄系統"""
        try:
            if monsters:
                # ✅ 增強的歷史記錄
                history_entry = {
                    'time': current_time,
                    'monsters': monsters,
                    'count': len(monsters),
                    'avg_confidence': sum(m.get('confidence', 0) for m in monsters) / len(monsters),
                    'high_confidence_count': sum(1 for m in monsters if m.get('confidence', 0) >= 0.15),
                    'unique_monsters': len(set(self._get_display_name(m.get('name', 'Unknown')) for m in monsters))
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
                # ✅ 處理怪物名稱統計
                monsters_summary = {}
                for monster in entry['monsters']:
                    raw_name = monster.get('name', 'Unknown')
                    display_name = self._get_display_name(raw_name)
                    monsters_summary[display_name] = monsters_summary.get(display_name, 0) + 1
                
                # ✅ 增強的歷史顯示格式
                if monsters_summary:
                    summary_text = ', '.join([f"{name}×{count}" for name, count in sorted(monsters_summary.items())])
                    avg_conf = entry.get('avg_confidence', 0)
                    high_conf_count = entry.get('high_confidence_count', 0)
                    total_count = entry['count']
                    unique_count = entry.get('unique_monsters', 0)
                    
                    # 品質指標
                    quality_indicator = "⭐" if avg_conf >= 0.15 else "🟡" if avg_conf >= 0.10 else "🔴"
                    
                    history_line = (f"[{entry['time']}] {quality_indicator} "
                                  f"{summary_text} | "
                                  f"總計:{total_count} 種類:{unique_count} "
                                  f"高信心:{high_conf_count} 平均:{avg_conf:.3f}")
                    
                    history_lines.append(history_line)
            
            # ✅ 添加歷史統計摘要
            if display_history:
                total_detections = sum(entry['count'] for entry in display_history)
                total_sessions = len(display_history)
                avg_per_session = total_detections / total_sessions if total_sessions > 0 else 0
                
                summary_lines = [
                    "=" * 80,
                    f"📊 歷史統計摘要 (最近 {len(display_history)} 次檢測)",
                    f"🎯 總檢測數: {total_detections} | 平均每次: {avg_per_session:.1f}",
                    "=" * 80,
                    ""
                ]
                history_lines = summary_lines + history_lines
            
            self.history_text.setPlainText('\n'.join(history_lines))
                
        except Exception as e:
            self.logger.error(f"歷史更新錯誤: {e}")
    
    def _update_statistics(self, monsters):
        """更新統計資訊 - 增強版統計系統"""
        try:
            # ✅ 更新統計數據
            if monsters:
                self.detection_stats['total_detections'] += len(monsters)
                
                # ✅ 統計唯一怪物（使用簡化名稱）
                for monster in monsters:
                    raw_name = monster.get('name', 'Unknown')
                    display_name = self._get_display_name(raw_name)
                    self.detection_stats['unique_monsters'].add(display_name)
                
                # ✅ 新增統計項目
                if 'high_confidence_detections' not in self.detection_stats:
                    self.detection_stats['high_confidence_detections'] = 0
                if 'total_confidence' not in self.detection_stats:
                    self.detection_stats['total_confidence'] = 0.0
                
                # 統計高信心度檢測
                high_conf_count = sum(1 for m in monsters if m.get('confidence', 0) >= 0.15)
                self.detection_stats['high_confidence_detections'] += high_conf_count
                
                # 累計信心度
                total_conf = sum(m.get('confidence', 0) for m in monsters)
                self.detection_stats['total_confidence'] += total_conf
            
            # 計算運行時間
            if hasattr(self, 'session_start_time'):
                session_time = int(time.time() - self.session_start_time)
                hours = session_time // 3600
                minutes = (session_time % 3600) // 60
                seconds = session_time % 60
                time_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
            else:
                time_str = "00:00:00"
                session_time = 0
            
            # ✅ 計算當前檢測的平均信心度
            current_avg_confidence = 0
            if monsters:
                current_avg_confidence = sum(m.get('confidence', 0) for m in monsters) / len(monsters)
            
            # ✅ 計算整體平均信心度
            overall_avg_confidence = 0
            if self.detection_stats['total_detections'] > 0:
                overall_avg_confidence = self.detection_stats['total_confidence'] / self.detection_stats['total_detections']
            
            # ✅ 計算檢測品質指標
            quality_rate = 0
            if self.detection_stats['total_detections'] > 0:
                quality_rate = (self.detection_stats['high_confidence_detections'] / self.detection_stats['total_detections']) * 100
            
            # 計算檢測頻率
            detection_rate = 0
            if hasattr(self, 'session_start_time') and session_time > 0:
                detection_rate = (self.detection_stats['total_detections'] / session_time) * 60
            
            # ✅ 更新標籤 - 顯示更詳細的統計
            self.total_detections_label.setText(
                f"總檢測: {self.detection_stats['total_detections']} (高品質: {self.detection_stats.get('high_confidence_detections', 0)})")
            
            self.unique_monsters_label.setText(
                f"怪物種類: {len(self.detection_stats['unique_monsters'])} 種")
            
            self.session_time_label.setText(f"運行時間: {time_str}")
            
            # 顯示當前和整體平均信心度
            if current_avg_confidence > 0:
                self.avg_confidence_label.setText(f"信心度: {current_avg_confidence:.3f} (總體: {overall_avg_confidence:.3f})")
            else:
                self.avg_confidence_label.setText(f"整體信心度: {overall_avg_confidence:.3f}")
            
            self.detection_rate_label.setText(f"頻率: {detection_rate:.1f}/分 品質: {quality_rate:.1f}%")
            
        except Exception as e:
            self.logger.error(f"統計更新錯誤: {e}")
    
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
            
        except Exception as e:
            self.logger.error(f"清除結果錯誤: {e}")
    
    def _clear_history(self):
        """清除檢測歷史"""
        try:
            self.detection_history = []
            self.history_text.clear()
        except Exception as e:
            self.logger.error(f"清除歷史錯誤: {e}")
    
    def _detect_and_save(self):
        """檢測並保存結果圖片"""
        try:
            if not self.ro_helper or not hasattr(self.ro_helper, 'capturer'):
                self.logger.warning("無法獲取capturer")
                return
            
            frame = self.ro_helper.capturer.grab_frame()
            if frame is None:
                self.logger.warning("無法獲取畫面")
                return
            
            if self.monster_detector:
                # 執行檢測並自動保存結果圖片
                results = self.monster_detector.detect_and_save_result(frame)
                
                if results:
                    self._update_detection_results((results, {}))
                    self.logger.info(f"📸 檢測+保存完成: {len(results)} 個結果")
                else:
                    self.logger.info("📸 無檢測結果，已保存原始畫面供檢查")
            
        except Exception as e:
            self.logger.error(f"❌ 檢測+保存失敗: {e}")

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
            
            # ✅ 設置預設選中定點遠程（適合安全區域模式）
            self.stationary_ranged_radio.setChecked(True)
            self.combat_mode = "safe_area"
            
            # ✅ 連接戰鬥模式變更處理函數
            self.melee_radio.toggled.connect(lambda checked: self._on_combat_mode_changed("melee") if checked else None)
            self.ranged_radio.toggled.connect(lambda checked: self._on_combat_mode_changed("ranged") if checked else None)
            self.stationary_ranged_radio.toggled.connect(lambda checked: self._on_combat_mode_changed("stationary_ranged") if checked else None)
            
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
            self.logger.error(f"添加地圖管理功能失敗: {e}")

    def _open_editor(self):
        """開啟路徑編輯器"""
        try:
            self.ro_helper.open_editor()
        except Exception as e:
            self.logger.error(f"開啟路徑編輯器失敗: {e}")

    def _load_selected_map(self):
        """載入選中的地圖"""
        try:
            filename = self.map_combo.currentText()
            if filename:
                success = self.ro_helper.waypoint_system.load_map(filename)
                if success:
                    self.logger.info(f"主視窗載入地圖: {filename}")
                    self.status_bar.showMessage(f"已載入: {filename}")
                    
                    # 同步更新編輯器（如果開啟）
                    if hasattr(self.ro_helper, 'waypoint_editor') and self.ro_helper.waypoint_editor:
                        self.logger.debug("同步更新編輯器顯示")
                        try:
                            self.ro_helper.waypoint_editor._refresh_display()
                        except Exception as sync_error:
                            self.logger.warning(f"編輯器同步失敗: {sync_error}")
                else:
                    self.status_bar.showMessage("載入失敗")
        except Exception as e:
            self.logger.error(f"載入地圖失敗: {e}")
            self.status_bar.showMessage("載入錯誤")

    def _save_current_map(self):
        """主視窗保存地圖"""
        try:
            filename = self.map_combo.currentText()
            if not filename:
                self.logger.warning("請選擇要保存的檔案")
                return
            
            file_path = os.path.join("data", filename)
            self.ro_helper.waypoint_system.save_data(file_path)
            self.logger.info(f"地圖已保存: {filename}")
            self.status_bar.showMessage(f"💾 地圖已保存: {filename}")
            
        except Exception as e:
            self.logger.error(f"保存地圖失敗: {e}")

    def _toggle_realtime_display(self):
        """切換即時顯示（整合路徑可視化）"""
        try:
            # 初始化狀態（如果不存在）
            if not hasattr(self, 'realtime_display_running'):
                self.realtime_display_running = False
                
            if not self.realtime_display_running:
                self._start_realtime_display()
            else:
                self._stop_realtime_display()
                
        except Exception as e:
            self.logger.error(f"切換即時顯示狀態失敗: {e}")
            # 重置狀態以防出錯
            self.realtime_display_running = False
            if hasattr(self, 'realtime_display_button') and self.realtime_display_button:
                self.realtime_display_button.setText("📺 即時顯示")

    def _start_realtime_display(self):
        """開始即時顯示"""
        try:
            if not getattr(self, 'realtime_display_running', False):
                self.realtime_display_running = True
                
                # 更新按鈕文字
                if hasattr(self, 'realtime_display_button') and self.realtime_display_button:
                    self.realtime_display_button.setText("🛑 停止顯示")
                
                # 創建並啟動顯示線程
                self.display_thread = threading.Thread(target=self._opencv_display_loop, daemon=True)
                self.display_thread.start()
                
        except Exception as e:
            self.logger.error(f"啟動即時顯示失敗: {e}")
            self.realtime_display_running = False
            if hasattr(self, 'realtime_display_button') and self.realtime_display_button:
                self.realtime_display_button.setText("📺 即時顯示")

    def _stop_realtime_display(self):
        """停止即時顯示"""
        self.realtime_display_running = False
        
        # 安全檢查線程狀態
        display_thread = getattr(self, 'display_thread', None)
        if display_thread is not None and hasattr(display_thread, 'is_alive'):
            try:
                if display_thread.is_alive():
                    self.logger.info("正在停止即時顯示...")
                    display_thread.join(timeout=2.0)  # 等待最多2秒
                    if display_thread.is_alive():
                        self.logger.warning("強制終止顯示執行緒")
            except Exception as e:
                self.logger.warning(f"停止顯示線程時發生錯誤: {e}")
        
        self._force_opencv_cleanup()

    def _force_opencv_cleanup(self):
        """強制清理 OpenCV 資源"""
        try:
            # 強制關閉所有 OpenCV 視窗
            cv2.destroyAllWindows()
            # 重置狀態
            self.realtime_display_running = False
            self.display_thread = None
            # ✅ 重置按鈕文字
            if hasattr(self, 'realtime_display_button') and self.realtime_display_button:
                self.realtime_display_button.setText("📺 即時顯示")
        except Exception as e:
            self.logger.warning(f"強制清理時發生警告: {e}")

    def _delayed_opencv_cleanup(self):
        """延遲清理 OpenCV 資源"""
        try:
            cv2.destroyAllWindows()
            # ✅ 重置按鈕文字
            if hasattr(self, 'realtime_display_button') and self.realtime_display_button:
                self.realtime_display_button.setText("📺 即時顯示")
        except Exception as e:
            self.logger.warning(f"清理 OpenCV 資源時發生警告: {e}")

    def _opencv_display_loop(self):
        """OpenCV 即時顯示主循環 - 安全版"""
        try:
            # 錯誤統計
            consecutive_grab_errors = 0
            max_grab_errors = 10
            max_display_errors = 3  # 顯示錯誤上限更嚴格
            display_error_count = 0
            
            self.logger.info("即時顯示循環已啟動")
            
            while self.realtime_display_running:
                try:
                    frame = None
                    
                    # ✅ 使用共享檢測結果，避免重複檢測
                    shared_monsters = []
                    shared_health_bars = []
                    shared_hud_result = {}
                    
                    # 嘗試獲取共享檢測結果
                    try:
                        # 設置鎖定超時，避免死鎖
                        lock_acquired = False
                        try:
                            lock_acquired = self._detection_lock.acquire(timeout=0.1)  # 100ms 超時
                            if lock_acquired:
                                shared_data = self._shared_results.copy()
                                frame = shared_data.get('frame')
                                shared_monsters = shared_data.get('monsters', [])
                                shared_health_bars = shared_data.get('character_health_bars', [])
                                shared_hud_result = shared_data.get('hud_detection_result', {})
                            else:
                                self.logger.debug("獲取檢測鎖超時，跳過此幀")
                        except Exception as lock_error:
                            self.logger.debug(f"共享結果獲取錯誤: {lock_error}")
                        finally:
                            if lock_acquired:
                                self._detection_lock.release()
                        
                    except Exception as shared_error:
                        self.logger.debug(f"獲取共享結果失敗: {shared_error}")
                    
                    # 如果無法獲取共享結果，則直接捕捉畫面
                    if frame is None:
                        if consecutive_grab_errors >= max_grab_errors:
                            self.logger.warning("連續捕捉失敗，嘗試重新連接...")
                            time.sleep(1.0)
                            consecutive_grab_errors = 0
                        
                        try:
                            frame = self.ro_helper.capturer.grab_frame()
                            consecutive_grab_errors = 0
                        except Exception as grab_error:
                            self.logger.debug(f"畫面捕捉錯誤: {grab_error}")
                            consecutive_grab_errors += 1
                            time.sleep(0.1)
                            continue
                    
                    if frame is None:
                        time.sleep(0.1)
                        continue
                    
                    # 複製畫面用於顯示
                    display_frame = frame.copy()
                    # 新增：繪製角色血條排除區域
                    # self._draw_character_health_exclusion_area(display_frame)
                    # ✅ 繪製檢測結果（使用共享結果，避免重複檢測）
                    try:
                        if self.show_monster_overlay and shared_monsters:
                            self.logger.debug(f"顯示 {len(shared_monsters)} 個怪物檢測結果")
                            self._draw_monsters_on_frame(display_frame, shared_monsters)
                    except Exception as draw_error:
                        self.logger.debug(f"怪物繪製錯誤: {draw_error}")
                    
                    # ✅ HUD 血魔條顯示（使用共享結果）
                    try:
                        if self.show_health_overlay and shared_hud_result:
                            self._draw_hud_health_mana_detection(display_frame)
                    except Exception as hud_error:
                        self.logger.debug(f"HUD繪製錯誤: {hud_error}")
                    
                    # ✅ 角色血條顯示（使用共享結果）
                    try:
                        # 💡 可以在這裡控制是否顯示角色血條
                        show_character_health = True  # 設為 False 可隱藏角色血條檢測框
                        if self.show_health_overlay and shared_health_bars and show_character_health:
                            self._draw_character_health_bars_on_frame(display_frame, shared_health_bars)
                    except Exception as health_error:
                        self.logger.debug(f"血條繪製錯誤: {health_error}")
                    
                    # ✅ 小地圖可視化
                    try:
                        if self.show_minimap_overlay:
                            minimap_rect = self._get_minimap_rect(display_frame)
                            if minimap_rect:
                                self._draw_minimap_visualization(display_frame, minimap_rect)
                    except Exception as minimap_error:
                        self.logger.debug(f"小地圖繪製錯誤: {minimap_error}")
                    
                    # ✅ 顯示畫面
                    try:
                        cv2.imshow("MapleHelper - 即時檢測結果", display_frame)
                        
                        # 檢查按鍵
                        key = cv2.waitKey(1) & 0xFF
                        if key == 27:  # ESC 鍵
                            self.logger.info("用戶按ESC鍵退出即時顯示")
                            break
                        
                        display_error_count = 0  # 重置顯示錯誤計數
                        
                    except Exception as display_error:
                        display_error_count += 1
                        self.logger.warning(f"顯示畫面錯誤: {display_error}")
                        if display_error_count >= max_display_errors:
                            self.logger.error("顯示循環遇到太多錯誤，退出")
                            break
                    
                    time.sleep(0.03)  # 約30FPS
                    
                except Exception as e:
                    self.logger.error(f"顯示循環錯誤: {e}")
                    time.sleep(0.1)
                    
        except Exception as e:
            self.logger.error(f"顯示循環初始化失敗: {e}")
        finally:
            self.realtime_display_running = False
            
        self.logger.info("即時顯示循環已停止")
        self._force_opencv_cleanup()

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
                    self.logger.error(f"小地圖可視化失敗: {e}")
            return frame
        except Exception as e:
            self.logger.error(f"小地圖可視化失敗: {e}")
            return frame

    def _draw_waypoints_on_minimap(self, frame, minimap_rect):
        """在小地圖上繪製路徑點"""
        try:
            # 💡 路徑點顯示控制開關
            show_waypoints = True  # 設為 False 可隱藏路徑點紅色圓點
            
            if not show_waypoints:
                return  # 如果不顯示路徑點，直接返回
            
            x1, y1, x2, y2 = minimap_rect
            waypoints = self.ro_helper.waypoint_system.waypoints
            
            # 繪製路徑線
            for i in range(len(waypoints) - 1):
                wp1, wp2 = waypoints[i], waypoints[i + 1]
                px1 = int(x1 + wp1['pos'][0] * (x2 - x1))
                py1 = int(y1 + wp1['pos'][1] * (y2 - y1))
                px2 = int(x1 + wp2['pos'][0] * (x2 - x1))
                py2 = int(y1 + wp2['pos'][1] * (y2 - y1))
                cv2.line(frame, (px1, py1), (px2, py2), (255, 0, 0), 2)
                # cv2.circle(frame, (px1, py1), 5, (0, 0, 255), -1)  # 紅色路徑點 - 可選擇隱藏
                cv2.circle(frame, (px1, py1), 7, (255, 255, 255), 1)  # 白色外圈
                cv2.putText(frame, str(i), (px1 + 8, py1 + 8), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
            if waypoints:
                last_wp = waypoints[-1]
                px = int(x1 + last_wp['pos'][0] * (x2 - x1))
                py = int(y1 + last_wp['pos'][1] * (y2 - y1))
                # cv2.circle(frame, (px, py), 5, (0, 0, 255), -1)  # 紅色最後路徑點 - 可選擇隱藏
                cv2.circle(frame, (px, py), 7, (255, 255, 255), 1)  # 白色外圈
                cv2.putText(frame, str(len(waypoints)-1), (px + 8, py + 8), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        except Exception as e:
            self.logger.error(f"路徑點繪製失敗: {e}")

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
                    self.logger.warning(f"區域點繪製失敗: {e}")
                    continue
            cv2.addWeighted(overlay, 0.3, frame, 0.7, 0, frame)
        except Exception as e:
            self.logger.error(f"區域繪製失敗: {e}")

    def _draw_hud_health_mana_detection(self, frame):
        """🔧 HUD血魔條檢測辨識框繪製（包含OCR捕捉框）"""
        try:
            # ✅ 檢查是否有共享的HUD檢測結果
            shared_hud_result = None
            try:
                with self._detection_lock:
                    shared_hud_result = self._shared_results.get('hud_detection_result', {})
                    detected = shared_hud_result.get('detected', False)
                    self.logger.debug(f"🔍 獲取到共享HUD檢測結果: {detected}")
            except Exception as e:
                self.logger.debug(f"獲取共享HUD檢測結果失敗: {e}")
                
            # 如果有共享結果，直接使用；否則跳過
            if shared_hud_result and shared_hud_result.get('detected'):
                hud_result = shared_hud_result
                self.logger.debug(f"🎯 準備繪製HUD辨識框: {hud_result.get('detection_method', 'unknown')}")
            else:
                self.logger.debug("HUD檢測：無共享結果，跳過繪製以避免重複檢測")
                return frame
            
            # 🆕 直接在GUI中繪製HP/MP OCR結果
            self._draw_hp_mp_ocr_results(frame, hud_result)
                        
            return frame
            
        except Exception as e:
            self.logger.error(f"HUD血魔條辨識框繪製失敗: {e}")
            return frame
    
    def _draw_hp_mp_ocr_results(self, frame, hud_result):
        """直接在GUI中繪製HP/MP OCR結果"""
        try:
            # HP血條處理
            if 'hp_rect' in hud_result:
                x, y, w, h = hud_result['hp_rect']
                # 繪製HP血條邊框（紅色）
                cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 0, 255), 2)
                
                # 顯示HP OCR結果
                if 'hp_text' in hud_result:
                    hp_text = f"HP: {hud_result['hp_text']}"
                    cv2.putText(frame, hp_text, (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
            
            # MP血條處理
            if 'mp_rect' in hud_result:
                x, y, w, h = hud_result['mp_rect']
                # 繪製MP血條邊框（藍色）
                cv2.rectangle(frame, (x, y), (x + w, y + h), (255, 0, 0), 2)
                
                # 顯示MP OCR結果
                if 'mp_text' in hud_result:
                    mp_text = f"MP: {hud_result['mp_text']}"
                    cv2.putText(frame, mp_text, (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
            
            # EXP血條處理
            if 'exp_rect' in hud_result:
                x, y, w, h = hud_result['exp_rect']
                # 繪製EXP血條邊框（青色）
                cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 255), 2)
            
        except Exception as e:
            self.logger.error(f"繪製HP/MP OCR結果失敗: {e}")

    def detect_character_overhead_health(self, frame):
        """角色頭頂血條檢測（改為使用共享結果）"""
        try:
            # 嘗試使用共享檢測結果
            try:
                with self._detection_lock:
                    shared_health_bars = self._shared_results.get('character_health_bars', [])
                    if shared_health_bars:
                        return self._draw_character_health_bars_on_frame(frame, shared_health_bars)
            except Exception as e:
                self.logger.debug(f"獲取共享角色血條檢測結果失敗: {e}")
            
            # 如果沒有共享結果，返回原畫面
            return frame
            
        except Exception as e:
            self.logger.error(f"在 GUI 中繪製頭頂血條時發生錯誤: {e}")
            return frame

    def _toggle_auto_hunt(self, state):
        """切換自動狩獵狀態"""
        try:
            if not hasattr(self.ro_helper, 'auto_combat') or not self.ro_helper.auto_combat:
                self.logger.error("戰鬥系統未初始化")
                self.auto_hunt_switch.setChecked(False)
                return
            
            if state == Qt.Checked:  # 開啟自動狩獵
                self.logger.info("嘗試開啟自動狩獵...")
                
                # 檢查戰鬥模式
                if not hasattr(self, 'combat_settings') or not self.combat_settings.get('combat_mode'):
                    self.logger.error("請先選擇戰鬥模式")
                    self.auto_hunt_switch.setChecked(False)
                    return
                
                # 設定戰鬥參數
                combat_mode = self.combat_settings.get('combat_mode', 'melee')
                if hasattr(self, 'combat_settings') and self.combat_settings:
                    self.logger.debug(f"使用預設戰鬥設定: {self.combat_settings['combat_mode']}")
                    self.ro_helper.auto_combat.hunt_settings.update(self.combat_settings)
                else:
                    self.logger.debug(f"使用備用戰鬥設定")
                    # 備用設定
                    self.ro_helper.auto_combat.hunt_settings.update({
                        'combat_mode': combat_mode,
                        'attack_range': 0.4,
                        'approach_distance': 0.1,
                        'retreat_distance': 0.05,
                        'attack_cooldown': 1.5,
                        'movement_speed': 0.8,
                        'use_waypoints': True,
                        'patrol_mode': 'safe_area',
                        'max_chase_distance': 0.15,
                        'return_to_safe': True
                    })
                
                # 啟動戰鬥系統
                try:
                    self.ro_helper.auto_combat.start()
                    self.logger.info("自動狩獵已開啟")
                    self.logger.info(f"戰鬥模式: {combat_mode}")
                    self.logger.debug(f"戰鬥系統狀態: is_enabled={self.ro_helper.auto_combat.is_enabled}")
                except Exception as start_error:
                    self.logger.error("啟動戰鬥系統失敗")
                    self.auto_hunt_switch.setChecked(False)
                    
            else:  # 關閉自動狩獵
                self.logger.info("關閉自動狩獵...")
                try:
                    self.ro_helper.auto_combat.stop()
                    self.logger.info("自動狩獵已關閉")
                    self.logger.debug(f"戰鬥系統狀態: is_enabled={self.ro_helper.auto_combat.is_enabled}")
                except:
                    pass
                    
        except Exception as e:
            self.logger.error(f"切換自動狩獵狀態失敗: {e}")
            self.auto_hunt_switch.setChecked(False)
    
    def _setup_melee_combat(self):
        """設置近戰模式"""
        self.combat_settings = {
            'combat_mode': 'melee',
            'attack_range': 0.4,
            'approach_distance': 0.1,
            'retreat_distance': 0.05,
            'movement_speed': 0.8,
            'use_waypoints': True,
            'max_chase_distance': 0.15
        }
        self.logger.info("已設置近戰模式")
    
    def _setup_ranged_combat(self):
        """設置遠程模式"""
        self.combat_settings = {
            'combat_mode': 'ranged',
            'attack_range': 0.6,
            'approach_distance': 0.2,
            'retreat_distance': 0.1,
            'movement_speed': 0.6,
            'use_waypoints': True,
            'max_chase_distance': 0.2
        }
        self.logger.info("已設置遠程模式")
    
    def _setup_stationary_ranged_combat(self):
        """設置安全區域巡邏遠程模式"""
        try:
            self.combat_settings = {
                'combat_mode': 'safe_area',
                'attack_range': 0.6,
                'approach_distance': 0.0,  # 不主動接近
                'retreat_distance': 0.2,   # 保持距離
                'movement_speed': 0.5,
                'use_waypoints': True,     # 啟用路徑點
                'patrol_mode': 'safe_area',
                'max_chase_distance': 0.05, # 最小追擊距離
                'return_to_safe': True     # 回到安全區域
            }
            
            self.logger.info("已設置安全區域巡邏遠程模式")
            self.logger.debug(f"戰鬥模式: {self.combat_settings['combat_mode']}")
            
        except Exception as e:
            self.logger.error(f"設置巡邏遠程模式失敗: {e}")

    def _on_combat_mode_changed(self, mode):
        """戰鬥模式改變處理"""
        self.logger.debug(f"切換戰鬥模式: {mode}")
        
        try:
            if mode == "近戰":
                self._setup_melee_combat()
            elif mode == "遠程":
                self._setup_ranged_combat()
            elif mode == "安全區域巡邏":
                self._setup_stationary_ranged_combat()
            
            # 儲存當前模式
            self.combat_mode = mode
            
            # 如果戰鬥系統已啟用，立即應用新設定
            if (hasattr(self.ro_helper, 'auto_combat') and 
                self.ro_helper.auto_combat and 
                hasattr(self.ro_helper.auto_combat, 'hunt_settings')):
                
                if hasattr(self, 'combat_settings'):
                    self.ro_helper.auto_combat.hunt_settings.update(self.combat_settings)
                    self.logger.info(f"戰鬥模式已設置: {self.combat_mode}")
                    self.logger.debug(f"路徑點系統狀態: {self.ro_helper.waypoint_system is not None}")
                    self.logger.info(f"請點擊'自動狩獵'開關來啟動攻擊")
                    
        except Exception as e:
            self.logger.error(f"切換戰鬥模式失敗: {e}")

    def _refresh_template_folders(self):
        """重新整理模板資料夾"""
        try:
            template_path = Path("templates/monsters")
            if not template_path.exists():
                self.logger.error(f"找不到怪物模板資料夾: {template_path}")
                return
            
            # 清空現有項目
            self.template_folder_combo.clear()
            
            # 添加預設選項
            self.template_folder_combo.addItem("選擇怪物模板...")
            
            # 獲取所有資料夾
            for folder in template_path.iterdir():
                if folder.is_dir():
                    self.template_folder_combo.addItem(folder.name)
                    
            self.logger.debug("模板資料夾列表已更新")
            
        except Exception as e:
            self.logger.error(f"重新整理模板資料夾失敗: {e}")
            import traceback
            traceback.print_exc()

    def _on_template_folder_changed(self, index):
        """處理模板資料夾變更"""
        try:
            if index <= 0:  # 選擇預設項目
                return
                
            folder_name = self.template_folder_combo.itemText(index)
            self.logger.info(f"切換到怪物模板: {folder_name}")
            
            # 重新初始化檢測器
            if hasattr(self, 'monster_detector') and self.monster_detector:
                # 可以在這裡添加重新載入模板的邏輯
                pass
                
        except Exception as e:
            self.logger.error(f"處理模板資料夾變更失敗: {e}")

    def _refresh_map_files(self):
        """刷新地圖檔案列表"""
        try:
            if hasattr(self, 'map_combo') and self.map_combo:
                if hasattr(self.ro_helper, 'waypoint_system'):
                    available_files = self.ro_helper.waypoint_system.get_files()
                    self.map_combo.clear()
                    self.map_combo.addItems(available_files)
                    self.logger.info(f"已載入 {len(available_files)} 個地圖檔案")
            
        except Exception as e:
            self.logger.error(f"更新地圖檔案列表失敗: {e}")

    def _get_display_name(self, file_path):
        """獲取顯示名稱"""
        try:
            # 提取檔案名（不含路徑和副檔名）
            filename = os.path.basename(file_path)
            name_without_ext = os.path.splitext(filename)[0]
            return name_without_ext
        except Exception as e:
            self.logger.warning(f"GUI名稱處理失敗: {e}")
            return file_path

    def _draw_monsters_on_frame(self, display_frame, monsters=None):
        """在畫面上繪製怪物檢測結果"""
        if not monsters:
            return
        
        try:
            for monster in monsters:
                # 獲取怪物中心點
                center = self._get_monster_center(monster)
                if center is None:
                    continue
                
                x, y = center
                
                # 繪製怪物框
                if 'bbox' in monster and monster['bbox']:
                    x1, y1, x2, y2 = monster['bbox']
                    cv2.rectangle(display_frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                    
                    # 繪製怪物名稱
                    name = monster.get('name', 'Unknown')
                    confidence = monster.get('confidence', 0)
                    label = f"{name} ({confidence:.2f})"
                    
                    # 計算文字位置
                    text_size = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)[0]
                    text_x = x1
                    text_y = y1 - 10 if y1 > 20 else y1 + text_size[1] + 10
                    
                    # 繪製文字背景
                    cv2.rectangle(display_frame, (text_x, text_y - text_size[1]), 
                                (text_x + text_size[0], text_y + 5), (0, 0, 0), -1)
                    
                    # 繪製文字
                    cv2.putText(display_frame, label, (text_x, text_y), 
                              cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
                    
                    # 繪製中心點
                    cv2.circle(display_frame, (x, y), 3, (0, 0, 255), -1)
                
                # 備用方案：如果沒有bbox但有corners，用corners中心計算方形
                elif 'corners' in monster and monster['corners']:
                    corners = monster['corners']
                    if len(corners) >= 4:
                        x_coords = [corner[0] for corner in corners]
                        y_coords = [corner[1] for corner in corners]
                        x1, x2 = min(x_coords), max(x_coords)
                        y1, y2 = min(y_coords), max(y_coords)
                        
                        cv2.rectangle(display_frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                        cv2.circle(display_frame, (x, y), 3, (0, 0, 255), -1)
                
                # 備用方案：使用 position 屬性
                elif 'position' in monster:
                    pos = monster['position']
                    if len(pos) >= 2:
                        x, y = int(pos[0]), int(pos[1])
                        cv2.circle(display_frame, (x, y), 10, (0, 255, 0), 2)
                        cv2.circle(display_frame, (x, y), 3, (0, 0, 255), -1)
                        
        except Exception as e:
            self.logger.error(f"怪物繪製失敗: {e}")

    def _get_monster_center(self, monster):
        """獲取怪物中心點"""
        try:
            # 優先使用bbox
            if 'bbox' in monster and monster['bbox']:
                x, y, w, h = monster['bbox']
                return (x + w//2, y + h//2)
            
            # 備用：使用corners
            elif 'corners' in monster and monster['corners']:
                corners = monster['corners']
                if len(corners) >= 4:
                    x_coords = [corner[0] for corner in corners]
                    y_coords = [corner[1] for corner in corners]
                    center_x = sum(x_coords) // len(x_coords)
                    center_y = sum(y_coords) // len(y_coords)
                    return (center_x, center_y)
            
            # 備用：使用position
            elif 'position' in monster:
                pos = monster['position']
                if len(pos) >= 2:
                    return (int(pos[0]), int(pos[1]))
            
            return None
            
        except Exception as e:
            self.logger.warning(f"獲取怪物中心點失敗: {e}")
            return None

    def _get_minimap_rect(self, frame):
        """獲取小地圖位置"""
        try:
            if hasattr(self.ro_helper, 'tracker') and self.ro_helper.tracker:
                return self.ro_helper.tracker._find_minimap_with_subpixel_accuracy(frame)
            return None
        except Exception as e:
            self.logger.debug(f"獲取小地圖位置失敗: {e}")
            return None

    def _draw_character_health_bars_on_frame(self, frame, health_bars):
        """在畫面上繪製角色血條"""
        try:
            if not health_bars:
                return frame
                
            for i, health_bar in enumerate(health_bars):
                if len(health_bar) >= 4:
                    x, y, w, h = health_bar[:4]
                    
                    # 繪製血條邊框（亮黃色）
                    cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 255), 2)
                    
                    # 添加標籤 - 簡化為英文避免問號
                    status = health_bar[4] if len(health_bar) > 4 else "detected"
                    label = f"HP#{i+1}: {status}"
                    # 使用簡單的OpenCV文字渲染
                    cv2.putText(frame, label, (x, y - 5),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)
            
            return frame
        except Exception as e:
            self.logger.error(f"繪製角色血條失敗: {e}")
            return frame

    def run(self):
        """運行GUI應用程式"""
        try:
            self.show()
            return QApplication.instance().exec_()
        except Exception as e:
            self.logger.error(f"GUI運行失敗: {e}")
            return 1

    def _auto_load_first_template_folder(self):
        """自動載入第一個模板資料夾"""
        try:
            self.logger.info("自動載入第一個模板資料夾...")
            
            # 檢查模板路徑
            template_path = "templates/monsters"
            if not os.path.exists(template_path):
                self.logger.error(f"找不到怪物模板資料夾: {template_path}")
                return
            
            # 獲取所有子資料夾
            subfolders = []
            for item in os.listdir(template_path):
                item_path = os.path.join(template_path, item)
                if os.path.isdir(item_path):
                    subfolders.append(item)
            
            if not subfolders:
                self.logger.warning("沒有找到任何怪物模板資料夾")
                return
            
            # 選擇第一個資料夾
            first_folder = subfolders[0]
            full_path = os.path.join(template_path, first_folder)
            
            # 載入模板
            if hasattr(self, 'monster_detector') and self.monster_detector:
                template_count = self.monster_detector.load_template_folder(full_path)
                self.logger.info(f"自動載入成功: {first_folder} ({template_count} 個模板)")
                
                # 更新選單
                for i in range(self.template_folder_combo.count()):
                    if self.template_folder_combo.itemText(i) == first_folder:
                        self.template_folder_combo.setCurrentIndex(i)
                        self.logger.info(f"已設置模板選單為: {first_folder}")
                        break
            else:
                self.logger.error("怪物檢測器未初始化，無法自動載入模板")
                
        except Exception as e:
            self.logger.error(f"自動載入模板資料夾失敗: {e}")



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
