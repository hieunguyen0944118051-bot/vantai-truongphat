# Bật ghi từ app vào Google Sheets (làm 1 lần, ~10 phút)

Dùng **dự án Apps Script mới, độc lập** — không dán vào project đang gắn với file Sheets, nên menu 🚛, email nhắc hạn 7–8h và việc tự lấy KM 6h **không bị ảnh hưởng**.

1. Đăng nhập Google bằng tài khoản **chủ file** "ĐỔ DẦU - BẢO DƯỠNG - ĐĂNG KIỂM - THAY VỎ - GIẤY ĐI ĐƯỜNG".
2. Mở <https://script.google.com> → **Dự án mới**. Đặt tên `TRUONGPHAT_APP_SYNC`.
3. Xóa nội dung mặc định, dán toàn bộ file `APP_SYNC.gs`. Bấm **Lưu**.
4. ⚙️ **Cài đặt dự án** → Múi giờ: **(GMT+07:00) Bangkok/Hà Nội**.
5. Chọn hàm **`APPSYNC_setup`** → **Chạy** → cấp quyền (Sheets + Drive).
   Mở **Nhật ký thực thi**, sao chép dòng `APP_SYNC_KEY (dán vào Render): …`.
6. **Triển khai → Tùy chọn triển khai mới → Ứng dụng web**:
   - Thực thi với tư cách: **Tôi**
   - Ai có quyền truy cập: **Bất kỳ ai** (an toàn vì mọi yêu cầu phải có khóa bí mật)
   - Bấm **Triển khai**, sao chép **URL ứng dụng web** (đuôi `/exec`).
7. Render → vantai-truongphat → **Environment**, thêm:
   - `APPS_SCRIPT_URL` = URL ở bước 6
   - `APPS_SCRIPT_KEY` = khóa ở bước 5
   - (tùy chọn) `XE_WRITE_ROLES` = `admin,manager` — vai trò được nhập/sửa; mặc định đã là vậy.
8. Lưu → Render tự khởi động lại. Vào app → **Xe & Chi phí**: dòng "Ghi vào Sheets: đang bật".

## App ghi những gì
| Thao tác | Kết quả trên Sheets |
|---|---|
| Nhập đổ dầu / bảo dưỡng / thay vỏ / thay bạt | Thêm 1 dòng ngay dưới dòng cuối của NHẬT KÝ, chỉ ghi cột nhập liệu; cột công thức, ô chọn ▼, định dạng giữ nguyên. Cột **MÃ APP** (R / M / L / J) chứa mã dòng. |
| Bấm 2 lần | Không ghi trùng (trùng MÃ APP). |
| Sửa | Chỉ sửa được dòng có MÃ APP (do app ghi). |
| Hủy | Ghi `ĐÃ HỦY (ngày giờ, người: lý do)` vào GHI CHÚ + gạch ngang dòng. **Không xóa.** |
| Đánh dấu đã TT | Đổi cột THANH TOÁN (+ NGÀY THANH TOÁN với dầu). Kiểm tra biển số khớp trước khi ghi. |
| Lần ghi đầu tiên | Tự tạo bản sao `BACKUP_<tên file>_<ngày>` cùng thư mục. |
| Mọi thao tác | Ghi vào tab **NHẬT KÝ APP** (tự tạo). |

**Lưu ý:** công thức tổng hợp sẵn có trên Sheets (TỔNG QUAN, tổng công nợ…) chưa tự loại dòng "ĐÃ HỦY". App đã loại; nếu muốn Sheets cũng loại, thêm điều kiện `"<>*ĐÃ HỦY*"` vào các SUMIFS/COUNTIFS.

Tắt ghi: xóa `APPS_SCRIPT_URL` trên Render (app quay về chỉ đọc).
