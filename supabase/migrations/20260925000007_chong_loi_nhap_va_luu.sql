-- Migration: 20260925000007_chong_loi_nhap_va_luu.sql
-- Bổ sung trường kiểm soát phiên bản (Optimistic Concurrency Control) và bảng Idempotency Keys

-- BƯỚC NÂNG CẤP (UPGRADE)
ALTER TABLE salan_chuyen ADD COLUMN IF NOT EXISTS phien_ban INTEGER DEFAULT 1;
ALTER TABLE salan_chuyen ADD COLUMN IF NOT EXISTS sua_boi TEXT;
ALTER TABLE salan_chuyen ADD COLUMN IF NOT EXISTS sua_luc TIMESTAMPTZ;

CREATE TABLE IF NOT EXISTS salan_idempotency_keys (
    key TEXT PRIMARY KEY,
    endpoint TEXT NOT NULL,
    ban_ghi_id INTEGER,
    ket_qua TEXT NOT NULL,
    thoi_diem TIMESTAMPTZ DEFAULT NOW()
);

-- BƯỚC QUAY LẠI (ROLLBACK)
-- DROP TABLE IF EXISTS salan_idempotency_keys;
-- ALTER TABLE salan_chuyen DROP COLUMN IF EXISTS phien_ban;
-- ALTER TABLE salan_chuyen DROP COLUMN IF EXISTS sua_boi;
-- ALTER TABLE salan_chuyen DROP COLUMN IF EXISTS sua_luc;
