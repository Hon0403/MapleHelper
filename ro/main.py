import cv2
import numpy as np
import matplotlib.pyplot as plt
import os
import math

# --- 設定區 ---
image_filename = 'cut_map.png'  # <<< 使用你上傳的已裁切圖片
grid_size = 2  # 每個格子的像素大小 (可調整)
# 可行走區域的 HSV 顏色範圍 (目前針對黃色，可能需微調)
lower_walkable = np.array([20, 100, 100]) # 黃色下限 (色相, 飽和度, 亮度)
upper_walkable = np.array([35, 255, 255]) # 黃色上限
# --- 設定區結束 ---

map_array = np.empty((0, 0), dtype=int) # 初始化 map_array
mask = None # 初始化 mask

if not os.path.exists(image_filename):
    print(f"錯誤：找不到檔案 '{image_filename}'。")
    exit()

# 直接讀取已裁切的地圖圖片
img = cv2.imread(image_filename)

if img is None:
    print(f"錯誤：無法使用 OpenCV 讀取檔案 '{image_filename}'。")
    exit()
else:
    # --- 因為 img 已經是裁切好的地圖，直接使用 img 進行處理 ---
    print("圖像成功載入 (已裁切)，尺寸為：", img.shape)

    # --- 圖像處理 (直接對 img 操作) ---
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV) # 使用 img
    mask = cv2.inRange(hsv, lower_walkable, upper_walkable) # 使用 hsv
    # --- 圖像處理結束 ---

    # --- 生成網格陣列 ---
    h, w = mask.shape[:2] # 使用 mask 的尺寸
    rows = math.ceil(h / grid_size)
    cols = math.ceil(w / grid_size)
    current_map_array_list = [] # 臨時列表
    for i in range(rows):
        row_data = []
        for j in range(cols):
            cell_y_start = i * grid_size
            cell_y_end = min((i + 1) * grid_size, h)
            cell_x_start = j * grid_size
            cell_x_end = min((j + 1) * grid_size, w)
            if cell_y_start >= cell_y_end or cell_x_start >= cell_x_end: continue
            cell = mask[cell_y_start:cell_y_end, cell_x_start:cell_x_end]
            if cell.size == 0:
                row_data.append(1) # 障礙
                continue
            if np.mean(cell) > 127:
                row_data.append(0) # 可行走
            else:
                row_data.append(1) # 障礙
        if row_data or cols > 0:
            current_map_array_list.append(row_data)

    if current_map_array_list:
        # 確保所有行的長度一致，用障礙物填充
        max_cols = max(len(r) for r in current_map_array_list)
        padded_list = [r + [1] * (max_cols - len(r)) for r in current_map_array_list]
        map_array = np.array(padded_list)
    else:
        map_array = np.empty((0, 0), dtype=int) # 保持空陣列
    # --- 生成網格陣列結束 ---

# --- 視覺化 (使用 img 和生成的 map_array) ---
if img is not None and map_array.size > 0 and mask is not None:
    fig, axes = plt.subplots(1, 3, figsize=(18, 6))
    fig.suptitle('地圖網格化分析 (使用已裁切圖片)', fontsize=16)

    # 1. 原始(已裁切)地圖
    axes[0].imshow(cv2.cvtColor(img, cv2.COLOR_BGR2RGB)) # 使用 img
    axes[0].set_title('1. 原始(已裁切)地圖')
    axes[0].axis('off')

    # 2. 顏色遮罩
    axes[1].imshow(mask, cmap='gray') # 使用 mask
    axes[1].set_title('2. 可行走顏色遮罩 (白色=符合)')
    axes[1].axis('off')

    # 3. 地圖與網格疊加
    axes[2].imshow(cv2.cvtColor(img, cv2.COLOR_BGR2RGB)) # 使用 img
    if map_array.size > 0:
        actual_rows, actual_cols = map_array.shape
        h_mask, w_mask = mask.shape[:2] # 獲取遮罩尺寸
        rows_ceil = math.ceil(h_mask / grid_size)
        cols_ceil = math.ceil(w_mask / grid_size)
        for i in range(actual_rows):
            for j in range(actual_cols):
                y = i * grid_size
                x = j * grid_size
                current_grid_h = min(grid_size, h_mask - y)
                current_grid_w = min(grid_size, w_mask - x)
                if i < map_array.shape[0] and j < map_array.shape[1]:
                    color = 'green' if map_array[i, j] == 0 else 'red'
                    rect = plt.Rectangle((x, y), current_grid_w, current_grid_h,
                                         linewidth=0, facecolor=color, alpha=0.4)
                    axes[2].add_patch(rect)

        for i in range(rows_ceil + 1):
            y_line = min(i * grid_size, h_mask)
            axes[2].axhline(y=y_line, color='black', linestyle='-', linewidth=0.5, alpha=0.5)
        for j in range(cols_ceil + 1):
            x_line = min(j * grid_size, w_mask)
            axes[2].axvline(x=x_line, color='black', linestyle='-', linewidth=0.5, alpha=0.5)

    axes[2].set_title('3. 地圖與網格疊加 (綠:可行走, 紅:障礙)')
    axes[2].set_xlim(0, w_mask) # 使用遮罩寬度
    axes[2].set_ylim(h_mask, 0) # 使用遮罩高度
    axes[2].axis('off')

    plt.tight_layout(rect=[0, 0, 1, 0.96])
    plt.show()
else:
    print("無法進行視覺化，因為 img 或 map_array 未能成功生成。")
# --- 視覺化結束 ---
