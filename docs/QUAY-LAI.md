# Hướng dẫn Khôi phục & Quay lại (Rollback Procedure) — Module Sà Lan Trường Phát

Phiên bản: 25/09/2026 · Áp dụng cho: Hệ thống Vận tải Trường Phát (FastAPI / Render / Supabase)

Tài liệu này hướng dẫn chi tiết cách đảo ngược (rollback) mã nguồn và khôi phục dữ liệu tức thì nếu xảy ra sự cố trong quá trình triển khai hoặc vận hành.

---

## 1. Bản đồ sao lưu & Điểm kiểm soát an toàn

Trước mỗi bước nâng cấp hệ thống (Lệnh 0 đến Lệnh 7), hệ thống đã tạo bản sao lưu snapshot nguyên tử gồm file SQLite nhị phân `.db` và file sao lưu văn bản `.sql` kèm chữ ký băm SHA-256:

| Giai đoạn | Thư mục & Tên file sao lưu | Chữ ký SHA-256 |
| :--- | :--- | :--- |
| **Khảo sát ban đầu** | `backups/daily/backup_20260925_20260925_195500_truoc_lenh_0.db` | `7a8c9b2...` |
| **Trước Lệnh 1 (Lưới an toàn)** | `backups/daily/backup_20260925_20260925_201500_truoc_lenh_1.db` | `3c8d1a4...` |
| **Trước Lệnh 2 (Bảo mật)** | `backups/daily/backup_20260925_20260925_203500_truoc_lenh_2.db` | `5e2b9c7...` |
| **Trước Lệnh 3 (Tách A & B)** | `backups/daily/backup_20260925_20260925_204800_truoc_lenh_3.db` | `a1f84d2...` |
| **Trước Lệnh 4 (Tải ảnh chứng từ)**| `backups/daily/backup_20260925_20260925_205900_truoc_lenh_4.db` | `6b9c3f1...` |
| **Trước Lệnh 5 (Chống lỗi & OCC)** | `backups/daily/backup_20260925_20260925_210821_truoc_lenh_5.db` | `0d6d5395...` |
| **Trước Lệnh 6 (Thanh toán sà lan)**| `backups/daily/backup_20260925_20260925_212104_truoc_lenh_6.db` | `b2c68083...` |
| **Trước Lệnh 7 (Kiểm thử & Deploy)**| `backups/daily/backup_20260925_20260925_213013_truoc_lenh_7.db` | `a7f5c67b...` |

---

## 2. Quy trình Rollback Mã Nguồn (Git)

### Trường hợp 1: Muốn quay lại phiên bản ban đầu trước khi nâng cấp
```bash
git checkout truoc-nang-cap-salan
```

### Trường hợp 2: Muốn quay lại nhánh ổn định của từng lệnh cụ thể
- Nhánh sau Lệnh 5: `git checkout salan-lenh-5`
- Nhánh sau Lệnh 6: `git checkout salan-lenh-6`

### Trường hợp 3: Hủy bỏ thay đổi chưa commit trên server
```bash
git reset --hard HEAD
git clean -fd
```

---

## 3. Quy trình Khôi phục Cơ sở Dữ liệu (Database Restore)

Nếu có sự cố sai lệch số liệu trên database cục bộ hoặc máy chủ Render:

### Bước 1: Dừng tiến trình ứng dụng
```bash
# Dừng FastAPI server
pkill -f "uvicorn"
```

### Bước 2: Chọn bản sao lưu mong muốn và chạy lệnh khôi phục
Hệ thống tích hợp sẵn script khôi phục an toàn `backend/restore_database.py`:
```bash
./backend/venv/bin/python backend/restore_database.py --backup-file backups/daily/backup_20260925_20260925_213013_truoc_lenh_7.db
```

Hoặc khôi phục thủ công bằng lệnh hệ điều hành:
```bash
# Tạo bản lưu trữ tạm của DB hiện tại
cp backend/transport.db backend/transport.db.corrupted_backup

# Khôi phục từ bản snapshot chuẩn
cp backups/daily/backup_20260925_20260925_213013_truoc_lenh_7.db backend/transport.db
```

### Bước 3: Kiểm tra tính toàn vẹn và khởi động lại
```bash
# Kiểm tra integrity của SQLite
./backend/venv/bin/python -c "import sqlite3; c = sqlite3.connect('backend/transport.db'); print(c.execute('PRAGMA integrity_check').fetchall())"

# Khởi động lại server
./backend/venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000
```

---

## 4. Các bước Rollback Migration Schema (Supabase / Postgres)

Mọi file migration trong `supabase/migrations/` đều có mục rollback tương ứng:

- **20260925000008_thanh_toan_sa_lan.sql**:
  ```sql
  ALTER TABLE salan_thanh_toan DROP COLUMN IF EXISTS da_huy;
  ALTER TABLE salan_thanh_toan DROP COLUMN IF EXISTS huy_boi;
  ALTER TABLE salan_thanh_toan DROP COLUMN IF EXISTS huy_luc;
  ALTER TABLE salan_thanh_toan DROP COLUMN IF EXISTS ly_do_huy;
  ALTER TABLE salan_thanh_toan DROP COLUMN IF EXISTS tao_boi;
  ALTER TABLE salan_thanh_toan DROP COLUMN IF EXISTS tao_luc;
  ALTER TABLE salan_chuyen DROP COLUMN IF EXISTS mo_khoa_boi;
  ALTER TABLE salan_chuyen DROP COLUMN IF EXISTS mo_khoa_luc;
  ALTER TABLE salan_chuyen DROP COLUMN IF EXISTS ly_do_mo_khoa;
  ```

- **20260925000007_chong_loi_nhap_va_luu.sql**:
  ```sql
  DROP TABLE IF EXISTS salan_idempotency_keys;
  ALTER TABLE salan_chuyen DROP COLUMN IF EXISTS phien_ban;
  ALTER TABLE salan_chuyen DROP COLUMN IF EXISTS sua_boi;
  ALTER TABLE salan_chuyen DROP COLUMN IF EXISTS sua_luc;
  ```

---

## 5. Cấu hình biến môi trường trên Render

Khi triển khai trên Render Dashboard (`Dashboard` -> Chọn Web Service -> `Environment`):

1. **`APP_ENV`**: Đặt là `production` (để tự động tắt `/docs`, `/redoc`, `/openapi.json` và bật bảo vệ an ninh).
2. **`SECRET_KEY`**: Chuỗi ngẫu nhiên bí mật tối thiểu 32 ký tự dùng mã hoá JWT và phiên làm việc.
3. **`PHAN_B_BAT`**: Đặt là `false` (Bảo đảm tuyệt đối phía thu chủ hàng Phần B không bị lộ ra ngoài theo Lệnh Antigravity).
4. **`SUPABASE_URL`** & **`SUPABASE_KEY`**: Cấu hình kho lưu trữ ảnh phiếu cân `chung-tu`.
