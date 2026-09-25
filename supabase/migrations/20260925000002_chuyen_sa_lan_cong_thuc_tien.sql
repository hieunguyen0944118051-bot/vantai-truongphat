-- Migration 002: Bảng chuyến, các bảng con và View công thức tiền chuẩn
-- Dự án: Quản lý Vận tải Sà lan Trường Phát (Bước 0 + Bước 1)
-- Ngày tạo: 2026-09-25

-- ============================================================================
-- 1. BẢNG CHUYẾN (Dùng chung cho Sà lan và Xe)
-- ============================================================================
CREATE TABLE IF NOT EXISTS public.chuyen (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    cong_ty VARCHAR(10) NOT NULL REFERENCES public.cong_ty(ma) DEFAULT 'TP',
    loai_phuong_tien TEXT NOT NULL DEFAULT 'sa_lan' CHECK (loai_phuong_tien IN ('sa_lan', 'xe')),
    ma_chuyen TEXT UNIQUE NOT NULL, -- VD: 'ĐT 26284-C01'
    so_thu_tu INTEGER NOT NULL,
    phuong_tien_ma TEXT NOT NULL REFERENCES public.phuong_tien(ma),
    chu_hang_ma TEXT NOT NULL REFERENCES public.chu_hang(ma),
    loai_hang_ma TEXT REFERENCES public.loai_hang(ma),
    so_lo_tau TEXT,
    ghi_chu TEXT,
    nguoi_nhap TEXT NOT NULL DEFAULT 'Hệ thống',
    thoi_diem_nhap TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    trang_thai TEXT NOT NULL DEFAULT 'dang_chay' CHECK (trang_thai IN ('dang_chay', 'da_giao', 'da_tra_sa_lan', 'huy')),
    
    -- Khối Nhận
    ngay_nhan DATE NOT NULL,
    noi_nhan_ma TEXT NOT NULL REFERENCES public.dia_diem(ma),
    kl_nhan_kg NUMERIC(15,0) NOT NULL CHECK (kl_nhan_kg >= 0),
    
    -- Khối Giao
    ngay_giao DATE,
    nha_may_giao_ma TEXT REFERENCES public.dia_diem(ma),
    kl_giao_kg NUMERIC(15,0) NOT NULL DEFAULT 0 CHECK (kl_giao_kg >= 0),
    
    -- Khối Cước sà lan
    don_gia_cuoc NUMERIC(15,0) NOT NULL DEFAULT 0 CHECK (don_gia_cuoc >= 0),
    vat_pct NUMERIC(6,4) NOT NULL DEFAULT 0.0000 CHECK (vat_pct >= 0),
    
    -- Khối Neo
    co_tinh_neo BOOLEAN NOT NULL DEFAULT FALSE,
    don_gia_neo NUMERIC(15,0) NOT NULL DEFAULT 3000 CHECK (don_gia_neo >= 0),
    ngay_cho_phep INTEGER NOT NULL DEFAULT 2 CHECK (ngay_cho_phep >= 0),
    
    -- Khối Hỗ trợ & Phun trùng
    ho_tro NUMERIC(15,0) NOT NULL DEFAULT 0 CHECK (ho_tro >= 0),
    ghi_chu_ho_tro TEXT,
    co_phun_trung BOOLEAN NOT NULL DEFAULT FALSE,
    don_gia_phun_trung NUMERIC(15,0) NOT NULL DEFAULT 3000 CHECK (don_gia_phun_trung >= 0),
    
    -- Khối Hao hụt & Thưởng / Bồi thường
    hh_cho_phep_pct NUMERIC(6,4) NOT NULL DEFAULT 0.0010 CHECK (hh_cho_phep_pct >= 0),
    gia_boi_thuong NUMERIC(15,0) NOT NULL DEFAULT 0 CHECK (gia_boi_thuong >= 0),
    co_thuong BOOLEAN NOT NULL DEFAULT FALSE,
    don_gia_thuong NUMERIC(15,0) NOT NULL DEFAULT 0 CHECK (don_gia_thuong >= 0),
    
    -- Khối Bảng kê & Thanh toán
    so_bang_ke TEXT,
    so_hoa_don_dau_vao TEXT,
    da_tra_tien BOOLEAN NOT NULL DEFAULT FALSE,
    ngay_thanh_toan DATE,
    khoa_so BOOLEAN NOT NULL DEFAULT FALSE, -- Khóa khi đã thanh toán, chỉ Alex mở
    
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    -- Ràng buộc logic kiểm tra
    CONSTRAINT chk_ngay_giao_sau_nhan CHECK (ngay_giao IS NULL OR ngay_giao >= ngay_nhan)
);

CREATE INDEX IF NOT EXISTS idx_chuyen_cong_ty ON public.chuyen(cong_ty);
CREATE INDEX IF NOT EXISTS idx_chuyen_phuong_tien ON public.chuyen(phuong_tien_ma);
CREATE INDEX IF NOT EXISTS idx_chuyen_chu_hang ON public.chuyen(chu_hang_ma);
CREATE INDEX IF NOT EXISTS idx_chuyen_ngay_nhan ON public.chuyen(ngay_nhan);
CREATE INDEX IF NOT EXISTS idx_chuyen_trang_thai ON public.chuyen(trang_thai);

-- ============================================================================
-- 2. BẢNG ĐỔ DẦU (Bảng con - Hỗ trợ đổ nhiều lần/chuyến)
-- ============================================================================
CREATE TABLE IF NOT EXISTS public.do_dau (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    chuyen_id UUID NOT NULL REFERENCES public.chuyen(id) ON DELETE CASCADE,
    ngay DATE NOT NULL,
    noi_do_ma TEXT REFERENCES public.dia_diem(ma),
    so_lit NUMERIC(15,2) NOT NULL DEFAULT 0 CHECK (so_lit >= 0),
    gia_dau NUMERIC(15,0) NOT NULL DEFAULT 0 CHECK (gia_dau >= 0),
    tien_dau NUMERIC(15,0) GENERATED ALWAYS AS (ROUND(so_lit * gia_dau)) STORED,
    anh_phieu TEXT,
    ghi_chu TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_do_dau_chuyen_id ON public.do_dau(chuyen_id);

-- ============================================================================
-- 3. BẢNG ỨNG PHÍ (Bảng con - Hỗ trợ ứng nhiều lần/chuyến)
-- ============================================================================
CREATE TABLE IF NOT EXISTS public.ung_phi (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    chuyen_id UUID NOT NULL REFERENCES public.chuyen(id) ON DELETE CASCADE,
    ngay DATE NOT NULL,
    so_tien NUMERIC(15,0) NOT NULL DEFAULT 0 CHECK (so_tien >= 0),
    noi_dung TEXT,
    anh_phieu TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_ung_phi_chuyen_id ON public.ung_phi(chuyen_id);

-- ============================================================================
-- 4. BẢNG TỆP ĐÍNH KÈM (Phiếu cân nhận/giao, dầu, ứng)
-- ============================================================================
CREATE TABLE IF NOT EXISTS public.tep_dinh_kem (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    chuyen_id UUID NOT NULL REFERENCES public.chuyen(id) ON DELETE CASCADE,
    loai_tep TEXT NOT NULL CHECK (loai_tep IN ('phieu_can_nhan', 'phieu_can_giao', 'phieu_dau', 'phieu_ung', 'khac')),
    duong_dan TEXT NOT NULL,
    ten_tep TEXT NOT NULL,
    dung_luong INTEGER,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_tep_chuyen_id ON public.tep_dinh_kem(chuyen_id);

-- ============================================================================
-- 5. BẢNG PHÍA THU - CƯỚC CHỦ HÀNG (1 dòng / chuyến)
-- ============================================================================
CREATE TABLE IF NOT EXISTS public.cuoc_thu (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    chuyen_id UUID NOT NULL UNIQUE REFERENCES public.chuyen(id) ON DELETE CASCADE,
    hinh_thuc TEXT NOT NULL DEFAULT 'theo_tan' CHECK (hinh_thuc IN ('theo_tan', 'tron_lo')),
    don_gia_thu NUMERIC(15,0) NOT NULL DEFAULT 0 CHECK (don_gia_thu >= 0),
    tien_tron_lo NUMERIC(15,0) NOT NULL DEFAULT 0 CHECK (tien_tron_lo >= 0),
    vat_pct_thu NUMERIC(6,4) NOT NULL DEFAULT 0.0800 CHECK (vat_pct_thu >= 0),
    xong_trung_thu NUMERIC(15,0) NOT NULL DEFAULT 0 CHECK (xong_trung_thu >= 0),
    chu_hang_ho_tro NUMERIC(15,0) NOT NULL DEFAULT 0 CHECK (chu_hang_ho_tro >= 0),
    giam_tru NUMERIC(15,0) NOT NULL DEFAULT 0 CHECK (giam_tru >= 0),
    ly_do_giam_tru TEXT,
    boi_thuong_chu_hang NUMERIC(15,0) NOT NULL DEFAULT 0 CHECK (boi_thuong_chu_hang >= 0),
    so_ngay_neo_cho_phep_thu INTEGER NOT NULL DEFAULT 2 CHECK (so_ngay_neo_cho_phep_thu >= 0),
    don_gia_neo_thu NUMERIC(15,0) NOT NULL DEFAULT 4000 CHECK (don_gia_neo_thu >= 0),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ============================================================================
-- 6. VIEW TÍNH TOÁN CÔNG THỨC TIỀN CHUẨN (Mục 6 Đặc tả)
-- Khớp chính xác chuyến ĐT 26284-C01: 1.098.070 kg / 1.000 * 61.000 = 66.982.270 đ
-- ============================================================================
CREATE OR REPLACE VIEW public.v_chuyen_tinh_toan AS
WITH agg_dau AS (
    SELECT chuyen_id, COALESCE(SUM(tien_dau), 0) AS tong_tien_dau
    FROM public.do_dau
    GROUP BY chuyen_id
),
agg_ung AS (
    SELECT chuyen_id, COALESCE(SUM(so_tien), 0) AS tong_ung
    FROM public.ung_phi
    GROUP BY chuyen_id
)
SELECT 
    c.id,
    c.cong_ty,
    c.loai_phuong_tien,
    c.ma_chuyen,
    c.so_thu_tu,
    c.phuong_tien_ma,
    c.chu_hang_ma,
    c.loai_hang_ma,
    c.so_lo_tau,
    c.ghi_chu,
    c.nguoi_nhap,
    c.thoi_diem_nhap,
    c.trang_thai,
    c.ngay_nhan,
    c.noi_nhan_ma,
    c.kl_nhan_kg,
    c.ngay_giao,
    c.nha_may_giao_ma,
    c.kl_giao_kg,
    c.don_gia_cuoc,
    c.vat_pct,
    c.co_tinh_neo,
    c.don_gia_neo,
    c.ngay_cho_phep,
    c.ho_tro,
    c.ghi_chu_ho_tro,
    c.co_phun_trung,
    c.don_gia_phun_trung,
    c.hh_cho_phep_pct,
    c.gia_boi_thuong,
    c.co_thuong,
    c.don_gia_thuong,
    c.so_bang_ke,
    c.so_hoa_don_dau_vao,
    c.da_tra_tien,
    c.ngay_thanh_toan,
    c.khoa_so,
    
    -- T = Khối lượng giao (kg) / 1000.0 (tấn)
    ROUND(c.kl_giao_kg / 1000.0, 3) AS tan_giao,
    
    -- PHÍA TRẢ SÀ LAN
    -- 1. Cước = T * don_gia_cuoc
    ROUND((c.kl_giao_kg / 1000.0) * c.don_gia_cuoc) AS cuoc_sa_lan,
    
    -- 2. VAT sà lan = Cước * vat_pct
    ROUND(ROUND((c.kl_giao_kg / 1000.0) * c.don_gia_cuoc) * c.vat_pct) AS vat_tien_sa_lan,
    
    -- 3. Ngày thực tế = Ngày giao - Ngày nhận
    CASE 
        WHEN c.ngay_giao IS NOT NULL THEN (c.ngay_giao - c.ngay_nhan)
        ELSE 0 
    END AS ngay_thuc_te,
    
    -- 4. Ngày neo = max(0, Ngày thực tế - Ngày cho phép)
    GREATEST(0, (CASE WHEN c.ngay_giao IS NOT NULL THEN (c.ngay_giao - c.ngay_nhan) ELSE 0 END) - c.ngay_cho_phep) AS ngay_neo,
    
    -- 5. Tiền neo = nếu Có tính neo: T * don_gia_neo * ngay_neo
    CASE 
        WHEN c.co_tinh_neo THEN 
            ROUND((c.kl_giao_kg / 1000.0) * c.don_gia_neo * GREATEST(0, (CASE WHEN c.ngay_giao IS NOT NULL THEN (c.ngay_giao - c.ngay_nhan) ELSE 0 END) - c.ngay_cho_phep))
        ELSE 0 
    END AS tien_neo,
    
    -- 6. Tiền phun trùng = nếu Có phun trùng: T * don_gia_phun_trung
    CASE 
        WHEN c.co_phun_trung THEN 
            ROUND((c.kl_giao_kg / 1000.0) * c.don_gia_phun_trung)
        ELSE 0 
    END AS tien_phun_trung,
    
    -- 7. Tiền dầu & Tiền ứng
    COALESCE(ad.tong_tien_dau, 0) AS tien_dau,
    COALESCE(au.tong_ung, 0) AS tien_ung,
    
    -- 8. Hao hụt
    (c.kl_nhan_kg - c.kl_giao_kg) AS hao_hut_kg,
    CASE 
        WHEN c.kl_nhan_kg > 0 THEN ROUND((c.kl_nhan_kg - c.kl_giao_kg)::NUMERIC / c.kl_nhan_kg, 4)
        ELSE 0 
    END AS hao_hut_pct,
    ROUND(c.kl_nhan_kg * c.hh_cho_phep_pct) AS muc_cho_phep_kg,
    GREATEST(0, (c.kl_nhan_kg - c.kl_giao_kg) - ROUND(c.kl_nhan_kg * c.hh_cho_phep_pct)) AS hut_vuot_kg,
    ROUND(GREATEST(0, (c.kl_nhan_kg - c.kl_giao_kg) - ROUND(c.kl_nhan_kg * c.hh_cho_phep_pct)) * c.gia_boi_thuong) AS boi_thuong,
    
    -- 9. Thưởng
    CASE 
        WHEN c.co_thuong THEN 
            GREATEST(0, ROUND(c.kl_nhan_kg * c.hh_cho_phep_pct) - GREATEST(0, c.kl_nhan_kg - c.kl_giao_kg))
        ELSE 0 
    END AS kg_thuong,
    CASE 
        WHEN c.co_thuong THEN 
            ROUND(GREATEST(0, ROUND(c.kl_nhan_kg * c.hh_cho_phep_pct) - GREATEST(0, c.kl_nhan_kg - c.kl_giao_kg)) * c.don_gia_thuong)
        ELSE 0 
    END AS tien_thuong,
    
    -- 10. CÒN LẠI PHẢI TRẢ SÀ LAN
    -- Cước + VAT + Neo + Hỗ trợ + Phun trùng + Thưởng - Dầu - Ứng - Bồi thường
    (
        ROUND((c.kl_giao_kg / 1000.0) * c.don_gia_cuoc) +
        ROUND(ROUND((c.kl_giao_kg / 1000.0) * c.don_gia_cuoc) * c.vat_pct) +
        (CASE WHEN c.co_tinh_neo THEN ROUND((c.kl_giao_kg / 1000.0) * c.don_gia_neo * GREATEST(0, (CASE WHEN c.ngay_giao IS NOT NULL THEN (c.ngay_giao - c.ngay_nhan) ELSE 0 END) - c.ngay_cho_phep)) ELSE 0 END) +
        c.ho_tro +
        (CASE WHEN c.co_phun_trung THEN ROUND((c.kl_giao_kg / 1000.0) * c.don_gia_phun_trung) ELSE 0 END) +
        (CASE WHEN c.co_thuong THEN ROUND(GREATEST(0, ROUND(c.kl_nhan_kg * c.hh_cho_phep_pct) - GREATEST(0, c.kl_nhan_kg - c.kl_giao_kg)) * c.don_gia_thuong) ELSE 0 END) -
        COALESCE(ad.tong_tien_dau, 0) -
        COALESCE(au.tong_ung, 0) -
        ROUND(GREATEST(0, (c.kl_nhan_kg - c.kl_giao_kg) - ROUND(c.kl_nhan_kg * c.hh_cho_phep_pct)) * c.gia_boi_thuong)
    ) AS con_lai_phai_tra,
    
    -- PHÍA THU CHỦ HÀNG
    ct.hinh_thuc AS hinh_thuc_thu,
    ct.don_gia_thu,
    ct.tien_tron_lo,
    ct.vat_pct_thu,
    ct.xong_trung_thu,
    ct.chu_hang_ho_tro,
    ct.giam_tru,
    ct.ly_do_giam_tru,
    ct.boi_thuong_chu_hang,
    ct.so_ngay_neo_cho_phep_thu,
    ct.don_gia_neo_thu,
    
    -- Cước thu
    CASE 
        WHEN ct.hinh_thuc = 'tron_lo' THEN ct.tien_tron_lo
        ELSE ROUND((c.kl_giao_kg / 1000.0) * COALESCE(ct.don_gia_thu, 0))
    END AS cuoc_thu,
    
    -- VAT thu
    ROUND(
        (CASE WHEN ct.hinh_thuc = 'tron_lo' THEN ct.tien_tron_lo ELSE ROUND((c.kl_giao_kg / 1000.0) * COALESCE(ct.don_gia_thu, 0)) END) * COALESCE(ct.vat_pct_thu, 0)
    ) AS vat_thu,
    
    -- Neo thu
    GREATEST(0, (CASE WHEN c.ngay_giao IS NOT NULL THEN (c.ngay_giao - c.ngay_nhan) ELSE 0 END) - COALESCE(ct.so_ngay_neo_cho_phep_thu, 2)) AS ngay_neo_thu,
    ROUND((c.kl_giao_kg / 1000.0) * COALESCE(ct.don_gia_neo_thu, 0) * GREATEST(0, (CASE WHEN c.ngay_giao IS NOT NULL THEN (c.ngay_giao - c.ngay_nhan) ELSE 0 END) - COALESCE(ct.so_ngay_neo_cho_phep_thu, 2))) AS neo_thu,
    
    -- PHẢI THU CHỦ HÀNG
    (
        (CASE WHEN ct.hinh_thuc = 'tron_lo' THEN ct.tien_tron_lo ELSE ROUND((c.kl_giao_kg / 1000.0) * COALESCE(ct.don_gia_thu, 0)) END) +
        ROUND((CASE WHEN ct.hinh_thuc = 'tron_lo' THEN ct.tien_tron_lo ELSE ROUND((c.kl_giao_kg / 1000.0) * COALESCE(ct.don_gia_thu, 0)) END) * COALESCE(ct.vat_pct_thu, 0)) +
        ROUND((c.kl_giao_kg / 1000.0) * COALESCE(ct.don_gia_neo_thu, 0) * GREATEST(0, (CASE WHEN c.ngay_giao IS NOT NULL THEN (c.ngay_giao - c.ngay_nhan) ELSE 0 END) - COALESCE(ct.so_ngay_neo_cho_phep_thu, 2))) +
        COALESCE(ct.xong_trung_thu, 0) +
        COALESCE(ct.chu_hang_ho_tro, 0) -
        COALESCE(ct.giam_tru, 0) -
        COALESCE(ct.boi_thuong_chu_hang, 0)
    ) AS phai_thu,
    
    -- LÃI GỘP CHUYẾN (Tính trước VAT, chỉ Quản trị và Ban Giám Đốc)
    (
        -- Thu trước VAT
        (
            (CASE WHEN ct.hinh_thuc = 'tron_lo' THEN ct.tien_tron_lo ELSE ROUND((c.kl_giao_kg / 1000.0) * COALESCE(ct.don_gia_thu, 0)) END) +
            ROUND((c.kl_giao_kg / 1000.0) * COALESCE(ct.don_gia_neo_thu, 0) * GREATEST(0, (CASE WHEN c.ngay_giao IS NOT NULL THEN (c.ngay_giao - c.ngay_nhan) ELSE 0 END) - COALESCE(ct.so_ngay_neo_cho_phep_thu, 2))) +
            COALESCE(ct.xong_trung_thu, 0) +
            COALESCE(ct.chu_hang_ho_tro, 0) -
            COALESCE(ct.giam_tru, 0) -
            COALESCE(ct.boi_thuong_chu_hang, 0)
        ) -
        -- Chi sà lan trước VAT (Dầu và Ứng không tính vào lãi gộp vì là tiền cước trả trước)
        (
            ROUND((c.kl_giao_kg / 1000.0) * c.don_gia_cuoc) +
            (CASE WHEN c.co_tinh_neo THEN ROUND((c.kl_giao_kg / 1000.0) * c.don_gia_neo * GREATEST(0, (CASE WHEN c.ngay_giao IS NOT NULL THEN (c.ngay_giao - c.ngay_nhan) ELSE 0 END) - c.ngay_cho_phep)) ELSE 0 END) +
            c.ho_tro +
            (CASE WHEN c.co_phun_trung THEN ROUND((c.kl_giao_kg / 1000.0) * c.don_gia_phun_trung) ELSE 0 END) +
            (CASE WHEN c.co_thuong THEN ROUND(GREATEST(0, ROUND(c.kl_nhan_kg * c.hh_cho_phep_pct) - GREATEST(0, c.kl_nhan_kg - c.kl_giao_kg)) * c.don_gia_thuong) ELSE 0 END) -
            ROUND(GREATEST(0, (c.kl_nhan_kg - c.kl_giao_kg) - ROUND(c.kl_nhan_kg * c.hh_cho_phep_pct)) * c.gia_boi_thuong)
        )
    ) AS lai_gop

FROM public.chuyen c
LEFT JOIN agg_dau ad ON ad.chuyen_id = c.id
LEFT JOIN agg_ung au ON au.chuyen_id = c.id
LEFT JOIN public.cuoc_thu ct ON ct.chuyen_id = c.id;

-- ============================================================================
-- 7. KÍCH HOẠT ROW LEVEL SECURITY (RLS) TRÊN CÁC BẢNG CHUYẾN
-- ============================================================================
ALTER TABLE public.chuyen ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.do_dau ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.ung_phi ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.tep_dinh_kem ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.cuoc_thu ENABLE ROW LEVEL SECURITY;

-- 7.1. Phân quyền bảng CHUYẾN theo công ty được làm và vai trò
DROP POLICY IF EXISTS rls_chuyen_select ON public.chuyen;
CREATE POLICY rls_chuyen_select ON public.chuyen
FOR SELECT USING (
    public.fn_can_access_company(cong_ty)
);

DROP POLICY IF EXISTS rls_chuyen_insert ON public.chuyen;
CREATE POLICY rls_chuyen_insert ON public.chuyen
FOR INSERT WITH CHECK (
    public.fn_can_access_company(cong_ty) AND 
    public.fn_has_role('quan_tri', 'nhap_van_hanh')
);

DROP POLICY IF EXISTS rls_chuyen_update ON public.chuyen;
CREATE POLICY rls_chuyen_update ON public.chuyen
FOR UPDATE USING (
    public.fn_can_access_company(cong_ty) AND 
    (
        public.fn_has_role('quan_tri') OR 
        (khoa_so = FALSE AND public.fn_has_role('nhap_van_hanh'))
    )
);

-- 7.2. Phân quyền bảng CƯỚC THU (Chỉ Kế toán và Quản trị được xem/sửa)
DROP POLICY IF EXISTS rls_cuoc_thu_select ON public.cuoc_thu;
CREATE POLICY rls_cuoc_thu_select ON public.cuoc_thu
FOR SELECT USING (
    public.fn_has_role('quan_tri', 'ke_toan', 'ban_giam_doc')
);

DROP POLICY IF EXISTS rls_cuoc_thu_modify ON public.cuoc_thu;
CREATE POLICY rls_cuoc_thu_modify ON public.cuoc_thu
FOR ALL USING (
    public.fn_has_role('quan_tri', 'ke_toan')
);
