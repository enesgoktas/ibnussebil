import { useEffect, useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api, ApiError } from "../api";
import { useAuth } from "../auth";
import {
  Badge,
  Button,
  ErrorBanner,
  Field,
  PageHeader,
  TextInput,
} from "../components/ui";
import { statusLabel } from "../format";
import type { Member } from "../types";

export function ProfilePage() {
  const { token, me, refresh, setMe, logout } = useAuth();
  const navigate = useNavigate();
  const [members, setMembers] = useState<Member[]>([]);
  const [fullName, setFullName] = useState(me?.user.full_name ?? "");
  const [savingName, setSavingName] = useState(false);
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [savingPassword, setSavingPassword] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  useEffect(() => {
    setFullName(me?.user.full_name ?? "");
  }, [me?.user.full_name]);

  useEffect(() => {
    if (!token) return;
    api
      .listMembers(token)
      .then(setMembers)
      .catch(() => setMembers([]));
  }, [token]);

  async function saveName(event: FormEvent) {
    event.preventDefault();
    if (!token) return;
    setSavingName(true);
    setError("");
    try {
      const updated = await api.updateMe(token, fullName);
      const next = await refresh();
      if (next) setMe({ ...next, user: updated });
      setNotice("Adın güncellendi.");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Ad güncellenemedi.");
    } finally {
      setSavingName(false);
    }
  }

  async function savePassword(event: FormEvent) {
    event.preventDefault();
    if (!token) return;
    if (newPassword !== confirmPassword) {
      setError("Yeni şifreler eşleşmiyor.");
      return;
    }
    setSavingPassword(true);
    setError("");
    try {
      await api.changePassword(token, currentPassword, newPassword);
      setCurrentPassword("");
      setNewPassword("");
      setConfirmPassword("");
      setNotice("Şifren güncellendi.");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Şifre güncellenemedi.");
    } finally {
      setSavingPassword(false);
    }
  }

  async function leaveCrew() {
    if (!token || !window.confirm("Kervandan ayrılmak istediğine emin misin?")) return;
    try {
      await api.leaveCrew(token);
      logout();
      navigate("/login", { replace: true });
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Kervandan ayrılınamadı.");
    }
  }

  return (
    <div className="page">
      <PageHeader
        eyebrow="Künye"
        title={me?.user.full_name ?? "Profil"}
        description="Hesabın, kervanın ve kafilen."
        actions={
          me?.role === "dispatcher" ? (
            <Link to="/kervan">
              <Button variant="secondary">Kervanı yönet</Button>
            </Link>
          ) : undefined
        }
      />
      {error ? <ErrorBanner message={error} onClose={() => setError("")} /> : null}
      {notice ? (
        <div className="notice-banner">
          <span>{notice}</span>
          <button onClick={() => setNotice("")}>×</button>
        </div>
      ) : null}

      <div className="profile-grid">
        <section className="panel identity-card">
          <div className="identity-head">
            <span className="avatar xl">{me?.user.full_name.slice(0, 1).toUpperCase()}</span>
            <div>
              <h2>{me?.user.full_name}</h2>
              <p>{me?.user.phone}</p>
              <div className="badge-row">
                <Badge tone={me?.role === "dispatcher" ? "gold" : "blue"}>
                  {me?.role ? statusLabel(me.role) : "Üye değil"}
                </Badge>
                <Badge tone="neutral">{me?.crew?.name}</Badge>
              </div>
            </div>
          </div>
          <div className="identity-meta">
            <div>
              <span>Kervan</span>
              <strong>{me?.crew?.name ?? "—"}</strong>
            </div>
            <div>
              <span>Depo</span>
              <strong>{me?.crew?.depot_name ?? "—"}</strong>
            </div>
            <div>
              <span>Vardiya</span>
              <strong>
                {me?.crew
                  ? `${String(Math.floor(me.crew.shift_start_min / 60)).padStart(2, "0")}:${String(
                      me.crew.shift_start_min % 60
                    ).padStart(2, "0")} – ${String(Math.floor(me.crew.shift_end_min / 60)).padStart(
                      2,
                      "0"
                    )}:${String(me.crew.shift_end_min % 60).padStart(2, "0")}`
                  : "—"}
              </strong>
            </div>
          </div>
          {me?.role === "driver" ? (
            <Button variant="ghost" onClick={() => void leaveCrew()}>
              Kervandan ayrıl
            </Button>
          ) : null}
        </section>

        <section className="panel">
          <span className="eyebrow">Hesap</span>
          <h2>Adını güncelle</h2>
          <form onSubmit={saveName} className="stack-form">
            <Field label="Ad soyad" htmlFor="profile-name">
              <TextInput
                id="profile-name"
                value={fullName}
                onChange={(event) => setFullName(event.target.value)}
                required
              />
            </Field>
            <Button type="submit" loading={savingName}>
              Kaydet
            </Button>
          </form>

          <div className="divider" />
          <span className="eyebrow">Güvenlik</span>
          <h2>Şifre değiştir</h2>
          <form onSubmit={savePassword} className="stack-form">
            <Field label="Mevcut şifre" htmlFor="current-password">
              <TextInput
                id="current-password"
                type="password"
                value={currentPassword}
                onChange={(event) => setCurrentPassword(event.target.value)}
                autoComplete="current-password"
                required
              />
            </Field>
            <Field label="Yeni şifre" htmlFor="new-password" hint="En az 8 karakter">
              <TextInput
                id="new-password"
                type="password"
                value={newPassword}
                onChange={(event) => setNewPassword(event.target.value)}
                autoComplete="new-password"
                required
              />
            </Field>
            <Field label="Yeni şifre (tekrar)" htmlFor="confirm-password">
              <TextInput
                id="confirm-password"
                type="password"
                value={confirmPassword}
                onChange={(event) => setConfirmPassword(event.target.value)}
                autoComplete="new-password"
                required
              />
            </Field>
            <Button type="submit" loading={savingPassword}>
              Şifreyi değiştir
            </Button>
          </form>
        </section>
      </div>

      <section className="panel">
        <div className="panel-head">
          <div>
            <span className="eyebrow">Kafile</span>
            <h2>Ekibin</h2>
          </div>
          <Badge tone="neutral">{members.length} kişi</Badge>
        </div>
        <div className="members-list compact-list">
          {members.map((member) => (
            <div className="member-row" key={member.id}>
              <span className="avatar small">{member.full_name.slice(0, 1).toUpperCase()}</span>
              <div className="member-main">
                <strong>{member.full_name}</strong>
                <small>{member.phone || "Telefon gizli"}</small>
              </div>
              <Badge tone={member.role === "dispatcher" ? "gold" : "blue"}>
                {statusLabel(member.role)}
              </Badge>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
