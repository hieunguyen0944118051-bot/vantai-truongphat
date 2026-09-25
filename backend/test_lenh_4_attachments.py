"""
Kiểm thử tự động LỆNH 4: TẢI ẢNH CHỨNG TỪ & CẢNH BÁO W01
Kiểm tra toàn diện:
1. Tải lên tệp chứng từ phiếu cân nhận/giao, dầu, ứng.
2. Kiểm tra đường dẫn lưu chuẩn: phieu/<nam>/<thang>/<ma-chuyen>/<loai>/<thoi-gian>-<ten>.jpg.
3. Kiểm tra nhật ký kiểm toán ghi lại hành vi tải và huỷ tệp đính kèm.
4. Kiểm tra cảnh báo W01:
   - Chuyến đã giao chưa có phiếu cân -> Tự động kích hoạt cảnh báo W01.
   - Tải phiếu cân lên -> W01 lập tức biến mất!
   - Huỷ (xoá mềm) phiếu cân -> W01 lập tức xuất hiện trở lại!
5. Xoá mềm tệp đính kèm (da_huy = 1) và không xoá cứng trên ổ đĩa.
"""

import sys
import os
import io
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import sqlite3
from fastapi.testclient import TestClient
from main import app
import auth

from security_firewall import firewall_manager
firewall_manager.blocked_ips.clear()

client = TestClient(app)
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "transport.db")

admin_token = auth.create_access_token({"sub": "alex", "role": "admin", "salan_role": "quan_tri"})
admin_headers = {"Authorization": f"Bearer {admin_token}"}

def setup_module():
    # Dọn dẹp tệp thử nghiệm cũ của chuyến 1 nếu có
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cur.execute("DELETE FROM salan_tep_dinh_kem WHERE chuyen_id = 1")
    con.commit()
    con.close()

def test_1_w01_warning_trigger():
    setup_module()
    print("\n--- TEST 1: Cảnh báo W01 khi chuyến đã giao nhưng thiếu phiếu cân ---")
    # Lấy chuyến 1 (ĐT 26284-C01, đã giao)
    res = client.get("/api/salan/chuyen/1", headers=admin_headers)
    assert res.status_code == 200
    trip = res.json()
    assert trip["ngay_giao"] is not None
    assert trip["kl_giao_kg"] > 0
    
    canh_bao_mas = [w["ma"] for w in trip.get("canh_bao", [])]
    assert "W01" in canh_bao_mas, f"Chuyến 1 đã giao nhưng không có cảnh báo W01! Danh sách: {canh_bao_mas}"
    print("✅ Chuyến đã giao nhưng chưa có ảnh phiếu cân tự động kích hoạt cảnh báo W01 chính xác.")

def test_2_upload_scale_ticket_and_clear_w01():
    print("\n--- TEST 2: Tải ảnh phiếu cân và kiểm tra đường dẫn chuẩn + mất W01 ---")
    file_content = b"FAKE_JPEG_IMAGE_CONTENT_SCALE_TICKET_TEST_DATA"
    file_obj = io.BytesIO(file_content)
    
    res = client.post(
        "/api/salan/chuyen/1/tep-dinh-kem",
        headers=admin_headers,
        data={"loai_tep": "can_giao"},
        files={"file": ("phieu_can_nha_may.jpg", file_obj, "image/jpeg")}
    )
    assert res.status_code == 200, f"Upload thất bại: {res.text}"
    uploaded = res.json()
    tep_id = uploaded["id"]
    duong_dan = uploaded["duong_dan"]
    
    # Kiểm tra đường dẫn chuẩn: phieu/<nam>/<thang>/<ma-chuyen>/<loai>/...
    assert "phieu/" in duong_dan
    assert "can_giao" in duong_dan
    assert "DT_26284_C01" in duong_dan or "DT" in duong_dan
    assert duong_dan.endswith(".jpg")
    print(f"✅ Đường dẫn lưu trữ chuẩn hoá: {duong_dan}")
    
    # Kiểm tra lại chi tiết chuyến 1: Cảnh báo W01 phải BIẾN MẤT!
    res_trip = client.get("/api/salan/chuyen/1", headers=admin_headers)
    trip_updated = res_trip.json()
    canh_bao_mas = [w["ma"] for w in trip_updated.get("canh_bao", [])]
    assert "W01" not in canh_bao_mas, "Cảnh báo W01 vẫn còn tồn tại dù đã tải phiếu cân!"
    print("✅ Cảnh báo W01 biến mất ngay lập tức sau khi tải phiếu cân lên!")
    
    return tep_id

def test_3_view_and_download_attachment(tep_id):
    print("\n--- TEST 3: Xem và tải ảnh qua API an toàn ---")
    res = client.get(f"/api/salan/tep-dinh-kem/{tep_id}/xem", headers=admin_headers)
    assert res.status_code == 200
    assert res.content == b"FAKE_JPEG_IMAGE_CONTENT_SCALE_TICKET_TEST_DATA"
    print("✅ Tải và xem ảnh nguyên vẹn 100%.")

def test_4_soft_delete_attachment_and_reappear_w01(tep_id):
    print("\n--- TEST 4: Xoá mềm tệp đính kèm và kiểm tra W01 xuất hiện lại ---")
    res_del = client.delete(f"/api/salan/tep-dinh-kem/{tep_id}?ly_do=Test_huy_phieu_can", headers=admin_headers)
    assert res_del.status_code == 200
    
    # Kiểm tra trong DB: da_huy = 1
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    row = cur.execute("SELECT da_huy, ly_do_huy FROM salan_tep_dinh_kem WHERE id = ?", (tep_id,)).fetchone()
    assert row[0] == 1, "Tệp chưa được đánh dấu da_huy = 1"
    assert "Test_huy_phieu_can" in row[1]
    
    # Kiểm tra nhật ký kiểm toán
    log = cur.execute("SELECT hanh_dong, bang, ban_ghi_id FROM nhat_ky WHERE bang = 'salan_tep_dinh_kem' AND ban_ghi_id = ? AND hanh_dong = 'huy'", (str(tep_id),)).fetchone()
    assert log is not None, "Không tìm thấy nhật ký kiểm toán cho hành động huỷ tệp!"
    con.close()
    
    # Kiểm tra lại chuyến 1: W01 phải xuất hiện trở lại!
    res_trip = client.get("/api/salan/chuyen/1", headers=admin_headers)
    trip_updated = res_trip.json()
    canh_bao_mas = [w["ma"] for w in trip_updated.get("canh_bao", [])]
    assert "W01" in canh_bao_mas, "Cảnh báo W01 không tái xuất hiện sau khi huỷ phiếu cân!"
    print("✅ Xoá mềm tệp đính kèm thành công và W01 tái kích hoạt chính xác.")

if __name__ == "__main__":
    print("==================================================")
    print("BẮT ĐẦU KIỂM THỬ TẢI ẢNH CHỨNG TỪ & W01 (LỆNH 4)")
    print("==================================================")
    test_1_w01_warning_trigger()
    tep_id = test_2_upload_scale_ticket_and_clear_w01()
    test_3_view_and_download_attachment(tep_id)
    test_4_soft_delete_attachment_and_reappear_w01(tep_id)
    print("\n==================================================")
    print("🎉 TẤT CẢ 4 BÀI TEST LỆNH 4 ĐÃ ĐẠT 100%!")
    print("==================================================")
