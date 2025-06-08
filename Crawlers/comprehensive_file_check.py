# optimized_complete_downloader.py - 基於成功經驗的完整下載器

import requests
import os
import time
import random
import json
from fake_useragent import UserAgent
from datetime import datetime

class OptimizedCompleteDownloader:
    """基於成功經驗優化的完整下載器"""
    
    def __init__(self):
        self.base_url = 'https://maplestory.io/api/TMS/209/mob/{}/download'
        self.output_dir = 'complete_downloads'
        self.progress_file = 'download_progress.json'
        
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)
        
        self.ua = UserAgent()
        self.setup_optimized_session()
        
        # ✅ 基於成功經驗調整的參數
        self.min_interval = 8     # 成功範圍：8-20秒
        self.max_interval = 20
        self.thinking_probability = 0.08  # 8%機率長思考（原來10%稍微降低）
        self.user_agent_rotation_frequency = 5  # 每5個輪換（證明有效）
        self.browse_simulation_frequency = 10   # 每10個模擬瀏覽
        
        # ✅ 錯誤處理優化
        self.error_cooldown = 60
        self.max_consecutive_errors = 3
        self.blacklist_ids = [230100]  # 已知失敗的ID
        
        # 統計
        self.stats = {
            'total_attempted': 0,
            'successful_downloads': 0,
            'http_500_count': 0,
            'user_agent_rotations': 0,
            'session_resets': 0,
            'downloaded_ids': [],
            'failed_ids': [],
            'start_time': datetime.now().isoformat()
        }
        
        # 載入之前的進度
        self.load_progress()
    
    def setup_optimized_session(self):
        """基於成功經驗的會話設定"""
        self.session = requests.Session()
        
        headers = {
            'User-Agent': self.ua.random,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'same-origin',
            'Cache-Control': 'max-age=0'
        }
        
        self.session.headers.update(headers)
    
    def optimized_human_delay(self):
        """基於成功經驗的人類化延遲"""
        # 基礎延遲（成功範圍：8-20秒）
        base_delay = random.uniform(self.min_interval, self.max_interval)
        
        # 思考延遲（成功案例：68.9秒）
        if random.random() < self.thinking_probability:
            thinking_delay = random.uniform(60, 90)
            print(f"💭 模擬思考延遲: {thinking_delay:.1f}秒")
            time.sleep(thinking_delay)
            return
        
        print(f"⏱️ 正常等待: {base_delay:.1f}秒")
        time.sleep(base_delay)
    
    def smart_browse_simulation(self):
        """聰明的瀏覽模擬（跳過404頁面）"""
        try:
            # 只訪問確定存在的頁面
            self.session.get('https://maplestory.io', timeout=15)
            print(f"🏠 訪問首頁: 200")
            time.sleep(random.uniform(2, 5))
            
        except Exception as e:
            print(f"🌐 瀏覽模擬失敗: {e}")
    
    def download_with_optimization(self, monster_id):
        """基於成功經驗的優化下載"""
        # 跳過黑名單ID
        if monster_id in self.blacklist_ids:
            print(f"⚫ 跳過黑名單ID: {monster_id}")
            return False
        
        # 跳過已下載ID
        if monster_id in self.stats['downloaded_ids']:
            print(f"⏭️ 跳過已下載: {monster_id}")
            return True
        
        url = self.base_url.format(monster_id)
        
        try:
            print(f"📥 嘗試下載: {monster_id}")
            
            response = self.session.get(url, timeout=30, allow_redirects=True)
            
            if response.status_code == 200:
                content_length = len(response.content)
                
                if content_length > 100:
                    filename = f'{monster_id}.zip'
                    filepath = os.path.join(self.output_dir, filename)
                    
                    with open(filepath, 'wb') as f:
                        f.write(response.content)
                    
                    print(f"✅ 成功: {filename} ({content_length:,}b)")
                    
                    self.stats['successful_downloads'] += 1
                    self.stats['downloaded_ids'].append(monster_id)
                    return True
                else:
                    print(f"❌ 檔案太小: {content_length}b")
                    self.stats['failed_ids'].append(monster_id)
                    return False
            
            elif response.status_code == 500:
                self.stats['http_500_count'] += 1
                print(f"🚫 HTTP 500 (第{self.stats['http_500_count']}次)")
                
                # 加入黑名單避免重複嘗試
                if monster_id not in self.blacklist_ids:
                    self.blacklist_ids.append(monster_id)
                    print(f"⚫ 加入黑名單: {monster_id}")
                
                print(f"❄️ HTTP 500冷卻: {self.error_cooldown}秒")
                time.sleep(self.error_cooldown)
                return False
            
            else:
                print(f"❌ HTTP {response.status_code}")
                self.stats['failed_ids'].append(monster_id)
                return False
                
        except Exception as e:
            print(f"❌ 請求異常: {e}")
            self.stats['failed_ids'].append(monster_id)
            return False
        
        finally:
            self.stats['total_attempted'] += 1
    
    def get_comprehensive_id_list(self):
        """產生從 100000 到 9400100 的連續 ID 區段（每段200個）"""
        start = 100000
        end = 9400100
        step = 1

        id_ranges = []
        for i in range(start, end, step):
            id_ranges.append((i, min(i + step, end)))

        return id_ranges
    
    def execute_complete_download(self):
        """執行完整下載"""
        print("🚀 開始基於成功經驗的完整下載")
        print("✅ 成功率預期：90%+")
        print(f"📁 輸出目錄: {os.path.abspath(self.output_dir)}")
        
        id_ranges = self.get_comprehensive_id_list()
        
        print(f"\n📊 將下載 {len(id_ranges)} 個範圍")
        
        total_success = 0
        
        for range_index, (start_id, end_id) in enumerate(id_ranges, 1):
            print(f"\n📋 [{range_index}/{len(id_ranges)}] 範圍: {start_id:,} - {end_id:,}")
            
            range_success = 0
            consecutive_errors = 0
            
            for monster_id in range(start_id, end_id + 1):
                success = self.download_with_optimization(monster_id)
                
                if success:
                    consecutive_errors = 0
                    range_success += 1
                    total_success += 1
                else:
                    consecutive_errors += 1
                
                # 連續錯誤檢查
                if consecutive_errors >= self.max_consecutive_errors:
                    print(f"⚠️ 連續錯誤{consecutive_errors}次，跳過剩餘範圍")
                    break
                
                # User-Agent輪換（每5個）
                if self.stats['total_attempted'] % self.user_agent_rotation_frequency == 0:
                    self.session.headers['User-Agent'] = self.ua.random
                    self.stats['user_agent_rotations'] += 1
                    print(f"🔄 輪換User-Agent (第{self.stats['user_agent_rotations']}次)")
                
                # 瀏覽模擬（每10個）
                if self.stats['total_attempted'] % self.browse_simulation_frequency == 0:
                    self.smart_browse_simulation()
                
                # 人類化延遲
                if monster_id < end_id:
                    self.optimized_human_delay()
                
                # 定期保存進度
                if self.stats['total_attempted'] % 50 == 0:
                    self.save_progress()
                    self.print_progress()
            
            print(f"📊 範圍結果: {range_success} 個怪物成功")
            
            # 範圍間休息
            if range_index < len(id_ranges):
                rest_time = random.uniform(30, 60)
                print(f"💤 範圍間休息: {rest_time:.1f}秒")
                time.sleep(rest_time)
        
        self.print_final_stats()
    
    def save_progress(self):
        """保存進度"""
        self.stats['last_update'] = datetime.now().isoformat()
        
        with open(self.progress_file, 'w', encoding='utf-8') as f:
            json.dump(self.stats, f, indent=2, ensure_ascii=False)
    
    def load_progress(self):
        """載入進度"""
        if os.path.exists(self.progress_file):
            try:
                with open(self.progress_file, 'r', encoding='utf-8') as f:
                    saved_stats = json.load(f)
                    
                self.stats.update(saved_stats)
                print(f"✅ 載入進度: 已下載 {len(self.stats['downloaded_ids'])} 個怪物")
                
            except Exception as e:
                print(f"⚠️ 載入進度失敗: {e}")
    
    def print_progress(self):
        """顯示進度"""
        success_rate = (self.stats['successful_downloads'] / self.stats['total_attempted'] * 100) if self.stats['total_attempted'] > 0 else 0
        
        print(f"\n📊 當前進度:")
        print(f"   總測試: {self.stats['total_attempted']}")
        print(f"   成功: {self.stats['successful_downloads']}")
        print(f"   成功率: {success_rate:.1f}%")
        print(f"   HTTP 500: {self.stats['http_500_count']}")
    
    def print_final_stats(self):
        """最終統計"""
        print("\n" + "="*60)
        print("🎉 基於成功經驗的完整下載完成！")
        print(f"📊 總測試: {self.stats['total_attempted']}")
        print(f"✅ 成功下載: {self.stats['successful_downloads']}")
        print(f"❌ 失敗: {len(self.stats['failed_ids'])}")
        print(f"🚫 HTTP 500: {self.stats['http_500_count']}")
        
        if self.stats['total_attempted'] > 0:
            success_rate = (self.stats['successful_downloads'] / self.stats['total_attempted']) * 100
            print(f"📈 最終成功率: {success_rate:.1f}%")
        
        print(f"📁 檔案位置: {os.path.abspath(self.output_dir)}")

# 使用範例
if __name__ == "__main__":
    print("🎯 基於成功經驗的完整下載器")
    print("✅ 92.9%成功率經驗優化")
    print("=" * 50)
    
    try:
        downloader = OptimizedCompleteDownloader()
        downloader.execute_complete_download()
    except ImportError:
        print("❌ 請先安裝：pip install fake-useragent")
