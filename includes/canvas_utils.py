# includes/canvas_utils.py - 畫布相關共用函數
"""
基於搜索結果[4][5]的重構最佳實踐
Canvas操作的共用工具函數庫
"""

import cv2
import numpy as np
from PIL import Image, ImageTk
import tkinter as tk

class CanvasUtils:
    """畫布操作統一工具類"""
    
    @staticmethod
    def transform_coordinates(x, y, canvas_width, canvas_height, scale_factor=1.0, 
                            direction="canvas_to_point", offset_x=0, offset_y=0):
        """✅ 通用座標轉換方法"""
        scaled_width = int(canvas_width * scale_factor)
        scaled_height = int(canvas_height * scale_factor)
        
        if offset_x == 0:
            offset_x = (canvas_width - scaled_width) // 2
        if offset_y == 0:
            offset_y = (canvas_height - scaled_height) // 2
        
        if direction == "canvas_to_point":
            image_x = x - offset_x
            image_y = y - offset_y
            
            if scaled_width > 0 and scaled_height > 0:
                rel_x = max(0.0, min(1.0, image_x / scaled_width))
                rel_y = max(0.0, min(1.0, image_y / scaled_height))
                return (rel_x, rel_y)
            return (0.5, 0.5)
        else:  # point_to_canvas
            image_x = x * scaled_width
            image_y = y * scaled_height
            canvas_x = image_x + offset_x
            canvas_y = image_y + offset_y
            return (canvas_x, canvas_y)
    
    @staticmethod
    def check_bounds(x, y, canvas_width, canvas_height, scale_factor=1.0, 
                    coordinate_type="canvas", offset_x=0, offset_y=0):
        """✅ 通用邊界檢查方法"""
        if coordinate_type == "canvas":
            scaled_width = int(canvas_width * scale_factor)
            scaled_height = int(canvas_height * scale_factor)
            
            if offset_x == 0:
                offset_x = (canvas_width - scaled_width) // 2
            if offset_y == 0:
                offset_y = (canvas_height - scaled_height) // 2
            
            return (offset_x <= x <= offset_x + scaled_width and
                    offset_y <= y <= offset_y + scaled_height)
        elif coordinate_type == "point":
            return (0.0 <= x <= 1.0 and 0.0 <= y <= 1.0)
        return False
    
    @staticmethod
    def get_scale_params(canvas_width, canvas_height, scale_factor=1.0):
        """✅ 通用縮放參數計算"""
        scaled_width = int(canvas_width * scale_factor)
        scaled_height = int(canvas_height * scale_factor)
        offset_x = (canvas_width - scaled_width) // 2
        offset_y = (canvas_height - scaled_height) // 2
        
        return {
            'scaled_width': scaled_width,
            'scaled_height': scaled_height,
            'offset_x': offset_x,
            'offset_y': offset_y,
            'scale_factor': scale_factor
        }
    
    @staticmethod
    def resize_image_to_canvas(image, canvas_width, canvas_height, fill_mode=True):
        """✅ 通用圖片縮放方法"""
        try:
            # 獲取原始圖片大小
            if isinstance(image, np.ndarray):
                h, w = image.shape[:2]
            else:
                w, h = image.size
            
            # 計算縮放比例
            if fill_mode:
                # 填滿模式：使用較大的縮放比例
                scale = max(canvas_width/w, canvas_height/h)
            else:
                # 適應模式：使用較小的縮放比例
                scale = min(canvas_width/w, canvas_height/h)
            
            # 計算新尺寸
            new_width = int(w * scale)
            new_height = int(h * scale)
            
            # 縮放圖片
            if isinstance(image, np.ndarray):
                resized = cv2.resize(image, (new_width, new_height), 
                                   interpolation=cv2.INTER_LANCZOS4)
            else:
                resized = image.resize((new_width, new_height), 
                                     Image.Resampling.LANCZOS)
            
            # 如果需要裁剪（填滿模式）
            if fill_mode and (new_width > canvas_width or new_height > canvas_height):
                if isinstance(resized, np.ndarray):
                    crop_x = (new_width - canvas_width) // 2
                    crop_y = (new_height - canvas_height) // 2
                    resized = resized[crop_y:crop_y+canvas_height, 
                                    crop_x:crop_x+canvas_width]
                else:
                    crop_x = (new_width - canvas_width) // 2
                    crop_y = (new_height - canvas_height) // 2
                    resized = resized.crop((
                        crop_x, crop_y,
                        crop_x + canvas_width,
                        crop_y + canvas_height
                    ))
            
            return resized
            
        except Exception as e:
            print(f"❌ 圖片縮放失敗: {e}")
            return image
    
    @staticmethod
    def create_canvas_image(canvas, image, scale_factor=1.0, fill_mode=True):
        """✅ 通用畫布圖片創建方法"""
        try:
            # 獲取畫布大小
            canvas_width = canvas.winfo_width()
            canvas_height = canvas.winfo_height()
            
            # 確保畫布大小有效
            if canvas_width <= 1 or canvas_height <= 1:
                canvas_width = canvas.cget('width')
                canvas_height = canvas.cget('height')
            
            # 縮放圖片
            resized = CanvasUtils.resize_image_to_canvas(
                image, canvas_width, canvas_height, fill_mode
            )
            
            # 轉換為PhotoImage
            if isinstance(resized, np.ndarray):
                resized = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)
                photo = ImageTk.PhotoImage(image=Image.fromarray(resized))
            else:
                photo = ImageTk.PhotoImage(image=resized)
            
            # 計算居中位置
            params = CanvasUtils.get_scale_params(canvas_width, canvas_height, scale_factor)
            
            # 創建圖片
            canvas.create_image(
                params['offset_x'], params['offset_y'],
                anchor=tk.NW,
                image=photo,
                tags="background"
            )
            
            # 保持引用
            canvas.image = photo
            
            return photo
            
        except Exception as e:
            print(f"❌ 創建畫布圖片失敗: {e}")
            return None
    
    @staticmethod
    def draw_point_on_canvas(canvas, x, y, radius=5, fill="red", outline="white", 
                           text=None, text_color="white", scale_factor=1.0):
        """✅ 通用點標記繪製方法"""
        try:
            # 獲取畫布大小
            canvas_width = canvas.winfo_width()
            canvas_height = canvas.winfo_height()
            
            # 轉換座標
            canvas_x, canvas_y = CanvasUtils.transform_coordinates(
                x, y, canvas_width, canvas_height, scale_factor,
                "point_to_canvas"
            )
            
            # 繪製點
            canvas.create_oval(
                canvas_x-radius, canvas_y-radius,
                canvas_x+radius, canvas_y+radius,
                fill=fill, outline=outline
            )
            
            # 如果有文字，繪製文字
            if text:
                canvas.create_text(
                    canvas_x, canvas_y-radius-5,
                    text=text,
                    fill=text_color,
                    font=("Arial", 8)
                )
            
        except Exception as e:
            print(f"❌ 繪製點標記失敗: {e}")
