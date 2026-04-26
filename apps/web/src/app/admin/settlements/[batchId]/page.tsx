"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import {
  downloadAdminSettlementBatchCsv,
  fetchAdminSettlementBatchById,
  getStoredAuthToken,
  getStoredAuthUser,
  updateAdminSettlementBatch,
  type ApiSettlementBatch
} from "@/lib/api";

type SettlementStatus = "draft" | "processing" | "closed";

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

export default function AdminSettlementDetailPage({ params }: { params: Promise<{ batchId: string }> }) {
  const [batchId, setBatchId] = useState("");
  const [batch, setBatch] = useState<ApiSettlementBatch | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isExporting, setIsExporting] = useState(false);
  const [isActing, setIsActing] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");
  const [successMessage, setSuccessMessage] = useState("");
  const [notesDraft, setNotesDraft] = useState("");
  const isAuthenticated = Boolean(getStoredAuthToken());
  const role = getStoredAuthUser()?.role;

  useEffect(() => {
    void params.then((resolved) => setBatchId(resolved.batchId));
  }, [params]);

  useEffect(() => {
    if (!isAuthenticated || !batchId) {
      setIsLoading(false);
      return;
    }

    setIsLoading(true);
    void fetchAdminSettlementBatchById(Number(batchId))
      .then((data) => {
        setBatch(data);
        setNotesDraft(data.notes || "");
        setErrorMessage("");
      })
      .catch((error: Error) => setErrorMessage(error.message))
      .finally(() => setIsLoading(false));
  }, [batchId, isAuthenticated]);

  if (!isAuthenticated) {
    return (
      <div className="empty-cart-box">
        <h2>Login required</h2>
        <p>Settlement detail is available only after authenticated finance or admin login.</p>
      </div>
    );
  }

  if (role !== "admin" && role !== "finance") {
    return (
      <div className="empty-cart-box">
        <h2>Permission required</h2>
        <p>Your current account does not have settlement detail access.</p>
      </div>
    );
  }

  async function handleExport() {
    if (!batch) {
      return;
    }

    setIsExporting(true);
    setErrorMessage("");
    try {
      const blob = await downloadAdminSettlementBatchCsv(batch.id);
      const url = window.URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = `settlement-${batch.batch_reference}.csv`;
      anchor.click();
      window.URL.revokeObjectURL(url);
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Could not export settlement batch.");
    } finally {
      setIsExporting(false);
    }
  }

  async function handleStatusUpdate(status: SettlementStatus) {
    if (!batch) {
      return;
    }

    setIsActing(true);
    setErrorMessage("");
    setSuccessMessage("");
    try {
      const updated = await updateAdminSettlementBatch(batch.id, {
        status,
        notes: notesDraft
      });
      setBatch(updated);
      setNotesDraft(updated.notes || "");
      setSuccessMessage(`Settlement batch moved to ${status}.`);
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Could not update settlement batch.");
    } finally {
      setIsActing(false);
    }
  }

  async function handleSaveNotes() {
    if (!batch) {
      return;
    }

    setIsActing(true);
    setErrorMessage("");
    setSuccessMessage("");
    try {
      const updated = await updateAdminSettlementBatch(batch.id, {
        status: batch.status as SettlementStatus,
        notes: notesDraft
      });
      setBatch(updated);
      setNotesDraft(updated.notes || "");
      setSuccessMessage("Settlement notes saved.");
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Could not save settlement notes.");
    } finally {
      setIsActing(false);
    }
  }

  if (isLoading) {
    return (
      <section className="soft-section">
        <div className="empty-cart-box">
          <h2>Loading settlement detail</h2>
          <p>Fetching payout, refund, and net settlement entries.</p>
        </div>
      </section>
    );
  }

  if (errorMessage || !batch) {
    return (
      <section className="soft-section">
        <div className="empty-cart-box">
          <h2>Could not load settlement detail</h2>
          <p>{errorMessage || "Settlement batch unavailable."}</p>
        </div>
      </section>
    );
  }

  return (
    <section className="soft-section">
      <div className="section-title-row">
        <div>
          <p className="eyebrow">Finance</p>
          <h1 className="page-title">Settlement {batch.batch_reference}</h1>
        </div>
        <div className="success-actions">
          <Link href="/admin/settlements" className="section-link">
            Back to settlements
          </Link>
          <button type="button" className="primary-action" onClick={() => void handleExport()} disabled={isExporting}>
            {isExporting ? "Exporting..." : "Export CSV"}
          </button>
        </div>
      </div>

      {errorMessage ? <p className="auth-error">{errorMessage}</p> : null}
      {!errorMessage && successMessage ? <p className="auth-success">{successMessage}</p> : null}

      <div className="review-grid">
        <article className="review-card">
          <h3>Provider</h3>
          <p>{batch.provider}</p>
        </article>
        <article className="review-card">
          <h3>Status</h3>
          <p>{batch.status.replace(/_/g, " ")}</p>
          <div className="success-actions" style={{ marginTop: 12 }}>
            {batch.status !== "draft" ? (
              <button type="button" className="secondary-action" onClick={() => void handleStatusUpdate("draft")} disabled={isActing}>
                Mark draft
              </button>
            ) : null}
            {batch.status !== "processing" ? (
              <button type="button" className="secondary-action" onClick={() => void handleStatusUpdate("processing")} disabled={isActing}>
                Mark processing
              </button>
            ) : null}
            {batch.status !== "closed" ? (
              <button data-testid="mark-settlement-closed-button" type="button" className="primary-action" onClick={() => void handleStatusUpdate("closed")} disabled={isActing}>
                Mark closed
              </button>
            ) : null}
          </div>
        </article>
        <article className="review-card">
          <h3>Captured</h3>
          <p>Rs. {batch.total_captured}</p>
        </article>
        <article className="review-card">
          <h3>Refunded</h3>
          <p>Rs. {batch.total_refunded}</p>
        </article>
        <article className="review-card">
          <h3>Net settled</h3>
          <p>Rs. {batch.total_net}</p>
        </article>
        <article className="review-card">
          <h3>Created by</h3>
          <p>{batch.created_by_name || "System"}</p>
        </article>

        <article className="review-card wide">
          <h3>Settlement window</h3>
          <p>{formatDate(batch.period_start)} to {formatDate(batch.period_end)}</p>
          <div className="summary-row">
            <span>Created</span>
            <strong>{formatDate(batch.created_at)}</strong>
          </div>
        </article>

        <article className="review-card wide">
          <h3>Settlement notes</h3>
          <textarea
            className="review-notes-input"
            rows={4}
            value={notesDraft}
            onChange={(event) => setNotesDraft(event.target.value)}
            placeholder="Add finance closeout notes, exception details, or payout references."
          />
          <div className="success-actions" style={{ marginTop: 12 }}>
            <button type="button" className="secondary-action" onClick={() => setNotesDraft(batch.notes || "")} disabled={isActing}>
              Reset
            </button>
            <button data-testid="save-settlement-notes-button" type="button" className="primary-action" onClick={() => void handleSaveNotes()} disabled={isActing}>
              {isActing ? "Saving..." : "Save notes"}
            </button>
          </div>
        </article>

        <article className="review-card wide">
          <h3>Settlement entries</h3>
          {batch.entries.length > 0 ? (
            batch.entries.map((entry) => (
              <div key={`${entry.order_number}-${entry.payment_reference}`} className="review-item">
                <span>
                  {entry.order_number} | {entry.payment_reference}
                  <br />
                  Refund: {entry.refund_status || "none"}
                </span>
                <strong>
                  Gross Rs. {entry.gross_amount} | Refund Rs. {entry.refund_amount} | Net Rs. {entry.net_amount}
                  <br />
                  {entry.settlement_status.replace(/_/g, " ")}
                </strong>
              </div>
            ))
          ) : (
            <p>No settlement entries recorded in this batch.</p>
          )}
        </article>
      </div>
    </section>
  );
}
