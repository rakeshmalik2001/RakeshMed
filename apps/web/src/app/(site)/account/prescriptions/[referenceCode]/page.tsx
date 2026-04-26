"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { useAuthSession } from "@/hooks/use-auth-session";
import {
  fetchMyPrescription,
  type ApiPrescriptionDetail
} from "@/lib/api";

function formatDate(value?: string | null) {
  if (!value) {
    return "Not available";
  }

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

function formatStatus(value: string) {
  return value
    .replace(/_/g, " ")
    .replace(/\b\w/g, (character) => character.toUpperCase());
}

export default function AccountPrescriptionDetailPage({ params }: { params: Promise<{ referenceCode: string }> }) {
  const [referenceCode, setReferenceCode] = useState("");
  const [prescription, setPrescription] = useState<ApiPrescriptionDetail | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState("");
  const session = useAuthSession();
  const isAuthenticated = session.isAuthenticated;

  useEffect(() => {
    void params.then((resolved) => setReferenceCode(resolved.referenceCode));
  }, [params]);

  useEffect(() => {
    if (!isAuthenticated || !referenceCode) {
      setIsLoading(false);
      return;
    }

    void fetchMyPrescription(referenceCode)
      .then((data) => {
        setPrescription(data);
        setErrorMessage("");
      })
      .catch((error: Error) => setErrorMessage(error.message))
      .finally(() => setIsLoading(false));
  }, [isAuthenticated, referenceCode]);

  return (
    <main className="page-shell">
      <div className="breadcrumb">Home / Account / Prescriptions / {referenceCode || "Detail"}</div>

      <section className="soft-section">
        <div className="section-title-row">
          <div>
            <p className="eyebrow">Account</p>
            <h1 className="page-title">Prescription detail</h1>
          </div>
          <div className="success-actions">
            <Link href="/account/prescriptions" className="section-link">
              Back to prescriptions
            </Link>
            <Link href="/upload-prescription" className="secondary-action">
              Upload another
            </Link>
          </div>
        </div>

        {!isAuthenticated ? (
          <div className="empty-cart-box">
            <h2>Login to view this prescription</h2>
            <p>You need to login with OTP to open uploaded prescription details and pharmacist guidance.</p>
            <Link href="/login" className="primary-action">
              Login
            </Link>
          </div>
        ) : isLoading ? (
          <div className="empty-cart-box">
            <h2>Loading prescription detail</h2>
            <p>Fetching file access, clarification notes, and pharmacist review guidance.</p>
          </div>
        ) : errorMessage || !prescription ? (
          <div className="empty-cart-box">
            <h2>Could not load prescription detail</h2>
            <p>{errorMessage || "Prescription unavailable."}</p>
          </div>
        ) : (
          <div className="review-grid">
            <article className="review-card">
              <h3>{prescription.reference_code}</h3>
              <p>{formatStatus(prescription.status)}</p>
              <div className="summary-row">
                <span>Priority</span>
                <strong>{formatStatus(prescription.review_priority)}</strong>
              </div>
            </article>

            <article className="review-card">
              <h3>Patient</h3>
              <p>{prescription.patient_name}</p>
              <div className="summary-row">
                <span>Doctor</span>
                <strong>{prescription.doctor_name}</strong>
              </div>
            </article>

            <article className="review-card">
              <h3>Submitted</h3>
              <p>{formatDate(prescription.created_at)}</p>
              <div className="summary-row">
                <span>Reviewed</span>
                <strong>{formatDate(prescription.reviewed_at)}</strong>
              </div>
            </article>

            <article className="review-card wide">
              <h3>Uploaded document</h3>
              <p>{prescription.uploaded_file_name}</p>
              <div className="summary-row">
                <span>File type</span>
                <strong>{prescription.uploaded_file_type || "Unknown type"}</strong>
              </div>
              <div className="success-actions">
                {prescription.file_access_url ? (
                  <a href={prescription.file_access_url} className="primary-action" target="_blank" rel="noreferrer">
                    View document
                  </a>
                ) : null}
              </div>
            </article>

            <article className="review-card wide">
              <h3>Submitted notes</h3>
              <p>{prescription.notes || "No extra notes were shared with this upload."}</p>
            </article>

            {prescription.clarification_message ? (
              <article className="review-card wide">
                <h3>Clarification requested</h3>
                <p>{prescription.clarification_message}</p>
              </article>
            ) : null}

            <article className="review-card wide">
              <h3>Pharmacist reviews</h3>
              {prescription.reviews.length > 0 ? (
                prescription.reviews.map((review) => (
                  <div key={review.id} className="review-item">
                    <span>
                      {formatStatus(review.decision)}
                      <br />
                      {review.notes || "No review notes added."}
                      {review.substitute_guidance ? (
                        <>
                          <br />
                          Substitute guidance: {review.substitute_guidance}
                        </>
                      ) : null}
                    </span>
                    <strong>
                      {review.reviewer_name || "Pharmacist"}
                      <br />
                      {formatDate(review.created_at)}
                    </strong>
                  </div>
                ))
              ) : (
                <p>No pharmacist review notes recorded yet.</p>
              )}
            </article>
          </div>
        )}
      </section>
    </main>
  );
}
