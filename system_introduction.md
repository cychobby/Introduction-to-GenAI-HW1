# Advanced GenAI Chat System v2: My very powerfulChatbot

## 系統簡介

這是一個多模態AI對話系統，整合了生成式AI技術。

### 核心功能特點

**1. 長期記憶持久化 (Long-term Memory)**
- ✅ 資料庫完整備份所有對話歷史
- ✅ 支援全會話搜尋
- ✅ 自動統計使用數據
- ✅ 支援對話匯出功能

**2. 多模態能力 (Multimodal)**
- ✅ 支援圖片上傳和視覺分析
- ✅ 圖片內容嵌入式對話

**3. 智慧模型路由 (Auto Routing)**
- ✅ 基於輸入內容自動選擇最優模型
- ✅ 任務類型識別 (寫程式/數學/分析圖片)
- ✅ 支援手動和自動模式切換

**4. 工具集成與MCP (Tool Use)**
- ✅ 計算機工具 - 數學運算
- ✅ 網路搜尋工具 - 即時資訊檢索
- ✅ 代碼執行工具 - 安全程式碼運行
- ✅ 文件操作工具 - 圖片讀寫管理

**5. 進階功能 (Additional Features)**
- ✅ 實時串流輸出 (Streaming)
- ✅ 訊息編輯/撤回機制
- ✅ 多API支援 (Groq, NVIDIA NIM, Anthropic MCP)
- ✅ 使用統計儀表板
- ✅ 會話管理與備份

### 技術架構

- **前端**: Streamlit 響應式Web介面
- **後端**: Python模組化架構
- **資料持久化**: SQLite資料庫
- **AI服務**: OpenAI相容API (Groq/NVIDIA)
- **工具系統**: 自定義工具執行器
- **多模態處理**: PIL圖片處理

專案連結：https://github.com/cychobby/Introduction-to-GenAI-HW1