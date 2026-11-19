import { useState, type FormEvent } from "react";
import { Navigate, useNavigate } from "react-router-dom";
import { ApiError } from "../api";
import { useAuth } from "../auth";
import { CaravanMark } from "../components/CaravanMark";
import { Button, ErrorBanner, Field, TextInput } from "../components/ui";

type Tab = "login" | "dispatcher" | "driver";

export function AuthPage() {
  const { login, signupDispatcher, signupDriver, me, loading } = useAuth();
  const navigate = useNavigate();
  const [tab, setTab] = useState<Tab>("login");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [phone, setPhone] = useState("");
  const [password, setPassword] = useState("");
  const [fullName, setFullName] = useState("");
  const [crewName, setCrewName] = useState("");
  const [depotName, setDepotName] = useState("Merkez Depo");
  const [inviteCode, setInviteCode] = useState("");

  if (!loading && me?.role) {
    return <Navigate to="/" replace />;
  }
  if (!loading && me && !me.role) {
    return <Navigate to="/join" replace />;
  }

  function go(nextRole: string | null) {
    navigate(nextRole ? "/" : "/join", { replace: true });
  }

  async function submit(event: FormEvent) {
    event.preventDefault();
    setError("");
    setBusy(true);
    try {
      if (tab === "login") {
        const me = await login(phone, password);
        go(me.role);
      } else if (tab === "dispatcher") {
        const me = await signupDispatcher({
          full_name: fullName,
          phone,
          password,
          crew_name: crewName,
          depot_name: depotName,
          depot_lat: 41.0082,
          depot_lon: 28.9784,
        });
        go(me.role);
      } else {
        const me = await signupDriver({
          full_name: fullName,
          phone,
          password,
          invite_code: inviteCode,
        });
        go(me.role);
      }
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Bağlantı kurulamadı.");
    } finally {
      setBusy(false);
    }
  }

  async function quickLogin(demoPhone: string) {
    setError("");
    setBusy(true);
    try {
      const me = await login(demoPhone, "demo1234");
      go(me.role);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Demo girişi başarısız.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="auth-page">
      <section className="auth-story">
        <div className="brand brand-large">
          <CaravanMark className="brand-mark" />
          <span className="brand-name">İbnüssebil</span>
        </div>
        <div className="story-copy">
          <span className="eyebrow light">Kervanını kur, güzergâhını çıkar</span>
          <h1>Excel’den sâikin telefonuna, beş dakikada.</h1>
          <p>
            Menzilleri irsal eyle, sâikleri seç, güzergâhları tek tıkla oluştur. Sâik
            uygulama indirmeden tarayıcıdan seferini görür.
          </p>
          <div className="story-steps">
            <div>
              <span>01</span>
              <strong>Nümune indir</strong>
              <small>Adresler, saatler, notlar.</small>
            </div>
            <div>
              <span>02</span>
              <strong>Sevkiyatı başlat</strong>
              <small>Menzilleri sâiklere dağıt.</small>
            </div>
            <div>
              <span>03</span>
              <strong>Yola çık</strong>
              <small>Sâik seferini telefonunda görsün.</small>
            </div>
          </div>
        </div>
        <div className="story-foot">
          <span>İbnüssebil</span>
          <span>Yolun oğlu, yükün emrinde.</span>
        </div>
      </section>

      <section className="auth-panel">
        <div className="auth-card">
          <div className="auth-tabs">
            <button className={tab === "login" ? "active" : ""} onClick={() => setTab("login")}>
              Giriş
            </button>
            <button
              className={tab === "dispatcher" ? "active" : ""}
              onClick={() => setTab("dispatcher")}
            >
              Kervan kur
            </button>
            <button className={tab === "driver" ? "active" : ""} onClick={() => setTab("driver")}>
              Sâik katıl
            </button>
          </div>

          <div className="auth-heading">
            <h2>
              {tab === "login"
                ? "Kervanına dön"
                : tab === "dispatcher"
                  ? "Yeni bir kervan kur"
                  : "Davet koduyla katıl"}
            </h2>
            <p>
              {tab === "login"
                ? "Telefon numaran ve şifrenle giriş yap."
                : tab === "dispatcher"
                  ? "Kervanı kur, kodu ekibinle paylaş."
                  : "Kervanbaşının paylaştığı kodu gir."}
            </p>
          </div>

          {error ? <ErrorBanner message={error} onClose={() => setError("")} /> : null}

          <form onSubmit={submit} className="auth-form">
            {tab !== "login" ? (
              <Field label="Ad soyad" htmlFor="full_name">
                <TextInput
                  id="full_name"
                  value={fullName}
                  onChange={(event) => setFullName(event.target.value)}
                  placeholder="Adın ve soyadın"
                  required
                />
              </Field>
            ) : null}

            {tab === "dispatcher" ? (
              <>
                <Field label="Kervan adı" htmlFor="crew_name" hint="Örn. Kadıköy Kervanı">
                  <TextInput
                    id="crew_name"
                    value={crewName}
                    onChange={(event) => setCrewName(event.target.value)}
                    placeholder="Kervan adı"
                    required
                  />
                </Field>
                <Field label="Depo adı" htmlFor="depot_name">
                  <TextInput
                    id="depot_name"
                    value={depotName}
                    onChange={(event) => setDepotName(event.target.value)}
                    placeholder="Merkez Depo"
                  />
                </Field>
              </>
            ) : null}

            <Field label="Telefon" htmlFor="phone">
              <TextInput
                id="phone"
                value={phone}
                onChange={(event) => setPhone(event.target.value)}
                placeholder="05XX XXX XX XX"
                autoComplete="tel"
                required
              />
            </Field>

            <Field label="Şifre" htmlFor="password" hint={tab === "login" ? undefined : "En az 8 karakter"}>
              <TextInput
                id="password"
                type="password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                placeholder="••••••••"
                autoComplete={tab === "login" ? "current-password" : "new-password"}
                required
              />
            </Field>

            {tab === "driver" ? (
              <Field label="Kervan kodu" htmlFor="invite_code" hint="Kervanbaşının paylaştığı 8 haneli kod">
                <TextInput
                  id="invite_code"
                  value={inviteCode}
                  onChange={(event) => setInviteCode(event.target.value.toUpperCase())}
                  placeholder="ABCD2345"
                  required
                />
              </Field>
            ) : null}

            <Button type="submit" loading={busy} className="btn-block">
              {tab === "login" ? "Giriş yap" : tab === "dispatcher" ? "Kervanı kur" : "Kervana katıl"}
            </Button>
          </form>

          {tab === "login" ? (
            <div className="demo-box">
              <span className="demo-label">Demo hesapları</span>
              <div className="demo-actions">
                <button type="button" onClick={() => void quickLogin("05001112233")} disabled={busy}>
                  Kervanbaşı demosu
                </button>
                <button type="button" onClick={() => void quickLogin("05002223344")} disabled={busy}>
                  Sâik demosu
                </button>
              </div>
              <small>Demo şifresi: demo1234</small>
            </div>
          ) : null}
        </div>
      </section>
    </div>
  );
}
