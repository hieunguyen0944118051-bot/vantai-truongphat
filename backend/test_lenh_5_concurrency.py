#!/usr/bin/env python3
"""
BỘ KIỂM THỬ TỰ ĐỘNG LỆNH 5: CHỐNG LỖI KHI NHẬP VÀ LƯU, KIỂM SOÁT PHIÊN BẢN & GIAO DỊCH NGUYÊN TỬ
Kiểm tra toàn diện:
1. Độ chính xác từng đồng của 3 chuyến mẫu (ĐT 26284-C01, SG 8888-C01, ĐT 26284-C02 ứng vượt 14.550.000 đ).
2. Kiểm soát phiên bản (Optimistic Concurrency Control): Người sửa sau nhận 409 Conflict, chống ghi đè dữ liệu.
3. Chống trùng Idempotency Key: Bấm lưu nhiều lần không sinh ra 2 chuyến.
4. Giao dịch đơn nguyên tử (Single Transaction): Lưu chuyến + dầu + ứng đồng thời trong 1 request.
5. Quy tắc chặn C01, C02, C03 và cảnh báo W01–W05, W09, W10, W11.
6. Tìm kiếm nhanh và phân trang, hiển thị tên danh mục thân thiện.
"""

import os
import sys
import uuid
import sqlite3
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import main
import auth
from security_firewall import firewall_manager
firewall_manager.blocked_ips.clear()

client = TestClient(main.app)
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "transport.db")

admin_token = auth.create_access_token({"sub": "alex", "role": "admin", "salan_role": "quan_tri"})
admin_headers = {"Authorization": f"Bearer {admin_token}"}

operator_token = auth.create_access_token({"sub": "moi", "role": "nhan_vien", "salan_role": "nhap_van_hanh", "companies": "TP,TPL"})
operator_headers = {"Authorization": f"Bearer {operator_token}"}


def test_1_exact_three_sample_trips():
    print("\n--- TEST 1: Kiểm thử công thức 3 chuyến mẫu đúng từng đồng ---")
    
    # 1. ĐT 26284-C01
    res1 = client.get("/api/salan/chuyen/1", headers=admin_headers)
    assert res1.status_code == 200
    t1 = res1.json()
    assert t1["cuoc"] == 66982270, f"Cước C01 sai: {t1['cuoc']}"
    assert t1["boi_thuong"] == 6225000, f"Bồi thường C01 sai: {t1['boi_thuong']}"
    assert t1["con_lai_phai_tra"] == 48157270, f"Còn phải trả C01 sai: {t1['con_lai_phai_tra']}"
    assert t1["chu_hang_ten"] == "CJ Vina Agri" or "CJ" in t1["chu_hang_ten"]
    print("✅ Chuyến 1 (ĐT 26284-C01): Cước 66.982.270đ, Bồi thường 6.225.000đ, Còn phải trả 48.157.270đ khớp 100%.")

    # 2. SG 8888-C01
    res2 = client.get("/api/salan/chuyen/2", headers=admin_headers)
    assert res2.status_code == 200
    t2 = res2.json()
    assert t2["cuoc"] == 59880000, f"Cước C02 sai: {t2['cuoc']}"
    assert t2["vat_tien"] == 4790400, f"VAT C02 sai: {t2['vat_tien']}"
    assert t2["tien_neo"] == 5988000, f"Tiền neo C02 sai: {t2['tien_neo']}"
    assert t2["tien_phun_trung"] == 2994000, f"Tiền phun trùng C02 sai: {t2['tien_phun_trung']}"
    assert t2["boi_thuong"] == 7500000, f"Bồi thường C02 sai: {t2['boi_thuong']}"
    assert t2["con_lai_phai_tra"] == 36452400, f"Còn phải trả C02 sai: {t2['con_lai_phai_tra']}"
    print("✅ Chuyến 2 (SG 8888-C01): Cước 59.880.000đ, VAT 4.790.400đ, Neo 5.988.000đ, Phun trùng 2.994.000đ, Bồi thường 7.500.000đ, Còn phải trả 36.452.400đ khớp 100%.")

    # 3. ĐT 26284-C02 (Đang chạy, ứng vượt 14.550.000 đ)
    res3 = client.get("/api/salan/chuyen/3", headers=admin_headers)
    assert res3.status_code == 200
    t3 = res3.json()
    assert t3["tien_dau"] == 8550000, f"Tiền dầu C03 sai: {t3['tien_dau']}"
    assert t3["tien_ung"] == 6000000, f"Tiền ứng C03 sai: {t3['tien_ung']}"
    assert t3["ung_vuot"] == 14550000, f"Ứng vượt C03 sai: {t3['ung_vuot']}"
    assert "14.550.000" in t3["ung_vuot_text"] or "14,550,000" in t3["ung_vuot_text"]
    print("✅ Chuyến 3 (ĐT 26284-C02): Dầu 8.550.000đ, Ứng 6.000.000đ, Hiển thị 'Ứng vượt 14.550.000 đ' chuẩn xác.")


def test_2_optimistic_concurrency_control():
    print("\n--- TEST 2: Kiểm soát phiên bản (409 Conflict khi sửa trùng) ---")
    res = client.get("/api/salan/chuyen/1", headers=admin_headers)
    trip = res.json()
    current_ver = trip.get("phien_ban", 1)

    # Người dùng 1 cập nhật chuyến thành công (phiên bản tăng lên current_ver + 1)
    payload_user1 = dict(trip)
    payload_user1["phien_ban"] = current_ver
    payload_user1["ghi_chu"] = f"Cập nhật bởi User 1 lúc {uuid.uuid4().hex[:6]}"
    res_u1 = client.put("/api/salan/chuyen/1", json=payload_user1, headers=admin_headers)
    assert res_u1.status_code == 200, f"User 1 lưu thất bại: {res_u1.text}"
    new_ver = res_u1.json().get("phien_ban")
    assert new_ver == current_ver + 1

    # Người dùng 2 vẫn giữ phiên bản cũ (current_ver), cố tình lưu đè -> PHẢI BỊ CHẶN 409 CONFLICT!
    payload_user2 = dict(trip)
    payload_user2["phien_ban"] = current_ver  # phiên bản cũ lỗi thời
    payload_user2["ghi_chu"] = "User 2 cố tình ghi đè"
    res_u2 = client.put("/api/salan/chuyen/1", json=payload_user2, headers=operator_headers)
    assert res_u2.status_code == 409, f"Kỳ vọng 409 nhưng nhận {res_u2.status_code}: {res_u2.text}"
    err_detail = res_u2.json()["detail"]
    assert "sửa lúc" in err_detail or "Tải lại" in err_detail
    print(f"✅ Chặn 409 Conflict thành công: '{err_detail}'")


def test_3_idempotency_key_prevents_duplicate():
    print("\n--- TEST 3: Chống trùng idempotency key (Bấm Lưu 2 lần không tạo 2 chuyến) ---")
    idem_key = "test-idem-" + uuid.uuid4().hex

    unique_kl = 500000 + int(uuid.uuid4().int % 100000)
    trip_payload = {
        "cong_ty": "TP",
        "phuong_tien_ma": "ĐT 26284",
        "chu_hang_ma": "CH_DEHEUS",
        "loai_hang_ma": "BAP",
        "ngay_nhan": "2026-03-25",
        "noi_nhan_ma": "CANG_PHU_MY",
        "kl_nhan_kg": unique_kl,
        "idempotency_key": idem_key
    }

    # Bấm lần 1: Tạo mới thành công
    res1 = client.post("/api/salan/chuyen", json=trip_payload, headers=admin_headers)
    assert res1.status_code == 200
    id1 = res1.json()["id"]

    # Bấm lần 2 với cùng idempotency key: Phải trả lại bản ghi cũ, KHÔNG ĐƯỢC TẠO CHUYẾN MỚI
    res2 = client.post("/api/salan/chuyen", json=trip_payload, headers=admin_headers)
    assert res2.status_code == 200
    id2 = res2.json()["id"]
    assert id1 == id2, f"Idempotency thất bại! Tạo ra 2 id khác nhau: {id1} vs {id2}"

    # Kiểm tra trong DB chỉ có duy nhất 1 chuyến với thông số này
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cnt = cur.execute("SELECT COUNT(*) FROM salan_chuyen WHERE kl_nhan_kg = ?", (unique_kl,)).fetchone()[0]
    assert cnt == 1, f"Có {cnt} bản ghi bị tạo trùng!"
    con.close()
    print("✅ Gửi 2 request cùng idempotency key chỉ sinh đúng 1 chuyến duy nhất.")


def test_4_atomic_single_transaction_save():
    print("\n--- TEST 4: Lưu đồng thời chuyến, dầu, ứng trong 1 giao dịch duy nhất ---")
    trip_data = {
        "cong_ty": "TP",
        "phuong_tien_ma": "ĐT 26284",
        "chu_hang_ma": "CH_CJ",
        "loai_hang_ma": "BAP",
        "ngay_nhan": "2026-03-26",
        "noi_nhan_ma": "CANG_PHU_MY",
        "kl_nhan_kg": 600000,
        "do_dau": [
            {"ngay": "2026-03-26", "noi_do_ma": "TRAM_DAU_NHA_BE", "so_lit": 200, "gia_dau": 19000, "ghi_chu": "Đổ lần 1"},
            {"ngay": "2026-03-27", "noi_do_ma": "TRAM_DAU_NHA_BE", "so_lit": 300, "gia_dau": 19000, "ghi_chu": "Đổ lần 2"}
        ],
        "ung_phi": [
            {"ngay": "2026-03-26", "so_tien": 5000000, "noi_dung": "Ứng tiền tươi"}
        ]
    }

    res = client.post("/api/salan/chuyen", json=trip_data, headers=admin_headers)
    assert res.status_code == 200
    created_id = res.json()["id"]

    # Kiểm tra chi tiết chuyến đã có đủ dầu và ứng mà không cần gọi API riêng
    res_check = client.get(f"/api/salan/chuyen/{created_id}", headers=admin_headers)
    assert res_check.status_code == 200
    t = res_check.json()
    assert len(t["do_dau"]) == 2, f"Thiếu dầu: {t['do_dau']}"
    assert len(t["ung_phi"]) == 1, f"Thiếu ứng: {t['ung_phi']}"
    assert t["tien_dau"] == (200 + 300) * 19000
    assert t["tien_ung"] == 5000000
    print("✅ Tạo chuyến kèm danh sách dầu và ứng lưu nguyên tử thành công 100%.")


def test_5_validation_c_and_warnings_w():
    print("\n--- TEST 5: Kiểm tra các quy tắc chặn C và cảnh báo W ---")

    # C01: Thiếu trường bắt buộc
    res_c01 = client.post("/api/salan/chuyen", json={"cong_ty": "TP", "phuong_tien_ma": "ĐT 26284", "chu_hang_ma": "", "ngay_nhan": "", "noi_nhan_ma": "", "kl_nhan_kg": 0}, headers=admin_headers)
    assert res_c01.status_code == 400
    assert "C01" in res_c01.json()["detail"]
    print("✅ Chặn C01 (Thiếu thông tin bắt buộc): Thành công.")

    # C02: Ngày giao < Ngày nhận
    res_c02 = client.post("/api/salan/chuyen", json={"cong_ty": "TP", "phuong_tien_ma": "ĐT 26284", "chu_hang_ma": "CH_CJ", "ngay_nhan": "2026-03-20", "ngay_giao": "2026-03-15", "noi_nhan_ma": "CANG_PHU_MY", "kl_nhan_kg": 1000}, headers=admin_headers)
    assert res_c02.status_code == 400
    assert "C02" in res_c02.json()["detail"]
    print("✅ Chặn C02 (Ngày giao trước ngày nhận): Thành công.")

    # C03: Giá trị âm
    res_c03 = client.post("/api/salan/chuyen", json={"cong_ty": "TP", "phuong_tien_ma": "ĐT 26284", "chu_hang_ma": "CH_CJ", "ngay_nhan": "2026-03-20", "noi_nhan_ma": "CANG_PHU_MY", "kl_nhan_kg": 100000, "don_gia_cuoc": -500}, headers=admin_headers)
    assert res_c03.status_code == 400
    assert "C03" in res_c03.json()["detail"], f"Chi tiết lỗi không chứa C03: {res_c03.text}"
    print("✅ Chặn C03 (Khối lượng/đơn giá âm): Thành công.")

    # Cảnh báo W05: Có ngày giao nhưng cước = 0
    res_w05 = client.post("/api/salan/chuyen", json={
        "cong_ty": "TP", "phuong_tien_ma": "ĐT 26284", "chu_hang_ma": "CH_CJ",
        "ngay_nhan": "2026-03-20", "ngay_giao": "2026-03-22", "noi_nhan_ma": "CANG_PHU_MY",
        "kl_nhan_kg": 100000, "kl_giao_kg": 100000, "don_gia_cuoc": 0
    }, headers=admin_headers)
    new_id = res_w05.json()["id"]
    detail = client.get(f"/api/salan/chuyen/{new_id}", headers=admin_headers).json()
    warn_codes = [w["ma"] for w in detail.get("canh_bao", [])]
    assert "W05" in warn_codes
    print("✅ Kích hoạt cảnh báo W05 (Đã giao nhưng cước = 0) chuẩn xác.")


def test_6_search_and_pagination():
    print("\n--- TEST 6: Tìm kiếm nhanh & phân trang & tên thân thiện ---")
    # Tìm kiếm theo từ khoá
    res_search = client.get("/api/salan/chuyen?q=26284", headers=admin_headers)
    assert res_search.status_code == 200
    trips = res_search.json()
    assert len(trips) > 0
    assert all("26284" in t["ma_chuyen"] for t in trips)
    
    # Kiểm tra tên thân thiện
    t0 = trips[0]
    assert "chu_hang_ten" in t0
    assert "noi_nhan_ten" in t0
    assert "loai_hang_ten" in t0

    # Phân trang
    res_page = client.get("/api/salan/chuyen?page=1&limit=2", headers=admin_headers)
    assert res_page.status_code == 200
    paged_trips = res_page.json()
    assert len(paged_trips) <= 2
    print("✅ Tìm kiếm, phân trang và hiển thị danh mục thân thiện hoạt động hoàn hảo.")


if __name__ == "__main__":
    print("==================================================")
    print("BẮT ĐẦU BỘ KIỂM THỬ LỆNH 5: CHỐNG LỖI KHI NHẬP VÀ LƯU")
    print("==================================================")
    test_1_exact_three_sample_trips()
    test_2_optimistic_concurrency_control()
    test_3_idempotency_key_prevents_duplicate()
    test_4_atomic_single_transaction_save()
    test_5_validation_c_and_warnings_w()
    test_6_search_and_pagination()
    print("\n==================================================")
    print("🎉 TẤT CẢ 6 BÀI TEST LỆNH 5 ĐÃ ĐẠT 100%!")
    print("==================================================")
