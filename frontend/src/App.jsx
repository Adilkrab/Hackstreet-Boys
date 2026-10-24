import { useCallback, useMemo, useState } from "react";
import { AppContext } from "./context.js";
import { APP_NAME, APP_TAGLINE, ROLES, SHOP_NAME } from "./config.js";
import { api } from "./services/api.js";
import { useLoad } from "./utils/useLoad.js";
import { Icon } from "./components/ui.jsx";
import Dashboard from "./pages/Dashboard.jsx";
import Products from "./pages/Products.jsx";
import StockCount from "./pages/StockCount.jsx";
import Approvals from "./pages/Approvals.jsx";
import ActivityLog from "./pages/ActivityLog.jsx";

const PAGES = [
  { key: "dashboard", label: "Dashboard", icon: "dashboard" },
  { key: "products", label: "Products", icon: "products" },
  { key: "count", label: "Stock count", icon: "count" },
  { key: "approvals", label: "Approvals", icon: "approvals" },
  { key: "activity", label: "Activity log", icon: "activity" },
];

function savedRole() {
  try {
    return ROLES[localStorage.getItem("role")] ? localStorage.getItem("role") : "owner";
  } catch {
    return "owner";
  }
}

export default function App() {
  const [page, setPage] = useState("dashboard");
  const [countProductId, setCountProductId] = useState(null);
  const [roleKey, setRoleKey] = useState(savedRole);
  const [refreshKey, setRefreshKey] = useState(0);
  const [toasts, setToasts] = useState([]);

  const role = ROLES[roleKey];

  // Number on the Approvals tab.
  const pending = useLoad(() => api.pending(), [refreshKey]);
  const pendingCount = pending.data?.length ?? 0;

  const notify = useCallback((message, tone = "good") => {
    const id = Math.random().toString(36).slice(2);
    setToasts((list) => [...list.slice(-2), { id, message, tone }]);
    setTimeout(() => setToasts((list) => list.filter((t) => t.id !== id)), 4500);
  }, []);

  const refresh = useCallback(() => setRefreshKey((k) => k + 1), []);

  const goTo = useCallback((next, options = {}) => {
    if (next === "count") setCountProductId(options.productId ?? null);
    setPage(next);
    window.scrollTo({ top: 0 });
  }, []);

  const changeRole = (key) => {
    setRoleKey(key);
    try {
      localStorage.setItem("role", key);
    } catch {
      /* private mode: ignore */
    }
    notify(`Now using the app as ${ROLES[key].name}.`, "info");
  };

  const context = useMemo(
    () => ({ role, notify, refresh, refreshKey, goTo }),
    [role, notify, refresh, refreshKey, goTo]
  );

  return (
    <AppContext.Provider value={context}>
      <div className="shell">
        <aside className="sidebar">
          <div className="brand">
            <span className="brand-mark">
              <Icon name="check" size={20} />
            </span>
            <div>
              <strong>{APP_NAME}</strong>
              <span>{APP_TAGLINE}</span>
            </div>
          </div>

          <nav className="nav" aria-label="Main">
            {PAGES.map((p) => (
              <button
                key={p.key}
                className={`nav-item ${page === p.key ? "active" : ""}`}
                onClick={() => goTo(p.key)}
                aria-current={page === p.key ? "page" : undefined}
              >
                <Icon name={p.icon} />
                <span>{p.label}</span>
                {p.key === "approvals" && pendingCount > 0 && <span className="nav-count">{pendingCount}</span>}
              </button>
            ))}
          </nav>

          <div className="sidebar-foot">
            <span className="hub-chip">
              <span className="hub-dot" /> Connected to Orbyte hub (simulated)
            </span>
          </div>
        </aside>

        <div className="main">
          <div className="topbar">
            <div className="shop">
              <span className="muted small">Shop</span>
              <strong>{SHOP_NAME}</strong>
            </div>
            <div className="role-switch" role="group" aria-label="Demo login">
              <span className="muted small">Signed in as (demo)</span>
              <div className="segmented">
                {Object.values(ROLES).map((r) => (
                  <button
                    key={r.key}
                    className={roleKey === r.key ? "on" : ""}
                    onClick={() => changeRole(r.key)}
                    aria-pressed={roleKey === r.key}
                  >
                    {r.label}
                  </button>
                ))}
              </div>
            </div>
          </div>

          <main className="content">
            {page === "dashboard" && <Dashboard />}
            {page === "products" && <Products />}
            {page === "count" && <StockCount initialProductId={countProductId} />}
            {page === "approvals" && <Approvals />}
            {page === "activity" && <ActivityLog />}
          </main>
        </div>

        <div className="toasts" aria-live="polite">
          {toasts.map((t) => (
            <div key={t.id} className={`toast toast-${t.tone}`}>
              {t.message}
            </div>
          ))}
        </div>
      </div>
    </AppContext.Provider>
  );
}
