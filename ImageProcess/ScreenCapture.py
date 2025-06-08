# ImageProcess/ScreenCapture.py - 修正版

import pyautogui
import pygetwindow as gw
import cv2
import numpy as np

def capture_bluestacks():
    """✅ 修正版：使用正確的visible屬性"""
    # 找到模擬器視窗（根據標題）
    win = None
    
    # ✅ 基於搜索結果[6]的多種BlueStacks視窗標題匹配
    bluestacks_titles = [
        "BlueStacks App Player",
        "BlueStacks",
        "BlueStacks 5",
        "BlueStacks Keymap Overlay"
    ]
    
    for title in bluestacks_titles:
        windows = gw.getWindowsWithTitle(title)
        for w in windows:
            # ✅ 修正：使用visible而不是isVisible
            if w.visible:
                win = w
                print(f"✅ 找到BlueStacks視窗: {title}")
                break
        if win:
            break
    
    if win is None:
        print("❌ 找不到 BlueStacks 視窗")
        print("🔍 當前所有視窗標題:")
        all_titles = gw.getAllTitles()
        for title in all_titles:
            if title and "blue" in title.lower():
                print(f"   - {title}")
        return None
    
    try:
        # ✅ 基於搜索結果[8]的視窗屬性檢查
        print(f"📊 視窗信息: {win.title}")
        print(f"   位置: ({win.left}, {win.top})")
        print(f"   尺寸: {win.width} × {win.height}")
        print(f"   可見: {win.visible}")
        
        # 擷取該視窗範圍畫面
        x, y, width, height = win.left, win.top, win.width, win.height
        
        # ✅ 邊界檢查
        if width <= 0 or height <= 0:
            print("❌ 視窗尺寸無效")
            return None
        
        # ✅ 基於搜索結果[8]的截圖方法
        screenshot = pyautogui.screenshot(region=(x, y, width, height))
        img = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)
        
        print(f"✅ 截圖成功: {img.shape}")
        return img
        
    except Exception as e:
        print(f"❌ 截圖失敗: {e}")
        return None

def capture_bluestacks_safe():
    """✅ 安全版本：包含更多錯誤處理"""
    try:
        return capture_bluestacks()
    except Exception as e:
        print(f"❌ capture_bluestacks 執行失敗: {e}")
        return None

# ✅ 測試函數
def test_capture():
    """測試截圖功能"""
    print("🔍 測試BlueStacks截圖功能...")
    
    # 顯示所有視窗
    print("📋 所有視窗標題:")
    all_titles = gw.getAllTitles()
    for i, title in enumerate(all_titles):
        if title:  # 只顯示非空標題
            print(f"   {i+1:2d}. {title}")
    
    # 嘗試截圖
    img = capture_bluestacks_safe()
    if img is not None:
        # 保存測試截圖
        cv2.imwrite('test_screenshot.png', img)
        print("✅ 測試截圖已保存: test_screenshot.png")
        return True
    else:
        print("❌ 測試截圖失敗")
        return False

if __name__ == "__main__":
    test_capture()
