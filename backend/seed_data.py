from datetime import date, timedelta
from database import SessionLocal, engine, Base
import models, auth

Base.metadata.create_all(bind=engine)
db = SessionLocal()

def seed():
    # 1. Admin & Users
    if not db.query(models.User).filter_by(username="admin").first():
        admin = models.User(
            username="admin",
            password_hash=auth.get_password_hash("admin123"),
            full_name="Ban Giám Đốc",
            role="admin"
        )
        staff = models.User(
            username="ketoan",
            password_hash=auth.get_password_hash("123456"),
            full_name="Kế Toán Vận Hành",
            role="staff"
        )
        db.add_all([admin, staff])
        db.commit()

    # 2. 26 Xe Đầu Kéo
    if db.query(models.Vehicle).count() == 0:
        brands = ["Hyundai HD1000", "Chenglong H7", "Howo A7", "Daewoo Novus", "Isuzu Giga", "Hino 700"]
        today = date.today()
        vehicles = []
        for i in range(1, 27):
            plate = f"51C-{70000 + i:05d}"
            brand_choice = brands[i % len(brands)]
            reg_exp = today + timedelta(days=(i * 15 - 20)) # một số xe sắp hết hạn
            ins_exp = today + timedelta(days=(i * 25 + 10))
            badge_exp = today + timedelta(days=(i * 30 + 50))
            status = "active" if i > 3 else ("maintenance" if i == 2 else "active")
            
            v = models.Vehicle(
                plate_number=plate,
                vehicle_type="Đầu kéo",
                brand=brand_choice.split()[0],
                model=brand_choice,
                year=2018 + (i % 6),
                payload_capacity=32.5 + (i % 5),
                status=status,
                registration_expiry=reg_exp,
                insurance_expiry=ins_exp,
                badge_expiry=badge_exp,
                notes=f"Xe đầu kéo phục vụ tuyến cảng Cát Lái - Bình Dương - Đồng Nai"
            )
            vehicles.append(v)
        db.add_all(vehicles)
        db.commit()

    # 3. 10 Sà Lan (4 nhà, 6 thuê)
    if db.query(models.Barge).count() == 0:
        barges = []
        # 4 Sà lan nhà
        for i in range(1, 5):
            b = models.Barge(
                name=f"Sà Lan Hoàng Long {i:02d}",
                registration_number=f"SG-{8000 + i}",
                payload_capacity=1200 + (i * 200),
                ownership_type="owned",
                rental_price_per_day=0.0,
                status="active",
                notes="Sà lan công ty tự vận hành, tuyến Vũng Tàu - Sài Gòn - Miền Tây"
            )
            barges.append(b)
        
        # 6 Sà lan thuê
        for i in range(1, 7):
            b = models.Barge(
                name=f"Sà Lan Thuê HP-{100 + i}",
                registration_number=f"LA-{5000 + i}",
                payload_capacity=1500 + (i * 100),
                ownership_type="rented",
                owner_name=f"Công ty Vận Tải Sông Biển {chr(64+i)}",
                owner_phone=f"090812345{i}",
                rental_price_per_day=4500000.0 + (i * 200000),
                status="active",
                notes=f"Hợp đồng thuê 6 tháng, chạy tuyến Cần Thơ - TP.HCM"
            )
            barges.append(b)
        db.add_all(barges)
        db.commit()

    # 4. Tài xế (15 tài xế mẫu)
    if db.query(models.Driver).count() == 0:
        today = date.today()
        names = [
            "Nguyễn Văn Hùng", "Trần Đình Trọng", "Lê Văn Minh", "Phạm Quốc Toàn",
            "Hoàng Văn Thắng", "Võ Văn Nam", "Đặng Hữu Tài", "Bùi Văn Hưng",
            "Ngô Thanh Bình", "Trịnh Quốc Cường", "Đỗ Minh Tuấn", "Lý Thanh Hải",
            "Vũ Đình Quang", "Dương Văn Lâm", "Hồ Tấn Tài"
        ]
        vehicles = db.query(models.Vehicle).all()
        drivers = []
        for i, name in enumerate(names):
            lic_exp = today + timedelta(days=(i * 25 - 10))
            d = models.Driver(
                full_name=name,
                phone=f"0912{345000 + i}",
                address="TP. Hồ Chí Minh",
                national_id=f"07908500{1000 + i}",
                national_id_expiry=today + timedelta(days=1000),
                license_number=f"790123456{i:02d}",
                license_class="FC",
                license_expiry=lic_exp,
                vehicle_id=vehicles[i % len(vehicles)].id if vehicles else None,
                status="active",
                notes="Tài xế nhiều năm kinh nghiệm, chạy an toàn"
            )
            drivers.append(d)
        db.add_all(drivers)
        db.commit()

    # 5. Bảng kê chuyến hàng mẫu (12 chuyến)
    if db.query(models.Trip).count() == 0:
        today = date.today()
        vehicles = db.query(models.Vehicle).all()
        barges = db.query(models.Barge).all()
        drivers = db.query(models.Driver).all()
        customers = ["Công ty Thép Hòa Phát", "Xi Măng Hà Tiên", "Gỗ An Cường", "Nông Sản Đồng Nai", "Tập đoàn Masan"]

        trips = []
        # Chuyến xe đầu kéo
        for i in range(1, 8):
            t_date = today - timedelta(days=i)
            t = models.Trip(
                trip_date=t_date,
                trip_code=f"BK-{today.strftime('%Y%m')}-{i:04d}",
                vehicle_id=vehicles[i-1].id if vehicles else None,
                driver_id=drivers[i-1].id if drivers else None,
                customer_name=customers[i % len(customers)],
                cargo_type="Thép cuộn / Container",
                origin="Cảng Cát Lái, Q.2, TP.HCM",
                destination="KCN VSIP 1, Bình Dương",
                num_trips=2,
                weight_tons=30.5,
                unit_price=250000,
                total_amount=30.5 * 250000,
                payment_status="paid" if i > 3 else "unpaid",
                notes="Giao đủ, tài xế ký nhận đầy đủ biên bản"
            )
            trips.append(t)
        
        # Chuyến sà lan
        for i in range(1, 5):
            t_date = today - timedelta(days=i*2)
            t = models.Trip(
                trip_date=t_date,
                trip_code=f"BK-SL-{today.strftime('%Y%m')}-{i:04d}",
                barge_id=barges[i-1].id if barges else None,
                customer_name=customers[(i+2) % len(customers)],
                cargo_type="Cát đá xây dựng / Clinker",
                origin="Mỏ đá Thạnh Phú, Đồng Nai",
                destination="Bến Cát, Bình Dương",
                num_trips=1,
                weight_tons=1200.0 + (i * 100),
                unit_price=65000,
                total_amount=(1200.0 + i*100) * 65000,
                payment_status="paid" if i % 2 == 0 else "unpaid",
                notes="Vận chuyển đường thủy thuận lợi"
            )
            trips.append(t)
        db.add_all(trips)
        db.commit()

    # 6. Nhiên liệu mẫu
    if db.query(models.FuelRecord).count() == 0:
        today = date.today()
        vehicles = db.query(models.Vehicle).all()
        fuel_records = []
        for i in range(1, 15):
            f_date = today - timedelta(days=i)
            v = vehicles[i % len(vehicles)]
            liters = 200.0 + (i * 10)
            price = 22500.0
            rec = models.FuelRecord(
                record_date=f_date,
                vehicle_id=v.id,
                liters=liters,
                price_per_liter=price,
                total_cost=liters * price,
                station_name="Petrolimex Cát Lái 05",
                odometer=120000.0 + (i * 250),
                notes="Đổ dầu theo lệnh điều xe"
            )
            fuel_records.append(rec)
        db.add_all(fuel_records)
        db.commit()

    print("✅ Khởi tạo dữ liệu mẫu thành công: 26 xe, 10 sà lan (4 nhà, 6 thuê), 15 tài xế, bảng kê & nhiên liệu!")
    db.close()

if __name__ == "__main__":
    seed()
