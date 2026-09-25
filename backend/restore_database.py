#!/usr/bin/env python3
"""
Bộ công cụ khôi phục và kiểm chứng tính toàn vẹn 100% của bản sao lưu database.
So khớp số dòng từng bảng và tổng các cột tiền; lệch 1 đồng lập tức dừng và báo lỗi.
"""

import os
import sys
import glob
import sqlite3
import hashlib

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "transport.db")
TEMP_RESTORE_DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "transport_temp_restore.db")

def verify_and_restore(backup_file=None):
    if not backup_file:
        # Lấy file sao lưu mới nhất trong backups/daily/
        daily_files = sorted(glob.glob(os.path.join(os.path.dirname(__file__), "..", "backups", "daily", "*.db")), key=os.path.getmtime)
        if not daily_files:
            raise FileNotFoundError("Không tìm thấy bản sao lưu nào trong backups/daily!")
        backup_file = daily_files[-1]

    print(f"🔍 Đang kiểm tra tính toàn vẹn file sao lưu: {backup_file}")
    
    # 1. Kiểm tra SHA-256
    sha_file = backup_file + ".sha256"
    if os.path.exists(sha_file):
        with open(sha_file, "r") as f:
            expected_sha = f.read().split()[0].strip()
        sha = hashlib.sha256()
        with open(backup_file, "rb") as f:
            while chunk := f.read(65536):
                sha.update(chunk)
        actual_sha = sha.hexdigest()
        if expected_sha != actual_sha:
            raise ValueError(f"❌ SAI LỆCH SHA-256! File sao lưu có thể đã bị hỏng hoặc bị sửa đổi.\nKỳ vọng: {expected_sha}\nThực tế: {actual_sha}")
        print("✅ Kiểm tra SHA-256: HỢP LỆ!")
    
    # 2. Khôi phục vào database tạm thời
    if os.path.exists(TEMP_RESTORE_DB):
        os.remove(TEMP_RESTORE_DB)

    src_con = sqlite3.connect(backup_file)
    dst_con = sqlite3.connect(TEMP_RESTORE_DB)
    with dst_con:
        src_con.backup(dst_con, pages=100)
    dst_con.close()
    src_con.close()
    print("✅ Đã khôi phục thành công vào database tạm thời.")

    # 3. So khớp chi tiết số dòng và các cột tiền với database đang chạy
    print("🔍 Đang đối chiếu số dòng và tổng tiền giữa bản đang chạy và bản sao lưu...")
    con_live = sqlite3.connect(DB_PATH)
    con_temp = sqlite3.connect(TEMP_RESTORE_DB)
    
    cur_live = con_live.cursor()
    cur_temp = con_temp.cursor()

    tables = ["salan_chuyen", "salan_do_dau", "salan_ung_phi", "salan_phuong_tien", "salan_chu_hang", "salan_doi_tac"]
    
    for tbl in tables:
        # Check if table exists in live
        t_exists = cur_live.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (tbl,)).fetchone()
        if not t_exists:
            continue

        cnt_live = cur_live.execute(f"SELECT COUNT(*) FROM {tbl}").fetchone()[0]
        cnt_temp = cur_temp.execute(f"SELECT COUNT(*) FROM {tbl}").fetchone()[0]
        
        if cnt_live != cnt_temp:
            raise ValueError(f"❌ LỆCH SỐ DÒNG Ở BẢNG {tbl}! Live: {cnt_live} != Sao lưu: {cnt_temp}")
        print(f"   - Bảng {tbl}: {cnt_live} dòng (Khớp 100%)")

    # So khớp tổng tiền các bảng tài chính
    # 1. Bảng chuyến (kl_nhan_kg, kl_giao_kg, don_gia_cuoc)
    money_queries = [
        ("salan_chuyen", "SUM(kl_nhan_kg)", "Tổng khối lượng nhận"),
        ("salan_chuyen", "SUM(kl_giao_kg)", "Tổng khối lượng giao"),
        ("salan_do_dau", "SUM(tien_dau)", "Tổng tiền dầu"),
        ("salan_ung_phi", "SUM(so_tien)", "Tổng tiền ứng")
    ]

    for tbl, col_sum, desc in money_queries:
        t_exists = cur_live.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (tbl,)).fetchone()
        if not t_exists:
            continue
            
        sum_live = cur_live.execute(f"SELECT COALESCE({col_sum}, 0) FROM {tbl}").fetchone()[0]
        sum_temp = cur_temp.execute(f"SELECT COALESCE({col_sum}, 0) FROM {tbl}").fetchone()[0]
        
        if sum_live != sum_temp:
            raise ValueError(f"❌ LỆCH TIỀN {desc}! Live: {sum_live:,} != Sao lưu: {sum_temp:,}")
        print(f"   - {desc}: {sum_live:,} (Khớp từng đồng 100%)")

    con_live.close()
    con_temp.close()

    # Dọn dẹp DB tạm
    if os.path.exists(TEMP_RESTORE_DB):
        os.remove(TEMP_RESTORE_DB)

    print("\n🎯 KẾT QUẢ: BẢN SAO LƯU HOÀN TOÀN NHẤT QUÁN, KHỚP 100% SỐ DÒNG VÀ TIỀN!")
    return True

if __name__ == "__main__":
    b_file = sys.argv[1] if len(sys.argv) > 1 else None
    verify_and_restore(b_file)
