"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import {
  fetchAdminPayments,
  getStoredAuthToken,
  getStoredAuthUser,
  type ApiAdminPaymentAttempt
} from "@/lib/api";

type PaymentFilter = "" | "created" | "pending" | "authorized" | "captured" | "refunded" | "failed";

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

export default function AdminPaymentsPage() {
  const [payments, setPayments] = useState<ApiAdminPaymentAttempt[]>([]);
  const [filter, setFilter] = useState<PaymentFilter>("");
  const [isLoading, setIsLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState("");
  const isAuthenticated = Boolean(getStoredAuthToken());
  const role = getStoredAuthUser()?.role;

  async function loadPayments(nextFilter: PaymentFilter) {
    setIsLoading(true);
    setErrorMessage("");
    try {
      const data = await fetchAdminPayments(nextFilter);
      setPayments(data);
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Could not load payment attempts.");
    } finally {
      setIsLoading(false);
    }
  }

  useEffect(() => {
    if (!isAuthenticated) {
      setIsLoading(false);
      return;
    }

    void loadPayments(filter);
  }, [filter, isAuthenticated]);

  if (!isAuthenticated) {
    return (
      <div className="empty-cart-box">
        <h2>Login required</h2>
        <p>Admin payments are available only after authenticated admin login.</p>
      </div>
    );
  }

  if (role !== "admin" && role !== "finance" && role !== "support_agent") {
    return (
      <div className="empty-cart-box">
        <h2>Permission required</h2>
        <p>Your current account does not have payment operations access.</p>
      </div>
    );
  }

  return (
    <section className="soft-section">
      <div className="section-title-row">
        <div>
          <p className="eyebrow">Admin</p>
          <h1 className="page-title">Payment Attempts Queue</h1>
        </div>
        <div className="success-actions">
          <select value={filter} className="checkout-inline-input" onChange={(event) => setFilter(event.target.value as PaymentFilter)}>
            <option value="">All payment states</option>
            <option value="created">Created</option>
            <option value="pending">Pending</option>
            <option value="authorized">Authorized</option>
            <option value="captured">Captured</option>
            <option value="refunded">Refunded</option>
            <option value="failed">Failed</option>
          </select>
        </div>
      </div>

      {errorMessage ? <p className="auth-error">{errorMessage}</p> : null}

      {isLoading ? (
        <div className="empty-cart-box">
          <h2>Loading payments</h2>
          <p>Fetching gateway attempts for finance and support operations.</p>
        </div>
      ) : payments.length === 0 ? (
        <div className="empty-cart-box">
          <h2>No payment attempts found</h2>
          <p>Try a different filter or wait for the next real payment attempt to be recorded.</p>
        </div>
      ) : (
        <div className="review-grid">
          {payments.map((payment) => (
            <article key={payment.payment_reference} className="review-card wide">
              <div className="section-title-row">
                <div>
                  <h3>{payment.payment_reference}</h3>
                  <p>{payment.order_number} | {payment.recipient}</p>
                </div>
                <strong>{payment.status}</strong>
              </div>
              <div className="review-item">
                <span>Provider</span>
                <strong>{payment.provider}</strong>
              </div>
              <div className="review-item">
                <span>Payment amount</span>
                <strong>Rs. {payment.amount}</strong>
              </div>
              <div className="review-item">
                <span>Order state</span>
                <strong>{payment.order_status.replace(/_/g, " ")}</strong>
              </div>
              <div className="review-item">
                <span>Order payment</span>
                <strong>{payment.payment_method} / {payment.payment_status.replace(/_/g, " ")}</strong>
              </div>
              <div className="review-item">
                <span>Started</span>
                <strong>{formatDate(payment.initiated_at)}</strong>
              </div>
              <div className="success-actions">
                <Link href={`/admin/orders/${payment.order_number}`} className="primary-action">
                  Open order
                </Link>
              </div>
            </article>
          ))}
        </div>
      )}
    </section>
  );
}
