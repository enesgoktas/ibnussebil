import { useState } from "react";
import { api, ApiError } from "../api";
import { useAuth } from "../auth";
import type { Route, RouteStop, Stop } from "../types";
import { formatClock, formatDistance, formatDuration, statusLabel } from "../format";
import { useRouteGeometry } from "../useRouteGeometry";
import { Badge, Button, EmptyState, ErrorBanner, Field, Modal, SelectInput } from "./ui";
import { MapView, type MapLine, type MapPoint } from "./MapView";

const ROUTE_COLORS = ["#0f3d2e", "#2f5d8a", "#9a6b1f", "#7a3e65", "#3d6b4f", "#8a3f2f"];

export function routeColor(index: number): string {
  return ROUTE_COLORS[index % ROUTE_COLORS.length];
}

export function RoutesBoard({
  routes,
  selectedId,
  onSelect,
  onPublish,
  onUnpublish,
  onDelete,
  busyId,
  depot,
  unassignedStops = [],
  onRefresh,
}: {
  routes: Route[];
  selectedId: number | null;
  onSelect: (id: number) => void;
  onPublish: (id: number) => void;
  onUnpublish: (id: number) => void;
  onDelete: (id: number) => void;
  busyId: number | null;
  depot: { lat: number; lon: number; name: string } | null;
  unassignedStops?: Stop[];
  onRefresh?: () => void;
}) {
  const { token } = useAuth();
  const [editRouteId, setEditRouteId] = useState<number | null>(null);
  const [editOrder, setEditOrder] = useState<RouteStop[]>([]);
  const [editBusy, setEditBusy] = useState(false);
  const [editError, setEditError] = useState("");
  const [addStopId, setAddStopId] = useState("");
  const selected = routes.find((route) => route.id === selectedId) ?? routes[0] ?? null;
  const selectedIndex = selected ? routes.findIndex((route) => route.id === selected.id) : -1;
  const { geometry: roadGeometry, source: geometrySource, loading: geometryLoading } = useRouteGeometry(selected?.id ?? null);

  const editRoute = routes.find((route) => route.id === editRouteId) ?? null;

  function openReorder(route: Route) {
    setEditRouteId(route.id);
    setEditOrder([...route.stops]);
    setEditError("");
    setAddStopId("");
  }

  function moveEditStop(index: number, direction: -1 | 1) {
    const target = index + direction;
    if (target < 0 || target >= editOrder.length) return;
    setEditOrder((previous) => {
      const next = [...previous];
      [next[index], next[target]] = [next[target], next[index]];
      return next;
    });
  }

  async function saveOrder() {
    if (!token || !editRoute) return;
    setEditBusy(true);
    setEditError("");
    try {
      await api.reorderRoute(token, editRoute.id, editOrder.map((item) => item.id));
      setEditRouteId(null);
      onRefresh?.();
    } catch (err) {
      setEditError(err instanceof ApiError ? err.message : "Sıra kaydedilemedi.");
    } finally {
      setEditBusy(false);
    }
  }

  async function removeEditStop(item: RouteStop) {
    if (!token || !editRoute) return;
    setEditBusy(true);
    setEditError("");
    try {
      const updated = await api.removeStopFromRoute(token, editRoute.id, item.id);
      setEditOrder(updated.stops);
      onRefresh?.();
    } catch (err) {
      setEditError(err instanceof ApiError ? err.message : "Menzil çıkarılamadı.");
    } finally {
      setEditBusy(false);
    }
  }

  async function addEditStop() {
    if (!token || !editRoute || !addStopId) return;
    setEditBusy(true);
    setEditError("");
    try {
      const updated = await api.addStopToRoute(token, editRoute.id, Number(addStopId));
      setEditOrder(updated.stops);
      setAddStopId("");
      onRefresh?.();
    } catch (err) {
      setEditError(err instanceof ApiError ? err.message : "Menzil eklenemedi.");
    } finally {
      setEditBusy(false);
    }
  }

  if (!routes.length) {
    return (
      <EmptyState
        icon="⌁"
        title="Henüz güzergâh yok"
        body="Menzilleri irsal ettikten sonra sâikleri seçip 'Sevkiyatı Başlat' ile güzergâhları oluştur."
      />
    );
  }
  const points: MapPoint[] = [];
  const lines: MapLine[] = [];

  if (depot) {
    points.push({ lat: depot.lat, lon: depot.lon, label: "D", tone: "gold" });
  }
  if (selected) {
    const color = routeColor(selectedIndex);
    const fallbackPoints: Array<[number, number]> = [];
    if (depot) fallbackPoints.push([depot.lat, depot.lon]);
    selected.stops.forEach((item, index) => {
      points.push({
        lat: item.stop.lat,
        lon: item.stop.lon,
        label: String(index + 1),
        tone: item.status === "delivered" ? "green" : item.status === "failed" ? "red" : "blue",
      });
      fallbackPoints.push([item.stop.lat, item.stop.lon]);
    });
    if (depot && fallbackPoints.length) fallbackPoints.push([depot.lat, depot.lon]);
    const routePoints =
      roadGeometry && roadGeometry.length > 1 ? roadGeometry : fallbackPoints;
    lines.push({ points: routePoints, color });
  }

  return (
    <div className="routes-board">
      <div className="route-list">
        {routes.map((route, index) => {
          const color = routeColor(index);
          const isSelected = route.id === selected?.id;
          return (
            <article
              key={route.id}
              className={`route-card ${isSelected ? "selected" : ""}`}
              onClick={() => onSelect(route.id)}
            >
              <div className="route-card-head">
                <div className="route-driver">
                  <span className="route-color" style={{ background: color }} />
                  <div>
                    <strong>{route.driver_name}</strong>
                    <small>
                      {route.stop_count} menzil · {formatDistance(route.total_distance_m)} ·{" "}
                      {formatDuration(route.total_duration_s)}
                    </small>
                  </div>
                </div>
                <Badge tone={route.status}>{statusLabel(route.status)}</Badge>
              </div>
              <div className="progress">
                <span style={{ width: `${route.stop_count ? (route.completed_count / route.stop_count) * 100 : 0}%` }} />
              </div>
              <div className="route-card-foot">
                <small>
                  {route.completed_count}/{route.stop_count} tamamlandı
                </small>
                <div className="route-actions" onClick={(event) => event.stopPropagation()}>
                  {route.status === "draft" ? (
                    <>
                      <Button variant="secondary" onClick={() => openReorder(route)}>
                        Sırala
                      </Button>
                      <Button
                        variant="primary"
                        loading={busyId === route.id}
                        onClick={() => onPublish(route.id)}
                      >
                        Yola Çıkar
                      </Button>
                      <Button variant="ghost" onClick={() => onDelete(route.id)}>
                        Sil
                      </Button>
                    </>
                  ) : null}
                  {route.status === "published" ? (
                    <Button variant="ghost" onClick={() => onUnpublish(route.id)}>
                      Taslağa Al
                    </Button>
                  ) : null}
                </div>
              </div>
              <details className="route-stops" onClick={(event) => event.stopPropagation()}>
                <summary>Menzilleri gör</summary>
                <ol>
                  {route.stops.map((item) => (
                    <li key={item.id}>
                      <span className={`stop-dot ${item.status}`} />
                      <span className="route-stop-seq">{item.sequence}</span>
                      <span>
                        <strong>{item.stop.recipient_name || item.stop.external_id}</strong>
                        <small>{item.stop.address}</small>
                      </span>
                      <span className="route-stop-time">{formatClock(item.planned_arrival_min)}</span>
                    </li>
                  ))}
                </ol>
              </details>
            </article>
          );
        })}
      </div>
      <div className="route-map-panel">
        <MapView points={points} lines={lines} height={430} />
        {selected ? (
          <div className="map-caption">
            <span className="route-color" style={{ background: routeColor(selectedIndex) }} />
            <strong>{selected.driver_name}</strong>
            <span>
              {selected.stop_count} menzil · {formatDistance(selected.total_distance_m)} ·{" "}
              {formatDuration(selected.total_duration_s)}
            </span>
            <span className={`map-source ${geometrySource === "osrm" ? "road" : ""}`}>
              {geometryLoading ? "Yol güzergâhı..." : geometrySource === "osrm" ? "Yol güzergâhı" : "Düz çizgi"}
            </span>
          </div>
        ) : null}
      </div>

      <Modal
        open={Boolean(editRoute)}
        title={`${editRoute?.driver_name ?? ""} sırasını düzenle`}
        onClose={() => setEditRouteId(null)}
        wide
        footer={
          <>
            <Button variant="ghost" onClick={() => setEditRouteId(null)}>
              Vazgeç
            </Button>
            <Button variant="primary" loading={editBusy} onClick={() => void saveOrder()}>
              Sırayı Kaydet
            </Button>
          </>
        }
      >
        {editError ? <ErrorBanner message={editError} onClose={() => setEditError("")} /> : null}
        <div className="reorder-list">
          {editOrder.map((item, index) => (
            <div className="reorder-row" key={item.id}>
              <span className="sequence">{index + 1}</span>
              <div className="reorder-main">
                <strong>{item.stop.recipient_name || item.stop.external_id}</strong>
                <small>{item.stop.address}</small>
                <span className="stop-meta">
                  {item.stop.time_window_start_min !== null && item.stop.time_window_end_min !== null
                    ? `${formatClock(item.stop.time_window_start_min)}–${formatClock(item.stop.time_window_end_min)}`
                    : "Zaman penceresi yok"}
                  {item.stop.weight_kg ? ` · ${item.stop.weight_kg} kg` : ""}
                </span>
              </div>
              <div className="reorder-actions">
                <button className="icon-btn" disabled={index === 0 || editBusy} onClick={() => moveEditStop(index, -1)} aria-label="Yukarı taşı">
                  ↑
                </button>
                <button
                  className="icon-btn"
                  disabled={index === editOrder.length - 1 || editBusy}
                  onClick={() => moveEditStop(index, 1)}
                  aria-label="Aşağı taşı"
                >
                  ↓
                </button>
                <button className="icon-btn danger" disabled={editBusy} onClick={() => void removeEditStop(item)} aria-label="Güzergâhtan çıkar">
                  ×
                </button>
              </div>
            </div>
          ))}
        </div>

        {unassignedStops.length ? (
          <div className="reorder-add">
            <Field label="Sevkiyat bekleyen menzil ekle" htmlFor="add-stop" hint="Menzil, sıranın sonuna eklenir">
              <SelectInput id="add-stop" value={addStopId} onChange={(event) => setAddStopId(event.target.value)}>
                <option value="">Menzil seç</option>
                {unassignedStops.map((stop) => (
                  <option key={stop.id} value={stop.id}>
                    {stop.external_id} — {stop.recipient_name || stop.address}
                  </option>
                ))}
              </SelectInput>
            </Field>
            <Button variant="secondary" disabled={!addStopId || editBusy} onClick={() => void addEditStop()}>
              Ekle
            </Button>
          </div>
        ) : null}
      </Modal>
    </div>
  );
}
