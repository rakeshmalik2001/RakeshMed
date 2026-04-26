"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { RoleDashboardView } from "@/components/role-dashboard-view";
import {
  fetchAdminSummary,
  getStoredAuthToken,
  getStoredAuthUser,
  type ApiAdminSummary
} from "@/lib/api";
import { getRoleDashboardConfig } from "@/lib/role-dashboard";

function formatCurrency(value: string) {
  const amount = Number.parseFloat(value);
  return Number.isNaN(amount) ? value : amount.toFixed(2);
}

export default function AdminDashboardPage() {
  const [summary, setSummary] = useState<ApiAdminSummary | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState("");
  const isAuthenticated = Boolean(getStoredAuthToken());
  const role = getStoredAuthUser()?.role;
  const config = getRoleDashboardConfig(role);

  useEffect(() => {
    if (!isAuthenticated) {
      setIsLoading(false);
      return;
    }

    void fetchAdminSummary()
      .then((data) => {
        setSummary(data);
        setErrorMessage("");
      })
      .catch((error: Error) => setErrorMessage(error.message))
      .finally(() => setIsLoading(false));
  }, [isAuthenticated]);

  if (!isAuthenticated) {
    return (
      <div className="empty-cart-box">
        <h2>Login required</h2>
        <p>Admin metrics are available only after authenticated admin login.</p>
      </div>
    );
  }

  if (role !== "admin" && role !== "catalog_manager" && role !== "finance" && role !== "support_agent" && role !== "warehouse_operator") {
    return (
      <div className="empty-cart-box">
        <h2>Permission required</h2>
        <p>Your current account does not have admin dashboard access.</p>
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="empty-cart-box">
        <h2>Loading dashboard metrics</h2>
        <p>Fetching orders, revenue, customer, and prescription queue counts.</p>
      </div>
    );
  }

  if (errorMessage || !summary) {
    return (
      <div className="empty-cart-box">
        <h2>Could not load dashboard</h2>
        <p>{errorMessage || "Summary unavailable."}</p>
      </div>
    );
  }

  return (
    <>
      {config ? (
        <RoleDashboardView
          config={{
            ...config,
            summaryCards: [
              { label: "Orders", value: `${summary.total_orders} total`, meta: `${summary.today_orders} placed today` },
              { label: "Revenue", value: `Rs. ${formatCurrency(summary.total_revenue)}`, meta: "Across confirmed and newly placed orders" },
              { label: "Prescription queue", value: `${summary.pending_prescription_review} pending`, meta: "Includes clarification-required cases" },
              { label: "Inventory risk", value: `${summary.low_stock_products} low stock`, meta: `${summary.out_of_stock_products} out of stock` }
            ]
          }}
        >
          <section className="section-grid role-dashboard-panels">
            <article className="card">
              <p className="eyebrow">Customer Base</p>
              <h3>{summary.customers} active customer accounts in the current operating view</h3>
              <p>{summary.saved_addresses} saved addresses and {summary.saved_payment_methods} saved payment methods are currently on file.</p>
            </article>
            <article className="card">
              <p className="eyebrow">Fulfillment Pulse</p>
              <h3>{summary.queued_fulfillment_orders} queued or packed orders need continued fulfillment attention</h3>
              <p>{summary.shipped_orders} orders are already shipped, while {summary.dispatch_ready_shipments} shipments are ready to dispatch.</p>
            </article>
            <article className="card">
              <p className="eyebrow">Delivery Risk</p>
              <h3>{summary.delivery_failed} failed attempts, {summary.delivery_returned} returns, and {summary.delivery_reattempt_due} reattempts due</h3>
              <p>{summary.delivery_in_transit} shipments are in transit and {summary.delivery_sla_breached} are beyond ETA.</p>
            </article>
          </section>
        </RoleDashboardView>
      ) : null}

      <div className="stats-grid">
        <div className="stat">
          <p className="eyebrow">Orders</p>
          <strong>{summary.total_orders} total</strong>
          <span>{summary.today_orders} placed today</span>
        </div>
        <div className="stat">
          <p className="eyebrow">Revenue</p>
          <strong>Rs. {formatCurrency(summary.total_revenue)}</strong>
          <span>Across confirmed and newly placed orders</span>
        </div>
        <div className="stat">
          <p className="eyebrow">Prescription Queue</p>
          <strong>{summary.pending_prescription_review} pending review</strong>
          <span>Includes clarification-required cases</span>
        </div>
        <div className="stat">
          <p className="eyebrow">Customers</p>
          <strong>{summary.customers}</strong>
          <span>{summary.saved_addresses} saved addresses</span>
        </div>
        <div className="stat">
          <p className="eyebrow">Inventory Risk</p>
          <strong>{summary.low_stock_products} low stock</strong>
          <span>{summary.out_of_stock_products} out of stock</span>
        </div>
        <div className="stat">
          <p className="eyebrow">Fulfillment</p>
          <strong>{summary.queued_fulfillment_orders} queued or packed</strong>
          <span>{summary.shipped_orders} already shipped</span>
        </div>
        <div className="stat">
          <p className="eyebrow">Dispatch Queue</p>
          <strong>{summary.dispatch_ready_shipments} ready to dispatch</strong>
          <span>{summary.delivery_in_transit} in transit now</span>
        </div>
        <div className="stat">
          <p className="eyebrow">Delivery Exceptions</p>
          <strong>{summary.delivery_failed} failed attempts</strong>
          <span>{summary.delivery_returned} returns / RTO</span>
        </div>
        <div className="stat">
          <p className="eyebrow">SLA Watch</p>
          <strong>{summary.delivery_reattempt_due} reattempts due</strong>
          <span>{summary.delivery_sla_breached} shipments beyond ETA</span>
        </div>
      </div>

      <div className="section-grid" style={{ marginTop: 24 }}>
        <article className="card">
          <p className="eyebrow">Catalog Health</p>
          <h3>{summary.catalog_products} live products ready for browse and search</h3>
          <p>{summary.saved_payment_methods} saved payment methods across customer accounts.</p>
        </article>

        <article className="card">
          <p className="eyebrow">Operational Focus</p>
          <h3>Prioritize dispatch-ready orders, stock alerts, delivery exceptions, and pharmacist review throughput.</h3>
          <p>Use these metrics to validate the live backend-driven flows across storefront, warehouse, dispatch, and operations.</p>
        </article>
      </div>

      <section className="soft-section" style={{ marginTop: 24 }}>
        <div className="section-title-row">
          <div>
            <p className="eyebrow">Recent Orders</p>
            <h2>Latest placed orders</h2>
          </div>
          <Link href="/account/orders" className="section-link">
            View customer order history
          </Link>
        </div>

        <div className="review-grid">
          {summary.recent_orders.map((order) => (
            <article key={order.order_number} className="review-card">
              <h3>{order.order_number}</h3>
              <p>{order.recipient}</p>
              <div className="review-item">
                <span>Status</span>
                <strong>{order.status.replace(/_/g, " ")}</strong>
              </div>
              <div className="review-item">
                <span>Total</span>
                <strong>Rs. {formatCurrency(order.total)}</strong>
              </div>
            </article>
          ))}
        </div>
      </section>
    </>
  );
}
