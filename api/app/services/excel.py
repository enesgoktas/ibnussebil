from __future__ import annotations

import csv
import io
from datetime import date, datetime, time
from typing import Any

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

from app.config import settings
from app.services.geocode import geocode_address

HEADERS = [
    ("menzil_id", "Menzil ID", 16),
    ("alici_adi", "Alıcı Adı", 24),
    ("telefon", "Telefon", 16),
    ("adres", "Adres", 52),
    ("enlem", "Enlem", 12),
    ("boylam", "Boylam", 12),
    ("baslangic_saat", "Başlangıç Saati", 16),
    ("bitis_saat", "Bitiş Saati", 14),
    ("agirlik_kg", "Ağırlık (kg)", 14),
    ("notlar", "Notlar", 32),
]

_ALIASES = {
    "menzil_id": {"menzil_id", "menzil id", "durak_id", "durak id", "stop_id", "stop id", "id"},
    "alici_adi": {"alici_adi", "alıcı adı", "alici", "alıcı", "recipient", "name"},
    "telefon": {"telefon", "phone", "tel"},
    "adres": {"adres", "address"},
    "enlem": {"enlem", "lat", "latitude"},
    "boylam": {"boylam", "lon", "lng", "longitude"},
    "baslangic_saat": {"baslangic_saat", "başlangıç saati", "baslangic", "başlangıç", "start"},
    "bitis_saat": {"bitis_saat", "bitiş saati", "bitis", "bitiş", "end"},
    "agirlik_kg": {"agirlik_kg", "ağırlık kg", "ağırlık", "weight", "weight_kg"},
    "notlar": {"notlar", "not", "notes", "note"},
}

_EXAMPLE_ROWS = [
    ["ORN-001", "Ayşe Yılmaz", "05551112233", "Moda Caddesi No: 12, Kadıköy, İstanbul", 40.9872, 29.0257, "09:00", "12:00", 2.5, "Kapıda ödeme"],
    ["ORN-002", "Mehmet Demir", "05552223344", "Bağdat Caddesi No: 145, Kadıköy, İstanbul", 40.9731, 29.0571, "10:00", "14:00", 1.2, ""],
    ["ORN-003", "Zeynep Kaya", "05553334455", "Beşiktaş Çarşı İçi No: 8, Beşiktaş, İstanbul", 41.0422, 29.0094, "", "", 4.0, "Aramadan bırakılabilir"],
    ["ORN-004", "Ali Çelik", "05554445566", "İstiklal Caddesi No: 60, Beyoğlu, İstanbul", 41.0338, 28.9772, "13:00", "17:00", 0.8, ""],
]


def _style_header(cell, fill: str = "0F3D2E") -> None:
    cell.fill = PatternFill("solid", fgColor=fill)
    cell.font = Font(color="FFFFFF", bold=True, size=11)
    cell.alignment = Alignment(horizontal="center", vertical="center")


def build_import_template() -> bytes:
    wb = Workbook()
    ws = wb.active
    ws.title = "Gönderiler"

    for col, (_, label, width) in enumerate(HEADERS, start=1):
        cell = ws.cell(row=1, column=col, value=label)
        _style_header(cell)
        ws.column_dimensions[get_column_letter(col)].width = width
    ws.freeze_panes = "A2"
    ws.row_dimensions[1].height = 26

    for row in _EXAMPLE_ROWS:
        ws.append(row)

    for row in ws.iter_rows(min_row=2, max_row=ws.max_row, min_col=5, max_col=6):
        for cell in row:
            cell.number_format = "0.000000"

    guide = wb.create_sheet("Nasıl Doldurulur")
    guide.column_dimensions["A"].width = 120
    guide["A1"] = "İbnüssebil — Excel Nümunesi"
    guide["A1"].font = Font(bold=True, size=16)
    notes = [
        "",
        "1. 'Gönderiler' sekmesini doldurun. Örnek satırları silmeyi unutmayın.",
        "2. Menzil ID her kervanda benzersiz olmalıdır. Aynı ID ikinci kez irsal edilirse satır reddedilir.",
        "3. Adres zorunludur. Enlem/boylam varsa adres çözümleme atlanır ve irsal hızlanır.",
        "4. Enlem/boylam yoksa adres, ücretsiz Photon servisi ile çözümlenmeye çalışılır.",
        "5. Saatler 24 saatlik düzende HH:MM olarak girilmelidir. Boş bırakılabilir.",
        "6. Ağırlık kg cinsindendir ve isteğe bağlıdır.",
        "7. En fazla 1.000 menzil irsal edebilirsiniz.",
        "",
        "İpucu: Toplu işlerde enlem/boylam sütunlarını doldurmak en güvenilir yöntemdir.",
    ]
    for index, note in enumerate(notes, start=2):
        guide.cell(row=index, column=1, value=note)

    buffer = io.BytesIO()
    wb.save(buffer)
    return buffer.getvalue()


def _normalize_header(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip().lower().replace("i̇", "i")


def _as_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value).strip()


def _as_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip().replace(",", ".")
    if not text:
        return None
    return float(text)


def _minutes_from_value(value: Any) -> int | None:
    if value is None or value == "":
        return None
    if isinstance(value, time):
        return value.hour * 60 + value.minute
    if isinstance(value, datetime):
        return value.hour * 60 + value.minute
    if isinstance(value, (int, float)):
        number = float(value)
        if 0 <= number <= 1:
            return int(round(number * 24 * 60))
        if 0 <= number <= 1440:
            return int(round(number))
        raise ValueError("Saat 0–24 aralığında olmalı")
    text = str(value).strip().replace(".", ":")
    parts = text.split(":")
    if len(parts) != 2:
        raise ValueError("Saat HH:MM biçiminde olmalı")
    hour, minute = int(parts[0]), int(parts[1])
    if not 0 <= hour <= 23 or not 0 <= minute <= 59:
        raise ValueError("Saat HH:MM biçiminde olmalı")
    return hour * 60 + minute


def parse_import(
    file_bytes: bytes,
    *,
    scheduled_date: date,
    existing_external_ids: set[str],
) -> tuple[list[dict[str, Any]], int, int]:
    try:
        workbook = load_workbook(io.BytesIO(file_bytes), data_only=True, read_only=True)
    except Exception as exc:
        raise ValueError("Dosya okunamadı. Lütfen .xlsx nümunesini kullanın.") from exc

    sheet = workbook.worksheets[0]
    header_values = [cell.value for cell in next(sheet.iter_rows(min_row=1, max_row=1))]
    normalized = [_normalize_header(value) for value in header_values]

    index_by_key: dict[str, int] = {}
    for key, aliases in _ALIASES.items():
        for idx, header in enumerate(normalized):
            if header in aliases:
                index_by_key[key] = idx
                break

    if "menzil_id" not in index_by_key or "adres" not in index_by_key:
        raise ValueError("Nümunede 'menzil_id' ve 'adres' sütunları bulunmalıdır.")

    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    total = 0
    geocode_attempts = 0

    for row_number, cells in enumerate(sheet.iter_rows(min_row=2, values_only=True), start=2):
        if total >= settings.MAX_IMPORT_ROWS:
            break
        if not any(value not in (None, "") for value in cells):
            continue
        total += 1

        def value_for(key: str) -> Any:
            idx = index_by_key.get(key)
            if idx is None or idx >= len(cells):
                return None
            return cells[idx]

        errors: list[str] = []
        external_id = _as_text(value_for("menzil_id"))
        recipient_name = _as_text(value_for("alici_adi"))
        phone = _as_text(value_for("telefon"))
        address = _as_text(value_for("adres"))
        notes = _as_text(value_for("notlar"))

        if not external_id:
            errors.append("Menzil ID boş olamaz.")
        elif external_id in seen:
            errors.append("Menzil ID dosya içinde tekrar ediyor.")
        elif external_id in existing_external_ids:
            errors.append("Bu Menzil ID daha önce irsal edilmiş.")

        if not address:
            errors.append("Adres boş olamaz.")

        lat: float | None = None
        lon: float | None = None
        try:
            lat = _as_float(value_for("enlem"))
            lon = _as_float(value_for("boylam"))
        except ValueError:
            errors.append("Enlem/boylam sayısal olmalı.")

        if (lat is None) ^ (lon is None):
            errors.append("Enlem ve boylam birlikte girilmelidir.")
        elif lat is None and lon is None and address:
            if geocode_attempts >= settings.MAX_GEOCODE_ROWS_PER_IMPORT:
                errors.append(
                    "Koordinatsız adres sınırı aşıldı. Enlem/boylam ekleyin veya "
                    f"en fazla {settings.MAX_GEOCODE_ROWS_PER_IMPORT} menzili koordinatsız irsal edin."
                )
            else:
                geocode_attempts += 1
                resolved = geocode_address(address)
                if resolved is None:
                    errors.append("Adres koordinata çevrilemedi. Enlem/boylam ekleyin.")
                else:
                    lat, lon = resolved

        if lat is not None and not -90 <= lat <= 90:
            errors.append("Enlem -90 ile 90 arasında olmalı.")
        if lon is not None and not -180 <= lon <= 180:
            errors.append("Boylam -180 ile 180 arasında olmalı.")

        start_min: int | None = None
        end_min: int | None = None
        try:
            start_min = _minutes_from_value(value_for("baslangic_saat"))
            end_min = _minutes_from_value(value_for("bitis_saat"))
        except ValueError as exc:
            errors.append(f"Saat hatası: {exc}")

        if (start_min is None) ^ (end_min is None):
            errors.append("Başlangıç ve bitiş saati birlikte girilmelidir.")
        elif start_min is not None and end_min is not None and start_min >= end_min:
            errors.append("Başlangıç saati bitişten önce olmalı.")

        weight: float | None = None
        try:
            weight = _as_float(value_for("agirlik_kg"))
            if weight is not None and weight < 0:
                errors.append("Ağırlık negatif olamaz.")
        except ValueError:
            errors.append("Ağırlık sayısal olmalı.")

        if external_id:
            seen.add(external_id)

        rows.append(
            {
                "row_number": row_number,
                "external_id": external_id,
                "recipient_name": recipient_name,
                "phone": phone,
                "address": address,
                "lat": lat,
                "lon": lon,
                "scheduled_date": scheduled_date.isoformat(),
                "time_window_start_min": start_min,
                "time_window_end_min": end_min,
                "weight_kg": weight,
                "notes": notes,
                "errors": errors,
                "status": "invalid" if errors else "valid",
            }
        )

    valid = sum(1 for row in rows if row["status"] == "valid")
    invalid = len(rows) - valid
    return rows, valid, invalid


def build_error_csv(rows: list[dict[str, Any]]) -> bytes:
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["satir", "menzil_id", "adres", "hatalar"])
    for row in rows:
        if row["status"] == "invalid":
            writer.writerow(
                [
                    row["row_number"],
                    row["external_id"],
                    row["address"],
                    "; ".join(row["errors"]),
                ]
            )
    return buffer.getvalue().encode("utf-8-sig")
