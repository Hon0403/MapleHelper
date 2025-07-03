# modules/simple_capturer_clean.py - 簡化版視窗捕獲器（移除多視窗邏輯）

import win32gui, win32ui, win32con
import numpy as np
import cv2
import time
import ctypes
from includes.log_utils import get_logger
from includes.config_utils import create_config_section

# PrintWindow API 宣告 - 修復版
try:
    _PrintWindow = win32gui.PrintWindow
except AttributeError:
    # 用 ctypes 取得 PrintWindow
    user32 = ctypes.windll.user32
    _PrintWindow = lambda hwnd, hdc, flags: user32.PrintWindow(hwnd, hdc, flags)

# PW_RENDERFULLCONTENT 常數
try:
    PW_RENDERFULLCONTENT = win32con.PW_RENDERFULLCONTENT
except AttributeError:
    PW_RENDERFULLCONTENT = 0x00000002

class SimpleCapturer:
    """簡化版視窗捕獲器 - 專注於楓之谷 Worlds"""
    
    def __init__(self, config=None):
        self.logger = get_logger("SimpleCapturer")
        self.config = config
        
        # 從配置讀取設定
        if config:
            config_section = create_config_section(config, 'capturer')
            self.window_title = config_section.get_string('window_title', 'MapleStory Worlds-Artale (繁體中文版)')
            self.capture_mode = config_section.get_string('capture_mode', 'window')
        else:
            self.window_title = 'MapleStory Worlds-Artale (繁體中文版)'
            self.capture_mode = 'window'
        
        # 基本屬性
        self.frame_cache = None
        self.cache_timestamp = 0
        self.error_count = 0
        self.window_handle = None
        
        # GDI 資源監控
        self.gdi_error_count = 0
        self.last_gdi_cleanup = time.time()
        self.cleanup_interval = 30  # 每30秒檢查一次
        
        # 初始化視窗
        self._init_window()
        
        self.logger.info("✅ 簡化版視窗捕獲器初始化完成")
    
    def _init_window(self):
        """初始化視窗捕獲"""
        try:
            if self.window_title:
                self.window_handle = self._find_window(self.window_title)
                if self.window_handle:
                    self.logger.info(f"✅ 找到目標視窗: {self.window_title}")
                else:
                    self.logger.warning(f"❌ 找不到視窗: {self.window_title}")
                    self._show_available_windows()
            else:
                self.logger.warning("❌ 未設定視窗標題")
                
        except Exception as e:
            self.logger.error(f"視窗初始化失敗: {e}")
    
    def _find_window(self, window_title):
        """尋找指定標題的視窗"""
        try:
            def enum_windows_callback(hwnd, windows):
                if win32gui.IsWindowVisible(hwnd):
                    title = win32gui.GetWindowText(hwnd)
                    if window_title.lower() in title.lower():
                        windows.append(hwnd)
                return True
            
            windows = []
            win32gui.EnumWindows(enum_windows_callback, windows)
            if windows:
                return windows[0]
            return None
        except Exception as e:
            self.logger.error(f"尋找視窗失敗: {e}")
            return None
    
    def _show_available_windows(self):
        """顯示系統中可用的視窗"""
        try:
            self.logger.info("🪟 系統中的可見視窗:")
            
            def enum_windows_callback(hwnd, windows):
                if win32gui.IsWindowVisible(hwnd):
                    title = win32gui.GetWindowText(hwnd)
                    if title.strip():  # 只顯示有標題的視窗
                        windows.append(title)
                return True
            
            windows = []
            win32gui.EnumWindows(enum_windows_callback, windows)
            
            # 過濾出可能的遊戲視窗
            game_windows = [w for w in windows if any(keyword in w.lower() for keyword in 
                           ['maple', 'artale', 'worlds'])]
            
            if game_windows:
                self.logger.info("   可能的遊戲視窗:")
                for window in game_windows[:10]:  # 只顯示前10個
                    self.logger.info(f"     - {window}")
            else:
                self.logger.info("   未找到明顯的遊戲視窗")
                
        except Exception as e:
            self.logger.error(f"顯示可用視窗失敗: {e}")
    
    def force_reconnect(self):
        """強制重新連接視窗"""
        self.logger.info(f"🔄 強制重新連接視窗: {self.window_title}")
        self.error_count = 0
        self.frame_cache = None
        
        if self.window_title:
            self.window_handle = self._find_window(self.window_title)
            if self.window_handle:
                self.logger.info(f"✅ 重新連接成功: {self.window_title}")
                return True
            else:
                self.logger.warning(f"❌ 重新連接失敗: 找不到視窗 {self.window_title}")
                self._show_available_windows()
                return False
        else:
            self.logger.warning("❌ 重新連接失敗: 未設定視窗標題")
            return False
    
    def _capture_window(self, hwnd):
        """使用 PrintWindow 捕獲視窗"""
        hwndDC = None
        mfcDC = None
        saveDC = None
        saveBitMap = None
        
        try:
            # 預檢查：確保視窗仍然有效
            if not win32gui.IsWindow(hwnd):
                self.logger.warning("視窗句柄無效，嘗試重新連接")
                if self.force_reconnect():
                    hwnd = self.window_handle
                else:
                    return None
            
            # 獲取視窗大小
            try:
                left, top, right, bottom = win32gui.GetWindowRect(hwnd)
                width = right - left
                height = bottom - top
            except Exception as e:
                self.logger.warning(f"獲取視窗大小失敗: {e}")
                return None
            
            if width <= 0 or height <= 0:
                self.logger.warning(f"視窗尺寸無效: {width}x{height}")
                return None
            
            # 建立GDI資源
            hwndDC = win32gui.GetWindowDC(hwnd)
            if not hwndDC:
                raise Exception("GetWindowDC failed")
            
            mfcDC = win32ui.CreateDCFromHandle(hwndDC)
            if not mfcDC:
                raise Exception("CreateDCFromHandle failed")
            
            saveDC = mfcDC.CreateCompatibleDC()
            if not saveDC:
                raise Exception("CreateCompatibleDC failed")
            
            saveBitMap = win32ui.CreateBitmap()
            if not saveBitMap:
                raise Exception("CreateBitmap failed")
            
            saveBitMap.CreateCompatibleBitmap(mfcDC, width, height)
            saveDC.SelectObject(saveBitMap)
            
            # 使用 PrintWindow 抓圖
            try:
                # 嘗試使用 win32con 的常數
                result = _PrintWindow(hwnd, saveDC.GetSafeHdc(), win32con.PW_RENDERFULLCONTENT)
            except AttributeError:
                # 如果沒有 PW_RENDERFULLCONTENT，使用數值 2
                result = _PrintWindow(hwnd, saveDC.GetSafeHdc(), 2)
            except Exception as e:
                raise Exception(f"PrintWindow API call failed - {e}")
            
            if result != 1:
                raise Exception(f"PrintWindow 返回失敗代碼: {result}")
            
            # 獲取位圖資料
            bmpinfo = saveBitMap.GetInfo()
            bmpstr = saveBitMap.GetBitmapBits(True)
            img = np.frombuffer(bmpstr, dtype='uint8')
            img.shape = (height, width, 4)
            
            # 轉換為 BGR 格式
            img = img[..., :3]
            img = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
            
            # 重置GDI錯誤計數
            self.gdi_error_count = 0
            return img
                
        except Exception as e:
            self.logger.error(f"PrintWindow 捕獲失敗: {e}")
            
            # 統計 GDI 相關錯誤
            if any(keyword in str(e) for keyword in ["CreateCompatibleDC", "CreateBitmap", "GetWindowDC"]):
                self.gdi_error_count += 1
                if self.gdi_error_count >= 3:
                    self.logger.warning("連續 GDI 錯誤，執行強制清理")
                    self._force_gdi_cleanup()
            return None
            
        finally:
            # 資源清理
            resources_released = []
            
            if saveBitMap:
                try:
                    win32gui.DeleteObject(saveBitMap.GetHandle())
                    resources_released.append("BitMap")
                except:
                    pass
            
            if saveDC:
                try:
                    saveDC.DeleteDC()
                    resources_released.append("SaveDC")
                except:
                    pass
            
            if mfcDC:
                try:
                    mfcDC.DeleteDC()
                    resources_released.append("MfcDC")
                except:
                    pass
            
            if hwndDC:
                try:
                    win32gui.ReleaseDC(hwnd, hwndDC)
                    resources_released.append("WindowDC")
                except:
                    pass
            
            # 資源已釋放，不再輸出日誌以減少噪音
    
    def grab_frame(self):
        """抓取視窗畫面"""
        try:
            current_time = time.time()
            
            # 定期檢查 GDI 資源狀況
            if current_time - self.last_gdi_cleanup > self.cleanup_interval:
                self._check_gdi_resources()
                self.last_gdi_cleanup = current_time
            
            if not self.window_handle:
                return self.frame_cache
            
            frame = self._capture_window(self.window_handle)
            if frame is not None:
                self.frame_cache = frame
                self.cache_timestamp = time.time()
                self.error_count = 0
                return frame
            else:
                return self.frame_cache
            
        except Exception as e:
            self.error_count += 1
            if self.error_count % 10 == 0:
                self.logger.error(f"抓取畫面失敗: {e}")
            return self.frame_cache
    
    def set_window_title(self, window_title):
        """設置要捕獲的視窗標題"""
        try:
            self.logger.info(f"🔄 設置視窗標題: '{self.window_title}' -> '{window_title}'")
            self.window_title = window_title
            self.capture_mode = 'window'
            self.window_handle = self._find_window(window_title)
            if self.window_handle:
                self.logger.info(f"已設置視窗捕獲: {window_title}")
                return True
            self.logger.error(f"無法找到視窗: {window_title}")
            return False
        except Exception as e:
            self.logger.error(f"設置視窗標題失敗: {e}")
            return False
    
    def get_screen_resolution(self):
        """獲取視窗解析度"""
        if self.window_handle:
            try:
                left, top, right, bottom = win32gui.GetWindowRect(self.window_handle)
                return {
                    'width': right - left,
                    'height': bottom - top,
                    'left': left,
                    'top': top
                }
            except:
                pass
        return {'width': 1920, 'height': 1080, 'left': 0, 'top': 0}
    
    def _check_gdi_resources(self):
        """檢查 GDI 資源使用情況"""
        try:
            import psutil
            current_process = psutil.Process()
            gdi_count = current_process.num_handles()
            
            if gdi_count > 1000:
                self.logger.warning(f"GDI 物件數量過多: {gdi_count}，執行清理")
                self._force_gdi_cleanup()
        except:
            pass
    
    def _force_gdi_cleanup(self):
        """強制 GDI 資源清理"""
        try:
            import gc
            gc.collect()
            self.gdi_error_count = 0
            self.logger.info("✅ GDI 資源清理完成")
        except Exception as e:
            self.logger.error(f"GDI 清理失敗: {e}")
    
    def cleanup(self):
        """清理資源"""
        self.frame_cache = None
        self.window_handle = None
        self._force_gdi_cleanup()
        self.logger.info("✅ 簡化版捕獲器資源已清理")
    
    def get_capture_info(self):
        """獲取捕獲資訊"""
        is_connected = (self.window_handle is not None and 
                       win32gui.IsWindow(self.window_handle) if self.window_handle else False)
        
        return {
            'window_title': self.window_title,
            'capture_mode': self.capture_mode,
            'window_handle': self.window_handle,
            'is_connected': is_connected,
            'has_cache': self.frame_cache is not None,
            'error_count': self.error_count,
            'gdi_error_count': self.gdi_error_count
        } 