#!/usr/bin/env python3
"""
Bộ kiểm thử tự động LỆNH 1 — LƯỚI AN TOÀN DỮ LIỆU.
Bao gồm 5 bài test bắt buộc theo quy định của tài liệu hướng dẫn.
"""

import os
import sqlite3
from fastapi.testclient import TestClient
import main
from backup_database import backup_database
from restore_database import verify_and_restore

client = TestClient(main.app)
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "transport.db")

def test_1_soft_delete_dau():
    """1. Gọi API xoá dầu -> dòng vẫn còn trong DB, có da_huy = 1, có dòng nhật ký."""
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    
    # Tạo 1 dòng dầu thử nghiệm
    cur.execute("""
    INSERT INTO salan_do_dau (chuyen_id, ngay, noi_do_ma, so_lit, gia_dau, tien_dau, ghi_chu, da_huy)
    VALUES (1, '2026-03-02', 'TRAM_DAU_NHA_BE', 100, 19000, 1900000, 'Dầu test xoá mềm', 0)
    """)
    dau_id = cur.lastrowid
    con.commit()
    con.close()

    # Gọi API xoá
    res = client.delete(f"/api/salan/dau/{dau_id}?ly_do=Huy%20do%20sai%20so%20lit")
    assert res.status_code == 200, f"Lỗi gọi API xoá dầu: {res.text}"

    # Kiểm tra lại DB: dòng KHÔNG bị xoá mà được đánh dấu da_huy = 1
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    row = cur.execute("SELECT da_huy, ly_do_huy, huy_boi FROM salan_do_dau WHERE id = ?", (dau_id,)).fetchone()
    assert row is not None, "Dòng dầu đã bị xoá cứng khỏi database! Vi phạm an toàn dữ liệu!"
    assert row[0] == 1, "Dòng dầu chưa được đánh dấu da_huy = 1"
    assert "Huy do sai so lit" in (row[1] or ""), "Lý do huỷ không được lưu"

    # Kiểm tra có bản ghi nhật ký
    log = cur.execute("SELECT hanh_dong, bang, ban_ghi_id FROM nhat_ky WHERE bang = 'salan_do_dau' AND ban_ghi_id = ? AND hanh_dong = 'huy'", (str(dau_id),)).fetchone()
    assert log is not None, "Không tìm thấy bản ghi nhật ký kiểm toán cho hành động huỷ dầu!"
    con.close()
    print("✅ TEST 1 ĐẠT: Xoá dầu là xoá mềm, dòng còn nguyên vẹn và nhật ký được ghi nhận.")

def test_2_audit_log_sua_chuyen():
    """2. Sửa đơn giá cước một chuyến -> nhật ký có giá trị cũ và mới."""
    # Lấy thông tin hiện tại của chuyến 1
    t1_res = client.get("/api/salan/chuyen/1")
    assert t1_res.status_code == 200
    t1 = t1_res.json()
    don_gia_cu = t1["don_gia_cuoc"]
    don_gia_moi = don_gia_cu + 1000

    # Cập nhật chuyến với đơn giá mới
    t1["don_gia_cuoc"] = don_gia_moi
    t1["nguoi_nhap"] = "Alex"
    put_res = client.put("/api/salan/chuyen/1", json=t1)
    assert put_res.status_code == 200

    # Kiểm tra nhật ký
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    log = cur.execute("""
    SELECT hanh_dong, gia_tri_cu, gia_tri_moi 
    FROM nhat_ky 
    WHERE bang = 'salan_chuyen' AND ban_ghi_id = '1' AND hanh_dong = 'sua'
    ORDER BY id DESC LIMIT 1
    """).fetchone()

    assert log is not None, "Không tìm thấy bản ghi nhật ký khi sửa chuyến!"
    assert str(don_gia_cu) in log[1], f"Đơn giá cũ {don_gia_cu} không có trong gia_tri_cu"
    assert str(don_gia_moi) in log[2], f"Đơn giá mới {don_gia_moi} không có trong gia_tri_moi"

    # Trả lại đơn giá cũ
    t1["don_gia_cuoc"] = don_gia_cu
    client.put("/api/salan/chuyen/1", json=t1)
    con.close()
    print("✅ TEST 2 ĐẠT: Sửa chuyến ghi đầy đủ giá trị cũ và giá trị mới vào nhật ký kiểm toán.")

def test_3_immutable_audit_log():
    """3. Thử sửa / xoá dòng nhật ký -> bị chặn bởi trigger database."""
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    
    # Lấy 1 id nhật ký bất kỳ
    log_id = cur.execute("SELECT id FROM nhat_ky LIMIT 1").fetchone()[0]

    # Thử UPDATE dòng nhật ký -> Phải bắn ngoại lệ
    update_blocked = False
    try:
        cur.execute("UPDATE nhat_ky SET hanh_dong = 'hack' WHERE id = ?", (log_id,))
        con.commit()
    except sqlite3.DatabaseError as e:
        update_blocked = True
        assert "bất biến" in str(e)
    assert update_blocked, "LỖI NGUY HIỂM: Dòng nhật ký có thể bị sửa!"

    # Thử DELETE dòng nhật ký -> Phải bắn ngoại lệ
    delete_blocked = False
    try:
        cur.execute("DELETE FROM nhat_ky WHERE id = ?", (log_id,))
        con.commit()
    except sqlite3.DatabaseError as e:
        delete_blocked = True
        assert "bất biến" in str(e)
    assert delete_blocked, "LỖI NGUY HIỂM: Dòng nhật ký có thể bị xoá!"

    con.close()
    print("✅ TEST 3 ĐẠT: Bảng nhật ký bất biến 100%, trigger chặn mọi thao tác UPDATE/DELETE.")

def test_4_protected_seed():
    """4. Gọi seed khi database đã có dữ liệu -> 403, dữ liệu không đổi."""
    res = client.post("/api/salan/seed-du-lieu-chuan")
    assert res.status_code == 403, f"Seed không bị chặn: {res.status_code} - {res.text}"
    assert "BẢO VỆ DỮ LIỆU" in res.json()["detail"]
    print("✅ TEST 4 ĐẠT: API seed bị khoá tuyệt đối khi database đã có dữ liệu, trả về mã 403.")

def test_5_backup_and_restore_consistency():
    """5. Sao lưu rồi khôi phục vào database tạm -> số dòng và tổng tiền khớp 100%."""
    backup_file = backup_database("test_lenh_1")
    assert os.path.exists(backup_file), "File sao lưu không tồn tại!"
    
    # Kiểm tra khôi phục và so khớp
    verified = verify_and_restore(backup_file)
    assert verified is True, "Khôi phục hoặc so khớp dữ liệu thất bại!"
    print("✅ TEST 5 ĐẠT: Sao lưu và khôi phục vào DB tạm khớp 100% từng đồng và từng số dòng.")

if __name__ == "__main__":
    print("🚀 BẮT ĐẦU CHẠY BỘ KIỂM THỬ AN TOÀN LỆNH 1...\n")
    test_1_soft_delete_dau()
    test_2_audit_log_sua_chuyen()
    test_3_immutable_audit_log()
    test_4_protected_seed()
    test_5_backup_and_restore_consistency()
    print("\n🎯 TẤT CẢ 5 BÀI TEST BẮT BUỘC CỦA LỆNH 1 ĐỀU ĐẠT 100%!")
