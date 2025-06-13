# includes/event_utils.py - 事件處理共用函數
"""
基於搜索結果[5]的事件處理統一工具
"""

class EventUtils:
    """事件處理統一工具類"""
    
    @staticmethod
    def process_mouse_event(event, canvas, canvas_width, canvas_height, scale_factor=1.0):
        """✅ 通用鼠標事件處理"""
        from .canvas_utils import CanvasUtils
        
        # 獲取canvas座標
        canvas_x = canvas.canvasx(event.x)
        canvas_y = canvas.canvasy(event.y)
        
        # 獲取縮放參數
        params = CanvasUtils.get_scale_params(canvas_width, canvas_height, scale_factor)
        
        # 邊界檢查
        if not CanvasUtils.check_bounds(canvas_x, canvas_y, canvas_width, canvas_height, 
                                       scale_factor, "canvas", params['offset_x'], params['offset_y']):
            return None
        
        # 座標轉換
        rel_x, rel_y = CanvasUtils.transform_coordinates(
            canvas_x, canvas_y, canvas_width, canvas_height, scale_factor, 
            "canvas_to_point", params['offset_x'], params['offset_y']
        )
        
        return {
            'canvas_pos': (canvas_x, canvas_y),
            'relative_pos': (rel_x, rel_y),
            'params': params,
            'event': event
        }
    
    @staticmethod
    def detect_drag(start_x, start_y, current_x, current_y, threshold=5):
        """✅ 通用拖曳檢測"""
        return (abs(current_x - start_x) > threshold or 
                abs(current_y - start_y) > threshold)
