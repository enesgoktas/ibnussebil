import { Navigate, Route, Routes } from "react-router-dom";
import { useAuth } from "./auth";
import { CaravanMark } from "./components/CaravanMark";
import { Shell } from "./components/Shell";
import { Spinner } from "./components/ui";
import { AuthPage } from "./pages/AuthPage";
import { CrewPage } from "./pages/CrewPage";
import { DispatcherRoutesPage } from "./pages/DispatcherRoutesPage";
import { DispatcherSevkPage } from "./pages/DispatcherSevkPage";
import { DriverRoutePage } from "./pages/DriverRoutePage";
import { JoinPage } from "./pages/JoinPage";
import { ProfilePage } from "./pages/ProfilePage";
import type { ReactNode } from "react";

function LoadingScreen() {
  return (
    <div className="boot-screen">
      <div className="brand brand-center">
        <CaravanMark className="brand-mark" />
        <span className="brand-name">İbnüssebil</span>
      </div>
      <Spinner label="Kervan hazırlanıyor" />
    </div>
  );
}

function ProtectedShell() {
  const { token, me, loading } = useAuth();
  if (loading) return <LoadingScreen />;
  if (!token || !me) return <Navigate to="/login" replace />;
  if (!me.role) return <Navigate to="/join" replace />;
  return <Shell />;
}

function JoinGate() {
  const { token, me, loading } = useAuth();
  if (loading) return <LoadingScreen />;
  if (!token || !me) return <Navigate to="/login" replace />;
  if (me.role) return <Navigate to="/" replace />;
  return <JoinPage />;
}

function HomeRedirect() {
  const { me } = useAuth();
  return <Navigate to={me?.role === "driver" ? "/seferim" : "/sevk"} replace />;
}

function DispatcherOnly({ children }: { children: ReactNode }) {
  const { me } = useAuth();
  if (me?.role !== "dispatcher") return <Navigate to="/seferim" replace />;
  return <>{children}</>;
}

function DriverOnly({ children }: { children: ReactNode }) {
  const { me } = useAuth();
  if (me?.role !== "driver") return <Navigate to="/sevk" replace />;
  return <>{children}</>;
}

export function App() {
  return (
    <Routes>
      <Route path="/login" element={<AuthPage />} />
      <Route path="/join" element={<JoinGate />} />
      <Route element={<ProtectedShell />}>
        <Route path="/" element={<HomeRedirect />} />
        <Route
          path="/sevk"
          element={
            <DispatcherOnly>
              <DispatcherSevkPage />
            </DispatcherOnly>
          }
        />
        <Route
          path="/seferler"
          element={
            <DispatcherOnly>
              <DispatcherRoutesPage />
            </DispatcherOnly>
          }
        />
        <Route
          path="/kervan"
          element={
            <DispatcherOnly>
              <CrewPage />
            </DispatcherOnly>
          }
        />
        <Route path="/profil" element={<ProfilePage />} />
        <Route
          path="/seferim"
          element={
            <DriverOnly>
              <DriverRoutePage />
            </DriverOnly>
          }
        />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
