# MapleHelper

楓之谷自動化輔助工具  
**功能：怪物自動辨識、路徑編輯、自動戰鬥、即時顯示、PyQt5 圖形介面**

---

## 主要特色

- **怪物自動辨識**  
  - 支援多模板匹配，遮擋/翻轉/多動作皆可辨識
  - 可自訂模板資料夾，動態切換怪物類型
  - 辨識結果即時疊加於畫面（含名稱、信心分數）
  - 優化辨識速度，支援高頻率更新

- **自動戰鬥系統**  
  - 智能戰鬥邏輯，自動追蹤和攻擊怪物
  - 支援安全區域設定，自動返回安全點
  - 可自訂攻擊間隔、移動速度等參數
  - 結合路徑系統，支援區域巡邏

- **路徑編輯器**  
  - 支援地圖障礙物、區域標記、路徑點編輯
  - 小地圖自動偵測，支援即時更新
  - 優化編輯器性能，減少延遲
  - 支援多種區域類型（可行走、禁止、繩索）

- **即時顯示**  
  - 內建 OpenCV 即時顯示視窗，可同步顯示辨識框
  - 支援 60FPS 高速更新
  - 優化畫面捕獲頻率，提升流暢度

- **GUI 操作介面**  
  - PyQt5 製作，所有功能皆可視覺化操作
  - 支援模板資料夾下拉選單、參數切換、狀態即時顯示
  - 優化視窗管理，避免主視窗跳轉

---

## 安裝與執行

1. **安裝 Python 3.8+ 與必要套件**
   ```bash
   pip install -r requirements.txt
   ```

2. **準備 BlueStacks/模擬器與 ADB**
   - 請確保 `HD-Adb.exe` 可用，並已連接模擬器
   - 支援 BlueStacks 5 以上版本

3. **啟動主程式**
   ```bash
   python main.py
   ```

---

## 資料夾結構

```
MapleHelper/
├─ main.py                      # 主程式入口
├─ modules/
│   ├─ simple_gui_monster_display.py   # 怪物辨識GUI
│   ├─ waypoint_editor.py              # 路徑編輯器
│   ├─ auto_combat_simple.py           # 自動戰鬥系統
│   ├─ simple_capturer.py              # 畫面捕獲
│   ├─ simple_adb.py                   # ADB 控制
│   └─ coordinate.py                   # 座標系統
├─ includes/
│   ├─ simple_template_utils.py        # 模板辨識核心
│   ├─ adb_utils.py                    # ADB 工具
│   ├─ grid_utils.py                   # 網格系統
│   ├─ movement_utils.py               # 移動控制
│   └─ canvas_utils.py                 # 畫布工具
├─ templates/
│   └─ monsters/
│       └─ 三眼章魚/
│           ├─ test1.png, test2.png... # 怪物模板圖
├─ data/                       # 路徑點、障礙物等資料
├─ configs/                    # 設定檔
└─ requirements.txt            # 依賴套件
```

---

## 常見問題

- **Q：辨識不到怪物怎麼辦？**  
  A：請多準備幾張不同動作/角度/大小的模板，並確保模板清晰、無雜訊。

- **Q：自動戰鬥不穩定怎麼辦？**  
  A：請調整 `auto_combat_simple.py` 中的戰鬥參數，如 `attack_interval`、`movement_interval` 等。

- **Q：路徑編輯器開啟慢怎麼辦？**  
  A：已優化編輯器性能，減少不必要的重繪和檢查。如仍有問題，可調整 `waypoint_editor.py` 中的延遲參數。

- **Q：如何調整辨識嚴格度？**  
  A：可修改 `includes/simple_template_utils.py` 內的 `confidence_threshold`、`inlier_ratio`、`match_count` 等參數。

---
