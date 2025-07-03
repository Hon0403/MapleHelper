import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import os
import logging

class ChineseTextRenderer:
    """中文文字渲染器 - 解決OpenCV無法顯示中文的問題"""
    
    def __init__(self, font_size=20):
        self.font_size = font_size
        self.font = self._get_chinese_font()
        self.logger = logging.getLogger(__name__)
        
    def _get_chinese_font(self):
        """獲取中文字體"""
        try:
            # Windows系統常見中文字體路径
            font_paths = [
                "C:/Windows/Fonts/msyh.ttc",  # 微軟雅黑
                "C:/Windows/Fonts/simsun.ttc",  # 宋體
                "C:/Windows/Fonts/simhei.ttf",  # 黑體
                "C:/Windows/Fonts/NotoSansCJK-Regular.ttc",  # Noto Sans CJK
            ]
            
            for font_path in font_paths:
                if os.path.exists(font_path):
                    try:
                        return ImageFont.truetype(font_path, self.font_size)
                    except:
                        continue
            
            # 如果找不到中文字體，使用默認字體
            return ImageFont.load_default()
            
        except Exception as e:
            self.logger.warning(f"載入中文字體失敗: {e}")
            return ImageFont.load_default()
    
    def put_chinese_text(self, img, text, position, font_color=(255, 255, 255), 
                        bg_color=None, font_size=None):
        """
        在OpenCV圖像上繪製中文文字
        
        Args:
            img: OpenCV圖像 (numpy array)
            text: 要顯示的文字
            position: 文字位置 (x, y)
            font_color: 字體顏色 (B, G, R)
            bg_color: 背景顏色，None表示透明背景
            font_size: 字體大小，None使用默認大小
            
        Returns:
            修改後的圖像
        """
        try:
            if font_size and font_size != self.font_size:
                # 臨時使用不同字體大小
                temp_font = ImageFont.truetype(self.font.path, font_size) if hasattr(self.font, 'path') else self.font
            else:
                temp_font = self.font
            
            # 將OpenCV圖像轉換為PIL圖像
            img_pil = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
            draw = ImageDraw.Draw(img_pil)
            
            # 獲取文字尺寸
            bbox = draw.textbbox((0, 0), text, font=temp_font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            
            x, y = position
            
            # 繪製背景（如果指定）
            if bg_color:
                bg_rect = [x-5, y-text_height-5, x+text_width+5, y+5]
                draw.rectangle(bg_rect, fill=bg_color)
            
            # 繪製文字 (PIL使用RGB格式)
            pil_color = (font_color[2], font_color[1], font_color[0])  # BGR轉RGB
            draw.text((x, y-text_height), text, font=temp_font, fill=pil_color)
            
            # 轉換回OpenCV格式
            img_result = cv2.cvtColor(np.array(img_pil), cv2.COLOR_RGB2BGR)
            
            return img_result
            
        except Exception as e:
            self.logger.warning(f"中文文字渲染失敗: {e}")
            # 降級到英文顯示
            cv2.putText(img, text.encode('ascii', 'ignore').decode('ascii'), 
                       position, cv2.FONT_HERSHEY_SIMPLEX, 0.6, font_color, 2)
            return img
    
    def put_text_with_background(self, img, text, position, font_color=(255, 255, 255),
                               bg_color=(0, 0, 0), font_size=None):
        """繪製帶背景的文字"""
        return self.put_chinese_text(img, text, position, font_color, bg_color, font_size)

# 全局實例
_chinese_renderer = None

def get_chinese_renderer(font_size=20):
    """獲取中文渲染器實例"""
    global _chinese_renderer
    if _chinese_renderer is None or _chinese_renderer.font_size != font_size:
        _chinese_renderer = ChineseTextRenderer(font_size)
    return _chinese_renderer

def safe_put_text(img, text, position, font_color=(255, 255, 255), 
                 bg_color=None, font_size=20):
    """
    安全的文字顯示函數 - 自動處理中文字符
    
    Args:
        img: OpenCV圖像
        text: 文字內容
        position: 位置 (x, y)
        font_color: 字體顏色 (B, G, R)
        bg_color: 背景顏色
        font_size: 字體大小
    """
    try:
        # 檢查是否包含中文字符
        if any('\u4e00' <= char <= '\u9fff' for char in text):
            # 包含中文，使用中文渲染器
            renderer = get_chinese_renderer(font_size)
            return renderer.put_chinese_text(img, text, position, font_color, bg_color, font_size)
        else:
            # 純英文，使用OpenCV原生功能
            if bg_color:
                # 計算背景框
                text_size = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 
                                          font_size/30.0, 2)[0]
                x, y = position
                cv2.rectangle(img, (x-5, y-text_size[1]-5), 
                            (x+text_size[0]+5, y+5), bg_color, -1)
            
            cv2.putText(img, text, position, cv2.FONT_HERSHEY_SIMPLEX, 
                       font_size/30.0, font_color, 2)
            return img
            
    except Exception as e:
        # 最後的降級方案
        try:
            cv2.putText(img, str(text), position, cv2.FONT_HERSHEY_SIMPLEX, 
                       0.6, font_color, 2)
        except:
            pass
        return img 