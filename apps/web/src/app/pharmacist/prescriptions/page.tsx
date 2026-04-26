"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import {
  fetchPharmacistQueue,
  getStoredAuthToken,
  getStoredAuthUser,
  type ApiPrescriptionRecord
} from "@/lib/api";

const filters = [
  { key: "", label: "All" },
  { key: "pending_review", label: "Pending review" },
  { key: "clarification_required", label: "Clarification" },
  { key: "approved", label: "Approved" },
  { key: "rejected", label: "Rejected" }
] as const;

function formatStatus(value: string) {
  return value.replace(/_/g, " ").replace(/\b\w/g, (character) => character.toUpperCase());
}

export default function PharmacistQueuePage() {
  const [items, setItems] = useState<ApiPrescriptionRecord[]>([]);
  const [statusFilter, setStatusFilter] = useState("");
  const [isLoading, setIsLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState("");
  const isAuthenticated = Boolean(getStoredAuthToken());
  const role = getStoredAuthUser()?.role;

  useEffect(() => {
    if (!isAuthenticated) {
      setIsLoading(false);
      return;
    }

    void fetchPharmacistQueue(statusFilter)
      .then((data) => {
        setItems(data);
        setErrorMessage("");
      })
      .catch((error: Error) => {
        setErrorMessage(error.message);
      })
      .finally(() => {
        setIsLoading(false);
      });
  }, [isAuthenticated, statusFilter]);

  return (
    <>
      <div className="section-title-row">
        <div>
          <p className="eyebrow">Prescription Queue</p>
          <h2>Pending review cases</h2>
        </div>
      </div>

      {!isAuthenticated ? (
        <div className="empty-cart-box">
          <h2>Login to access pharmacist tools</h2>
          <p>This queue is available only after authenticated pharmacist or admin login.</p>
        </div>
      ) : role !== "pharmacist" && role !== "admin" ? (
        <div className="empty-cart-box">
          <h2>Permission required</h2>
          <p>Your current account does not have pharmacist review access.</p>
        </div>
      ) : isLoading ? (
        <div className="empty-cart-box">
          <h2>Loading review queue</h2>
          <p>Fetching prescriptions awaiting pharmacist action.</p>
        </div>
      ) : errorMessage ? (
        <div className="empty-cart-box">
          <h2>Could not load queue</h2>
          <p>{errorMessage}</p>
        </div>
      ) : (
        <>
          <div className="payment-methods" style={{ marginBottom: 20 }}>
            {filters.map((filter) => (
              <button
                key={filter.key || "all"}
                type="button"
                className={`payment-card ${statusFilter === filter.key ? "active" : ""}`}
                onClick={() => setStatusFilter(filter.key)}
                data-testid={`pharmacist-queue-filter-${filter.key || "all"}`}
              >
                <strong>{filter.label}</strong>
              </button>
            ))}
          </div>

          <div className="section-grid">
            {items.map((item) => (
              <article key={item.reference_code} className="review-card">
                <div className="summary-row">
                  <strong>{item.reference_code}</strong>
                  <span className="small-pill">{formatStatus(item.review_priority)}</span>
                </div>
                <h3>{item.patient_name}</h3>
                <p>{item.doctor_name || "Doctor name not provided"}</p>
                <div className="review-item">
                  <span>Status</span>
                  <strong>{formatStatus(item.status)}</strong>
                </div>
                <div className="review-item">
                  <span>Uploaded file</span>
                  <strong>{item.uploaded_file_name}</strong>
                </div>
                <Link
                  href={`/pharmacist/prescriptions/${item.reference_code}`}
                  className="section-link"
                  data-testid={`pharmacist-queue-open-${item.reference_code}`}
                >
                  Open review
                </Link>
              </article>
            ))}
          </div>
        </>
      )}
    </>
  );
}
