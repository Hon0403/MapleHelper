import cv2
import os

template_path = "test1.png"
screenshot_path = "detection_result_1749364777.png"

template = cv2.imread(template_path, cv2.IMREAD_UNCHANGED)
screenshot = cv2.imread(screenshot_path, cv2.IMREAD_UNCHANGED)

if template is None or screenshot is None:
    print("❌ 圖片讀取失敗")
    exit()

if template.shape[2] == 4:
    template_gray = cv2.cvtColor(template, cv2.COLOR_BGRA2GRAY)
    mask = template[:, :, 3]
else:
    template_gray = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY)
    mask = None

if screenshot.shape[2] == 4:
    screenshot_gray = cv2.cvtColor(screenshot, cv2.COLOR_BGRA2GRAY)
else:
    screenshot_gray = cv2.cvtColor(screenshot, cv2.COLOR_BGR2GRAY)

th, tw = template_gray.shape[:2]
sh, sw = screenshot_gray.shape[:2]

if sh < th or sw < tw:
    print("❌ 模板尺寸大於截圖，無法比對")
    exit()

# 用遮罩做 template matching
if mask is not None:
    res = cv2.matchTemplate(screenshot_gray, template_gray, cv2.TM_CCOEFF_NORMED, mask=mask)
else:
    res = cv2.matchTemplate(screenshot_gray, template_gray, cv2.TM_CCOEFF_NORMED)

min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)
print(f"{os.path.basename(template_path)} vs {os.path.basename(screenshot_path)}: {max_val:.3f}")

# 可視化比對結果
if max_val > 0.5:
    top_left = max_loc
    bottom_right = (top_left[0] + tw, top_left[1] + th)
    cv2.rectangle(screenshot, top_left, bottom_right, (0, 0, 255), 2)
    cv2.imwrite("debug_match_result.png", screenshot)
    print("已輸出比對結果圖：debug_match_result.png")