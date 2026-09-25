#!/usr/bin/env python3
"""
Hệ thống sao lưu database tự động chuẩn ngân hàng / kế toán — Vận tải Trường Phát.
Tạo bản sao lưu nhất quán, mã băm SHA-256, tự động giữ 30 bản ngày + 12 bản tháng.
"""

import os
import sys
import glob
import shutil
import sqlite3
import hashlib
from datetime import datetime

BACKUP_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backups"))
DAILY_DIR = os.path.join(BACKUP_ROOT, "daily")
MONTHLY_DIR = os.path.join(BACKUP_ROOT, "monthly")

os.makedirs(DAILY_DIR, exist_ok=True)
os.makedirs(MONTHLY_DIR, exist_ok=True)

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "transport.db")

def calculate_sha256(file_path):
    sha = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(65536):
            sha.update(chunk)
    return sha.hexdigest()

def backup_database(label="auto"):
    now = datetime.now()
    ts = now.strftime("%Y%m%d_%H%M%S")
    day_str = now.strftime("%Y%m%d")
    month_str = now.strftime("%Y%m")

    daily_filename = f"backup_{day_str}_{ts}_{label}.db"
    daily_filepath = os.path.join(DAILY_DIR, daily_filename)

    if not os.path.exists(DB_PATH):
        raise FileNotFoundError(f"Không tìm thấy database gốc tại {DB_PATH}")

    # 1. Sao lưu SQLite an toàn qua SQLite Backup API (không bị lock khi app đang ghi)
    src_con = sqlite3.connect(DB_PATH)
    dst_con = sqlite3.connect(daily_filepath)
    with dst_con:
        src_con.backup(dst_con, pages=100)
    dst_con.close()
    src_con.close()

    # 2. Tạo SQL Dump kèm theo
    sql_dump_path = daily_filepath.replace(".db", ".sql")
    dump_con = sqlite3.connect(daily_filepath)
    with open(sql_dump_path, "w", encoding="utf-8") as f:
        for line in dump_con.iterdump():
            f.write(f"{line}\n")
    dump_con.close()

    # 3. Tính toán mã băm SHA-256
    sha256_hash = calculate_sha256(daily_filepath)
    sha_file = daily_filepath + ".sha256"
    with open(sha_file, "w") as f:
        f.write(f"{sha256_hash}  {os.path.basename(daily_filepath)}\n")

    # 4. Sao chép vào bản sao lưu tháng (nếu là bản đầu tiên của tháng hoặc ngày cuối)
    monthly_filename = f"backup_month_{month_str}.db"
    monthly_filepath = os.path.join(MONTHLY_DIR, monthly_filename)
    shutil.copy2(daily_filepath, monthly_filepath)
    with open(monthly_filepath + ".sha256", "w") as f:
        f.write(f"{sha256_hash}  {monthly_filename}\n")

    # 5. Dọn dẹp lưu trữ: Giữ đúng 30 bản ngày + 12 bản tháng gần nhất
    cleanup_retention(DAILY_DIR, max_keep=30)
    cleanup_retention(MONTHLY_DIR, max_keep=12)

    print(f"✅ Đã sao lưu database thành công:")
    print(f"   - File DB: {daily_filepath}")
    print(f"   - File SQL: {sql_dump_path}")
    print(f"   - SHA-256: {sha256_hash}")
    return daily_filepath

def cleanup_retention(target_dir, max_keep=30):
    files = sorted(glob.glob(os.path.join(target_dir, "*.db")), key=os.path.getmtime)
    if len(files) > max_keep:
        to_delete = files[:-max_keep]
        for f in to_delete:
            try:
                os.remove(f)
                if os.path.exists(f + ".sha256"):
                    os.remove(f + ".sha256")
                sql = f.replace(".db", ".sql")
                if os.path.exists(sql):
                    os.remove(sql)
            except Exception as e:
                print(f"Lỗi dọn dẹp {f}: {e}")

if __name__ == "__main__":
    lbl = sys.argv[1] if len(sys.argv) > 1 else "manual"
    backup_database(lbl)
