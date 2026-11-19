import { useCallback, useEffect, useState } from "react";
import { api, ApiError } from "../api";
import { useAuth } from "../auth";
import { RoutesBoard } from "../components/RoutesBoard";
import { ErrorBanner, PageHeader, Spinner, StatCard } from "../components/ui";
import { formatDate, todayISO } from "../format";
import type { Route, Stop } from "../types";

export function DispatcherRoutesPage() {
  const { token, me } = useAuth();
  const [date, setDate] = useState(todayISO());
  const [routes, setRoutes] = useState<Route[]>([]);
  const [stops, setStops] = useState<Stop[]>([]);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);
  const [busyId, setBusyId] = useState<number | null>(null);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  const load = useCallback(async () => {
    if (!token) return;
    setLoading(true);
    try {
      const [next, nextStops] = await Promise.all([api.listRoutes(token, date), api.listStops(token, date)]);
      setRoutes(next);
      setStops(nextStops);
      setSelectedId((previous) =>
        previous && next.some((route) => route.id === previous) ? previous : next[0]?.id ?? null
      );
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Seferler getirilemedi.");
    } finally {
      setLoading(false);
    }
  }, [token, date]);

  useEffect(() => {
    void load();
  }, [load]);

  async function action(kind: "publish" | "unpublish" | "delete", routeId: number) {
    if (!token) return;
    if (kind === "delete" && !window.confirm("Taslak güzergâh silinsin mi?")) return;
    setBusyId(routeId);
    setError("");
    try {
      if (kind === "publish") {
        await api.publishRoute(token, routeId);
        setNotice("Güzergâh yola çıkarıldı.");
      } else if (kind === "unpublish") {
        await api.unpublishRoute(token, routeId);
        setNotice("Güzergâh taslağa alındı.");
      } else {
        await api.deleteRoute(token, routeId);
        setNotice("Taslak güzergâh silindi.");
      }
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "İşlem tamamlanamadı.");
    } finally {
      setBusyId(null);
    }
  }

  const published = routes.filter((route) => route.status === "published").length;
  const completed = routes.filter((route) => route.status === "completed").length;
  const totalStops = routes.reduce((sum, route) => sum + route.stop_count, 0);
  const totalDone = routes.reduce((sum, route) => sum + route.completed_count, 0);

  return (
    <div className="page">
      <PageHeader
        eyebrow="Seferler"
        title="Tüm güzergâhlar"
        description="Taslakları yola çıkar, sâiklerin ilerlemesini izle."
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

      <div className="stats-grid">
        <StatCard label="Güzergâh" value={routes.length} hint={formatDate(date)} />
        <StatCard label="Yolda" value={published} tone="blue" />
        <StatCard label="Tamamlanan" value={completed} tone="green" />
        <StatCard label="Menzil" value={`${totalDone}/${totalStops}`} tone="gold" hint="Tamamlanan / toplam" />
      </div>

      <section className="panel routes-panel">
        {loading ? (
          <Spinner />
        ) : (
          <RoutesBoard
            routes={routes}
            selectedId={selectedId}
            onSelect={setSelectedId}
            onPublish={(id) => void action("publish", id)}
            onUnpublish={(id) => void action("unpublish", id)}
            onDelete={(id) => void action("delete", id)}
            busyId={busyId}
            depot={{
              lat: me?.crew?.depot_lat ?? 41.0082,
              lon: me?.crew?.depot_lon ?? 28.9784,
              name: me?.crew?.depot_name ?? "Depo",
            }}
            unassignedStops={stops.filter((stop) => stop.status === "unassigned")}
            onRefresh={() => void load()}
          />
        )}
      </section>
    </div>
  );
}
