from __future__ import annotations

from app.models import Crew, Membership, Route, RouteStop, Stop, User
from app.schemas import (
    CrewOut,
    CrewWithCode,
    MembershipOut,
    RouteOut,
    RouteStopOut,
    StopOut,
    UserOut,
)


def user_out(user: User) -> UserOut:
    return UserOut(id=user.id, full_name=user.full_name, phone=user.phone)


def crew_out(crew: Crew) -> CrewOut:
    return CrewOut.model_validate(crew)


def crew_with_code_out(crew: Crew) -> CrewWithCode:
    return CrewWithCode.model_validate(crew)


def membership_out(membership: Membership) -> MembershipOut:
    return MembershipOut(
        id=membership.id,
        role=membership.role,
        status=membership.status,
        user=user_out(membership.user),
    )


def stop_out(stop: Stop) -> StopOut:
    return StopOut.model_validate(stop)


def route_stop_out(route_stop: RouteStop) -> RouteStopOut:
    return RouteStopOut(
        id=route_stop.id,
        sequence=route_stop.sequence,
        planned_arrival_min=route_stop.planned_arrival_min,
        status=route_stop.status,
        failure_reason=route_stop.failure_reason,
        driver_note=route_stop.driver_note,
        stop=stop_out(route_stop.stop),
    )


def route_out(route: Route) -> RouteOut:
    stops = [route_stop_out(item) for item in sorted(route.stops, key=lambda item: item.sequence)]
    completed = sum(1 for item in stops if item.status in {"delivered", "failed"})
    return RouteOut(
        id=route.id,
        driver_id=route.driver_id,
        driver_name=route.driver.full_name if route.driver else "",
        route_date=route.route_date,
        status=route.status,
        total_distance_m=route.total_distance_m,
        total_duration_s=route.total_duration_s,
        published_at=route.published_at,
        stop_count=len(stops),
        completed_count=completed,
        stops=stops,
    )
