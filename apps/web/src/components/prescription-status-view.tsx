"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import { useCart } from "@/components/cart-provider";
import { PrescriptionStatusCard } from "@/components/prescription-status-card";
import { fetchMyPrescription, getStoredAuthToken, type ApiPrescriptionDetail } from "@/lib/api";

type PrescriptionStatusViewProps = {
  mode: "submitted" | "pending" | "approved" | "rejected";
};

function formatSubmittedAt(value: string | undefined) {
  if (!value) {
    return "Just now";
  }

  return new Intl.DateTimeFormat("en-IN", {
    day: "numeric",
    month: "short",
    hour: "numeric",
    minute: "2-digit"
  }).format(new Date(value));
}

function deriveRouteStatus(status?: string) {
  if (status === "approved") {
    return "approved";
  }
  if (status === "rejected" || status === "clarification_required") {
    return "rejected";
  }
  if (status === "pending_review") {
    return "pending";
  }
  return "submitted";
}

export function PrescriptionStatusView({ mode }: PrescriptionStatusViewProps) {
  const { latestPrescription } = useCart();
  const [prescription, setPrescription] = useState<ApiPrescriptionDetail | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");
  const isAuthenticated = Boolean(getStoredAuthToken());
  const referenceCode = latestPrescription?.id;

  useEffect(() => {
    if (!isAuthenticated || !referenceCode) {
      return;
    }

    setIsLoading(true);
    void fetchMyPrescription(referenceCode)
      .then((data) => {
        setPrescription(data);
        setErrorMessage("");
      })
      .catch((error: Error) => {
        setErrorMessage(error.message);
      })
      .finally(() => {
        setIsLoading(false);
      });
  }, [isAuthenticated, referenceCode]);

  const effectiveStatus = deriveRouteStatus(prescription?.status ?? latestPrescription?.status ?? mode);
  const effectiveReference = prescription?.reference_code ?? latestPrescription?.id ?? "RX-Preview";
  const patientName = prescription?.patient_name ?? latestPrescription?.patientName ?? "Your uploaded prescription";
  const doctorName = prescription?.doctor_name ?? latestPrescription?.doctorName ?? "Doctor details pending";
  const fileName = prescription?.uploaded_file_name ?? latestPrescription?.fileName ?? "Prescription upload pending";
  const reviewEta = prescription?.review_eta_hours ? `${prescription.review_eta_hours} hour(s)` : `${latestPrescription?.reviewEtaMinutes ?? 25} minutes`;

  const content = useMemo(() => {
    if (effectiveStatus === "approved") {
      return {
        status: "approved" as const,
        title: "Prescription approved",
        description: "Your uploaded prescription has been verified and eligible items can continue through checkout.",
        primaryHref: "/cart" as const,
        primaryLabel: "Continue to cart",
        secondaryHref: "/account/prescriptions" as const,
        secondaryLabel: "Open prescription detail",
        meta: [
          { label: "Reference", value: effectiveReference },
          { label: "Doctor", value: doctorName },
          { label: "Current status", value: "Approved" }
        ],
        highlights: [
          "Pharmacist verification is complete for this upload.",
          "Approved medicines can continue through cart and checkout.",
          "Open account prescriptions if you want the full review history."
        ]
      };
    }

    if (effectiveStatus === "rejected") {
      return {
        status: "rejected" as const,
        title: prescription?.status === "clarification_required" ? "Prescription needs clarification" : "Prescription needs a new upload",
        description:
          prescription?.clarification_message ||
          "Important details are unclear or missing. Please upload a clearer image or a valid prescription.",
        primaryHref: "/upload-prescription" as const,
        primaryLabel: "Upload again",
        secondaryHref: "/account/prescriptions" as const,
        secondaryLabel: "Open prescription detail",
        meta: [
          { label: "Reference", value: effectiveReference },
          { label: "File checked", value: fileName },
          { label: "Current status", value: prescription?.status === "clarification_required" ? "Clarification required" : "Rejected" }
        ],
        highlights: [
          "Make sure the doctor name, patient name, and medicine lines are visible in one frame.",
          "Avoid blur, crop, glare, or shadows on the stamp and prescription date.",
          "Use account prescription detail for pharmacist notes or clarification text."
        ]
      };
    }

    if (effectiveStatus === "pending") {
      return {
        status: "pending" as const,
        title: "Pharmacist review in progress",
        description: "Our team is reviewing medicine names, quantities, and any substitute requests from your upload.",
        primaryHref: "/account/prescriptions" as const,
        primaryLabel: "Open prescription detail",
        secondaryHref: "/cart" as const,
        secondaryLabel: "Back to cart",
        meta: [
          { label: "Reference", value: effectiveReference },
          { label: "Patient", value: patientName },
          { label: "Review ETA", value: reviewEta }
        ],
        highlights: [
          "Doctor details and medicine lines are being checked for readability.",
          "Substitute requests are reviewed only where pharmacist-approved alternatives are suitable.",
          "Notifications and account detail will update when the review state changes."
        ]
      };
    }

    return {
      status: "submitted" as const,
      title: "Prescription submitted successfully",
      description: "Your prescription has been uploaded and queued for pharmacist triage.",
      primaryHref: "/account/prescriptions" as const,
      primaryLabel: "Open prescription detail",
      secondaryHref: "/upload-prescription" as const,
      secondaryLabel: "Upload another",
      meta: [
        { label: "Reference", value: effectiveReference },
        { label: "File", value: fileName },
        { label: "Submitted", value: formatSubmittedAt(prescription?.created_at ?? latestPrescription?.submittedAt) }
      ],
      highlights: [
        `Patient: ${patientName}`,
        `Prescribing doctor: ${doctorName}`,
        prescription?.notes || latestPrescription?.notes || "We will review medicine names and substitute requests from your notes."
      ]
    };
  }, [doctorName, effectiveReference, effectiveStatus, fileName, latestPrescription?.notes, latestPrescription?.submittedAt, patientName, prescription, reviewEta]);

  if (!referenceCode) {
    return (
      <section className="rx-status-card submitted">
        <h1>No recent prescription found</h1>
        <p>Upload a prescription or open your account prescription history to continue.</p>
        <div className="success-actions">
          <Link href="/upload-prescription" className="primary-action">
            Upload prescription
          </Link>
          <Link href="/account/prescriptions" className="secondary-action">
            Account prescriptions
          </Link>
        </div>
      </section>
    );
  }

  return (
    <>
      <PrescriptionStatusCard {...content} />
      {isLoading ? (
        <p className="rx-status-inline-note">Refreshing the latest pharmacist review state...</p>
      ) : null}
      {errorMessage ? (
        <p className="rx-status-inline-note">Showing your last saved upload details. Live refresh failed: {errorMessage}</p>
      ) : null}
    </>
  );
}
