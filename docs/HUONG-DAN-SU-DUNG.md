# Hướng Dẫn Sử Dụng Module Sà Lan (Dành Cho Nhân Viên Vận Hành: Mới & Hoa)

Phiên bản: 25/09/2026 · Áp dụng cho: Màn hình Vận tải Sà lan Trường Phát

Tài liệu hướng dẫn tóm tắt 1 trang giúp nhân viên nhập liệu thao tác chính xác, nhanh chóng và không bị lỗi.

---

## 1. Đăng nhập & Vai trò làm việc

1. Truy cập địa chỉ: `http://localhost:8000/salan` (hoặc tên miền máy chủ Render).
2. Nhập tài khoản và mật khẩu của bạn (VD: tài khoản `moi` hoặc `hoa`).
3. Sau khi đăng nhập, hệ thống tự động nhận diện vai trò **Nhập vận hành** và các công ty bạn được phép làm việc (`TP`, `TPL`, `NK`).
4. **Lưu ý bảo mật**: Toàn bộ số liệu phía thu của khách hàng (giá bán, tiền cước thu, lãi gộp) đã được ẩn khỏi màn hình làm việc của bạn.

---

## 2. Nhập chuyến sà lan mới (Khối Chuyến, Nhận & Giao)

1. Bấm nút xanh **"+ Thêm Chuyến Sà Lan Mới"** ở góc trên bên phải.
2. **Quy tắc màu sắc trên form**:
   - **Ô màu xanh lam (`#3d85c6`)**: Ô bạn cần nhập liệu (Công ty, Sà lan, Chủ hàng, Loại hàng, Ngày, Nơi nhận/giao, Khối lượng).
   - **Ô màu cam (`#c25e00`)**: Ô hệ thống tự động tính toán (Cước sà lan, Hao hụt %, Bồi thường, Còn phải trả sà lan). Bạn không cần gõ vào các ô này.
3. **Các trường bắt buộc (Quy tắc C01 - Không được để trống)**:
   - Công ty (`TP` / `TPL` / `NK`)
   - Sà lan (Chọn từ danh sách, VD: `ĐT 26284`)
   - Chủ hàng (VD: `CJ Vina Agri`, `Greenfeed`)
   - Ngày nhận, Nơi nhận và Khối lượng nhận (kg).
4. **Các quy tắc chặn tự động của hệ thống**:
   - **Chặn C02**: Ngày giao không được trước ngày nhận.
   - **Chặn C03**: Không được nhập số âm cho khối lượng, đơn giá hoặc tiền dầu/ứng.
   - **Chặn C07**: Chuyến đã được Ban Giám đốc / Alex thanh toán và khoá sổ thì không được tự ý sửa đổi (muốn sửa phải báo Alex mở khoá kèm lý do).
5. **Chống mất dữ liệu khi đang gõ**:
   - Hệ thống tự động lưu nháp vào máy mỗi 10 giây.
   - Nếu bạn lỡ tay đóng form hoặc mất kết nối, khi mở lại form sẽ hiển thị thông báo khôi phục bản nháp chưa lưu.

---

## 3. Tải và quản lý ảnh chứng từ (Phiếu cân, Dầu, Ứng)

1. **Phiếu cân nhận & Phiếu cân giao**:
   - Trong khối Nhận hàng, bấm nút **"📷 Phiếu cân nhận"**.
   - Trong khối Giao hàng, bấm nút **"📷 Phiếu cân giao"**.
   - Có thể chọn trực tiếp từ máy ảnh điện thoại hoặc chọn file ảnh từ máy tính (hỗ trợ JPG, PNG, WEBP, PDF).
2. **Phiếu đổ dầu & Phiếu ứng**:
   - Ở mỗi dòng đổ dầu hoặc tạm ứng chi phí luồng lạch, bấm biểu tượng **📷** ở cột Thao tác để gắn phiếu thanh toán dầu hoặc giấy ký nhận ứng tiền.
3. **Xem lại & Xoá ảnh**:
   - Bấm vào ảnh thu nhỏ để mở cửa sổ xem ảnh cỡ lớn.
   - Khi cần xoá ảnh sai, hệ thống yêu cầu nhập lý do huỷ để lưu nhật ký kiểm toán.

---

## 4. Xử lý các cờ cảnh báo màu đỏ & vàng

Hệ thống có các cờ thông minh báo ngay trên danh sách chuyến:

| Cờ cảnh báo | Ý nghĩa & Cách xử lý |
| :--- | :--- |
| **⚠️ W01 (Đỏ)** | Chuyến đã có ngày giao nhưng **chưa tải ảnh phiếu cân**. Cần tải ngay ảnh phiếu cân nhận hoặc giao lên để mất cờ đỏ. |
| **⚠️ W02 (Cam)** | Dôi hàng (Khối lượng giao lớn hơn khối lượng nhận). Cần kiểm tra lại phiếu cân hai đầu. |
| **⚠️ W03 (Vàng)**| Hụt vượt mức cho phép nhưng chưa nhập giá bồi thường (đ/kg). Cần bổ sung giá bồi thường. |
| **⚠️ W04 (Vàng)**| Chuyến bị neo phát sinh ngày neo nhưng chưa chọn "Có tính neo". Cần tích chọn nếu tính tiền neo cho chủ sà lan. |
| **⚠️ W05 (Vàng)**| Chuyến đã giao nhưng đơn giá cước bằng 0. Cần cập nhật đơn giá cước theo hợp đồng. |
| **⚠️ W09 (Cam)** | **Ứng vượt**: Tiền dầu + tiền ứng lớn hơn tiền cước. Hệ thống hiển thị huy hiệu cam "Ứng vượt ... đ" để nhắc theo dõi nợ ngược. |
| **⚠️ W10 (Vàng)**| Chuyến đã giao nhưng chưa điền số bảng kê. |

---

## 5. Tìm kiếm & Tra cứu nhanh

- Ô tìm kiếm nhanh ở đầu trang cho phép bạn gõ số hiệu sà lan (VD: `26284`, `8888`), mã chuyến, hoặc tên nhà máy để lọc ra chuyến ngay lập tức mà không cần bấm Enter.
- Có thể dùng các bộ lọc Công ty, Tháng, Trạng thái để kiểm tra nhanh các chuyến còn nợ sà lan.
