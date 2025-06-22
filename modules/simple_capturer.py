# modules/simple_capturer.py - 使用統一ADB連接版本

import subprocess
import cv2
import numpy as np
import time
import threading
import os
from includes.adb_utils import ADBUtils  # ✅ 使用統一ADB工具
from includes.config_utils import create_config_section
from includes.log_utils import get_logger
import io
from PIL import Image
import queue

class SimpleCapturer:
    """✅ 效能優化版捕捉器 - 智能緩存與異步處理"""
    
    def __init__(self, config=None):
        # ✅ 使用共用工具初始化
        self.logger = get_logger("SimpleCapturer")
        
        # ✅ 使用 ConfigSection 簡化配置讀取
        if config:
            config_section = create_config_section(config, 'capturer')
            self.adb_path = config_section.get_string('adb_path', 'adb')
            self.device_id = config_section.get_string('device_id', '')
            self.cache_duration = config_section.get_float('cache_duration', 0.1)
            self.min_capture_interval = config_section.get_float('min_capture_interval', 0.05)
            self.max_capture_interval = config_section.get_float('max_capture_interval', 0.2)
            self.max_errors = config_section.get_int('max_errors', 5)
            self.error_reset_time = config_section.get_float('error_reset_time', 10)
        else:
            # 設置默認配置
            self.adb_path = 'adb'
            self.device_id = ''
            self.cache_duration = 0.1  # 降低到 100ms，提高響應性
            self.min_capture_interval = 0.05  # 降低到 50ms (20 FPS)
            self.max_capture_interval = 0.2   # 最大 200ms (5 FPS)
            self.max_errors = 5
            self.error_reset_time = 10  # 10秒後重置錯誤計數
        
        # ✅ 效能優化：改進緩存機制
        self.frame_cache = None
        self.cache_timestamp = 0
        self.frame_queue = queue.Queue(maxsize=3)  # 增加佇列大小
        self.result_queue = queue.Queue(maxsize=5)
        
        # 線程鎖
        self.capture_lock = threading.Lock()
        
        # ✅ 效能優化：智能捕捉間隔
        self.last_capture_time = 0
        self.current_capture_interval = self.min_capture_interval
        
        # ✅ 效能優化：添加錯誤計數
        self.error_count = 0
        
        # 初始化ADB連接
        self._init_adb_connection()
        
        # 啟動異步截圖
        if self.is_connected:
            self._start_async_capture()
    
    def _init_adb_connection(self):
        """✅ 使用adb_utils.py的統一連接管理"""
        self.device_id = ADBUtils.ensure_connection()
        
        if self.device_id:
            self.is_connected = True
            # 獲取實際使用的ADB路徑
            self.adb_path = ADBUtils.get_adb_path()
            self.logger.init_success("ADB連接")
        else:
            self.is_connected = False
            self.logger.error("ADB連接失敗")
            
            # 顯示連接信息以便調試
            connection_info = ADBUtils.get_connection_info()
            self.logger.info(f"連接狀態: {connection_info}")
    
    def _start_async_capture(self):
        """啟動異步截圖"""
        self.capture_thread = threading.Thread(
            target=self._async_capture_worker,
            daemon=True
        )
        self.capture_thread.start()
    
    def _async_capture_worker(self):
        """✅ 效能優化版異步截圖工作執行緒"""
        consecutive_errors = 0
        last_error_time = 0
        
        while True:
            try:
                current_time = time.time()
                
                # ✅ 效能優化：動態調整捕捉頻率
                if consecutive_errors > 3:
                    # 錯誤較多時降低頻率
                    self.current_capture_interval = min(
                        self.current_capture_interval * 1.2, 
                        self.max_capture_interval
                    )
                elif consecutive_errors == 0 and current_time - last_error_time > 5:
                    # 穩定時提高頻率
                    self.current_capture_interval = max(
                        self.current_capture_interval * 0.9, 
                        self.min_capture_interval
                    )
                
                # 檢查是否需要更新緩存
                if (self.frame_cache is None or 
                    current_time - self.cache_timestamp >= self.cache_duration):
                    
                    # ✅ 效能優化：使用更快的截圖方法
                    frame = self._fast_screenshot()
                    
                    if frame is not None:
                        self.frame_cache = frame
                        self.cache_timestamp = current_time
                        consecutive_errors = 0  # 重置錯誤計數
                        
                        # 放入結果佇列
                        try:
                            self.result_queue.put(frame, block=False)
                        except queue.Full:
                            # 佇列滿時移除舊幀
                            try:
                                self.result_queue.get_nowait()
                                self.result_queue.put(frame, block=False)
                            except:
                                pass
                    else:
                        consecutive_errors += 1
                        last_error_time = current_time
                
                # ✅ 效能優化：動態睡眠
                sleep_time = max(0.01, self.current_capture_interval)
                time.sleep(sleep_time)
                
            except Exception as e:
                consecutive_errors += 1
                last_error_time = time.time()
                self.logger.error("異步截圖失敗", e)
                time.sleep(0.1)
    
    def _fast_screenshot(self):
        """✅ 效能優化：快速截圖方法"""
        try:
            # 使用 exec-out 避免臨時文件
            result = subprocess.run([
                self.adb_path, '-s', self.device_id, 
                'exec-out', 'screencap', '-p'
            ], capture_output=True, timeout=2)  # 降低超時時間
            
            if result.returncode == 0 and result.stdout:
                # 直接使用 numpy 讀取圖片數據
                image_data = np.frombuffer(result.stdout, dtype=np.uint8)
                frame = cv2.imdecode(image_data, cv2.IMREAD_COLOR)
                
                if frame is not None:
                    return frame
            
            return None
            
        except subprocess.TimeoutExpired:
            self.logger.warning("截圖超時")
            return None
        except Exception as e:
            self.logger.error("快速截圖失敗", e)
            return None
    
    def grab_frame(self):
        """✅ 效能優化版：智能緩存和錯誤處理"""
        try:
            current_time = time.time()
            
            # 檢查緩存是否有效
            if (self.frame_cache is not None and 
                current_time - self.cache_timestamp < self.cache_duration):
                return self.frame_cache
            
            # 從結果佇列獲取最新幀
            try:
                frame = self.result_queue.get_nowait()
                self.frame_cache = frame
                self.cache_timestamp = current_time
                return frame
            except queue.Empty:
                # 佇列為空時返回緩存
                return self.frame_cache
            
        except Exception as e:
            self.error_count += 1
            if self.error_count % 10 == 0:  # 每10次錯誤才打印一次
                self.logger.error("獲取畫面失敗", e)
            return None
    
    def _cleanup(self):
        """清理資源"""
        try:
            # 清空佇列
            while not self.frame_queue.empty():
                self.frame_queue.get_nowait()
            while not self.result_queue.empty():
                self.result_queue.get_nowait()
            
            # 清理緩存
            self.frame_cache = None
            
        except Exception as e:
            self.logger.error("清理資源失敗", e)
    
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
                print(f"❌ 截圖異常 (嘗試 {attempt + 1}/{max_retries}): {e}")
                time.sleep(retry_delay)
        
        return None
    
    def _capture_via_temp_file(self):
        """✅ 效能優化：改進的臨時文件截圖"""
        try:
            # 使用更短的超時時間
            result = subprocess.run([
                self.adb_path, '-s', self.device_id, 
                'shell', 'screencap', '-p', '/sdcard/temp_screen.png'
            ], capture_output=True, timeout=3)
            
            if result.returncode != 0:
                return None
            
            # 快速拉取
            result = subprocess.run([
                self.adb_path, '-s', self.device_id, 
                'pull', '/sdcard/temp_screen.png', 'temp_screen.png'
            ], capture_output=True, timeout=3)
            
            if result.returncode == 0:
                img = cv2.imread('temp_screen.png')
                # 立即清理
                try:
                    os.remove('temp_screen.png')
                    subprocess.run([
                        self.adb_path, '-s', self.device_id, 
                        'shell', 'rm', '/sdcard/temp_screen.png'
                    ], capture_output=True, timeout=1)
                except:
                    pass
                return img
            
            return None
            
        except Exception as e:
            print(f"❌ 臨時文件截圖失敗: {e}")
            return None
    
    def _safe_imread(self, image_data):
        """✅ 效能優化：安全的圖片讀取"""
        try:
            # 使用 numpy 直接處理
            nparr = np.frombuffer(image_data, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            return img
        except Exception as e:
            print(f"❌ 圖片讀取失敗: {e}")
            return None
    
    def _cleanup_files_sync(self, temp_path, local_path):
        """✅ 效能優化：同步文件清理"""
        try:
            # 並行清理本地和遠程文件
            local_cleanup = threading.Thread(
                target=lambda: os.remove(local_path) if os.path.exists(local_path) else None
            )
            remote_cleanup = threading.Thread(
                target=lambda: subprocess.run([
                    self.adb_path, '-s', self.device_id, 'shell', 'rm', temp_path
                ], capture_output=True, timeout=1)
            )
            
            local_cleanup.start()
            remote_cleanup.start()
            
            local_cleanup.join(timeout=1)
            remote_cleanup.join(timeout=1)
            
        except Exception as e:
            print(f"⚠️ 文件清理失敗: {e}")
    
    def test_adb_connection(self):
        """測試ADB連接"""
        try:
            result = subprocess.run([
                self.adb_path, '-s', self.device_id, 'shell', 'echo', 'test'
            ], capture_output=True, timeout=2)
            return result.returncode == 0
        except:
            return False
    
    def restart_adb_if_needed(self):
        """✅ 效能優化：智能重啟ADB"""
        if self.error_count > self.max_errors:
            print("🔄 錯誤過多，嘗試重啟ADB連接...")
            try:
                self._init_adb_connection()
                self.error_count = 0
                return True
            except Exception as e:
                print(f"❌ 重啟ADB失敗: {e}")
                return False
        return True
    
    def get_device_info(self):
        """獲取設備信息"""
        try:
            result = subprocess.run([
                self.adb_path, '-s', self.device_id, 'shell', 'getprop', 'ro.product.model'
            ], capture_output=True, text=True, timeout=2)
            
            if result.returncode == 0:
                return result.stdout.strip()
            return "Unknown"
            
        except Exception as e:
            print(f"❌ 獲取設備信息失敗: {e}")
            return "Unknown"
    
    def get_screen_resolution(self):
        """✅ 效能優化：獲取螢幕解析度"""
        try:
            result = subprocess.run([
                self.adb_path, '-s', self.device_id, 'shell', 'wm', 'size'
            ], capture_output=True, text=True, timeout=2)
            
            if result.returncode == 0:
                size_str = result.stdout.strip()
                if 'Physical size:' in size_str:
                    size_part = size_str.split('Physical size:')[1].strip()
                    width, height = map(int, size_part.split('x'))
                    return width, height
            return None
            
        except Exception as e:
            print(f"❌ 獲取螢幕解析度失敗: {e}")
            return None
    
    def cleanup(self):
        """清理資源"""
        self._cleanup()
    
    def get_capture_info(self):
        """✅ 效能優化：獲取捕捉器信息"""
        return {
            'is_connected': self.is_connected,
            'device_id': self.device_id,
            'error_count': self.error_count,
            'current_capture_interval': self.current_capture_interval,
            'cache_duration': self.cache_duration,
            'queue_size': self.result_queue.qsize(),
            'has_cached_frame': self.frame_cache is not None
        }
    
    def force_reconnect(self):
        """強制重新連接"""
        try:
            print("🔄 強制重新連接ADB...")
            self._init_adb_connection()
            self.error_count = 0
            return self.is_connected
        except Exception as e:
            print(f"❌ 強制重連失敗: {e}")
            return False

# ✅ 保持相容性
class EnhancedSimpleCapturer(SimpleCapturer):
    """✅ 效能優化：增強版捕捉器"""
    
    def __init__(self, config=None):
        super().__init__(config)
        
        # 添加更多效能優化
        self.frame_history = []  # 幀歷史
        self.max_history = 5     # 最大歷史幀數
        
        # 添加效能監控
        self.capture_times = []
        self.max_capture_times = 10
    
    def grab_frame(self):
        """✅ 效能優化：增強版幀獲取"""
        start_time = time.time()
        
        frame = super().grab_frame()
        
        # 記錄捕捉時間
        capture_time = time.time() - start_time
        self.capture_times.append(capture_time)
        if len(self.capture_times) > self.max_capture_times:
            self.capture_times.pop(0)
        
        # 添加到歷史
        if frame is not None:
            self.frame_history.append(frame)
            if len(self.frame_history) > self.max_history:
                self.frame_history.pop(0)
        
        return frame
    
    def get_performance_stats(self):
        """獲取效能統計"""
        if not self.capture_times:
            return {}
        
        return {
            'avg_capture_time': sum(self.capture_times) / len(self.capture_times),
            'max_capture_time': max(self.capture_times),
            'min_capture_time': min(self.capture_times),
            'history_size': len(self.frame_history)
        }
