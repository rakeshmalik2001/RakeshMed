"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import {
  fetchAdminSettlementBatches,
  getStoredAuthToken,
  getStoredAuthUser,
  type ApiSettlementBatch
} from "@/lib/api";

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

export default function AdminSettlementsPage() {
  const [batches, setBatches] = useState<ApiSettlementBatch[]>([]);
  const [providerFilter, setProviderFilter] = useState("");
  const [fromFilter, setFromFilter] = useState("");
  const [toFilter, setToFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState<"" | "draft" | "processing" | "closed">("");
  const [isLoading, setIsLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState("");
  const isAuthenticated = Boolean(getStoredAuthToken());
  const role = getStoredAuthUser()?.role;
  const visibleBatches = statusFilter ? batches.filter((batch) => batch.status === statusFilter) : batches;
  const totalNet = visibleBatches.reduce((sum, batch) => sum + Number.parseFloat(batch.total_net || "0"), 0);
  const draftCount = visibleBatches.filter((batch) => batch.status === "draft").length;
  const processingCount = visibleBatches.filter((batch) => batch.status === "processing").length;
  const closedCount = visibleBatches.filter((batch) => batch.status === "closed").length;

  useEffect(() => {
    if (!isAuthenticated) {
      setIsLoading(false);
      return;
    }

    setIsLoading(true);
    void fetchAdminSettlementBatches({
      provider: providerFilter || undefined,
      from: fromFilter || undefined,
      to: toFilter || undefined
    })
      .then((data) => {
        setBatches(data);
        setErrorMessage("");
      })
      .catch((error: Error) => setErrorMessage(error.message))
      .finally(() => setIsLoading(false));
  }, [fromFilter, isAuthenticated, providerFilter, toFilter]);

  if (!isAuthenticated) {
    return (
      <div className="empty-cart-box">
        <h2>Login required</h2>
        <p>Settlement history is available only after authenticated finance or admin login.</p>
      </div>
    );
  }

  if (role !== "admin" && role !== "finance") {
    return (
      <div className="empty-cart-box">
        <h2>Permission required</h2>
        <p>Your current account does not have settlement access.</p>
      </div>
    );
  }

  return (
    <section className="soft-section">
      <div className="section-title-row">
        <div>
          <p className="eyebrow">Finance</p>
          <h1 className="page-title">Settlement batches</h1>
        </div>
        <Link href="/admin/reconciliation" className="section-link">
          Back to reconciliation
        </Link>
      </div>

      {errorMessage ? <p className="auth-error">{errorMessage}</p> : null}

      <div className="review-grid">
        <article className="review-card wide">
          <h3>Filters</h3>
          <div className="rx-form-grid">
            <label className="rx-field">
              <span>Provider</span>
              <input value={providerFilter} onChange={(event) => setProviderFilter(event.target.value)} placeholder="Gateway name" />
            </label>
            <label className="rx-field">
              <span>From</span>
              <input type="datetime-local" value={fromFilter} onChange={(event) => setFromFilter(event.target.value)} />
            </label>
            <label className="rx-field">
              <span>To</span>
              <input type="datetime-local" value={toFilter} onChange={(event) => setToFilter(event.target.value)} />
            </label>
            <label className="rx-field">
              <span>Status</span>
              <select value={statusFilter} onChange={(event) => setStatusFilter(event.target.value as "" | "draft" | "processing" | "closed")}>
                <option value="">All statuses</option>
                <option value="draft">Draft</option>
                <option value="processing">Processing</option>
                <option value="closed">Closed</option>
              </select>
            </label>
          </div>
        </article>

        {!isLoading ? (
          <>
            <article className="review-card">
              <h3>Visible batches</h3>
              <p>{visibleBatches.length}</p>
            </article>
            <article className="review-card">
              <h3>Draft</h3>
              <p>{draftCount}</p>
            </article>
            <article className="review-card">
              <h3>Processing</h3>
              <p>{processingCount}</p>
            </article>
            <article className="review-card">
              <h3>Closed</h3>
              <p>{closedCount}</p>
            </article>
            <article className="review-card wide">
              <h3>Net closeout value</h3>
              <p>Rs. {totalNet.toFixed(2)}</p>
            </article>
          </>
        ) : null}

        {isLoading ? (
          <article className="review-card wide">
            <h3>Loading settlements</h3>
            <p>Fetching closed payout batches and refund offsets.</p>
          </article>
        ) : visibleBatches.length === 0 ? (
          <article className="review-card wide">
            <h3>No settlement batches yet</h3>
            <p>Create a settlement batch from reconciliation to start tracking payout closeouts here.</p>
          </article>
        ) : (
          visibleBatches.map((batch) => (
            <article key={batch.id} className="review-card wide">
              <div className="section-title-row">
                <div>
                  <h3>{batch.batch_reference}</h3>
                  <p>{batch.provider} | {batch.entries.length} item(s)</p>
                </div>
                <Link href={`/admin/settlements/${batch.id}`} className="section-link">
                  Open detail
                </Link>
              </div>

              <div className="review-item">
                <span>Settlement window</span>
                <strong>{formatDate(batch.period_start)} to {formatDate(batch.period_end)}</strong>
              </div>
              <div className="review-item">
                <span>Captured</span>
                <strong>Rs. {batch.total_captured}</strong>
              </div>
              <div className="review-item">
                <span>Refunded</span>
                <strong>Rs. {batch.total_refunded}</strong>
              </div>
              <div className="review-item">
                <span>Net settled</span>
                <strong>Rs. {batch.total_net}</strong>
              </div>
              <div className="review-item">
                <span>Status</span>
                <strong>{batch.status.replace(/_/g, " ")}</strong>
              </div>
              <div className="review-item">
                <span>Created</span>
                <strong>{formatDate(batch.created_at)}</strong>
              </div>
            </article>
          ))
        )}
      </div>
    </section>
  );
}
