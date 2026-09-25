# Changelog — Dự án Vận tải Sà lan Trường Phát

Tất cả các thay đổi kiến trúc, database migrations và luồng thi công được ghi lại chi tiết tại đây.

---

## [2026-09-25] - Khởi động Bước 1: Danh mục, Người dùng, Phân quyền & Nhật ký sửa

### 1. Khảo sát & Kiến trúc
- Đã khảo sát codebase hiện tại: Frontend chạy **React 18 + Vite + Tailwind CSS**, Backend chạy **FastAPI + SQLite** cho đội xe tải và định vị GPS.
- Khớp quy tắc Mục 11: Giữ nguyên ứng dụng hiện tại, không đụng tới các module đang chạy (GPS, phạt nguội, bảo dưỡng, v.v.). Module sà lan kết nối trực tiếp với database Supabase THỬ qua Supabase Client và RLS.

### 2. Database Migration (`supabase/migrations/20260925000001_danh_muc_nguoi_dung_phan_quyen.sql`)
- **Bảng `cong_ty`**: Khởi tạo 3 dòng cố định gồm Trường Phát (`TP`), Trường Phát Logistics (`TPL`), Nguyên Khang (`NK`).
- **Bảng `nguoi_dung`**: Thiết lập 4 vai trò (`quan_tri`, `nhap_van_hanh`, `ke_toan`, `ban_giam_doc`) và mảng công ty được phân quyền truy cập (`cong_ty_duoc_lam`).
- **Bảng `doi_tac`**: Lưu thông tin chủ sà lan, thuyền trưởng, hộ kinh doanh nhận thanh toán.
- **Bảng `phuong_tien`**: Dùng chung cho sà lan, xe, rơ-mooc. Phân loại sà lan chuẩn 3 giá trị (`thue`, `chuyen`, `ho_kinh_doanh`). Ràng buộc bắt buộc số hợp đồng đối với hộ kinh doanh. Trigger tự động chuẩn hóa khoảng trắng của số hiệu sà lan.
- **Bảng `chu_hang`**: Quản lý mã, tên chuẩn, mảng `ten_goi_khac`, hao hụt cho phép %, số ngày cho phép nhận-giao, đơn giá neo thu và ngày neo cho phép phía thu.
- **Bảng `dia_diem`**: Gộp 3 danh mục nơi nhận / nhà máy giao / nơi đổ dầu với mảng vai trò.
- **Bảng `loai_hang`**: Quản lý mặt hàng nông sản và viên nén.
- **Bảng `tham_so`**: Cấu hình hao hụt (0.10%, 0.15%), đơn giá neo/phun trùng (3.000 / 5.000 đ/tấn), thuế suất VAT (0%, 8%).
- **Bảng `nhat_ky_sua`**: Nhật ký kiểm toán bất biến (Trigger chặn UPDATE và DELETE). Chỉ Quản trị (`quan_tri`) và Ban giám đốc (`ban_giam_doc`) được xem.
- **Row Level Security (RLS)**:
  - Tất cả người dùng xác thực được đọc danh mục.
  - Người nhập vận hành và kế toán được thêm danh mục, không được xóa danh mục.
  - Chỉ Alex (`quan_tri`) được gộp, sửa hoặc xóa danh mục.

---

## [2026-09-25] - Bước 2: Bảng Chuyến, Bảng Con & Bộ Tính Toán Tài Chính Hoàn Chỉnh

### 1. Database Migration (`supabase/migrations/20260925000002_chuyen_sa_lan_cong_thuc_tien.sql`)
- **Bảng `chuyen`**: Khởi tạo cấu trúc dùng chung cho cả sà lan và xe tải; đầy đủ các khối Nhận, Giao, Cước sà lan, Neo, Hỗ trợ, Phun trùng, Hao hụt, Thưởng/Bồi thường, Bảng kê.
- **Bảng con `do_dau` & `ung_phi`**: Phá bỏ giới hạn 2 lần của Sheets, hỗ trợ nhập đổ dầu và ứng phí nhiều lần linh hoạt.
- **Bảng `cuoc_thu`**: Quản lý cước thu theo tấn hoặc trọn lô, neo thu, bù trừ công nợ.
- **View `v_chuyen_tinh_toan`**: Toàn bộ công thức tiền nằm ở database view theo đúng Mục 6 đặc tả (làm tròn số nguyên đồng, kiểm tra dôi hàng, hụt vượt, thưởng/phạt).

### 2. Bộ Kiểm Chứng Tự Động (`backend/test_salan_formulas.py`)
- Kiểm thử đối chiếu dữ liệu sổ thật:
  - Test case 1: Chuyến mẫu `ĐT 26284-C01` (1.098.070 kg ÷ 1.000 × 61.000 đ/tấn = 66.982.270 đ) khớp 100% từng đồng.
  - Test case 2: Chuyến hụt vượt định mức, neo 2 ngày, đổ dầu 2 lần, ứng phí 2 lần khớp từng đồng khoản còn lại phải trả (36.452.400 đ).
  - Test case 3: Quy tắc dôi hàng (hao hụt âm) không được tính thưởng khống theo Mục 11.
- Tỷ lệ vượt qua: **100%**.

### 3. Phân Hệ Phần Mềm Hoàn Chỉnh (`http://localhost:8000/salan`)
- **Backend**: Router FastAPI (`backend/routers/salan.py`) kết nối trực tiếp SQLite cục bộ, tự động sinh mã chuyến định dạng `ĐT 26284-C01`, cập nhật nhật ký kiểm toán.
- **Giao diện Web Chuyên Nghiệp (`backend/static/salan.html`)**:
  - Tuân thủ quy ước màu sắc: **Ô xanh (#3d85c6)** là người nhập, **ô cam (#c25e00)** là hệ thống tự tính (readonly).
  - Tích hợp chuyển đổi phân quyền trực tiếp (Alex, Mới/Hoa, Liễu/Hoa, Ban Giám Đốc) để kiểm tra việc ẩn cột cước thu, công nợ và lãi gộp.
  - Hỗ trợ thêm/xóa dòng dầu và ứng phí động ngay trên form.
  - Chức năng lập phiếu thanh toán sà lan, tự động gợi ý phân bổ tiền và in phiếu thanh toán khổ A4 chuẩn kế toán.
  - Báo cáo Lãi gộp chi tiết từng chuyến dành riêng cho Quản trị và Ban Giám Đốc.
- **Khởi động 1-click**: Tạo file thực thi [`CHAY_PHAN_MEM_SA_LAN.command`](file:///Users/alex/.gemini/antigravity/scratch/transport-management/CHAY_PHAN_MEM_SA_LAN.command).
