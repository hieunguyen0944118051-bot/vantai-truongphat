"""Mã PIN cấp 2: ưu tiên biến môi trường SECURITY_PIN trên Render, sau đó giá trị đã lưu trong CSDL.
Không có mã mặc định nào trong code."""
import os
import models


def pin_setting(db):
    return db.query(models.SystemSetting).filter(
        (models.SystemSetting.key == "security_pin") | (models.SystemSetting.key == "security_pin_code")
    ).first()


def expected_pin(db):
    env = (os.environ.get("SECURITY_PIN") or "").strip()
    if env:
        return env
    s = pin_setting(db)
    return s.value.strip() if (s and s.value and s.value.strip()) else None
