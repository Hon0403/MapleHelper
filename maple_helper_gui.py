import math

class MapleHelperGUI:
    def draw_arrow(self, canvas, x1, y1, x2, y2, color="red", width=2):
        """繪製箭頭"""
        # 計算箭頭方向
        dx = x2 - x1
        dy = y2 - y1
        length = (dx**2 + dy**2)**0.5
        
        if length == 0:
            return
            
        # 計算箭頭角度
        angle = math.atan2(dy, dx)
        
        # 箭頭大小
        arrow_size = 10
        
        # 計算箭頭尖端位置
        arrow_x = x2 - arrow_size * math.cos(angle)
        arrow_y = y2 - arrow_size * math.sin(angle)
        
        # 計算箭頭兩側點
        arrow_angle1 = angle + math.pi * 0.75
        arrow_angle2 = angle - math.pi * 0.75
        
        arrow_x1 = arrow_x + arrow_size * math.cos(arrow_angle1)
        arrow_y1 = arrow_y + arrow_size * math.sin(arrow_angle1)
        
        arrow_x2 = arrow_x + arrow_size * math.cos(arrow_angle2)
        arrow_y2 = arrow_y + arrow_size * math.sin(arrow_angle2)
        
        # 繪製主線
        canvas.create_line(x1, y1, x2, y2, fill=color, width=width)
        
        # 繪製箭頭
        canvas.create_polygon(
            x2, y2,
            arrow_x1, arrow_y1,
            arrow_x2, arrow_y2,
            fill=color, outline=color
        )

    def _draw_waypoints(self):
        """繪製路徑點和連接線"""
        # 清除現有的繪圖
        self.canvas.delete("waypoint")
        
        # 繪製連接線
        for i in range(len(self.waypoints) - 1):
            x1, y1 = self.waypoints[i]
            x2, y2 = self.waypoints[i + 1]
            self.draw_arrow(
                self.canvas,
                x1, y1, x2, y2,
                color="blue",
                width=2
            )
        
        # 繪製路徑點
        for i, (x, y) in enumerate(self.waypoints):
            # 繪製點
            self.canvas.create_oval(
                x - 5, y - 5,
                x + 5, y + 5,
                fill="red",
                outline="black",
                tags="waypoint"
            )
            
            # 繪製編號
            self.canvas.create_text(
                x, y - 15,
                text=str(i + 1),
                fill="black",
                tags="waypoint"
            ) 