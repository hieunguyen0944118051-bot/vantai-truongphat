# Hướng Dẫn Vận Hành Hệ Thống Sao Lưu & Khôi Phục Dữ Liệu
**Dự án: Quản lý Vận tải Sà lan Trường Phát**  
*Phiên bản: 25/09/2026*

---

## 1. Nguyên Tắc An Toàn Dữ Liệu
1. **Quy tắc 3-2-1**:
   - Dữ liệu luôn có 3 bản: Bản đang chạy (Production/Supabase), Bản lưu cục bộ hằng đêm, Bản đồng bộ về NAS văn phòng công ty.
   - Định kỳ hằng tháng tải 1 bản về Google Drive lưu trữ ngoại tuyến.
2. **Kiểm tra SHA-256**: Mỗi file sao lưu luôn có file `.sha256` đi kèm để đảm bảo file không bị hỏng hóc hoặc can thiệp.
3. **Thử nghiệm khôi phục**: Định kỳ mỗi tuần chạy script khôi phục vào database tạm để kiểm tra khớp từng đồng tiền và số dòng.

---

## 2. Cách Chạy Sao Lưu Thủ Công & Tự Động

### A. Chạy sao lưu thủ công bất cứ lúc nào
Mở terminal tại thư mục dự án và chạy:
```bash
./backend/venv/bin/python backend/backup_database.py "truoc_khi_cap_nhat"
```
Hệ thống sẽ tạo ra:
- File cơ sở dữ liệu: `backups/daily/backup_YYYYMMDD_HHMMSS_truoc_khi_cap_nhat.db`
- File SQL script xuất: `backups/daily/backup_YYYYMMDD_HHMMSS_truoc_khi_cap_nhat.sql`
- File mã kiểm tra toàn vẹn: `backups/daily/backup_YYYYMMDD_HHMMSS_truoc_khi_cap_nhat.db.sha256`

### B. Thiết lập tự động chạy mỗi đêm (Cronjob trên Mac/Linux)
Mở crontab bằng lệnh:
```bash
crontab -e
```
Thêm dòng sau để tự động sao lưu vào lúc 23:30 mỗi đêm:
```cron
30 23 * * * cd /Users/alex/.gemini/antigravity/scratch/transport-management && ./backend/venv/bin/python backend/backup_database.py "auto_nightly" >> backups/backup_cron.log 2>&1
```

Chính sách lưu giữ:
- Tự động giữ **30 bản sao lưu ngày** gần nhất trong `backups/daily/`.
- Tự động giữ **12 bản sao lưu tháng** gần nhất trong `backups/monthly/`.

---

## 3. Cách Đồng Bộ Về Thiết Bị NAS Văn Phòng

Giả sử ổ NAS văn phòng được gắn (mount) tại `/Volumes/NAS_TRUONGPHAT/backup_transport/` hoặc qua địa chỉ IP mạng nội bộ qua `rsync`:

### Cách 1: Sao chép sang thư mục NAS đã kết nối
```bash
rsync -avz --progress backups/ /Volumes/NAS_TRUONGPHAT/backup_transport/
```

### Cách 2: Đồng bộ qua mạng nội bộ qua giao thức SSH/Rsync
```bash
rsync -avz -e ssh backups/ admin@192.168.1.200:/volume1/Backups/TransportManagement/
```
*(Chỉ sao chép thêm file mới, không bao giờ xoá file cũ trên NAS).*

---

## 4. Cách Khôi Phục Dữ Liệu Từng Bước (Disaster Recovery)

Khi cần khôi phục dữ liệu hoặc kiểm tra tính toàn vẹn:

### Bước 1: Kiểm thử khôi phục thử nghiệm vào Database tạm
Chạy lệnh:
```bash
./backend/venv/bin/python backend/restore_database.py
```
Hoặc chỉ định rõ file cần khôi phục:
```bash
./backend/venv/bin/python backend/restore_database.py "backups/daily/backup_20260925_203000_manual.db"
```
Hệ thống sẽ:
1. Xác minh mã SHA-256.
2. Nạp dữ liệu vào database tạm thời.
3. Đối chiếu số dòng từng bảng (`salan_chuyen`, `salan_do_dau`, `salan_ung_phi`...) và tổng từng cột tiền. Lệch 1 đồng lập tức báo lỗi.

### Bước 2: Khôi phục chính thức đè lên Database Production (Khi có sự cố thực sự)
1. Dừng ứng dụng đang chạy:
   ```bash
   pkill -f uvicorn
   ```
2. Lưu bản hiện tại trước khi đè:
   ```bash
   cp backend/transport.db backend/transport.db.corrupted_bak
   ```
3. Chép file sao lưu tốt nhất vào vị trí hoạt động:
   ```bash
   cp backups/daily/backup_20260925_xxxxxx.db backend/transport.db
   ```
4. Khởi động lại ứng dụng:
   ```bash
   ./CHAY_PHAN_MEM_SA_LAN.command
   ```
5. Đăng nhập kiểm tra lại màn hình Sổ chuyến sà lan.
