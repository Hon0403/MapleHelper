"""
生命週期管理器 - 負責管理主循環和效能優化
"""

import time
import threading
from typing import Dict, Any, Optional
from includes.log_utils import get_logger


class LifecycleManager:
    """生命週期管理器 - 管理主循環和效能優化"""
    
    def __init__(self, component_manager):
        self.logger = get_logger("LifecycleManager")
        self.component_manager = component_manager
        
        # 主循環控制
        self._running = False
        self._thread = None
        
        # 效能優化設定
        self.update_intervals = {
            'frame_capture': 0.05,    # 20 FPS
            'position_tracking': 0.1,  # 10 FPS
            'combat_update': 0.2,      # 5 FPS
            'health_check': 1.0,       # 1 FPS
            'status_update': 0.5       # 2 FPS
        }
        
        # 時間追蹤
        self.last_update_times = {
            'frame_capture': 0,
            'position_tracking': 0,
            'combat_update': 0,
            'health_check': 0,
            'status_update': 0
        }
        
        # 效能統計
        self.performance_stats = {
            'fps': 0,
            'frame_count': 0,
            'last_fps_time': time.time(),
            'avg_loop_time': 0,
            'max_loop_time': 0
        }
        
        # 緩存管理
        self.frame_cache = None
        self.position_cache = None
        self.cache_timestamp = 0
        self.cache_duration = 0.1  # 100ms緩存
        
        self.is_initialized = False
        self.logger.info("生命週期管理器已創建")
    
    def initialize(self) -> bool:
        """初始化生命週期管理器"""
        if self.is_initialized:
            return True
        
        try:
            self.logger.info("初始化生命週期管理器...")
            
            # 從設定檔讀取更新頻率
            config = self.component_manager.config
            main_loop_config = config.get('main_loop', {})
            
            for key in self.update_intervals:
                if key in main_loop_config:
                    self.update_intervals[key] = main_loop_config[key]
            
            # 從設定檔讀取緩存設定
            capturer_config = config.get('capturer', {})
            self.cache_duration = capturer_config.get('cache_duration', 0.1)
            
            self.is_initialized = True
            self.logger.info("✅ 生命週期管理器初始化完成")
            return True
            
        except Exception as e:
            self.logger.error(f"生命週期管理器初始化失敗: {e}")
            return False
    
    def start(self) -> bool:
        """啟動主循環"""
        if self._running:
            return True
        
        try:
            self.logger.info("啟動主循環...")
            
            self._running = True
            self._thread = threading.Thread(target=self._main_loop, daemon=True)
            self._thread.start()
            
            self.logger.info("✅ 主循環已啟動")
            return True
            
        except Exception as e:
            self.logger.error(f"啟動主循環失敗: {e}")
            return False
    
    def stop(self) -> bool:
        """停止主循環"""
        if not self._running:
            return True
        
        try:
            self.logger.info("停止主循環...")
            
            self._running = False
            
            if self._thread and self._thread.is_alive():
                self._thread.join(timeout=2.0)
            
            self.logger.info("✅ 主循環已停止")
            return True
            
        except Exception as e:
            self.logger.error(f"停止主循環失敗: {e}")
            return False
    
    def cleanup(self):
        """清理資源"""
        try:
            self.logger.info("清理生命週期管理器...")
            
            self.stop()
            
            # 清理緩存
            self.frame_cache = None
            self.position_cache = None
            
            self.is_initialized = False
            self.logger.info("✅ 生命週期管理器清理完成")
            
        except Exception as e:
            self.logger.error(f"生命週期管理器清理失敗: {e}")
    
    def _main_loop(self):
        """主循環 - 效能優化版"""
        self.logger.info("主循環開始")
        
        frame_count = 0
        last_fps_time = time.time()
        
        # 從設定檔讀取睡眠時間
        config = self.component_manager.config
        main_loop_config = config.get('main_loop', {})
        sleep_time = main_loop_config.get('sleep_time', 0.02)
        
        while self._running:
            loop_start_time = time.time()
            
            try:
                current_time = time.time()
                
                # 智能畫面捕捉
                if self._should_update('frame_capture'):
                    self._update_frame_capture()
                
                # 智能位置追蹤
                if self._should_update('position_tracking'):
                    self._update_position_tracking()
                
                # 智能戰鬥更新
                if self._should_update('combat_update'):
                    self._update_combat()
                
                # 智能血條檢查
                if self._should_update('health_check'):
                    self._update_health_check()
                
                # 智能狀態更新
                if self._should_update('status_update'):
                    self._update_performance_stats(loop_start_time)
                
                # 計算FPS
                frame_count += 1
                if current_time - last_fps_time >= 1.0:
                    fps = frame_count / (current_time - last_fps_time)
                    self.performance_stats['fps'] = fps
                    frame_count = 0
                    last_fps_time = current_time
                    
                    # 顯示效能資訊
                    if fps > 0:
                        self.logger.info(f"效能: {fps:.1f} FPS, 平均循環時間: {self.performance_stats['avg_loop_time']*1000:.1f}ms")
                
                # 動態睡眠時間
                loop_time = time.time() - loop_start_time
                actual_sleep_time = max(0.001, sleep_time - loop_time)
                time.sleep(actual_sleep_time)
                
            except Exception as e:
                self.logger.error(f"主循環錯誤: {e}")
                time.sleep(0.1)
        
        self.logger.info("主循環已停止")
    
    def _should_update(self, update_type: str) -> bool:
        """檢查是否應該更新"""
        current_time = time.time()
        last_update = self.last_update_times.get(update_type, 0)
        interval = self.update_intervals.get(update_type, 0.1)
        
        if current_time - last_update >= interval:
            self.last_update_times[update_type] = current_time
            return True
        return False
    
    def _update_frame_capture(self):
        """更新畫面捕捉"""
        try:
            capturer = self.component_manager.get_component('capturer')
            if capturer:
                frame = capturer.grab_frame()
                if frame is not None:
                    self.frame_cache = frame
                    self.cache_timestamp = time.time()
        except Exception as e:
            self.logger.error(f"畫面捕捉更新失敗: {e}")
    
    def _update_position_tracking(self):
        """更新位置追蹤"""
        try:
            tracker = self.component_manager.get_component('tracker')
            if tracker and self.frame_cache is not None:
                rel_pos = tracker.track_player(self.frame_cache)
                if rel_pos:
                    self.position_cache = rel_pos
        except Exception as e:
            self.logger.error(f"位置追蹤更新失敗: {e}")
    
    def _update_combat(self):
        """更新戰鬥系統"""
        try:
            combat = self.component_manager.get_component('combat')
            if combat and combat.is_enabled and self.frame_cache is not None:
                combat.update(self.position_cache, self.frame_cache)
        except Exception as e:
            self.logger.error(f"戰鬥系統更新失敗: {e}")
    
    def _update_health_check(self):
        """更新血條檢查"""
        try:
            health_detector = self.component_manager.get_component('health_detector')
            if health_detector and self.frame_cache is not None:
                # 血條檢測邏輯
                pass
        except Exception as e:
            self.logger.error(f"血條檢查更新失敗: {e}")
    
    def _update_performance_stats(self, loop_start_time: float):
        """更新效能統計"""
        current_time = time.time()
        loop_time = current_time - loop_start_time
        
        # 更新平均循環時間
        if self.performance_stats['avg_loop_time'] == 0:
            self.performance_stats['avg_loop_time'] = loop_time
        else:
            self.performance_stats['avg_loop_time'] = (
                self.performance_stats['avg_loop_time'] * 0.9 + loop_time * 0.1
            )
        
        # 更新最大循環時間
        if loop_time > self.performance_stats['max_loop_time']:
            self.performance_stats['max_loop_time'] = loop_time
    
    def get_status(self) -> Dict[str, Any]:
        """獲取狀態"""
        return {
            'running': self._running,
            'initialized': self.is_initialized,
            'performance': self.performance_stats.copy(),
            'update_intervals': self.update_intervals.copy()
        }
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """獲取效能統計"""
        return self.performance_stats.copy() 