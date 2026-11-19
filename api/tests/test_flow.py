from __future__ import annotations

from datetime import date
from io import BytesIO

from openpyxl import Workbook
from openpyxl.writer.excel import ExcelWriter  # noqa: F401


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _xlsx(rows: list[list]) -> bytes:
    wb = Workbook()
    ws = wb.active
    ws.append(
        [
            "durak_id",
            "alici_adi",
            "telefon",
            "adres",
            "enlem",
            "boylam",
            "baslangic_saat",
            "bitis_saat",
            "agirlik_kg",
            "notlar",
        ]
    )
    for row in rows:
        ws.append(row)
    buffer = BytesIO()
    wb.save(buffer)
    return buffer.getvalue()


def test_full_dispatcher_driver_flow(client):
    today = date.today().isoformat()

    dispatcher = client.post(
        "/api/auth/signup-dispatcher",
        json={
            "full_name": "Test Kervanbaşı",
            "phone": "05001112233",
            "password": "demo1234",
            "crew_name": "Test Kervanı",
            "depot_name": "Test Depo",
            "depot_lat": 40.99,
            "depot_lon": 29.03,
        },
    )
    assert dispatcher.status_code == 201, dispatcher.text
    dispatcher_token = dispatcher.json()["access_token"]

    crew = client.get("/api/crews/me", headers=_auth(dispatcher_token))
    assert crew.status_code == 200, crew.text
    code = crew.json()["invite_code"]
    assert code

    driver = client.post(
        "/api/auth/signup-driver",
        json={
            "full_name": "Test Sâik",
            "phone": "05002223344",
            "password": "demo1234",
            "invite_code": code,
        },
    )
    assert driver.status_code == 201, driver.text
    driver_token = driver.json()["access_token"]

    template = client.get("/api/imports/template", headers=_auth(dispatcher_token))
    assert template.status_code == 200
    assert template.content[:2] == b"PK"

    content = _xlsx(
        [
            ["T-1", "Ayşe", "05551112233", "Moda Cad. No 1, Kadıköy", 40.987, 29.025, "09:00", "12:00", 2, ""],
            ["T-2", "Mehmet", "05552223344", "Bağdat Cad. No 2, Kadıköy", 40.973, 29.057, "10:00", "14:00", 1, ""],
            ["T-3", "Zeynep", "05553334455", "Beşiktaş No 3", 41.042, 29.009, "", "", 3, ""],
            ["T-4", "Ali", "05554445566", "Üsküdar No 4", 41.026, 29.015, "13:00", "17:00", 1, ""],
        ]
    )
    preview = client.post(
        "/api/imports/preview",
        headers=_auth(dispatcher_token),
        files={"file": ("test.xlsx", content, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
        data={"scheduled_date": today},
    )
    assert preview.status_code == 200, preview.text
    payload = preview.json()
    assert payload["valid_rows"] == 4
    assert payload["invalid_rows"] == 0

    commit = client.post(
        f"/api/imports/{payload['import_id']}/commit",
        headers=_auth(dispatcher_token),
    )
    assert commit.status_code == 200, commit.text
    assert commit.json()["created_count"] == 4

    stops = client.get(f"/api/stops?route_date={today}", headers=_auth(dispatcher_token))
    assert stops.status_code == 200, stops.text
    assert len(stops.json()) == 4

    drivers = client.get("/api/crews/members", headers=_auth(dispatcher_token))
    driver_id = next(item["id"] for item in drivers.json() if item["role"] == "driver")

    optimized = client.post(
        "/api/routes/optimize",
        headers=_auth(dispatcher_token),
        json={"route_date": today, "driver_ids": [driver_id]},
    )
    assert optimized.status_code == 200, optimized.text
    optimized_payload = optimized.json()
    assert len(optimized_payload["routes"]) == 1
    assert optimized_payload["routes"][0]["stop_count"] == 4
    route_id = optimized_payload["routes"][0]["id"]
    original_order = [item["id"] for item in optimized_payload["routes"][0]["stops"]]

    reordered = client.post(
        f"/api/routes/{route_id}/reorder",
        headers=_auth(dispatcher_token),
        json={"route_stop_ids": list(reversed(original_order))},
    )
    assert reordered.status_code == 200, reordered.text
    assert [item["id"] for item in reordered.json()["stops"]] == list(reversed(original_order))

    last_item = reordered.json()["stops"][-1]
    removed = client.delete(
        f"/api/routes/{route_id}/stops/{last_item['id']}",
        headers=_auth(dispatcher_token),
    )
    assert removed.status_code == 200, removed.text
    assert removed.json()["stop_count"] == 3

    added = client.post(
        f"/api/routes/{route_id}/stops",
        headers=_auth(dispatcher_token),
        json={"stop_id": last_item["stop"]["id"]},
    )
    assert added.status_code == 200, added.text
    assert added.json()["stop_count"] == 4

    published = client.post(f"/api/routes/{route_id}/publish", headers=_auth(dispatcher_token))
    assert published.status_code == 200, published.text

    geometry = client.get(f"/api/routes/{route_id}/geometry", headers=_auth(dispatcher_token))
    assert geometry.status_code == 200, geometry.text
    assert geometry.json()["source"] == "fallback"
    assert len(geometry.json()["coordinates"]) == 6

    no_route_before = client.get(
        "/api/driver/route", headers=_auth(driver_token), params={"route_date": today}
    )
    assert no_route_before.status_code == 200, no_route_before.text
    driver_route = no_route_before.json()
    assert driver_route["stop_count"] == 4

    first_stop = driver_route["stops"][0]
    update = client.patch(
        f"/api/driver/route-stops/{first_stop['id']}",
        headers=_auth(driver_token),
        json={"status": "delivered", "driver_note": "Teslim edildi"},
    )
    assert update.status_code == 200, update.text
    assert update.json()["status"] == "delivered"

    manual = client.post(
        "/api/stops",
        headers=_auth(dispatcher_token),
        json={
            "recipient_name": "Manuel Menzil",
            "phone": "05550001111",
            "address": "Moda Caddesi No: 77, Kadıköy",
            "lat": 40.9875,
            "lon": 29.0265,
            "scheduled_date": today,
            "time_window_start_min": 600,
            "time_window_end_min": 720,
            "weight_kg": 1.5,
            "notes": "Manuel eklendi",
        },
    )
    assert manual.status_code == 201, manual.text
    assert manual.json()["status"] == "unassigned"

    # Driver cannot see the crew invite code.
    me = client.get("/api/auth/me", headers=_auth(driver_token))
    assert me.status_code == 200
    assert me.json()["invite_code"] is None

    # Promote driver to dispatcher.
    promoted = client.patch(
        f"/api/crews/members/{driver_id}/role",
        headers=_auth(dispatcher_token),
        json={"role": "dispatcher"},
    )
    assert promoted.status_code == 200, promoted.text
    driver_me = client.get("/api/auth/me", headers=_auth(driver_token))
    assert driver_me.json()["role"] == "dispatcher"

    # Owner cannot demote themselves when they are the only dispatcher.
    demote = client.patch(
        f"/api/crews/members/{dispatcher.json()['user']['id']}/role",
        headers=_auth(dispatcher_token),
        json={"role": "driver"},
    )
    assert demote.status_code == 200, demote.text
    # Ownership was transferred to the other dispatcher.
    crew_after = client.get("/api/crews/me", headers=_auth(dispatcher_token))
    assert crew_after.status_code == 200
    assert crew_after.json()["is_owner"] is False


def test_permissions_and_import_errors(client):
    dispatcher = client.post(
        "/api/auth/signup-dispatcher",
        json={
            "full_name": "Sahip",
            "phone": "05009998877",
            "password": "demo1234",
            "crew_name": "Yetki Kervanı",
        },
    )
    token = dispatcher.json()["access_token"]
    today = date.today().isoformat()

    content = _xlsx(
        [
            ["DUP-1", "A", "", "Adres 1", 41.0, 29.0, "", "", "", ""],
            ["DUP-1", "B", "", "Adres 2", 41.1, 29.1, "", "", "", ""],
            ["", "C", "", "Adres 3", 41.2, 29.2, "", "", "", ""],
        ]
    )
    preview = client.post(
        "/api/imports/preview",
        headers=_auth(token),
        files={"file": ("bad.xlsx", content, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
        data={"scheduled_date": today},
    )
    assert preview.status_code == 200, preview.text
    body = preview.json()
    assert body["valid_rows"] == 1
    assert body["invalid_rows"] == 2
    errors = " ".join(" ".join(row["errors"]) for row in body["rows"] if row["status"] == "invalid")
    assert "tekrar" in errors
    assert "boş" in errors
