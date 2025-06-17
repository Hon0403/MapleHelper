import cv2
import numpy as np
import os

def calculate_red_area(image_path):
    """
    計算單張圖片中紅色區域的面積。
    """
    # 1. 讀取圖片
    frame = cv2.imread(image_path)
    if frame is None:
        print(f"錯誤：無法讀取圖片 {image_path}")
        return None

    # 2. 轉換到 HSV 色彩空間
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

    # 3. 定義紅色的 HSV 範圍
    # 這個範圍針對的是像血條一樣明亮、飽和的紅色
    # 範圍 (H:色相, S:飽和度, V:明度)
    red_lower = np.array([0, 150, 150])
    red_upper = np.array([10, 255, 255])
    
    # 建立遮罩
    mask = cv2.inRange(hsv, red_lower, red_upper)

    # 4. 尋找輪廓
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    if not contours:
        # 如果沒有找到任何紅色輪廓
        return 0

    # 5. 計算最大輪廓的面積
    # 假設血條是圖中最大塊的紅色物體
    largest_contour = max(contours, key=cv2.contourArea)
    area = int(cv2.contourArea(largest_contour))
    
    return area

# --- 主程式開始 ---
# 您提供的圖片檔案列表
image_files = ["templates/MainScreen/Health.png", "templates/MainScreen/Health50%.png", "templates/MainScreen/Health10%.png"]

print("--- 開始分析血條面積 ---")

# 用一個字典來儲存結果
results = {}

for file in image_files:
    if os.path.exists(file):
        # 呼叫函式計算面積
        calculated_area = calculate_red_area(file)
        if calculated_area is not None:
            results[file] = calculated_area
            # 使用 ljust 讓輸出對齊，方便閱讀
            print(f"檔案: {file.ljust(15)} | 偵測到的紅色面積: {calculated_area} 像素")
    else:
        print(f"找不到檔案: {file}，請確認檔案名稱及路徑是否正確。")

print("\n--- 分析完成 ---")

# --- 根據結果進行分析和建議 ---
if results:
    min_area = min(results.values())
    max_area = max(results.values())
    
    print("\n【分析結論】")
    print(f"您提供的樣本中，最小的血條面積約為: {min_area}")
    print(f"您提供的樣本中，最大的血條面積約為: {max_area}")
    
    # 根據測量結果，提出建議的篩選範圍
    suggested_min = int(min_area * 0.8) # 建議下限為最小值的 80%
    suggested_max = int(max_area * 1.2) # 建議上限為最大值的 120%

    print("\n【建議設定】")
    print(f"建議將面積下限設定在 {suggested_min} 左右 (比 {min_area} 稍低)")
    print(f"建議將面積上限設定在 {suggested_max} 左右 (比 {max_area} 稍高)")
    print(f"所以，一個可靠的面積條件是： if {suggested_min} < area < {suggested_max}:")