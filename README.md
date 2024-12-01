# AI 圖片展示網站 (Python 版本)

這是一個用於展示和管理 AI 生成圖片的網站系統，支援 Stable Diffusion 和 ComfyUI 生成的圖片。

## 功能特點

- 自動識別並分類 SD 和 ComfyUI 生成的圖片
- 自動讀取圖片中的生成參數
- 關鍵詞管理和搜尋功能
- 支援 R18 內容的標記和過濾
- 縮圖自動生成
- 檔案自動整理功能

## 系統需求

- Python 3.8 或更高版本
- SQLite 3
- 作業系統：Windows/Linux/MacOS

## 安裝步驟

1. 下載或克隆專案到本地：
```bash
git clone [[repository_url]](https://github.com/sainitutu/AI_picture_display_website_python.git)
```

2. 執行 start.bat：
   - 會自動建立 Python 虛擬環境
   - 安裝所需的套件
   - 啟動網站伺服器

## 目錄結構

```
AI_picture_display_website_python/
├── app.py                 # 主程式
├── requirements.txt       # Python 套件需求
├── start.bat             # 啟動腳本
├── assets/
│   ├── uploads/          # 上傳圖片儲存目錄
│   └── thumbnails/       # 縮圖儲存目錄
├── database/
│   └── schema.sql        # 資料庫結構
├── public/
│   └── css/
│       └── style.css     # 網站樣式
└── templates/            # HTML 模板
    ├── index.html        # 首頁
    ├── upload.html       # 上傳頁面
    ├── view.html         # 檢視頁面
    └── edit.html         # 編輯頁面
```

## 使用說明

1. 啟動網站：
   - 點擊 start.bat
   - 等待虛擬環境設置完成
   - 伺服器會在 http://localhost:5000 啟動

2. 上傳圖片：
   - 點擊「新增圖片」
   - 選擇圖片檔案
   - 系統會自動分析圖片類型（SD/Comfy）
   - 自動讀取生成參數
   - 可以新增關鍵詞和設定 R18 標記

3. 瀏覽圖片：
   - 首頁顯示圖片縮圖列表
   - 可以依據類型和關鍵詞篩選
   - 點擊圖片查看詳細資訊

4. 編輯圖片：
   - 在檢視頁面點擊「編輯」
   - 可以修改類型、關鍵詞、參數等資訊
   - 可以設定或取消 R18 標記

5. 整理檔案：
   - 點擊「整理資料」
   - 系統會自動清理未使用的檔案

## 注意事項

- 上傳目錄和縮圖目錄會自動建立
- 資料庫檔案會在首次執行時自動建立
- 請勿手動刪除 assets 目錄下的檔案
- 建議定期使用整理功能清理未使用的檔案

## 開發說明

- 使用 Flask 框架開發
- 使用 SQLite 資料庫
- 支援 PNG 格式圖片的 metadata 讀取
- 自動產生縮圖功能
- 關鍵詞即時搜尋建議

## 授權

本專案採用 MIT 授權條款。詳見 LICENSE 檔案。
