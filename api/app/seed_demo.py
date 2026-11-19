from __future__ import annotations

import argparse
from datetime import date, datetime, timezone

from sqlalchemy import select

from app.database import Base, SessionLocal, engine, init_db
from app.models import Crew, Membership, Route, RouteStop, Stop, User
from app.security import generate_invite_code, hash_password, invite_expiry
from app.services.routing import haversine_m

DEMO_PASSWORD = "demo1234"

DEPOT = ("Kadıköy Sevkiyat Deposu", 40.9901, 29.0270)

STOPS = [
    ("ORN-1001", "Ayşe Yılmaz", "05551112233", "Moda Caddesi No: 12, Kadıköy, İstanbul", 40.9872, 29.0257, 540, 720, 2.5, "Kapıda ödeme"),
    ("ORN-1002", "Mehmet Demir", "05552223344", "Bağdat Caddesi No: 145, Kadıköy, İstanbul", 40.9731, 29.0571, 600, 840, 1.2, ""),
    ("ORN-1003", "Zeynep Kaya", "05553334455", "Beşiktaş Çarşı İçi No: 8, Beşiktaş, İstanbul", 41.0422, 29.0094, 0, 0, 4.0, "Aramadan bırakılabilir"),
    ("ORN-1004", "Ali Çelik", "05554445566", "İstiklal Caddesi No: 60, Beyoğlu, İstanbul", 41.0338, 28.9772, 780, 1020, 0.8, ""),
    ("ORN-1005", "Fatma Şahin", "05555556677", "Üsküdar Meydan No: 3, Üsküdar, İstanbul", 41.0265, 29.0150, 540, 780, 3.1, "Ofis resepsiyon"),
    ("ORN-1006", "Hasan Yıldız", "05556667788", "Kadıköy Rıhtım No: 22, Kadıköy, İstanbul", 40.9903, 29.0280, 600, 900, 1.7, ""),
    ("ORN-1007", "Elif Aydın", "05557778899", "Acıbadem Caddesi No: 90, Üsküdar, İstanbul", 41.0021, 29.0430, 0, 0, 2.2, "Komşuya bırakılabilir"),
    ("ORN-1008", "Burak Özkan", "05558889900", "Fenerbahçe Mah. No: 18, Kadıköy, İstanbul", 40.9770, 29.0430, 720, 960, 5.0, "Soğuk zincir"),
    ("ORN-1009", "Merve Arslan", "05559990011", "Şişli Halaskargazi No: 55, Şişli, İstanbul", 41.0600, 28.9870, 660, 900, 1.0, ""),
    ("ORN-1010", "Emre Koç", "05550001122", "Bostancı Sahil Yolu No: 7, Kadıköy, İstanbul", 40.9550, 29.0950, 780, 1080, 3.6, "Otopark girişi"),
    ("ORN-1011", "Selin Acar", "05550002233", "Nişantaşı Abdi İpekçi No: 21, Şişli, İstanbul", 41.0480, 28.9940, 0, 0, 0.9, ""),
    ("ORN-1012", "Kerem Polat", "05550003344", "Maltepe Bağdat Cad. No: 310, Maltepe, İstanbul", 40.9350, 29.1300, 600, 900, 2.0, "Arayın"),
]


def seed(reset: bool = False) -> None:
    if reset:
        Base.metadata.drop_all(bind=engine)
    init_db()

    db = SessionLocal()
    try:
        if db.scalar(select(User).limit(1)) is not None and not reset:
            print("Demo verisi zaten mevcut. Sıfırlamak için --reset kullanın.")
            return

        dispatcher = User(
            full_name="Demo Kervanbaşı",
            phone="05001112233",
            password_hash=hash_password(DEMO_PASSWORD),
        )
        driver = User(
            full_name="Demo Sâik",
            phone="05002223344",
            password_hash=hash_password(DEMO_PASSWORD),
        )
        driver2 = User(
            full_name="İkinci Sâik",
            phone="05003334455",
            password_hash=hash_password(DEMO_PASSWORD),
        )
        db.add_all([dispatcher, driver, driver2])
        db.flush()

        crew = Crew(
            name="Kadıköy Kervanı",
            owner_id=dispatcher.id,
            invite_code=generate_invite_code(),
            invite_expires_at=invite_expiry(365),
            invite_max_uses=100,
            depot_name=DEPOT[0],
            depot_lat=DEPOT[1],
            depot_lon=DEPOT[2],
            shift_start_min=9 * 60,
            shift_end_min=18 * 60,
            service_minutes=5,
            max_stops_per_driver=30,
        )
        db.add(crew)
        db.flush()

        db.add_all(
            [
                Membership(crew_id=crew.id, user_id=dispatcher.id, role="dispatcher"),
                Membership(crew_id=crew.id, user_id=driver.id, role="driver"),
                Membership(crew_id=crew.id, user_id=driver2.id, role="driver"),
            ]
        )

        today = date.today()
        stops: list[Stop] = []
        for index, item in enumerate(STOPS):
            external_id, recipient, phone, address, lat, lon, start, end, weight, notes = item
            stop = Stop(
                crew_id=crew.id,
                external_id=external_id,
                recipient_name=recipient,
                phone=phone,
                address=address,
                lat=lat,
                lon=lon,
                scheduled_date=today,
                time_window_start_min=start or None,
                time_window_end_min=end or None,
                weight_kg=weight,
                notes=notes,
                status="unassigned",
            )
            db.add(stop)
            stops.append(stop)
        db.flush()

        # Seed one published route so the driver demo is useful immediately.
        route_stops = stops[:3]
        for stop in route_stops:
            stop.status = "assigned"
        total_distance = 0
        previous = (DEPOT[1], DEPOT[2])
        for stop in route_stops:
            total_distance += haversine_m(previous[0], previous[1], stop.lat, stop.lon)
            previous = (stop.lat, stop.lon)
        total_distance += haversine_m(previous[0], previous[1], DEPOT[1], DEPOT[2])
        route = Route(
            crew_id=crew.id,
            driver_id=driver.id,
            route_date=today,
            status="published",
            total_distance_m=total_distance,
            total_duration_s=int(total_distance / (28_000 / 3600) * 1.25),
            created_by=dispatcher.id,
            published_at=datetime.now(timezone.utc),
        )
        db.add(route)
        db.flush()
        arrival = 9 * 60
        for sequence, stop in enumerate(route_stops, start=1):
            db.add(
                RouteStop(
                    route_id=route.id,
                    stop_id=stop.id,
                    sequence=sequence,
                    planned_arrival_min=arrival,
                )
            )
            arrival += 25

        db.commit()
        print("Demo verisi hazır.")
        print("")
        print("Kervan kodu:", crew.invite_code)
        print("Kervanbaşı:  05001112233 / demo1234")
        print("Sâik:       05002223344 / demo1234")
        print("Sâik 2:     05003334455 / demo1234")
    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--reset", action="store_true", help="Veritabanını sıfırla")
    args = parser.parse_args()
    seed(reset=args.reset)
