"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { RoleDashboardView } from "@/components/role-dashboard-view";
import {
  fetchPharmacistQueue,
  getStoredAuthToken,
  getStoredAuthUser,
  type ApiPrescriptionRecord
} from "@/lib/api";
import { getRoleDashboardConfig } from "@/lib/role-dashboard";

const pharmacistConfig = getRoleDashboardConfig("pharmacist");

function humanizeStatus(value: string) {
  return value.replace(/_/g, " ").replace(/\b\w/g, (character) => character.toUpperCase());
}

export default function PharmacistDashboardPage() {
  const [items, setItems] = useState<ApiPrescriptionRecord[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState("");
  const isAuthenticated = Boolean(getStoredAuthToken());
  const role = getStoredAuthUser()?.role;

  useEffect(() => {
    if (!isAuthenticated) {
      setIsLoading(false);
      return;
    }

    void fetchPharmacistQueue("")
      .then((data) => {
        setItems(data);
        setErrorMessage("");
      })
      .catch((error: Error) => setErrorMessage(error.message))
      .finally(() => setIsLoading(false));
  }, [isAuthenticated]);

  if (!pharmacistConfig) {
    return null;
  }

  if (!isAuthenticated) {
    return (
      <div className="empty-cart-box">
        <h2>Login to access pharmacist tools</h2>
        <p>This dashboard is available only after authenticated pharmacist or admin login.</p>
      </div>
    );
  }

  if (role !== "pharmacist" && role !== "admin") {
    return (
      <div className="empty-cart-box">
        <h2>Permission required</h2>
        <p>Your current account does not have pharmacist review access.</p>
      </div>
    );
  }

  const pending = items.filter((item) => item.status === "pending_review").length;
  const urgent = items.filter((item) => item.review_priority === "urgent").length;
  const clarification = items.filter((item) => item.status === "clarification_required").length;

  return (
    <RoleDashboardView
      config={{
        ...pharmacistConfig,
        summaryCards: [
          { label: "Queue size", value: String(items.length), meta: "Prescription cases currently visible in the review queue" },
          { label: "Pending review", value: String(pending), meta: "Fresh submissions that still need pharmacist action" },
          { label: "Urgent cases", value: String(urgent), meta: "High-priority reviews that should be handled first" },
          { label: "Clarifications", value: String(clarification), meta: "Cases waiting on more detail before approval" }
        ]
      }}
    >
      <section className="soft-section role-dashboard-section">
        <div className="section-title-row">
          <div>
            <p className="eyebrow">Queue Preview</p>
            <h2>Next cases to review</h2>
          </div>
          <Link href="/pharmacist/prescriptions" className="section-link">
            Open full queue
          </Link>
        </div>

        {isLoading ? (
          <div className="empty-cart-box">
            <h2>Loading pharmacist dashboard</h2>
            <p>Fetching prescription queue counts and recent cases.</p>
          </div>
        ) : errorMessage ? (
          <div className="empty-cart-box">
            <h2>Could not load pharmacist dashboard</h2>
            <p>{errorMessage}</p>
          </div>
        ) : (
          <div className="review-grid">
            {items.slice(0, 6).map((item) => (
              <article key={item.reference_code} className="review-card">
                <div className="summary-row">
                  <strong>{item.reference_code}</strong>
                  <span className="small-pill">{humanizeStatus(item.review_priority)}</span>
                </div>
                <h3>{item.patient_name}</h3>
                <p>{item.doctor_name || "Doctor name not provided"}</p>
                <div className="review-item">
                  <span>Status</span>
                  <strong>{humanizeStatus(item.status)}</strong>
                </div>
                <div className="review-item">
                  <span>Uploaded file</span>
                  <strong>{item.uploaded_file_name}</strong>
                </div>
                <Link href={`/pharmacist/prescriptions/${item.reference_code}`} className="section-link">
                  Open review
                </Link>
              </article>
            ))}
            {items.length === 0 ? (
              <div className="empty-cart-box">
                <h2>No prescriptions waiting</h2>
                <p>The review queue is currently clear.</p>
              </div>
            ) : null}
          </div>
        )}
      </section>
    </RoleDashboardView>
  );
}
