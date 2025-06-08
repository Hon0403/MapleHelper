# modules/simple_waypoint_system.py - 添加障礙物標記功能

import json
import os
from typing import Dict, List, Optional, Tuple

from modules.coordinate_system import coordinate_system


class SimpleWaypointSystem:
    def __init__(self):
        self.waypoints: List[Dict] = []
        # ✅ 新增：障礙物和特殊區域
        self.obstacles: List[Dict] = []
        self.special_zones: List[Dict] = []
        self.current_target_index = 0
        self.tolerance = 0.05
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
        
        self.coordinate_system = coordinate_system
        self._init_default_waypoints()
        
        print("🗺️ 路徑點系統已整合障礙物標記功能")

    def add_obstacle(self, position: Tuple[float, float], obstacle_type: str, 
                    size: Tuple[float, float] = (0.05, 0.05)) -> Dict:
        """添加障礙物標記"""
        obstacle = {
            'id': len(self.obstacles),
            'pos': position,
            'type': obstacle_type,
            'size': size,  # 障礙物大小
            'passable': self.obstacle_types.get(obstacle_type, {}).get('passable', False),
            'name': f"{self.obstacle_types.get(obstacle_type, {}).get('name', '未知')}_{len(self.obstacles)}"
        }
        
        self.obstacles.append(obstacle)
        print(f"🚧 添加障礙物: {obstacle['name']} at {position}")
        return obstacle
    
    def add_action_zone(self, position: Tuple[float, float], zone_type: str,
                       size: Tuple[float, float] = (0.03, 0.03)) -> Dict:
        """添加特殊動作區域"""
        zone = {
            'id': len(self.special_zones),
            'pos': position,
            'type': zone_type,
            'size': size,
            'action': self.action_zones.get(zone_type, {}).get('action', 'none'),
            'name': f"{self.action_zones.get(zone_type, {}).get('name', '未知')}_{len(self.special_zones)}"
        }
        
        self.special_zones.append(zone)
        print(f"🎯 添加動作區域: {zone['name']} at {position}")
        return zone
    
    def check_obstacles_on_path(self, from_pos: Tuple[float, float], 
                               to_pos: Tuple[float, float]) -> List[Dict]:
        """檢查路徑上的障礙物"""
        obstacles_on_path = []
        
        for obstacle in self.obstacles:
            if not obstacle['passable']:
                # 簡單的線段與矩形相交檢測
                if self._line_intersects_rect(from_pos, to_pos, 
                                            obstacle['pos'], obstacle['size']):
                    obstacles_on_path.append(obstacle)
        
        return obstacles_on_path
    
    def get_action_for_position(self, position: Tuple[float, float]) -> Optional[str]:
        """獲取位置上的特殊動作"""
        for zone in self.special_zones:
            if self._point_in_rect(position, zone['pos'], zone['size']):
                return zone['action']
        return None
    
    def get_movement_with_obstacles(self, current_pos: Tuple[float, float]) -> Dict:
        """✅ 基於搜索結果[17]的障礙物感知移動"""
        target = self.get_next_waypoint(current_pos)
        if not target:
            return {'direction': None, 'action': None, 'obstacles': []}
        
        # 確保使用相同類型的座標進行比較
        target_pos = target['pos']  # 已經是相對座標
        
        # 檢查路徑上的障礙物
        obstacles = self.check_obstacles_on_path(current_pos, target_pos)
        
        # 檢查當前位置的特殊動作
        special_action = self.get_action_for_position(current_pos)
        
        # 基本移動方向
        direction = self.coordinate_system.get_movement_direction(
            current_pos, target_pos, 
            self.coordinate_system.CoordinateType.MINIMAP
        )
        
        # 如果有障礙物，嘗試繞路
        if obstacles:
            direction = self._find_alternative_path(current_pos, target_pos, obstacles)
        
        return {
            'direction': self._simplify_direction(direction),
            'action': special_action,
            'obstacles': obstacles,
            'target': target
        }
    
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
            if not self.check_obstacles_on_path(test_pos, to_pos):
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
    
    def save_map_data(self, filename: str = "data/map_data.json"):
        """保存地圖數據 - 包含區域標記"""
        # ✅ 基於搜索結果[6]的grid data結構
        area_grid_json = {}
        for key, value in self.area_grid.items():
            if isinstance(key, tuple):
                string_key = f"{key[0]},{key[1]}"
                area_grid_json[string_key] = value
            else:
                area_grid_json[str(key)] = value
        
        map_data = {
            'waypoints': self.waypoints,
            'obstacles': self.obstacles,
            'special_zones': self.special_zones,
            # ✅ 確保保存區域標記
            'area_grid': area_grid_json,
            'obstacle_types': self.obstacle_types,
            'action_zones': self.action_zones
        }
        
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(map_data, f, indent=2, ensure_ascii=False)
        
        print(f"💾 地圖數據已保存: {filename}")
    
    def load_map_data(self, file_path=None):
        """✅ 修正版：自動載入現有檔案"""
        try:
            if file_path is None:
                # ✅ 不使用硬編碼，改為自動選擇現有檔案
                available_files = self.get_available_map_files()
                
                if available_files:
                    # 優先載入常用檔案名稱
                    preferred_files = ['路徑_0點.json', 'fsaf.json', 'map.json', 'default_map.json']
                    selected_file = None
                    
                    # 按優先順序尋找
                    for preferred in preferred_files:
                        if preferred in available_files:
                            selected_file = preferred
                            break
                    
                    # 如果沒有找到優先檔案，使用第一個可用檔案
                    if not selected_file:
                        selected_file = available_files[0]
                    
                    file_path = os.path.join("data", selected_file)
                    print(f"🔄 自動選擇載入: {selected_file}")
                else:
                    print("❌ data資料夾中沒有可用的地圖檔案")
                    return False
            
            # ✅ 確保使用絕對路徑
            if not os.path.isabs(file_path):
                base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                full_path = os.path.join(base_dir, file_path)
            else:
                full_path = file_path
            
            print(f"🔍 載入路徑檔案: {full_path}")
            
            if not os.path.exists(full_path):
                print(f"❌ 地圖檔案不存在: {full_path}")
                return False
            
            with open(full_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 載入資料
            self.waypoints = data.get('waypoints', [])
            self.obstacles = data.get('obstacles', [])
            self.area_grid = data.get('area_grid', {})
            
            print(f"✅ 載入成功: {os.path.basename(full_path)}")
            print(f"   📍 路徑點: {len(self.waypoints)} 個")
            print(f"   🚧 障礙物: {len(self.obstacles)} 個") 
            print(f"   🎨 區域標記: {len(self.area_grid)} 個")
            
            return True
            
        except Exception as e:
            print(f"❌ 載入失敗: {e}")
            return False

    def _simplify_direction(self, direction: str) -> str:
        """簡化方向指令"""
        direction_map = {
            'down_right': 'right',
            'down_left': 'left', 
            'up_right': 'right',
            'up_left': 'left'
        }
        return direction_map.get(direction, direction)

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

    def unified_area_management(self, position, area_type, operation="add"):
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
    
    def _list_available_data_files(self):
        """✅ 基於搜索結果[18]的數據目錄檢查"""
        try:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            data_dir = os.path.join(base_dir, "data")
            
            print(f"🔍 檢查數據目錄: {data_dir}")
            
            if not os.path.exists(data_dir):
                print(f"❌ data資料夾不存在")
                return
            
            # 列出所有JSON檔案
            json_files = []
            all_files = []
            
            for file in os.listdir(data_dir):
                all_files.append(file)
                if file.endswith('.json'):
                    json_files.append(file)
            
            print(f"📁 data資料夾內容:")
            print(f"   📄 所有檔案: {all_files}")
            print(f"   📋 JSON檔案: {json_files}")
            
            # 嘗試載入每個JSON檔案
            for json_file in json_files:
                self._try_load_json_file(os.path.join(data_dir, json_file))
                
        except Exception as e:
            print(f"❌ 檢查數據目錄失敗: {e}")

    def _try_load_json_file(self, file_path):
        """嘗試載入JSON檔案並顯示內容"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            waypoints_count = len(data.get('waypoints', []))
            obstacles_count = len(data.get('obstacles', []))
            area_grid_count = len(data.get('area_grid', {}))
            
            print(f"   ✅ {os.path.basename(file_path)}: {waypoints_count}路徑點, {obstacles_count}障礙物, {area_grid_count}區域")
            
        except Exception as e:
            print(f"   ❌ {os.path.basename(file_path)}: 載入失敗 - {e}")

    def get_available_map_files(self):
        """✅ 獲取可用的地圖檔案列表"""
        try:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            data_dir = os.path.join(base_dir, "data")
            
            if not os.path.exists(data_dir):
                return []
            
            json_files = []
            for file in os.listdir(data_dir):
                if file.endswith('.json'):
                    json_files.append(file)
            
            return sorted(json_files)
            
        except Exception as e:
            print(f"❌ 獲取檔案列表失敗: {e}")
            return []

    def load_specific_map(self, filename):
        """載入特定地圖檔案"""
        if not filename.endswith('.json'):
            filename += '.json'
        
        file_path = os.path.join("data", filename)
        return self.load_map_data(file_path)    
    
    def get_initial_map_file(self):
        """✅ 獲取初始地圖檔案（給main.py使用）"""
        available_files = self.get_available_map_files()
        
        if not available_files:
            return None
        
        # 優先順序
        preferred_files = ['路徑_0點.json', 'fsaf.json', 'map.json', 'default_map.json']
        
        for preferred in preferred_files:
            if preferred in available_files:
                return preferred
        
        # 返回第一個可用檔案
        return available_files[0]    