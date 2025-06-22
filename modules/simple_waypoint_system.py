# modules/simple_waypoint_system.py - PyQt5版本：添加障礙物標記功能

import json
import os
from typing import Dict, List, Optional, Tuple

from PyQt5.QtCore import QObject, pyqtSignal

from includes.grid_utils import GridUtils
from includes.config_utils import create_config_section
from includes.log_utils import get_logger
from includes.data_utils import get_data_manager

class SimpleWaypointSystem(QObject):
    """路徑點系統 - PyQt5版本：支援信號發射"""
    
    # ✅ PyQt5 信號定義
    waypoint_added = pyqtSignal(dict)  # 路徑點添加信號
    waypoint_removed = pyqtSignal(int)  # 路徑點移除信號
    waypoint_updated = pyqtSignal(int, dict)  # 路徑點更新信號
    obstacle_added = pyqtSignal(dict)  # 障礙物添加信號
    area_updated = pyqtSignal(dict)  # 區域更新信號
    map_loaded = pyqtSignal(str)  # 地圖載入信號
    map_saved = pyqtSignal(str)  # 地圖保存信號
    
    def __init__(self, config=None):
        super().__init__()  # ✅ PyQt5 QObject 初始化
        
        # ✅ 使用共用工具初始化
        self.logger = get_logger("SimpleWaypointSystem")
        self.data_manager = get_data_manager()
        
        # ✅ 使用 ConfigSection 簡化配置讀取
        if config:
            config_section = create_config_section(config, 'waypoint_system')
            self.tolerance = config_section.get_float('tolerance', 0.05)
            self.obstacle_size = config_section.get_list('obstacle_size', [0.05, 0.05])
            self.action_zone_size = config_section.get_list('action_zone_size', [0.03, 0.03])
            self.delete_threshold = config_section.get_float('delete_threshold', 0.05)
            self.area_mark_step = config_section.get_float('area_mark_step', 0.01)
        else:
            # 預設值
            self.tolerance = 0.05
            self.obstacle_size = [0.05, 0.05]
            self.action_zone_size = [0.03, 0.03]
            self.delete_threshold = 0.05
            self.area_mark_step = 0.01
        
        self.waypoints: List[Dict] = []
        # ✅ 新增：障礙物和特殊區域
        self.obstacles: List[Dict] = []
        self.special_zones: List[Dict] = []
        self.current_target_index = 0
        self.area_grid = {}  # 區域標記網格
        
        # ✅ 基於搜索結果[16]的障礙物類型定義
        self.obstacle_types = {
            'wall': {'name': '牆壁', 'color': 'red', 'passable': False},
            'water': {'name': '水域', 'color': 'blue', 'passable': False},
            'tree': {'name': '樹木', 'color': 'green', 'passable': False},
            'building': {'name': '建築物', 'color': 'gray', 'passable': False}
        }
        
        # ✅ 基於搜索結果[17]的特殊動作區域
        self.action_zones = {
            'rope': {'name': '繩索', 'color': 'brown', 'action': 'climb_rope'},
            'ladder': {'name': '階梯', 'color': 'yellow', 'action': 'climb_ladder'},
            'door': {'name': '門', 'color': 'purple', 'action': 'open_door'},
            'portal': {'name': '傳送點', 'color': 'cyan', 'action': 'use_portal'},
            'npc': {'name': 'NPC', 'color': 'orange', 'action': 'talk_npc'}
        }
        
        self._init_default_waypoints()
        
        # 初始化 A* 網格系統
        self.grid_utils = GridUtils()
        
        self.logger.init_success("路徑點系統")
        if config:
            self.logger.info(f"已從設定檔載入參數: tolerance={self.tolerance}")

    def add_point(self, position: Tuple[float, float], name: str = None) -> Dict:
        """添加路徑點"""
        waypoint_id = len(self.waypoints)
        waypoint = {
            'id': waypoint_id,
            'pos': position,
            'name': name or f'路徑點{waypoint_id}'
        }
        self.waypoints.append(waypoint)
        self.waypoint_added.emit(waypoint)
        self.logger.info(f"已添加路徑點: {waypoint}")
        return waypoint

    def remove_point(self, waypoint_id: int) -> bool:
        """移除路徑點"""
        for i, waypoint in enumerate(self.waypoints):
            if waypoint['id'] == waypoint_id:
                removed_waypoint = self.waypoints.pop(i)
                self.waypoint_removed.emit(waypoint_id)
                self.logger.info(f"已移除路徑點: {removed_waypoint}")
                return True
        return False

    def update_point(self, waypoint_id: int, **kwargs) -> bool:
        """更新路徑點"""
        for waypoint in self.waypoints:
            if waypoint['id'] == waypoint_id:
                waypoint.update(kwargs)
                self.waypoint_updated.emit(waypoint_id, waypoint)
                self.logger.info(f"已更新路徑點: {waypoint}")
                return True
        return False

    def add_obstacle(self, position: Tuple[float, float], obstacle_type: str, 
                    size: Tuple[float, float] = (0.05, 0.05)) -> Dict:
        """添加障礙物"""
        obstacle_id = len(self.obstacles)
        obstacle = {
            'id': obstacle_id,
            'pos': position,
            'type': obstacle_type,
            'size': size,
            'passable': False
        }
        self.obstacles.append(obstacle)
        self.obstacle_added.emit(obstacle)
        self.logger.info(f"已添加障礙物: {obstacle}")
        return obstacle

    def add_zone(self, position: Tuple[float, float], zone_type: str,
                       size: Tuple[float, float] = (0.03, 0.03)) -> Dict:
        """添加特殊區域"""
        zone_id = len(self.special_zones)
        zone = {
            'id': zone_id,
            'pos': position,
            'type': zone_type,
            'size': size
        }
        self.special_zones.append(zone)
        self.logger.info(f"已添加特殊區域: {zone}")
        return zone

    def check_path(self, from_pos: Tuple[float, float], 
                               to_pos: Tuple[float, float]) -> List[Dict]:
        """檢查路徑上的障礙物"""
        obstacles_on_path = []
        
        for obstacle in self.obstacles:
            if not obstacle.get('passable', False):
                if self._line_intersects_rect(from_pos, to_pos, 
                                            obstacle['pos'], obstacle['size']):
                    obstacles_on_path.append(obstacle)
        
        return obstacles_on_path

    def get_action(self, position: Tuple[float, float]) -> Optional[str]:
        """獲取位置對應的動作"""
        for zone in self.special_zones:
            if self._point_in_rect(position, zone['pos'], zone['size']):
                return zone['type']
        return None

    def get_movement(self, current_pos: Tuple[float, float]) -> Dict:
        """獲取移動建議（考慮障礙物）"""
        if not self.waypoints:
            return {'direction': 'none', 'reason': 'no_waypoints'}
        
        # 獲取下一個目標
        next_waypoint = self.get_next_waypoint(current_pos)
        if not next_waypoint:
            return {'direction': 'none', 'reason': 'no_next_waypoint'}
        
        target_pos = next_waypoint['pos']
        
        # 檢查路徑上的障礙物
        obstacles = self.check_path(current_pos, target_pos)
        
        if obstacles:
            # 有障礙物，尋找替代路徑
            alternative_direction = self._find_alternative_path(current_pos, target_pos, obstacles)
            return {
                'direction': alternative_direction,
                'reason': 'obstacle_detected',
                'obstacles': obstacles,
                'target': target_pos
            }
        else:
            # 無障礙物，直接移動
            dx = target_pos[0] - current_pos[0]
            dy = target_pos[1] - current_pos[1]
            
            if abs(dx) > abs(dy):
                direction = 'right' if dx > 0 else 'left'
            else:
                direction = 'down' if dy > 0 else 'up'
            
            return {
                'direction': direction,
                'reason': 'direct_path',
                'target': target_pos
            }

    def save_data(self, filename: str = "data/map_data.json"):
        """保存地圖數據 - 包含 A* 網格信息"""
        try:
            data = {
                'waypoints': self.waypoints,
                'obstacles': self.obstacles,
                'special_zones': self.special_zones,
                'area_grid': self.area_grid
            }
            
            # ✅ 使用 DataManager 保存
            success = self.data_manager.save_json(filename, data)
            
            if success:
                self.logger.info(f"地圖數據已保存: {filename}")
                self.map_saved.emit(filename)
            else:
                self.logger.error("保存地圖數據失敗")
            
            return success
            
        except Exception as e:
            self.logger.error("保存地圖數據失敗", e)
            return False

    def load_data(self, file_path=None):
        """載入地圖數據 - 重建 A* 網格"""
        try:
            if file_path is None:
                file_path = self.get_initial_map_file()
            if not file_path:
                self.logger.error("找不到地圖文件")
                return False
                
            # ✅ 使用 DataManager 載入
            data = self.data_manager.load_json(file_path)
            if not data:
                self.logger.error("載入地圖數據失敗")
                return False
                
            # 清除現有數據
            self.waypoints.clear()
            self.obstacles.clear()
            self.special_zones.clear()
            self.area_grid.clear()
            self.grid_utils.clear()
            
            # 載入路徑點
            for waypoint in data.get('waypoints', []):
                self.waypoints.append(waypoint)
                
            # 載入障礙物
            for obstacle in data.get('obstacles', []):
                self.obstacles.append(obstacle)
                if not obstacle.get('passable', False):
                    self.grid_utils.add_obstacle(
                        obstacle['pos'], 
                        obstacle.get('size', (0.05, 0.05))
                    )
                    
            # 載入特殊區域
            for zone in data.get('special_zones', []):
                self.special_zones.append(zone)
                self.grid_utils.add_special_zone(
                    zone['pos'],
                    zone['type'],
                    zone.get('size', (0.03, 0.03))
                )
                
            # 載入區域網格
            self.area_grid = data.get('area_grid', {})
            self.logger.info(f"載入的區域網格: {self.area_grid}")
            
            # 處理區域網格中的特殊區域
            for key, area_type in self.area_grid.items():
                if isinstance(key, str) and ',' in key:
                    x_str, y_str = key.split(',')
                    fx, fy = float(x_str), float(y_str)
                elif isinstance(key, tuple):
                    fx, fy = key
                else:
                    continue
                
                if area_type == "forbidden":
                    # 將禁止區域同步為障礙物
                    self.grid_utils.add_obstacle((fx, fy), (0.02, 0.02))
                    self.logger.info(f"同步禁止區域為障礙物: ({fx}, {fy})")
                elif area_type == "rope":
                    # 將繩索區域添加到特殊區域
                    self.add_zone((fx, fy), "rope", (0.02, 0.02))
                    self.logger.info(f"同步繩索區域: ({fx}, {fy})")
            
            self.logger.info(f"地圖數據已載入: {file_path}")
            self.map_loaded.emit(file_path)
            return True
            
        except Exception as e:
            self.logger.error("載入地圖數據失敗", e)
            return False

    def get_next_waypoint(self, current_pos: Tuple[float, float]) -> Optional[Dict]:
        """獲取下一個路徑點"""
        if not self.waypoints:
            return None
        
        if self.current_target_index >= len(self.waypoints):
            self.current_target_index = 0
        
        return self.waypoints[self.current_target_index]

    def _init_default_waypoints(self):
        """初始化預設路徑點"""
        # 使用相對座標(0.0-1.0)
        self.waypoints = [
            {'id': 0, 'pos': (0.3, 0.3), 'name': '起點'},
            {'id': 1, 'pos': (0.7, 0.3), 'name': '右上'},
            {'id': 2, 'pos': (0.7, 0.7), 'name': '右下'},
            {'id': 3, 'pos': (0.3, 0.7), 'name': '左下'}
        ]

    def manage_area(self, position, area_type, operation="add"):
        """統一的區域管理介面"""
        if operation == "add":
            self.area_grid[position] = area_type
        elif operation == "remove":
            self.area_grid.pop(position, None)
        elif operation == "get":
            return self.area_grid.get(position, None)
        elif operation == "check":
            return position in self.area_grid
        
        return True

    def list_files(self):
        """✅ 基於搜索結果[18]的數據目錄檢查"""
        try:
            # ✅ 使用 DataManager 掃描檔案
            data_dir = self.data_manager.get_data_dir()
            self.logger.info(f"檢查數據目錄: {data_dir}")
            
            if not self.data_manager.data_dir_exists():
                self.logger.error("data資料夾不存在")
                return
            
            # 列出所有JSON檔案
            json_files = self.data_manager.list_json_files()
            all_files = self.data_manager.list_all_files()
            
            self.logger.info(f"data資料夾內容:")
            self.logger.info(f"  所有檔案: {all_files}")
            self.logger.info(f"  JSON檔案: {json_files}")
            
            # 嘗試載入每個JSON檔案
            for json_file in json_files:
                self._try_load_json_file(os.path.join(data_dir, json_file))
                
        except Exception as e:
            self.logger.error("檢查數據目錄失敗", e)

    def try_load_file(self, file_path):
        """嘗試載入JSON檔案並顯示內容"""
        try:
            # ✅ 使用 DataManager 載入
            data = self.data_manager.load_json(file_path)
            if not data:
                self.logger.error(f"{os.path.basename(file_path)}: 載入失敗")
                return
            
            waypoints_count = len(data.get('waypoints', []))
            obstacles_count = len(data.get('obstacles', []))
            area_grid_count = len(data.get('area_grid', {}))
            
            self.logger.info(f"{os.path.basename(file_path)}: {waypoints_count}路徑點, {obstacles_count}障礙物, {area_grid_count}區域")
            
        except Exception as e:
            self.logger.error(f"{os.path.basename(file_path)}: 載入失敗", e)

    def get_files(self):
        """獲取所有可用的地圖檔案列表"""
        try:
            # ✅ 使用 DataManager 掃描
            data_dir = self.data_manager.get_data_dir()
            self.logger.info(f"掃描目錄: {data_dir}")
            
            # 確保 data 目錄存在
            if not self.data_manager.data_dir_exists():
                self.logger.warning("data 目錄不存在，嘗試建立...")
                self.data_manager.ensure_data_dir()
                return []
            
            # 掃描所有 JSON 檔案
            json_files = self.data_manager.list_json_files()
            
            # 按檔案名稱排序
            json_files.sort()
            
            self.logger.info(f"掃描到 {len(json_files)} 個地圖檔案")
            if json_files:
                self.logger.info(f"檔案列表: {json_files}")
            
            return json_files
            
        except Exception as e:
            self.logger.error("獲取地圖檔案列表失敗", e)
            return []

    def load_map(self, filename):
        """載入特定地圖檔案"""
        if not filename.endswith('.json'):
            filename += '.json'
        
        # ✅ 使用 DataManager 載入並處理數據
        data = self.data_manager.load_json(filename)
        if data:
            # 清除現有數據
            self.waypoints.clear()
            self.obstacles.clear()
            self.special_zones.clear()
            self.area_grid.clear()
            self.grid_utils.clear()
            
            # 載入路徑點
            for waypoint in data.get('waypoints', []):
                self.waypoints.append(waypoint)
                
            # 載入障礙物
            for obstacle in data.get('obstacles', []):
                self.obstacles.append(obstacle)
                if not obstacle.get('passable', False):
                    self.grid_utils.add_obstacle(
                        obstacle['pos'], 
                        obstacle.get('size', (0.05, 0.05))
                    )
                    
            # 載入特殊區域
            for zone in data.get('special_zones', []):
                self.special_zones.append(zone)
                self.grid_utils.add_special_zone(
                    zone['pos'],
                    zone['type'],
                    zone.get('size', (0.03, 0.03))
                )
                
            # 載入區域網格
            self.area_grid = data.get('area_grid', {})
            
            self.logger.info(f"地圖數據已載入: {filename}")
            self.map_loaded.emit(filename)
            return True
        else:
            self.logger.error(f"載入地圖數據失敗: {filename}")
            return False

    def get_initial(self):
        """✅ 獲取初始地圖檔案（給main.py使用）"""
        available_files = self.get_files()
        
        if not available_files:
            return None
        
        # 優先順序
        preferred_files = ['路徑_0點.json', 'fsaf.json', 'map.json', 'default_map.json']
        
        for preferred in preferred_files:
            if preferred in available_files:
                return preferred
        
        # 返回第一個可用檔案
        return available_files[0]

    def connect_gui(self, gui_widget):
        """連接到GUI小部件的便利方法"""
        try:
            # 連接信號到GUI更新方法
            if hasattr(gui_widget, 'on_waypoint_added'):
                self.waypoint_added.connect(gui_widget.on_waypoint_added)
            
            if hasattr(gui_widget, 'on_waypoint_removed'):
                self.waypoint_removed.connect(gui_widget.on_waypoint_removed)
            
            if hasattr(gui_widget, 'on_obstacle_added'):
                self.obstacle_added.connect(gui_widget.on_obstacle_added)
            
            if hasattr(gui_widget, 'on_area_updated'):
                self.area_updated.connect(gui_widget.on_area_updated)
            
            if hasattr(gui_widget, 'on_map_loaded'):
                self.map_loaded.connect(gui_widget.on_map_loaded)
            
            if hasattr(gui_widget, 'on_map_saved'):
                self.map_saved.connect(gui_widget.on_map_saved)
            
            self.logger.info("已連接PyQt5 GUI信號")
            return True
            
        except Exception as e:
            self.logger.error("連接GUI失敗", e)
            return False

    def disconnect_gui(self, gui_widget):
        """從GUI小部件斷開連接的便利方法"""
        try:
            # 斷開所有信號連接
            self.waypoint_added.disconnect()
            self.waypoint_removed.disconnect()
            self.waypoint_updated.disconnect()
            self.obstacle_added.disconnect()
            self.area_updated.disconnect()
            self.map_loaded.disconnect()
            self.map_saved.disconnect()
            
            self.logger.info("已斷開PyQt5 GUI信號")
            return True
            
        except Exception as e:
            self.logger.error("斷開GUI失敗", e)
            return False

    def get_status(self):
        """獲取系統狀態（供GUI顯示）"""
        return {
            'waypoints_count': len(self.waypoints),
            'obstacles_count': len(self.obstacles),
            'special_zones_count': len(self.special_zones),
            'area_grid_count': len(self.area_grid),
            'current_target': self.current_target_index,
            'coordinate_system': type(self.coordinate_system).__name__
        }

    def emit_status(self):
        """手動發射狀態更新信號"""
        status = self.get_status()
        # 可以添加狀態更新信號
        # self.status_updated.emit(status)
        return status

    def get_all(self):
        """回傳所有路徑點（相容外部調用）"""
        return self.waypoints

    def _find_alternative_path(self, from_pos: Tuple[float, float], 
                              to_pos: Tuple[float, float], obstacles: List[Dict]) -> str:
        """✅ 基於搜索結果[19]的簡單避障算法"""
        # 使用相對座標的偏移
        offsets = [
            (0.05, 0),    # 右偏
            (-0.05, 0),   # 左偏  
            (0, 0.05),    # 下偏
            (0, -0.05)    # 上偏
        ]
        
        for offset_x, offset_y in offsets:
            test_pos = (from_pos[0] + offset_x, from_pos[1] + offset_y)
            
            # 確保座標在有效範圍內
            test_pos = (
                max(0.0, min(1.0, test_pos[0])),
                max(0.0, min(1.0, test_pos[1]))
            )
            
            # 檢查這個偏移位置是否避開障礙物
            if not self.check_path(test_pos, to_pos):
                return self.coordinate_system.get_movement_direction(
                    from_pos, test_pos, 
                    self.coordinate_system.CoordinateType.MINIMAP
                )
        
        # 如果都避不開，返回原方向
        return self.coordinate_system.get_movement_direction(
            from_pos, to_pos, 
            self.coordinate_system.CoordinateType.MINIMAP
        )
    
    def _line_intersects_rect(self, line_start: Tuple[float, float], 
                             line_end: Tuple[float, float],
                             rect_center: Tuple[float, float], 
                             rect_size: Tuple[float, float]) -> bool:
        """線段與矩形相交檢測（使用相對座標）"""
        # 矩形邊界
        rx1 = rect_center[0] - rect_size[0] / 2
        ry1 = rect_center[1] - rect_size[1] / 2
        rx2 = rect_center[0] + rect_size[0] / 2
        ry2 = rect_center[1] + rect_size[1] / 2
        
        # 確保所有座標都在有效範圍內
        rx1 = max(0.0, min(1.0, rx1))
        ry1 = max(0.0, min(1.0, ry1))
        rx2 = max(0.0, min(1.0, rx2))
        ry2 = max(0.0, min(1.0, ry2))
        
        # 檢查線段端點是否在矩形內
        return (rx1 <= line_start[0] <= rx2 and ry1 <= line_start[1] <= ry2) or \
               (rx1 <= line_end[0] <= rx2 and ry1 <= line_end[1] <= ry2)
    
    def _point_in_rect(self, point: Tuple[float, float], 
                      rect_center: Tuple[float, float], 
                      rect_size: Tuple[float, float]) -> bool:
        """點是否在矩形內"""
        rx1 = rect_center[0] - rect_size[0] / 2
        ry1 = rect_center[1] - rect_size[1] / 2
        rx2 = rect_center[0] + rect_size[0] / 2
        ry2 = rect_center[1] + rect_size[1] / 2
        
        return rx1 <= point[0] <= rx2 and ry1 <= point[1] <= ry2