import type { Route } from "next";
import Link from "next/link";
import { FiAlertTriangle, FiCheckCircle, FiClock, FiFileText } from "react-icons/fi";

type PrescriptionStatusCardProps = {
  status: "submitted" | "pending" | "approved" | "rejected";
  title: string;
  description: string;
  primaryHref: Route;
  primaryLabel: string;
  secondaryHref?: Route;
  secondaryLabel?: string;
  meta?: Array<{ label: string; value: string }>;
  highlights?: string[];
};

export function PrescriptionStatusCard({
  status,
  title,
  description,
  primaryHref,
  primaryLabel,
  secondaryHref,
  secondaryLabel,
  meta = [],
  highlights = []
}: PrescriptionStatusCardProps) {
  const statusConfig = {
    approved: {
      label: "Approved",
      Icon: FiCheckCircle,
      summary: "Eligible medicines are cleared for checkout."
    },
    rejected: {
      label: "Rejected",
      Icon: FiAlertTriangle,
      summary: "A clearer file or valid prescription is needed."
    },
    pending: {
      label: "In review",
      Icon: FiClock,
      summary: "Pharmacist verification is currently in progress."
    },
    submitted: {
      label: "Submitted",
      Icon: FiFileText,
      summary: "Your files are queued for pharmacist triage."
    }
  }[status];

  return (
    <section className={`rx-status-card ${status}`}>
      <div className="rx-status-icon" aria-label={statusConfig.label}>
        <statusConfig.Icon />
      </div>
      <span className="small-pill rx-status-pill">{statusConfig.label}</span>
      <h1>{title}</h1>
      <p>{description}</p>
      <div className="rx-status-summary">{statusConfig.summary}</div>
      {meta.length > 0 ? (
        <div className="rx-status-meta-grid">
          {meta.map((item) => (
            <article key={item.label} className="rx-status-meta-card">
              <span>{item.label}</span>
              <strong>{item.value}</strong>
            </article>
          ))}
        </div>
      ) : null}
      {highlights.length > 0 ? (
        <div className="rx-status-list">
          {highlights.map((item) => (
            <article key={item} className="rx-status-list-item">
              <span className="rx-status-list-dot" aria-hidden="true" />
              <p>{item}</p>
            </article>
          ))}
        </div>
      ) : null}
      <div className="success-actions">
        <Link href={primaryHref} className="primary-action">
          {primaryLabel}
        </Link>
        {secondaryHref && secondaryLabel ? (
          <Link href={secondaryHref} className="secondary-action">
            {secondaryLabel}
          </Link>
        ) : null}
      </div>
    </section>
  );
}
