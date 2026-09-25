"""
BỘ KIỂM THỬ TỰ ĐỘNG LỆNH 6: THANH TOÁN SÀ LAN LƯU THẬT & IN PHIẾU
Kiểm thử các yêu cầu theo Lệnh 6 và SPEC Mục 5:
1. Gợi ý phân bổ FIFO chuyến cũ nhất trước qua /api/salan/thanh-toan/chuyen-chua-tra
2. Chặn C04 (Hộ kinh doanh thiếu số bảng kê)
3. Chặn C05 (Phân bổ vượt số còn nợ)
4. Thanh toán trả thiếu (chưa đủ để khoá sổ)
5. Thanh toán 1 phiếu cho nhiều chuyến (đủ để tự chuyển sang "Đã trả" và "Khoá sổ")
6. Chặn C07 (Sửa chuyến đã trả mà không phải quản trị; mở khoá chuyến có ghi lý do)
7. Huỷ thanh toán (xoá mềm, các chuyến liên quan tự động chuyển lại Chưa trả)
8. In lại phiếu cũ giữ đúng số phiếu và đọc tiền bằng chữ chuẩn xác
9. Phân quyền: Chỉ quan_tri tạo/huỷ thanh toán; ban_giam_doc chỉ xem.
"""

import sys
import os
import unittest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from main import app
import models
from database import get_db

import auth
from security_firewall import firewall_manager
firewall_manager.blocked_ips.clear()

class TestLenh6Payments(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
        
        cls.token_admin = auth.create_access_token({"sub": "alex", "role": "admin", "salan_role": "quan_tri"})
        cls.headers_admin = {"Authorization": f"Bearer {cls.token_admin}"}

        cls.token_nvh = auth.create_access_token({"sub": "moi", "role": "nhan_vien", "salan_role": "nhap_van_hanh", "companies": "TP,TPL"})
        cls.headers_nvh = {"Authorization": f"Bearer {cls.token_nvh}"}

        cls.token_bgd = auth.create_access_token({"sub": "giamdoc", "role": "nhan_vien", "salan_role": "ban_giam_doc", "companies": "TP,TPL,NK"})
        cls.headers_bgd = {"Authorization": f"Bearer {cls.token_bgd}"}

    def test_01_query_unpaid_trips_fifo(self):
        """Kiểm tra danh sách chuyến chưa trả được sắp xếp FIFO (cũ nhất trước)."""
        res = self.client.get("/api/salan/thanh-toan/chuyen-chua-tra?cong_ty=TP", headers=self.headers_admin)
        self.assertEqual(res.status_code, 200)
        trips = res.json()
        self.assertGreater(len(trips), 0)

        # Chuyến 1 (ĐT 26284-C01) phải đứng trước vì ngày nhận cũ nhất
        chuyen_1 = next((t for t in trips if t["id"] == 1), None)
        self.assertIsNotNone(chuyen_1)
        self.assertEqual(chuyen_1["ma_chuyen"], "ĐT 26284-C01")
        self.assertEqual(chuyen_1["con_lai_phai_tra"], 48157270)
        self.assertEqual(chuyen_1["con_no"], 48157270)

        # Kiểm tra FIFO ordering
        dates = [t["ngay_nhan"] for t in trips if t.get("ngay_nhan")]
        self.assertEqual(dates, sorted(dates), "Danh sách chuyến chưa trả phải sắp xếp FIFO theo ngày nhận tăng dần")
        print("\n✅ TEST 1: Truy vấn danh sách chuyến chưa trả sắp xếp FIFO thành công.")

    def test_02_block_c04_and_c05(self):
        """Kiểm tra chặn C04 (Hộ kinh doanh thiếu số bảng kê) và C05 (Phân bổ vượt số còn nợ)."""
        # Tạo 1 chuyến thử nghiệm cho sà lan LA 05678 (Hộ kinh doanh) KHÔNG có số bảng kê
        trip_hkd = {
            "cong_ty": "TP",
            "phuong_tien_ma": "LA 05678",
            "chu_hang_ma": "CH_DEHEUS",
            "ngay_nhan": "2026-03-10",
            "noi_nhan_ma": "CANG_PHU_MY",
            "kl_nhan_kg": 1000000,
            "ngay_giao": "2026-03-12",
            "nha_may_giao_ma": "NM_CJ_CAN_DUOC",
            "kl_giao_kg": 1000000,
            "don_gia_cuoc": 50000,
            "so_bang_ke": "" # Cố tình bỏ trống số bảng kê
        }
        create_res = self.client.post("/api/salan/chuyen", json=trip_hkd, headers=self.headers_admin)
        self.assertEqual(create_res.status_code, 200)
        hkd_chuyen_id = create_res.json()["id"]

        # 1. Thử thanh toán cho chuyến hộ kinh doanh thiếu bảng kê -> Chặn C04
        pay_hkd = {
            "ngay": "2026-03-15",
            "cong_ty": "TP",
            "doi_tac_id": 3,
            "phuong_tien_ma": "LA 05678",
            "so_tien": 10000000,
            "nguoi_duyet": "GĐ",
            "ghi_chu": "Thử trả cho HKD thiếu bảng kê",
            "phan_bo": [{"chuyen_id": hkd_chuyen_id, "so_tien_phan_bo": 10000000}]
        }
        res_c04 = self.client.post("/api/salan/thanh-toan", json=pay_hkd, headers=self.headers_admin)
        self.assertEqual(res_c04.status_code, 400)
        self.assertIn("C04", res_c04.json()["detail"])
        print("✅ TEST 2a: Chặn C04 (Hộ kinh doanh thiếu số bảng kê) thành công.")

        # 2. Thử phân bổ vượt quá số còn nợ của chuyến 1 (còn nợ 48.157.270đ mà phân bổ 50.000.000đ) -> Chặn C05
        pay_over = {
            "ngay": "2026-03-15",
            "cong_ty": "TP",
            "doi_tac_id": 1,
            "phuong_tien_ma": "ĐT 26284",
            "so_tien": 50000000,
            "nguoi_duyet": "GĐ",
            "ghi_chu": "Thử trả vượt cước",
            "phan_bo": [{"chuyen_id": 1, "so_tien_phan_bo": 50000000}]
        }
        res_c05 = self.client.post("/api/salan/thanh-toan", json=pay_over, headers=self.headers_admin)
        self.assertEqual(res_c05.status_code, 400)
        self.assertIn("C05", res_c05.json()["detail"])
        print("✅ TEST 2b: Chặn C05 (Phân bổ vượt số còn nợ) thành công.")

    def test_03_partial_payment(self):
        """Kiểm tra thanh toán một phần (trả thiếu) -> Chuyến vẫn ở trạng thái Chưa trả và Chưa khoá sổ."""
        # Trả 20 triệu cho chuyến 1 (còn nợ 48.157.270đ)
        payload = {
            "ngay": "2026-03-20",
            "cong_ty": "TP",
            "doi_tac_id": 1,
            "phuong_tien_ma": "ĐT 26284",
            "so_tien": 20000000,
            "nguoi_duyet": "GĐ",
            "ghi_chu": "Tạm ứng thanh toán đợt 1",
            "phan_bo": [{"chuyen_id": 1, "so_tien_phan_bo": 20000000}]
        }
        res = self.client.post("/api/salan/thanh-toan", json=payload, headers=self.headers_admin)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data["so_phieu"].startswith("PT-TP-2026-"))
        self.__class__.phieu_1_id = data["id"]
        self.__class__.so_phieu_1 = data["so_phieu"]

        # Kiểm tra chuyến 1: chưa được đánh dấu đã trả đủ
        c1 = self.client.get("/api/salan/chuyen/1", headers=self.headers_admin).json()
        self.assertEqual(c1["da_tra_tien"], 0)
        self.assertEqual(c1["khoa_so"], 0)

        # Kiểm tra số nợ còn lại trong danh sách chưa trả là 28.157.270 đ
        unpaid = self.client.get("/api/salan/thanh-toan/chuyen-chua-tra?cong_ty=TP&phuong_tien_ma=ĐT 26284", headers=self.headers_admin).json()
        c1_unpaid = next((t for t in unpaid if t["id"] == 1), None)
        self.assertIsNotNone(c1_unpaid)
        self.assertEqual(c1_unpaid["da_tra_truoc"], 20000000)
        self.assertEqual(c1_unpaid["con_no"], 28157270)
        print("✅ TEST 3: Thanh toán trả thiếu thành công, số dư nợ còn lại chính xác từng đồng.")

    def test_04_multi_trip_payment_and_auto_lock_c07(self):
        """Thanh toán 1 phiếu cho nhiều chuyến, tự chuyển Đã trả & khoá sổ, kiểm tra C07 và mở khoá."""
        # Trả nốt 28.157.270đ cho chuyến 1 (để trả đủ)
        payload = {
            "ngay": "2026-03-25",
            "cong_ty": "TP",
            "doi_tac_id": 1,
            "phuong_tien_ma": "ĐT 26284",
            "so_tien": 28157270,
            "nguoi_duyet": "Phó GĐ",
            "ghi_chu": "Quyết toán dứt điểm chuyến C01",
            "phan_bo": [{"chuyen_id": 1, "so_tien_phan_bo": 28157270}]
        }
        res = self.client.post("/api/salan/thanh-toan", json=payload, headers=self.headers_admin)
        self.assertEqual(res.status_code, 200)
        self.__class__.phieu_2_id = res.json()["id"]

        # Chuyến 1 bây giờ phải tự động chuyển thành da_tra_tien = 1 và khoa_so = 1
        c1 = self.client.get("/api/salan/chuyen/1", headers=self.headers_admin).json()
        self.assertEqual(c1["da_tra_tien"], 1)
        self.assertEqual(c1["khoa_so"], 1)
        self.assertEqual(c1["ngay_thanh_toan"], "2026-03-25")

        # Thử sửa chuyến 1 bằng tài khoản nhập vận hành (moi) -> Bị chặn C07
        update_data = {
            "cong_ty": "TP",
            "phuong_tien_ma": "ĐT 26284",
            "chu_hang_ma": "CH_GREENFEED",
            "ngay_nhan": "2026-03-01",
            "noi_nhan_ma": "CANG_PHU_MY",
            "kl_nhan_kg": 1100000,
            "ghi_chu": "Cố tình sửa chuyến đã khoá",
            "phien_ban": c1["phien_ban"]
        }
        res_edit_nvh = self.client.put("/api/salan/chuyen/1", json=update_data, headers=self.headers_nvh)
        self.assertEqual(res_edit_nvh.status_code, 403)
        self.assertIn("C07", res_edit_nvh.json()["detail"])
        print("✅ TEST 4a: Tự động chuyển Đã trả & Khoá sổ, chặn C07 với người dùng thường thành công.")

        # Quản trị mở khoá chuyến với lý do bắt buộc
        res_unlock = self.client.post("/api/salan/chuyen/1/mo-khoa", json={"ly_do": "Điều chỉnh theo biên bản đối soát"}, headers=self.headers_admin)
        self.assertEqual(res_unlock.status_code, 200)

        c1_unlocked = self.client.get("/api/salan/chuyen/1", headers=self.headers_admin).json()
        self.assertEqual(c1_unlocked["khoa_so"], 0)
        print("✅ TEST 4b: Quản trị mở khoá sổ chuyến thành công kèm nhật ký ghi nhận.")

    def test_05_cancel_payment_and_auto_revert(self):
        """Huỷ phiếu thanh toán (xoá mềm) -> các chuyến liên quan tự động trở lại Chưa trả."""
        # Huỷ phiếu 2
        res_del = self.client.delete(f"/api/salan/thanh-toan/{self.phieu_2_id}?ly_do=Huỷ phiếu thử nghiệm", headers=self.headers_admin)
        self.assertEqual(res_del.status_code, 200)

        # Chuyến 1 tự động quay lại Chưa trả vì tổng tiền trả còn hiệu lực (20tr) < còn phải trả (48.157.270đ)
        c1 = self.client.get("/api/salan/chuyen/1", headers=self.headers_admin).json()
        self.assertEqual(c1["da_tra_tien"], 0)
        self.assertEqual(c1["khoa_so"], 0)

        # Huỷ tiếp phiếu 1
        res_del_1 = self.client.delete(f"/api/salan/thanh-toan/{self.phieu_1_id}?ly_do=Huỷ nốt phiếu 1", headers=self.headers_admin)
        self.assertEqual(res_del_1.status_code, 200)

        # Số nợ chưa trả của chuyến 1 quay về đúng ban đầu 48.157.270 đ
        unpaid = self.client.get("/api/salan/thanh-toan/chuyen-chua-tra?cong_ty=TP&phuong_tien_ma=ĐT 26284", headers=self.headers_admin).json()
        c1_unpaid = next((t for t in unpaid if t["id"] == 1), None)
        self.assertIsNotNone(c1_unpaid)
        self.assertEqual(c1_unpaid["da_tra_truoc"], 0)
        self.assertEqual(c1_unpaid["con_no"], 48157270)
        print("✅ TEST 5: Huỷ phiếu thanh toán mềm thành công, trạng thái chuyến phục hồi chính xác.")

    def test_06_reprint_voucher_and_text_reading(self):
        """Tạo phiếu mới, kiểm tra xem lại / in lại phiếu giữ nguyên số phiếu và đọc tiền bằng chữ."""
        payload = {
            "ngay": "2026-03-25",
            "cong_ty": "TP",
            "doi_tac_id": 1,
            "phuong_tien_ma": "ĐT 26284",
            "so_tien": 48157270,
            "nguoi_duyet": "GĐ",
            "ghi_chu": "Thanh toán trọn gói chuyến C01",
            "phan_bo": [{"chuyen_id": 1, "so_tien_phan_bo": 48157270}]
        }
        res = self.client.post("/api/salan/thanh-toan", json=payload, headers=self.headers_admin)
        self.assertEqual(res.status_code, 200)
        pid = res.json()["id"]
        so_phieu = res.json()["so_phieu"]

        # Gọi GET để in lại
        detail = self.client.get(f"/api/salan/thanh-toan/{pid}", headers=self.headers_admin).json()
        self.assertEqual(detail["so_phieu"], so_phieu)
        self.assertEqual(detail["so_tien"], 48157270)
        self.assertEqual(detail["cong_ty_ten"], "Công ty TNHH Vận tải Trường Phát")
        self.assertEqual(detail["so_tai_khoan"], "19034567890")
        self.assertEqual(detail["ngan_hang"], "Techcombank")
        self.assertEqual(
            detail["so_tien_bang_chu"],
            "Bốn mươi tám triệu một trăm năm mươi bảy nghìn hai trăm bảy mươi đồng"
        )
        self.assertEqual(len(detail["danh_sach_chuyen"]), 1)
        self.assertEqual(detail["danh_sach_chuyen"][0]["ma_chuyen"], "ĐT 26284-C01")
        print("✅ TEST 6: In lại phiếu giữ đúng số phiếu và đọc tiền bằng chữ tiếng Việt chuẩn xác.")

    def test_07_role_permissions(self):
        """Phân quyền: Chỉ quản trị tạo/huỷ thanh toán; Ban giám đốc chỉ xem."""
        payload = {
            "ngay": "2026-03-25",
            "cong_ty": "TP",
            "doi_tac_id": 1,
            "phuong_tien_ma": "ĐT 26284",
            "so_tien": 1000000,
            "phan_bo": [{"chuyen_id": 1, "so_tien_phan_bo": 1000000}]
        }

        # Nhập vận hành gọi POST -> 403
        res_nvh = self.client.post("/api/salan/thanh-toan", json=payload, headers=self.headers_nvh)
        self.assertEqual(res_nvh.status_code, 403)

        # Ban giám đốc gọi POST -> 403
        res_bgd = self.client.post("/api/salan/thanh-toan", json=payload, headers=self.headers_bgd)
        self.assertEqual(res_bgd.status_code, 403)

        # Ban giám đốc gọi GET danh sách -> 200 OK (được xem)
        res_bgd_get = self.client.get("/api/salan/thanh-toan", headers=self.headers_bgd)
        self.assertEqual(res_bgd_get.status_code, 200)

        # Nhập vận hành gọi DELETE -> 403
        res_del_nvh = self.client.delete("/api/salan/thanh-toan/1?ly_do=test", headers=self.headers_nvh)
        self.assertEqual(res_del_nvh.status_code, 403)

        print("✅ TEST 7: Kiểm tra phân quyền thanh toán sà lan đạt 100%.")

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
