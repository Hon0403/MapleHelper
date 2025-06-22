# MapleStory Helper - 分層架構設計

## 🏗️ **架構概述**

MapleStory Helper 採用**分層架構**設計，將複雜的系統分解為多個層次，每個層次都有明確的職責和邊界。

## 📁 **目錄結構**

```
MapleHelper/
├── core/                          # 🎯 核心層
│   ├── __init__.py
│   ├── application.py             # 應用程式主類別
│   ├── component_manager.py       # 組件管理器
│   └── lifecycle_manager.py       # 生命週期管理器
├── includes/                      # 🔧 工具層
│   ├── config_utils.py            # 設定檔工具
│   ├── log_utils.py               # 日誌工具
│   ├── base_classes.py            # 基底類別
│   └── ...                        # 其他工具模組
├── modules/                       # 🧩 功能層
│   ├── simple_capturer.py         # 畫面捕捉
│   ├── coordinate.py              # 角色追蹤
│   ├── auto_combat_simple.py      # 戰鬥系統
│   ├── waypoint_editor.py         # 路徑編輯器
│   └── ...                        # 其他功能模組
├── configs/                       # ⚙️ 配置層
│   └── bluestacks.yaml            # 主要設定檔
├── main.py                        # 舊版主程式
├── main_new.py                    # 🆕 新版主程式（分層架構）
└── ARCHITECTURE.md                # 本文件
```

## 🎯 **分層架構詳解**

### 1. **核心層 (Core Layer)**

負責應用程式的整體架構和協調。

#### `MapleStoryApplication`
- **職責**: 應用程式主類別，負責整體協調
- **功能**: 
  - 載入設定檔
  - 管理組件管理器
  - 管理生命週期管理器
  - 提供統一的應用程式介面

#### `ComponentManager`
- **職責**: 管理所有系統組件的生命週期
- **功能**:
  - 組件註冊和依賴管理
  - 組件初始化順序控制
  - 組件狀態監控
  - 組件間依賴檢查

#### `LifecycleManager`
- **職責**: 管理主循環和效能優化
- **功能**:
  - 智能更新頻率控制
  - 效能統計和監控
  - 緩存管理
  - 主循環協調

### 2. **工具層 (Utility Layer)**

提供共用的工具和基底類別。

#### `ConfigUtils`
- **職責**: 設定檔處理工具
- **功能**: YAML/JSON 檔案載入、保存、合併

#### `ConfigSection`
- **職責**: 設定檔區段讀取工具
- **功能**: 類型安全的參數讀取

#### `BaseComponent`
- **職責**: 組件基底類別
- **功能**: 統一的組件生命週期管理

### 3. **功能層 (Feature Layer)**

實現具體的功能模組。

#### 組件類型
- **畫面捕捉**: `SimpleCapturer`
- **角色追蹤**: `TemplateMatcherTracker`
- **戰鬥系統**: `SimpleCombat`
- **路徑系統**: `SimpleWaypointSystem`
- **血條檢測**: `HealthManaDetector`
- **GUI 介面**: `MonsterDetectionGUI`
- **路徑編輯器**: `WaypointEditor`

### 4. **配置層 (Configuration Layer)**

管理所有設定和參數。

#### `bluestacks.yaml`
- **職責**: 集中管理所有設定
- **內容**: 各組件的配置參數

## 🔄 **組件依賴關係**

```
capturer (畫面捕捉)
    ↓
tracker (角色追蹤) ← waypoint_system (路徑系統)
    ↓                    ↓
combat (戰鬥系統) ←──────┘
    ↓
gui (GUI介面) ← editor (路徑編輯器)
```

## ⚡ **效能優化特性**

### 1. **智能更新頻率**
- 畫面捕捉: 20 FPS
- 位置追蹤: 10 FPS
- 戰鬥更新: 5 FPS
- 血條檢查: 1 FPS
- 狀態更新: 2 FPS

### 2. **緩存機制**
- 畫面緩存: 100ms
- 位置緩存: 動態管理
- 組件狀態緩存

### 3. **動態睡眠時間**
- 根據實際執行時間調整
- 最小睡眠時間: 1ms

## 🛠️ **使用方式**

### 舊版 (main.py)
```python
# 複雜的初始化邏輯
app = MapleStoryHelper()
app.start()
```

### 新版 (main_new.py)
```python
# 清晰的分層架構
app = MapleStoryApplication()
setup_components(app)
app.initialize()
app.start()
```

## ✅ **架構優勢**

### 1. **職責分離**
- 每個層次都有明確的職責
- 降低模組間耦合度
- 提高程式碼可維護性

### 2. **統一管理**
- 組件生命週期統一管理
- 設定檔統一管理
- 錯誤處理統一管理

### 3. **易於擴展**
- 新增組件只需註冊
- 依賴關係自動檢查
- 初始化順序自動控制

### 4. **效能優化**
- 智能更新頻率控制
- 緩存機制
- 效能監控

### 5. **易於測試**
- 組件可獨立測試
- 依賴注入
- 模擬組件支援

## 🔄 **遷移指南**

### 從舊版遷移到新版

1. **備份現有程式碼**
2. **使用 `main_new.py` 替代 `main.py`**
3. **檢查組件設定檔**
4. **測試功能完整性**

### 組件適配

現有組件需要實現以下介面：
- `initialize()` - 初始化
- `start()` - 啟動
- `stop()` - 停止
- `cleanup()` - 清理
- `get_status()` - 獲取狀態

## 📊 **效能對比**

| 項目 | 舊版 | 新版 |
|------|------|------|
| 主程式行數 | 564行 | 120行 |
| 組件管理 | 分散 | 統一 |
| 設定檔管理 | 混亂 | 集中 |
| 錯誤處理 | 分散 | 統一 |
| 效能監控 | 基本 | 完整 |
| 可維護性 | 低 | 高 |

## 🎯 **未來規劃**

1. **插件系統**: 支援動態載入組件
2. **配置熱重載**: 支援運行時修改設定
3. **效能分析**: 更詳細的效能分析工具
4. **自動化測試**: 完整的測試框架
5. **文檔生成**: 自動生成 API 文檔 