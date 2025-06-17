import cv2
import numpy as np
import os
import shutil
import glob

output_dir = "auto_templates"
os.makedirs(output_dir, exist_ok=True)

# === 1. 自動裁切怪物模板 ===
screenshot_path = "D:/Full_end/Python/MapleHelper/current_frame_1749364772.png"  # 來源截圖
template_path = "D:/Full_end/Python/MapleHelper/test1.png"  # 參考模板

img = cv2.imread(screenshot_path, cv2.IMREAD_UNCHANGED)
template = cv2.imread(template_path, cv2.IMREAD_UNCHANGED)

if img is None or template is None:
    print("❌ 讀取圖片失敗")
    exit()

print(f"截圖大小: {img.shape}")
print(f"參考模板大小: {template.shape}")

# 轉灰階
if img.shape[2] == 4:
    gray = cv2.cvtColor(img, cv2.COLOR_BGRA2GRAY)
else:
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

if template.shape[2] == 4:
    template_gray = cv2.cvtColor(template, cv2.COLOR_BGRA2GRAY)
    mask = template[:, :, 3]
else:
    template_gray = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY)
    mask = None

# 模板匹配找參考位置
res = cv2.matchTemplate(gray, template_gray, cv2.TM_CCOEFF_NORMED, mask=mask)
min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)
reference_x, reference_y = max_loc
th, tw = template_gray.shape[:2]

print(f"參考模板位置: ({reference_x}, {reference_y})")
print(f"匹配值: {max_val:.3f}")

# 二值化+輪廓
binary = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)
kernel = np.ones((3,3), np.uint8)
binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)
binary = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel)
contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
print(f"\n找到 {len(contours)} 個輪廓")

# 根據參考模板位置和大小過濾輪廓，自動裁切
count = 0
template_paths_auto = []
for i, cnt in enumerate(contours):
    x, y, w, h = cv2.boundingRect(cnt)
    center_x = x + w//2
    center_y = y + h//2
    ref_center_x = reference_x + tw//2
    ref_center_y = reference_y + th//2
    distance = np.sqrt((center_x - ref_center_x)**2 + (center_y - ref_center_y)**2)
    print(f"\n輪廓 {i}:")
    print(f"位置: ({x}, {y}), 大小: {w}x{h}")
    print(f"中心點: ({center_x}, {center_y})")
    print(f"與參考模板距離: {distance:.1f}")
    # 大幅放寬條件：允許更大尺寸差異與距離，最小尺寸更小
    if (abs(w - tw) < 200 and abs(h - th) < 200 and distance < 600 and w >= 10 and h >= 10 and w < img.shape[1] and h < img.shape[0]):
        padding = 20  # 增加邊界填充
        x = max(0, x - padding)
        y = max(0, y - padding)
        w = min(img.shape[1] - x, w + 2*padding)
        h = min(img.shape[0] - y, h + 2*padding)
        roi = img[y:y+h, x:x+w]
        out_path = os.path.join(output_dir, f"template_{count}.png")
        cv2.imwrite(out_path, roi)
        template_paths_auto.append(out_path)
        print(f"✅ 已裁切模板: {out_path}")
        print(f"   位置: ({x}, {y}), 大小: {w}x{h}")
        count += 1
    else:
        print("❌ 不符合過濾條件")
print(f"\n共裁切出 {count} 個模板")

# === 2. 合併手動模板與自動模板 ===
template_paths = [template_path] + template_paths_auto

# === 3. 批次命中率統計 ===
hit_counts = {os.path.basename(t): 0 for t in template_paths}
max_match_values = {}
threshold = 0.5
for template_path in template_paths:
    template = cv2.imread(template_path, cv2.IMREAD_UNCHANGED)
    if template is None:
        continue
    if template.shape[2] == 4:
        template_gray = cv2.cvtColor(template, cv2.COLOR_BGRA2GRAY)
        mask = template[:, :, 3]
    else:
        template_gray = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY)
        mask = None
    th, tw = template_gray.shape[:2]
    screenshot = cv2.imread(screenshot_path, cv2.IMREAD_UNCHANGED)
    if screenshot is None or screenshot.shape[0] < th or screenshot.shape[1] < tw:
        continue
    if screenshot.shape[2] == 4:
        screenshot_gray = cv2.cvtColor(screenshot, cv2.COLOR_BGRA2GRAY)
    else:
        screenshot_gray = cv2.cvtColor(screenshot, cv2.COLOR_BGR2GRAY)
    if mask is not None:
        res = cv2.matchTemplate(screenshot_gray, template_gray, cv2.TM_CCOEFF_NORMED, mask=mask)
    else:
        res = cv2.matchTemplate(screenshot_gray, template_gray, cv2.TM_CCOEFF_NORMED)
    min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)
    max_match_values[os.path.basename(template_path)] = max_val
    print(f"\n比對結果 {os.path.basename(template_path)}:")
    print(f"最大匹配值: {max_val:.3f}")
    print(f"匹配位置: {max_loc}")
    if max_val >= threshold:
        hit_counts[os.path.basename(template_path)] += 1
        cv2.rectangle(screenshot, max_loc, (max_loc[0]+tw, max_loc[1]+th), (0,255,0), 2)
        cv2.imwrite(f"match_result_{os.path.basename(template_path)}", screenshot)
sorted_hits = sorted(hit_counts.items(), key=lambda x: x[1], reverse=True)
print("\n模板命中次數統計：")
for name, count in sorted_hits:
    print(f"{name}: {count} hits")

# === 4. 自動挑選最佳模板 ===
best_dir = "best_templates"
os.makedirs(best_dir, exist_ok=True)
best_templates = sorted(max_match_values.items(), key=lambda x: x[1], reverse=True)[:3]
print(f"\n自動挑選最大匹配值最高的前3張模板：")
for name, val in best_templates:
    src = os.path.join(os.path.dirname(template_paths[0]), name) if name == os.path.basename(template_path) else os.path.join(output_dir, name)
    dst = os.path.join(best_dir, name)
    shutil.copyfile(src, dst)
    print(f"{name} 匹配值: {val:.3f} 已複製到 {best_dir}/")
print("\n請直接使用 best_templates 資料夾裡的模板做後續辨識！") 