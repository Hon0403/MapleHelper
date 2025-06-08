# includes/grid_utils.py - 網格相關共用函數
"""
基於搜索結果[3][4]的網格操作工具
"""

class GridUtils:
    """網格操作統一工具類"""
    
    @staticmethod
    def paint_grid_area(center_x, center_y, brush_size, grid_size=0.01, 
                       area_manager=None, area_type="walkable"):
        """✅ 通用網格區域繪製"""
        painted_cells = []
        
        for dx in range(-int(brush_size/grid_size), int(brush_size/grid_size)+1):
            for dy in range(-int(brush_size/grid_size), int(brush_size/grid_size)+1):
                grid_x = center_x + dx * grid_size
                grid_y = center_y + dy * grid_size
                distance = ((dx * grid_size)**2 + (dy * grid_size)**2)**0.5
                
                if distance <= brush_size:
                    grid_key = (round(grid_x, 2), round(grid_y, 2))
                    painted_cells.append(grid_key)
                    
                    # 如果有區域管理器，直接添加
                    if area_manager and hasattr(area_manager, 'unified_area_management'):
                        area_manager.unified_area_management(grid_key, area_type, "add")
        
        return painted_cells
    
    @staticmethod
    def draw_line_grid(x1, y1, x2, y2, brush_size, grid_size=0.01):
        """✅ 通用直線網格計算"""
        line_cells = []
        steps = int(max(abs(x2-x1), abs(y2-y1)) * 1000)
        steps = max(steps, 10)
        
        for i in range(steps + 1):
            t = i / steps
            x = x1 + t * (x2 - x1)
            y = y1 + t * (y2 - y1)
            
            # 計算這個點的網格
            for dx in range(-int(brush_size/grid_size), int(brush_size/grid_size)+1):
                for dy in range(-int(brush_size/grid_size), int(brush_size/grid_size)+1):
                    grid_x = x + dx * grid_size
                    grid_y = y + dy * grid_size
                    distance = ((dx * grid_size)**2 + (dy * grid_size)**2)**0.5
                    
                    if distance <= brush_size:
                        grid_key = (round(grid_x, 2), round(grid_y, 2))
                        if grid_key not in line_cells:
                            line_cells.append(grid_key)
        
        return line_cells
