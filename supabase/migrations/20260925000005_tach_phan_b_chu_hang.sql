-- ====================================================================
-- MIGRATION 20260925000005: TÁCH RIÊNG PHẦN B (BẢNG KÊ CHỦ HÀNG & CƯỚC THU)
-- Áp dụng cho PostgreSQL / Supabase
-- ====================================================================

-- Bước nâng cấp:
CREATE TABLE IF NOT EXISTS salan_cuoc_thu (
    id SERIAL PRIMARY KEY,
    chuyen_id INTEGER NOT NULL UNIQUE,
    chu_hang_ma VARCHAR(50) NOT NULL,
    hinh_thuc_thu VARCHAR(30) DEFAULT 'theo_tan',
    don_gia_thu NUMERIC(15, 0) DEFAULT 0,
    tien_tron_lo NUMERIC(15, 0) DEFAULT 0,
    vat_pct_thu NUMERIC(5, 4) DEFAULT 0.0800,
    cuoc_thu NUMERIC(15, 0) DEFAULT 0,
    vat_thu NUMERIC(15, 0) DEFAULT 0,
    xong_trung_thu NUMERIC(15, 0) DEFAULT 0,
    neo_thu NUMERIC(15, 0) DEFAULT 0,
    chu_hang_ho_tro NUMERIC(15, 0) DEFAULT 0,
    giam_tru NUMERIC(15, 0) DEFAULT 0,
    ly_do_giam_tru TEXT,
    boi_thuong_chu_hang NUMERIC(15, 0) DEFAULT 0,
    tong_phai_thu NUMERIC(15, 0) DEFAULT 0,
    da_xuat_hoa_don BOOLEAN DEFAULT FALSE,
    so_hoa_don TEXT,
    ngay_hoa_don DATE,
    da_thu_tien BOOLEAN DEFAULT FALSE,
    so_tien_da_thu NUMERIC(15, 0) DEFAULT 0,
    ngay_thu_tien DATE,
    ngay_tao TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    ngay_cap_nhat TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    nguoi_cap_nhat VARCHAR(100),
    da_huy SMALLINT DEFAULT 0,
    ly_do_huy TEXT
);

CREATE INDEX IF NOT EXISTS idx_salan_cuoc_thu_chuyen_id ON salan_cuoc_thu(chuyen_id);
CREATE INDEX IF NOT EXISTS idx_salan_cuoc_thu_chu_hang ON salan_cuoc_thu(chu_hang_ma);

COMMENT ON TABLE salan_cuoc_thu IS 'Phần B: Dữ liệu tính cước thu chủ hàng và công nợ (Tách riêng khỏi Phần A)';

-- Bước quay lại (Rollback):
-- DROP TABLE IF EXISTS salan_cuoc_thu;
