import { useCallback, useEffect, useState, type FormEvent } from "react";
import { api, ApiError } from "../api";
import { useAuth } from "../auth";
import {
  Badge,
  Button,
  ErrorBanner,
  Field,
  PageHeader,
  SelectInput,
  Spinner,
  TextInput,
} from "../components/ui";
import { minutesToTime, statusLabel, timeToMinutes } from "../format";
import type { Crew, Member, Role } from "../types";

export function CrewPage() {
  const { token, me, refresh } = useAuth();
  const [crew, setCrew] = useState<Crew | null>(null);
  const [members, setMembers] = useState<Member[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [copied, setCopied] = useState(false);

  const load = useCallback(async () => {
    if (!token) return;
    setLoading(true);
    try {
      const [nextCrew, nextMembers] = await Promise.all([api.getCrew(token), api.listMembers(token)]);
      setCrew(nextCrew);
      setMembers(nextMembers);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Kervan getirilemedi.");
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => {
    void load();
  }, [load]);

  async function saveSettings(event: FormEvent) {
    event.preventDefault();
    if (!token || !crew) return;
    setSaving(true);
    setError("");
    try {
      const updated = await api.updateCrew(token, {
        name: crew.name,
        depot_name: crew.depot_name,
        depot_lat: crew.depot_lat,
        depot_lon: crew.depot_lon,
        shift_start_min: crew.shift_start_min,
        shift_end_min: crew.shift_end_min,
        service_minutes: crew.service_minutes,
        max_stops_per_driver: crew.max_stops_per_driver,
      });
      setCrew(updated);
      setNotice("Kervan ayarları kaydedildi.");
      await refresh();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Ayarlar kaydedilemedi.");
    } finally {
      setSaving(false);
    }
  }

  async function rotateCode() {
    if (!token || !window.confirm("Mevcut davet kodu geçersiz olacak. Devam edilsin mi?")) return;
    try {
      const result = await api.rotateCode(token);
      setCrew((previous) =>
        previous
          ? {
              ...previous,
              invite_code: result.invite_code,
              invite_expires_at: result.invite_expires_at,
              invite_uses: 0,
            }
          : previous
      );
      setNotice("Yeni davet kodu oluşturuldu.");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Kod yenilenemedi.");
    }
  }

  async function copyCode() {
    if (!crew?.invite_code) return;
    await navigator.clipboard.writeText(crew.invite_code);
    setCopied(true);
    window.setTimeout(() => setCopied(false), 1800);
  }

  async function changeRole(member: Member, role: Role) {
    if (!token) return;
    try {
      await api.changeRole(token, member.id, role);
      await load();
      await refresh();
      setNotice(`${member.full_name} artık ${statusLabel(role).toLowerCase()}.`);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Rol değiştirilemedi.");
    }
  }

  async function removeMember(member: Member) {
    if (!token || !window.confirm(`${member.full_name} kervandan çıkarılsın mı?`)) return;
    try {
      await api.removeMember(token, member.id);
      await load();
      setNotice(`${member.full_name} kervandan çıkarıldı.`);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Üye çıkarılamadı.");
    }
  }

  if (loading || !crew) return <div className="page"><Spinner /></div>;

  return (
    <div className="page">
      <PageHeader
        eyebrow="Kervan"
        title={crew.name}
        description="Ekibini, davet kodunu ve sevkiyat varsayılanlarını yönet."
        actions={<Badge tone="gold">{crew.member_count} kişi</Badge>}
      />
      {error ? <ErrorBanner message={error} onClose={() => setError("")} /> : null}
      {notice ? (
        <div className="notice-banner">
          <span>{notice}</span>
          <button onClick={() => setNotice("")}>×</button>
        </div>
      ) : null}

      <div className="crew-grid">
        <section className="panel invite-panel">
          <span className="eyebrow">Davet kodu</span>
          <h2>Kervanına sâik çağır</h2>
          <p>Kodu WhatsApp’tan paylaş. Sâik kodu girerek kervana katılır ve yalnızca kendi seferini görür.</p>
          <div className="invite-code">
            <span>{crew.invite_code ?? "—"}</span>
            <Button variant="secondary" onClick={() => void copyCode()}>
              {copied ? "Kopyalandı" : "Kopyala"}
            </Button>
          </div>
          <div className="invite-meta">
            <span>{crew.invite_uses ?? 0} / {crew.invite_max_uses ?? 0} kullanım</span>
            <button className="link-btn" onClick={() => void rotateCode()}>
              Kodu yenile
            </button>
          </div>
        </section>

        <section className="panel">
          <span className="eyebrow">Kafile</span>
          <h2>Üyeler</h2>
          <div className="members-list">
            {members.map((member) => (
              <div className="member-row" key={member.id}>
                <span className="avatar">{member.full_name.slice(0, 1).toUpperCase()}</span>
                <div className="member-main">
                  <strong>
                    {member.full_name} {member.is_owner ? <span className="owner-tag">Sahip</span> : null}
                  </strong>
                  <small>{member.phone || "Telefon gizli"}</small>
                </div>
                {member.is_owner ? (
                  <Badge tone="gold">Kervanbaşı</Badge>
                ) : (
                  <SelectInput
                    value={member.role}
                    onChange={(event) => void changeRole(member, event.target.value as Role)}
                  >
                    <option value="driver">Sâik</option>
                    <option value="dispatcher">Kervanbaşı</option>
                  </SelectInput>
                )}
                {!member.is_owner && member.id !== me?.user.id ? (
                  <button className="icon-btn danger" onClick={() => void removeMember(member)} aria-label="Çıkar">
                    ×
                  </button>
                ) : null}
              </div>
            ))}
          </div>
          <p className="panel-note">
            Kervan sahibi çıkarılamaz. Son kervanbaşı sâik yapılamaz. Aktif seferi olan sâik çıkarılamaz.
          </p>
        </section>
      </div>

      <section className="panel">
        <div className="panel-head">
          <div>
            <span className="eyebrow">Sevkiyat varsayılanları</span>
            <h2>Depo ve vardiya</h2>
          </div>
        </div>
        <form className="settings-grid" onSubmit={saveSettings}>
          <Field label="Kervan adı" htmlFor="crew-name">
            <TextInput
              id="crew-name"
              value={crew.name}
              onChange={(event) => setCrew({ ...crew, name: event.target.value })}
            />
          </Field>
          <Field label="Depo adı" htmlFor="depot-name">
            <TextInput
              id="depot-name"
              value={crew.depot_name}
              onChange={(event) => setCrew({ ...crew, depot_name: event.target.value })}
            />
          </Field>
          <Field label="Depo enlemi" htmlFor="depot-lat" hint="Harita koordinatı">
            <TextInput
              id="depot-lat"
              type="number"
              step="0.000001"
              value={crew.depot_lat}
              onChange={(event) => setCrew({ ...crew, depot_lat: Number(event.target.value) })}
            />
          </Field>
          <Field label="Depo boylamı" htmlFor="depot-lon" hint="Harita koordinatı">
            <TextInput
              id="depot-lon"
              type="number"
              step="0.000001"
              value={crew.depot_lon}
              onChange={(event) => setCrew({ ...crew, depot_lon: Number(event.target.value) })}
            />
          </Field>
          <Field label="Vardiya başlangıcı" htmlFor="shift-start">
            <TextInput
              id="shift-start"
              type="time"
              value={minutesToTime(crew.shift_start_min)}
              onChange={(event) =>
                setCrew({ ...crew, shift_start_min: timeToMinutes(event.target.value) })
              }
            />
          </Field>
          <Field label="Vardiya bitişi" htmlFor="shift-end">
            <TextInput
              id="shift-end"
              type="time"
              value={minutesToTime(crew.shift_end_min)}
              onChange={(event) =>
                setCrew({ ...crew, shift_end_min: timeToMinutes(event.target.value) })
              }
            />
          </Field>
          <Field label="Menzil başına hizmet" htmlFor="service" hint="Dakika">
            <TextInput
              id="service"
              type="number"
              min={0}
              max={120}
              value={crew.service_minutes}
              onChange={(event) => setCrew({ ...crew, service_minutes: Number(event.target.value) })}
            />
          </Field>
          <Field label="Sâik başına menzil" htmlFor="max-stops" hint="Sevkiyat üst sınırı">
            <TextInput
              id="max-stops"
              type="number"
              min={1}
              max={200}
              value={crew.max_stops_per_driver}
              onChange={(event) =>
                setCrew({ ...crew, max_stops_per_driver: Number(event.target.value) })
              }
            />
          </Field>
          <div className="settings-actions">
            <Button type="submit" loading={saving}>
              Ayarları kaydet
            </Button>
          </div>
        </form>
      </section>
    </div>
  );
}
