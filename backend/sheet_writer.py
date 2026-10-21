"""Gửi yêu cầu ghi tới Apps Script Web App (apps_script/APP_SYNC.gs).

Cấu hình bằng biến môi trường Render (không ghi trong code):
  APPS_SCRIPT_URL  – link Web App (…/exec)
  APPS_SCRIPT_KEY  – khóa bí mật in ra khi chạy APPSYNC_setup()
Chưa cấu hình -> mọi thao tác ghi trả lỗi rõ ràng, app vẫn đọc bình thường.
"""
import json
import os
import urllib.error
import urllib.request


class SheetWriteError(Exception):
    pass


def configured() -> bool:
    return bool(os.environ.get("APPS_SCRIPT_URL") and os.environ.get("APPS_SCRIPT_KEY"))


def send(action: str, payload: dict, user: str) -> dict:
    url, key = os.environ.get("APPS_SCRIPT_URL"), os.environ.get("APPS_SCRIPT_KEY")
    if not (url and key):
        raise SheetWriteError("Chưa bật ghi vào Google Sheets (thiếu APPS_SCRIPT_URL / APPS_SCRIPT_KEY trên Render).")
    body = json.dumps({"key": key, "action": action, "user": user, **payload}, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"}, method="POST")
    try:
        # Apps Script trả 302 -> urllib tự đi theo bằng GET để lấy kết quả JSON
        with urllib.request.urlopen(req, timeout=40) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
    except urllib.error.URLError as e:
        raise SheetWriteError(f"Không kết nối được Apps Script: {e}") from e
    try:
        out = json.loads(raw)
    except ValueError as e:
        raise SheetWriteError("Apps Script trả về không phải JSON (kiểm tra quyền truy cập Web App: 'Bất kỳ ai').") from e
    if not out.get("ok"):
        raise SheetWriteError(out.get("error") or "Apps Script báo lỗi")
    return out
