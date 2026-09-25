#!/usr/bin/env python3
"""
Bộ kiểm tra công thức tính toán tiền sà lan (Trường Phát Logistics).
Kiểm chứng từng đồng theo Mục 6 & Mục 11 của Đặc tả kỹ thuật.
"""

from decimal import Decimal, ROUND_HALF_UP

def round_cur(val):
    """Làm tròn số nguyên đồng (0.5 làm tròn lên) theo chuẩn ngân sách kế toán."""
    return int(Decimal(str(val)).quantize(Decimal('1'), rounding=ROUND_HALF_UP))

def tinh_chuyen_sa_lan(
    kl_nhan_kg: int,
    kl_giao_kg: int,
    don_gia_cuoc: int,
    vat_pct: float,
    ngay_nhan_str: str,
    ngay_giao_str: str,
    ngay_cho_phep: int = 2,
    co_tinh_neo: bool = False,
    don_gia_neo: int = 3000,
    ho_tro: int = 0,
    co_phun_trung: bool = False,
    don_gia_phun_trung: int = 3000,
    danh_sach_dau: list = None, # [{'lit': ..., 'gia': ...}]
    danh_sach_ung: list = None, # [tien, ...]
    hh_cho_phep_pct: float = 0.0010,
    gia_boi_thuong: int = 0,
    co_thuong: bool = False,
    don_gia_thuong: int = 0,
    # Phía thu
    hinh_thuc_thu: str = 'theo_tan',
    don_gia_thu: int = 0,
    tien_tron_lo: int = 0,
    vat_pct_thu: float = 0.08,
    so_ngay_neo_thu_cho_phep: int = 2,
    don_gia_neo_thu: int = 4000,
    xong_trung_thu: int = 0,
    chu_hang_ho_tro: int = 0,
    giam_tru: int = 0,
    boi_thuong_chu_hang: int = 0
):
    from datetime import datetime
    d_nhan = datetime.strptime(ngay_nhan_str, "%Y-%m-%d")
    d_giao = datetime.strptime(ngay_giao_str, "%Y-%m-%d")
    ngay_thuc_te = max(0, (d_giao - d_nhan).days)
    
    # Tấn giao
    T = Decimal(kl_giao_kg) / Decimal(1000)
    
    # 1. Cước
    cuoc = round_cur(T * Decimal(don_gia_cuoc))
    
    # 2. VAT cước
    vat_tien = round_cur(Decimal(cuoc) * Decimal(str(vat_pct)))
    
    # 3. Neo
    ngay_neo = max(0, ngay_thuc_te - ngay_cho_phep)
    tien_neo = round_cur(T * Decimal(don_gia_neo) * Decimal(ngay_neo)) if co_tinh_neo else 0
    
    # 4. Phun trùng
    tien_phun_trung = round_cur(T * Decimal(don_gia_phun_trung)) if co_phun_trung else 0
    
    # 5. Dầu & Ứng
    tien_dau = sum(round_cur(Decimal(str(item['lit'])) * Decimal(item['gia'])) for item in (danh_sach_dau or []))
    tien_ung = sum(item for item in (danh_sach_ung or []))
    
    # 6. Hao hụt
    hao_hut_kg = kl_nhan_kg - kl_giao_kg
    hao_hut_pct = (Decimal(hao_hut_kg) / Decimal(kl_nhan_kg)) if kl_nhan_kg > 0 else Decimal(0)
    muc_cho_phep_kg = round_cur(Decimal(kl_nhan_kg) * Decimal(str(hh_cho_phep_pct)))
    hut_vuot_kg = max(0, hao_hut_kg - muc_cho_phep_kg)
    boi_thuong = round_cur(Decimal(hut_vuot_kg) * Decimal(gia_boi_thuong))
    
    # 7. Thưởng
    # Mục 11: Dôi hàng (hao hụt âm) tính bằng 0, không thưởng phần dôi
    if co_thuong:
        kg_thuong = max(0, muc_cho_phep_kg - max(0, hao_hut_kg))
        tien_thuong = round_cur(Decimal(kg_thuong) * Decimal(don_gia_thuong))
    else:
        kg_thuong = 0
        tien_thuong = 0
        
    # 8. CÒN LẠI PHẢI TRẢ SÀ LAN
    # Cước + VAT + Neo + Hỗ trợ + Phun trùng + Thưởng − Dầu − Ứng − Bồi thường
    con_lai_phai_tra = (
        cuoc + vat_tien + tien_neo + ho_tro + tien_phun_trung + tien_thuong
        - tien_dau - tien_ung - boi_thuong
    )
    
    # Phía thu
    if hinh_thuc_thu == 'tron_lo':
        cuoc_thu = tien_tron_lo
    else:
        cuoc_thu = round_cur(T * Decimal(don_gia_thu))
    vat_thu = round_cur(Decimal(cuoc_thu) * Decimal(str(vat_pct_thu)))
    
    ngay_neo_thu = max(0, ngay_thuc_te - so_ngay_neo_thu_cho_phep)
    neo_thu = round_cur(T * Decimal(don_gia_neo_thu) * Decimal(ngay_neo_thu))
    
    phai_thu = (
        cuoc_thu + vat_thu + neo_thu + xong_trung_thu + chu_hang_ho_tro
        - giam_tru - boi_thuong_chu_hang
    )
    
    # LÃI GỘP (Tính trước VAT)
    thu_truoc_vat = cuoc_thu + neo_thu + xong_trung_thu + chu_hang_ho_tro - giam_tru - boi_thuong_chu_hang
    chi_sa_lan_truoc_vat = cuoc + tien_neo + ho_tro + tien_phun_trung + tien_thuong - boi_thuong
    lai_gop = thu_truoc_vat - chi_sa_lan_truoc_vat
    
    return {
        "cuoc": cuoc,
        "vat_tien": vat_tien,
        "ngay_thuc_te": ngay_thuc_te,
        "ngay_neo": ngay_neo,
        "tien_neo": tien_neo,
        "tien_phun_trung": tien_phun_trung,
        "tien_dau": tien_dau,
        "tien_ung": tien_ung,
        "hao_hut_kg": hao_hut_kg,
        "hao_hut_pct": float(hao_hut_pct),
        "muc_cho_phep_kg": muc_cho_phep_kg,
        "hut_vuot_kg": hut_vuot_kg,
        "boi_thuong": boi_thuong,
        "kg_thuong": kg_thuong,
        "tien_thuong": tien_thuong,
        "con_lai_phai_tra": con_lai_phai_tra,
        "cuoc_thu": cuoc_thu,
        "vat_thu": vat_thu,
        "neo_thu": neo_thu,
        "phai_thu": phai_thu,
        "lai_gop": lai_gop
    }

def run_tests():
    print("--- KIỂM TRA TEST CASE 1: Chuyến thực tế ĐT 26284-C01 (Mục 6) ---")
    # 1.098.070 kg ÷ 1.000 × 61.000 đ/tấn = 66.982.270 đ
    res1 = tinh_chuyen_sa_lan(
        kl_nhan_kg=1100000,
        kl_giao_kg=1098070,
        don_gia_cuoc=61000,
        vat_pct=0.0,
        ngay_nhan_str="2026-03-01",
        ngay_giao_str="2026-03-03"
    )
    assert res1["cuoc"] == 66982270, f"Lệch cước: {res1['cuoc']} != 66982270"
    print(f"✅ Khớp sổ tuyệt đối cước: {res1['cuoc']:,} đ")

    print("\n--- KIỂM TRA TEST CASE 2: Hao hụt vượt & Đổ dầu nhiều lần & Ứng tiền ---")
    res2 = tinh_chuyen_sa_lan(
        kl_nhan_kg=1000000,
        kl_giao_kg=998000, # Hao hụt 2.000 kg. Cho phép 0.10% = 1.000 kg -> Vượt 1.000 kg
        don_gia_cuoc=60000,
        vat_pct=0.08,
        ngay_nhan_str="2026-03-01",
        ngay_giao_str="2026-03-05", # 4 ngày thực tế -> Neo 4 - 2 = 2 ngày
        ngay_cho_phep=2,
        co_tinh_neo=True,
        don_gia_neo=3000,
        ho_tro=500000,
        co_phun_trung=True,
        don_gia_phun_trung=3000,
        danh_sach_dau=[
            {"lit": 500, "gia": 19000}, # 9.500.000
            {"lit": 300, "gia": 19000}  # 5.700.000 -> Tổng dầu = 15.200.000
        ],
        danh_sach_ung=[10000000, 5000000], # Tổng ứng = 15.000.000
        hh_cho_phep_pct=0.0010,
        gia_boi_thuong=7500, # Bồi thường: 1.000 kg * 7.500 = 7.500.000
        co_thuong=False,
        # Thu
        don_gia_thu=75000,
        vat_pct_thu=0.08
    )
    assert res2["cuoc"] == 59880000 # 998 * 60.000
    assert res2["vat_tien"] == round_cur(59880000 * 0.08) # 4.790.400
    assert res2["ngay_neo"] == 2
    assert res2["tien_neo"] == round_cur(998 * 3000 * 2) # 5.988.000
    assert res2["tien_phun_trung"] == round_cur(998 * 3000) # 2.994.000
    assert res2["tien_dau"] == 15200000
    assert res2["tien_ung"] == 15000000
    assert res2["hut_vuot_kg"] == 1000
    assert res2["boi_thuong"] == 7500000
    expected_pay = (
        59880000 + 4790400 + 5988000 + 500000 + 2994000
        - 15200000 - 15000000 - 7500000
    )
    assert res2["con_lai_phai_tra"] == expected_pay, f"{res2['con_lai_phai_tra']} != {expected_pay}"
    print(f"✅ Khớp từng đồng còn lại phải trả: {res2['con_lai_phai_tra']:,} đ")

    print("\n--- KIỂM TRA TEST CASE 3: Dôi hàng (Hao hụt âm) không được thưởng thêm ---")
    res3 = tinh_chuyen_sa_lan(
        kl_nhan_kg=1000000,
        kl_giao_kg=1000500, # Giao nhiều hơn nhận 500 kg
        don_gia_cuoc=60000,
        vat_pct=0.0,
        ngay_nhan_str="2026-03-01",
        ngay_giao_str="2026-03-02",
        co_thuong=True,
        don_gia_thuong=2000,
        hh_cho_phep_pct=0.0010 # Cho phép 1000 kg
    )
    assert res3["hao_hut_kg"] == -500
    # Theo Mục 11: max(0, muc_cho_phep - max(0, hao_hut_kg)) -> max(0, 1000 - 0) = 1000 kg
    assert res3["kg_thuong"] == 1000, f"Kg thưởng dôi hàng sai: {res3['kg_thuong']} != 1000"
    print(f"✅ Quy tắc dôi hàng chuẩn xác, kg thưởng = {res3['kg_thuong']} kg")

    print("\n🎯 TẤT CẢ TEST CASE CÔNG THỨC ĐỀU VƯỢT QUA 100%!")

if __name__ == "__main__":
    run_tests()
