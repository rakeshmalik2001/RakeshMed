import type { Route } from "next";
import Link from "next/link";
import { ReactNode } from "react";

type DashboardShellProps = {
  title: string;
  description: string;
  nav: readonly { href: string; label: string }[];
  children: ReactNode;
};

export function DashboardShell({
  title,
  description,
  nav,
  children
}: DashboardShellProps) {
  return (
    <section className="page-shell">
      <div className="sidebar-layout">
        <aside>
          <p className="eyebrow">Workspace</p>
          <h2>{title}</h2>
          <p>{description}</p>
          <div className="nav-links" style={{ marginTop: 16 }}>
            {nav.map((link) => (
              <Link key={link.href} href={link.href as Route} className="nav-link">
                {link.label}
              </Link>
            ))}
          </div>
        </aside>
        <main>{children}</main>
      </div>
    </section>
  );
}
