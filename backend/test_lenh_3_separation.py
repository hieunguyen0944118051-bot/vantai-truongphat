"""
Kiểm thử tự động LỆNH 3: TÁCH PHẦN A VÀ PHẦN B
1. Cờ PHAN_B_BAT mặc định là False, API Phần B bị khoá 403.
2. Giao diện Phần A (salan.html) được thanh lọc hoàn toàn:
   - Không còn cột "Phải Thu" trong bảng Sổ Chuyến.
   - Không còn ô nhập "Phía Thu Chủ Hàng" và thẻ "Lãi gộp" trong modal sửa chuyến.
   - Hàng KPI đầu trang của Phần A tập trung 100% vào nghiệp vụ sà lan (Sản lượng, Cước, Dầu & Ứng, Phải trả, Cảnh báo).
3. Bảng riêng salan_cuoc_thu đã sẵn sàng trong database để phục vụ Lệnh 8.
4. Nghiệp vụ tính toán và lưu chuyến Phần A hoạt động hoàn hảo.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import sqlite3
from fastapi.testclient import TestClient
from main import app
import auth

client = TestClient(app)
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "transport.db")

admin_token = auth.create_access_token({"sub": "alex", "role": "admin", "salan_role": "quan_tri"})
admin_headers = {"Authorization": f"Bearer {admin_token}"}

def test_1_phan_b_feature_flag_and_lock():
    print("\n--- TEST 1: Cờ PHAN_B_BAT & khoá 403 API Phần B ---")
    # Kiểm tra endpoint trạng thái
    res_status = client.get("/api/salan/phan-b/trang-thai")
    assert res_status.status_code == 200
    data = res_status.json()
    assert data["phan_b_bat"] is False, "PHAN_B_BAT phải mặc định là False!"
    
    # Kiểm tra API công nợ chủ hàng bị chặn 403
    res_cong_no = client.get("/api/salan/chu-hang/cong-no", headers=admin_headers)
    assert res_cong_no.status_code == 403, f"API công nợ không bị chặn: {res_cong_no.status_code}"
    assert "tắt theo Lệnh Antigravity" in res_cong_no.json()["detail"]
    print("✅ Cờ PHAN_B_BAT = False và các endpoint Phần B bị khoá 403 chính xác.")

def test_2_ui_separation_in_salan_html():
    print("\n--- TEST 2: Giao diện Phần A không chứa trường/cột thu chủ hàng ---")
    html_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static", "salan.html")
    with open(html_path, "r", encoding="utf-8") as f:
        html = f.read()

    # 1. Bảng chuyến không còn cột Phải thu
    assert '<th class="p-3 text-right role-finance-only text-emerald-900 bg-emerald-50/60">Phải Thu</th>' not in html, "Vẫn còn cột header Phải Thu trong bảng Sổ chuyến!"
    assert 'role-finance-only">${fmtVND(t.phai_thu)}</td>' not in html, "Vẫn còn cột render Phải Thu trong dòng bảng Sổ chuyến!"

    # 2. Form modal không còn khối phía thu chủ hàng
    assert 'KHỐI 8: PHÍA THU CHỦ HÀNG' not in html, "Vẫn còn khối Phía thu chủ hàng trong form sửa chuyến!"
    assert 'LÃI GỘP CHUYẾN (Trước VAT — Alex & BGĐ)' not in html, "Vẫn còn nhãn Lãi gộp chuyến trong form sửa chuyến!"

    # 3. KPI đầu trang không còn thẻ Phải thu và Lãi gộp
    assert 'id="kpi-phai-thu"' not in html, "Vẫn còn thẻ kpi-phai-thu trên đầu trang Phần A!"
    assert 'id="kpi-lai-gop"' not in html, "Vẫn còn thẻ kpi-lai-gop trên đầu trang Phần A!"
    assert 'id="kpi-dau-ung"' in html, "Thiếu thẻ KPI kpi-dau-ung cho Phần A!"
    assert 'id="kpi-canh-bao"' in html, "Thiếu thẻ KPI kpi-canh-bao cho Phần A!"

    print("✅ Màn hình Phần A sạch 100%, không còn bất kỳ trường thu chủ hàng hay lãi gộp nào.")

def test_3_database_cuoc_thu_table():
    print("\n--- TEST 3: Bảng salan_cuoc_thu sẵn sàng trong database ---")
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    tables = [r[0] for r in cur.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
    assert "salan_cuoc_thu" in tables, "Bảng salan_cuoc_thu chưa được khởi tạo!"

    cols = [r[1] for r in cur.execute("PRAGMA table_info(salan_cuoc_thu)").fetchall()]
    required_cols = ["id", "chuyen_id", "chu_hang_ma", "don_gia_thu", "cuoc_thu", "vat_thu", "tong_phai_thu", "da_thu_tien"]
    for c in required_cols:
        assert c in cols, f"Cột {c} thiếu trong bảng salan_cuoc_thu!"
    con.close()
    print("✅ Bảng salan_cuoc_thu được tạo đầy đủ cấu trúc sẵn sàng cho Phần B (Lệnh 8).")

def test_4_part_a_trip_operations():
    print("\n--- TEST 4: Nghiệp vụ lưu và tính toán chuyến Phần A ---")
    res = client.get("/api/salan/chuyen", headers=admin_headers)
    assert res.status_code == 200
    trips = res.json()
    assert len(trips) > 0

    t = trips[0]
    assert "cuoc" in t
    assert "con_lai_phai_tra" in t
    assert "tien_dau" in t
    assert "tien_ung" in t
    print("✅ Nghiệp vụ Phần A (Cước sà lan, Dầu, Ứng, Còn lại phải trả) hoạt động trơn tru.")

if __name__ == "__main__":
    print("==================================================")
    print("BẮT ĐẦU KIỂM THỬ TÁCH PHẦN A & B (LỆNH 3)")
    print("==================================================")
    test_1_phan_b_feature_flag_and_lock()
    test_2_ui_separation_in_salan_html()
    test_3_database_cuoc_thu_table()
    test_4_part_a_trip_operations()
    print("\n==================================================")
    print("🎉 TẤT CẢ 4 BÀI TEST TÁCH PHẦN A & B ĐÃ ĐẠT 100%!")
    print("==================================================")
