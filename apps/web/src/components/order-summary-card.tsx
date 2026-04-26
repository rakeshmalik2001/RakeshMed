"use client";

import type { Route } from "next";
import Link from "next/link";

import { useCart } from "@/components/cart-provider";

type OrderSummaryCardProps = {
  title?: string;
  ctaLabel?: string;
  ctaHref?: Route;
  helperText?: string;
  onCta?: () => void;
  ctaDisabled?: boolean;
};

export function OrderSummaryCard({
  title = "Order Summary",
  ctaLabel = "Proceed",
  ctaHref,
  helperText,
  onCta,
  ctaDisabled = false
}: OrderSummaryCardProps) {
  const { itemCount, subtotal, discount, delivery, total, requiresPrescriptionCount } = useCart();
  const canContinue = itemCount > 0 && !ctaDisabled;

  return (
    <aside className="summary-card sticky-summary">
      <h3>{title}</h3>
      <div className="summary-lines">
        <div className="summary-row">
          <span>Subtotal</span>
          <strong>Rs. {subtotal.toFixed(2)}</strong>
        </div>
        <div className="summary-row">
          <span>Discount</span>
          <strong className="positive">- Rs. {discount.toFixed(2)}</strong>
        </div>
        <div className="summary-row">
          <span>Delivery</span>
          <strong>Rs. {delivery.toFixed(2)}</strong>
        </div>
        <div className="summary-row">
          <span>Prescription review</span>
          <strong>{requiresPrescriptionCount > 0 ? `${requiresPrescriptionCount} item(s)` : "Not needed"}</strong>
        </div>
        <div className="summary-row">
          <span>Cart items</span>
          <strong>{itemCount}</strong>
        </div>
      </div>
      <div className="summary-total">
        <span>Total</span>
        <strong>Rs. {total.toFixed(2)}</strong>
      </div>
      {helperText ? <p className="summary-helper-text">{helperText}</p> : null}
      {onCta && canContinue ? (
        <button data-testid="summary-cta-button" type="button" className="primary-action summary-button" onClick={onCta}>
          {ctaLabel}
        </button>
      ) : ctaHref && canContinue ? (
        <Link href={ctaHref} className="primary-action summary-button" data-testid="summary-cta-link">
          {ctaLabel}
        </Link>
      ) : (
        <button data-testid="summary-cta-disabled" type="button" className="primary-action summary-button" disabled>
          {itemCount > 0 ? ctaLabel : "Add items to continue"}
        </button>
      )}
    </aside>
  );
}
