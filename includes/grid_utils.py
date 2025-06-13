# includes/grid_utils.py - 網格相關共用函數
"""
基於搜索結果[3][4]的網格操作工具
"""

import numpy as np
from typing import List, Tuple, Dict, Set, Optional
import heapq

class GridUtils:
    """網格工具類 - 用於 A* 路徑規劃"""
    
    def __init__(self, grid_size: Tuple[int, int] = (100, 100)):
        self.grid_size = grid_size
        self.grid = np.zeros(grid_size, dtype=int)
        self.obstacles: Set[Tuple[int, int]] = set()
        self.special_zones: Dict[Tuple[int, int], str] = {}
        
    def world_to_grid(self, world_pos: Tuple[float, float]) -> Tuple[int, int]:
        """將世界座標轉換為網格座標"""
        x = int(world_pos[0] * self.grid_size[0])
        y = int(world_pos[1] * self.grid_size[1])
        return (max(0, min(x, self.grid_size[0]-1)), 
                max(0, min(y, self.grid_size[1]-1)))
    
    def grid_to_world(self, grid_pos: Tuple[int, int]) -> Tuple[float, float]:
        """將網格座標轉換為世界座標"""
        x = grid_pos[0] / self.grid_size[0]
        y = grid_pos[1] / self.grid_size[1]
        return (x, y)
    
    def add_obstacle(self, world_pos: Tuple[float, float], size: Tuple[float, float] = (0.05, 0.05)):
        """添加障礙物到網格"""
        center = self.world_to_grid(world_pos)
        size_x = int(size[0] * self.grid_size[0])
        size_y = int(size[1] * self.grid_size[1])
        
        for x in range(max(0, center[0]-size_x//2), min(self.grid_size[0], center[0]+size_x//2+1)):
            for y in range(max(0, center[1]-size_y//2), min(self.grid_size[1], center[1]+size_y//2+1)):
                self.obstacles.add((x, y))
                self.grid[y, x] = 1
    
    def add_special_zone(self, world_pos: Tuple[float, float], zone_type: str, 
                        size: Tuple[float, float] = (0.03, 0.03)):
        """添加特殊區域到網格"""
        center = self.world_to_grid(world_pos)
        size_x = int(size[0] * self.grid_size[0])
        size_y = int(size[1] * self.grid_size[1])
        
        for x in range(max(0, center[0]-size_x//2), min(self.grid_size[0], center[0]+size_x//2+1)):
            for y in range(max(0, center[1]-size_y//2), min(self.grid_size[1], center[1]+size_y//2+1)):
                self.special_zones[(x, y)] = zone_type
                self.grid[y, x] = 2
    
    def is_walkable(self, grid_pos: Tuple[int, int]) -> bool:
        """檢查網格位置是否可行走"""
        return (0 <= grid_pos[0] < self.grid_size[0] and 
                0 <= grid_pos[1] < self.grid_size[1] and 
                grid_pos not in self.obstacles)
    
    def get_neighbors(self, grid_pos: Tuple[int, int]) -> List[Tuple[int, int]]:
        """獲取相鄰的可行走網格"""
        x, y = grid_pos
        neighbors = []
        
        # 8方向移動
        for dx, dy in [(-1,-1), (-1,0), (-1,1), (0,-1), (0,1), (1,-1), (1,0), (1,1)]:
            new_pos = (x + dx, y + dy)
            if self.is_walkable(new_pos):
                neighbors.append(new_pos)
        
        return neighbors
    
    def heuristic(self, a: Tuple[int, int], b: Tuple[int, int]) -> float:
        """計算啟發式函數（使用對角線距離）"""
        dx = abs(a[0] - b[0])
        dy = abs(a[1] - b[1])
        return max(dx, dy) + (np.sqrt(2) - 1) * min(dx, dy)
    
    def find_path(self, start_world: Tuple[float, float], 
                 end_world: Tuple[float, float]) -> Optional[List[Tuple[float, float]]]:
        """使用 A* 算法尋找路徑"""
        start = self.world_to_grid(start_world)
        end = self.world_to_grid(end_world)
        
        if not self.is_walkable(start) or not self.is_walkable(end):
            return None
        
        # 初始化開放列表和關閉列表
        open_set = []
        closed_set = set()
        came_from = {}
        
        # 初始化起點的 g_score 和 f_score
        g_score = {start: 0}
        f_score = {start: self.heuristic(start, end)}
        heapq.heappush(open_set, (f_score[start], start))
        
        while open_set:
            current = heapq.heappop(open_set)[1]
            
            if current == end:
                # 重建路徑
                path = []
                while current in came_from:
                    path.append(self.grid_to_world(current))
                    current = came_from[current]
                path.append(self.grid_to_world(start))
                path.reverse()
                return self._smooth_path(path)
            
            closed_set.add(current)
            
            for neighbor in self.get_neighbors(current):
                if neighbor in closed_set:
                    continue
                
                # 計算新的 g_score
                tentative_g_score = g_score[current] + self.heuristic(current, neighbor)
                
                if neighbor not in g_score or tentative_g_score < g_score[neighbor]:
                    came_from[neighbor] = current
                    g_score[neighbor] = tentative_g_score
                    f_score[neighbor] = tentative_g_score + self.heuristic(neighbor, end)
                    
                    if neighbor not in [x[1] for x in open_set]:
                        heapq.heappush(open_set, (f_score[neighbor], neighbor))
        
        return None
    
    def _smooth_path(self, path: List[Tuple[float, float]]) -> List[Tuple[float, float]]:
        """平滑路徑，減少不必要的轉折"""
        if len(path) <= 2:
            return path
        
        smoothed = [path[0]]
        current = 0
        
        while current < len(path) - 1:
            # 尋找最遠的可見點
            furthest = current + 1
            for i in range(current + 2, len(path)):
                if self._is_line_of_sight(path[current], path[i]):
                    furthest = i
            
            smoothed.append(path[furthest])
            current = furthest
        
        return smoothed
    
    def _is_line_of_sight(self, start: Tuple[float, float], end: Tuple[float, float]) -> bool:
        """檢查兩點之間是否有視線（無障礙物）"""
        start_grid = self.world_to_grid(start)
        end_grid = self.world_to_grid(end)
        
        # 使用 Bresenham 算法檢查線段上的點
        x1, y1 = start_grid
        x2, y2 = end_grid
        dx = abs(x2 - x1)
        dy = abs(y2 - y1)
        x, y = x1, y1
        n = 1 + dx + dy
        x_inc = 1 if x2 > x1 else -1
        y_inc = 1 if y2 > y1 else -1
        error = dx - dy
        dx *= 2
        dy *= 2
        
        for _ in range(n):
            if not self.is_walkable((x, y)):
                return False
            
            if error > 0:
                x += x_inc
                error -= dy
            else:
                y += y_inc
                error += dx
        
        return True
    
    def clear(self):
        """清除網格數據"""
        self.grid = np.zeros(self.grid_size, dtype=int)
        self.obstacles.clear()
        self.special_zones.clear()
