import { useEffect, useRef, useState } from "react";
import { NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../auth";
import { statusLabel } from "../format";
import { CaravanMark } from "./CaravanMark";

const dispatcherDesktop = [
  { to: "/sevk", label: "Sevkiyat", icon: "⌁" },
  { to: "/seferler", label: "Seferler", icon: "≡" },
  { to: "/kervan", label: "Kervan", icon: "◉" },
];

const driverDesktop = [{ to: "/seferim", label: "Seferim", icon: "⌁" }];

export function Shell() {
  const { me, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [menuOpen, setMenuOpen] = useState(false);
  const userMenuRef = useRef<HTMLDivElement | null>(null);

  const desktopNav = me?.role === "dispatcher" ? dispatcherDesktop : driverDesktop;
  const mobileNav =
    me?.role === "dispatcher"
      ? [...dispatcherDesktop, { to: "/profil", label: "Künye", icon: "◇" }]
      : [{ to: "/seferim", label: "Seferim", icon: "⌁" }, { to: "/profil", label: "Künye", icon: "◇" }];

  useEffect(() => {
    setMenuOpen(false);
  }, [location.pathname]);

  useEffect(() => {
    if (!menuOpen) return;
    function onPointerDown(event: MouseEvent) {
      if (userMenuRef.current && !userMenuRef.current.contains(event.target as Node)) {
        setMenuOpen(false);
      }
    }
    function onKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") setMenuOpen(false);
    }
    document.addEventListener("mousedown", onPointerDown);
    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.removeEventListener("mousedown", onPointerDown);
      document.removeEventListener("keydown", onKeyDown);
    };
  }, [menuOpen]);

  function handleLogout() {
    setMenuOpen(false);
    logout();
    navigate("/login");
  }

  return (
    <div className="app-shell">
      <header className="topbar">
        <NavLink to="/" className="brand">
          <CaravanMark className="brand-mark" />
          <span className="brand-name">İbnüssebil</span>
        </NavLink>
        <nav className="desktop-nav">
          {desktopNav.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) => (isActive ? "nav-link active" : "nav-link")}
            >
              <span className="nav-icon">{item.icon}</span>
              {item.label}
            </NavLink>
          ))}
        </nav>
        <div className="topbar-user" ref={userMenuRef}>
          <button
            type="button"
            className={`user-chip ${menuOpen ? "open" : ""}`}
            onClick={() => setMenuOpen((value) => !value)}
            aria-haspopup="menu"
            aria-expanded={menuOpen}
          >
            <span className="avatar">{me?.user.full_name.slice(0, 1).toUpperCase()}</span>
            <span className="user-meta">
              <strong>{me?.user.full_name}</strong>
              <small>
                {me?.crew?.name} · {me?.role ? statusLabel(me.role) : ""}
              </small>
            </span>
            <span className="user-chevron">⌄</span>
          </button>
          {menuOpen ? (
            <div className="user-menu" role="menu">
              <div className="user-menu-head">
                <strong>{me?.user.full_name}</strong>
                <span>
                  {me?.crew?.name} · {me?.role ? statusLabel(me.role) : ""}
                </span>
              </div>
              <button
                type="button"
                role="menuitem"
                onClick={() => {
                  setMenuOpen(false);
                  navigate("/profil");
                }}
              >
                Künye
              </button>
              <button type="button" role="menuitem" className="danger" onClick={handleLogout}>
                Çıkış yap
              </button>
            </div>
          ) : null}
        </div>
      </header>

      <main className="app-main">
        <Outlet />
      </main>

      <nav className="mobile-nav">
        {mobileNav.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            className={({ isActive }) => (isActive ? "mobile-link active" : "mobile-link")}
          >
            <span>{item.icon}</span>
            <small>{item.label}</small>
          </NavLink>
        ))}
      </nav>
    </div>
  );
}
