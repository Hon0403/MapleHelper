import cv2
import numpy as np
import os
import glob
from pathlib import Path

def clean_directory(directory):
    """清理目錄中的舊模板檔案"""
    # 要刪除的檔案類型
    patterns = ['*_flipped.png', '*_roi*.png', '*_keypoints.png', '*_resized.png']
    
    # 刪除所有符合模式的檔案
    for pattern in patterns:
        files = glob.glob(os.path.join(directory, pattern))
        for file in files:
            try:
                os.remove(file)
                print(f"🗑️ 已刪除: {file}")
            except Exception as e:
                print(f"❌ 無法刪除 {file}: {e}")

def enhance_image(image):
    """增強圖像品質"""
    # 轉換為灰度圖
    if len(image.shape) == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image.copy()
    
    # 自適應直方圖均衡化
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
    enhanced = clahe.apply(gray)
    
    # 降噪
    denoised = cv2.fastNlMeansDenoising(enhanced, None, 10, 7, 21)
    
    # 銳化
    kernel = np.array([[-1,-1,-1], [-1,9,-1], [-1,-1,-1]])
    sharpened = cv2.filter2D(denoised, -1, kernel)
    
    return sharpened

def extract_roi(image, padding=5):
    """提取感興趣區域"""
    # 轉換為灰度圖
    if len(image.shape) == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image.copy()
    
    # 二值化
    _, binary = cv2.threshold(gray, 1, 255, cv2.THRESH_BINARY)
    
    # 找到非零像素的邊界
    contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return image
    
    # 找到最大的輪廓
    max_contour = max(contours, key=cv2.contourArea)
    x, y, w, h = cv2.boundingRect(max_contour)
    
    # 添加邊距
    x = max(0, x - padding)
    y = max(0, y - padding)
    w = min(image.shape[1] - x, w + 2 * padding)
    h = min(image.shape[0] - y, h + 2 * padding)
    
    return image[y:y+h, x:x+w]

def process_template(template_path, output_dir):
    """處理單個模板"""
    # 讀取原始圖像
    original = cv2.imread(template_path, cv2.IMREAD_UNCHANGED)
    if original is None:
        print(f"❌ 無法讀取圖像: {template_path}")
        return
    
    # 提取 ROI
    roi = extract_roi(original)
    
    # 增強圖像
    enhanced = enhance_image(roi)
    
    # 水平翻轉
    flipped = cv2.flip(enhanced, 1)
    
    # 生成輸出檔案名稱
    base_name = os.path.splitext(os.path.basename(template_path))[0]
    
    # 只保存翻轉後的圖像
    output_path = os.path.join(output_dir, f"{base_name}_flipped.png")
    cv2.imwrite(output_path, flipped)
    print(f"✅ 已生成翻轉模板: {output_path}")

def main():
    # 設定輸入和輸出目錄
    input_dir = "templates/monsters/三眼章魚"
    output_dir = input_dir
    
    # 確保輸出目錄存在
    os.makedirs(output_dir, exist_ok=True)
    
    # 清理舊的模板檔案
    print("🧹 清理舊的模板檔案...")
    clean_directory(output_dir)
    
    # 取得所有 PNG 檔案
    png_files = glob.glob(os.path.join(input_dir, "*.png"))
    
    # 過濾掉已經處理過的檔案
    png_files = [f for f in png_files if not any(x in f for x in ['_flipped', '_roi', '_keypoints', '_resized'])]
    
    print(f"📁 找到 {len(png_files)} 個需要處理的模板")
    
    # 處理每個模板
    for template_path in png_files:
        process_template(template_path, output_dir)
    
    print("✨ 所有模板處理完成！")

if __name__ == "__main__":
    main() 