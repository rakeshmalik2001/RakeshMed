"use client";

import type { Route } from "next";
import Link from "next/link";

type DegradedStateProps = {
  title: string;
  description: string;
  actionLabel?: string;
  actionHref?: Route;
  onRetry?: () => void;
  secondaryLabel?: string;
  secondaryHref?: Route;
};

export function DegradedState({
  title,
  description,
  actionLabel = "Try again",
  actionHref,
  onRetry,
  secondaryLabel,
  secondaryHref
}: DegradedStateProps) {
  return (
    <div className="empty-cart-box degraded-state">
      <h2>{title}</h2>
      <p>{description}</p>
      <div className="success-actions">
        {onRetry ? (
          <button type="button" className="primary-action" onClick={onRetry}>
            {actionLabel}
          </button>
        ) : actionHref ? (
          <Link href={actionHref} className="primary-action">
            {actionLabel}
          </Link>
        ) : null}
        {secondaryHref && secondaryLabel ? (
          <Link href={secondaryHref} className="secondary-action">
            {secondaryLabel}
          </Link>
        ) : null}
      </div>
    </div>
  );
}
