import { useCallback, useEffect, useMemo, useState, type FormEvent } from "react";
import { Link } from "react-router-dom";
import { api, ApiError, saveBlob } from "../api";
import { useAuth } from "../auth";
import { RoutesBoard } from "../components/RoutesBoard";
import {
  Badge,
  Button,
  EmptyState,
  ErrorBanner,
  Field,
  Modal,
  PageHeader,
  Spinner,
  StatCard,
  TextInput,
} from "../components/ui";
import { formatClock, formatDate, statusLabel, timeToMinutes, todayISO } from "../format";
import type { ImportPreview, Member, Route, Stop } from "../types";

export function DispatcherSevkPage() {
  const { token, me } = useAuth();
  const [date, setDate] = useState(todayISO());
  const [stops, setStops] = useState<Stop[]>([]);
  const [routes, setRoutes] = useState<Route[]>([]);
  const [members, setMembers] = useState<Member[]>([]);
  const [selectedDrivers, setSelectedDrivers] = useState<number[]>([]);
  const [selectedRouteId, setSelectedRouteId] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [busyRouteId, setBusyRouteId] = useState<number | null>(null);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [importOpen, setImportOpen] = useState(false);
  const [importFile, setImportFile] = useState<File | null>(null);
  const [importDate, setImportDate] = useState(date);
  const [importPreview, setImportPreview] = useState<ImportPreview | null>(null);
  const [importBusy, setImportBusy] = useState(false);
  const [commitBusy, setCommitBusy] = useState(false);
  const [manualOpen, setManualOpen] = useState(false);
  const [manualBusy, setManualBusy] = useState(false);
  const [manualError, setManualError] = useState("");
  const [manualForm, setManualForm] = useState({
    external_id: "",
    recipient_name: "",
    phone: "",
    address: "",
    start: "",
    end: "",
    weight: "",
    notes: "",
    lat: "",
    lon: "",
  });

  const load = useCallback(async () => {
    if (!token) return;
    setLoading(true);
    setError("");
    try {
      const [nextStops, nextRoutes, nextMembers] = await Promise.all([
        api.listStops(token, date),
        api.listRoutes(token, date),
        api.listMembers(token),
      ]);
      const rank: Record<string, number> = { unassigned: 0, assigned: 1, delivered: 2, failed: 3 };
      nextStops.sort(
        (a, b) => (rank[a.status] ?? 9) - (rank[b.status] ?? 9) || a.external_id.localeCompare(b.external_id)
      );
      setStops(nextStops);
      setRoutes(nextRoutes);
      setMembers(nextMembers);
      const driverIds = nextMembers.filter((item) => item.role === "driver").map((item) => item.id);
      setSelectedDrivers((previous) => {
        const kept = previous.filter((id) => driverIds.includes(id));
        return kept.length ? kept : driverIds;
      });
      setSelectedRouteId((previous) => {
        if (previous && nextRoutes.some((route) => route.id === previous)) return previous;
        return nextRoutes[0]?.id ?? null;
      });
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Veriler getirilemedi.");
    } finally {
      setLoading(false);
    }
  }, [token, date]);

  useEffect(() => {
    void load();
  }, [load]);

  const drivers = useMemo(() => members.filter((item) => item.role === "driver"), [members]);
  const unassigned = stops.filter((stop) => stop.status === "unassigned");
  const delivered = stops.filter((stop) => stop.status === "delivered").length;
  const failed = stops.filter((stop) => stop.status === "failed").length;

  function toggleDriver(id: number) {
    setSelectedDrivers((previous) =>
      previous.includes(id) ? previous.filter((value) => value !== id) : [...previous, id]
    );
  }

  async function optimize() {
    if (!token) return;
    if (!selectedDrivers.length) {
      setError("En az bir sâik seçin.");
      return;
    }
    setBusy(true);
    setError("");
    setNotice("");
    try {
      const result = await api.optimize(token, date, selectedDrivers);
      await load();
      setSelectedRouteId(result.routes[0]?.id ?? null);
      setNotice(
        `${result.routes.length} güzergâh oluşturuldu. ${
          result.unassigned_stop_ids.length
            ? `${result.unassigned_stop_ids.length} menzil kapasite/varış penceresi nedeniyle sevkiyata giremedi.`
            : "Tüm menziller sevkiyata girdi."
        }`
      );
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Sevkiyat tamamlanamadı.");
    } finally {
      setBusy(false);
    }
  }

  async function publish(routeId: number) {
    if (!token) return;
    setBusyRouteId(routeId);
    setError("");
    try {
      await api.publishRoute(token, routeId);
      await load();
      setNotice("Güzergâh yola çıkarıldı. Sâik artık seferini görebilir.");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Güzergâh yola çıkarılamadı.");
    } finally {
      setBusyRouteId(null);
    }
  }

  async function unpublish(routeId: number) {
    if (!token) return;
    setBusyRouteId(routeId);
    setError("");
    try {
      await api.unpublishRoute(token, routeId);
      await load();
      setNotice("Güzergâh taslağa alındı.");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Güzergâh geri alınamadı.");
    } finally {
      setBusyRouteId(null);
    }
  }

  async function removeRoute(routeId: number) {
    if (!token || !window.confirm("Taslak güzergâh silinsin mi?")) return;
    setBusyRouteId(routeId);
    try {
      await api.deleteRoute(token, routeId);
      await load();
      setNotice("Taslak güzergâh silindi.");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Güzergâh silinemedi.");
    } finally {
      setBusyRouteId(null);
    }
  }

  async function downloadTemplate() {
    if (!token) return;
    try {
      saveBlob(await api.downloadTemplate(token), "ibnussebil-sablon.xlsx");
    } catch {
      setError("Nümune indirilemedi.");
    }
  }

  async function previewImport() {
    if (!token || !importFile) return;
    setImportBusy(true);
    setError("");
    try {
      setImportPreview(await api.previewImport(token, importFile, importDate));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Dosya okunamadı.");
    } finally {
      setImportBusy(false);
    }
  }

  async function commitImport() {
    if (!token || !importPreview) return;
    setCommitBusy(true);
    try {
      const result = await api.commitImport(token, importPreview.import_id);
      setImportOpen(false);
      setImportPreview(null);
      setImportFile(null);
      setNotice(`${result.created_count} menzil irsal edildi.`);
      if (importDate !== date) setDate(importDate);
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Menziller irsal edilemedi.");
    } finally {
      setCommitBusy(false);
    }
  }

  async function downloadErrors() {
    if (!token || !importPreview) return;
    try {
      saveBlob(
        await api.downloadImportErrors(token, importPreview.import_id),
        `ibnussebil-hatalar-${importPreview.import_id}.csv`
      );
    } catch {
      setError("Hata dosyası indirilemedi.");
    }
  }

  function updateManual(key: keyof typeof manualForm, value: string) {
    setManualForm((previous) => ({ ...previous, [key]: value }));
  }

  async function createManualStop(event?: FormEvent) {
    event?.preventDefault();
    if (!token) return;
    setManualBusy(true);
    setManualError("");
    try {
      const created = await api.createStop(token, {
        external_id: manualForm.external_id.trim() || undefined,
        recipient_name: manualForm.recipient_name.trim(),
        phone: manualForm.phone.trim(),
        address: manualForm.address.trim(),
        lat: manualForm.lat.trim() ? Number(manualForm.lat) : null,
        lon: manualForm.lon.trim() ? Number(manualForm.lon) : null,
        scheduled_date: date,
        time_window_start_min: manualForm.start ? timeToMinutes(manualForm.start) : null,
        time_window_end_min: manualForm.end ? timeToMinutes(manualForm.end) : null,
        weight_kg: manualForm.weight.trim() ? Number(manualForm.weight) : null,
        notes: manualForm.notes.trim(),
      });
      setManualOpen(false);
      setManualForm({
        external_id: "",
        recipient_name: "",
        phone: "",
        address: "",
        start: "",
        end: "",
        weight: "",
        notes: "",
        lat: "",
        lon: "",
      });
      setNotice(`${created.external_id} menzili eklendi.`);
      await load();
    } catch (err) {
      setManualError(err instanceof ApiError ? err.message : "Menzil eklenemedi.");
    } finally {
      setManualBusy(false);
    }
  }

  return (
    <div className="page">
      <PageHeader
        eyebrow="Sevkiyat Divanı"
        title="Günün Sevkiyatı"
        description="Menzilleri irsal eyle, sâikleri seç ve güzergâhları tek tıkla oluştur."
        actions={
          <>
            <input
              className="input date-input"
              type="date"
              value={date}
              onChange={(event) => {
                setDate(event.target.value);
                setImportDate(event.target.value);
              }}
            />
            <Button variant="secondary" onClick={() => void downloadTemplate()}>
              Nümune İndir
            </Button>
            <Button
              variant="secondary"
              onClick={() => {
                setManualOpen(true);
                setManualError("");
              }}
            >
              Menzil Ekle
            </Button>
            <Button
              variant="gold"
              onClick={() => {
                setImportOpen(true);
                setImportDate(date);
                setImportPreview(null);
                setImportFile(null);
              }}
            >
              Excel’den İrsal Eyle
            </Button>
          </>
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
        <StatCard label="Menzil" value={stops.length} hint={formatDate(date)} />
        <StatCard label="Sevkiyat Bekleyen" value={unassigned.length} tone="gold" hint="İrsal edilen, atanmayan" />
        <StatCard label="Güzergâh" value={routes.length} tone="blue" hint={`${drivers.length} sâik`} />
        <StatCard
          label="Teslim"
          value={delivered}
          tone="green"
          hint={failed ? `${failed} başarısız` : "Başarısız yok"}
        />
      </div>

      <div className="dispatch-grid">
        <section className="panel">
          <div className="panel-head">
            <div>
              <span className="eyebrow">Menziller</span>
              <h2>Menziller</h2>
            </div>
            <Badge tone={unassigned.length ? "gold" : "green"}>
              {unassigned.length ? `${unassigned.length} sevkiyat bekliyor` : "Hazır"}
            </Badge>
          </div>
          {stops.length ? (
            <div className="stop-table">
              {stops.map((stop) => (
                <div className="stop-row" key={stop.id}>
                  <span className="stop-id">{stop.external_id}</span>
                  <div className="stop-main">
                    <strong>{stop.recipient_name || "Alıcı"}</strong>
                    <small>{stop.address}</small>
                    <span className="stop-meta">
                      {stop.time_window_start_min !== null && stop.time_window_end_min !== null
                        ? `${formatClock(stop.time_window_start_min)} – ${formatClock(stop.time_window_end_min)}`
                        : "Zaman penceresi yok"}
                      {stop.weight_kg ? ` · ${stop.weight_kg} kg` : ""}
                    </span>
                  </div>
                  <Badge tone={stop.status}>{statusLabel(stop.status)}</Badge>
                </div>
              ))}
            </div>
          ) : (
            <EmptyState
              icon="⇩"
              title="Bu tarih için menzil yok"
              body="Excel nümunesini indir, doldur ve irsal eyle. Örnek satırlar nümunede hazır."
              action={
                <Button variant="secondary" onClick={() => void downloadTemplate()}>
                  Nümune İndir
                </Button>
              }
            />
          )}
        </section>

        <section className="panel driver-panel">
          <div className="panel-head">
            <div>
              <span className="eyebrow">Kafile</span>
              <h2>Sâikleri seç</h2>
            </div>
            <Link to="/kervan" className="link-inline">
              Kervanı yönet
            </Link>
          </div>
          {drivers.length ? (
            <>
              {drivers.map((driver) => (
                <label className="driver-row" key={driver.id}>
                  <input
                    type="checkbox"
                    checked={selectedDrivers.includes(driver.id)}
                    onChange={() => toggleDriver(driver.id)}
                  />
                  <span className="avatar small">{driver.full_name.slice(0, 1).toUpperCase()}</span>
                  <span>
                    <strong>{driver.full_name}</strong>
                    <small>Vardiya ve menzil limiti kervan ayarında</small>
                  </span>
                </label>
              ))}
              <Button className="btn-block" loading={busy} onClick={() => void optimize()} disabled={!unassigned.length}>
                {unassigned.length ? `Sevkiyatı Başlat (${unassigned.length} menzil)` : "Sevkiyat bekleyen menzil yok"}
              </Button>
              <p className="panel-note">
                Sevkiyat, seçili sâiklerin taslak güzergâhlarını yeniler. Yoldaki güzergâhlara dokunmaz.
              </p>
            </>
          ) : (
            <EmptyState
              icon="◉"
              title="Henüz sâik yok"
              body="Kervan sayfasındaki davet kodunu paylaş; sâik kodu girerek katılsın."
              action={
                <Link to="/kervan">
                  <Button variant="secondary">Davet kodunu aç</Button>
                </Link>
              }
            />
          )}
        </section>
      </div>

      <section className="panel routes-panel">
        <div className="panel-head">
          <div>
            <span className="eyebrow">Güzergâhlar</span>
            <h2>{routes.length ? "Bugünün seferleri" : "Seferler"}</h2>
          </div>
          <span className="panel-note">Yola çıkarılan güzergâh sâikin ekranında görünür.</span>
        </div>
        {loading ? (
          <Spinner />
        ) : (
          <RoutesBoard
            routes={routes}
            selectedId={selectedRouteId}
            onSelect={setSelectedRouteId}
            onPublish={(id) => void publish(id)}
            onUnpublish={(id) => void unpublish(id)}
            onDelete={(id) => void removeRoute(id)}
            busyId={busyRouteId}
            depot={{ lat: me?.crew?.depot_lat ?? 41.0082, lon: me?.crew?.depot_lon ?? 28.9784, name: me?.crew?.depot_name ?? "Depo" }}
            unassignedStops={unassigned}
            onRefresh={() => void load()}
          />
        )}
      </section>

      <Modal
        open={importOpen}
        title="Excel’den menzil irsal eyle"
        onClose={() => setImportOpen(false)}
        wide
        footer={
          <>
            <Button variant="ghost" onClick={() => setImportOpen(false)}>
              Vazgeç
            </Button>
            {importPreview ? (
              <Button
                variant="primary"
                loading={commitBusy}
                disabled={!importPreview.valid_rows}
                onClick={() => void commitImport()}
              >
                {importPreview.valid_rows} menzili irsal eyle
              </Button>
            ) : (
              <Button
                variant="primary"
                loading={importBusy}
                disabled={!importFile}
                onClick={() => void previewImport()}
              >
                Önizle
              </Button>
            )}
          </>
        }
      >
        <div className="import-form">
          <div className="import-top">
            <label className="file-drop">
              <input
                type="file"
                accept=".xlsx"
                onChange={(event) => {
                  setImportFile(event.target.files?.[0] ?? null);
                  setImportPreview(null);
                }}
              />
              <span>{importFile ? importFile.name : "Excel nümunesini seç (.xlsx)"}</span>
              <small>Nümune kullanman en güvenilir yoldur.</small>
            </label>
            <label className="field compact">
              <span>Sefer tarihi</span>
              <input
                className="input"
                type="date"
                value={importDate}
                onChange={(event) => {
                  setImportDate(event.target.value);
                  setImportPreview(null);
                }}
              />
            </label>
          </div>

          {importPreview ? (
            <div className="import-preview">
              <div className="import-summary">
                <Badge tone="green">{importPreview.valid_rows} geçerli</Badge>
                <Badge tone={importPreview.invalid_rows ? "red" : "neutral"}>
                  {importPreview.invalid_rows} hatalı
                </Badge>
                <span className="muted">Toplam {importPreview.total_rows} satır</span>
                {importPreview.invalid_rows ? (
                  <button className="link-btn" onClick={() => void downloadErrors()}>
                    Hata dosyasını indir
                  </button>
                ) : null}
              </div>
              <div className="preview-table">
                <table>
                  <thead>
                    <tr>
                      <th>Satır</th>
                      <th>Menzil</th>
                      <th>Alıcı</th>
                      <th>Adres</th>
                      <th>Durum</th>
                    </tr>
                  </thead>
                  <tbody>
                    {importPreview.rows.map((row) => (
                      <tr key={`${row.row_number}-${row.external_id}`} className={row.status}>
                        <td>{row.row_number}</td>
                        <td>{row.external_id || "—"}</td>
                        <td>{row.recipient_name || "—"}</td>
                        <td>{row.address || "—"}</td>
                        <td>
                          {row.status === "valid" ? (
                            <Badge tone="green">Geçerli</Badge>
                          ) : (
                            <span className="row-error" title={row.errors.join(" · ")}>
                              {row.errors[0]}
                            </span>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          ) : (
            <div className="import-hint">
              <strong>Nümune sütunları</strong>
              <span>menzil_id · alici_adi · telefon · adres · enlem · boylam · baslangic_saat · bitis_saat · agirlik_kg · notlar</span>
              <small>
                Enlem/boylam yoksa adres ücretsiz Photon servisiyle çözümlenir. Toplu işlerde koordinat
                vermek daha güvenilirdir.
              </small>
            </div>
          )}
        </div>
      </Modal>

      <Modal
        open={manualOpen}
        title="Elle menzil ekle"
        onClose={() => setManualOpen(false)}
        wide
        footer={
          <>
            <Button variant="ghost" onClick={() => setManualOpen(false)}>
              Vazgeç
            </Button>
            <Button variant="primary" loading={manualBusy} onClick={() => void createManualStop()}>
              Menzili Ekle
            </Button>
          </>
        }
      >
        <form className="manual-form" onSubmit={createManualStop}>
          {manualError ? <ErrorBanner message={manualError} onClose={() => setManualError("")} /> : null}
          <div className="manual-grid">
            <Field label="Menzil ID" htmlFor="manual-id" hint="Boş bırakılırsa otomatik üretilir">
              <TextInput
                id="manual-id"
                value={manualForm.external_id}
                onChange={(event) => updateManual("external_id", event.target.value)}
                placeholder="MAN-001"
              />
            </Field>
            <Field label="Alıcı adı" htmlFor="manual-recipient">
              <TextInput
                id="manual-recipient"
                value={manualForm.recipient_name}
                onChange={(event) => updateManual("recipient_name", event.target.value)}
                placeholder="Ad soyad"
              />
            </Field>
            <Field label="Telefon" htmlFor="manual-phone">
              <TextInput
                id="manual-phone"
                value={manualForm.phone}
                onChange={(event) => updateManual("phone", event.target.value)}
                placeholder="05XX XXX XX XX"
              />
            </Field>
            <Field label="Ağırlık (kg)" htmlFor="manual-weight">
              <TextInput
                id="manual-weight"
                type="number"
                min={0}
                step="0.1"
                value={manualForm.weight}
                onChange={(event) => updateManual("weight", event.target.value)}
                placeholder="0"
              />
            </Field>
          </div>
          <Field label="Adres" htmlFor="manual-address" hint="Enlem/boylam boşsa adres otomatik çözümlenir">
            <textarea
              id="manual-address"
              className="input textarea"
              value={manualForm.address}
              onChange={(event) => updateManual("address", event.target.value)}
              placeholder="Mahalle, cadde, no, ilçe, il"
              required
            />
          </Field>
          <div className="manual-grid">
            <Field label="Başlangıç saati" htmlFor="manual-start">
              <TextInput
                id="manual-start"
                type="time"
                value={manualForm.start}
                onChange={(event) => updateManual("start", event.target.value)}
              />
            </Field>
            <Field label="Bitiş saati" htmlFor="manual-end">
              <TextInput
                id="manual-end"
                type="time"
                value={manualForm.end}
                onChange={(event) => updateManual("end", event.target.value)}
              />
            </Field>
            <Field label="Enlem" htmlFor="manual-lat" hint="İsteğe bağlı">
              <TextInput
                id="manual-lat"
                type="number"
                step="0.000001"
                value={manualForm.lat}
                onChange={(event) => updateManual("lat", event.target.value)}
                placeholder="41.0082"
              />
            </Field>
            <Field label="Boylam" htmlFor="manual-lon" hint="İsteğe bağlı">
              <TextInput
                id="manual-lon"
                type="number"
                step="0.000001"
                value={manualForm.lon}
                onChange={(event) => updateManual("lon", event.target.value)}
                placeholder="28.9784"
              />
            </Field>
          </div>
          <Field label="Not" htmlFor="manual-notes">
            <textarea
              id="manual-notes"
              className="input textarea"
              value={manualForm.notes}
              onChange={(event) => updateManual("notes", event.target.value)}
              placeholder="Kapıda ödeme, arayın, komşuya bırakılabilir..."
            />
          </Field>
          <button type="submit" hidden />
        </form>
      </Modal>
    </div>
  );
}
