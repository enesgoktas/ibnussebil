import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { api, ApiError } from "../api";
import { useAuth } from "../auth";
import { CaravanMark } from "../components/CaravanMark";
import { Button, ErrorBanner, Field, TextInput } from "../components/ui";

export function JoinPage() {
  const { token, me, refresh, logout } = useAuth();
  const navigate = useNavigate();
  const [code, setCode] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    if (!token) return;
    setBusy(true);
    setError("");
    try {
      await api.joinCrew(token, code);
      await refresh();
      navigate("/", { replace: true });
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Kervana katılınamadı.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="join-page">
      <div className="join-card">
        <div className="brand brand-center">
          <CaravanMark className="brand-mark" />
          <span className="brand-name">İbnüssebil</span>
        </div>
        <span className="eyebrow">Bir kervana katıl</span>
        <h1>Hoş geldin{me?.user.full_name ? `, ${me.user.full_name.split(" ")[0]}` : ""}.</h1>
        <p>Kervanbaşının paylaştığı davet kodunu girerek ekibe katıl.</p>
        {error ? <ErrorBanner message={error} onClose={() => setError("")} /> : null}
        <form onSubmit={submit}>
          <Field label="Kervan kodu" htmlFor="code" hint="8 haneli davet kodu">
            <TextInput
              id="code"
              value={code}
              onChange={(event) => setCode(event.target.value.toUpperCase())}
              placeholder="ABCD2345"
              required
            />
          </Field>
          <Button type="submit" loading={busy} className="btn-block">
            Kervana katıl
          </Button>
        </form>
        <button
          className="link-btn"
          onClick={() => {
            logout();
            navigate("/login");
          }}
        >
          Başka bir hesapla giriş yap
        </button>
      </div>
    </div>
  );
}
