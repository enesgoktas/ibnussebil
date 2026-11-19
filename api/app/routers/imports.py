from __future__ import annotations

import json
from datetime import date

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import Context, require_dispatcher
from app.models import ImportBatch, Stop
from app.schemas import ImportCommitResponse, ImportPreviewResponse, ImportPreviewRow
from app.services.audit import log_event
from app.services.excel import build_error_csv, build_import_template, parse_import

router = APIRouter(prefix="/imports", tags=["imports"])

_MAX_FILE_BYTES = 5 * 1024 * 1024


@router.get("/template")
def download_template(_: Context = Depends(require_dispatcher)):
    content = build_import_template()
    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": 'attachment; filename="ibnussebil-sablon.xlsx"'},
    )


@router.post("/preview", response_model=ImportPreviewResponse)
async def preview_import(
    file: UploadFile = File(...),
    scheduled_date: date = Form(...),
    context: Context = Depends(require_dispatcher),
    db: Session = Depends(get_db),
):
    if not (file.filename or "").lower().endswith(".xlsx"):
        raise HTTPException(status_code=422, detail="Lütfen .xlsx uzantılı nümune irsal edin.")
    content = await file.read()
    if len(content) > _MAX_FILE_BYTES:
        raise HTTPException(status_code=413, detail="Dosya 5 MB sınırını aşıyor.")

    existing = set(
        db.scalars(select(Stop.external_id).where(Stop.crew_id == context.crew.id)).all()
    )
    try:
        rows, valid, invalid = parse_import(
            content,
            scheduled_date=scheduled_date,
            existing_external_ids=existing,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    if not rows:
        raise HTTPException(status_code=422, detail="Dosyada veri satırı bulunamadı.")

    batch = ImportBatch(
        crew_id=context.crew.id,
        created_by=context.user.id,
        filename=file.filename or "sablon.xlsx",
        scheduled_date=scheduled_date,
        status="preview",
        total_rows=len(rows),
        valid_rows=valid,
        invalid_rows=invalid,
        rows_json=json.dumps(rows, ensure_ascii=False),
    )
    db.add(batch)
    log_event(
        db,
        crew_id=context.crew.id,
        actor_id=context.user.id,
        action="import.previewed",
        details=f"{file.filename}: {valid} geçerli, {invalid} hatalı",
    )
    db.commit()
    db.refresh(batch)

    return ImportPreviewResponse(
        import_id=batch.id,
        filename=batch.filename,
        scheduled_date=batch.scheduled_date,
        total_rows=batch.total_rows,
        valid_rows=batch.valid_rows,
        invalid_rows=batch.invalid_rows,
        rows=[ImportPreviewRow(**row) for row in rows],
    )


@router.post("/{import_id}/commit", response_model=ImportCommitResponse)
def commit_import(
    import_id: int,
    context: Context = Depends(require_dispatcher),
    db: Session = Depends(get_db),
):
    batch = db.get(ImportBatch, import_id)
    if batch is None or batch.crew_id != context.crew.id:
        raise HTTPException(status_code=404, detail="İrsal kaydı bulunamadı.")
    if batch.status != "preview":
        raise HTTPException(status_code=409, detail="Bu irsal zaten işlendi.")

    rows = json.loads(batch.rows_json)
    existing = set(
        db.scalars(select(Stop.external_id).where(Stop.crew_id == context.crew.id)).all()
    )
    created = 0
    skipped = 0
    for row in rows:
        if row["status"] != "valid":
            skipped += 1
            continue
        if row["external_id"] in existing:
            skipped += 1
            continue
        db.add(
            Stop(
                crew_id=context.crew.id,
                import_id=batch.id,
                external_id=row["external_id"],
                recipient_name=row.get("recipient_name") or "",
                phone=row.get("phone") or "",
                address=row["address"],
                lat=float(row["lat"]),
                lon=float(row["lon"]),
                scheduled_date=batch.scheduled_date,
                time_window_start_min=row.get("time_window_start_min"),
                time_window_end_min=row.get("time_window_end_min"),
                weight_kg=row.get("weight_kg"),
                notes=row.get("notes") or "",
                status="unassigned",
            )
        )
        existing.add(row["external_id"])
        created += 1

    if created == 0:
        raise HTTPException(status_code=422, detail="İrsal edilecek geçerli menzil bulunamadı.")

    batch.status = "committed"
    log_event(
        db,
        crew_id=context.crew.id,
        actor_id=context.user.id,
        action="import.committed",
        details=f"{created} menzil eklendi",
    )
    db.commit()
    return ImportCommitResponse(created_count=created, skipped_count=skipped)


@router.get("/{import_id}/errors.csv")
def download_errors(
    import_id: int,
    context: Context = Depends(require_dispatcher),
    db: Session = Depends(get_db),
):
    batch = db.get(ImportBatch, import_id)
    if batch is None or batch.crew_id != context.crew.id:
        raise HTTPException(status_code=404, detail="İrsal kaydı bulunamadı.")
    rows = json.loads(batch.rows_json)
    return Response(
        content=build_error_csv(rows),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="ibnussebil-hatalar-{batch.id}.csv"'},
    )
