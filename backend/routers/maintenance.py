from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from datetime import date, timedelta
import models, schemas, auth
from database import get_db
from sheets_service import sheets_client
from gps_service import gps_client, OFFICIAL_DRIVERS_BY_CLEAN_PLATE

router = APIRouter(prefix="/api/maintenance", tags=["Maintenance"])

APPS_SCRIPT_TEMPLATE = """// ============================================================================
// GOOGLE APPS SCRIPT ĐỒNG BỘ 2 CHIỀU: PHẦN MỀM WEB ⇄ GOOGLE TRANG TÍNH
// Dán mã này vào Tiện ích mở rộng -> Apps Script trên file ĐỔ DẦU - BẢO DƯỠNG
// Nhấn Triển khai (Deploy) -> Nội dung triển khai mới -> Ứng dụng Web (Bất kỳ ai)
// ============================================================================
function doPost(e) {
  try {
    var data = JSON.parse(e.postData.contents);
    var cat = data.category;
    var p = data.payload || {};
    var ss = SpreadsheetApp.getActiveSpreadsheet();

    if (cat === 'fuel_log') {
      var sh = ss.getSheetByName('ĐỔ DẦU');
      if (sh) {
        sh.appendRow(['', sh.getLastRow() - 12, p.record_date || new Date(), (p.plate_number || '').replace(/[-.]/g, ''), p.station || '', Number(p.liters || 0), Number(p.unit_price || 0), Number(p.total_cost || 0), Number(p.odometer || 0), p.tank_status || 'Đầy bình', p.invoice_no || '', p.payment_status || 'Công nợ (chưa trả)', p.payment_date || '', p.notes || 'Nhập từ Phần mềm']);
      }
    } else if (cat === 'repair_log' || cat === 'oil_maintenance' || cat === 'grease_maintenance' || cat === 'gearbox_maintenance') {
      var shM = ss.getSheetByName('BẢO DƯỠNG XE + MOOC');
      if (shM) {
        shM.appendRow(['', p.record_date || new Date(), (p.plate_number || '').replace(/[-.]/g, ''), p.category || 'Thay nhớt động cơ', Number(p.odometer || p.last_km || 0), p.description || p.notes || 'Cập nhật từ Phần mềm', p.garage || '', p.invoice_no || '', Number(p.amount || 0), p.payment_status || 'Đã thanh toán', p.notes || '']);
      }
    } else if (cat === 'tire_log') {
      var shT = ss.getSheetByName('THAY VỎ XE');
      if (shT) {
        shT.appendRow(['', p.record_date || new Date(), (p.plate_number || '').replace(/[-.]/g, ''), p.position || '', Number(p.quantity || 2), p.brand || '', p.supplier || '', p.invoice_no || '', Number(p.amount || 0), p.payment_status || 'Đã thanh toán', p.notes || '']);
      }
    } else if (cat === 'tarp_log') {
      var shB = ss.getSheetByName('THAY BẠT XE');
      if (shB) {
        shB.appendRow(['', p.record_date || new Date(), (p.plate_number || '').replace(/[-.]/g, ''), p.description || '', p.supplier || 'Phùng Lĩnh', p.invoice_no || '', Number(p.amount || 0), p.payment_status || 'Công nợ (chưa trả)', p.notes || '']);
      }
    }
    return ContentService.createTextOutput(JSON.stringify({status: 'ok'})).setMimeType(ContentService.MimeType.JSON);
  } catch (err) {
    return ContentService.createTextOutput(JSON.stringify({status: 'error', message: err.toString()})).setMimeType(ContentService.MimeType.JSON);
  }
}
"""


@router.get("/full-sheet")
def get_full_maintenance_and_fuel_sheet(
    force_refresh: bool = False,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    """
    Trả về toàn bộ dữ liệu 6 tab từ Google Sheet `ĐỔ DẦU - BẢO DƯỠNG - ĐĂNG KIỂM - THAY VỎ - GIẤY ĐI ĐƯỜNG`
    kết hợp với Định mức dầu BA GPS để đối chiếu song song (BA GPS vs Trang Tính) và dữ liệu nhập 2 chiều.
    """
    wb_data = sheets_client.fetch_full_maintenance_and_fuel_workbook(force_refresh=force_refresh)

    # Đối chiếu Định mức dầu BA GPS vs Định mức dầu Trang Tính cho cả 26 xe
    try:
        gps_fleet = gps_client.fetch_live_fleet()
    except Exception:
        gps_fleet = []

    gps_by_clean = {
        item["plate_number"].replace("-", "").replace(".", "").replace(" ", "").upper(): item
        for item in gps_fleet
    }

    dual_norms = []
    sheet_norms = wb_data.get("fuel", {}).get("vehicle_norms", {})
    for clean_p, sh_info in sheet_norms.items():
        g_item = gps_by_clean.get(clean_p, {})
        bagps_norm = g_item.get("actual_norm", 0.0)
        sheet_norm = sh_info.get("sheet_norm_l100km", 0.0)
        v_type = sh_info.get("vehicle_type", "Xe Ben")
        std_norm = 35.0 if v_type == "Xe Ben" else 33.0
        variance = round(sheet_norm - bagps_norm, 1) if (sheet_norm > 0 and bagps_norm > 0) else 0.0

        dual_norms.append({
            "plate_number": sh_info.get("plate_number"),
            "clean_plate": clean_p,
            "vehicle_type": v_type,
            "driver_name": OFFICIAL_DRIVERS_BY_CLEAN_PLATE.get(clean_p) or g_item.get("driver_name", "Tài xế công ty"),
            "bagps_daily_km": g_item.get("daily_km", 0.0),
            "bagps_consumed_liters": g_item.get("consumed_liters", 0.0),
            "bagps_fuel_level": g_item.get("fuel_liters", 0.0),
            "bagps_norm": bagps_norm,
            "bagps_norm_l100km": bagps_norm,
            "sheet_norm": sheet_norm,
            "sheet_norm_l100km": sheet_norm,
            "standard_norm_l100km": std_norm,
            "diff_norm": variance,
            "variance_l100km": variance,
            "sheet_total_liters": sh_info.get("total_liters", 0.0),
            "sheet_total_cost": sh_info.get("total_cost", 0.0),
            "sheet_total_km": sh_info.get("total_km_tracked", 0),
            "refuel_count": sh_info.get("fill_count", 0),
            "sheet_fill_count": sh_info.get("fill_count", 0),
            "latest_odo": sh_info.get("last_odo", 0),
            "sheet_last_odo": sh_info.get("last_odo", 0),
            "sheet_last_fuel_date": sh_info.get("last_fuel_date", "—")
        })

    webhook_setting = db.query(models.SystemSetting).filter(
        models.SystemSetting.key == "google_apps_script_webhook_url"
    ).first()

    maint = wb_data.get("maintenance", {})
    docs = wb_data.get("documents", {})
    fuel_obj = wb_data.get("fuel", {})
    tires_obj = wb_data.get("tires", {})

    # Đảm bảo cả cấu trúc lồng và cấu trúc phẳng đều có đủ cho Frontend
    docs_enriched = {
        **docs,
        "gdd_list": [
            {
                **d,
                "gdd_head_expiry": d.get("head_expiry", "—"),
                "gdd_trailer_expiry": d.get("trailer_expiry", "—"),
                "bank_name": d.get("notes", "")
            }
            for d in docs.get("road_permits", [])
        ]
    }
    fuel_enriched = {
        **fuel_obj,
        "recent_logs": [
            {
                **r,
                "odo_km": r.get("odometer", 0) if isinstance(r.get("odometer"), (int, float)) else 0
            }
            for r in fuel_obj.get("records", [])
        ]
    }
    tires_enriched = {
        **tires_obj,
        "detail_logs": [
            {
                **t,
                "total_cost": t.get("amount", 0)
            }
            for t in tires_obj.get("logs", [])
        ]
    }
    tarps_enriched = {
        **wb_data.get("tarps", {}),
        "logs": [
            {
                **tp,
                "cost": tp.get("amount", 0)
            }
            for tp in wb_data.get("tarps", {}).get("logs", [])
        ]
    }
    repair_enriched = [
        {
            **rp,
            "km_odo": rp.get("odometer", "—"),
            "garage_name": rp.get("garage", "—"),
            "total_cost": rp.get("amount", 0)
        }
        for rp in maint.get("repair_logs", [])
    ]
    grease_enriched = [
        {
            **gr,
            "next_date": gr.get("next_due_date", "—")
        }
        for gr in maint.get("grease_trailer", [])
    ]

    return {
        **wb_data,
        "oil_maintenance": maint.get("oil_changes", []),
        "repair_logs": repair_enriched,
        "grease_maintenance": grease_enriched,
        "gearbox_maintenance": maint.get("gearbox_oil", []),
        "documents": docs_enriched,
        "fuel": fuel_enriched,
        "tires": tires_enriched,
        "tarps": tarps_enriched,
        "dual_fuel_norms": dual_norms,
        "webhook_url": webhook_setting.value if webhook_setting and webhook_setting.value else "",
        "apps_script_template": APPS_SCRIPT_TEMPLATE
    }


@router.post("/two-way-entry")
def create_or_update_two_way_entry(
    data: Dict[str, Any] = Body(...),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    category = (data.get("category") or "repair_log").strip()
    plate_number = (data.get("plate_number") or "").strip()
    record_date = (data.get("record_date") or data.get("date") or date.today().strftime("%Y-%m-%d")).strip()
    record_key = (data.get("record_key") or "").strip()
    payload = data.get("payload") if isinstance(data.get("payload"), dict) else (
        data.get("data") if isinstance(data.get("data"), dict) else data
    )

    res = sheets_client.save_two_way_record(
        category=category,
        payload=payload,
        plate_number=plate_number,
        record_date=record_date,
        record_key=record_key,
        updated_by=current_user.full_name or current_user.username
    )
    return res


@router.post("/webhook-config")
def save_webhook_config(
    data: Dict[str, Any] = Body(...),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    webhook_url = (data.get("webhook_url") or "").strip()
    fuel_maint_url = (data.get("fuel_maint_sheet_url") or "").strip()

    if "webhook_url" in data:
        s = db.query(models.SystemSetting).filter(models.SystemSetting.key == "google_apps_script_webhook_url").first()
        if not s:
            s = models.SystemSetting(key="google_apps_script_webhook_url", value=webhook_url)
            db.add(s)
        else:
            s.value = webhook_url

    if fuel_maint_url:
        s2 = db.query(models.SystemSetting).filter(models.SystemSetting.key == "fuel_maint_sheet_url").first()
        if not s2:
            s2 = models.SystemSetting(key="fuel_maint_sheet_url", value=fuel_maint_url)
            db.add(s2)
        else:
            s2.value = fuel_maint_url
        sheets_client.cached_full_workbook = None

    db.commit()
    return {
        "status": "success",
        "message": "Đã lưu cấu hình đồng bộ 2 chiều Phần mềm ⇄ Google Trang Tính!",
        "webhook_url": webhook_url
    }


@router.get("/oil")
def get_oil_maintenance_status(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    """
    Trả về danh sách 26 xe từ Bảng ① Thay nhớt động cơ trên Trang Tính.
    """
    try:
        sheet_data = sheets_client.fetch_maintenance_sheet()
        if sheet_data:
            return sheet_data
    except Exception as e:
        print("Error fetching maintenance sheet:", e)

    vehicles = db.query(models.Vehicle).all()
    res = []
    for i, v in enumerate(vehicles, 1):
        res.append({
            "stt": i,
            "plate_number": v.plate_number,
            "norm_km": "15.000",
            "last_km": v.oil_last_km or "—",
            "last_date": v.oil_last_date.strftime("%d/%m/%Y") if v.oil_last_date else "—",
            "current_km": v.current_odometer or "—",
            "due_km": (v.oil_last_km + 15000) if v.oil_last_km else "—",
            "remaining_km": "—",
            "status": "Còn xa",
            "notes": v.notes or ""
        })
    return res


@router.get("/tires/summary")
def get_tires_summary(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    wb_data = sheets_client.fetch_full_maintenance_and_fuel_workbook()
    tires_data = wb_data.get("tires", {})
    by_v = tires_data.get("by_vehicle", [])
    if by_v:
        summary = [{
            "plate_number": item["plate_number"],
            "q1": item.get("q1_tires", 0),
            "q2": item.get("q2_tires", 0),
            "q3": item.get("q3_tires", 0),
            "q4": item.get("q4_tires", 0),
            "total_tires": item.get("total_tires", 0),
            "total_cost": item.get("total_cost", 0.0)
        } for item in by_v]
        return {
            "summary": summary,
            "logs": tires_data.get("logs", []),
            "total_tires_all": tires_data.get("summary", {}).get("total_tires", 193),
            "total_cost_all": tires_data.get("summary", {}).get("total_cost", 917030000.0),
            "unpaid_debt": tires_data.get("summary", {}).get("unpaid_debt", 10900000.0)
        }

    records = db.query(models.TireRecord).all()
    v_map = {}
    for r in records:
        v_p = r.vehicle.plate_number if r.vehicle else "Khác"
        if v_p not in v_map:
            v_map[v_p] = {"plate_number": v_p, "q1": 0, "q2": 0, "q3": 0, "q4": 0, "total_tires": 0, "total_cost": 0.0}
        q = (r.record_date.month - 1) // 3 + 1
        cnt = getattr(r, "tire_count", 2)
        v_map[v_p][f"q{q}"] += cnt
        v_map[v_p]["total_tires"] += cnt
        v_map[v_p]["total_cost"] += r.total_cost

    summary = list(v_map.values())
    return {
        "summary": summary,
        "logs": [],
        "total_tires_all": sum(s["total_tires"] for s in summary),
        "total_cost_all": sum(s["total_cost"] for s in summary),
        "unpaid_debt": 0.0
    }


@router.get("/tarps")
def get_tarp_records(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    wb_data = sheets_client.fetch_full_maintenance_and_fuel_workbook()
    tarp_logs = wb_data.get("tarps", {}).get("logs", [])
    if tarp_logs:
        return tarp_logs
    return db.query(models.TarpRecord).order_by(models.TarpRecord.record_date.desc()).all()
