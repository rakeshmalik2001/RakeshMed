"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import { DegradedState } from "@/components/degraded-state";
import { LoadingPanel } from "@/components/loading-panel";
import { fetchOrders, getStoredAuthToken, type ApiOrder } from "@/lib/api";

import styles from "./page.module.css";

function formatCurrency(value: string) {
  const amount = Number.parseFloat(value);

  if (Number.isNaN(amount)) {
    return value;
  }

  return amount.toFixed(2);
}

function formatStatus(value: string) {
  return value.replace(/_/g, " ");
}

function formatDate(value: string) {
  try {
    return new Intl.DateTimeFormat("en-IN", {
      day: "2-digit",
      month: "short",
      year: "numeric",
      hour: "numeric",
      minute: "2-digit"
    }).format(new Date(value));
  } catch {
    return value;
  }
}

export default function OrdersPage() {
  const [orders, setOrders] = useState<ApiOrder[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const isAuthenticated = Boolean(getStoredAuthToken());

  useEffect(() => {
    if (!isAuthenticated) {
      setIsLoading(false);
      return;
    }

    void fetchOrders()
      .then((data) => {
        setOrders(data);
        setError(null);
      })
      .catch((fetchError: Error) => {
        setError(fetchError.message);
      })
      .finally(() => {
        setIsLoading(false);
      });
  }, [isAuthenticated]);

  const orderStats = useMemo(
    () => [
      {
        label: "Total orders",
        value: orders.length
      },
      {
        label: "Confirmed",
        value: orders.filter((order) => order.status === "confirmed").length
      },
      {
        label: "Under review",
        value: orders.filter((order) => order.status === "pending_prescription_review").length
      },
      {
        label: "Cancelled",
        value: orders.filter((order) => order.status === "cancelled").length
      }
    ],
    [orders]
  );

  return (
    <main className={`page-shell ${styles.ordersPage}`}>
      <div className={`breadcrumb ${styles.breadcrumb}`}>Home / Account / Orders</div>

      <section className={`soft-section ${styles.ordersShell}`}>
        <div className={styles.heroHeader}>
          <div>
            <p className="eyebrow">Account</p>
            <h1 className={`page-title ${styles.heroTitle}`}>Order history</h1>
            <p className={styles.heroCopy}>
              Review every order in one place, including payment status, delivery progress, prescription dependencies,
              and the next action you might need to take.
            </p>
          </div>
          <div className={styles.heroActions}>
            <Link href="/search" className={styles.primaryAction}>
              Search medicines
            </Link>
            <Link href="/account" className={styles.secondaryAction}>
              Back to account
            </Link>
          </div>
        </div>

        {!isAuthenticated ? (
          <div className="empty-cart-box">
            <h2>Login to view your orders</h2>
            <p>Your placed orders, prescription review status, and totals will appear here after OTP login.</p>
            <div className="success-actions">
              <Link href="/login" className="primary-action">
                Login
              </Link>
              <Link href="/search" className="secondary-action">
                Browse medicines
              </Link>
            </div>
          </div>
        ) : isLoading ? (
          <LoadingPanel
            title="Loading your orders"
            description="Fetching placed orders, delivery states, payment progress, and prescription flags."
          />
        ) : error ? (
          <DegradedState
            title="Could not load order history"
            description={error}
            onRetry={() => {
              setIsLoading(true);
              setError(null);
              void fetchOrders()
                .then((data) => {
                  setOrders(data);
                  setError(null);
                })
                .catch((fetchError: Error) => {
                  setError(fetchError.message);
                })
                .finally(() => {
                  setIsLoading(false);
                });
            }}
            secondaryHref="/search"
            secondaryLabel="Browse medicines"
          />
        ) : orders.length === 0 ? (
          <div className="empty-cart-box">
            <h2>No orders yet</h2>
            <p>Once you place an order through checkout, it will appear here with status, payment progress, and details.</p>
            <div className="success-actions">
              <Link href="/search" className="primary-action">
                Search medicines
              </Link>
              <Link href="/categories" className="secondary-action">
                Browse categories
              </Link>
            </div>
          </div>
        ) : (
          <>
            <div className={styles.statsGrid}>
              {orderStats.map((stat) => (
                <article key={stat.label} className={styles.statCard}>
                  <p>{stat.label}</p>
                  <strong>{stat.value}</strong>
                </article>
              ))}
            </div>

            <div className={styles.orderList}>
              {orders.map((order) => {
                const itemCount = order.items.reduce((sum, item) => sum + item.qty, 0);
                const deliveryState = order.delivery_shipment?.status || order.fulfillment_status;

                return (
                  <article key={order.order_number} className={styles.orderCard}>
                    <div className={styles.orderHead}>
                      <div>
                        <p className={styles.orderEyebrow}>Order</p>
                        <h2>{order.order_number}</h2>
                        <p className={styles.orderMeta}>Placed on {formatDate(order.created_at)}</p>
                      </div>
                      <Link href={`/account/orders/${order.order_number}`} className={styles.inlineLink}>
                        View details
                      </Link>
                    </div>

                    <div className={styles.badgeRow}>
                      <span className={styles.statusBadge}>{formatStatus(order.status)}</span>
                      <span className={styles.infoBadge}>Payment: {formatStatus(order.payment_status)}</span>
                      <span className={styles.infoBadge}>Delivery: {formatStatus(deliveryState)}</span>
                    </div>

                    <div className={styles.orderGrid}>
                      <div className={styles.infoCard}>
                        <span>Items</span>
                        <strong>{itemCount}</strong>
                      </div>
                      <div className={styles.infoCard}>
                        <span>Total</span>
                        <strong>Rs. {formatCurrency(order.total)}</strong>
                      </div>
                      <div className={styles.infoCard}>
                        <span>Payment method</span>
                        <strong>{order.payment_method}</strong>
                      </div>
                      <div className={styles.infoCard}>
                        <span>Prescription review</span>
                        <strong>{order.requires_prescription_count > 0 ? `${order.requires_prescription_count} item(s)` : "Not needed"}</strong>
                      </div>
                    </div>

                    <div className={styles.orderFooter}>
                      <div>
                        <span>Tracking / ETA</span>
                        <strong>
                          {order.delivery_shipment?.eta_label || "ETA pending"}
                          {order.tracking_reference ? ` | ${order.tracking_reference}` : ""}
                        </strong>
                      </div>
                      {order.delivery_shipment?.next_attempt_at ? (
                        <div>
                          <span>Next attempt</span>
                          <strong>{formatDate(order.delivery_shipment.next_attempt_at)}</strong>
                        </div>
                      ) : null}
                    </div>
                  </article>
                );
              })}
            </div>
          </>
        )}
      </section>
    </main>
  );
}
