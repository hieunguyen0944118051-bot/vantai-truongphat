#!/bin/bash
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
cd "$DIR"

echo "================================================================"
echo "  🚚 VẬN TẢI TRƯỜNG PHÁT - HỆ THỐNG QUẢN LÝ VẬN TẢI XE BEN"
echo "================================================================"
(sleep 1.5 && open "http://localhost:8000/weighbridge") &

# Start Zalo daily background monitor
./backend/venv/bin/python backend/zalo_watcher.py 2>&1 &

cd backend
./venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000
