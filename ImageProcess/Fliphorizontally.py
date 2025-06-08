# 圖片轉向和隨機裁剪
import os
import random
import cv2
import numpy as np

def random_crop(image, crop_ratio=0.6, std_threshold=5):
    h, w = image.shape[:2]
    ch, cw = int(h * crop_ratio), int(w * crop_ratio)

    if h < ch or w < cw:
        return None

    for _ in range(10):  # 最多嘗試10次尋找有效裁剪
        y1 = random.randint(0, h - ch)
        x1 = random.randint(0, w - cw)
        crop = image[y1:y1 + ch, x1:x1 + cw]
        gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
        if np.std(gray) >= std_threshold:
            return crop

    return None  # 裁了10次都無效才放棄

def flip_templates_left_to_right(input_dir: str, output_dir: str, roi_output_dir: str, flipped_roi_output_dir: str):
    os.makedirs(output_dir, exist_ok=True)
    os.makedirs(roi_output_dir, exist_ok=True)
    os.makedirs(flipped_roi_output_dir, exist_ok=True)

    for filename in os.listdir(input_dir):
        if filename.lower().endswith(('.png', '.jpg', '.jpeg')):
            input_path = os.path.join(input_dir, filename)
            base_name = os.path.splitext(filename)[0]
            image = cv2.imread(input_path, cv2.IMREAD_COLOR)
            if image is None:
                print(f"❌ 無法讀取圖像: {filename}")
                continue

            roi = random_crop(image, crop_ratio=0.6)
            if roi is not None:
                roi_path = os.path.join(roi_output_dir, f"{base_name}_roi_orig.png")
                cv2.imwrite(roi_path, roi)
                print(f"🎯 已產生原圖隨機裁切模板: {roi_path}")
            else:
                print(f"⚠️ 無法產生原圖裁切模板: {filename}")

            flipped_image = cv2.flip(image, 1)
            flipped_path = os.path.join(output_dir, f"{base_name}_flipped.png")
            cv2.imwrite(flipped_path, flipped_image)
            print(f"✅ 已翻轉並儲存: {flipped_path}")

            flipped_roi = random_crop(flipped_image, crop_ratio=0.6)
            if flipped_roi is not None:
                flipped_roi_path = os.path.join(flipped_roi_output_dir, f"{base_name}_roi_flipped.png")
                cv2.imwrite(flipped_roi_path, flipped_roi)
                print(f"🎯 已產生翻轉圖隨機裁切模板: {flipped_roi_path}")
            else:
                print(f"⚠️ 無法產生翻轉裁切模板: {filename}")



# ✅ 使用範例
input_templates_dir = "templates/monsters"
output_flipped_dir = "templates/monsters_flipped"
roi_output_dir = "templates/monsters_flipped"
flipped_roi_output_dir = "templates/monsters_flipped"

flip_templates_left_to_right(input_templates_dir, output_flipped_dir, roi_output_dir, flipped_roi_output_dir)
