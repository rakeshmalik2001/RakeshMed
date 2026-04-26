"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import {
  createAdminSettlementBatch,
  createAdminReconciliationSnapshot,
  downloadAdminReconciliationCsvWithFilters,
  downloadAdminSettlementBatchCsv,
  fetchAdminReconciliationWithFilters,
  getStoredAuthToken,
  getStoredAuthUser,
  type ApiReconciliationSummary
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

export default function AdminReconciliationPage() {
  const [summary, setSummary] = useState<ApiReconciliationSummary | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isExporting, setIsExporting] = useState(false);
  const [isCapturing, setIsCapturing] = useState(false);
  const [isCreatingSettlement, setIsCreatingSettlement] = useState(false);
  const [snapshotNotes, setSnapshotNotes] = useState("");
  const [providerFilter, setProviderFilter] = useState("");
  const [fromFilter, setFromFilter] = useState("");
  const [toFilter, setToFilter] = useState("");
  const [errorMessage, setErrorMessage] = useState("");
  const isAuthenticated = Boolean(getStoredAuthToken());
  const role = getStoredAuthUser()?.role;

  async function loadSummary() {
    const data = await fetchAdminReconciliationWithFilters({
      provider: providerFilter,
      from: fromFilter,
      to: toFilter
    });
    setSummary(data);
  }

  useEffect(() => {
    if (!isAuthenticated) {
      setIsLoading(false);
      return;
    }

    void loadSummary()
      .catch((error: Error) => setErrorMessage(error.message))
      .finally(() => setIsLoading(false));
  }, [isAuthenticated, providerFilter, fromFilter, toFilter]);

  if (!isAuthenticated) {
    return (
      <div className="empty-cart-box">
        <h2>Login required</h2>
        <p>Reconciliation is available only after authenticated finance or admin login.</p>
      </div>
    );
  }

  if (role !== "admin" && role !== "finance") {
    return (
      <div className="empty-cart-box">
        <h2>Permission required</h2>
        <p>Your current account does not have reconciliation access.</p>
      </div>
    );
  }

  async function handleExport() {
    setIsExporting(true);
    setErrorMessage("");
    try {
      const blob = await downloadAdminReconciliationCsvWithFilters({
        provider: providerFilter,
        from: fromFilter,
        to: toFilter
      });
      const url = window.URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = "payment-reconciliation.csv";
      anchor.click();
      window.URL.revokeObjectURL(url);
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Could not export reconciliation.");
    } finally {
      setIsExporting(false);
    }
  }

  async function handleCaptureSnapshot() {
    setIsCapturing(true);
    setErrorMessage("");
    try {
      await createAdminReconciliationSnapshot(snapshotNotes);
      setSnapshotNotes("");
      await loadSummary();
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Could not capture reconciliation snapshot.");
    } finally {
      setIsCapturing(false);
    }
  }

  async function handleCreateSettlementBatch() {
    setIsCreatingSettlement(true);
    setErrorMessage("");
    try {
      await createAdminSettlementBatch({
        provider: providerFilter || undefined,
        period_start: fromFilter || undefined,
        period_end: toFilter || undefined,
        notes: snapshotNotes || undefined
      });
      await loadSummary();
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Could not create settlement batch.");
    } finally {
      setIsCreatingSettlement(false);
    }
  }

  async function handleExportSettlement(batchId: number) {
    setErrorMessage("");
    try {
      const blob = await downloadAdminSettlementBatchCsv(batchId);
      const url = window.URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = `settlement-${batchId}.csv`;
      anchor.click();
      window.URL.revokeObjectURL(url);
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Could not export settlement batch.");
    }
  }

  return (
    <section className="soft-section">
      <div className="section-title-row">
        <div>
          <p className="eyebrow">Finance</p>
          <h1 className="page-title">Payment Reconciliation</h1>
        </div>
        <div className="inline-actions">
          <button data-testid="save-reconciliation-snapshot-button" type="button" className="secondary-action" onClick={() => void handleCaptureSnapshot()} disabled={isCapturing}>
            {isCapturing ? "Capturing..." : "Save Snapshot"}
          </button>
          <button data-testid="create-settlement-button" type="button" className="secondary-action" onClick={() => void handleCreateSettlementBatch()} disabled={isCreatingSettlement}>
            {isCreatingSettlement ? "Creating..." : "Create Settlement"}
          </button>
          <button type="button" className="primary-action" onClick={() => void handleExport()} disabled={isExporting}>
            {isExporting ? "Exporting..." : "Export CSV"}
          </button>
        </div>
      </div>

      {errorMessage ? <p className="auth-error">{errorMessage}</p> : null}

      {isLoading ? (
        <div className="empty-cart-box">
          <h2>Loading reconciliation</h2>
          <p>Fetching captured totals, refunds, duplicate webhooks, and settlement mismatches.</p>
        </div>
      ) : !summary ? (
        <div className="empty-cart-box">
          <h2>No reconciliation data</h2>
          <p>Reconciliation data will appear here after live payment attempts and webhook events are recorded.</p>
        </div>
      ) : (
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
            </div>
          </article>

          <article className="review-card wide">
            <h3>Snapshot notes</h3>
            <textarea
              className="review-notes-input"
              rows={3}
              value={snapshotNotes}
              onChange={(event) => setSnapshotNotes(event.target.value)}
              placeholder="Optional note for this reconciliation checkpoint."
            />
          </article>
          <article className="review-card">
            <h3>Provider</h3>
            <p>{summary.provider}</p>
          </article>
          <article className="review-card">
            <h3>Captured total</h3>
            <p>Rs. {summary.captured_total}</p>
          </article>
          <article className="review-card">
            <h3>Refunded total</h3>
            <p>Rs. {summary.refunded_total}</p>
          </article>
          <article className="review-card">
            <h3>Pending refunds</h3>
            <p>{summary.pending_refund_count}</p>
          </article>
          <article className="review-card">
            <h3>Duplicate webhooks</h3>
            <p>{summary.duplicate_webhooks}</p>
          </article>
          <article className="review-card">
            <h3>Unmatched paid orders</h3>
            <p>{summary.unmatched_paid_orders}</p>
          </article>

          <article className="review-card wide">
            <h3>Recent webhook events</h3>
            {summary.latest_webhooks.length > 0 ? (
              summary.latest_webhooks.map((event) => (
                <div key={event.event_id} className="review-item">
                  <span>{event.event_type} | {event.payment_reference || event.order_number}</span>
                  <strong>{formatDate(event.created_at)}</strong>
                </div>
              ))
            ) : (
              <p>No webhook events captured yet.</p>
            )}
          </article>

          <article className="review-card wide">
            <h3>Snapshot history</h3>
            {summary.snapshot_history.length > 0 ? (
              summary.snapshot_history.map((snapshot) => (
                <div key={`${snapshot.created_at}-${snapshot.created_by_label}`} className="review-item">
                  <span>
                    Rs. {snapshot.captured_total} captured | Rs. {snapshot.refunded_total} refunded
                    {snapshot.notes ? ` | ${snapshot.notes}` : ""}
                  </span>
                  <strong>
                    {formatDate(snapshot.created_at)}
                    {snapshot.created_by_label ? ` | ${snapshot.created_by_label}` : ""}
                  </strong>
                </div>
              ))
            ) : (
              <p>No reconciliation snapshots saved yet.</p>
            )}
          </article>

          <article className="review-card wide">
            <h3>Settlement history</h3>
            {summary.settlement_history.length > 0 ? (
              summary.settlement_history.map((batch) => (
                <div key={batch.id} className="review-item">
                  <span>
                    {batch.batch_reference} | Rs. {batch.total_net} net
                    {batch.notes ? ` | ${batch.notes}` : ""}
                  </span>
                  <strong>
                    <Link href={`/admin/settlements/${batch.id}`} className="section-link">
                      Open batch
                    </Link>
                    <button type="button" className="section-link" onClick={() => void handleExportSettlement(batch.id)}>
                      Export batch
                    </button>
                  </strong>
                </div>
              ))
            ) : (
              <p>No settlement batches created yet.</p>
            )}
          </article>
        </div>
      )}
    </section>
  );
}
