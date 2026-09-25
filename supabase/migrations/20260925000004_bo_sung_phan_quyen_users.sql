-- ====================================================================
-- MIGRATION 20260925000004: BỔ SUNG PHÂN QUYỀN SÀ LAN & CÔNG TY CHO USERS
-- Áp dụng cho PostgreSQL / Supabase
-- ====================================================================

ALTER TABLE users ADD COLUMN IF NOT EXISTS salan_role VARCHAR(50);
ALTER TABLE users ADD COLUMN IF NOT EXISTS companies TEXT;

COMMENT ON COLUMN users.salan_role IS 'Vai trò module Sà lan: quan_tri, ban_giam_doc, ke_toan, nhap_van_hanh';
COMMENT ON COLUMN users.companies IS 'Danh sách mã công ty được phép truy cập, phân cách bởi dấu phẩy, vd: TP,TPL';
