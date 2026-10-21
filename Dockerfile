# Render đang build dịch vụ bằng Docker — KHÔNG xóa file này.
FROM python:3.10-slim

WORKDIR /app

COPY backend/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY backend /app

EXPOSE 8000

# Render cấp cổng qua biến PORT; chạy máy khác thì mặc định 8000
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"]
