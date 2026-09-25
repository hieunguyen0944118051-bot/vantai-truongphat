-- Migration: 20260925000008_thanh_toan_sa_lan.sql
-- Hoàn thiện lưu trữ thanh toán sà lan, phân bổ chuyến và khoá sổ chuyến

-- BƯỚC NÂNG CẤP (UPGRADE)
ALTER TABLE salan_thanh_toan ADD COLUMN IF NOT EXISTS da_huy INTEGER DEFAULT 0;
ALTER TABLE salan_thanh_toan ADD COLUMN IF NOT EXISTS huy_boi TEXT;
ALTER TABLE salan_thanh_toan ADD COLUMN IF NOT EXISTS huy_luc TIMESTAMPTZ;
ALTER TABLE salan_thanh_toan ADD COLUMN IF NOT EXISTS ly_do_huy TEXT;
ALTER TABLE salan_thanh_toan ADD COLUMN IF NOT EXISTS tao_boi TEXT;
ALTER TABLE salan_thanh_toan ADD COLUMN IF NOT EXISTS tao_luc TIMESTAMPTZ;

ALTER TABLE salan_chuyen ADD COLUMN IF NOT EXISTS mo_khoa_boi TEXT;
ALTER TABLE salan_chuyen ADD COLUMN IF NOT EXISTS mo_khoa_luc TIMESTAMPTZ;
ALTER TABLE salan_chuyen ADD COLUMN IF NOT EXISTS ly_do_mo_khoa TEXT;

-- BƯỚC QUAY LẠI (ROLLBACK)
-- ALTER TABLE salan_thanh_toan DROP COLUMN IF EXISTS da_huy;
-- ALTER TABLE salan_thanh_toan DROP COLUMN IF EXISTS huy_boi;
-- ALTER TABLE salan_thanh_toan DROP COLUMN IF EXISTS huy_luc;
-- ALTER TABLE salan_thanh_toan DROP COLUMN IF EXISTS ly_do_huy;
-- ALTER TABLE salan_thanh_toan DROP COLUMN IF EXISTS tao_boi;
-- ALTER TABLE salan_thanh_toan DROP COLUMN IF EXISTS tao_luc;
-- ALTER TABLE salan_chuyen DROP COLUMN IF EXISTS mo_khoa_boi;
-- ALTER TABLE salan_chuyen DROP COLUMN IF EXISTS mo_khoa_luc;
-- ALTER TABLE salan_chuyen DROP COLUMN IF EXISTS ly_do_mo_khoa;
