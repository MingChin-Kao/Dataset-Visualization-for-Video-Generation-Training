# 使用輕量化的 Python 基礎映像檔
FROM python:3.10-slim

# 設定工作目錄
WORKDIR /app

# 複製專案的需求檔案
COPY requirements.txt .

# 安裝必要的依賴
RUN pip install --no-cache-dir -r requirements.txt

# 複製專案的所有檔案到容器中
COPY . .

# 暴露 Flask 預設的埠
EXPOSE 5000

# 設定環境變數以啟用 Flask 的開發模式
ENV FLASK_APP=app.py
ENV FLASK_RUN_HOST=0.0.0.0
ENV FLASK_ENV=development

# 啟動 Flask 應用程式
CMD ["flask", "run", "--reload"]