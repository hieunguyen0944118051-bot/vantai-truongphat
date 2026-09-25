import os
import sqlite3
from datetime import datetime, date
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional, List
from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel

router = APIRouter(prefix="/api/salan", tags=["Salan Management"])

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "transport.db")

def get_con():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    return con

def round_cur(val):
    if val is None:
        return 0
    return int(Decimal(str(val)).quantize(Decimal('1'), rounding=ROUND_HALF_UP))

def init_salan_tables():
    con = get_con()
    cur = con.cursor()
    
    # 1. Danh mục
    cur.execute("""
    CREATE TABLE IF NOT EXISTS salan_cong_ty (
        ma TEXT PRIMARY KEY,
        ten TEXT NOT NULL,
        mst TEXT
    )""")
    
    cur.execute("""
    CREATE TABLE IF NOT EXISTS salan_doi_tac (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ma TEXT UNIQUE,
        ten TEXT NOT NULL,
        so_dien_thoai TEXT,
        so_tai_khoan TEXT,
        ngan_hang TEXT,
        mst TEXT,
        ghi_chu TEXT
    )""")
    
    cur.execute("""
    CREATE TABLE IF NOT EXISTS salan_phuong_tien (
        ma TEXT PRIMARY KEY,
        loai_phuong_tien TEXT NOT NULL DEFAULT 'sa_lan',
        phan_loai_sa_lan TEXT,
        so_huu TEXT DEFAULT 'doi_tac',
        doi_tac_id INTEGER,
        han_dang_kiem TEXT,
        han_bao_hiem TEXT,
        so_hop_dong TEXT,
        so_chuyen_truoc_so INTEGER DEFAULT 0,
        FOREIGN KEY (doi_tac_id) REFERENCES salan_doi_tac(id)
    )""")
    
    cur.execute("""
    CREATE TABLE IF NOT EXISTS salan_chu_hang (
        ma TEXT PRIMARY KEY,
        ten_chuan TEXT NOT NULL,
        ten_goi_khac TEXT,
        mst TEXT,
        nhom_chu_hang TEXT,
        hh_cho_phep_pct REAL DEFAULT 0.0010,
        ngay_cho_phep_nhan_giao INTEGER DEFAULT 2,
        don_gia_neo_thu INTEGER DEFAULT 4000,
        so_ngay_neo_cho_phep_thu INTEGER DEFAULT 2
    )""")
    
    cur.execute("""
    CREATE TABLE IF NOT EXISTS salan_dia_diem (
        ma TEXT PRIMARY KEY,
        ten TEXT NOT NULL,
        vai_tro TEXT,
        tinh TEXT
    )""")
    
    cur.execute("""
    CREATE TABLE IF NOT EXISTS salan_loai_hang (
        ma TEXT PRIMARY KEY,
        ten TEXT NOT NULL
    )""")
    
    # 2. Bảng Chuyến
    cur.execute("""
    CREATE TABLE IF NOT EXISTS salan_chuyen (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        cong_ty TEXT NOT NULL DEFAULT 'TP',
        loai_phuong_tien TEXT NOT NULL DEFAULT 'sa_lan',
        ma_chuyen TEXT UNIQUE NOT NULL,
        so_thu_tu INTEGER NOT NULL,
        phuong_tien_ma TEXT NOT NULL,
        chu_hang_ma TEXT NOT NULL,
        loai_hang_ma TEXT,
        so_lo_tau TEXT,
        ghi_chu TEXT,
        nguoi_nhap TEXT NOT NULL DEFAULT 'Alex',
        thoi_diem_nhap TEXT,
        trang_thai TEXT NOT NULL DEFAULT 'dang_chay',
        
        ngay_nhan TEXT NOT NULL,
        noi_nhan_ma TEXT NOT NULL,
        kl_nhan_kg INTEGER NOT NULL,
        
        ngay_giao TEXT,
        nha_may_giao_ma TEXT,
        kl_giao_kg INTEGER DEFAULT 0,
        
        don_gia_cuoc INTEGER DEFAULT 0,
        vat_pct REAL DEFAULT 0,
        
        co_tinh_neo INTEGER DEFAULT 0,
        don_gia_neo INTEGER DEFAULT 3000,
        ngay_cho_phep INTEGER DEFAULT 2,
        
        ho_tro INTEGER DEFAULT 0,
        ghi_chu_ho_tro TEXT,
        co_phun_trung INTEGER DEFAULT 0,
        don_gia_phun_trung INTEGER DEFAULT 3000,
        
        hh_cho_phep_pct REAL DEFAULT 0.0010,
        gia_boi_thuong INTEGER DEFAULT 0,
        co_thuong INTEGER DEFAULT 0,
        don_gia_thuong INTEGER DEFAULT 0,
        
        so_bang_ke TEXT,
        so_hoa_don_dau_vao TEXT,
        da_tra_tien INTEGER DEFAULT 0,
        ngay_thanh_toan TEXT,
        khoa_so INTEGER DEFAULT 0,
        da_huy INTEGER DEFAULT 0,
        ly_do_huy TEXT,
        
        -- Phía thu chủ hàng
        hinh_thuc_thu TEXT DEFAULT 'theo_tan',
        don_gia_thu INTEGER DEFAULT 0,
        tien_tron_lo INTEGER DEFAULT 0,
        vat_pct_thu REAL DEFAULT 0.08,
        xong_trung_thu INTEGER DEFAULT 0,
        chu_hang_ho_tro INTEGER DEFAULT 0,
        giam_tru INTEGER DEFAULT 0,
        ly_do_giam_tru TEXT,
        boi_thuong_chu_hang INTEGER DEFAULT 0,
        so_ngay_neo_cho_phep_thu INTEGER DEFAULT 2,
        don_gia_neo_thu INTEGER DEFAULT 4000
    )""")
    
    # 3. Bảng Đổ dầu
    cur.execute("""
    CREATE TABLE IF NOT EXISTS salan_do_dau (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        chuyen_id INTEGER NOT NULL,
        ngay TEXT NOT NULL,
        noi_do_ma TEXT,
        so_lit REAL NOT NULL DEFAULT 0,
        gia_dau INTEGER NOT NULL DEFAULT 0,
        tien_dau INTEGER NOT NULL DEFAULT 0,
        anh_phieu TEXT,
        ghi_chu TEXT,
        FOREIGN KEY (chuyen_id) REFERENCES salan_chuyen(id) ON DELETE CASCADE
    )""")
    
    # 4. Bảng Ứng phí
    cur.execute("""
    CREATE TABLE IF NOT EXISTS salan_ung_phi (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        chuyen_id INTEGER NOT NULL,
        ngay TEXT NOT NULL,
        so_tien INTEGER NOT NULL DEFAULT 0,
        noi_dung TEXT,
        anh_phieu TEXT,
        FOREIGN KEY (chuyen_id) REFERENCES salan_chuyen(id) ON DELETE CASCADE
    )""")
    
    # 5. Bảng Thanh toán phân bổ
    cur.execute("""
    CREATE TABLE IF NOT EXISTS salan_thanh_toan (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        so_phieu TEXT UNIQUE NOT NULL,
        ngay TEXT NOT NULL,
        cong_ty TEXT NOT NULL,
        doi_tac_id INTEGER,
        phuong_tien_ma TEXT,
        so_tien INTEGER NOT NULL,
        nguoi_duyet TEXT,
        ghi_chu TEXT
    )""")
    
    cur.execute("""
    CREATE TABLE IF NOT EXISTS salan_thanh_toan_chuyen (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        thanh_toan_id INTEGER NOT NULL,
        chuyen_id INTEGER NOT NULL,
        so_tien_phan_bo INTEGER NOT NULL,
        FOREIGN KEY (thanh_toan_id) REFERENCES salan_thanh_toan(id) ON DELETE CASCADE,
        FOREIGN KEY (chuyen_id) REFERENCES salan_chuyen(id)
    )""")
    
    # 6. Bảng Nhật ký kiểm toán bất biến (nhat_ky)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS nhat_ky (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        bang TEXT NOT NULL,
        ban_ghi_id TEXT NOT NULL,
        hanh_dong TEXT NOT NULL,
        gia_tri_cu TEXT,
        gia_tri_moi TEXT,
        nguoi_dung_id TEXT,
        thoi_diem TEXT NOT NULL,
        ip TEXT
    )""")

    # Trigger ngăn chặn tuyệt đối xoá/sửa nhật ký
    cur.execute("""
    CREATE TRIGGER IF NOT EXISTS trg_ngan_xoa_nhat_ky
    BEFORE DELETE ON nhat_ky
    BEGIN
        SELECT RAISE(ABORT, 'Bảng nhật ký kiểm toán là bất biến: Nghiêm cấm mọi hành vi xoá!');
    END;
    """)
    cur.execute("""
    CREATE TRIGGER IF NOT EXISTS trg_ngan_sua_nhat_ky
    BEFORE UPDATE ON nhat_ky
    BEGIN
        SELECT RAISE(ABORT, 'Bảng nhật ký kiểm toán là bất biến: Nghiêm cấm mọi hành vi sửa!');
    END;
    """)

    # Kiểm tra và bổ sung cột chống xoá cứng (soft delete) cho các bảng nếu chưa có
    def add_col_if_missing(table, col, col_def):
        cols = [c[1] for c in cur.execute(f"PRAGMA table_info({table})").fetchall()]
        if col not in cols:
            cur.execute(f"ALTER TABLE {table} ADD COLUMN {col} {col_def}")

    add_col_if_missing("salan_chuyen", "da_huy", "INTEGER NOT NULL DEFAULT 0")
    add_col_if_missing("salan_chuyen", "ly_do_huy", "TEXT")
    add_col_if_missing("salan_chuyen", "huy_boi", "TEXT")
    add_col_if_missing("salan_chuyen", "huy_luc", "TEXT")
    add_col_if_missing("salan_chuyen", "la_du_lieu_mau", "INTEGER NOT NULL DEFAULT 0")

    add_col_if_missing("salan_do_dau", "da_huy", "INTEGER NOT NULL DEFAULT 0")
    add_col_if_missing("salan_do_dau", "ly_do_huy", "TEXT")
    add_col_if_missing("salan_do_dau", "huy_boi", "TEXT")
    add_col_if_missing("salan_do_dau", "huy_luc", "TEXT")

    add_col_if_missing("salan_ung_phi", "da_huy", "INTEGER NOT NULL DEFAULT 0")
    add_col_if_missing("salan_ung_phi", "ly_do_huy", "TEXT")
    add_col_if_missing("salan_ung_phi", "huy_boi", "TEXT")
    add_col_if_missing("salan_ung_phi", "huy_luc", "TEXT")

    # Đánh dấu dữ liệu mẫu hiện có
    cur.execute("UPDATE salan_chuyen SET la_du_lieu_mau = 1 WHERE id IN (1, 2, 3)")

    con.commit()
    con.close()

# Khởi tạo bảng ngay khi import
init_salan_tables()

def ghi_nhat_ky(cur, bang: str, ban_ghi_id: str, hanh_dong: str, gia_tri_cu=None, gia_tri_moi=None, nguoi_dung_id="Alex", ip=None):
    """Ghi nhật ký kiểm toán trong cùng transaction."""
    import json
    gt_cu_str = json.dumps(gia_tri_cu, ensure_ascii=False) if isinstance(gia_tri_cu, (dict, list)) else (str(gia_tri_cu) if gia_tri_cu else None)
    gt_moi_str = json.dumps(gia_tri_moi, ensure_ascii=False) if isinstance(gia_tri_moi, (dict, list)) else (str(gia_tri_moi) if gia_tri_moi else None)
    thoi_diem = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cur.execute("""
    INSERT INTO nhat_ky (bang, ban_ghi_id, hanh_dong, gia_tri_cu, gia_tri_moi, nguoi_dung_id, thoi_diem, ip)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (bang, str(ban_ghi_id), hanh_dong, gt_cu_str, gt_moi_str, nguoi_dung_id, thoi_diem, ip))

def tinh_toan_chuyen(row, danh_sach_dau, danh_sach_ung):
    """Tính toán mọi khoản tiền của chuyến theo đúng công thức Mục 6 Đặc tả."""
    kl_nhan = row['kl_nhan_kg'] or 0
    kl_giao = row['kl_giao_kg'] or 0
    don_gia_cuoc = row['don_gia_cuoc'] or 0
    vat_pct = float(row['vat_pct'] or 0)
    
    ngay_nhan = row['ngay_nhan']
    ngay_giao = row['ngay_giao']
    
    ngay_thuc_te = 0
    if ngay_nhan and ngay_giao:
        try:
            d_nhan = datetime.strptime(ngay_nhan[:10], "%Y-%m-%d")
            d_giao = datetime.strptime(ngay_giao[:10], "%Y-%m-%d")
            ngay_thuc_te = max(0, (d_giao - d_nhan).days)
        except Exception:
            pass
            
    T = Decimal(kl_giao) / Decimal(1000)
    
    # 1. Cước
    cuoc = round_cur(T * Decimal(don_gia_cuoc))
    vat_tien = round_cur(Decimal(cuoc) * Decimal(str(vat_pct)))
    
    # 2. Neo
    ngay_cho_phep = row['ngay_cho_phep'] or 2
    ngay_neo = max(0, ngay_thuc_te - ngay_cho_phep)
    co_tinh_neo = bool(row['co_tinh_neo'])
    don_gia_neo = row['don_gia_neo'] or 3000
    tien_neo = round_cur(T * Decimal(don_gia_neo) * Decimal(ngay_neo)) if co_tinh_neo else 0
    
    # 3. Phun trùng & Hỗ trợ
    ho_tro = row['ho_tro'] or 0
    co_phun_trung = bool(row['co_phun_trung'])
    don_gia_phun_trung = row['don_gia_phun_trung'] or 3000
    tien_phun_trung = round_cur(T * Decimal(don_gia_phun_trung)) if co_phun_trung else 0
    
    # 4. Dầu & Ứng
    tien_dau = sum(item['tien_dau'] for item in danh_sach_dau)
    tien_ung = sum(item['so_tien'] for item in danh_sach_ung)
    
    # 5. Hao hụt & Thưởng / Bồi thường (Chỉ tính khi ĐÃ GIAO HÀNG và có khối lượng giao)
    hh_cho_phep_pct = float(row['hh_cho_phep_pct'] or 0.0010)
    gia_boi_thuong = row['gia_boi_thuong'] or 0
    co_thuong = bool(row['co_thuong'])
    don_gia_thuong = row['don_gia_thuong'] or 0
    
    if ngay_giao and kl_giao > 0:
        hao_hut_kg = kl_nhan - kl_giao
        hao_hut_pct = (Decimal(hao_hut_kg) / Decimal(kl_nhan)) if kl_nhan > 0 else Decimal(0)
        muc_cho_phep_kg = round_cur(Decimal(kl_nhan) * Decimal(str(hh_cho_phep_pct)))
        hut_vuot_kg = max(0, hao_hut_kg - muc_cho_phep_kg)
        boi_thuong = round_cur(Decimal(hut_vuot_kg) * Decimal(gia_boi_thuong))
        
        if co_thuong:
            # Mục 11: Dôi hàng (hao hụt âm) không được thưởng thêm
            kg_thuong = max(0, muc_cho_phep_kg - max(0, hao_hut_kg))
            tien_thuong = round_cur(Decimal(kg_thuong) * Decimal(don_gia_thuong))
        else:
            kg_thuong = 0
            tien_thuong = 0
    else:
        # Đang chạy trên đường, chưa có số liệu giao -> Không tính hao hụt & bồi thường
        hao_hut_kg = 0
        hao_hut_pct = Decimal(0)
        muc_cho_phep_kg = 0
        hut_vuot_kg = 0
        boi_thuong = 0
        kg_thuong = 0
        tien_thuong = 0
        
    # 6. Còn lại phải trả sà lan
    con_lai_phai_tra = (
        cuoc + vat_tien + tien_neo + ho_tro + tien_phun_trung + tien_thuong
        - tien_dau - tien_ung - boi_thuong
    )
    
    # 7. Phía thu chủ hàng
    hinh_thuc_thu = row['hinh_thuc_thu'] or 'theo_tan'
    don_gia_thu = row['don_gia_thu'] or 0
    tien_tron_lo = row['tien_tron_lo'] or 0
    vat_pct_thu = float(row['vat_pct_thu'] or 0.08)
    so_ngay_neo_cho_phep_thu = row['so_ngay_neo_cho_phep_thu'] or 2
    don_gia_neo_thu = row['don_gia_neo_thu'] or 4000
    xong_trung_thu = row['xong_trung_thu'] or 0
    chu_hang_ho_tro = row['chu_hang_ho_tro'] or 0
    giam_tru = row['giam_tru'] or 0
    boi_thuong_chu_hang = row['boi_thuong_chu_hang'] or 0
    
    if hinh_thuc_thu == 'tron_lo':
        cuoc_thu = tien_tron_lo
    else:
        cuoc_thu = round_cur(T * Decimal(don_gia_thu))
    vat_thu = round_cur(Decimal(cuoc_thu) * Decimal(str(vat_pct_thu)))
    
    ngay_neo_thu = max(0, ngay_thuc_te - so_ngay_neo_cho_phep_thu)
    neo_thu = round_cur(T * Decimal(don_gia_neo_thu) * Decimal(ngay_neo_thu))
    
    phai_thu = (
        cuoc_thu + vat_thu + neo_thu + xong_trung_thu + chu_hang_ho_tro
        - giam_tru - boi_thuong_chu_hang
    )
    
    # 8. Lãi gộp (tính trước VAT)
    thu_truoc_vat = cuoc_thu + neo_thu + xong_trung_thu + chu_hang_ho_tro - giam_tru - boi_thuong_chu_hang
    chi_sa_lan_truoc_vat = cuoc + tien_neo + ho_tro + tien_phun_trung + tien_thuong - boi_thuong
    lai_gop = thu_truoc_vat - chi_sa_lan_truoc_vat
    
    # 9. Danh sách cảnh báo (C01-C07, W01-W11)
    canh_bao = []
    if ngay_giao and kl_giao == 0:
        canh_bao.append({"ma": "W01", "noi_dung": "Có ngày giao nhưng thiếu khối lượng giao"})
    if kl_giao > kl_nhan and kl_nhan > 0:
        canh_bao.append({"ma": "W02", "noi_dung": f"Dôi hàng: Giao nhiều hơn nhận {kl_giao - kl_nhan:,} kg"})
    if hut_vuot_kg > 0 and gia_boi_thuong == 0:
        canh_bao.append({"ma": "W03", "noi_dung": f"Hụt vượt {hut_vuot_kg:,} kg nhưng chưa có giá bồi thường"})
    if ngay_neo > 0 and not co_tinh_neo:
        canh_bao.append({"ma": "W04", "noi_dung": f"Neo {ngay_neo} ngày nhưng chưa chọn Có tính neo"})
    if (tien_dau + tien_ung) > cuoc and cuoc > 0:
        canh_bao.append({"ma": "W09", "noi_dung": "Dầu + Ứng lớn hơn cước: Sà lan đang nợ ngược"})
    if lai_gop < 0 and cuoc_thu > 0:
        canh_bao.append({"ma": "W06", "noi_dung": f"Lãi gộp chuyến âm: {lai_gop:,} đ"})

    return {
        "tan_giao": float(round(T, 3)),
        "cuoc": cuoc,
        "vat_tien": vat_tien,
        "ngay_thuc_te": ngay_thuc_te,
        "ngay_neo": ngay_neo,
        "tien_neo": tien_neo,
        "tien_phun_trung": tien_phun_trung,
        "tien_dau": tien_dau,
        "tien_ung": tien_ung,
        "hao_hut_kg": hao_hut_kg,
        "hao_hut_pct": float(round(hao_hut_pct * 100, 3)),
        "muc_cho_phep_kg": muc_cho_phep_kg,
        "hut_vuot_kg": hut_vuot_kg,
        "boi_thuong": boi_thuong,
        "kg_thuong": kg_thuong,
        "tien_thuong": tien_thuong,
        "con_lai_phai_tra": con_lai_phai_tra,
        "cuoc_thu": cuoc_thu,
        "vat_thu": vat_thu,
        "ngay_neo_thu": ngay_neo_thu,
        "neo_thu": neo_thu,
        "phai_thu": phai_thu,
        "lai_gop": lai_gop,
        "canh_bao": canh_bao
    }

# ============================================================================
# API ENDPOINTS
# ============================================================================

@router.get("/danh-muc")
def get_danh_muc():
    con = get_con()
    cur = con.cursor()
    
    cong_ty = [dict(r) for r in cur.execute("SELECT * FROM salan_cong_ty").fetchall()]
    doi_tac = [dict(r) for r in cur.execute("SELECT * FROM salan_doi_tac").fetchall()]
    phuong_tien = [dict(r) for r in cur.execute("SELECT * FROM salan_phuong_tien").fetchall()]
    chu_hang = [dict(r) for r in cur.execute("SELECT * FROM salan_chu_hang").fetchall()]
    dia_diem = [dict(r) for r in cur.execute("SELECT * FROM salan_dia_diem").fetchall()]
    loai_hang = [dict(r) for r in cur.execute("SELECT * FROM salan_loai_hang").fetchall()]
    
    con.close()
    return {
        "cong_ty": cong_ty,
        "doi_tac": doi_tac,
        "phuong_tien": phuong_tien,
        "chu_hang": chu_hang,
        "dia_diem": dia_diem,
        "loai_hang": loai_hang
    }

@router.get("/chuyen")
def get_danh_sach_chuyen(
    cong_ty: Optional[str] = None,
    sa_lan: Optional[str] = None,
    chu_hang: Optional[str] = None,
    thang: Optional[str] = None,
    trang_thai: Optional[str] = None
):
    con = get_con()
    cur = con.cursor()
    
    sql = "SELECT * FROM salan_chuyen WHERE da_huy = 0"
    params = []
    
    if cong_ty:
        sql += " AND cong_ty = ?"
        params.append(cong_ty)
    if sa_lan:
        sql += " AND phuong_tien_ma = ?"
        params.append(sa_lan)
    if chu_hang:
        sql += " AND chu_hang_ma = ?"
        params.append(chu_hang)
    if thang:
        sql += " AND strftime('%Y-%m', ngay_nhan) = ?"
        params.append(thang)
    if trang_thai:
        sql += " AND trang_thai = ?"
        params.append(trang_thai)
        
    sql += " ORDER BY ngay_nhan DESC, id DESC"
    rows = cur.execute(sql, params).fetchall()
    
    result = []
    for r in rows:
        row_dict = dict(r)
        c_id = row_dict['id']
        
        # Lấy danh sách dầu & ứng (chỉ lấy dòng chưa huỷ)
        dau_rows = [dict(d) for d in cur.execute("SELECT * FROM salan_do_dau WHERE chuyen_id = ? AND da_huy = 0", (c_id,)).fetchall()]
        ung_rows = [dict(u) for u in cur.execute("SELECT * FROM salan_ung_phi WHERE chuyen_id = ? AND da_huy = 0", (c_id,)).fetchall()]
        
        calc = tinh_toan_chuyen(row_dict, dau_rows, ung_rows)
        row_dict.update(calc)
        row_dict['do_dau'] = dau_rows
        row_dict['ung_phi'] = ung_rows
        result.append(row_dict)
        
    con.close()
    return result

@router.get("/chuyen/{chuyen_id}")
def get_chi_tiet_chuyen(chuyen_id: int):
    con = get_con()
    cur = con.cursor()
    row = cur.execute("SELECT * FROM salan_chuyen WHERE id = ? AND da_huy = 0", (chuyen_id,)).fetchone()
    if not row:
        con.close()
        raise HTTPException(status_code=404, detail="Không tìm thấy chuyến")
        
    row_dict = dict(row)
    dau_rows = [dict(d) for d in cur.execute("SELECT * FROM salan_do_dau WHERE chuyen_id = ? AND da_huy = 0", (chuyen_id,)).fetchall()]
    ung_rows = [dict(u) for u in cur.execute("SELECT * FROM salan_ung_phi WHERE chuyen_id = ? AND da_huy = 0", (chuyen_id,)).fetchall()]
    
    calc = tinh_toan_chuyen(row_dict, dau_rows, ung_rows)
    row_dict.update(calc)
    row_dict['do_dau'] = dau_rows
    row_dict['ung_phi'] = ung_rows
    con.close()
    return row_dict

class ChuyenCreateUpdate(BaseModel):
    cong_ty: str = "TP"
    phuong_tien_ma: str
    chu_hang_ma: str
    loai_hang_ma: Optional[str] = None
    so_lo_tau: Optional[str] = None
    ghi_chu: Optional[str] = None
    ngay_nhan: str
    noi_nhan_ma: str
    kl_nhan_kg: int
    ngay_giao: Optional[str] = None
    nha_may_giao_ma: Optional[str] = None
    kl_giao_kg: Optional[int] = 0
    don_gia_cuoc: Optional[int] = 0
    vat_pct: Optional[float] = 0.0
    co_tinh_neo: Optional[bool] = False
    don_gia_neo: Optional[int] = 3000
    ngay_cho_phep: Optional[int] = 2
    ho_tro: Optional[int] = 0
    ghi_chu_ho_tro: Optional[str] = None
    co_phun_trung: Optional[bool] = False
    don_gia_phun_trung: Optional[int] = 3000
    hh_cho_phep_pct: Optional[float] = 0.0010
    gia_boi_thuong: Optional[int] = 0
    co_thuong: Optional[bool] = False
    don_gia_thuong: Optional[int] = 0
    so_bang_ke: Optional[str] = None
    so_hoa_don_dau_vao: Optional[str] = None
    # Phía thu
    hinh_thuc_thu: Optional[str] = "theo_tan"
    don_gia_thu: Optional[int] = 0
    tien_tron_lo: Optional[int] = 0
    vat_pct_thu: Optional[float] = 0.08
    xong_trung_thu: Optional[int] = 0
    chu_hang_ho_tro: Optional[int] = 0
    giam_tru: Optional[int] = 0
    ly_do_giam_tru: Optional[str] = None
    boi_thuong_chu_hang: Optional[int] = 0
    so_ngay_neo_cho_phep_thu: Optional[int] = 2
    don_gia_neo_thu: Optional[int] = 4000
    nguoi_nhap: Optional[str] = "Alex"

@router.post("/chuyen")
def tao_chuyen_moi(data: ChuyenCreateUpdate):
    # Kiểm tra C01
    if not data.cong_ty or not data.phuong_tien_ma or not data.chu_hang_ma or not data.ngay_nhan or not data.noi_nhan_ma or data.kl_nhan_kg <= 0:
        raise HTTPException(status_code=400, detail="[C01] Thiếu thông tin bắt buộc: công ty, sà lan, chủ hàng, ngày nhận, nơi nhận hoặc khối lượng nhận!")
        
    # Kiểm tra C02
    if data.ngay_giao and data.ngay_giao < data.ngay_nhan:
        raise HTTPException(status_code=400, detail="[C02] Ngày giao không được trước ngày nhận!")
        
    # Kiểm tra C03
    if data.kl_nhan_kg < 0 or (data.kl_giao_kg and data.kl_giao_kg < 0) or data.don_gia_cuoc < 0:
        raise HTTPException(status_code=400, detail="[C03] Khối lượng hoặc đơn giá không được mang giá trị âm!")
        
    con = get_con()
    cur = con.cursor()
    
    # Tự sinh mã chuyến: ví dụ ĐT 26284-C01, ĐT 26284-C02...
    # Lấy số chuyến trước sổ của sà lan + số chuyến hiện có trong database
    pt = cur.execute("SELECT so_chuyen_truoc_so FROM salan_phuong_tien WHERE ma = ?", (data.phuong_tien_ma,)).fetchone()
    so_truoc = pt['so_chuyen_truoc_so'] if pt and pt['so_chuyen_truoc_so'] else 0
    
    current_count = cur.execute("SELECT COUNT(*) as cnt FROM salan_chuyen WHERE phuong_tien_ma = ?", (data.phuong_tien_ma,)).fetchone()['cnt']
    stt = so_truoc + current_count + 1
    
    # Định dạng: ĐT 26284-C01 (nếu quá 99 thì C100)
    suffix = f"C{stt:02d}" if stt < 100 else f"C{stt}"
    ma_chuyen = f"{data.phuong_tien_ma}-{suffix}"
    
    # Suy ra trạng thái tự động
    trang_thai = "da_giao" if data.ngay_giao else "dang_chay"
    thoi_diem = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    cur.execute("""
    INSERT INTO salan_chuyen (
        cong_ty, loai_phuong_tien, ma_chuyen, so_thu_tu, phuong_tien_ma, chu_hang_ma,
        loai_hang_ma, so_lo_tau, ghi_chu, nguoi_nhap, thoi_diem_nhap, trang_thai,
        ngay_nhan, noi_nhan_ma, kl_nhan_kg,
        ngay_giao, nha_may_giao_ma, kl_giao_kg,
        don_gia_cuoc, vat_pct,
        co_tinh_neo, don_gia_neo, ngay_cho_phep,
        ho_tro, ghi_chu_ho_tro, co_phun_trung, don_gia_phun_trung,
        hh_cho_phep_pct, gia_boi_thuong, co_thuong, don_gia_thuong,
        so_bang_ke, so_hoa_don_dau_vao,
        hinh_thuc_thu, don_gia_thu, tien_tron_lo, vat_pct_thu,
        xong_trung_thu, chu_hang_ho_tro, giam_tru, ly_do_giam_tru,
        boi_thuong_chu_hang, so_ngay_neo_cho_phep_thu, don_gia_neo_thu
    ) VALUES (
        ?, 'sa_lan', ?, ?, ?, ?,
        ?, ?, ?, ?, ?, ?,
        ?, ?, ?,
        ?, ?, ?,
        ?, ?,
        ?, ?, ?,
        ?, ?, ?, ?,
        ?, ?, ?, ?,
        ?, ?,
        ?, ?, ?, ?,
        ?, ?, ?, ?,
        ?, ?, ?
    )""", (
        data.cong_ty, ma_chuyen, stt, data.phuong_tien_ma, data.chu_hang_ma,
        data.loai_hang_ma, data.so_lo_tau, data.ghi_chu, data.nguoi_nhap, thoi_diem, trang_thai,
        data.ngay_nhan, data.noi_nhan_ma, data.kl_nhan_kg,
        data.ngay_giao, data.nha_may_giao_ma, data.kl_giao_kg,
        data.don_gia_cuoc, data.vat_pct,
        1 if data.co_tinh_neo else 0, data.don_gia_neo, data.ngay_cho_phep,
        data.ho_tro, data.ghi_chu_ho_tro, 1 if data.co_phun_trung else 0, data.don_gia_phun_trung,
        data.hh_cho_phep_pct, data.gia_boi_thuong, 1 if data.co_thuong else 0, data.don_gia_thuong,
        data.so_bang_ke, data.so_hoa_don_dau_vao,
        data.hinh_thuc_thu, data.don_gia_thu, data.tien_tron_lo, data.vat_pct_thu,
        data.xong_trung_thu, data.chu_hang_ho_tro, data.giam_tru, data.ly_do_giam_tru,
        data.boi_thuong_chu_hang, data.so_ngay_neo_cho_phep_thu, data.don_gia_neo_thu
    ))
    
    new_id = cur.lastrowid
    
    # Ghi nhật ký
    cur.execute("""
    INSERT INTO salan_nhat_ky_sua (bang, ban_ghi_id, hanh_dong, tai_khoan, thoi_diem)
    VALUES ('salan_chuyen', ?, 'TAO_MOI', ?, ?)
    """, (str(new_id), data.nguoi_nhap, thoi_diem))
    
    con.commit()
    con.close()
    return {"message": "Đã tạo chuyến thành công", "id": new_id, "ma_chuyen": ma_chuyen}

@router.put("/chuyen/{chuyen_id}")
def cap_nhat_chuyen(chuyen_id: int, data: ChuyenCreateUpdate):
    con = get_con()
    cur = con.cursor()
    
    existing = cur.execute("SELECT * FROM salan_chuyen WHERE id = ?", (chuyen_id,)).fetchone()
    if not existing:
        con.close()
        raise HTTPException(status_code=404, detail="Không tìm thấy chuyến")
        
    if existing['khoa_so']:
        raise HTTPException(status_code=400, detail="[C07] Chuyến này đã thanh toán và bị khóa, chỉ Alex mới có quyền mở khóa!")
        
    trang_thai = "da_giao" if data.ngay_giao else "dang_chay"
    thoi_diem = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    cur.execute("""
    UPDATE salan_chuyen SET
        cong_ty = ?, phuong_tien_ma = ?, chu_hang_ma = ?, loai_hang_ma = ?, so_lo_tau = ?, ghi_chu = ?,
        ngay_nhan = ?, noi_nhan_ma = ?, kl_nhan_kg = ?,
        ngay_giao = ?, nha_may_giao_ma = ?, kl_giao_kg = ?,
        don_gia_cuoc = ?, vat_pct = ?,
        co_tinh_neo = ?, don_gia_neo = ?, ngay_cho_phep = ?,
        ho_tro = ?, ghi_chu_ho_tro = ?, co_phun_trung = ?, don_gia_phun_trung = ?,
        hh_cho_phep_pct = ?, gia_boi_thuong = ?, co_thuong = ?, don_gia_thuong = ?,
        so_bang_ke = ?, so_hoa_don_dau_vao = ?, trang_thai = ?,
        hinh_thuc_thu = ?, don_gia_thu = ?, tien_tron_lo = ?, vat_pct_thu = ?,
        xong_trung_thu = ?, chu_hang_ho_tro = ?, giam_tru = ?, ly_do_giam_tru = ?,
        boi_thuong_chu_hang = ?, so_ngay_neo_cho_phep_thu = ?, don_gia_neo_thu = ?
    WHERE id = ?
    """, (
        data.cong_ty, data.phuong_tien_ma, data.chu_hang_ma, data.loai_hang_ma, data.so_lo_tau, data.ghi_chu,
        data.ngay_nhan, data.noi_nhan_ma, data.kl_nhan_kg,
        data.ngay_giao, data.nha_may_giao_ma, data.kl_giao_kg,
        data.don_gia_cuoc, data.vat_pct,
        1 if data.co_tinh_neo else 0, data.don_gia_neo, data.ngay_cho_phep,
        data.ho_tro, data.ghi_chu_ho_tro, 1 if data.co_phun_trung else 0, data.don_gia_phun_trung,
        data.hh_cho_phep_pct, data.gia_boi_thuong, 1 if data.co_thuong else 0, data.don_gia_thuong,
        data.so_bang_ke, data.so_hoa_don_dau_vao, trang_thai,
        data.hinh_thuc_thu, data.don_gia_thu, data.tien_tron_lo, data.vat_pct_thu,
        data.xong_trung_thu, data.chu_hang_ho_tro, data.giam_tru, data.ly_do_giam_tru,
        data.boi_thuong_chu_hang, data.so_ngay_neo_cho_phep_thu, data.don_gia_neo_thu,
        chuyen_id
    ))
    
    # Ghi nhật ký sửa chi tiết vào bảng nhat_ky
    gia_tri_cu = {
        "don_gia_cuoc": existing["don_gia_cuoc"],
        "kl_nhan_kg": existing["kl_nhan_kg"],
        "kl_giao_kg": existing["kl_giao_kg"],
        "co_tinh_neo": existing["co_tinh_neo"],
        "don_gia_neo": existing["don_gia_neo"],
        "trang_thai": existing["trang_thai"],
        "so_bang_ke": existing["so_bang_ke"]
    }
    gia_tri_moi = {
        "don_gia_cuoc": data.don_gia_cuoc,
        "kl_nhan_kg": data.kl_nhan_kg,
        "kl_giao_kg": data.kl_giao_kg,
        "co_tinh_neo": 1 if data.co_tinh_neo else 0,
        "don_gia_neo": data.don_gia_neo,
        "trang_thai": trang_thai,
        "so_bang_ke": data.so_bang_ke
    }
    ghi_nhat_ky(cur, "salan_chuyen", str(chuyen_id), "sua", gia_tri_cu=gia_tri_cu, gia_tri_moi=gia_tri_moi, nguoi_dung_id=data.nguoi_nhap)
    
    con.commit()
    con.close()
    return {"message": "Đã cập nhật chuyến thành công"}

@router.delete("/chuyen/{chuyen_id}")
def xoa_chuyen(chuyen_id: int, ly_do: str = Query("Huỷ chuyến", description="Lý do huỷ chuyến")):
    """Xoá mềm chuyến: Đánh dấu da_huy = 1 và lưu nhật ký kiểm toán."""
    con = get_con()
    cur = con.cursor()
    existing = cur.execute("SELECT * FROM salan_chuyen WHERE id = ?", (chuyen_id,)).fetchone()
    if not existing:
        con.close()
        raise HTTPException(status_code=404, detail="Không tìm thấy chuyến")
    if existing["da_huy"]:
        con.close()
        return {"message": "Chuyến đã được huỷ trước đó"}
        
    thoi_diem = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cur.execute("""
    UPDATE salan_chuyen 
    SET da_huy = 1, ly_do_huy = ?, huy_boi = 'Alex', huy_luc = ?
    WHERE id = ?
    """, (ly_do, thoi_diem, chuyen_id))
    
    ghi_nhat_ky(
        cur, "salan_chuyen", str(chuyen_id), "huy",
        gia_tri_cu={"ma_chuyen": existing["ma_chuyen"], "da_huy": 0},
        gia_tri_moi={"ma_chuyen": existing["ma_chuyen"], "da_huy": 1, "ly_do_huy": ly_do},
        nguoi_dung_id="Alex"
    )
    con.commit()
    con.close()
    return {"message": "Đã đánh dấu huỷ chuyến thành công (xoá mềm, lưu nhật ký)"}

class DoDauItem(BaseModel):
    ngay: str
    noi_do_ma: Optional[str] = None
    so_lit: float
    gia_dau: int
    ghi_chu: Optional[str] = None

@router.post("/chuyen/{chuyen_id}/dau")
def them_do_dau(chuyen_id: int, item: DoDauItem):
    tien_dau = round_cur(Decimal(str(item.so_lit)) * Decimal(item.gia_dau))
    con = get_con()
    cur = con.cursor()
    cur.execute("""
    INSERT INTO salan_do_dau (chuyen_id, ngay, noi_do_ma, so_lit, gia_dau, tien_dau, ghi_chu)
    VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (chuyen_id, item.ngay, item.noi_do_ma, item.so_lit, item.gia_dau, tien_dau, item.ghi_chu))
    new_id = cur.lastrowid
    ghi_nhat_ky(cur, "salan_do_dau", str(new_id), "tao", gia_tri_cu=None, gia_tri_moi={"chuyen_id": chuyen_id, "so_lit": item.so_lit, "tien_dau": tien_dau})
    con.commit()
    con.close()
    return {"message": "Đã thêm lần đổ dầu", "tien_dau": tien_dau, "id": new_id}

class UngPhiItem(BaseModel):
    ngay: str
    so_tien: int
    noi_dung: Optional[str] = None

@router.post("/chuyen/{chuyen_id}/ung")
def them_ung_phi(chuyen_id: int, item: UngPhiItem):
    con = get_con()
    cur = con.cursor()
    cur.execute("""
    INSERT INTO salan_ung_phi (chuyen_id, ngay, so_tien, noi_dung)
    VALUES (?, ?, ?, ?)
    """, (chuyen_id, item.ngay, item.so_tien, item.noi_dung))
    new_id = cur.lastrowid
    ghi_nhat_ky(cur, "salan_ung_phi", str(new_id), "tao", gia_tri_cu=None, gia_tri_moi={"chuyen_id": chuyen_id, "so_tien": item.so_tien})
    con.commit()
    con.close()
    return {"message": "Đã thêm lần ứng phí", "id": new_id}

@router.delete("/dau/{dau_id}")
def xoa_do_dau(dau_id: int, ly_do: str = Query("Huỷ dòng đổ dầu", description="Lý do huỷ")):
    """Xoá mềm dòng đổ dầu: Đánh dấu da_huy = 1 và ghi nhật ký."""
    con = get_con()
    cur = con.cursor()
    existing = cur.execute("SELECT * FROM salan_do_dau WHERE id = ?", (dau_id,)).fetchone()
    if not existing:
        con.close()
        raise HTTPException(status_code=404, detail="Không tìm thấy dòng dầu")
        
    thoi_diem = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cur.execute("""
    UPDATE salan_do_dau 
    SET da_huy = 1, ly_do_huy = ?, huy_boi = 'Alex', huy_luc = ?
    WHERE id = ?
    """, (ly_do, thoi_diem, dau_id))
    
    ghi_nhat_ky(
        cur, "salan_do_dau", str(dau_id), "huy",
        gia_tri_cu={"chuyen_id": existing["chuyen_id"], "so_lit": existing["so_lit"], "tien_dau": existing["tien_dau"], "da_huy": 0},
        gia_tri_moi={"da_huy": 1, "ly_do_huy": ly_do},
        nguoi_dung_id="Alex"
    )
    con.commit()
    con.close()
    return {"message": "Đã huỷ dòng dầu (xoá mềm, lưu nhật ký)"}

@router.delete("/ung/{ung_id}")
def xoa_ung_phi(ung_id: int, ly_do: str = Query("Huỷ dòng ứng phí", description="Lý do huỷ")):
    """Xoá mềm dòng ứng phí: Đánh dấu da_huy = 1 và ghi nhật ký."""
    con = get_con()
    cur = con.cursor()
    existing = cur.execute("SELECT * FROM salan_ung_phi WHERE id = ?", (ung_id,)).fetchone()
    if not existing:
        con.close()
        raise HTTPException(status_code=404, detail="Không tìm thấy dòng ứng")
        
    thoi_diem = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cur.execute("""
    UPDATE salan_ung_phi 
    SET da_huy = 1, ly_do_huy = ?, huy_boi = 'Alex', huy_luc = ?
    WHERE id = ?
    """, (ly_do, thoi_diem, ung_id))
    
    ghi_nhat_ky(
        cur, "salan_ung_phi", str(ung_id), "huy",
        gia_tri_cu={"chuyen_id": existing["chuyen_id"], "so_tien": existing["so_tien"], "da_huy": 0},
        gia_tri_moi={"da_huy": 1, "ly_do_huy": ly_do},
        nguoi_dung_id="Alex"
    )
    con.commit()
    con.close()
    return {"message": "Đã huỷ dòng ứng (xoá mềm, lưu nhật ký)"}

@router.get("/tong-quan")
def get_tong_quan(cong_ty: Optional[str] = None, thang: Optional[str] = None):
    """Báo cáo tổng quan tình hình sà lan & Lãi gộp (Alex + Ban giám đốc)."""
    con = get_con()
    cur = con.cursor()
    
    sql = "SELECT * FROM salan_chuyen WHERE da_huy = 0"
    params = []
    if cong_ty:
        sql += " AND cong_ty = ?"
        params.append(cong_ty)
    if thang:
        sql += " AND strftime('%Y-%m', ngay_nhan) = ?"
        params.append(thang)
        
    rows = cur.execute(sql, params).fetchall()
    
    tong_chuyen = len(rows)
    tong_kl_giao = 0
    tong_cuoc_sa_lan = 0
    tong_phai_tra = 0
    tong_phai_thu = 0
    tong_lai_gop = 0
    chuyen_chua_tra = 0
    tong_canh_bao = 0
    
    for r in rows:
        row_dict = dict(r)
        c_id = row_dict['id']
        dau_rows = [dict(d) for d in cur.execute("SELECT * FROM salan_do_dau WHERE chuyen_id = ?", (c_id,)).fetchall()]
        ung_rows = [dict(u) for u in cur.execute("SELECT * FROM salan_ung_phi WHERE chuyen_id = ?", (c_id,)).fetchall()]
        calc = tinh_toan_chuyen(row_dict, dau_rows, ung_rows)
        
        tong_kl_giao += row_dict['kl_giao_kg'] or 0
        tong_cuoc_sa_lan += calc['cuoc']
        tong_phai_tra += calc['con_lai_phai_tra']
        tong_phai_thu += calc['phai_thu']
        tong_lai_gop += calc['lai_gop']
        if not row_dict['da_tra_tien']:
            chuyen_chua_tra += 1
        tong_canh_bao += len(calc['canh_bao'])
        
    con.close()
    return {
        "tong_chuyen": tong_chuyen,
        "tong_san_luong_tan": round(tong_kl_giao / 1000.0, 2),
        "tong_cuoc_sa_lan": tong_cuoc_sa_lan,
        "tong_phai_tra_sa_lan": tong_phai_tra,
        "tong_phai_thu_chu_hang": tong_phai_thu,
        "tong_lai_gop": tong_lai_gop,
        "so_chuyen_chua_tra": chuyen_chua_tra,
        "so_canh_bao": tong_canh_bao
    }

@router.post("/seed-du-lieu-chuan")
def seed_du_lieu_chuan():
    """Khởi tạo danh mục gốc và chuyến mẫu thực tế.
    CHỈ cho phép khi APP_ENV=dev VÀ database hoàn toàn chưa có chuyến nào."""
    app_env = os.environ.get("APP_ENV", "production").lower()
    con = get_con()
    cur = con.cursor()
    
    cnt = cur.execute("SELECT COUNT(*) FROM salan_chuyen").fetchone()[0]
    if app_env != "dev" or cnt > 0:
        con.close()
        raise HTTPException(
            status_code=403, 
            detail="[BẢO VỆ DỮ LIỆU] API nạp dữ liệu mẫu bị khoá: Chỉ chạy khi APP_ENV=dev VÀ database chưa có bất kỳ dữ liệu chuyến nào!"
        )
    
    # 1. Danh mục Công ty
    cur.execute("INSERT OR REPLACE INTO salan_cong_ty VALUES ('TP', 'Công ty TNHH Vận tải Trường Phát', '0312345678')")
    cur.execute("INSERT OR REPLACE INTO salan_cong_ty VALUES ('TPL', 'Công ty TNHH Trường Phát Logistics', '0319876543')")
    cur.execute("INSERT OR REPLACE INTO salan_cong_ty VALUES ('NK', 'Công ty CP TM & VT Nguyên Khang', '0315558888')")
    
    # 2. Đối tác sà lan
    cur.execute("INSERT OR REPLACE INTO salan_doi_tac (id, ma, ten, so_dien_thoai, so_tai_khoan, ngan_hang) VALUES (1, 'DT_HIEP', 'Nguyễn Văn Hiệp (Chủ sà lan ĐT 26284)', '0908123456', '19034567890', 'Techcombank')")
    cur.execute("INSERT OR REPLACE INTO salan_doi_tac (id, ma, ten, so_dien_thoai, so_tai_khoan, ngan_hang) VALUES (2, 'DT_LONG', 'Trần Văn Long (Chủ sà lan SG 8888)', '0913987654', '0071000888999', 'Vietcombank')")
    cur.execute("INSERT OR REPLACE INTO salan_doi_tac (id, ma, ten, so_dien_thoai, so_tai_khoan, ngan_hang) VALUES (3, 'DT_HO_THINH', 'Hộ kinh doanh Vận tải Thịnh Phát', '0988776655', '68689999222', 'MBBank')")
    
    # 3. Phương tiện Sà lan
    cur.execute("INSERT OR REPLACE INTO salan_phuong_tien VALUES ('ĐT 26284', 'sa_lan', 'thue', 'doi_tac', 1, '2026-12-31', '2026-12-31', '', 0)")
    cur.execute("INSERT OR REPLACE INTO salan_phuong_tien VALUES ('SG 8888', 'sa_lan', 'chuyen', 'doi_tac', 2, '2026-10-15', '2026-11-20', '', 0)")
    cur.execute("INSERT OR REPLACE INTO salan_phuong_tien VALUES ('ĐT 27198', 'sa_lan', 'chuyen', 'doi_tac', 1, '2026-09-30', '2026-09-30', '', 0)")
    cur.execute("INSERT OR REPLACE INTO salan_phuong_tien VALUES ('LA 05678', 'sa_lan', 'ho_kinh_doanh', 'doi_tac', 3, '2026-11-01', '2026-11-01', 'HĐ-HKD-2026/01', 0)")
    
    # 4. Chủ hàng
    cur.execute("INSERT OR REPLACE INTO salan_chu_hang VALUES ('CH_CJ', 'CJ Vina Agri', 'CJ Cần Đước, CJ Long An', '0302111222', 'CJ Group', 0.0010, 2, 4000, 2)")
    cur.execute("INSERT OR REPLACE INTO salan_chu_hang VALUES ('CH_GREENFEED', 'Greenfeed Việt Nam', 'Greenfeed Bến Lức', '0304333444', 'Greenfeed', 0.0015, 3, 5000, 2)")
    cur.execute("INSERT OR REPLACE INTO salan_chu_hang VALUES ('CH_DEHEUS', 'De Heus Hải Phòng / Đồng Nai', 'De Heus', '0308777999', 'De Heus', 0.0010, 2, 4000, 2)")
    
    # 5. Địa điểm
    cur.execute("INSERT OR REPLACE INTO salan_dia_diem VALUES ('CANG_PHU_MY', 'Cảng Quốc Tế Phú Mỹ', 'noi_nhan', 'Bà Rịa - Vũng Tàu')")
    cur.execute("INSERT OR REPLACE INTO salan_dia_diem VALUES ('CANG_CAT_LAI', 'Cảng Cát Lái', 'noi_nhan', 'TP.HCM')")
    cur.execute("INSERT OR REPLACE INTO salan_dia_diem VALUES ('NM_CJ_CAN_DUOC', 'Nhà máy CJ Cần Đước', 'nha_may_giao', 'Long An')")
    cur.execute("INSERT OR REPLACE INTO salan_dia_diem VALUES ('NM_GREENFEED_BEN_LUC', 'Nhà máy Greenfeed Bến Lức', 'nha_may_giao', 'Long An')")
    cur.execute("INSERT OR REPLACE INTO salan_dia_diem VALUES ('TRAM_DAU_NHA_BE', 'Trạm Xăng Dầu Nhà Bè', 'noi_do_dau', 'TP.HCM')")
    
    # 6. Loại hàng
    cur.execute("INSERT OR REPLACE INTO salan_loai_hang VALUES ('BAP', 'Bắp hạt vàng')")
    cur.execute("INSERT OR REPLACE INTO salan_loai_hang VALUES ('BA_NANH', 'Bã đậu nành')")
    cur.execute("INSERT OR REPLACE INTO salan_loai_hang VALUES ('GO_NEN', 'Viên gỗ nén')")
    
    # CHUYẾN 1: Chuẩn sách giáo khoa ĐT 26284-C01 (Khớp sổ từng đồng: Cước 66.982.270 đ)
    cur.execute("""
    INSERT INTO salan_chuyen (
        id, cong_ty, loai_phuong_tien, ma_chuyen, so_thu_tu, phuong_tien_ma, chu_hang_ma, loai_hang_ma, so_lo_tau, ghi_chu,
        nguoi_nhap, thoi_diem_nhap, trang_thai,
        ngay_nhan, noi_nhan_ma, kl_nhan_kg,
        ngay_giao, nha_may_giao_ma, kl_giao_kg,
        don_gia_cuoc, vat_pct,
        co_tinh_neo, don_gia_neo, ngay_cho_phep,
        ho_tro, ghi_chu_ho_tro, co_phun_trung, don_gia_phun_trung,
        hh_cho_phep_pct, gia_boi_thuong, co_thuong, don_gia_thuong,
        so_bang_ke, so_hoa_don_dau_vao, da_tra_tien,
        hinh_thuc_thu, don_gia_thu, tien_tron_lo, vat_pct_thu,
        xong_trung_thu, chu_hang_ho_tro, giam_tru, boi_thuong_chu_hang
    ) VALUES (
        1, 'TP', 'sa_lan', 'ĐT 26284-C01', 1, 'ĐT 26284', 'CH_CJ', 'BAP', 'Lô 12 - Tàu Ocean Queen', 'Chuyến mẫu chuẩn kiểm chứng cước 66.982.270đ',
        'Hoa', '2026-03-01 08:30:00', 'da_giao',
        '2026-03-01', 'CANG_PHU_MY', 1100000,
        '2026-03-03', 'NM_CJ_CAN_DUOC', 1098070,
        61000, 0.0,
        0, 3000, 2,
        0, '', 0, 3000,
        0.0010, 7500, 0, 0,
        'BK-2026-001', 'HD-00123', 0,
        'theo_tan', 75000, 0, 0.08,
        0, 0, 0, 0
    )""")
    
    # Đổ dầu 1 lần chuyến 1
    cur.execute("""
    INSERT INTO salan_do_dau (chuyen_id, ngay, noi_do_ma, so_lit, gia_dau, tien_dau, ghi_chu)
    VALUES (1, '2026-03-01', 'TRAM_DAU_NHA_BE', 400, 19000, 7600000, 'Cây dầu Nhà Bè cấp phiếu số 889')
    """)
    
    # Ứng phí chuyến 1
    cur.execute("""
    INSERT INTO salan_ung_phi (chuyen_id, ngay, so_tien, noi_dung)
    VALUES (1, '2026-03-01', 5000000, 'Ứng tiền chi phí cầu cảng Phú Mỹ')
    """)
    
    # CHUYẾN 2: Có tính Neo + Phun trùng + Đổ dầu 2 lần + Hụt vượt bồi thường
    cur.execute("""
    INSERT INTO salan_chuyen (
        id, cong_ty, loai_phuong_tien, ma_chuyen, so_thu_tu, phuong_tien_ma, chu_hang_ma, loai_hang_ma, so_lo_tau, ghi_chu,
        nguoi_nhap, thoi_diem_nhap, trang_thai,
        ngay_nhan, noi_nhan_ma, kl_nhan_kg,
        ngay_giao, nha_may_giao_ma, kl_giao_kg,
        don_gia_cuoc, vat_pct,
        co_tinh_neo, don_gia_neo, ngay_cho_phep,
        ho_tro, ghi_chu_ho_tro, co_phun_trung, don_gia_phun_trung,
        hh_cho_phep_pct, gia_boi_thuong, co_thuong, don_gia_thuong,
        so_bang_ke, so_hoa_don_dau_vao, da_tra_tien,
        hinh_thuc_thu, don_gia_thu, tien_tron_lo, vat_pct_thu,
        xong_trung_thu, chu_hang_ho_tro, giam_tru, boi_thuong_chu_hang
    ) VALUES (
        2, 'TPL', 'sa_lan', 'SG 8888-C01', 1, 'SG 8888', 'CH_GREENFEED', 'BA_NANH', 'Lô 05B - Cảng Cát Lái', 'Neo 2 ngày, phun trùng, dầu 2 lần',
        'Mới', '2026-03-05 09:15:00', 'da_giao',
        '2026-03-05', 'CANG_CAT_LAI', 1000000,
        '2026-03-09', 'NM_GREENFEED_BEN_LUC', 998000,
        60000, 0.08,
        1, 3000, 2,
        500000, 'Hỗ trợ neo ban đêm', 1, 3000,
        0.0010, 7500, 0, 0,
        'BK-2026-002', '', 0,
        'theo_tan', 78000, 0, 0.08,
        3500000, 500000, 0, 0
    )""")
    cur.execute("INSERT INTO salan_do_dau (chuyen_id, ngay, noi_do_ma, so_lit, gia_dau, tien_dau, ghi_chu) VALUES (2, '2026-03-05', 'TRAM_DAU_NHA_BE', 500, 19000, 9500000, 'Đổ lần 1')")
    cur.execute("INSERT INTO salan_do_dau (chuyen_id, ngay, noi_do_ma, so_lit, gia_dau, tien_dau, ghi_chu) VALUES (2, '2026-03-07', 'TRAM_DAU_NHA_BE', 300, 19000, 5700000, 'Đổ lần 2')")
    cur.execute("INSERT INTO salan_ung_phi (chuyen_id, ngay, so_tien, noi_dung) VALUES (2, '2026-03-06', 10000000, 'Ứng chuyển khoản thuyền trưởng')")
    cur.execute("INSERT INTO salan_ung_phi (chuyen_id, ngay, so_tien, noi_dung) VALUES (2, '2026-03-08', 5000000, 'Ứng phụ phí dỡ hàng')")

    # CHUYẾN 3: Sà lan đang chạy trên sông (chưa có ngày giao)
    cur.execute("""
    INSERT INTO salan_chuyen (
        id, cong_ty, loai_phuong_tien, ma_chuyen, so_thu_tu, phuong_tien_ma, chu_hang_ma, loai_hang_ma, so_lo_tau, ghi_chu,
        nguoi_nhap, thoi_diem_nhap, trang_thai,
        ngay_nhan, noi_nhan_ma, kl_nhan_kg,
        don_gia_cuoc, vat_pct,
        co_tinh_neo, don_gia_neo, ngay_cho_phep,
        ho_tro, co_phun_trung, don_gia_phun_trung,
        hh_cho_phep_pct, gia_boi_thuong, co_thuong, don_gia_thuong
    ) VALUES (
        3, 'TP', 'sa_lan', 'ĐT 26284-C02', 2, 'ĐT 26284', 'CH_DEHEUS', 'BAP', 'Tàu Polaris Star', 'Đang vận chuyển trên luồng sông',
        'Hoa', '2026-03-24 14:00:00', 'dang_chay',
        '2026-03-24', 'CANG_PHU_MY', 1250000,
        62000, 0.0,
        1, 3000, 2,
        0, 0, 3000,
        0.0010, 7500, 1, 2000
    )""")
    cur.execute("INSERT INTO salan_do_dau (chuyen_id, ngay, noi_do_ma, so_lit, gia_dau, tien_dau, ghi_chu) VALUES (3, '2026-03-24', 'TRAM_DAU_NHA_BE', 450, 19000, 8550000, 'Đổ dầu trước khi chạy')")
    cur.execute("INSERT INTO salan_ung_phi (chuyen_id, ngay, so_tien, noi_dung) VALUES (3, '2026-03-24', 6000000, 'Ứng chi phí luồng lạch')")

    con.commit()
    con.close()
    return {"message": "Đã nạp thành công bộ dữ liệu danh mục & 3 chuyến mẫu thực tế"}
