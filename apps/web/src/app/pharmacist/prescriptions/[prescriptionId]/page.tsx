"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import {
  fetchPharmacistPrescription,
  getStoredAuthToken,
  getStoredAuthUser,
  reviewPrescription,
  type ApiPrescriptionDetail,
  type ReviewPrescriptionPayload
} from "@/lib/api";

function formatStatus(value: string) {
  return value.replace(/_/g, " ").replace(/\b\w/g, (character) => character.toUpperCase());
}

export default function PharmacistPrescriptionDetailPage({
  params
}: {
  params: Promise<{ prescriptionId: string }>;
}) {
  const [prescriptionId, setPrescriptionId] = useState("");
  const [record, setRecord] = useState<ApiPrescriptionDetail | null>(null);
  const [notes, setNotes] = useState("");
  const [clarificationMessage, setClarificationMessage] = useState("");
  const [substituteGuidance, setSubstituteGuidance] = useState("");
  const [isLoading, setIsLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");
  const isAuthenticated = Boolean(getStoredAuthToken());
  const role = getStoredAuthUser()?.role;

  useEffect(() => {
    void params.then((resolved) => setPrescriptionId(resolved.prescriptionId));
  }, [params]);

  useEffect(() => {
    if (!prescriptionId || !isAuthenticated) {
      setIsLoading(false);
      return;
    }

    void fetchPharmacistPrescription(prescriptionId)
      .then((data) => {
        setRecord(data);
        setErrorMessage(data ? "" : "Prescription not found.");
      })
      .catch((error: Error) => setErrorMessage(error.message))
      .finally(() => setIsLoading(false));
  }, [isAuthenticated, prescriptionId]);

  async function handleDecision(decision: ReviewPrescriptionPayload["decision"]) {
    if (!prescriptionId) {
      return;
    }

    setSubmitting(true);
    setErrorMessage("");

    try {
      const updated = await reviewPrescription(prescriptionId, {
        decision,
        notes,
        substitute_guidance: substituteGuidance,
        clarification_message: clarificationMessage
      });
      setRecord(updated);
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Could not submit decision.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="page-shell">
      <div className="breadcrumb">Pharmacist / Prescriptions / {prescriptionId || "Detail"}</div>

      <section className="soft-section">
        <div className="section-title-row">
          <div>
            <p className="eyebrow">Pharmacist Review</p>
            <h1 className="page-title">Prescription detail review</h1>
          </div>
          <Link href="/pharmacist/prescriptions" className="section-link">
            Back to queue
          </Link>
        </div>

        {!isAuthenticated ? (
          <div className="empty-cart-box">
            <h2>Login required</h2>
            <p>Authenticate to review prescriptions.</p>
          </div>
        ) : role !== "pharmacist" && role !== "admin" ? (
          <div className="empty-cart-box">
            <h2>Permission required</h2>
            <p>Your current account does not have pharmacist review access.</p>
          </div>
        ) : isLoading ? (
          <div className="empty-cart-box">
            <h2>Loading prescription detail</h2>
            <p>Fetching patient, doctor, and review history.</p>
          </div>
        ) : errorMessage || !record ? (
          <div className="empty-cart-box">
            <h2>Could not load prescription</h2>
            <p>{errorMessage || "Prescription not found."}</p>
          </div>
        ) : (
          <div className="review-grid">
            <article className="review-card">
              <h3>{record.reference_code}</h3>
              <p>{record.patient_name}</p>
              <div className="review-item">
                <span>Status</span>
                <strong>{formatStatus(record.status)}</strong>
              </div>
              <div className="review-item">
                <span>Priority</span>
                <strong>{formatStatus(record.review_priority)}</strong>
              </div>
            </article>

            <article className="review-card">
              <h3>Prescription details</h3>
              <p>Doctor: {record.doctor_name || "Not provided"}</p>
              <div className="review-item">
                <span>Uploaded file</span>
                <strong>
                  {record.file_access_url || record.uploaded_file_url ? (
                    <a href={record.file_access_url || record.uploaded_file_url} target="_blank" rel="noreferrer">
                      {record.uploaded_file_name}
                    </a>
                  ) : (
                    record.uploaded_file_name
                  )}
                </strong>
              </div>
              <div className="review-item">
                <span>Notes</span>
                <strong>{record.notes || "None"}</strong>
              </div>
            </article>

            <article className="review-card wide">
              <h3>Review decision</h3>
              <div className="rx-form-grid">
                <label className="rx-field wide">
                  <span>Reviewer notes</span>
                  <textarea
                    value={notes}
                    onChange={(event) => setNotes(event.target.value)}
                    data-testid="pharmacist-review-notes"
                  />
                </label>
                <label className="rx-field wide">
                  <span>Clarification message</span>
                  <textarea
                    value={clarificationMessage}
                    onChange={(event) => setClarificationMessage(event.target.value)}
                    data-testid="pharmacist-clarification-message"
                  />
                </label>
                <label className="rx-field wide">
                  <span>Substitute guidance</span>
                  <textarea
                    value={substituteGuidance}
                    onChange={(event) => setSubstituteGuidance(event.target.value)}
                    data-testid="pharmacist-substitute-guidance"
                  />
                </label>
              </div>

              <div className="success-actions" style={{ marginTop: 16 }}>
                <button
                  type="button"
                  className="primary-action"
                  disabled={submitting}
                  onClick={() => handleDecision("approved")}
                  data-testid="pharmacist-approve-button"
                >
                  Approve
                </button>
                <button
                  type="button"
                  className="secondary-action"
                  disabled={submitting}
                  onClick={() => handleDecision("clarification_required")}
                  data-testid="pharmacist-clarification-button"
                >
                  Ask clarification
                </button>
                <button
                  type="button"
                  className="secondary-action"
                  disabled={submitting}
                  onClick={() => handleDecision("rejected")}
                  data-testid="pharmacist-reject-button"
                >
                  Reject
                </button>
              </div>
            </article>

            <article className="review-card wide">
              <h3>Audit trail</h3>
              {record.reviews.length === 0 ? (
                <p>No review decisions recorded yet.</p>
              ) : (
                record.reviews.map((review) => (
                  <div key={review.id} className="review-item">
                    <span>
                      {formatStatus(review.decision)} by {review.reviewer_name}
                    </span>
                    <strong>{review.notes || review.substitute_guidance || "No remarks"}</strong>
                  </div>
                ))
              )}
            </article>
          </div>
        )}
      </section>
    </main>
  );
}
