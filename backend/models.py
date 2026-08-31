from sqlalchemy import Column, Integer, String, Float, Date, DateTime, ForeignKey, Boolean, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    full_name = Column(String, nullable=False)
    role = Column(String, default="staff") # admin, manager, staff, viewer
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class Vehicle(Base):
    __tablename__ = "vehicles"

    id = Column(Integer, primary_key=True, index=True)
    plate_number = Column(String, unique=True, index=True, nullable=False) # Biển số xe (63H-042.73...)
    trailer_number = Column(String, nullable=True) # Số Rơ-moóc (63R-011.85...)
    vehicle_type = Column(String, default="Xe Ben") # Xe Ben, Xe Thùng
    brand = Column(String, nullable=True) # Hãng xe
    model = Column(String, nullable=True)
    year = Column(Integer, nullable=True)
    payload_capacity = Column(Float, default=31.5) # Tải trọng (tấn)
    status = Column(String, default="active") # active, maintenance, inactive

    # Giấy tờ & Đăng kiểm
    registration_expiry = Column(Date, nullable=True) # Hạn đăng kiểm
    insurance_expiry = Column(Date, nullable=True) # Hạn bảo hiểm
    badge_expiry = Column(Date, nullable=True) # Hạn phù hiệu xe
    gdd_head_expiry = Column(Date, nullable=True) # Hạn Giấy đi đường Đầu kéo
    gdd_trailer_expiry = Column(Date, nullable=True) # Hạn Giấy đi đường Rơ-moóc

    # Bảo dưỡng thay nhớt (Định mức 15.000 km)
    oil_interval_km = Column(Float, default=15000.0)
    oil_last_km = Column(Float, nullable=True)
    oil_last_date = Column(Date, nullable=True)
    current_odometer = Column(Float, nullable=True)

    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    drivers = relationship("Driver", back_populates="vehicle")
    trips = relationship("Trip", back_populates="vehicle")
    fuel_records = relationship("FuelRecord", back_populates="vehicle")
    tire_records = relationship("TireRecord", back_populates="vehicle")
    tarp_records = relationship("TarpRecord", back_populates="vehicle")

class Barge(Base):
    __tablename__ = "barges"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)
    registration_number = Column(String, nullable=True)
    payload_capacity = Column(Float)
    ownership_type = Column(String, default="owned") # owned (nhà), rented (thuê)
    owner_name = Column(String, nullable=True)
    owner_phone = Column(String, nullable=True)
    rental_price_per_day = Column(Float, default=0.0)
    status = Column(String, default="active")
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    trips = relationship("Trip", back_populates="barge")

class Driver(Base):
    __tablename__ = "drivers"

    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String, nullable=False)
    phone = Column(String, nullable=True)
    address = Column(String, nullable=True)
    national_id = Column(String, nullable=True)
    national_id_expiry = Column(Date, nullable=True)
    license_number = Column(String, nullable=True)
    license_class = Column(String, default="FC")
    license_expiry = Column(Date, nullable=True)
    vehicle_id = Column(Integer, ForeignKey("vehicles.id"), nullable=True)
    status = Column(String, default="active")
    rating_score = Column(Float, default=95.0) # Đánh giá hiệu suất % (90 - 99%)
    fuel_saving_score = Column(Float, default=94.0) # Tiết kiệm dầu %
    safety_score = Column(Float, default=98.0) # An toàn GPS %
    total_trips = Column(Integer, default=0) # Tổng chuyến hoàn thành
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    vehicle = relationship("Vehicle", back_populates="drivers")
    trips = relationship("Trip", back_populates="driver")

class Trip(Base):
    __tablename__ = "trips"

    id = Column(Integer, primary_key=True, index=True)
    trip_date = Column(Date, nullable=False, default=datetime.utcnow)
    trip_code = Column(String, unique=True, index=True, nullable=True)
    vehicle_id = Column(Integer, ForeignKey("vehicles.id"), nullable=True)
    barge_id = Column(Integer, ForeignKey("barges.id"), nullable=True)
    driver_id = Column(Integer, ForeignKey("drivers.id"), nullable=True)
    customer_name = Column(String, nullable=False)
    cargo_type = Column(String, nullable=True)
    origin = Column(String, nullable=False)
    destination = Column(String, nullable=False)
    num_trips = Column(Integer, default=1)
    weight_tons = Column(Float, default=0.0)
    volume_m3 = Column(Float, default=0.0)
    unit_price = Column(Float, default=0.0)
    total_amount = Column(Float, default=0.0)
    payment_status = Column(String, default="unpaid")
    notes = Column(Text, nullable=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    vehicle = relationship("Vehicle", back_populates="trips")
    barge = relationship("Barge", back_populates="trips")
    driver = relationship("Driver", back_populates="trips")

class FuelRecord(Base):
    __tablename__ = "fuel_records"

    id = Column(Integer, primary_key=True, index=True)
    record_date = Column(Date, nullable=False, default=datetime.utcnow)
    vehicle_id = Column(Integer, ForeignKey("vehicles.id"), nullable=False)
    liters = Column(Float, nullable=False)
    price_per_liter = Column(Float, nullable=False)
    total_cost = Column(Float, nullable=False)
    station_name = Column(String, nullable=True)
    odometer = Column(Float, nullable=True)
    notes = Column(Text, nullable=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    vehicle = relationship("Vehicle", back_populates="fuel_records")

class TireRecord(Base):
    __tablename__ = "tire_records"

    id = Column(Integer, primary_key=True, index=True)
    record_date = Column(Date, nullable=False, default=datetime.utcnow)
    vehicle_id = Column(Integer, ForeignKey("vehicles.id"), nullable=False)
    quarter = Column(String, default="Q3") # Q1, Q2, Q3, Q4
    tire_count = Column(Integer, default=2)
    position = Column(String, nullable=True) # Vị trí lắp
    unit_price = Column(Float, default=0.0)
    total_cost = Column(Float, default=0.0)
    supplier = Column(String, nullable=True)
    payment_status = Column(String, default="paid") # paid, unpaid
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    vehicle = relationship("Vehicle", back_populates="tire_records")

class TarpRecord(Base):
    __tablename__ = "tarp_records"

    id = Column(Integer, primary_key=True, index=True)
    record_date = Column(Date, nullable=False, default=datetime.utcnow)
    vehicle_id = Column(Integer, ForeignKey("vehicles.id"), nullable=True)
    description = Column(String, nullable=False) # Kích thước bạt (VD: May bạt da mỏng 6,5x10,7)
    supplier = Column(String, default="Phùng Lĩnh")
    invoice_number = Column(String, nullable=True)
    total_cost = Column(Float, default=0.0)
    payment_status = Column(String, default="paid") # paid, unpaid
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    vehicle = relationship("Vehicle", back_populates="tarp_records")

class WeighbridgeTrip(Base):
    __tablename__ = "weighbridge_trips"

    id = Column(Integer, primary_key=True, index=True)
    trip_order = Column(Integer, nullable=True)
    plate_number = Column(String, index=True, nullable=False)
    trip_type = Column(String, default="Đường dài")
    date_receive = Column(String, nullable=True)
    date_delivery = Column(String, nullable=True)
    origin = Column(String, nullable=True)
    destination = Column(String, nullable=True)
    commodity = Column(String, nullable=True)
    weight_receive_kg = Column(Float, default=0.0)
    weight_delivery_kg = Column(Float, default=0.0)
    weight_loss_kg = Column(Float, default=0.0)
    weight_loss_pct = Column(Float, default=0.0)
    unit_price = Column(Float, default=0.0)
    amount_by_ton = Column(Float, default=0.0)
    amount_by_trip = Column(Float, default=0.0)
    
    cost_toll = Column(Float, default=0.0)
    cost_load = Column(Float, default=0.0)
    cost_unload = Column(Float, default=0.0)
    cost_parking = Column(Float, default=0.0)
    cost_tip = Column(Float, default=0.0)
    cost_other = Column(Float, default=0.0)
    cost_station = Column(Float, default=0.0)
    total_cost = Column(Float, default=0.0)
    cost_driver_reported = Column(Float, default=0.0)
    cost_difference = Column(Float, default=0.0)
    
    notes = Column(Text, nullable=True)
    num_trips = Column(Integer, default=1)
    driver_name = Column(String, nullable=True)
    # Vehicle category: Xe Ben vs Xe Thùng
    vehicle_category = Column(String, default="Xe Ben")

    # Chi đầu nhận
    cost_load_origin = Column(Float, default=0.0)      # Bốc lên hàng
    cost_gate_origin = Column(Float, default=0.0)      # Cổng / Bến nhận
    cost_tarp_origin = Column(Float, default=0.0)      # Quét thùng / lót bạt nhận

    # Chi đầu giao
    cost_unload_dest = Column(Float, default=0.0)      # Bốc xuống hàng
    cost_parking_dest = Column(Float, default=0.0)     # Bến bãi / trạm cân giao
    cost_tarp_dest = Column(Float, default=0.0)        # Tháo kèo / bạt giao

    # Đánh dấu không chắc chắn để tô màu & chỉnh sửa
    is_uncertain = Column(Boolean, default=False)
    uncertain_fields = Column(Text, nullable=True)     # JSON array string e.g. ["sl_giao_kg"]

    # Tracking & Verification
    exchange_ticket_no = Column(String, nullable=True)
    is_office_exchanged = Column(Boolean, default=False)
    driver_weight_reported = Column(Float, nullable=True)
    weight_check_note = Column(String, nullable=True)
    source_images_json = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class VehicleCostItem(Base):
    """
    Theo dõi Chi Phí Ngoài Chuyến theo từng xe:
    Dầu DO, Urê, Vá vỏ / lốp, Sửa chữa, Mua vật tư, Bến bãi, Ứng tiền.
    Khớp 100% với Sheet 'CHI PHÍ NGOÀI CHUYẾN' và 'CP THEO XE'.
    """
    __tablename__ = "vehicle_cost_items"

    id = Column(Integer, primary_key=True, index=True)
    plate_number = Column(String, index=True, nullable=False)
    driver_name = Column(String, nullable=True)
    cost_date = Column(String, nullable=True)  # YYYY-MM-DD or DD/MM/YYYY
    cost_type = Column(String, index=True, nullable=False)  # Dầu DO, Urê, Vá vỏ / lốp, Sửa chữa, Mua vật tư, Bến bãi, Ứng tiền
    description = Column(Text, nullable=True)
    liters = Column(Float, nullable=True)
    unit_price = Column(Float, nullable=True)
    amount = Column(Float, default=0.0)
    odo_km = Column(Float, nullable=True)
    source_image = Column(String, nullable=True)
    raw_ocr_snippet = Column(Text, nullable=True)
    is_verified = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class ZaloProcessedFile(Base):
    """
    Quản lý danh sách ảnh Zalo đã quét hằng ngày:
    Đảm bảo 100% không bao giờ bỏ sót file nào và không quét trùng lặp.
    """
    __tablename__ = "zalo_processed_files"

    id = Column(Integer, primary_key=True, index=True)
    file_path = Column(String, unique=True, index=True, nullable=False)
    file_name = Column(String, nullable=False)
    file_size = Column(Integer, default=0)
    file_mtime = Column(Float, default=0.0)
    detected_category = Column(String, nullable=True)
    plate_number = Column(String, nullable=True)
    trip_id = Column(Integer, nullable=True)
    cost_item_id = Column(Integer, nullable=True)
    status = Column(String, default="processed")  # processed, error, pending_review
    processed_at = Column(DateTime, default=datetime.utcnow)

class SystemSetting(Base):
    __tablename__ = "system_settings"

    key = Column(String, primary_key=True, index=True)
    value = Column(Text, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
