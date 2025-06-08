# modules/coordinate_system.py - 統一座標系統

import math
from typing import Tuple, Optional, Dict, Any
from enum import Enum

class CoordinateType(Enum):
    """座標類型枚舉"""
    MINIMAP = "minimap"          # 小地圖相對座標 (0.0-1.0)
    SCREEN = "screen"            # 螢幕像素座標
    WORLD = "world"              # 遊戲世界座標  
    WAYPOINT = "waypoint"        # 路徑點座標
    TILE = "tile"                # 地圖磚塊座標

class CoordinateSystem:
    """統一座標系統管理器"""
    
    def __init__(self):
        # 螢幕和遊戲設定
        self.screen_width = 1920
        self.screen_height = 1080
        self.bluestacks_width = 900
        self.bluestacks_height = 1600
        
        # 小地圖設定
        self.minimap_bounds = None  # 會由 coordinate.py 提供
        self.minimap_size = (200, 200)  # 預設小地圖大小
        
        # 世界座標設定
        self.world_scale = 1.0  # 世界座標縮放比例
        self.tile_size = 32     # 地圖磚塊大小（像素）
        
        # 座標偏移（用於校正）
        self.offsets = {
            CoordinateType.MINIMAP: (0.0, 0.0),
            CoordinateType.SCREEN: (0, 0),
            CoordinateType.WORLD: (0.0, 0.0),
            CoordinateType.WAYPOINT: (0.0, 0.0)
        }
        
        print("🗺️ 統一座標系統已初始化")
    
    def set_minimap_bounds(self, bounds: Tuple[int, int, int, int]):
        """設定小地圖邊界（由 coordinate.py 提供）"""
        self.minimap_bounds = bounds
        x1, y1, x2, y2 = bounds
        self.minimap_size = (x2 - x1, y2 - y1)
    
    def convert(self, point: Tuple[float, float], 
                from_type: CoordinateType, 
                to_type: CoordinateType) -> Tuple[float, float]:
        """座標轉換核心方法"""
        
        if from_type == to_type:
            return point
        
        # 先轉換到標準化座標（世界座標）
        world_point = self._to_world_coordinate(point, from_type)
        
        # 再從世界座標轉換到目標座標
        return self._from_world_coordinate(world_point, to_type)
    
    def _to_world_coordinate(self, point: Tuple[float, float], 
                           from_type: CoordinateType) -> Tuple[float, float]:
        """轉換到世界座標"""
        x, y = point
        
        if from_type == CoordinateType.WORLD:
            return (x, y)
        
        elif from_type == CoordinateType.MINIMAP:
            # 小地圖相對座標 -> 世界座標
            world_x = x * self.bluestacks_width * self.world_scale
            world_y = y * self.bluestacks_height * self.world_scale
            return (world_x, world_y)
        
        elif from_type == CoordinateType.SCREEN:
            # 螢幕像素座標 -> 世界座標
            rel_x = x / self.bluestacks_width
            rel_y = y / self.bluestacks_height
            world_x = rel_x * self.bluestacks_width * self.world_scale
            world_y = rel_y * self.bluestacks_height * self.world_scale
            return (world_x, world_y)
        
        elif from_type == CoordinateType.WAYPOINT:
            # 路徑點座標 -> 世界座標（與小地圖相同）
            return self._to_world_coordinate(point, CoordinateType.MINIMAP)
        
        elif from_type == CoordinateType.TILE:
            # 磚塊座標 -> 世界座標
            world_x = x * self.tile_size
            world_y = y * self.tile_size
            return (world_x, world_y)
        
        return (x, y)
    
    def _from_world_coordinate(self, world_point: Tuple[float, float], 
                             to_type: CoordinateType) -> Tuple[float, float]:
        """從世界座標轉換到指定座標"""
        wx, wy = world_point
        
        if to_type == CoordinateType.WORLD:
            return (wx, wy)
        
        elif to_type == CoordinateType.MINIMAP:
            # 世界座標 -> 小地圖相對座標
            rel_x = wx / (self.bluestacks_width * self.world_scale)
            rel_y = wy / (self.bluestacks_height * self.world_scale)
            return (max(0.0, min(1.0, rel_x)), max(0.0, min(1.0, rel_y)))
        
        elif to_type == CoordinateType.SCREEN:
            # 世界座標 -> 螢幕像素座標
            rel_x = wx / (self.bluestacks_width * self.world_scale)
            rel_y = wy / (self.bluestacks_height * self.world_scale)
            screen_x = rel_x * self.bluestacks_width
            screen_y = rel_y * self.bluestacks_height
            return (int(screen_x), int(screen_y))
        
        elif to_type == CoordinateType.WAYPOINT:
            # 世界座標 -> 路徑點座標（與小地圖相同）
            return self._from_world_coordinate(world_point, CoordinateType.MINIMAP)
        
        elif to_type == CoordinateType.TILE:
            # 世界座標 -> 磚塊座標
            tile_x = wx / self.tile_size
            tile_y = wy / self.tile_size
            return (int(tile_x), int(tile_y))
        
        return (wx, wy)
    
    def calculate_distance(self, point1: Tuple[float, float], point2: Tuple[float, float],
                          coord_type: CoordinateType = CoordinateType.WORLD) -> float:
        """計算兩點間距離"""
        # 轉換到世界座標進行計算
        world_p1 = self.convert(point1, coord_type, CoordinateType.WORLD)
        world_p2 = self.convert(point2, coord_type, CoordinateType.WORLD)
        
        dx = world_p2[0] - world_p1[0]
        dy = world_p2[1] - world_p1[1]
        return math.sqrt(dx**2 + dy**2)
    
    def get_direction_vector(self, from_point: Tuple[float, float], 
                           to_point: Tuple[float, float],
                           coord_type: CoordinateType = CoordinateType.WORLD) -> Tuple[float, float]:
        """獲取方向向量"""
        world_from = self.convert(from_point, coord_type, CoordinateType.WORLD)
        world_to = self.convert(to_point, coord_type, CoordinateType.WORLD)
        
        dx = world_to[0] - world_from[0]
        dy = world_to[1] - world_from[1]
        
        # 歸一化
        distance = math.sqrt(dx**2 + dy**2)
        if distance > 0:
            return (dx / distance, dy / distance)
        return (0.0, 0.0)
    
    def get_movement_direction(self, from_point: Tuple[float, float], 
                             to_point: Tuple[float, float],
                             coord_type: CoordinateType = CoordinateType.MINIMAP) -> str:
        """獲取8方向移動指令"""
        direction_vector = self.get_direction_vector(from_point, to_point, coord_type)
        dx, dy = direction_vector
        
        # 8方向判斷
        angle = math.degrees(math.atan2(dy, dx))
        if angle < 0:
            angle += 360
        
        # 根據角度確定方向
        if 337.5 <= angle or angle < 22.5:
            return 'right'
        elif 22.5 <= angle < 67.5:
            return 'down_right'
        elif 67.5 <= angle < 112.5:
            return 'down'
        elif 112.5 <= angle < 157.5:
            return 'down_left'
        elif 157.5 <= angle < 202.5:
            return 'left'
        elif 202.5 <= angle < 247.5:
            return 'up_left'
        elif 247.5 <= angle < 292.5:
            return 'up'
        elif 292.5 <= angle < 337.5:
            return 'up_right'
        
        return 'right'  # 預設方向
    
    def calibrate_offset(self, measured_point: Tuple[float, float], 
                        expected_point: Tuple[float, float], 
                        coord_type: CoordinateType):
        """座標系校正（當發現座標偏移時使用）"""
        offset_x = expected_point[0] - measured_point[0]
        offset_y = expected_point[1] - measured_point[1]
        
        self.offsets[coord_type] = (offset_x, offset_y)
        print(f"🔧 座標校正 {coord_type.value}: 偏移 ({offset_x:.3f}, {offset_y:.3f})")
    
    def get_debug_info(self) -> Dict[str, Any]:
        """獲取座標系統除錯資訊"""
        return {
            'screen_size': (self.screen_width, self.screen_height),
            'bluestacks_size': (self.bluestacks_width, self.bluestacks_height),
            'minimap_bounds': self.minimap_bounds,
            'minimap_size': self.minimap_size,
            'world_scale': self.world_scale,
            'tile_size': self.tile_size,
            'offsets': {k.value: v for k, v in self.offsets.items()}
        }

# 全域座標系統實例
coordinate_system = CoordinateSystem()
