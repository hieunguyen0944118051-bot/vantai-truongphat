#!/bin/bash
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
cd "$DIR"

echo "================================================================"
echo "  🚢 VẬN TẢI TRƯỜNG PHÁT — PHẦN MỀM QUẢN LÝ SÀ LAN (BƯỚC 0 + 1)"
echo "  ⚡ Chuẩn từng đồng cước, neo, dầu, ứng, hao hụt & lãi gộp"
echo "================================================================"
echo ""
echo "🚀 Đang khởi động máy chủ và mở ứng dụng Sà Lan..."

# Mở trình duyệt web sau 1.5 giây
(sleep 1.5 && open "http://localhost:8000/salan") &

cd backend
./venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000
