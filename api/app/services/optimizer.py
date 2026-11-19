from __future__ import annotations

from dataclasses import dataclass, field

from ortools.constraint_solver import pywrapcp, routing_enums_pb2

from app.config import settings
from app.services.routing import build_matrix


@dataclass(frozen=True)
class OptStop:
    id: int
    lat: float
    lon: float
    time_window_start_min: int | None = None
    time_window_end_min: int | None = None


@dataclass(frozen=True)
class OptDriver:
    id: int
    max_stops: int


@dataclass
class OptRoute:
    driver_id: int
    stops: list[tuple[int, int | None]] = field(default_factory=list)
    distance_m: int = 0
    duration_s: int = 0


@dataclass
class OptResult:
    routes: list[OptRoute]
    unassigned_stop_ids: list[int]
    total_distance_m: int
    total_duration_s: int
    solver_status: str
    matrix_source: str


class OptimizationError(RuntimeError):
    pass


def optimize(
    *,
    depot_lat: float,
    depot_lon: float,
    stops: list[OptStop],
    drivers: list[OptDriver],
    shift_start_min: int,
    shift_end_min: int,
    service_minutes: int,
    time_limit_seconds: int | None = None,
) -> OptResult:
    if not stops:
        raise OptimizationError("Sevkiyat bekleyen menzil yok.")
    if not drivers:
        raise OptimizationError("Seçili sâik yok.")

    points: list[tuple[float, float]] = [(depot_lat, depot_lon)]
    points.extend((stop.lat, stop.lon) for stop in stops)
    distances, durations, matrix_source = build_matrix(points)

    manager = pywrapcp.RoutingIndexManager(len(points), len(drivers), 0)
    routing = pywrapcp.RoutingModel(manager)

    def distance_callback(from_index: int, to_index: int) -> int:
        from_node = manager.IndexToNode(from_index)
        to_node = manager.IndexToNode(to_index)
        return distances[from_node][to_node]

    distance_callback_index = routing.RegisterTransitCallback(distance_callback)
    routing.AddDimension(distance_callback_index, 0, 50_000_000, True, "Distance")
    distance_dimension = routing.GetDimensionOrDie("Distance")
    distance_dimension.SetGlobalSpanCostCoefficient(20)

    def duration_callback(from_index: int, to_index: int) -> int:
        from_node = manager.IndexToNode(from_index)
        to_node = manager.IndexToNode(to_index)
        service = service_minutes * 60 if to_node != 0 else 0
        return durations[from_node][to_node] + service

    duration_callback_index = routing.RegisterTransitCallback(duration_callback)
    routing.SetArcCostEvaluatorOfAllVehicles(duration_callback_index)

    horizon = max(24 * 60 * 60, (shift_end_min - shift_start_min) * 60 + 6 * 3600)
    routing.AddDimension(
        duration_callback_index,
        60 * 60,  # waiting is allowed
        horizon,
        False,
        "Time",
    )
    time_dimension = routing.GetDimensionOrDie("Time")
    time_dimension.SetGlobalSpanCostCoefficient(100)
    for vehicle_index in range(len(drivers)):
        start_index = routing.Start(vehicle_index)
        end_index = routing.End(vehicle_index)
        time_dimension.CumulVar(start_index).SetRange(
            shift_start_min * 60, shift_start_min * 60
        )
        time_dimension.CumulVar(end_index).SetRange(
            shift_start_min * 60, shift_end_min * 60
        )

    for position, stop in enumerate(stops, start=1):
        index = manager.NodeToIndex(position)
        if stop.time_window_start_min is not None and stop.time_window_end_min is not None:
            time_dimension.CumulVar(index).SetRange(
                stop.time_window_start_min * 60, stop.time_window_end_min * 60
            )

    def stop_count_callback(from_index: int) -> int:
        node = manager.IndexToNode(from_index)
        return 0 if node == 0 else 1

    stop_count_callback_index = routing.RegisterUnaryTransitCallback(stop_count_callback)
    routing.AddDimensionWithVehicleCapacity(
        stop_count_callback_index,
        0,
        [max(1, driver.max_stops) for driver in drivers],
        True,
        "Stops",
    )

    # Prefer serving every stop; allow dropping only when constraints make it
    # impossible. The dispatcher sees the unassigned list after the solve.
    drop_penalty = 50_000_000
    for position in range(1, len(points)):
        routing.AddDisjunction([manager.NodeToIndex(position)], drop_penalty)

    search = pywrapcp.DefaultRoutingSearchParameters()
    search.first_solution_strategy = routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
    search.local_search_metaheuristic = (
        routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
    )
    search.time_limit.FromSeconds(
        time_limit_seconds or settings.OPTIMIZER_TIME_LIMIT_SECONDS
    )
    search.log_search = False

    solution = routing.SolveWithParameters(search)
    if solution is None:
        raise OptimizationError(
            "Uygun bir güzergâh bulunamadı. Sâik sayısını, vardiya saatlerini "
            "veya menzil limitlerini artırın."
        )

    result_routes: list[OptRoute] = []
    assigned: set[int] = set()
    total_distance = 0
    total_duration = 0

    for vehicle_index, driver in enumerate(drivers):
        index = routing.Start(vehicle_index)
        node_sequence: list[int] = []
        while not routing.IsEnd(index):
            node = manager.IndexToNode(index)
            if node != 0:
                node_sequence.append(node)
            index = solution.Value(routing.NextVar(index))

        if not node_sequence:
            continue

        route = OptRoute(driver_id=driver.id)
        current_time = shift_start_min * 60
        previous_node = 0
        distance_m = 0
        for node in node_sequence:
            stop = stops[node - 1]
            travel_s = durations[previous_node][node]
            distance_m += distances[previous_node][node]
            arrival = current_time + travel_s
            if stop.time_window_start_min is not None:
                arrival = max(arrival, stop.time_window_start_min * 60)
            route.stops.append((stop.id, arrival))
            assigned.add(stop.id)
            current_time = arrival + service_minutes * 60
            previous_node = node

        return_travel = durations[previous_node][0]
        distance_m += distances[previous_node][0]
        current_time += return_travel
        route.distance_m = int(distance_m)
        route.duration_s = int(current_time - shift_start_min * 60)
        result_routes.append(route)
        total_distance += route.distance_m
        total_duration += route.duration_s

    unassigned = [stop.id for stop in stops if stop.id not in assigned]
    return OptResult(
        routes=result_routes,
        unassigned_stop_ids=unassigned,
        total_distance_m=total_distance,
        total_duration_s=total_duration,
        solver_status=str(routing.status()),
        matrix_source=matrix_source,
    )
