import { useCallback, useEffect, useMemo, useState } from "react";
import { api, ApiError } from "../api";
import { useAuth } from "../auth";
import { MapView, type MapLine, type MapPoint } from "../components/MapView";
import { useRouteGeometry } from "../useRouteGeometry";
import {
  Badge,
  Button,
  EmptyState,
  ErrorBanner,
  Field,
  Modal,
  PageHeader,
  SelectInput,
  Spinner,
  StatCard,
  TextInput,
} from "../components/ui";
import { formatClock, formatDistance, formatDuration, formatDate, statusLabel, todayISO } from "../format";
import type { Route, RouteStop } from "../types";

const FAILURE_REASONS = [
  "Müşteri adreste yok",
  "Adres bulunamadı",
  "Teslim alınmadı",
  "Telefonla ulaşılamadı",
  "Diğer",
];

export function DriverRoutePage() {
  const { token, me } = useAuth();
  const [date, setDate] = useState(todayISO());
  const [route, setRoute] = useState<Route | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [busyStopId, setBusyStopId] = useState<number | null>(null);
  const [failureStop, setFailureStop] = useState<RouteStop | null>(null);
  const [failureReason, setFailureReason] = useState(FAILURE_REASONS[0]);
  const [failureNote, setFailureNote] = useState("");

  const load = useCallback(async () => {
    if (!token) return;
    setLoading(true);
    setError("");
    try {
      setRoute(await api.driverRoute(token, date));
    } catch (err) {
      if (err instanceof ApiError && err.status === 404) {
        setRoute(null);
      } else {
        setError(err instanceof ApiError ? err.message : "Sefer getirilemedi.");
      }
    } finally {
      setLoading(false);
    }
  }, [token, date]);

  useEffect(() => {
    void load();
  }, [load]);

  async function setStatus(item: RouteStop, status: "delivered" | "failed" | "pending") {
    if (!token) return;
    setBusyStopId(item.id);
    setError("");
    try {
      await api.updateDriverStop(token, item.id, {
        status,
        failure_reason: status === "failed" ? failureReason : undefined,
        driver_note: status === "failed" ? failureNote : undefined,
      });
      setNotice(
        status === "delivered"
          ? "Menzil teslim edildi."
          : status === "failed"
            ? "Menzil teslim edilemedi olarak işaretlendi."
            : "Menzil yeniden açıldı."
      );
      setFailureStop(null);
      setFailureNote("");
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Durum güncellenemedi.");
    } finally {
      setBusyStopId(null);
    }
  }

  const points = useMemo<MapPoint[]>(() => {
    if (!route) return [];
    return route.stops.map((item, index) => ({
      lat: item.stop.lat,
      lon: item.stop.lon,
      label: String(index + 1),
      tone:
        item.status === "delivered" ? "green" : item.status === "failed" ? "red" : "blue",
    }));
  }, [route]);

  const { geometry: roadGeometry, source: geometrySource, loading: geometryLoading } = useRouteGeometry(route?.id ?? null);

  const lines = useMemo<MapLine[]>(() => {
    if (!route) return [];
    if (roadGeometry && roadGeometry.length > 1) {
      return [{ points: roadGeometry, color: "#0f3d2e" }];
    }
    const coords: Array<[number, number]> = [];
    if (me?.crew) coords.push([me.crew.depot_lat, me.crew.depot_lon]);
    route.stops.forEach((item) => coords.push([item.stop.lat, item.stop.lon]));
    if (me?.crew && coords.length) coords.push([me.crew.depot_lat, me.crew.depot_lon]);
    return [{ points: coords, color: "#0f3d2e" }];
  }, [route, me?.crew, roadGeometry]);

  if (loading) return <div className="page"><Spinner label="Sefer getiriliyor" /></div>;

  return (
    <div className="page">
      <PageHeader
        eyebrow="Seferim"
        title={route ? route.driver_name : "Bugünün seferi"}
        description={
          route
            ? `${formatDate(route.route_date)} · ${route.stop_count} menzil · ${formatDistance(
                route.total_distance_m
              )}`
            : "Yola çıkarılmış güzergâhın burada görünür."
        }
        actions={
          <input
            className="input date-input"
            type="date"
            value={date}
            onChange={(event) => setDate(event.target.value)}
          />
        }
      />
      {error ? <ErrorBanner message={error} onClose={() => setError("")} /> : null}
      {notice ? (
        <div className="notice-banner">
          <span>{notice}</span>
          <button onClick={() => setNotice("")}>×</button>
        </div>
      ) : null}

      {!route ? (
        <EmptyState
          icon="⌁"
          title="Bu tarih için sefer yok"
          body="Kervanbaşın güzergâhı yola çıkardığında menzillerin burada görünecek."
        />
      ) : (
        <>
          <div className="stats-grid">
            <StatCard label="Menzil" value={route.stop_count} hint={formatDate(route.route_date)} />
            <StatCard
              label="Tamamlanan"
              value={`${route.completed_count}/${route.stop_count}`}
              tone="green"
            />
            <StatCard label="Mesafe" value={formatDistance(route.total_distance_m)} tone="blue" />
            <StatCard label="Tahmini süre" value={formatDuration(route.total_duration_s)} tone="gold" />
          </div>

          {route.status === "completed" ? (
            <div className="complete-banner">
              <strong>Sefer tamamlandı.</strong>
              <span>Tüm menziller işlendi. Eline sağlık.</span>
            </div>
          ) : null}

          <div className="driver-grid">
            <section className="panel route-map-panel">
              <div className="panel-head">
                <div>
                  <span className="eyebrow">Güzergâh</span>
                  <h2>Bugünkü seferin</h2>
                </div>
                <div className="badge-row">
                  <Badge tone={route.status}>{statusLabel(route.status)}</Badge>
                  <span className={`map-source ${geometrySource === "osrm" ? "road" : ""}`}>
                    {geometryLoading ? "Yol güzergâhı..." : geometrySource === "osrm" ? "Yol güzergâhı" : "Düz çizgi"}
                  </span>
                </div>
              </div>
              <MapView points={points} lines={lines} height={380} />
              <div className="progress progress-large">
                <span
                  style={{
                    width: `${route.stop_count ? (route.completed_count / route.stop_count) * 100 : 0}%`,
                  }}
                />
              </div>
            </section>

            <section className="panel">
              <div className="panel-head">
                <div>
                  <span className="eyebrow">Menziller</span>
                  <h2>Menziller</h2>
                </div>
                <span className="panel-note">Sırayla ilerle</span>
              </div>
              <div className="driver-stops">
                {route.stops.map((item, index) => {
                  const mapUrl = `https://www.google.com/maps/dir/?api=1&destination=${item.stop.lat},${item.stop.lon}`;
                  return (
                    <article className={`driver-stop ${item.status}`} key={item.id}>
                      <div className="driver-stop-head">
                        <span className={`sequence ${item.status}`}>{index + 1}</span>
                        <div className="driver-stop-main">
                          <strong>{item.stop.recipient_name || item.stop.external_id}</strong>
                          <small>{item.stop.address}</small>
                          <span className="stop-meta">
                            {item.planned_arrival_min !== null
                              ? `Tahmini varış ${formatClock(item.planned_arrival_min)}`
                              : "Varış saati yok"}
                            {item.stop.time_window_start_min !== null &&
                            item.stop.time_window_end_min !== null
                              ? ` · Pencere ${formatClock(item.stop.time_window_start_min)}–${formatClock(
                                  item.stop.time_window_end_min
                                )}`
                              : ""}
                            {item.stop.weight_kg ? ` · ${item.stop.weight_kg} kg` : ""}
                          </span>
                          {item.stop.notes ? <span className="stop-note">{item.stop.notes}</span> : null}
                          {item.failure_reason ? (
                            <span className="failure-note">Neden: {item.failure_reason}</span>
                          ) : null}
                        </div>
                        <Badge tone={item.status}>{statusLabel(item.status)}</Badge>
                      </div>
                      <div className="driver-stop-actions">
                        <a className="btn btn-secondary" href={mapUrl} target="_blank" rel="noreferrer">
                          Yol tarifi
                        </a>
                        {item.stop.phone ? (
                          <a className="btn btn-ghost" href={`tel:${item.stop.phone}`}>
                            Ara
                          </a>
                        ) : null}
                        {item.status === "pending" ? (
                          <>
                            <Button
                              variant="primary"
                              loading={busyStopId === item.id}
                              onClick={() => void setStatus(item, "delivered")}
                            >
                              Teslim edildi
                            </Button>
                            <Button
                              variant="danger"
                              onClick={() => {
                                setFailureStop(item);
                                setFailureReason(FAILURE_REASONS[0]);
                                setFailureNote("");
                              }}
                            >
                              Teslim edilemedi
                            </Button>
                          </>
                        ) : (
                          <Button
                            variant="ghost"
                            loading={busyStopId === item.id}
                            onClick={() => void setStatus(item, "pending")}
                          >
                            Düzelt
                          </Button>
                        )}
                      </div>
                    </article>
                  );
                })}
              </div>
            </section>
          </div>
        </>
      )}

      <Modal
        open={Boolean(failureStop)}
        title="Teslim edilemedi"
        onClose={() => setFailureStop(null)}
        footer={
          <>
            <Button variant="ghost" onClick={() => setFailureStop(null)}>
              Vazgeç
            </Button>
            <Button
              variant="danger"
              loading={busyStopId === failureStop?.id}
              onClick={() => failureStop && void setStatus(failureStop, "failed")}
            >
              Kaydet
            </Button>
          </>
        }
      >
        <div className="stack-form">
          <Field label="Neden" htmlFor="failure-reason">
            <SelectInput
              id="failure-reason"
              value={failureReason}
              onChange={(event) => setFailureReason(event.target.value)}
            >
              {FAILURE_REASONS.map((reason) => (
                <option key={reason} value={reason}>
                  {reason}
                </option>
              ))}
            </SelectInput>
          </Field>
          <Field label="Not" htmlFor="failure-note" hint="İsteğe bağlı">
            <TextInput
              id="failure-note"
              value={failureNote}
              onChange={(event) => setFailureNote(event.target.value)}
              placeholder="Örn. 14:30'da tekrar denenecek"
            />
          </Field>
        </div>
      </Modal>
    </div>
  );
}
