#!/bin/bash
cd "$(dirname "$0")/backend"
echo "🚀 Đang khởi động Hệ Thống Quản Lý Vận Tải Xe Đầu Kéo & Sà Lan..."
echo "🌐 Mở trình duyệt tại: http://localhost:8000"
./venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000
