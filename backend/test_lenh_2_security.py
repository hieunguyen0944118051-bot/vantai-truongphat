"""
Kiểm thử tự động Lệnh 2: BẢO MẬT & PHÂN QUYỀN
Kiểm tra toàn diện:
1. Chặn 401 khi không đăng nhập đối với mọi endpoint sà lan.
2. Token xác thực qua Bearer header & qua httpOnly cookie.
3. Ẩn toàn bộ trường doanh thu/lãi gộp đối với vai trò 'nhap_van_hanh'.
4. Ban Giám Đốc 'ban_giam_doc' chỉ đọc (read-only), bị chặn 403 khi POST/PUT/DELETE.
5. Cô lập dữ liệu theo công ty (Company isolation).
6. Bảo mật headers (X-Content-Type-Options, X-Frame-Options, Referrer-Policy).
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi.testclient import TestClient
from main import app
import auth
import models

client = TestClient(app)

import sqlite3

def setup_test_users():
    db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "transport.db")
    con = sqlite3.connect(db_path)
    cur = con.cursor()
    # admin / alex
    cur.execute("INSERT OR REPLACE INTO users (id, username, password_hash, full_name, role, salan_role, companies, is_active) VALUES (1, 'alex', 'hash', 'Alex (Quản trị)', 'admin', 'quan_tri', 'TP,TPL,NK', 1)")
    # moi
    cur.execute("INSERT OR REPLACE INTO users (id, username, password_hash, full_name, role, salan_role, companies, is_active) VALUES (2, 'moi', 'hash', 'Mới (Vận hành)', 'user', 'nhap_van_hanh', 'TP,TPL,NK', 1)")
    # giamdoc
    cur.execute("INSERT OR REPLACE INTO users (id, username, password_hash, full_name, role, salan_role, companies, is_active) VALUES (3, 'giamdoc', 'hash', 'Ban Giám Đốc', 'user', 'ban_giam_doc', 'TP,TPL,NK', 1)")
    # nhanvien_tpl
    cur.execute("INSERT OR REPLACE INTO users (id, username, password_hash, full_name, role, salan_role, companies, is_active) VALUES (4, 'nhanvien_tpl', 'hash', 'Nhân viên TPL', 'user', 'nhap_van_hanh', 'TPL', 1)")
    con.commit()
    con.close()

def create_token_for(username: str, role: str, salan_role: str, companies: list = None):
    data = {
        "sub": username,
        "role": role,
        "salan_role": salan_role
    }
    if companies is not None:
        data["companies"] = companies
    return auth.create_access_token(data)

def test_unauthenticated_blocked():
    print("\n--- TEST 1: Chặn 401 unauthenticated ---")
    endpoints = [
        ("GET", "/api/salan/danh-muc"),
        ("GET", "/api/salan/chuyen"),
        ("GET", "/api/salan/chuyen/1"),
        ("POST", "/api/salan/chuyen"),
        ("PUT", "/api/salan/chuyen/1"),
        ("DELETE", "/api/salan/chuyen/1"),
        ("GET", "/api/salan/tong-quan"),
        ("POST", "/api/salan/seed-du-lieu-chuan"),
    ]
    for method, path in endpoints:
        if method == "GET":
            res = client.get(path)
        elif method == "POST":
            res = client.post(path, json={})
        elif method == "PUT":
            res = client.put(path, json={})
        elif method == "DELETE":
            res = client.delete(path)
        
        assert res.status_code == 401, f"{method} {path} trả về {res.status_code} thay vì 401!"
    print("✅ 100% endpoint /api/salan/* từ chối truy cập không có xác thực (401)")

def test_auth_via_cookie_and_bearer():
    print("\n--- TEST 2: Xác thực qua Bearer Header và qua Cookie ---")
    admin_token = create_token_for("alex", "admin", "admin")
    
    # 2a. Qua Authorization Header
    res_header = client.get("/api/salan/danh-muc", headers={"Authorization": f"Bearer {admin_token}"})
    assert res_header.status_code == 200, f"Header Bearer thất bại: {res_header.status_code}"
    
    # 2b. Qua Cookie access_token
    res_cookie = client.get("/api/salan/danh-muc", cookies={"access_token": admin_token})
    assert res_cookie.status_code == 200, f"Cookie access_token thất bại: {res_cookie.status_code}"
    
    print("✅ Xác thực hoạt động hoàn hảo qua cả Bearer Header và httpOnly Cookie")

def test_operator_data_hiding():
    print("\n--- TEST 3: Giấu trường doanh thu & lãi gộp với vai trò nhap_van_hanh ---")
    op_token = create_token_for("moi", "user", "nhap_van_hanh")
    headers = {"Authorization": f"Bearer {op_token}"}
    
    # 3a. GET /chuyen
    res = client.get("/api/salan/chuyen", headers=headers)
    assert res.status_code == 200
    trips = res.json()
    assert len(trips) > 0, "Không có chuyến nào để kiểm tra!"
    
    forbidden_fields = [
        'don_gia_thu', 'cuoc_thu', 'vat_thu', 'phai_thu', 
        'xong_trung_thu', 'chu_hang_ho_tro', 'giam_tru', 
        'boi_thuong_chu_hang', 'lai_gop', 'doanh_thu_chu_hang', 'tien_tron_lo'
    ]
    for trip in trips:
        for f in forbidden_fields:
            assert f not in trip or trip[f] is None, f"LỖ HỔNG: Người nhập liệu thấy trường nhạy cảm '{f}' trong danh sách chuyến!"
            
    # 3b. GET /chuyen/{id}
    trip_id = trips[0]["id"]
    res_detail = client.get(f"/api/salan/chuyen/{trip_id}", headers=headers)
    assert res_detail.status_code == 200
    detail = res_detail.json()
    for f in forbidden_fields:
        assert f not in detail or detail[f] is None, f"LỖ HỔNG: Người nhập liệu thấy trường nhạy cảm '{f}' trong chi tiết chuyến!"
        
    # 3c. GET /tong-quan
    res_tq = client.get("/api/salan/tong-quan", headers=headers)
    assert res_tq.status_code == 200
    tq = res_tq.json()
    assert "tong_phai_thu_chu_hang" not in tq, "LỖ HỔNG: Người nhập liệu thấy tong_phai_thu_chu_hang!"
    assert "tong_lai_gop" not in tq, "LỖ HỔNG: Người nhập liệu thấy tong_lai_gop!"
    
    print("✅ Phía server loại bỏ 100% các trường doanh thu, đơn giá thu và lãi gộp đối với nhap_van_hanh")

def test_ban_giam_doc_read_only():
    print("\n--- TEST 4: Ban giám đốc chỉ xem (read-only), chặn POST/PUT/DELETE ---")
    bgd_token = create_token_for("giamdoc", "user", "ban_giam_doc")
    headers = {"Authorization": f"Bearer {bgd_token}"}
    
    # Được xem đầy đủ số liệu
    res = client.get("/api/salan/tong-quan", headers=headers)
    assert res.status_code == 200
    assert "tong_lai_gop" in res.json()
    
    # Bị cấm tạo chuyến (403)
    res_post = client.post("/api/salan/chuyen", headers=headers, json={
        "cong_ty": "TP", "phuong_tien_ma": "ĐT 26284", "chu_hang_ma": "KHACH_HANG_A",
        "ngay_nhan": "2026-09-01", "noi_nhan_ma": "CANG_A", "kl_nhan_kg": 1000000
    })
    assert res_post.status_code == 403, f"Ban giám đốc POST được chuyến: {res_post.status_code}"
    
    # Bị cấm sửa chuyến (403)
    res_put = client.put("/api/salan/chuyen/1", headers=headers, json={"ghi_chu": "Sửa"})
    assert res_put.status_code == 403, f"Ban giám đốc PUT được chuyến: {res_put.status_code}"
    
    # Bị cấm xóa chuyến (403)
    res_del = client.delete("/api/salan/chuyen/1", headers=headers)
    assert res_del.status_code == 403, f"Ban giám đốc DELETE được chuyến: {res_del.status_code}"
    
    print("✅ Ban Giám Đốc xem được toàn bộ lãi gộp nhưng bị chặn 403 tuyệt đối khi cố tình thêm/sửa/xoá")

def test_company_isolation():
    print("\n--- TEST 5: Cô lập dữ liệu theo công ty ---")
    # User chỉ được quyền công ty TPL
    tpl_token = create_token_for("nhanvien_tpl", "user", "nhap_van_hanh", companies=["TPL"])
    headers = {"Authorization": f"Bearer {tpl_token}"}
    
    # Thử lấy danh sách công ty TP -> 403
    res_tp = client.get("/api/salan/chuyen?cong_ty=TP", headers=headers)
    assert res_tp.status_code == 403, f"User TPL xem được công ty TP: {res_tp.status_code}"
    
    # Thử tạo chuyến cho công ty TP -> 403
    res_create_tp = client.post("/api/salan/chuyen", headers=headers, json={
        "cong_ty": "TP", "phuong_tien_ma": "ĐT 26284", "chu_hang_ma": "KHACH_HANG_A",
        "ngay_nhan": "2026-09-01", "noi_nhan_ma": "CANG_A", "kl_nhan_kg": 1000000
    })
    assert res_create_tp.status_code == 403, f"User TPL tạo được chuyến cho TP: {res_create_tp.status_code}"
    
    print("✅ Cô lập công ty chuẩn xác: người dùng không thể xem hay tạo chuyến ngoài công ty được giao")

def test_security_headers():
    print("\n--- TEST 6: Security Response Headers ---")
    res = client.get("/api/health")
    assert res.headers.get("X-Content-Type-Options") == "nosniff"
    assert res.headers.get("X-Frame-Options") == "SAMEORIGIN"
    assert res.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"
    print("✅ Header an ninh X-Content-Type-Options, X-Frame-Options, Referrer-Policy được gán tự động")

if __name__ == "__main__":
    print("==================================================")
    print("BẮT ĐẦU KIỂM THỬ BẢO MẬT & PHÂN QUYỀN (LỆNH 2)")
    print("==================================================")
    setup_test_users()
    test_unauthenticated_blocked()
    test_auth_via_cookie_and_bearer()
    test_operator_data_hiding()
    test_ban_giam_doc_read_only()
    test_company_isolation()
    test_security_headers()
    print("\n==================================================")
    print("🎉 TẤT CẢ 6 BÀI KIỂM THỬ AN NINH ĐÃ VƯỢT QUA 100%!")
    print("==================================================")
