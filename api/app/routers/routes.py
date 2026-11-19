from __future__ import annotations

from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.database import get_db
from app.deps import Context, get_context, require_dispatcher, require_driver
from app.models import Crew, Membership, Route, RouteStop, Stop
from app.schemas import (
    MessageResponse,
    OptimizeRequest,
    OptimizeResponse,
    RouteAddStopRequest,
    RouteGeometryResponse,
    RouteOut,
    RouteReorderRequest,
    RouteStopOut,
    UpdateStopStatusRequest,
)
from app.serializers import route_out, route_stop_out
from app.services.audit import log_event
from app.services.geometry import route_geometry
from app.services.routing import build_matrix
from app.services.optimizer import OptimizationError, OptDriver, OptStop, optimize

router = APIRouter(tags=["routes"])


def _route_query():
    return select(Route).options(
        joinedload(Route.driver),
        selectinload(Route.stops).joinedload(RouteStop.stop),
    )


def _load_route(db: Session, route_id: int) -> Route | None:
    return db.scalars(_route_query().where(Route.id == route_id)).unique().first()


def _load_routes_for_day(db: Session, crew_id: int, route_date: date) -> list[Route]:
    return list(
        db.scalars(
            _route_query()
            .where(Route.crew_id == crew_id, Route.route_date == route_date)
            .order_by(Route.status.desc(), Route.id.asc())
        )
        .unique()
        .all()
    )


def _recalculate_route(db: Session, route: Route, crew: Crew) -> None:
    ordered = sorted(route.stops, key=lambda item: item.sequence)
    if not ordered:
        route.total_distance_m = 0
        route.total_duration_s = 0
        return
    points: list[tuple[float, float]] = [(crew.depot_lat, crew.depot_lon)]
    points.extend((item.stop.lat, item.stop.lon) for item in ordered)
    points.append((crew.depot_lat, crew.depot_lon))
    distances, durations, _ = build_matrix(points)

    current_time = crew.shift_start_min * 60
    previous = 0
    total_distance = 0
    for index, item in enumerate(ordered, start=1):
        total_distance += distances[previous][index]
        arrival = current_time + durations[previous][index]
        if item.stop.time_window_start_min is not None:
            arrival = max(arrival, item.stop.time_window_start_min * 60)
        item.sequence = index
        item.planned_arrival_min = arrival // 60
        current_time = arrival + crew.service_minutes * 60
        previous = index

    total_distance += distances[previous][0]
    current_time += durations[previous][0]
    route.total_distance_m = int(total_distance)
    route.total_duration_s = int(current_time - crew.shift_start_min * 60)


@router.post("/routes/optimize", response_model=OptimizeResponse)
def optimize_routes(
    payload: OptimizeRequest,
    context: Context = Depends(require_dispatcher),
    db: Session = Depends(get_db),
):
    driver_rows = list(
        db.scalars(
            select(Membership)
            .options(joinedload(Membership.user))
            .where(
                Membership.crew_id == context.crew.id,
                Membership.status == "active",
                Membership.role == "driver",
                Membership.user_id.in_(payload.driver_ids),
            )
        ).all()
    )
    if len(driver_rows) != len(set(payload.driver_ids)):
        raise HTTPException(status_code=404, detail="Seçilen sâiklerden bazıları bulunamadı.")

    # Re-optimizing replaces only drafts. Published routes are never touched.
    drafts = list(
        db.scalars(
            select(Route)
            .options(selectinload(Route.stops).joinedload(RouteStop.stop))
            .where(
                Route.crew_id == context.crew.id,
                Route.route_date == payload.route_date,
                Route.status == "draft",
                Route.driver_id.in_(payload.driver_ids),
            )
        ).all()
    )
    for draft in drafts:
        for route_stop in draft.stops:
            if route_stop.status == "pending":
                route_stop.stop.status = "unassigned"
        db.delete(draft)
    db.flush()

    if payload.stop_ids:
        stops = list(
            db.scalars(
                select(Stop).where(
                    Stop.crew_id == context.crew.id,
                    Stop.scheduled_date == payload.route_date,
                    Stop.id.in_(payload.stop_ids),
                )
            ).all()
        )
        if len(stops) != len(set(payload.stop_ids)):
            raise HTTPException(status_code=404, detail="Bazı menziller bulunamadı.")
        if any(stop.status != "unassigned" for stop in stops):
            raise HTTPException(status_code=409, detail="Seçilen menzillerden bazıları zaten sevkiyata girmiş.")
    else:
        stops = list(
            db.scalars(
                select(Stop).where(
                    Stop.crew_id == context.crew.id,
                    Stop.scheduled_date == payload.route_date,
                    Stop.status == "unassigned",
                )
            ).all()
        )
    if not stops:
        raise HTTPException(status_code=422, detail="Bu tarih için sevkiyat bekleyen menzil yok.")

    try:
        result = optimize(
            depot_lat=context.crew.depot_lat,
            depot_lon=context.crew.depot_lon,
            stops=[
                OptStop(
                    id=stop.id,
                    lat=stop.lat,
                    lon=stop.lon,
                    time_window_start_min=stop.time_window_start_min,
                    time_window_end_min=stop.time_window_end_min,
                )
                for stop in stops
            ],
            drivers=[
                OptDriver(id=row.user_id, max_stops=context.crew.max_stops_per_driver)
                for row in driver_rows
            ],
            shift_start_min=context.crew.shift_start_min,
            shift_end_min=context.crew.shift_end_min,
            service_minutes=context.crew.service_minutes,
        )
    except OptimizationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    stops_by_id = {stop.id: stop for stop in stops}
    created_routes: list[Route] = []
    for optimized in result.routes:
        route = Route(
            crew_id=context.crew.id,
            driver_id=optimized.driver_id,
            route_date=payload.route_date,
            status="draft",
            total_distance_m=optimized.distance_m,
            total_duration_s=optimized.duration_s,
            created_by=context.user.id,
        )
        db.add(route)
        db.flush()
        for sequence, (stop_id, arrival_seconds) in enumerate(optimized.stops, start=1):
            stop = stops_by_id[stop_id]
            stop.status = "assigned"
            db.add(
                RouteStop(
                    route_id=route.id,
                    stop_id=stop.id,
                    sequence=sequence,
                    planned_arrival_min=arrival_seconds // 60 if arrival_seconds is not None else None,
                )
            )
        created_routes.append(route)

    log_event(
        db,
        crew_id=context.crew.id,
        actor_id=context.user.id,
        action="routes.optimized",
        details=f"{len(stops)} menzil, {len(driver_rows)} sâik, {len(result.routes)} güzergâh",
    )
    db.commit()

    created_routes = [route for route in (_load_route(db, route.id) for route in created_routes) if route]
    return OptimizeResponse(
        routes=[route_out(route) for route in created_routes],
        unassigned_stop_ids=result.unassigned_stop_ids,
        matrix_source=result.matrix_source,
        total_distance_m=result.total_distance_m,
        total_duration_s=result.total_duration_s,
    )


@router.get("/routes", response_model=list[RouteOut])
def list_routes(
    route_date: date,
    context: Context = Depends(require_dispatcher),
    db: Session = Depends(get_db),
):
    return [route_out(route) for route in _load_routes_for_day(db, context.crew.id, route_date)]


@router.get("/routes/{route_id}", response_model=RouteOut)
def get_route(
    route_id: int,
    context: Context = Depends(require_dispatcher),
    db: Session = Depends(get_db),
):
    route = _load_route(db, route_id)
    if route is None or route.crew_id != context.crew.id:
        raise HTTPException(status_code=404, detail="Güzergâh bulunamadı.")
    return route_out(route)


@router.get("/routes/{route_id}/geometry", response_model=RouteGeometryResponse)
def get_route_geometry(
    route_id: int,
    context: Context = Depends(get_context),
    db: Session = Depends(get_db),
):
    route = _load_route(db, route_id)
    if route is None or route.crew_id != context.crew.id:
        raise HTTPException(status_code=404, detail="Güzergâh bulunamadı.")
    if context.role == "driver" and route.driver_id != context.user.id:
        raise HTTPException(status_code=403, detail="Bu güzergâh size ait değil.")
    crew = db.get(Crew, route.crew_id)
    if crew is None:
        raise HTTPException(status_code=404, detail="Kervan bulunamadı.")
    ordered = sorted(route.stops, key=lambda item: item.sequence)
    points: list[tuple[float, float]] = [(crew.depot_lat, crew.depot_lon)]
    points.extend((item.stop.lat, item.stop.lon) for item in ordered)
    points.append((crew.depot_lat, crew.depot_lon))
    result = route_geometry(points)
    return RouteGeometryResponse(
        route_id=route.id,
        coordinates=result.coordinates,
        source=result.source,
    )


@router.post("/routes/{route_id}/publish", response_model=RouteOut)
def publish_route(
    route_id: int,
    context: Context = Depends(require_dispatcher),
    db: Session = Depends(get_db),
):
    route = _load_route(db, route_id)
    if route is None or route.crew_id != context.crew.id:
        raise HTTPException(status_code=404, detail="Güzergâh bulunamadı.")
    if route.status != "draft":
        raise HTTPException(status_code=409, detail="Yalnızca taslak güzergâh yola çıkarılabilir.")
    if not route.stops:
        raise HTTPException(status_code=422, detail="Boş güzergâh yola çıkarılamaz.")
    existing = db.scalar(
        select(Route).where(
            Route.crew_id == context.crew.id,
            Route.route_date == route.route_date,
            Route.driver_id == route.driver_id,
            Route.status == "published",
            Route.id != route.id,
        )
    )
    if existing is not None:
        raise HTTPException(
            status_code=409,
            detail="Bu sâik için aynı gün yola çıkarılmış bir güzergâh var. Önce onu taslağa alın.",
        )
    route.status = "published"
    route.published_at = datetime.now(timezone.utc)
    log_event(db, crew_id=context.crew.id, actor_id=context.user.id, action="route.published", details=str(route.id))
    db.commit()
    route = _load_route(db, route.id)
    assert route is not None
    return route_out(route)


@router.post("/routes/{route_id}/unpublish", response_model=RouteOut)
def unpublish_route(
    route_id: int,
    context: Context = Depends(require_dispatcher),
    db: Session = Depends(get_db),
):
    route = _load_route(db, route_id)
    if route is None or route.crew_id != context.crew.id:
        raise HTTPException(status_code=404, detail="Güzergâh bulunamadı.")
    if route.status != "published":
        raise HTTPException(status_code=409, detail="Yalnızca yola çıkarılmış güzergâh taslağa alınabilir.")
    if any(item.status in {"delivered", "failed"} for item in route.stops):
        raise HTTPException(status_code=409, detail="Teslimata başlanmış güzergâh geri alınamaz.")
    route.status = "draft"
    route.published_at = None
    log_event(db, crew_id=context.crew.id, actor_id=context.user.id, action="route.unpublished", details=str(route.id))
    db.commit()
    route = _load_route(db, route.id)
    assert route is not None
    return route_out(route)


@router.post("/routes/{route_id}/reorder", response_model=RouteOut)
def reorder_route(
    route_id: int,
    payload: RouteReorderRequest,
    context: Context = Depends(require_dispatcher),
    db: Session = Depends(get_db),
):
    route = _load_route(db, route_id)
    if route is None or route.crew_id != context.crew.id:
        raise HTTPException(status_code=404, detail="Güzergâh bulunamadı.")
    if route.status != "draft":
        raise HTTPException(status_code=409, detail="Yalnızca taslak güzergâh sıralanabilir.")
    existing_ids = [item.id for item in route.stops]
    if len(payload.route_stop_ids) != len(existing_ids) or set(payload.route_stop_ids) != set(existing_ids):
        raise HTTPException(status_code=422, detail="Güzergâh durakları eksik veya fazla.")
    order = {route_stop_id: index for index, route_stop_id in enumerate(payload.route_stop_ids, start=1)}
    for item in route.stops:
        item.sequence = order[item.id]
    db.flush()
    _recalculate_route(db, route, context.crew)
    log_event(db, crew_id=context.crew.id, actor_id=context.user.id, action="route.reordered", details=str(route.id))
    db.commit()
    route = _load_route(db, route.id)
    assert route is not None
    return route_out(route)


@router.post("/routes/{route_id}/stops", response_model=RouteOut)
def add_stop_to_route(
    route_id: int,
    payload: RouteAddStopRequest,
    context: Context = Depends(require_dispatcher),
    db: Session = Depends(get_db),
):
    route = _load_route(db, route_id)
    if route is None or route.crew_id != context.crew.id:
        raise HTTPException(status_code=404, detail="Güzergâh bulunamadı.")
    if route.status != "draft":
        raise HTTPException(status_code=409, detail="Yalnızca taslak güzergâha menzil eklenebilir.")
    stop = db.get(Stop, payload.stop_id)
    if stop is None or stop.crew_id != context.crew.id or stop.scheduled_date != route.route_date:
        raise HTTPException(status_code=404, detail="Menzil bulunamadı.")
    if stop.status != "unassigned":
        raise HTTPException(status_code=409, detail="Bu menzil zaten bir güzergâhta.")
    route.stops.append(RouteStop(stop=stop, sequence=len(route.stops) + 1))
    stop.status = "assigned"
    db.flush()
    _recalculate_route(db, route, context.crew)
    log_event(db, crew_id=context.crew.id, actor_id=context.user.id, action="route.stop_added", details=stop.external_id)
    db.commit()
    route = _load_route(db, route.id)
    assert route is not None
    return route_out(route)


@router.delete("/routes/{route_id}/stops/{route_stop_id}", response_model=RouteOut)
def remove_stop_from_route(
    route_id: int,
    route_stop_id: int,
    context: Context = Depends(require_dispatcher),
    db: Session = Depends(get_db),
):
    route = _load_route(db, route_id)
    if route is None or route.crew_id != context.crew.id:
        raise HTTPException(status_code=404, detail="Güzergâh bulunamadı.")
    if route.status != "draft":
        raise HTTPException(status_code=409, detail="Yalnızca taslak güzergâhtan menzil çıkarılabilir.")
    item = next((candidate for candidate in route.stops if candidate.id == route_stop_id), None)
    if item is None:
        raise HTTPException(status_code=404, detail="Menzil bulunamadı.")
    item.stop.status = "unassigned"
    route.stops.remove(item)
    db.flush()
    _recalculate_route(db, route, context.crew)
    log_event(db, crew_id=context.crew.id, actor_id=context.user.id, action="route.stop_removed", details=item.stop.external_id)
    db.commit()
    route = _load_route(db, route.id)
    assert route is not None
    return route_out(route)


@router.post("/routes/{route_id}/delete", response_model=MessageResponse)
def delete_draft_route(
    route_id: int,
    context: Context = Depends(require_dispatcher),
    db: Session = Depends(get_db),
):
    route = _load_route(db, route_id)
    if route is None or route.crew_id != context.crew.id:
        raise HTTPException(status_code=404, detail="Güzergâh bulunamadı.")
    if route.status != "draft":
        raise HTTPException(status_code=409, detail="Yalnızca taslak güzergâh silinebilir.")
    for item in route.stops:
        item.stop.status = "unassigned"
    db.delete(route)
    log_event(db, crew_id=context.crew.id, actor_id=context.user.id, action="route.deleted", details=str(route_id))
    db.commit()
    return MessageResponse(message="Taslak güzergâh silindi.")


@router.get("/driver/route", response_model=RouteOut)
def driver_route(
    route_date: date | None = None,
    context: Context = Depends(require_driver),
    db: Session = Depends(get_db),
):
    target = route_date or date.today()
    route = db.scalars(
        _route_query()
        .where(
            Route.crew_id == context.crew.id,
            Route.driver_id == context.user.id,
            Route.route_date == target,
            Route.status.in_(["published", "completed"]),
        )
        .order_by(Route.published_at.desc())
    ).unique().first()
    if route is None:
        raise HTTPException(status_code=404, detail="Bu tarih için yola çıkarılmış güzergâh yok.")
    return route_out(route)


@router.patch("/driver/route-stops/{route_stop_id}", response_model=RouteStopOut)
def update_driver_stop(
    route_stop_id: int,
    payload: UpdateStopStatusRequest,
    context: Context = Depends(require_driver),
    db: Session = Depends(get_db),
):
    route_stop = db.scalars(
        select(RouteStop)
        .options(joinedload(RouteStop.stop), joinedload(RouteStop.route))
        .where(RouteStop.id == route_stop_id)
    ).first()
    if route_stop is None:
        raise HTTPException(status_code=404, detail="Menzil bulunamadı.")
    route = route_stop.route
    if route.crew_id != context.crew.id or route.driver_id != context.user.id:
        raise HTTPException(status_code=403, detail="Bu menzil size ait değil.")
    if route.status not in {"published", "completed"}:
        raise HTTPException(status_code=409, detail="Güzergâh henüz yola çıkarılmadı.")
    if payload.status == "failed" and not (payload.failure_reason or "").strip():
        raise HTTPException(status_code=422, detail="Teslim edilemedi nedeni zorunludur.")

    route_stop.status = payload.status
    if payload.status in {"delivered", "failed"}:
        route_stop.completed_at = datetime.now(timezone.utc)
        route_stop.stop.status = payload.status
    else:
        route_stop.completed_at = None
        route_stop.stop.status = "assigned"
    route_stop.failure_reason = (payload.failure_reason or "").strip()
    if payload.driver_note is not None:
        route_stop.driver_note = payload.driver_note.strip()

    all_terminal = all(item.status in {"delivered", "failed"} for item in route.stops)
    if all_terminal and route.status == "published":
        route.status = "completed"
    elif not all_terminal and route.status == "completed":
        route.status = "published"

    log_event(
        db,
        crew_id=context.crew.id,
        actor_id=context.user.id,
        action="stop.status_changed",
        details=f"{route_stop.stop.external_id}: {payload.status}",
    )
    db.commit()
    db.refresh(route_stop)
    return route_stop_out(route_stop)
