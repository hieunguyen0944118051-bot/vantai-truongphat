# Đặc tả phần mềm Trường Phát — Bước 0 + Bước 1 (Sà lan)

Phiên bản: 25/09/2026 · Chủ dự án: Alex Nguyễn
Bản gốc: Claude Doc cùng tên. Khi bản gốc thay đổi, xuất lại file này.

## 0. Quy tắc cho AI agent (đọc trước khi làm)

1. Làm đúng thứ tự thi công ở Mục 10. Mỗi lần chỉ làm **một** bước; xong thì dừng, báo cáo và chờ Alex duyệt.
2. Không sửa, không xoá các module đang chạy của app (GPS, phạt nguội, bảo dưỡng, lệnh điều xe…) trừ khi được yêu cầu rõ.
3. Chỉ làm trên dự án Supabase **THỬ**. Không đụng dự án THẬT.
4. Mọi thay đổi database viết thành file migration SQL trong `supabase/migrations/`, chạy lại được.
5. Công thức tiền chỉ nằm trong database (view hoặc function). Giao diện chỉ hiển thị, không tự tính.
6. Phân quyền bằng Row Level Security. Khoá `service_role` không bao giờ nằm trong code giao diện và không bao giờ bị commit lên GitHub.
7. Tên bảng, tên cột: tiếng Việt không dấu, `snake_case` (VD `chu_hang`, `kl_giao_kg`). Nhãn hiển thị cho người dùng: tiếng Việt có dấu.
8. Tiền: kiểu `numeric`, số nguyên đồng. Khối lượng: số nguyên kg. Không dùng kiểu số thực.
9. Mỗi công thức tiền phải có test; kết quả mong đợi lấy từ sổ sà lan thật.
10. Chỗ nào đặc tả chưa rõ: hỏi Alex, không tự đoán.

## 1. Mục tiêu & phạm vi

Bước 0 + 1 thay sổ sà lan và file công nợ chủ hàng sà lan bằng phần mềm có database riêng. Nghiệm thu khi chạy song song với Google Sheets 1 tháng và mọi khoản tiền khớp từng đồng.

**Trong phạm vi**

- **Bước 0 — Nền:** đăng nhập, phân quyền theo vai trò và theo công ty, danh mục gốc, bảng CHUYẾN dùng chung cho xe và sà lan, nhật ký sửa.
- **Bước 1 — Sà lan trọn luồng:** nhập chuyến, tính cước / neo / phun trùng / hao hụt / thưởng / bồi thường, tải phiếu cân, thanh toán sà lan, công nợ chủ hàng, hoá đơn, thu tiền, tổng quan, in phiếu thanh toán, báo cáo lãi gộp sà lan (chỉ Alex và ban giám đốc xem).

**Ngoài phạm vi (làm ở bước sau)**

- Bước 2: lệnh điều xe, chuyến xe, bảng kê xe, công nợ chủ hàng phía xe.
- Bước 3: sao kê ngân hàng, SInvoice, dầu, bảo dưỡng, lương, lãi lỗ theo xe.

## 2. Người dùng & phân quyền

| Vai trò | Người | Được nhập / sửa | Không được thấy |
| --- | --- | --- | --- |
| Quản trị (`quan_tri`) | Alex | Tất cả; riêng trạng thái trả tiền và ngày thanh toán chỉ Alex sửa | — |
| Nhập vận hành (`nhap_van_hanh`) | Mới, Hoa | Chuyến (nhận, giao, cước sà lan, neo, hỗ trợ, phun trùng, dầu, ứng, hao hụt, thưởng / bồi thường, số bảng kê), phiếu cân; thêm mục danh mục | Đơn giá thu chủ hàng, công nợ, lãi gộp |
| Kế toán (`ke_toan`) | Liễu, Hoa | Phía chủ hàng: đơn giá thu, xông trùng thu, chủ hàng hỗ trợ, giảm trừ, hoá đơn, tiền về; ra phiếu thanh toán sà lan | Lãi gộp; thu và trả không đặt cạnh nhau trên cùng màn hình |
| Ban giám đốc (`ban_giam_doc`) | GĐ, Phó GĐ | Không sửa gì | — |

## 3. Mô hình dữ liệu — Danh mục gốc
- `cong_ty`: mã (TP / TPL / NK), tên, MST
- `phuong_tien`: mã = số hiệu, loại (sa_lan / xe / mooc), phân loại (thue / chuyen / ho_kinh_doanh), sở hữu, đối tác...
- `doi_tac`: tên, SĐT, STK, MST...
- `chu_hang`: mã, tên chuẩn, tên khác, MST, nhóm, hao hụt %, ngày nhận->giao, đơn giá neo thu...
- `dia_diem`: mã, tên, vai trò, tỉnh...
- `loai_hang`: mã, tên...
- `tham_so`: loại, mã, giá trị...
- `nguoi_dung`: tài khoản, họ tên, vai trò, công ty được làm...

## 4. Mô hình dữ liệu — Chuyến sà lan
- Bảng CHUYẾN dùng chung cho sà lan và xe.
- Bảng con: đổ dầu (nhiều lần), ứng phí (nhiều lần), tệp đính kèm.

## 5. Mô hình dữ liệu — Công nợ, hoá đơn, thanh toán
- Phía thu: `cuoc_thu`, `hoa_don`, `hoa_don_chuyen`, `thu_tien`.
- Phía trả: `thanh_toan`, `thanh_toan_chuyen`.

## 6. Công thức tính tiền
- Khớp sổ ĐT 26284-C01: 1.098.070 kg ÷ 1.000 × 61.000 = 66.982.270 đ.
- Cước, VAT, Neo, Phun trùng, Dầu, Ứng, Hao hụt, Bồi thường, Thưởng, Còn lại phải trả.
- Lãi gộp = Thu trước VAT - Chi sà lan trước VAT (chỉ Alex & Ban Giám Đốc).

## 7. Quy tắc kiểm tra & cảnh báo
- Chặn: C01 - C07.
- Cảnh báo: W01 - W11.
