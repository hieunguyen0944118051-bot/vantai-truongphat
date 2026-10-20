from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import date, datetime
import io
import openpyxl
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
import models, schemas, auth
from database import get_db
from sheets_service import sheets_client, SheetNotFoundError
from gps_service import gps_client

router = APIRouter(prefix="/api/trips", tags=["Trips"])

@router.get("/sheets-live")
def get_sheets_live_trips(
    view_date: Optional[str] = Query(None, alias="date"),
    current_user: models.User = Depends(auth.get_current_user)
):
    """
    Get live daily dispatch from Google Sheets, merged with live BA GPS telemetry.
    """
    try:
        res = sheets_client.fetch_daily_trips(target_date=view_date)
    except SheetNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi khi đọc Google Sheets: {str(e)}")

    # Merge real-time GPS telemetry directly
    try:
        fleet = gps_client.fetch_live_fleet()
        gps_map = {
            v["plate_number"].replace("-", "").replace(".", "").replace(" ", "").upper(): v
            for v in fleet
        }
    except Exception:
        gps_map = {}

    for t in res["all_trips"]:
        clean_p = t["raw_plate"].replace("-", "").replace(".", "").replace(" ", "").upper()
        tel = gps_map.get(clean_p)
        if tel:
            t["gps_address"] = tel["address"] or "Bãi xe Trường Phát"
            t["speed"] = tel["speed"]
            t["is_running"] = tel["speed"] > 0
            if tel["speed"] > 0:
                t["movement_state"] = f"🟢 Xe đang chạy ({tel['speed']} km/h)"
                t["op_badge_class"] = "bg-emerald-100 text-emerald-800"
            elif tel["status_type"] == "idling":
                t["movement_state"] = "🟡 Xe dừng nổ máy"
                t["op_badge_class"] = "bg-amber-100 text-amber-800"
            else:
                t["movement_state"] = "⚪ Xe đang đỗ (Tắt máy)"
                t["op_badge_class"] = "bg-slate-100 text-slate-700"
        else:
            t["gps_address"] = "Bãi xe Trường Phát / Đậu bãi"
            t["speed"] = 0
            t["is_running"] = False
            t["movement_state"] = "⚪ Xe đậu bãi"
            t["op_badge_class"] = "bg-slate-100 text-slate-600"

    return {"success": True, "data": res}

@router.post("/sync-sheets")
def sync_trips_from_sheets(
    view_date: Optional[str] = Query(None, alias="date"),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.require_role(["admin", "manager"]))
):
    """
    Sync trips from Google Sheets into the local database for historical reporting.
    """
    try:
        if view_date:
            try:
                sync_date = datetime.strptime(view_date, "%Y-%m-%d").date()
            except Exception:
                sync_date = date.today()
        else:
            sync_date = date.today()

        data = sheets_client.fetch_daily_trips(target_date=sync_date.strftime("%Y-%m-%d"))
        trips = data.get("all_trips", [])
        
        vehicles = db.query(models.Vehicle).all()
        v_map = {v.plate_number.replace("-", "").replace(".", "").replace(" ", "").upper(): v for v in vehicles}

        date_prefix = sync_date.strftime("%Y%m%d")
        synced_count = 0

        for t in trips:
            clean_plate = t["raw_plate"].replace("-", "").replace(".", "").replace(" ", "").upper()
            v = v_map.get(clean_plate)
            
            trip_code = f"TRIP-{date_prefix}-{t['stt']:03d}-{clean_plate[-4:]}"
            existing = db.query(models.Trip).filter(
                models.Trip.trip_code == trip_code
            ).first()

            if existing:
                existing.customer_name = t["customer_name"]
                existing.cargo_type = t["cargo_type"]
                existing.origin = t["origin"]
                existing.destination = t["destination"]
                existing.num_trips = 1 if t["status_code"] == "active" else 0
                existing.weight_tons = 30.0 if t["status_code"] == "active" else 0.0
                existing.notes = t["route"]
            else:
                new_trip = models.Trip(
                    trip_date=sync_date,
                    trip_code=trip_code,
                    vehicle_id=v.id if v else None,
                    customer_name=t["customer_name"],
                    cargo_type=t["cargo_type"],
                    origin=t["origin"],
                    destination=t["destination"],
                    num_trips=1 if t["status_code"] == "active" else 0,
                    weight_tons=30.0 if t["status_code"] == "active" else 0.0,
                    notes=t["route"]
                )
                db.add(new_trip)
                synced_count += 1
        db.commit()
        return {
            "success": True,
            "message": f"Đã đồng bộ thành công {len(trips)} chuyến từ Google Trang Tính ngày {sync_date.strftime('%d/%m/%Y')}!",
            "active_count": data.get("active_count", 0),
            "off_count": data.get("off_count", 0),
            "synced_count": synced_count
        }
    except SheetNotFoundError as e:
        db.rollback()
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Lỗi khi đồng bộ Google Sheets: {str(e)}")

@router.get("", response_model=List[schemas.TripOut])
def get_trips(
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    vehicle_id: Optional[int] = None,
    customer_name: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    query = db.query(models.Trip)
    if date_from:
        query = query.filter(models.Trip.trip_date >= date_from)
    if date_to:
        query = query.filter(models.Trip.trip_date <= date_to)
    if vehicle_id:
        query = query.filter(models.Trip.vehicle_id == vehicle_id)
    if customer_name:
        query = query.filter(models.Trip.customer_name.ilike(f"%{customer_name}%"))
    return query.order_by(models.Trip.trip_date.desc(), models.Trip.id.desc()).all()

@router.get("/export/excel")
def export_trips_excel(
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    try:
        data = sheets_client.fetch_daily_trips()
        trips_data = data["all_trips"]
    except Exception:
        trips_data = []

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Lệnh Điều Xe Thực Tế"

    ws.merge_cells("A1:G1")
    title_cell = ws["A1"]
    title_cell.value = "CÔNG TY TNHH DV VẬN TẢI TRƯỜNG PHÁT - BẢNG ĐIỀU PHỐI XE THỰC TẾ"
    title_cell.font = Font(name="Arial", size=14, bold=True, color="1E3A5F")
    title_cell.alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[1].height = 30

    headers = [
        "STT", "Biển Số Xe", "Loại Xe", "Tuyến Đường (Đi => Đến)",
        "Loại Hàng Hóa", "Chủ Hàng", "Trạng Thái Hoạt Động"
    ]
    for col_num, header in enumerate(headers, 1):
        cell = ws.cell(row=2, column=col_num)
        cell.value = header
        cell.font = Font(name="Arial", size=11, bold=True, color="FFFFFF")
        cell.fill = PatternFill(start_color="1E3A5F", end_color="1E3A5F", fill_type="solid")
        cell.alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[2].height = 25

    thin_border = Border(
        left=Side(style='thin', color='D0D7DE'),
        right=Side(style='thin', color='D0D7DE'),
        top=Side(style='thin', color='D0D7DE'),
        bottom=Side(style='thin', color='D0D7DE')
    )

    for row_idx, t in enumerate(trips_data, 3):
        ws.cell(row=row_idx, column=1, value=t["stt"]).alignment = Alignment(horizontal="center")
        ws.cell(row=row_idx, column=2, value=t["plate_number"]).alignment = Alignment(horizontal="center")
        ws.cell(row=row_idx, column=3, value=t["vehicle_type"]).alignment = Alignment(horizontal="center")
        ws.cell(row=row_idx, column=4, value=t["route"]).alignment = Alignment(horizontal="left")
        ws.cell(row=row_idx, column=5, value=t["cargo_type"]).alignment = Alignment(horizontal="left")
        ws.cell(row=row_idx, column=6, value=t["customer_name"]).alignment = Alignment(horizontal="left")
        ws.cell(row=row_idx, column=7, value=t["status_text"]).alignment = Alignment(horizontal="center")

        for c in range(1, 8):
            ws.cell(row=row_idx, column=c).border = thin_border
            ws.cell(row=row_idx, column=c).font = Font(name="Arial", size=10)

    for col in ws.columns:
        max_len = max(len(str(cell.value or '')) for cell in col)
        col_letter = openpyxl.utils.get_column_letter(col[0].column)
        ws.column_dimensions[col_letter].width = max(max_len + 4, 12)

    output = io.BytesIO()
    wb.save(output)
    output.seek(0)

    filename = f"Bang_Ke_Dieu_Xe_{date.today().strftime('%Y%m%d')}.xlsx"
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

@router.get("/sheets-config")
def get_sheets_config(
    current_user: models.User = Depends(auth.get_current_user)
):
    """Danh sách file XE NHẬN HÀNG theo từng tháng + trạng thái (đã có / chưa có)."""
    return sheets_client.list_month_config()

@router.post("/sheets-config")
def save_sheets_config(
    payload: dict,
    current_user: models.User = Depends(auth.require_role(["admin", "manager"]))
):
    """
    payload:
      {"month": "2026-11", "url": "<link Google Sheets>"}  -> dán tay link cho 1 tháng
      {"month": "2026-11", "url": ""}                      -> xóa link tay, quay về tự dò
      {"folder_ids": "<link/ID thư mục Drive>"}            -> đổi thư mục tự dò
      {"refresh": true}                                     -> dò lại thư mục ngay
    Tương thích cũ: {"month": "09", "url": ...} hiểu là tháng 09 năm hiện tại.
    """
    if "folder_ids" in payload:
        sheets_client._set_setting("sheets_folder_ids", str(payload.get("folder_ids") or "").strip())
        sheets_client.clear_caches()
    if payload.get("refresh"):
        sheets_client.clear_caches()
        sheets_client.discover_month_sheets(force=True)

    month_raw = str(payload.get("month", "")).strip()
    if month_raw:
        url = str(payload.get("url", "") or "").strip()
        if "-" in month_raw:
            yyyy, mm = month_raw.split("-", 1)
            year, month = int(yyyy), int(mm)
        else:
            year, month = date.today().year, int(month_raw)
        if not 1 <= month <= 12:
            raise HTTPException(status_code=400, detail="Tháng không hợp lệ")
        if url and "/spreadsheets/d/" not in url and len(url) < 30:
            raise HTTPException(status_code=400, detail="Link Google Sheets không hợp lệ")
        sheets_client.set_sheet_url_for_month(f"{month:02d}", url, year=year)
        msg = (f"Đã lưu link Trang tính Tháng {month:02d}/{year}!" if url
               else f"Đã xóa link tay Tháng {month:02d}/{year}, app sẽ tự tìm file theo tên.")
    else:
        msg = "Đã cập nhật cấu hình."
    return {"success": True, "message": msg, **sheets_client.list_month_config()}


@router.get("/sheets-debug")
def sheets_debug(
    view_date: Optional[str] = Query(None, alias="date"),
    current_user: models.User = Depends(auth.require_role(["admin"]))
):
    """Chẩn đoán đọc file tháng: tên các tab + 20 dòng đầu của tab ngày được chọn (chỉ admin)."""
    import io as _io, traceback
    d = datetime.strptime(view_date, "%Y-%m-%d").date() if view_date else date.today()
    out = {"date": d.isoformat()}
    try:
        sid = sheets_client.get_sheet_id_for(d)
        out["sheet_id"] = sid
        data = sheets_client._get_xlsx_bytes(sid)
        out["bytes"] = len(data)
        out["head"] = data[:8].hex()
        wb = openpyxl.load_workbook(_io.BytesIO(data), data_only=True, read_only=True)
        out["sheets"] = wb.sheetnames
        day_str = f"{d.day:02d}"
        name = next((n for n in wb.sheetnames if n.strip().startswith(day_str)), None)
        out["matched"] = name
        if name:
            rows = []
            for r in wb[name].iter_rows(values_only=True):
                vals = [str(c).strip() if c is not None else "" for c in r]
                if any(vals):
                    rows.append(vals[:14])
                if len(rows) >= 25:
                    break
            out["rows"] = rows
    except Exception as e:
        out["error"] = repr(e)
        out["trace"] = traceback.format_exc()[-1500:]
    return out
