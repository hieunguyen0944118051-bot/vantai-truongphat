-- ====================================================================
-- MIGRATION 20260925000006: BẢNG TỆP ĐÍNH KÈM CHỨNG TỪ SÀ LAN
-- Áp dụng cho PostgreSQL / Supabase
-- ====================================================================

-- Bước nâng cấp:
CREATE TABLE IF NOT EXISTS salan_tep_dinh_kem (
    id SERIAL PRIMARY KEY,
    chuyen_id INTEGER NOT NULL REFERENCES salan_chuyen(id) ON DELETE CASCADE,
    loai_tep VARCHAR(50) NOT NULL, -- can_nhan, can_giao, phieu_dau, phieu_ung, hoa_don, khac
    ten_goc TEXT NOT NULL,
    duong_dan TEXT NOT NULL,
    kich_thuoc_bytes BIGINT NOT NULL DEFAULT 0,
    mime_type VARCHAR(100) NOT NULL DEFAULT 'image/jpeg',
    nguoi_tai VARCHAR(100) NOT NULL DEFAULT 'Alex',
    thoi_diem_tai TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    da_huy SMALLINT NOT NULL DEFAULT 0,
    ly_do_huy TEXT,
    huy_boi VARCHAR(100),
    huy_luc TIMESTAMP WITH TIME ZONE
);

CREATE INDEX IF NOT EXISTS idx_salan_tep_chuyen ON salan_tep_dinh_kem(chuyen_id);
CREATE INDEX IF NOT EXISTS idx_salan_tep_loai ON salan_tep_dinh_kem(loai_tep);

COMMENT ON TABLE salan_tep_dinh_kem IS 'Lưu trữ tệp đính kèm phiếu cân nhận/giao, hoá đơn, dầu, ứng';

-- Bước quay lại (Rollback):
-- DROP TABLE IF EXISTS salan_tep_dinh_kem;
