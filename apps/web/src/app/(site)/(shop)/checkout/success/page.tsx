"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { useCart } from "@/components/cart-provider";
import { CheckoutStepper } from "@/components/checkout-stepper";
import { useAuthSession } from "@/hooks/use-auth-session";
import { useOrderRefresh } from "@/hooks/use-order-refresh";
import { fetchOrderById, type ApiOrder } from "@/lib/api";
import {
  formatOrderStatusLabel,
  getPaymentStatusDescription,
  getPaymentStatusLabel,
  isOrderAwaitingPaymentUpdate
} from "@/lib/order-status";

export default function CheckoutSuccessPage() {
  const { addresses, lastOrder, syncLastOrderFromApi } = useCart();
  const { isAuthenticated } = useAuthSession();
  const [liveOrder, setLiveOrder] = useState<ApiOrder | null>(null);
  const selectedAddress = addresses.find((address) => address.id === lastOrder?.addressId) ?? addresses[0];
  const resolvedOrderId = liveOrder?.order_number ?? lastOrder?.id ?? null;
  const resolvedAddressLabel = liveOrder?.address_label ?? lastOrder?.addressLabel ?? null;
  const resolvedPaymentMethod = liveOrder?.payment_method ?? lastOrder?.paymentMethod ?? null;
  const resolvedPaymentStatus = liveOrder?.payment_status ?? lastOrder?.paymentStatus ?? null;
  const resolvedItemCount =
    liveOrder?.items.reduce((sum, item) => sum + item.qty, 0) ?? lastOrder?.itemCount ?? 0;
  const resolvedTotal = liveOrder ? Number(liveOrder.total) : lastOrder?.total ?? 0;
  const resolvedRequiresPrescriptionCount =
    liveOrder?.requires_prescription_count ?? lastOrder?.requiresPrescriptionCount ?? 0;
  const resolvedStatus = liveOrder?.status ?? lastOrder?.status ?? "placed";
  const deliveryLabel = selectedAddress
    ? `${resolvedAddressLabel ?? selectedAddress.label}, ${selectedAddress.city}`
    : resolvedAddressLabel ?? "Add an address in your account";
  const paymentLabel = liveOrder
    ? getPaymentStatusLabel(liveOrder.payment_method, liveOrder.payment_status)
    : resolvedPaymentMethod && resolvedPaymentStatus
      ? getPaymentStatusLabel(resolvedPaymentMethod, resolvedPaymentStatus)
      : "Payment status pending";
  const isPaymentPending =
    liveOrder
      ? isOrderAwaitingPaymentUpdate(liveOrder)
      : resolvedPaymentMethod && resolvedPaymentStatus
        ? resolvedPaymentMethod !== "COD" &&
          resolvedPaymentStatus !== "paid" &&
          resolvedStatus !== "cancelled"
        : false;
  const heading =
    resolvedPaymentStatus === "failed"
      ? "Your order needs a fresh payment attempt"
      : isPaymentPending
        ? "Your order is placed and payment is still being confirmed"
        : "Your order has been placed successfully";
  const badgeLabel =
    resolvedPaymentStatus === "failed"
      ? "Payment attention needed"
      : isPaymentPending
        ? "Order placed"
        : "Order confirmed";

  useEffect(() => {
    if (!isAuthenticated || !lastOrder?.id) {
      return;
    }

    void fetchOrderById(lastOrder.id)
      .then((order) => {
        if (order) {
          setLiveOrder(order);
          syncLastOrderFromApi(order);
        }
      })
      .catch(() => {
        // keep local checkout state if order fetch fails
      });
  }, [isAuthenticated, lastOrder?.id, syncLastOrderFromApi]);

  const { isRefreshing, lastCheckedAt } = useOrderRefresh({
    enabled: isAuthenticated && Boolean(liveOrder) && isOrderAwaitingPaymentUpdate(liveOrder),
    orderId: lastOrder?.id ?? "",
    onUpdate: (order) => {
      setLiveOrder(order);
      syncLastOrderFromApi(order);
    }
  });

  return (
    <main className="page-shell">
      <div className="breadcrumb">Home / Checkout / Success</div>
      <CheckoutStepper current="success" />

      <section className="success-shell">
        <div className="success-badge" data-testid="checkout-success-badge">{badgeLabel}</div>
        <h1>{heading}</h1>
        <p>
          Order ID `{resolvedOrderId ?? "TC-PENDING"}` is recorded. Prescription review and delivery
          updates will continue to appear in your account and notifications.
        </p>
        {isPaymentPending ? (
          <p data-testid="checkout-success-payment-note">
            {isRefreshing
              ? "We are checking for a gateway update right now."
              : "We keep checking this order for payment updates automatically every 10 seconds."}
            {lastCheckedAt
              ? ` Last checked at ${new Date(lastCheckedAt).toLocaleTimeString("en-IN", {
                  hour: "numeric",
                  minute: "2-digit"
                })}.`
              : ""}
            {" "}Open order details if you need to retry or inspect the payment link.
          </p>
        ) : null}

        <div className="success-summary-grid">
          <div className="success-card">
            <strong>Expected delivery</strong>
            <span>Tomorrow, 6 PM - 9 PM</span>
          </div>
          <div className="success-card">
            <strong>Payment</strong>
            <span>{paymentLabel}</span>
          </div>
          <div className="success-card">
            <strong>Payment note</strong>
            <span>
              {liveOrder
                ? getPaymentStatusDescription(liveOrder)
                : resolvedPaymentMethod && resolvedPaymentStatus
                  ? getPaymentStatusDescription({
                      payment_method: resolvedPaymentMethod,
                      payment_status: resolvedPaymentStatus,
                      status: resolvedStatus
                    })
                  : "Payment details will appear here once the order is available."}
            </span>
          </div>
          <div className="success-card">
            <strong>Prescription review</strong>
            <span>
              {resolvedRequiresPrescriptionCount > 0
                ? `${resolvedRequiresPrescriptionCount} medicine(s) pending pharmacist verification`
                : "No prescription review pending"}
            </span>
          </div>
          <div className="success-card">
            <strong>Delivering to</strong>
            <span>{deliveryLabel}</span>
          </div>
          <div className="success-card">
            <strong>Items confirmed</strong>
            <span>{resolvedItemCount} item(s)</span>
          </div>
          <div className="success-card">
            <strong>Amount payable</strong>
            <span>Rs. {resolvedTotal.toFixed(2)}</span>
          </div>
          <div className="success-card">
            <strong>Order status</strong>
            <span>{formatOrderStatusLabel(resolvedStatus)}</span>
          </div>
        </div>

        <div className="success-actions">
          <Link
            href={resolvedOrderId ? `/account/orders/${resolvedOrderId}` : "/account/orders"}
            className="primary-action"
            data-testid="checkout-success-primary-action"
          >
            {isPaymentPending ? "Open order details" : "View order"}
          </Link>
          <Link href="/categories" className="secondary-action">
            Continue shopping
          </Link>
        </div>
      </section>
    </main>
  );
}
