import type { ButtonHTMLAttributes, InputHTMLAttributes, ReactNode, SelectHTMLAttributes } from "react";

export function Button({
  variant = "primary",
  loading = false,
  className = "",
  children,
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: "primary" | "secondary" | "ghost" | "danger" | "gold";
  loading?: boolean;
}) {
  return (
    <button className={`btn btn-${variant} ${className}`} disabled={loading || props.disabled} {...props}>
      {loading ? <span className="btn-spinner" /> : null}
      {children}
    </button>
  );
}

export function Field({
  label,
  hint,
  error,
  children,
  htmlFor,
}: {
  label: string;
  hint?: string;
  error?: string;
  children: ReactNode;
  htmlFor?: string;
}) {
  return (
    <div className="field">
      <label htmlFor={htmlFor}>{label}</label>
      {children}
      {hint ? <span className="hint">{hint}</span> : null}
      {error ? <span className="field-error">{error}</span> : null}
    </div>
  );
}

export function TextInput(props: InputHTMLAttributes<HTMLInputElement>) {
  return <input {...props} className={`input ${props.className ?? ""}`} />;
}

export function SelectInput(props: SelectHTMLAttributes<HTMLSelectElement>) {
  return <select {...props} className={`input ${props.className ?? ""}`} />;
}

export function Badge({ tone = "neutral", children }: { tone?: string; children: ReactNode }) {
  return <span className={`badge badge-${tone}`}>{children}</span>;
}

export function StatCard({
  label,
  value,
  hint,
  tone = "green",
}: {
  label: string;
  value: ReactNode;
  hint?: string;
  tone?: "green" | "gold" | "blue" | "red";
}) {
  return (
    <div className={`stat-card stat-${tone}`}>
      <span className="stat-label">{label}</span>
      <strong>{value}</strong>
      {hint ? <span className="stat-hint">{hint}</span> : null}
    </div>
  );
}

export function Modal({
  open,
  title,
  onClose,
  children,
  footer,
  wide = false,
}: {
  open: boolean;
  title: string;
  onClose: () => void;
  children: ReactNode;
  footer?: ReactNode;
  wide?: boolean;
}) {
  if (!open) return null;
  return (
    <div className="modal-backdrop" onMouseDown={onClose}>
      <div
        className={`modal ${wide ? "modal-wide" : ""}`}
        onMouseDown={(event) => event.stopPropagation()}
        role="dialog"
        aria-modal="true"
      >
        <div className="modal-head">
          <h2>{title}</h2>
          <button className="icon-btn" onClick={onClose} aria-label="Kapat">
            ×
          </button>
        </div>
        <div className="modal-body">{children}</div>
        {footer ? <div className="modal-footer">{footer}</div> : null}
      </div>
    </div>
  );
}

export function Spinner({ label = "Getiriliyor" }: { label?: string }) {
  return (
    <div className="spinner-wrap">
      <span className="spinner" />
      <span>{label}</span>
    </div>
  );
}

export function EmptyState({
  title,
  body,
  action,
  icon = "◇",
}: {
  title: string;
  body: string;
  action?: ReactNode;
  icon?: string;
}) {
  return (
    <div className="empty-state">
      <div className="empty-icon">{icon}</div>
      <h3>{title}</h3>
      <p>{body}</p>
      {action}
    </div>
  );
}

export function ErrorBanner({ message, onClose }: { message: string; onClose?: () => void }) {
  return (
    <div className="error-banner">
      <span>{message}</span>
      {onClose ? (
        <button onClick={onClose} aria-label="Kapat">
          ×
        </button>
      ) : null}
    </div>
  );
}

export function PageHeader({
  eyebrow,
  title,
  description,
  actions,
}: {
  eyebrow?: string;
  title: string;
  description?: string;
  actions?: ReactNode;
}) {
  return (
    <div className="page-header">
      <div>
        {eyebrow ? <span className="eyebrow">{eyebrow}</span> : null}
        <h1>{title}</h1>
        {description ? <p>{description}</p> : null}
      </div>
      {actions ? <div className="page-actions">{actions}</div> : null}
    </div>
  );
}
