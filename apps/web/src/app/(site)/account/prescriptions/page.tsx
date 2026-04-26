"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { useAuthSession } from "@/hooks/use-auth-session";
import {
  fetchMyPrescriptions,
  type ApiPrescriptionRecord
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

function formatStatus(value: string) {
  return value
    .replace(/_/g, " ")
    .replace(/\b\w/g, (character) => character.toUpperCase());
}

function formatBytes(value?: number) {
  if (!value) {
    return "Size unavailable";
  }

  if (value < 1024 * 1024) {
    return `${(value / 1024).toFixed(0)} KB`;
  }

  return `${(value / (1024 * 1024)).toFixed(1)} MB`;
}

export default function AccountPrescriptionsPage() {
  const [prescriptions, setPrescriptions] = useState<ApiPrescriptionRecord[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState("");
  const session = useAuthSession();
  const isAuthenticated = session.isAuthenticated;

  useEffect(() => {
    if (!isAuthenticated) {
      setIsLoading(false);
      return;
    }

    void fetchMyPrescriptions()
      .then((data) => {
        setPrescriptions(data);
        setErrorMessage("");
      })
      .catch((error: Error) => setErrorMessage(error.message))
      .finally(() => setIsLoading(false));
  }, [isAuthenticated]);

  return (
    <main className="page-shell">
      <div className="breadcrumb">Home / Account / Prescriptions</div>

      <section className="soft-section">
        <div className="section-title-row">
          <div>
            <p className="eyebrow">Account</p>
            <h1 className="page-title">Prescription uploads</h1>
          </div>
          <div className="success-actions">
            <Link href="/account" className="section-link">
              Back to account
            </Link>
            <Link href="/upload-prescription" className="primary-action">
              Upload new prescription
            </Link>
          </div>
        </div>

        {!isAuthenticated ? (
          <div className="empty-cart-box">
            <h2>Login to view prescriptions</h2>
            <p>Your uploaded prescriptions and pharmacist review updates will appear here after OTP login.</p>
            <Link href="/login" className="primary-action">
              Login
            </Link>
          </div>
        ) : isLoading ? (
          <div className="empty-cart-box">
            <h2>Loading prescriptions</h2>
            <p>Fetching uploaded files, review status, and pharmacist guidance.</p>
          </div>
        ) : errorMessage ? (
          <div className="empty-cart-box">
            <h2>Could not load prescriptions</h2>
            <p>{errorMessage}</p>
          </div>
        ) : prescriptions.length === 0 ? (
          <div className="empty-cart-box">
            <h2>No prescriptions uploaded yet</h2>
            <p>Once you upload a prescription, its file, review status, and pharmacist updates will appear here.</p>
            <div className="success-actions">
              <Link href="/upload-prescription" className="primary-action">
                Upload prescription
              </Link>
              <Link href="/search" className="secondary-action">
                Search medicines
              </Link>
            </div>
          </div>
        ) : (
          <div className="review-grid">
            {prescriptions.map((prescription) => (
              <article key={prescription.reference_code} className="review-card wide">
                <div className="section-title-row">
                  <div>
                    <h3>{prescription.reference_code}</h3>
                    <p>{prescription.patient_name} | {prescription.doctor_name}</p>
                  </div>
                  <strong>{formatStatus(prescription.status)}</strong>
                </div>

                <div className="review-item">
                  <span>Uploaded file</span>
                  <strong>{prescription.uploaded_file_name}</strong>
                </div>
                <div className="review-item">
                  <span>File details</span>
                  <strong>{prescription.uploaded_file_type || "Unknown type"} | {formatBytes(prescription.uploaded_file_size_bytes)}</strong>
                </div>
                <div className="review-item">
                  <span>Uploaded on</span>
                  <strong>{formatDate(prescription.created_at)}</strong>
                </div>
                <div className="review-item">
                  <span>Review priority</span>
                  <strong>{formatStatus(prescription.review_priority)}</strong>
                </div>
                <div className="review-item">
                  <span>Estimated review</span>
                  <strong>{prescription.review_eta_hours} hour(s)</strong>
                </div>
                <div className="success-actions">
                  <Link href={`/account/prescriptions/${prescription.reference_code}`} className="secondary-action">
                    Open detail
                  </Link>
                  {prescription.file_access_url ? (
                    <a href={prescription.file_access_url} className="primary-action" target="_blank" rel="noreferrer">
                      View document
                    </a>
                  ) : null}
                  <Link href="/account/notifications" className="secondary-action">
                    Review updates
                  </Link>
                  <Link href="/upload-prescription" className="secondary-action">
                    Upload another
                  </Link>
                </div>
              </article>
            ))}
          </div>
        )}
      </section>
    </main>
  );
}
