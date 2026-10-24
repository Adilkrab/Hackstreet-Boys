// Small reusable building blocks used by every page.
import { useEffect } from "react";

const ICON_PATHS = {
  dashboard: "M4 4h7v7H4zM13 4h7v4h-7zM13 10h7v10h-7zM4 13h7v7H4z",
  products: "M3 7l9-4 9 4-9 4-9-4zM3 7v10l9 4 9-4V7M12 11v10",
  count: "M9 4h6M9 4a2 2 0 0 0-2 2v0H5v15h14V6h-2v0a2 2 0 0 0-2-2M9 13l2 2 4-4",
  approvals: "M12 3l7 3v6c0 4.5-3 7.5-7 9-4-1.5-7-4.5-7-9V6l7-3zM9 12l2 2 4-4",
  activity: "M4 6h16M4 12h10M4 18h7M18 15v6M15 18h6",
  plus: "M12 5v14M5 12h14",
  upload: "M12 16V4M7 9l5-5 5 5M4 16v4h16v-4",
  sync: "M4 12a8 8 0 0 1 14-5.3L20 9M20 4v5h-5M20 12a8 8 0 0 1-14 5.3L4 15M4 20v-5h5",
  alert: "M12 3l10 18H2L12 3zM12 10v5M12 18v.5",
  check: "M5 12l5 5 9-10",
  x: "M6 6l12 12M18 6L6 18",
  lock: "M6 11h12v10H6zM8 11V8a4 4 0 0 1 8 0v3",
  history: "M3 12a9 9 0 1 0 3-6.7L3 8M3 3v5h5M12 7v5l3 3",
  arrowIn: "M12 4v12M7 11l5 5 5-5M4 20h16",
  arrowOut: "M12 20V8M7 13l5-5 5 5M4 4h16",
  download: "M12 4v12M7 11l5 5 5-5M4 20h16",
};

export function Icon({ name, size = 18 }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.9"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d={ICON_PATHS[name]} />
    </svg>
  );
}

export function Badge({ tone = "neutral", children }) {
  return <span className={`badge badge-${tone}`}>{children}</span>;
}

export function StatCard({ label, value, hint, tone = "neutral", onClick }) {
  const Tag = onClick ? "button" : "div";
  return (
    <Tag className={`stat stat-${tone}`} onClick={onClick} type={onClick ? "button" : undefined}>
      <span className="stat-label">{label}</span>
      <span className="stat-value">{value}</span>
      {hint && <span className="stat-hint">{hint}</span>}
    </Tag>
  );
}

export function Modal({ title, onClose, children, wide = false }) {
  useEffect(() => {
    const onKey = (e) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  return (
    <div className="modal-backdrop" onMouseDown={(e) => e.target === e.currentTarget && onClose()}>
      <div className={`modal ${wide ? "modal-wide" : ""}`} role="dialog" aria-modal="true" aria-label={title}>
        <div className="modal-head">
          <h2>{title}</h2>
          <button className="icon-btn" onClick={onClose} aria-label="Close">
            <Icon name="x" />
          </button>
        </div>
        <div className="modal-body">{children}</div>
      </div>
    </div>
  );
}

export function EmptyState({ title, children }) {
  return (
    <div className="empty">
      <strong>{title}</strong>
      {children && <p>{children}</p>}
    </div>
  );
}

export function ErrorBox({ error, onRetry }) {
  if (!error) return null;
  return (
    <div className="callout callout-bad" role="alert">
      <Icon name="alert" />
      <div>
        {error.message}
        {onRetry && (
          <button className="link-btn" onClick={onRetry}>
            Try again
          </button>
        )}
      </div>
    </div>
  );
}

export function Loading({ label = "Loading…" }) {
  return <div className="loading">{label}</div>;
}

export function PageHeader({ title, subtitle, children }) {
  return (
    <header className="page-head">
      <div>
        <h1>{title}</h1>
        {subtitle && <p className="muted">{subtitle}</p>}
      </div>
      {children && <div className="page-actions">{children}</div>}
    </header>
  );
}
