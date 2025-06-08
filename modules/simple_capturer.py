# modules/simple_capturer.py - 使用統一ADB連接版本

import subprocess
import cv2
import numpy as np
import time
import threading
import os
from includes.adb_utils import ADBUtils  # ✅ 使用統一ADB工具

class SimpleCapturer:
    """簡化版捕捉器 - 使用統一ADB連接"""
    
    def __init__(self, config):
        self.config = config
        
        # ✅ 不再硬編碼ADB路徑，使用adb_utils.py統一管理
        self.adb_path = None
        self.device_id = None
        
        # 線程鎖
        self.capture_lock = threading.Lock()
        
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
        """使用傳統ADB截圖 - 穩定無衝突"""
        if not self.is_connected:
            # 嘗試重新建立連接
            print("🔄 嘗試重新建立ADB連接...")
            self._init_adb_connection()
            
            if not self.is_connected:
                print("❌ ADB未連接，無法捕捉畫面")
                return None
        
        # 線程安全保護
        with self.capture_lock:
            return self._capture_via_traditional_adb()
    
    def _capture_via_traditional_adb(self):
        """✅ 修正版：只在失敗時輸出日誌"""
        try:
            temp_path = "/sdcard/screenshot.png"
            local_path = "temp_screenshot.png"

            # 1. 截圖（移除成功日誌）
            success, stdout, stderr = ADBUtils.execute_command(
                self.adb_path, self.device_id,
                ['shell', 'screencap', '-p', temp_path],
                timeout=3
            )

            if not success:
                print(f"❌ ADB截圖失敗: {stderr}")  # ✅ 只在失敗時輸出
                if "device not found" in stderr or "device offline" in stderr:
                    print("🔄 設備離線，嘗試重新連接...")
                    self._init_adb_connection()
                return None

            # 2. 拉取檔案（移除成功日誌）
            success, stdout, stderr = ADBUtils.execute_command(
                self.adb_path, self.device_id,
                ['pull', temp_path, local_path],
                timeout=3
            )

            if not success:
                print(f"❌ ADB拉取失敗: {stderr}")  # ✅ 只在失敗時輸出
                return None

            # 3. 讀取圖片
            if os.path.exists(local_path):
                img = cv2.imread(local_path)
                
                # 清理檔案
                ADBUtils.execute_command(
                    self.adb_path, self.device_id,
                    ['shell', 'rm', temp_path]
                )
                os.remove(local_path)

                if img is not None:
                    # ✅ 移除成功輸出，靜默返回
                    return img
                else:
                    print("❌ 圖片讀取失敗")  # ✅ 只在失敗時輸出
                    return None
            else:
                print("❌ 本地檔案不存在")  # ✅ 只在失敗時輸出
                return None

        except Exception as e:
            print(f"❌ ADB截圖異常: {e}")  # ✅ 只在異常時輸出
            return None
    
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
