-- Migration 003: Lưới an toàn dữ liệu, chống xoá cứng và bảng nhật ký kiểm toán bất biến
-- Dự án: Quản lý Vận tải Sà lan Trường Phát (Lệnh 1)
-- Ngày tạo: 2026-09-25

-- ============================================================================
-- 1. BỔ SUNG CÁC CỘT CHỐNG XOÁ CỨNG (SOFT DELETE) & ĐÁNH DẤU DỮ LIỆU MẪU
-- ============================================================================

-- Bảng chuyến
ALTER TABLE public.chuyen 
    ADD COLUMN IF NOT EXISTS da_huy BOOLEAN NOT NULL DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS ly_do_huy TEXT,
    ADD COLUMN IF NOT EXISTS huy_boi TEXT,
    ADD COLUMN IF NOT EXISTS huy_luc TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS la_du_lieu_mau BOOLEAN NOT NULL DEFAULT FALSE;

-- Bảng đổ dầu
ALTER TABLE public.do_dau 
    ADD COLUMN IF NOT EXISTS da_huy BOOLEAN NOT NULL DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS ly_do_huy TEXT,
    ADD COLUMN IF NOT EXISTS huy_boi TEXT,
    ADD COLUMN IF NOT EXISTS huy_luc TIMESTAMPTZ;

-- Bảng ứng phí
ALTER TABLE public.ung_phi 
    ADD COLUMN IF NOT EXISTS da_huy BOOLEAN NOT NULL DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS ly_do_huy TEXT,
    ADD COLUMN IF NOT EXISTS huy_boi TEXT,
    ADD COLUMN IF NOT EXISTS huy_luc TIMESTAMPTZ;

-- ============================================================================
-- 2. BẢNG NHẬT KÝ KIỂM TOÁN CHUẨN (BẤT BIẾN)
-- ============================================================================
CREATE TABLE IF NOT EXISTS public.nhat_ky (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    bang TEXT NOT NULL,
    ban_ghi_id TEXT NOT NULL,
    hanh_dong TEXT NOT NULL CHECK (hanh_dong IN ('tao', 'sua', 'huy', 'khoi_phuc')),
    gia_tri_cu JSONB,
    gia_tri_moi JSONB,
    nguoi_dung_id TEXT,
    thoi_diem TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    ip TEXT
);

CREATE INDEX IF NOT EXISTS idx_nhat_ky_bang_ban_ghi ON public.nhat_ky(bang, ban_ghi_id);
CREATE INDEX IF NOT EXISTS idx_nhat_ky_thoi_diem_desc ON public.nhat_ky(thoi_diem DESC);

-- Trigger ngăn chặn tuyệt đối UPDATE và DELETE trên nhat_ky
CREATE OR REPLACE FUNCTION public.fn_ngan_sua_xoa_nhat_ky()
RETURNS TRIGGER AS $$
BEGIN
    RAISE EXCEPTION 'Bảng nhật ký kiểm toán là bất biến: Nghiêm cấm mọi hành vi sửa hoặc xoá!';
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_ngan_sua_xoa_nhat_ky ON public.nhat_ky;
CREATE TRIGGER trg_ngan_sua_xoa_nhat_ky
BEFORE UPDATE OR DELETE ON public.nhat_ky
FOR EACH ROW EXECUTE FUNCTION public.fn_ngan_sua_xoa_nhat_ky();

-- ============================================================================
-- 3. BƯỚC QUAY LẠI (ROLLBACK INSTRUCTIONS)
-- Trong trường hợp cần rollback migration này, chạy các lệnh sau:
-- DROP TRIGGER IF EXISTS trg_ngan_sua_xoa_nhat_ky ON public.nhat_ky;
-- DROP FUNCTION IF EXISTS public.fn_ngan_sua_xoa_nhat_ky();
-- DROP TABLE IF EXISTS public.nhat_ky;
-- ALTER TABLE public.chuyen DROP COLUMN IF EXISTS da_huy, DROP COLUMN IF EXISTS ly_do_huy, DROP COLUMN IF EXISTS huy_boi, DROP COLUMN IF EXISTS huy_luc, DROP COLUMN IF EXISTS la_du_lieu_mau;
-- ALTER TABLE public.do_dau DROP COLUMN IF EXISTS da_huy, DROP COLUMN IF EXISTS ly_do_huy, DROP COLUMN IF EXISTS huy_boi, DROP COLUMN IF EXISTS huy_luc;
-- ALTER TABLE public.ung_phi DROP COLUMN IF EXISTS da_huy, DROP COLUMN IF EXISTS ly_do_huy, DROP COLUMN IF EXISTS huy_boi, DROP COLUMN IF EXISTS huy_luc;
-- ============================================================================
