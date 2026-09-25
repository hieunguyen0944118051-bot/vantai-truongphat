"""
BỘ KIỂM THỬ TỔNG THỂ VÀ ĐÓNG VAI 3 NGƯỜI DÙNG (LỆNH 7)
Đóng vai 3 đối tượng người dùng thực tế:
1. nhap_van_hanh (Mới): Tạo chuyến -> tải phiếu cân -> giao hàng -> thử xem lãi gộp (bị ẩn) -> thử tạo thanh toán (bị chặn 403).
2. ban_giam_doc (Giám Đốc): Xem toàn bộ số liệu và lãi gộp -> thử ghi/sửa dữ liệu (bị chặn 403).
3. quan_tri (Alex): Toàn quyền vận hành -> lập phiếu thanh toán -> in phiếu -> khoá sổ -> mở khoá -> huỷ phiếu.
"""

import sys
import os
import unittest
import io
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from main import app
import auth
from security_firewall import firewall_manager
firewall_manager.blocked_ips.clear()

class TestLenh7E2EFlow(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

        cls.token_nvh = auth.create_access_token({"sub": "moi", "role": "nhan_vien", "salan_role": "nhap_van_hanh", "companies": "TP,TPL"})
        cls.headers_nvh = {"Authorization": f"Bearer {cls.token_nvh}"}

        cls.token_bgd = auth.create_access_token({"sub": "giamdoc", "role": "nhan_vien", "salan_role": "ban_giam_doc", "companies": "TP,TPL,NK"})
        cls.headers_bgd = {"Authorization": f"Bearer {cls.token_bgd}"}

        cls.token_admin = auth.create_access_token({"sub": "alex", "role": "admin", "salan_role": "quan_tri", "companies": "TP,TPL,NK"})
        cls.headers_admin = {"Authorization": f"Bearer {cls.token_admin}"}

    def test_e2e_full_workflow(self):
        print("\n==================================================")
        print("BẮT ĐẦU KIỂM THỬ TRỌN LUỒNG 3 VAI TRÒ NGƯỜI DÙNG")
        print("==================================================")

        # -------------------------------------------------------------
        # BƯỚC 1: NHẬP VẬN HÀNH (MỚI) TẠO CHUYẾN SÀ LAN MỚI
        # -------------------------------------------------------------
        trip_payload = {
            "cong_ty": "TP",
            "phuong_tien_ma": "ĐT 26284",
            "chu_hang_ma": "CH_GREENFEED",
            "loai_hang_ma": "BAP",
            "so_lo_tau": "Lô 99 E2E",
            "ngay_nhan": "2026-03-25",
            "noi_nhan_ma": "CANG_PHU_MY",
            "kl_nhan_kg": 1150000,
            "ngay_giao": "2026-03-28",
            "nha_may_giao_ma": "NM_CJ_CAN_DUOC",
            "kl_giao_kg": 1148500,
            "don_gia_cuoc": 63000,
            "vat_pct": 0.0,
            "co_tinh_neo": True,
            "don_gia_neo": 3000,
            "ngay_cho_phep": 2,
            "so_bang_ke": "BK-E2E-001",
            "do_dau": [
                {"ngay": "2026-03-25", "noi_do_ma": "TRAM_DAU_NHA_BE", "so_lit": 500, "gia_dau": 19500, "tien_dau": 9750000, "ghi_chu": "Đổ dầu chuyến E2E"}
            ],
            "ung_phi": [
                {"ngay": "2026-03-26", "so_tien": 5000000, "noi_dung": "Ứng tiền luồng lạch"}
            ]
        }
        res_create = self.client.post("/api/salan/chuyen", json=trip_payload, headers=self.headers_nvh)
        self.assertEqual(res_create.status_code, 200)
        trip_id = res_create.json()["id"]
        ma_chuyen = res_create.json()["ma_chuyen"]
        print(f"👉 1. [Mới] Đã tạo chuyến thành công: ID {trip_id} - Mã: {ma_chuyen}")

        # Tải ảnh phiếu cân
        fake_jpg = io.BytesIO(b"\xff\xd8\xff\xe0\x00\x10JFIF" + b"scale_ticket_binary_data")
        res_upload = self.client.post(
            f"/api/salan/chuyen/{trip_id}/tep-dinh-kem",
            data={"loai_tep": "can_giao", "ghi_chu": "Phiếu cân nhà máy"},
            files={"file": ("phieu_can_giao.jpg", fake_jpg, "image/jpeg")},
            headers=self.headers_nvh
        )
        self.assertEqual(res_upload.status_code, 200)
        print("👉 2. [Mới] Đã tải ảnh phiếu cân giao thành công.")

        # Kiểm tra bảo mật: Mới xem chuyến không có lãi gộp hoặc giá thu
        res_view_nvh = self.client.get(f"/api/salan/chuyen/{trip_id}", headers=self.headers_nvh)
        self.assertEqual(res_view_nvh.status_code, 200)
        nvh_data = res_view_nvh.json()
        self.assertNotIn("lai_gop", nvh_data)
        self.assertNotIn("don_gia_thu", nvh_data)
        self.assertNotIn("phai_thu", nvh_data)
        print("👉 3. [Bảo mật] Kiểm tra dữ liệu trả về cho Mới: hoàn toàn sạch các trường tài chính thu & lãi gộp.")

        # Mới thử tạo thanh toán -> Bị chặn 403
        res_nvh_pay = self.client.post("/api/salan/thanh-toan", json={
            "ngay": "2026-03-28", "cong_ty": "TP", "so_tien": 1000000, "phan_bo": [{"chuyen_id": trip_id, "so_tien_phan_bo": 1000000}]
        }, headers=self.headers_nvh)
        self.assertEqual(res_nvh_pay.status_code, 403)
        print("👉 4. [Phân quyền] Mới bị chặn 403 khi cố tình tạo phiếu thanh toán.")

        # -------------------------------------------------------------
        # BƯỚC 2: BAN GIÁM ĐỐC (GIÁM ĐỐC) XEM SỐ LIỆU & LÃI GỘP
        # -------------------------------------------------------------
        res_view_bgd = self.client.get(f"/api/salan/chuyen/{trip_id}", headers=self.headers_bgd)
        self.assertEqual(res_view_bgd.status_code, 200)
        bgd_data = res_view_bgd.json()
        self.assertIn("lai_gop", bgd_data)
        print(f"👉 5. [Ban Giám Đốc] Xem được toàn bộ số liệu và lãi gộp: {bgd_data['lai_gop']:,} đ")

        # Ban Giám Đốc thử sửa chuyến -> Bị chặn 403 (Read-only)
        res_bgd_edit = self.client.put(f"/api/salan/chuyen/{trip_id}", json={
            "cong_ty": "TP", "phuong_tien_ma": "ĐT 26284", "chu_hang_ma": "CH_GREENFEED",
            "ngay_nhan": "2026-03-25", "noi_nhan_ma": "CANG_PHU_MY", "kl_nhan_kg": 1150000,
            "phien_ban": bgd_data["phien_ban"]
        }, headers=self.headers_bgd)
        self.assertEqual(res_bgd_edit.status_code, 403)
        print("👉 6. [Phân quyền] Ban Giám Đốc bị chặn 403 khi cố tình sửa chuyến (chuẩn vai trò chỉ xem).")

        # -------------------------------------------------------------
        # BƯỚC 3: QUẢN TRỊ VIÊN (ALEX) THANH TOÁN & IN PHIẾU
        # -------------------------------------------------------------
        # Lấy số nợ còn lại của chuyến vừa tạo
        unpaid = self.client.get(f"/api/salan/thanh-toan/chuyen-chua-tra?cong_ty=TP&phuong_tien_ma=ĐT 26284", headers=self.headers_admin).json()
        this_trip = next((t for t in unpaid if t["id"] == trip_id), None)
        self.assertIsNotNone(this_trip)
        con_no = this_trip["con_no"]
        print(f"👉 7. [Alex] Xác nhận số tiền còn phải trả chuyến {ma_chuyen}: {con_no:,} đ")

        # Lập phiếu thanh toán
        res_pay = self.client.post("/api/salan/thanh-toan", json={
            "ngay": "2026-03-28",
            "cong_ty": "TP",
            "doi_tac_id": 1,
            "phuong_tien_ma": "ĐT 26284",
            "so_tien": con_no,
            "nguoi_duyet": "GĐ",
            "ghi_chu": f"Quyết toán chuyến {ma_chuyen}",
            "phan_bo": [{"chuyen_id": trip_id, "so_tien_phan_bo": con_no}]
        }, headers=self.headers_admin)
        self.assertEqual(res_pay.status_code, 200)
        pay_data = res_pay.json()
        payment_id = pay_data["id"]
        so_phieu = pay_data["so_phieu"]
        print(f"👉 8. [Alex] Đã tạo phiếu thanh toán thật: {so_phieu} ({con_no:,} đ - {pay_data['so_tien_bang_chu']})")

        # Kiểm tra chuyến đã tự động chuyển sang Đã trả & Khoá sổ
        trip_after_pay = self.client.get(f"/api/salan/chuyen/{trip_id}", headers=self.headers_admin).json()
        self.assertEqual(trip_after_pay["da_tra_tien"], 1)
        self.assertEqual(trip_after_pay["khoa_so"], 1)
        print("👉 9. [Hệ thống] Chuyến đã tự động chuyển trạng thái 'Đã trả' và 'Khoá sổ'.")

        # In phiếu thanh toán chuẩn A4
        res_print = self.client.get(f"/api/salan/thanh-toan/{payment_id}", headers=self.headers_admin)
        self.assertEqual(res_print.status_code, 200)
        print_data = res_print.json()
        self.assertEqual(print_data["so_phieu"], so_phieu)
        self.assertEqual(len(print_data["danh_sach_chuyen"]), 1)
        print(f"👉 10. [In phiếu] Xuất dữ liệu in phiếu A4 thành công cho {print_data['doi_tac_ten']}.")

        # Mở khoá sổ chuyến
        res_unlock = self.client.post(f"/api/salan/chuyen/{trip_id}/mo-khoa", json={"ly_do": "Mở để đối chiếu chi phí phát sinh"}, headers=self.headers_admin)
        self.assertEqual(res_unlock.status_code, 200)
        print("👉 11. [Alex] Mở khoá sổ chuyến thành công kèm lý do kiểm toán.")

        # Huỷ phiếu thanh toán
        res_cancel = self.client.delete(f"/api/salan/thanh-toan/{payment_id}?ly_do=Huỷ phiếu sau kiểm thử", headers=self.headers_admin)
        self.assertEqual(res_cancel.status_code, 200)
        
        trip_reverted = self.client.get(f"/api/salan/chuyen/{trip_id}", headers=self.headers_admin).json()
        self.assertEqual(trip_reverted["da_tra_tien"], 0)
        self.assertEqual(trip_reverted["khoa_so"], 0)
        print("👉 12. [Hệ thống] Huỷ phiếu thanh toán mềm thành công: chuyến tự phục hồi trạng thái 'Chưa trả'.")
        print("\n==================================================")
        print("🎉 TOÀN BỘ LUỒNG E2E ĐÃ HOÀN TẤT THÀNH CÔNG 100%!")
        print("==================================================")

    @classmethod
    def tearDownClass(cls):
        import sqlite3
        con = sqlite3.connect("backend/transport.db")
        con.execute("UPDATE salan_thanh_toan SET da_huy = 1 WHERE da_huy = 0")
        con.execute("UPDATE salan_chuyen SET da_tra_tien = 0, khoa_so = 0, ngay_thanh_toan = NULL WHERE id = 1")
        con.commit()
        con.close()

if __name__ == "__main__":
    unittest.main(verbosity=2)
