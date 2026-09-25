-- Migration 001: Danh mục gốc, người dùng, phân quyền (RLS) và nhật ký sửa
-- Dự án: Quản lý Vận tải Sà lan Trường Phát (Bước 0 & Bước 1)
-- Ngày tạo: 2026-09-25

-- 1. BẬT TIỆN ÍCH EXTENSION CẦN THIẾT
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================================================
-- 2. BẢNG CÔNG TY (3 công ty cố định)
-- ============================================================================
CREATE TABLE IF NOT EXISTS public.cong_ty (
    ma VARCHAR(10) PRIMARY KEY,
    ten TEXT NOT NULL,
    mst TEXT,
    dia_chi TEXT,
    kich_hoat BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Khởi tạo 3 dòng công ty cố định
INSERT INTO public.cong_ty (ma, ten, mst)
VALUES 
    ('TP', 'Công ty TNHH Vận tải Trường Phát', ''),
    ('TPL', 'Công ty TNHH Trường Phát Logistics', ''),
    ('NK', 'Công ty Cổ phần Thương mại & Vận tải Nguyên Khang', '')
ON CONFLICT (ma) DO UPDATE 
SET ten = EXCLUDED.ten,
    mst = COALESCE(EXCLUDED.mst, public.cong_ty.mst);

-- ============================================================================
-- 3. BẢNG NGƯỜI DÙNG & PHÂN QUYỀN
-- ============================================================================
-- Vai trò chuẩn:
-- 'quan_tri'       : Alex (toàn quyền)
-- 'nhap_van_hanh'  : Mới, Hoa (nhập chuyến, phiếu cân, danh mục)
-- 'ke_toan'        : Liễu, Hoa (phía chủ hàng, hoá đơn, tiền về, thanh toán)
-- 'ban_giam_doc'   : GĐ, Phó GĐ (chỉ xem, thấy lãi gộp)

CREATE TABLE IF NOT EXISTS public.nguoi_dung (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    auth_user_id UUID UNIQUE, -- Nối sang auth.users của Supabase
    tai_khoan TEXT UNIQUE NOT NULL,
    ho_ten TEXT NOT NULL,
    vai_tro TEXT[] NOT NULL DEFAULT ARRAY['nhap_van_hanh']::TEXT[],
    cong_ty_duoc_lam TEXT[] NOT NULL DEFAULT ARRAY['TP', 'TPL', 'NK']::TEXT[],
    pin_cap_2 TEXT,
    kich_hoat BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Index tra cứu người dùng
CREATE INDEX IF NOT EXISTS idx_nguoi_dung_tai_khoan ON public.nguoi_dung(tai_khoan);
CREATE INDEX IF NOT EXISTS idx_nguoi_dung_auth_id ON public.nguoi_dung(auth_user_id);

-- ============================================================================
-- 4. BẢNG ĐỐI TÁC (Chủ sà lan / Thuyền trưởng / Hộ kinh doanh)
-- ============================================================================
CREATE TABLE IF NOT EXISTS public.doi_tac (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ma TEXT UNIQUE,
    ten TEXT NOT NULL,
    so_dien_thoai TEXT,
    so_tai_khoan TEXT,
    ngan_hang TEXT,
    mst TEXT,
    ghi_chu TEXT,
    kich_hoat BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_doi_tac_ten ON public.doi_tac(ten);

-- ============================================================================
-- 5. BẢNG PHƯƠNG TIỆN (Dùng chung cho sà lan, xe, rơ-mooc)
-- ============================================================================
CREATE TABLE IF NOT EXISTS public.phuong_tien (
    ma TEXT PRIMARY KEY, -- Số hiệu (VD: 'ĐT 26284', chuẩn hoá khoảng trắng)
    loai_phuong_tien TEXT NOT NULL CHECK (loai_phuong_tien IN ('sa_lan', 'xe', 'mooc')),
    phan_loai_sa_lan TEXT CHECK (
        phan_loai_sa_lan IS NULL OR 
        phan_loai_sa_lan IN ('thue', 'chuyen', 'ho_kinh_doanh')
    ), -- Chỉ 3 giá trị: Sà lan thuê / Vận chuyển chuyến / Hộ kinh doanh + vận chuyển
    so_huu TEXT NOT NULL DEFAULT 'doi_tac' CHECK (so_huu IN ('cong_ty', 'doi_tac')),
    doi_tac_id UUID REFERENCES public.doi_tac(id) ON DELETE SET NULL,
    han_dang_kiem DATE,
    han_bao_hiem DATE,
    so_hop_dong TEXT, -- Bắt buộc nếu là hộ kinh doanh
    so_chuyen_truoc_so INTEGER NOT NULL DEFAULT 0,
    kich_hoat BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_ho_kinh_doanh_hop_dong CHECK (
        phan_loai_sa_lan != 'ho_kinh_doanh' OR (so_hop_dong IS NOT NULL AND trim(so_hop_dong) != '')
    )
);

CREATE INDEX IF NOT EXISTS idx_phuong_tien_loai ON public.phuong_tien(loai_phuong_tien);
CREATE INDEX IF NOT EXISTS idx_phuong_tien_doi_tac ON public.phuong_tien(doi_tac_id);

-- Trigger chuẩn hoá khoảng trắng mã phương tiện (VD: 'ĐT26284' và 'ĐT  26284' -> 'ĐT 26284')
CREATE OR REPLACE FUNCTION public.fn_chuan_hoa_ma_phuong_tien()
RETURNS TRIGGER AS $$
BEGIN
    NEW.ma := regexp_replace(trim(NEW.ma), '\s+', ' ', 'g');
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_chuan_hoa_ma_phuong_tien ON public.phuong_tien;
CREATE TRIGGER trg_chuan_hoa_ma_phuong_tien
BEFORE INSERT OR UPDATE OF ma ON public.phuong_tien
FOR EACH ROW EXECUTE FUNCTION public.fn_chuan_hoa_ma_phuong_tien();

-- ============================================================================
-- 6. BẢNG CHỦ HÀNG
-- ============================================================================
CREATE TABLE IF NOT EXISTS public.chu_hang (
    ma TEXT PRIMARY KEY, -- Mã chủ hàng (VD: 'CH001')
    ten_chuan TEXT NOT NULL,
    ten_goi_khac TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[],
    mst TEXT,
    nhom_chu_hang TEXT,
    hh_cho_phep_pct NUMERIC(6,4) NOT NULL DEFAULT 0.0010, -- Ví dụ 0.10% = 0.0010
    ngay_cho_phep_nhan_giao INTEGER NOT NULL DEFAULT 2, -- Số ngày nhận -> giao
    don_gia_neo_thu NUMERIC(15,0) NOT NULL DEFAULT 0, -- đ/tấn/ngày
    so_ngay_neo_cho_phep_thu INTEGER NOT NULL DEFAULT 0, -- Số ngày neo cho phép phía thu
    kich_hoat BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_chu_hang_ten_chuan ON public.chu_hang(ten_chuan);

-- ============================================================================
-- 7. BẢNG ĐỊA ĐIỂM (Nơi nhận, nhà máy giao, nơi đổ dầu gộp chung)
-- ============================================================================
CREATE TABLE IF NOT EXISTS public.dia_diem (
    ma TEXT PRIMARY KEY,
    ten TEXT NOT NULL,
    vai_tro TEXT[] NOT NULL DEFAULT ARRAY['noi_nhan']::TEXT[], -- 'noi_nhan', 'nha_may_giao', 'noi_do_dau'
    tinh TEXT,
    kich_hoat BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_dia_diem_ten ON public.dia_diem(ten);

-- ============================================================================
-- 8. BẢNG LOẠI HÀNG
-- ============================================================================
CREATE TABLE IF NOT EXISTS public.loai_hang (
    ma TEXT PRIMARY KEY,
    ten TEXT NOT NULL,
    kich_hoat BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Khởi tạo các loại hàng nông sản / viên nén thông dụng
INSERT INTO public.loai_hang (ma, ten)
VALUES 
    ('BAP', 'Bắp'),
    ('BA', 'Bã nành / Bã hạt'),
    ('GO_NEN', 'Gỗ nén'),
    ('VIEN_NEN', 'Viên nén mùn cưa')
ON CONFLICT (ma) DO UPDATE SET ten = EXCLUDED.ten;

-- ============================================================================
-- 9. BẢNG THAM SỐ HỆ THỐNG
-- ============================================================================
CREATE TABLE IF NOT EXISTS public.tham_so (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    loai TEXT NOT NULL, -- 'hh_cho_phep_pct', 'don_gia_neo', 'don_gia_phun_trung', 'vat_pct'
    ma TEXT,
    gia_tri NUMERIC(15,4) NOT NULL,
    hieu_luc_tu_ngay DATE NOT NULL DEFAULT CURRENT_DATE,
    ghi_chu TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Các tham số mặc định hiện nay:
-- HH: 0.10% (0.0010) và 0.15% (0.0015)
-- Neo / Phun trùng: 3.000 / 5.000 đ/tấn
-- VAT: 0% / 8% / 10%
INSERT INTO public.tham_so (loai, ma, gia_tri, hieu_luc_tu_ngay, ghi_chu)
VALUES 
    ('hh_cho_phep_pct', 'MAC_DINH_010', 0.0010, '2026-01-01', 'Hao hụt chuẩn 0.10%'),
    ('hh_cho_phep_pct', 'MUC_015', 0.0015, '2026-01-01', 'Hao hụt mức 0.15%'),
    ('don_gia_neo', 'NEO_3000', 3000, '2026-01-01', 'Đơn giá neo 3.000 đ/tấn/ngày'),
    ('don_gia_neo', 'NEO_5000', 5000, '2026-01-01', 'Đơn giá neo 5.000 đ/tấn/ngày'),
    ('don_gia_phun_trung', 'PT_3000', 3000, '2026-01-01', 'Phun trùng 3.000 đ/tấn'),
    ('vat_pct', 'VAT_0', 0, '2026-01-01', 'Thuế suất 0%'),
    ('vat_pct', 'VAT_8', 0.08, '2026-01-01', 'Thuế suất 8%')
ON CONFLICT DO NOTHING;

-- ============================================================================
-- 10. BẢNG NHẬT KÝ SỬA (Audit Log - Bất khả xâm phạm)
-- ============================================================================
CREATE TABLE IF NOT EXISTS public.nhat_ky_sua (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    bang TEXT NOT NULL,
    ban_ghi_id TEXT NOT NULL,
    hanh_dong TEXT NOT NULL, -- 'INSERT', 'UPDATE', 'DELETE', 'MO_KHOA', 'BO_QUA_CANH_BAO'
    cot TEXT,
    gia_tri_cu TEXT,
    gia_tri_moi TEXT,
    nguoi_dung_id UUID,
    tai_khoan TEXT,
    ly_do TEXT,
    thoi_diem TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp()
);

CREATE INDEX IF NOT EXISTS idx_nhat_ky_bang_id ON public.nhat_ky_sua(bang, ban_ghi_id);
CREATE INDEX IF NOT EXISTS idx_nhat_ky_thoi_diem ON public.nhat_ky_sua(thoi_diem DESC);
CREATE INDEX IF NOT EXISTS idx_nhat_ky_tai_khoan ON public.nhat_ky_sua(tai_khoan);

-- Ngăn chặn tuyệt đối hành vi XÓA hoặc SỬA nhật ký kiểm toán (kể cả quản trị)
CREATE OR REPLACE FUNCTION public.fn_ngan_xoa_nhat_ky()
RETURNS TRIGGER AS $$
BEGIN
    RAISE EXCEPTION 'Nhật ký sửa là bất khả biến: Không ai được quyền sửa hoặc xoá!';
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_ngan_xoa_nhat_ky ON public.nhat_ky_sua;
CREATE TRIGGER trg_ngan_xoa_nhat_ky
BEFORE UPDATE OR DELETE ON public.nhat_ky_sua
FOR EACH ROW EXECUTE FUNCTION public.fn_ngan_xoa_nhat_ky();

-- ============================================================================
-- 11. HÀM HỖ TRỢ KIỂM TRA PHÂN QUYỀN
-- ============================================================================
CREATE OR REPLACE FUNCTION public.fn_current_user_profile()
RETURNS public.nguoi_dung AS $$
DECLARE
    v_profile public.nguoi_dung;
BEGIN
    SELECT * INTO v_profile
    FROM public.nguoi_dung
    WHERE auth_user_id = auth.uid()
      AND kich_hoat = TRUE
    LIMIT 1;
    RETURN v_profile;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER STABLE;

CREATE OR REPLACE FUNCTION public.fn_has_role(VARIADIC p_roles TEXT[])
RETURNS BOOLEAN AS $$
DECLARE
    v_user_roles TEXT[];
BEGIN
    SELECT vai_tro INTO v_user_roles
    FROM public.nguoi_dung
    WHERE auth_user_id = auth.uid()
      AND kich_hoat = TRUE;

    IF v_user_roles IS NULL THEN
        RETURN FALSE;
    END IF;

    -- 'quan_tri' luôn có mọi quyền
    IF 'quan_tri' = ANY(v_user_roles) THEN
        RETURN TRUE;
    END IF;

    -- Kiểm tra có trùng bất kỳ role nào trong danh sách được truyền vào
    RETURN v_user_roles && p_roles;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER STABLE;

CREATE OR REPLACE FUNCTION public.fn_can_access_company(p_cong_ty TEXT)
RETURNS BOOLEAN AS $$
DECLARE
    v_companies TEXT[];
    v_roles TEXT[];
BEGIN
    SELECT cong_ty_duoc_lam, vai_tro INTO v_companies, v_roles
    FROM public.nguoi_dung
    WHERE auth_user_id = auth.uid()
      AND kich_hoat = TRUE;

    IF v_companies IS NULL THEN
        RETURN FALSE;
    END IF;

    IF 'quan_tri' = ANY(v_roles) THEN
        RETURN TRUE;
    END IF;

    RETURN p_cong_ty = ANY(v_companies);
END;
$$ LANGUAGE plpgsql SECURITY DEFINER STABLE;

-- ============================================================================
-- 12. KÍCH HOẠT ROW LEVEL SECURITY (RLS) TRÊN CÁC BẢNG DANH MỤC
-- ============================================================================
ALTER TABLE public.cong_ty ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.nguoi_dung ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.doi_tac ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.phuong_tien ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.chu_hang ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.dia_diem ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.loai_hang ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.tham_so ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.nhat_ky_sua ENABLE ROW LEVEL SECURITY;

-- 12.1. Phân quyền bảng CÔNG TY
DROP POLICY IF EXISTS rls_cong_ty_select ON public.cong_ty;
CREATE POLICY rls_cong_ty_select ON public.cong_ty
FOR SELECT USING (auth.role() = 'authenticated');

DROP POLICY IF EXISTS rls_cong_ty_modify ON public.cong_ty;
CREATE POLICY rls_cong_ty_modify ON public.cong_ty
FOR ALL USING (public.fn_has_role('quan_tri'));

-- 12.2. Phân quyền bảng NGƯỜI DÙNG
DROP POLICY IF EXISTS rls_nguoi_dung_select ON public.nguoi_dung;
CREATE POLICY rls_nguoi_dung_select ON public.nguoi_dung
FOR SELECT USING (
    public.fn_has_role('quan_tri', 'ban_giam_doc') OR 
    auth_user_id = auth.uid()
);

DROP POLICY IF EXISTS rls_nguoi_dung_modify ON public.nguoi_dung;
CREATE POLICY rls_nguoi_dung_modify ON public.nguoi_dung
FOR ALL USING (public.fn_has_role('quan_tri'));

-- 12.3. Phân quyền các bảng DANH MỤC GỐC (doi_tac, phuong_tien, chu_hang, dia_diem, loai_hang, tham_so)
-- Quy tắc đặc tả:
-- - Người dùng xác thực được xem
-- - Người nhập (nhap_van_hanh, ke_toan) được thêm, KHÔNG ĐƯỢC XOÁ
-- - Chỉ Alex (quan_tri) gộp mục trùng hoặc sửa trạng thái ngừng dùng
DO $$
DECLARE
    tbl TEXT;
BEGIN
    FOR tbl IN SELECT unnest(ARRAY['doi_tac', 'phuong_tien', 'chu_hang', 'dia_diem', 'loai_hang', 'tham_so'])
    LOOP
        EXECUTE format('DROP POLICY IF EXISTS rls_%I_select ON public.%I', tbl, tbl);
        EXECUTE format('CREATE POLICY rls_%I_select ON public.%I FOR SELECT USING (auth.role() = ''authenticated'')', tbl, tbl);

        EXECUTE format('DROP POLICY IF EXISTS rls_%I_insert ON public.%I', tbl, tbl);
        EXECUTE format('CREATE POLICY rls_%I_insert ON public.%I FOR INSERT WITH CHECK (public.fn_has_role(''quan_tri'', ''nhap_van_hanh'', ''ke_toan''))', tbl, tbl);

        EXECUTE format('DROP POLICY IF EXISTS rls_%I_update ON public.%I', tbl, tbl);
        EXECUTE format('CREATE POLICY rls_%I_update ON public.%I FOR UPDATE USING (public.fn_has_role(''quan_tri''))', tbl, tbl);

        EXECUTE format('DROP POLICY IF EXISTS rls_%I_delete ON public.%I', tbl, tbl);
        EXECUTE format('CREATE POLICY rls_%I_delete ON public.%I FOR DELETE USING (public.fn_has_role(''quan_tri''))', tbl, tbl);
    END LOOP;
END $$;

-- 12.4. Phân quyền bảng NHẬT KÝ SỬA
-- Chỉ Alex (quan_tri) và Ban giám đốc được xem nhật ký sửa; không ai được xoá
DROP POLICY IF EXISTS rls_nhat_ky_sua_select ON public.nhat_ky_sua;
CREATE POLICY rls_nhat_ky_sua_select ON public.nhat_ky_sua
FOR SELECT USING (public.fn_has_role('quan_tri', 'ban_giam_doc'));

DROP POLICY IF EXISTS rls_nhat_ky_sua_insert ON public.nhat_ky_sua;
CREATE POLICY rls_nhat_ky_sua_insert ON public.nhat_ky_sua
FOR INSERT WITH CHECK (auth.role() = 'authenticated');
