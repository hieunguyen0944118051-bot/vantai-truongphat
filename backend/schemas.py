from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import date, datetime

# Token
class Token(BaseModel):
    access_token: str
    token_type: str
    user: dict

# User
class UserBase(BaseModel):
    username: str
    full_name: str
    role: Optional[str] = "staff"
    is_active: Optional[bool] = True

class UserCreate(UserBase):
    password: str

class UserOut(UserBase):
    id: int
    created_at: datetime
    class Config:
        from_attributes = True

class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str
    confirm_password: str

# Vehicle
class VehicleBase(BaseModel):
    plate_number: str
    trailer_number: Optional[str] = None
    vehicle_type: Optional[str] = "Xe Ben"
    brand: Optional[str] = None
    model: Optional[str] = None
    year: Optional[int] = None
    payload_capacity: Optional[float] = 31.5
    status: Optional[str] = "active"
    registration_expiry: Optional[date] = None
    insurance_expiry: Optional[date] = None
    badge_expiry: Optional[date] = None
    gdd_head_expiry: Optional[date] = None
    gdd_trailer_expiry: Optional[date] = None
    oil_interval_km: Optional[float] = 15000.0
    oil_last_km: Optional[float] = None
    oil_last_date: Optional[date] = None
    current_odometer: Optional[float] = None
    notes: Optional[str] = None

class VehicleCreate(VehicleBase):
    pass

class VehicleUpdate(BaseModel):
    plate_number: Optional[str] = None
    trailer_number: Optional[str] = None
    vehicle_type: Optional[str] = None
    brand: Optional[str] = None
    model: Optional[str] = None
    year: Optional[int] = None
    payload_capacity: Optional[float] = None
    status: Optional[str] = None
    registration_expiry: Optional[date] = None
    insurance_expiry: Optional[date] = None
    badge_expiry: Optional[date] = None
    gdd_head_expiry: Optional[date] = None
    gdd_trailer_expiry: Optional[date] = None
    oil_interval_km: Optional[float] = None
    oil_last_km: Optional[float] = None
    oil_last_date: Optional[date] = None
    current_odometer: Optional[float] = None
    notes: Optional[str] = None

class VehicleOut(VehicleBase):
    id: int
    created_at: datetime
    class Config:
        from_attributes = True

# Barge
class BargeBase(BaseModel):
    name: str
    registration_number: Optional[str] = None
    payload_capacity: Optional[float] = None
    ownership_type: Optional[str] = "owned"
    owner_name: Optional[str] = None
    owner_phone: Optional[str] = None
    rental_price_per_day: Optional[float] = 0.0
    status: Optional[str] = "active"
    notes: Optional[str] = None

class BargeCreate(BargeBase):
    pass

class BargeUpdate(BaseModel):
    name: Optional[str] = None
    registration_number: Optional[str] = None
    payload_capacity: Optional[float] = None
    ownership_type: Optional[str] = None
    owner_name: Optional[str] = None
    owner_phone: Optional[str] = None
    rental_price_per_day: Optional[float] = None
    status: Optional[str] = None
    notes: Optional[str] = None

class BargeOut(BargeBase):
    id: int
    created_at: datetime
    class Config:
        from_attributes = True

# Driver
class DriverBase(BaseModel):
    full_name: str
    phone: Optional[str] = None
    address: Optional[str] = None
    national_id: Optional[str] = None
    national_id_expiry: Optional[date] = None
    license_number: Optional[str] = None
    license_class: Optional[str] = "FC"
    license_expiry: Optional[date] = None
    vehicle_id: Optional[int] = None
    status: Optional[str] = "active"
    rating_score: Optional[float] = 95.0
    fuel_saving_score: Optional[float] = 94.0
    safety_score: Optional[float] = 98.0
    total_trips: Optional[int] = 0
    notes: Optional[str] = None

class DriverCreate(DriverBase):
    pass

class DriverUpdate(BaseModel):
    full_name: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    national_id: Optional[str] = None
    national_id_expiry: Optional[date] = None
    license_number: Optional[str] = None
    license_class: Optional[str] = None
    license_expiry: Optional[date] = None
    vehicle_id: Optional[int] = None
    status: Optional[str] = None
    rating_score: Optional[float] = None
    fuel_saving_score: Optional[float] = None
    safety_score: Optional[float] = None
    total_trips: Optional[int] = None
    notes: Optional[str] = None

class DriverOut(DriverBase):
    id: int
    created_at: datetime
    vehicle: Optional[VehicleOut] = None
    class Config:
        from_attributes = True

# Trip
class TripBase(BaseModel):
    trip_date: date
    trip_code: Optional[str] = None
    vehicle_id: Optional[int] = None
    barge_id: Optional[int] = None
    driver_id: Optional[int] = None
    customer_name: str
    cargo_type: Optional[str] = None
    origin: str
    destination: str
    num_trips: Optional[int] = 1
    weight_tons: Optional[float] = 0.0
    volume_m3: Optional[float] = 0.0
    unit_price: Optional[float] = 0.0
    total_amount: Optional[float] = 0.0
    payment_status: Optional[str] = "unpaid"
    notes: Optional[str] = None

class TripCreate(TripBase):
    pass

class TripUpdate(BaseModel):
    trip_date: Optional[date] = None
    trip_code: Optional[str] = None
    vehicle_id: Optional[int] = None
    barge_id: Optional[int] = None
    driver_id: Optional[int] = None
    customer_name: Optional[str] = None
    cargo_type: Optional[str] = None
    origin: Optional[str] = None
    destination: Optional[str] = None
    num_trips: Optional[int] = None
    weight_tons: Optional[float] = None
    volume_m3: Optional[float] = None
    unit_price: Optional[float] = None
    total_amount: Optional[float] = None
    payment_status: Optional[str] = None
    notes: Optional[str] = None

class TripOut(TripBase):
    id: int
    created_at: datetime
    vehicle: Optional[VehicleOut] = None
    barge: Optional[BargeOut] = None
    driver: Optional[DriverOut] = None
    class Config:
        from_attributes = True

# FuelRecord
class FuelRecordBase(BaseModel):
    record_date: date
    vehicle_id: int
    liters: float
    price_per_liter: float
    total_cost: float
    station_name: Optional[str] = None
    odometer: Optional[float] = None
    notes: Optional[str] = None

class FuelRecordCreate(FuelRecordBase):
    pass

class FuelRecordUpdate(BaseModel):
    record_date: Optional[date] = None
    vehicle_id: Optional[int] = None
    liters: Optional[float] = None
    price_per_liter: Optional[float] = None
    total_cost: Optional[float] = None
    station_name: Optional[str] = None
    odometer: Optional[float] = None
    notes: Optional[str] = None

class FuelRecordOut(FuelRecordBase):
    id: int
    created_at: datetime
    vehicle: Optional[VehicleOut] = None
    class Config:
        from_attributes = True

# TireRecord
class TireRecordBase(BaseModel):
    record_date: date
    vehicle_id: int
    quarter: Optional[str] = "Q3"
    tire_count: int
    position: Optional[str] = None
    unit_price: Optional[float] = 0.0
    total_cost: float
    supplier: Optional[str] = None
    payment_status: Optional[str] = "paid"
    notes: Optional[str] = None

class TireRecordCreate(TireRecordBase):
    pass

class TireRecordOut(TireRecordBase):
    id: int
    created_at: datetime
    vehicle: Optional[VehicleOut] = None
    class Config:
        from_attributes = True

# TarpRecord
class TarpRecordBase(BaseModel):
    record_date: date
    vehicle_id: Optional[int] = None
    description: str
    supplier: Optional[str] = "Phùng Lĩnh"
    invoice_number: Optional[str] = None
    total_cost: float
    payment_status: Optional[str] = "paid"
    notes: Optional[str] = None

class TarpRecordCreate(TarpRecordBase):
    pass

class TarpRecordOut(TarpRecordBase):
    id: int
    created_at: datetime
    vehicle: Optional[VehicleOut] = None
    class Config:
        from_attributes = True
