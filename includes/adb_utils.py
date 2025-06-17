# includes/adb_utils.py - 共用ADB連接管理函數庫

import subprocess
import time
import re
import os
import sys
from typing import Tuple, List, Optional, Dict, Any

class ADBUtils:
    """✅ 基於搜索結果[3][5]的純粹ADB連接管理共用函數庫"""
    
    # 類變數：連接狀態管理
    _current_device_id = None
    _connection_verified = False
    _last_check_time = 0
    _check_interval = 60
    _adb_path = None

    @staticmethod
    def get_adb_path() -> str:
        """✅ 獲取ADB路徑"""
        if ADBUtils._adb_path:
            return ADBUtils._adb_path

        try:
            # 獲取程式主目錄
            if getattr(sys, 'frozen', False):
                main_dir = os.path.dirname(sys.executable)
            elif '__file__' in globals():
                main_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            else:
                main_dir = os.getcwd()

<<<<<<< HEAD
            main_dir_adb = os.path.join(main_dir, "adb.exe")
            
            if os.path.exists(main_dir_adb):
                print(f"✅ 找到adb.exe: {main_dir_adb}")
                ADBUtils._adb_path = main_dir_adb
                return main_dir_adb
            else:
                print(f"❌ adb.exe不存在: {main_dir_adb}")
=======
            main_dir_adb = os.path.join(main_dir, "HD-Adb.exe")
            
            if os.path.exists(main_dir_adb):
                print(f"✅ 找到HD-Adb.exe: {main_dir_adb}")
                ADBUtils._adb_path = main_dir_adb
                return main_dir_adb
            else:
                print(f"❌ HD-Adb.exe不存在: {main_dir_adb}")
>>>>>>> 0ff736d04a6e034a0b49bbf5875afbe4eecd9665
                ADBUtils._adb_path = main_dir_adb
                return main_dir_adb

        except Exception as e:
            print(f"❌ 獲取ADB路徑失敗: {e}")
<<<<<<< HEAD
            fallback_path = os.path.join(os.getcwd(), "adb.exe")
=======
            fallback_path = os.path.join(os.getcwd(), "HD-Adb.exe")
>>>>>>> 0ff736d04a6e034a0b49bbf5875afbe4eecd9665
            ADBUtils._adb_path = fallback_path
            return fallback_path

    @staticmethod
    def execute_command(adb_path: str = None, device_id: str = "", 
                       command: List[str] = [], timeout: int = 5) -> Tuple[bool, str, str]:
        """✅ 執行ADB命令的統一接口"""
        if adb_path is None:
            adb_path = ADBUtils.get_adb_path()

        if not os.path.exists(adb_path):
<<<<<<< HEAD
            return False, "", f"adb.exe不存在: {adb_path}"
=======
            return False, "", f"HD-Adb.exe不存在: {adb_path}"
>>>>>>> 0ff736d04a6e034a0b49bbf5875afbe4eecd9665

        try:
            if device_id:
                cmd = [adb_path, '-s', device_id] + command
            else:
                cmd = [adb_path] + command

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
            success = result.returncode == 0
            return success, result.stdout, result.stderr

        except subprocess.TimeoutExpired:
            return False, "", "命令超時"
        except FileNotFoundError:
<<<<<<< HEAD
            return False, "", f"adb.exe不存在或無法執行: {adb_path}"
=======
            return False, "", f"HD-Adb.exe不存在或無法執行: {adb_path}"
>>>>>>> 0ff736d04a6e034a0b49bbf5875afbe4eecd9665
        except Exception as e:
            return False, "", str(e)

    @staticmethod
    def execute_adb_command(device_id: str, shell_command: str) -> bool:
        """✅ 基於搜索結果[3]的shell命令執行"""
        try:
            success, stdout, stderr = ADBUtils.execute_command(
                device_id=device_id,
                command=['shell', shell_command]
            )
            return success
        except Exception as e:
            print(f"❌ shell命令執行失敗: {e}")
            return False

    @staticmethod
    def find_bluestacks_device() -> Optional[str]:
        """✅ BlueStacks設備檢測"""
        adb_path = ADBUtils.get_adb_path()
        
        if not os.path.exists(adb_path):
<<<<<<< HEAD
            print(f"❌ adb.exe不存在: {adb_path}")
=======
            print(f"❌ HD-Adb.exe不存在: {adb_path}")
>>>>>>> 0ff736d04a6e034a0b49bbf5875afbe4eecd9665
            return None

        try:
            print("🔍 搜尋BlueStacks設備...")
            
            # 檢查ADB devices列表
            success, stdout, stderr = ADBUtils.execute_command(
                adb_path, "", ['devices'], timeout=10
            )

            if success:
                lines = stdout.strip().split('\n')[1:]
                for line in lines:
                    if line.strip() and 'device' in line:
                        device_id = line.split()[0]
                        if '127.0.0.1:' in device_id:
                            print(f"✅ 從devices列表找到: {device_id}")
                            return device_id

            # 端口掃描
            print("🔍 掃描BlueStacks常用端口...")
            bluestacks_ports = [5555, 5556, 5557, 5558, 5559]
            
            for port in bluestacks_ports:
                device_id = f"127.0.0.1:{port}"
                
                # 嘗試連接
                connect_success, _, _ = ADBUtils.execute_command(
                    adb_path, "", ['connect', device_id], timeout=5
                )
                
                # 測試連接
                if ADBUtils.test_connection(device_id):
                    print(f"✅ 成功連接BlueStacks端口: {port}")
                    return device_id
                
                time.sleep(0.5)

            print("❌ 無法找到BlueStacks設備")
            return None

        except Exception as e:
            print(f"❌ BlueStacks設備檢測失敗: {e}")
            return None

    @staticmethod
    def connect_to_bluestacks(force_reconnect: bool = False) -> Optional[str]:
        """✅ 統一的BlueStacks連接管理"""
        adb_path = ADBUtils.get_adb_path()
        if not os.path.exists(adb_path):
<<<<<<< HEAD
            print(f"❌ adb.exe不存在: {adb_path}")
=======
            print(f"❌ HD-Adb.exe不存在: {adb_path}")
>>>>>>> 0ff736d04a6e034a0b49bbf5875afbe4eecd9665
            return None

        current_time = time.time()

        # 檢查現有連接
        if (not force_reconnect and
            ADBUtils._connection_verified and
            ADBUtils._current_device_id and
            (current_time - ADBUtils._last_check_time) < ADBUtils._check_interval):
            
            if ADBUtils.test_connection(ADBUtils._current_device_id):
                return ADBUtils._current_device_id

        print("🔄 重新建立BlueStacks連接...")
        
        # 嘗試重新連接
        device_id = ADBUtils.find_bluestacks_device()
        
        if device_id:
            ADBUtils._current_device_id = device_id
            ADBUtils._connection_verified = True
            ADBUtils._last_check_time = current_time
            print(f"✅ BlueStacks連接成功: {device_id}")
            return device_id
        else:
            ADBUtils._current_device_id = None
            ADBUtils._connection_verified = False
            ADBUtils._last_check_time = current_time
            print("❌ BlueStacks連接失敗")
            return None

    @staticmethod
    def ensure_connection() -> Optional[str]:
        """✅ 確保ADB連接可用"""
        adb_path = ADBUtils.get_adb_path()
        if not os.path.exists(adb_path):
<<<<<<< HEAD
            print(f"❌ adb.exe不存在: {adb_path}")
=======
            print(f"❌ HD-Adb.exe不存在: {adb_path}")
>>>>>>> 0ff736d04a6e034a0b49bbf5875afbe4eecd9665
            return None

        # 嘗試連接
        device_id = ADBUtils.connect_to_bluestacks()
        if device_id:
            return device_id

        # 重啟ADB服務後再試
        print("🔄 嘗試重啟ADB服務...")
        if ADBUtils.restart_adb_server():
            time.sleep(3)
            device_id = ADBUtils.connect_to_bluestacks(force_reconnect=True)
            return device_id

        return None

    @staticmethod
    def restart_adb_server() -> bool:
        """✅ 重啟ADB服務"""
        adb_path = ADBUtils.get_adb_path()
        
        if not os.path.exists(adb_path):
<<<<<<< HEAD
            print(f"❌ adb.exe不存在: {adb_path}")
=======
            print(f"❌ HD-Adb.exe不存在: {adb_path}")
>>>>>>> 0ff736d04a6e034a0b49bbf5875afbe4eecd9665
            return False

        try:
            print("🔄 重啟ADB服務...")
            
            # 停止ADB服務
            subprocess.run([adb_path, 'kill-server'], capture_output=True, timeout=10)
            time.sleep(2)
            
            # 啟動ADB服務
            result = subprocess.run([adb_path, 'start-server'], capture_output=True, timeout=10)
            
            if result.returncode == 0:
                print("✅ ADB服務重啟成功")
                ADBUtils._current_device_id = None
                ADBUtils._connection_verified = False
                return True
            else:
                print("❌ ADB服務重啟失敗")
                return False

        except Exception as e:
            print(f"❌ ADB服務重啟異常: {e}")
            return False

    @staticmethod
    def test_connection(device_id: str) -> bool:
        """✅ 測試ADB連接"""
        adb_path = ADBUtils.get_adb_path()
        
        if not os.path.exists(adb_path):
            return False

        try:
            success, stdout, stderr = ADBUtils.execute_command(
                adb_path, device_id, ['shell', 'echo', 'test'], timeout=3
            )
            return success and 'test' in stdout
        except Exception:
            return False

    # ✅ 基於搜索結果[3][5]的基本ADB命令封裝
    @staticmethod
    def send_keyevent(device_id: str, keycode: str) -> bool:
        """✅ 改進版按鍵發送"""
        if not device_id:
            print("❌ 無效的設備ID")
            return False
            
        print(f"🎯 發送按鍵: {keycode}")
        
        # 嘗試使用 input keyevent
        success, stdout, stderr = ADBUtils.execute_command(
            device_id=device_id,
            command=['shell', f'input keyevent {keycode}']
        )
        
        if success:
            print(f"✅ 按鍵發送成功: {keycode}")
            return True
            
        print(f"⚠️ input keyevent 失敗，嘗試使用 sendevent...")
        
        try:
            # 獲取輸入設備路徑
            success, stdout, stderr = ADBUtils.execute_command(
                device_id=device_id,
                command=['shell', 'getevent -p | grep -e "add device" -e "ABS_MT_POSITION"']
            )
            
            if not success:
                print("❌ 無法獲取輸入設備路徑")
                return False
                
            # 解析設備路徑
            device_path = None
            for line in stdout.split('\n'):
                if 'add device' in line:
                    device_path = line.split('"')[1]
                    break
                    
            if not device_path:
                print("❌ 無法找到輸入設備路徑")
                return False
                
            print(f"🔍 使用輸入設備: {device_path}")
            
            # 發送按鍵事件
            key_events = [
                f'sendevent {device_path} 3 57 0',  # 按下
                f'sendevent {device_path} 0 0 0',   # 同步
                f'sendevent {device_path} 3 57 4294967295',  # 釋放
                f'sendevent {device_path} 0 0 0'    # 同步
            ]
            
            for event in key_events:
                success, stdout, stderr = ADBUtils.execute_command(
                    device_id=device_id,
                    command=['shell', event]
                )
                if not success:
                    print(f"❌ 發送事件失敗: {event}")
                    return False
                time.sleep(0.05)  # 事件間隔
                
            print(f"✅ 按鍵事件發送成功: {keycode}")
            return True
            
        except Exception as e:
            print(f"❌ 按鍵發送失敗: {e}")
            return False

    @staticmethod
    def send_longpress_keyevent(device_id: str, keycode: str) -> bool:
        """✅ 基於搜索結果[3]的長按按鍵"""
        success, stdout, stderr = ADBUtils.execute_command(
            device_id=device_id,
            command=['shell', 'input', 'keyevent', '--longpress', keycode]
        )
        return success

    @staticmethod
    def tap_screen(device_id: str, x: int, y: int) -> bool:
        """點擊螢幕"""
        success, stdout, stderr = ADBUtils.execute_command(
            device_id=device_id,
            command=['shell', 'input', 'tap', str(x), str(y)]
        )
        return success

    @staticmethod
    def swipe_screen(device_id: str, x1: int, y1: int, x2: int, y2: int, duration_ms: int) -> bool:
        """✅ 滑動螢幕"""
        success, stdout, stderr = ADBUtils.execute_command(
            device_id=device_id,
            command=['shell', 'input', 'swipe', str(x1), str(y1), str(x2), str(y2), str(duration_ms)]
        )
        return success

    @staticmethod
    def send_text(device_id: str, text: str) -> bool:
        """✅ 發送文字"""
        success, stdout, stderr = ADBUtils.execute_command(
            device_id=device_id,
            command=['shell', 'input', 'text', text]
        )
        return success

    # ✅ 狀態查詢方法
    @staticmethod
    def get_current_device() -> Optional[str]:
        """獲取當前連接的設備ID"""
        return ADBUtils._current_device_id if ADBUtils._connection_verified else None

    @staticmethod
    def get_connection_info() -> Dict[str, Any]:
        """獲取連接狀態信息"""
        adb_path = ADBUtils.get_adb_path()
        return {
            'adb_path': adb_path,
            'adb_exists': os.path.exists(adb_path),
            'current_device': ADBUtils._current_device_id,
            'is_connected': ADBUtils._connection_verified,
            'last_check': ADBUtils._last_check_time,
            'check_interval': ADBUtils._check_interval
        }

    @staticmethod
    def get_device_info(device_id: str) -> Dict[str, str]:
        """✅ 基於搜索結果[5]的設備信息獲取"""
        try:
            info = {}
            
            # 獲取設備型號
            success, stdout, stderr = ADBUtils.execute_command(
                device_id=device_id,
                command=['shell', 'getprop', 'ro.product.model']
            )
            if success:
                info['model'] = stdout.strip()
            
            # 獲取Android版本
            success, stdout, stderr = ADBUtils.execute_command(
                device_id=device_id,
                command=['shell', 'getprop', 'ro.build.version.release']
            )
            if success:
                info['android_version'] = stdout.strip()
            
            # 獲取螢幕尺寸
            success, stdout, stderr = ADBUtils.execute_command(
                device_id=device_id,
                command=['shell', 'wm', 'size']
            )
            if success:
                info['screen_size'] = stdout.strip()
            
            return info
            
        except Exception as e:
            print(f"❌ 獲取設備信息失敗: {e}")
            return {}
