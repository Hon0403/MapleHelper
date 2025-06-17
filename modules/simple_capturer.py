# modules/simple_capturer.py - 使用統一ADB連接版本

import subprocess
import cv2
import numpy as np
import time
import threading
import os
from includes.adb_utils import ADBUtils  # ✅ 使用統一ADB工具
import io
from PIL import Image

class SimpleCapturer:
    """✅ 改進版捕捉器 - 優化捕捉頻率"""
    
    def __init__(self, config):
        self.config = config
        
        # ✅ 不再硬編碼ADB路徑，使用adb_utils.py統一管理
        self.adb_path = None
        self.device_id = None
        
        # 線程鎖
        self.capture_lock = threading.Lock()
        
        # 快取上次捕捉時間
        self.last_capture_time = 0
        self.min_capture_interval = 0.2  # 增加最小捕捉間隔到 0.2 秒（5 FPS）
        
        # 初始化ADB連接
        self._init_adb_connection()
    
    def _init_adb_connection(self):
        """✅ 使用adb_utils.py的統一連接管理"""
        self.device_id = ADBUtils.ensure_connection()
        
        if self.device_id:
            self.is_connected = True
            # 獲取實際使用的ADB路徑
            self.adb_path = ADBUtils.get_adb_path()
            print(f"✅ ADB連接成功: {self.device_id}")
            print(f"📍 使用ADB路徑: {self.adb_path}")
        else:
            self.is_connected = False
            print("❌ ADB連接失敗")
            
            # 顯示連接信息以便調試
            connection_info = ADBUtils.get_connection_info()
            print(f"📊 連接狀態: {connection_info}")
    
    def grab_frame(self):
        """✅ 改進版：優化捕捉頻率"""
        if not self.is_connected:
            # 嘗試重新建立連接
            print("🔄 嘗試重新建立ADB連接...")
            self._init_adb_connection()
            
            if not self.is_connected:
                print("❌ ADB未連接，無法捕捉畫面")
                return None
        
        # 檢查捕捉間隔
        current_time = time.time()
        if current_time - self.last_capture_time < self.min_capture_interval:
            return None
        
        # 線程安全保護
        with self.capture_lock:
            frame = self._capture_via_traditional_adb()
            if frame is not None:
                self.last_capture_time = current_time
            return frame
    
    def _capture_via_traditional_adb(self):
        """穩定版：使用臨時文件進行截圖"""
        max_retries = 3
        retry_delay = 0.8
        
        for attempt in range(max_retries):
            try:
                # 生成臨時文件名
                timestamp = int(time.time() * 1000)
                temp_path = f"/sdcard/screenshot_{timestamp}.png"
                local_path = f"temp_screenshot_{timestamp}.png"
                
                # 執行截圖
                success, _, stderr = ADBUtils.execute_command(
                    self.adb_path, self.device_id,
                    ['shell', 'screencap', '-p', temp_path],
                    timeout=8
                )
                
                if not success:
                    print(f"⚠️ 截圖失敗 (嘗試 {attempt + 1}/{max_retries}): {stderr}")
                    time.sleep(retry_delay)
                    continue
                
                # 拉取文件
                success, _, stderr = ADBUtils.execute_command(
                    self.adb_path, self.device_id,
                    ['pull', temp_path, local_path],
                    timeout=5
                )
                
                if not success:
                    print(f"⚠️ 拉取文件失敗 (嘗試 {attempt + 1}/{max_retries}): {stderr}")
                    time.sleep(retry_delay)
                    continue
                
                # 讀取圖片
                img = cv2.imread(local_path)
                if img is None:
                    print(f"⚠️ 圖片讀取失敗 (嘗試 {attempt + 1}/{max_retries})")
                    time.sleep(retry_delay)
                    continue
                
                # 清理文件
                try:
                    os.remove(local_path)
                    ADBUtils.execute_command(
                        self.adb_path, self.device_id,
                        ['shell', 'rm', temp_path],
                        timeout=2
                    )
                except:
                    pass
                
                print(f"✅ 截圖成功，尺寸: {img.shape}")
                return img
                
            except Exception as e:
                print(f"⚠️ 截圖過程異常 (嘗試 {attempt + 1}/{max_retries}): {e}")
                time.sleep(retry_delay)
        
        return None

    def _capture_via_temp_file(self):
        """備用方案：使用臨時文件進行截圖"""
        try:
            # 生成臨時文件名
            timestamp = int(time.time() * 1000)
            temp_path = f"/sdcard/screenshot_{timestamp}.png"
            local_path = f"temp_screenshot_{timestamp}.png"
            
            # 執行截圖
            success, _, stderr = ADBUtils.execute_command(
                self.adb_path, self.device_id,
                ['shell', 'screencap', '-p', temp_path],
                timeout=8
            )
            
            if not success:
                print(f"⚠️ 臨時文件截圖失敗: {stderr}")
                return None
            
            # 拉取文件
            success, _, stderr = ADBUtils.execute_command(
                self.adb_path, self.device_id,
                ['pull', temp_path, local_path],
                timeout=5
            )
            
            if not success:
                print(f"⚠️ 拉取臨時文件失敗: {stderr}")
                return None
            
            # 讀取圖片
            img = cv2.imread(local_path)
            
            # 清理文件
            try:
                os.remove(local_path)
                ADBUtils.execute_command(
                    self.adb_path, self.device_id,
                    ['shell', 'rm', temp_path],
                    timeout=2
                )
            except:
                pass
            
            return img
            
        except Exception as e:
            print(f"❌ 臨時文件截圖失敗: {e}")
            return None

    def _safe_imread(self, image_data):
        """從記憶體數據讀取圖片"""
        try:
            if isinstance(image_data, bytes):
                # 如果是字節數據，直接轉換
                img = Image.open(io.BytesIO(image_data))
            else:
                # 如果是文件路徑，讀取文件
                img = Image.open(image_data)
            return np.array(img)
        except Exception as e:
            print(f"❌ 圖片讀取失敗: {e}")
            return None

    def _cleanup_files_sync(self, temp_path, local_path):
        """同步清理檔案"""
        try:
            # 清理設備端檔案
            ADBUtils.execute_command(
                self.adb_path, self.device_id,
                ['shell', 'rm', '-f', temp_path],
                timeout=2
            )
            
            # 清理本地檔案
            if os.path.exists(local_path):
                try:
                    os.remove(local_path)
                except:
                    pass
        except:
            pass
    
    def test_adb_connection(self):
        """✅ 使用adb_utils.py測試連接"""
        if self.device_id:
            return ADBUtils.test_connection(self.device_id)
        return False
    
    def restart_adb_if_needed(self):
        """✅ 使用adb_utils.py重啟ADB服務"""
        print("🔄 重啟ADB服務...")
        success = ADBUtils.restart_adb_server()
        
        if success:
            # 重啟後重新初始化連接
            time.sleep(2)
            self._init_adb_connection()
        
        return success
    
    def get_device_info(self):
        """✅ 獲取設備信息"""
        if not self.is_connected:
            return None
        
        try:
            # 使用ADBUtils獲取設備屬性
            success, model, _ = ADBUtils.execute_command(
                self.adb_path, self.device_id,
                ['shell', 'getprop', 'ro.product.model']
            )
            
            success2, version, _ = ADBUtils.execute_command(
                self.adb_path, self.device_id,
                ['shell', 'getprop', 'ro.build.version.release']
            )
            
            return {
                'device_id': self.device_id,
                'model': model.strip() if success else 'Unknown',
                'android_version': version.strip() if success2 else 'Unknown',
                'connection_info': ADBUtils.get_connection_info()
            }
            
        except Exception as e:
            print(f"❌ 獲取設備信息失敗: {e}")
            return None
    
    def cleanup(self):
        """清理資源"""
        print("✅ 傳統ADB捕捉器已清理")
        # adb_utils.py會自動管理連接狀態，無需手動清理
    
    def get_capture_info(self):
        """✅ 獲取完整的捕捉信息"""
        return {
            'method': 'traditional_adb_with_unified_utils',
            'connected': self.is_connected,
            'device': self.device_id,
            'thread_safe': True,
            'adb_path': self.adb_path,
            'connection_info': ADBUtils.get_connection_info() if self.is_connected else None,
            'device_info': self.get_device_info()
        }
    
    def force_reconnect(self):
        """✅ 強制重新連接"""
        print("🔄 強制重新連接ADB...")
        
        # 使用adb_utils.py的強制重連功能
        self.device_id = ADBUtils.connect_to_bluestacks(force_reconnect=True)
        
        if self.device_id:
            self.is_connected = True
            self.adb_path = ADBUtils.get_adb_path()
            print(f"✅ 強制重連成功: {self.device_id}")
            return True
        else:
            self.is_connected = False
            print("❌ 強制重連失敗")
            return False

# ✅ 保持相容性
class EnhancedSimpleCapturer(SimpleCapturer):
    pass
