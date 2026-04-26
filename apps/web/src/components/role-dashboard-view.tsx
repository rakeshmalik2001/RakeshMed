import type { ReactNode } from "react";
import Link from "next/link";

import type { RoleDashboardConfig } from "@/lib/role-dashboard";

type RoleDashboardViewProps = {
  config: RoleDashboardConfig;
  children?: ReactNode;
};

export function RoleDashboardView({ config, children }: RoleDashboardViewProps) {
  return (
    <div className="role-dashboard-shell">
      <section className="role-dashboard-hero">
        <div className="role-dashboard-copy">
          <p className="eyebrow">{config.eyebrow}</p>
          <h1 className="page-title">{config.title}</h1>
          <p>{config.intro}</p>
        </div>
        <div className="role-dashboard-hero-card">
          <p className="eyebrow">Operating Lens</p>
          <ul className="role-dashboard-streams">
            {config.workstreams.map((stream) => (
              <li key={stream}>{stream}</li>
            ))}
          </ul>
        </div>
      </section>

      <section className="stats-grid">
        {config.summaryCards.map((card) => (
          <article key={card.label} className="stat role-dashboard-stat">
            <p className="eyebrow">{card.label}</p>
            <strong>{card.value}</strong>
            <span>{card.meta}</span>
          </article>
        ))}
      </section>

      {children}

      <section className="section-grid role-dashboard-panels">
        {config.panels.map((panel) => (
          <article key={panel.title} className="card">
            <p className="eyebrow">Workspace Panel</p>
            <h3>{panel.title}</h3>
            <p>{panel.body}</p>
            {panel.href && panel.hrefLabel ? (
              <Link href={panel.href} className="section-link">
                {panel.hrefLabel}
              </Link>
            ) : null}
          </article>
        ))}
      </section>
    </div>
  );
}
