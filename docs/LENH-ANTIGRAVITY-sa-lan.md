# Bộ lệnh Antigravity — Nâng cấp module Sà lan

Ngày rà soát: 25/09/2026 · Bản rà soát: `http://localhost:8000/salan`
Dùng kèm: `docs/SPEC-buoc-0-1-sa-lan.md`. Chỗ nào file này khác SPEC thì **file này thắng**.

---

## A. Kết quả rà soát hiện trạng

Công thức tiền đang **đúng**: đã tính tay 3 chuyến mẫu, khớp từng đồng (ĐT 26284-C01 còn phải trả 48.157.270 đ; SG 8888-C01 còn phải trả 36.452.400 đ, lãi gộp 27.966.000 đ). Vấn đề nằm ở bảo mật, an toàn dữ liệu và cách tổ chức màn hình.

| # | Mức | Vấn đề | Bằng chứng |
| --- | --- | --- | --- |
| 1 | Nghiêm trọng | Cả 11 API của sà lan **không cần đăng nhập**, trong khi 37 API phần xe thì có | Gọi `GET /api/salan/chuyen` không kèm token vẫn trả đủ dữ liệu; `openapi.json` không khai bảo mật cho các API sà lan |
| 2 | Nghiêm trọng | API `POST /api/salan/seed-du-lieu-chuan` và nút "Nạp dữ liệu mẫu sổ" nằm ngay trên giao diện, không cần đăng nhập | Có thể ghi đè hoặc làm lẫn dữ liệu thật |
| 3 | Nghiêm trọng | Vai trò chọn bằng ô dropdown đầu trang; phần cần giấu chỉ bị ẩn bằng CSS (`role-finance-only`) | API trả đủ 76 trường cho mọi người, gồm đơn giá thu, phải thu, lãi gộp |
| 4 | Cao | Không có chỗ tải ảnh; ảnh hiện **không lưu ở đâu cả** | 0 ô chọn file; bảng chuyến không có trường phiếu cân; bảng đổ dầu có cột `anh_phieu` nhưng không dùng |
| 5 | Cao | Lưu chuyến bằng nhiều request rời (chuyến, từng lần dầu, từng lần ứng) và không kiểm tra kết quả | Lỗi giữa chừng → lưu nửa vời mà người dùng không biết |
| 6 | Cao | Xoá dầu, xoá ứng là xoá cứng; chưa có nhật ký sửa | `DELETE /api/salan/dau/{id}`, `DELETE /api/salan/ung/{id}` |
| 7 | Cao | Thanh toán sà lan và công nợ chưa có API lưu | Phiếu in không để lại lịch sử; trạng thái "Đã trả" không có nguồn gốc |
| 8 | Cao | Phía thu nằm chung form và chung bảng với phía trả | Form sửa chuyến có Đơn giá thu, Tổng phải thu, Lãi gộp; bảng Sổ chuyến có cột Phải thu và thẻ Lãi gộp |
| 9 | Trung bình | "Người nhập" là chữ chọn tay ("Hoa", "Mới"), không lấy từ tài khoản đăng nhập | Ai cũng ghi được tên người khác |
| 10 | Trung bình | Cảnh báo không chạy | Cả 3 chuyến có `canh_bao` rỗng dù không có phiếu cân |
| 11 | Trung bình | Form thiếu trường và thiếu ràng buộc | Thiếu đơn giá phun trùng, có thưởng / đơn giá thưởng, số bảng kê, số HĐ đầu vào; Công ty / Sà lan / Chủ hàng không bắt buộc; ô số nhập được số âm; HH cho phép gõ tự do |
| 12 | Trung bình | Hiển thị mã thay cho tên, ngày dạng quốc tế | `CH_GREENFEED`, `CANG_PHU_MY`, `NM_CJ_CAN_DUOC`; `2026-03-24` |
| 13 | Trung bình | Token lưu trong localStorage; tài liệu API mở công khai; Tailwind nạp qua CDN | Console báo Tailwind CDN không dùng cho production |
| 14 | Trung bình | Tỷ lệ và số tấn là số thực | `hh_cho_phep_pct = 0.001`, `tan_giao = 1098.07`; dễ lệch đồng khi số liệu lớn |
| 15 | Cần kiểm tra | Database là gì, nằm ở đâu | Nếu là SQLite trên ổ đĩa Render thì **mất dữ liệu mỗi lần deploy hoặc khởi động lại** |
| 16 | Cần Alex xác nhận | VAT thu chỉ tính trên cước, không tính trên neo thu và xông trùng thu; VAT trả sà lan cũng chỉ tính trên cước | SG 8888-C01: VAT thu 6.227.520 = 8% × 77.844.000 (chỉ cước) |

---

## B. Quyết định thiết kế

**Tách 2 phần hoàn toàn**

| | Phần A — Bảng kê sà lan | Phần B — Bảng kê chủ hàng |
| --- | --- | --- |
| Nội dung | Chuyến, nhận / giao, cước trả sà lan, neo, hỗ trợ, phun trùng, dầu, ứng, hao hụt, thưởng / bồi thường, phiếu cân, thanh toán sà lan, in phiếu, hồ sơ sà lan | Đơn giá thu, neo thu, xông trùng thu, hỗ trợ / giảm trừ / bồi thường chủ hàng, hoá đơn, tiền về, công nợ |
| Ai dùng | `quan_tri`, `nhap_van_hanh`, `ban_giam_doc` (chỉ xem) | Chỉ `chu_hang` (1 người), `quan_tri`, `ban_giam_doc` (chỉ xem) |
| Làm khi nào | **Bây giờ** | **Sau**. Tới lúc đó ẩn hoàn toàn: không có trên menu, API trả 403 |
| Lãi gộp | Không xuất hiện | Chỉ ở trang Tổng quan & lãi gộp của `quan_tri` và `ban_giam_doc` |

"Ẩn" nghĩa là **server không gửi dữ liệu**, không phải giấu bằng CSS.

**Ảnh lưu ở đâu**

- Kho ảnh riêng tư trên đám mây (Supabase Storage), cùng chỗ với database. Xem ảnh bằng link ký tạm, hết hạn sau 10 phút.
- **Không** lưu ảnh trên ổ đĩa server Render (bị xoá khi deploy). **Không** lưu ảnh dạng base64 trong database.
- Mỗi đêm sao lưu toàn bộ kho ảnh và database về NAS văn phòng.
- Đường dẫn: `phieu/<nam>/<thang>/<ma-chuyen-khong-dau>/<loai>/<thoi-gian>-<so>.jpg`, VD `phieu/2026/09/DT26284-C01/can-nhan/20260925-101500-1.jpg`.

**Nguyên tắc chống mất dữ liệu**

- Không có lệnh xoá cứng nào trong giao diện và API. Xoá = đánh dấu huỷ + lý do.
- Mọi thay đổi ghi nhật ký giá trị cũ → mới, người sửa, thời điểm. Không ai xoá được nhật ký.
- Lưu một chuyến = một request = một giao dịch database: hoặc lưu hết, hoặc không lưu gì.
- Hai người sửa cùng một chuyến: người lưu sau nhận thông báo "đã có người sửa", không ghi đè.
- Trước mỗi lần deploy hoặc migration: tự sao lưu database.
- Sao lưu 3 nơi: bản sao lưu tự động của nhà cung cấp, NAS văn phòng, Google Drive (hằng tháng). Mỗi tuần thử khôi phục một lần.

---

## C. Cách dùng

1. Bỏ file này và `SPEC-buoc-0-1-sa-lan.md` vào thư mục `docs/` của dự án.
2. Mở phiên làm việc mới trên Antigravity, dán **Lệnh khởi động** một lần.
3. Dán **từng lệnh một** theo thứ tự 0 → 7. Mỗi lệnh xong, agent phải báo cáo theo **Mẫu báo cáo**. Gửi báo cáo cho Claude rà soát, được duyệt mới dán lệnh tiếp theo.
4. Lệnh 8 (Phần B) chỉ dán khi Alex quyết định làm phần chủ hàng.

---

## D. Lệnh khởi động (dán 1 lần đầu phiên)

```
Bạn là kỹ sư phần mềm cấp cao, làm module Sà lan cho phần mềm vận tải Trường Phát (FastAPI, chạy tại localhost:8000, deploy trên Render).
Đọc kỹ docs/LENH-ANTIGRAVITY-sa-lan.md (mục A, B) và docs/SPEC-buoc-0-1-sa-lan.md (mục 0). Chỗ nào hai file khác nhau thì theo LENH-ANTIGRAVITY-sa-lan.md.

Quy tắc bắt buộc cho mọi lệnh sau:
1. Chỉ làm đúng phạm vi lệnh. Không sửa module phần xe, trừ khi lệnh yêu cầu.
2. Trước khi sửa code: tạo nhánh git mới tên theo lệnh (VD salan-lenh-1) và sao lưu database.
3. Không bao giờ xoá dữ liệu thật, không chạy lệnh DROP / TRUNCATE / DELETE hàng loạt trên dữ liệu thật.
4. Mọi thay đổi cấu trúc database viết thành migration có bước nâng cấp và bước quay lại.
5. Tiền dùng Decimal / numeric, số nguyên đồng. Không dùng float cho tiền, tấn, tỷ lệ.
6. Không để khoá bí mật, mật khẩu, chuỗi kết nối database trong code; chỉ dùng biến môi trường; .env nằm trong .gitignore.
7. Viết test tự động cho mọi thứ bạn làm; chạy toàn bộ test trước khi báo xong.
8. Chỗ nào chưa rõ: dừng lại và hỏi, không tự đoán.
9. Xong mỗi lệnh: dừng, báo cáo đúng Mẫu báo cáo ở cuối file docs/LENH-ANTIGRAVITY-sa-lan.md, chờ duyệt.

Trả lời "Đã hiểu" và tóm tắt 9 quy tắc trên trong 5 dòng. Chưa làm gì khác.
```

---

## E. Các lệnh theo thứ tự

### Lệnh 0 — Khảo sát và sao lưu (chưa sửa code)
### Lệnh 1 — Lưới an toàn dữ liệu (làm trước mọi thứ)
### Lệnh 2 — Bảo mật
### Lệnh 3 — Tách Phần A và Phần B
### Lệnh 4 — Tải ảnh phiếu cân, phiếu dầu, phiếu ứng
### Lệnh 5 — Chống lỗi khi nhập và lưu
### Lệnh 6 — Thanh toán sà lan lưu thật
### Lệnh 7 — Kiểm thử tổng và đưa lên Render
### Lệnh 8 — Phần B: Bảng kê chủ hàng (CHỈ LÀM KHI ALEX QUYẾT ĐỊNH)

---

## F. Mẫu báo cáo (agent phải trả lời đúng mẫu này sau mỗi lệnh)

```
BÁO CÁO LỆNH <số>
1. Đã làm: <gạch đầu dòng, mỗi dòng 1 việc>
2. File đã sửa / tạo: <danh sách đường dẫn>
3. Migration: <tên migration, có bước quay lại không>
4. Test: <số test đạt / tổng>; test mới thêm: <danh sách>
5. Sao lưu trước khi làm: <đường dẫn file sao lưu>
6. Chưa làm được / rủi ro còn lại: <...>
7. Câu hỏi cho Alex: <...>
```
