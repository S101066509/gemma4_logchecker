FROM python:3.11-slim

# 設定工作目錄
WORKDIR /app

# 安裝基本依賴 (如需編譯部分庫，可在此加入 build-essential)
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 複製依賴清單並安裝
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 複製整個專案內容 (app/ 目錄會在 docker-compose 中被 volume 覆蓋以方便開發)
COPY . .

# 設定 PYTHONPATH 確保模組能正確被引用
ENV PYTHONPATH=/app

# 啟動命令
CMD ["python", "-m", "app.server"]
