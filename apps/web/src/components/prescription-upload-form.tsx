"use client";

import { useRouter } from "next/navigation";
import { useMemo, useState } from "react";

import { useCart } from "@/components/cart-provider";
import { createPrescription, type ApiPrescriptionRecord } from "@/lib/api";

function mapApiStatusToLocalStatus(status: ApiPrescriptionRecord["status"]) {
  if (status === "pending_review" || status === "clarification_required") {
    return "pending" as const;
  }

  return status;
}

export function PrescriptionUploadForm() {
  const router = useRouter();
  const { latestPrescription, savePrescriptionRecord } = useCart();
  const [fileName, setFileName] = useState("");
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [patientName, setPatientName] = useState(latestPrescription?.patientName ?? "");
  const [doctorName, setDoctorName] = useState(latestPrescription?.doctorName ?? "");
  const [notes, setNotes] = useState(latestPrescription?.notes ?? "");
  const [touched, setTouched] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [errorMessage, setErrorMessage] = useState("");
  const fileLabel = fileName || latestPrescription?.fileName || "";

  const canSubmit = useMemo(() => {
    return fileLabel.trim().length > 0 && patientName.trim().length > 0 && doctorName.trim().length > 0;
  }, [doctorName, fileLabel, patientName]);

  async function handleSubmit() {
    setTouched(true);
    setErrorMessage("");

    if (!canSubmit || submitting) {
      return;
    }

    setSubmitting(true);
    setUploadProgress(0);

    try {
      if (!selectedFile) {
        throw new Error("Please choose a prescription file.");
      }

      const apiRecord = await createPrescription({
        patient_name: patientName,
        doctor_name: doctorName,
        notes,
        file: selectedFile
      }, setUploadProgress);

      savePrescriptionRecord({
        id: apiRecord.reference_code,
        fileName: apiRecord.uploaded_file_name,
        patientName: apiRecord.patient_name,
        doctorName: apiRecord.doctor_name,
        notes: apiRecord.notes ?? notes,
        status: mapApiStatusToLocalStatus(apiRecord.status),
        submittedAt: apiRecord.created_at,
        reviewEtaMinutes: apiRecord.review_eta_hours * 60
      });

      router.push("/upload-prescription/submitted");
    } catch (error) {
      const message = error instanceof Error ? error.message : "Prescription upload failed.";
      setErrorMessage(message);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="rx-form-panel">
      <div className="rx-form-topbar">
        <div>
          <span className="small-pill">Same-day pharmacist review</span>
          <h2 className="page-title">Start your prescription review</h2>
        </div>
        <div className="rx-trust-stack">
          <div className="rx-trust-item">
            <strong>10 min</strong>
            <span>Fast triage for clear uploads</span>
          </div>
          <div className="rx-trust-item">
            <strong>Secure</strong>
            <span>Shared only with pharmacy reviewers</span>
          </div>
        </div>
      </div>

      <label className="rx-dropzone">
        <strong>{fileLabel || "Drag and drop prescription here"}</strong>
        <p>{fileLabel ? "Selected file ready for review" : "or click to upload from your device"}</p>
        <span className="secondary-action">Choose File</span>
        <input
          data-testid="prescription-file-input"
          className="hidden-file-input"
          type="file"
          accept=".jpg,.jpeg,.png,.pdf"
          onChange={(event) => {
            const file = event.target.files?.[0] ?? null;
            setSelectedFile(file);
            setFileName(file?.name ?? "");
          }}
        />
      </label>

      <div className="rx-file-meta-row">
        <span className="rx-file-pill">Accepted: JPG, PNG, PDF</span>
        <span className="rx-file-pill">Doctor stamp visible</span>
        <span className="rx-file-pill">Medicine lines readable</span>
      </div>

      <div className="rx-form-grid">
        <label className="rx-field">
          <span>Patient name</span>
          <input
            data-testid="prescription-patient-name"
            type="text"
            value={patientName}
            onChange={(event) => setPatientName(event.target.value)}
            placeholder="Enter patient full name"
          />
        </label>
        <label className="rx-field">
          <span>Doctor name</span>
          <input
            data-testid="prescription-doctor-name"
            type="text"
            value={doctorName}
            onChange={(event) => setDoctorName(event.target.value)}
            placeholder="Enter prescribing doctor name"
          />
        </label>
        <label className="rx-field wide">
          <span>Notes for pharmacist</span>
          <textarea
            data-testid="prescription-notes"
            value={notes}
            onChange={(event) => setNotes(event.target.value)}
            placeholder="Add notes like alternate brands, refill urgency, or delivery instructions"
          />
        </label>
      </div>

      <div className="rx-privacy-box">
        Your uploaded prescription is stored securely and shared only with authorized pharmacy reviewers.
        {submitting ? ` Upload progress: ${uploadProgress}%` : ""}
        {!canSubmit && touched ? " Please complete patient name, doctor name, and file selection." : ""}
        {errorMessage ? ` ${errorMessage}` : ""}
      </div>

      <div className="rx-review-checklist">
        <article className="rx-review-card">
          <strong>What our team checks</strong>
          <span>Doctor and patient details, medicine names, refill instructions, and substitute suitability.</span>
        </article>
        <article className="rx-review-card">
          <strong>What happens next</strong>
          <span>Clear prescriptions move into review, then approved items can continue directly to cart.</span>
        </article>
      </div>

      <div className="success-actions">
        <button
          data-testid="submit-prescription-button"
          type="button"
          className="primary-action"
          onClick={handleSubmit}
        >
          {submitting ? "Submitting..." : "Submit prescription"}
        </button>
        <button
          type="button"
          className="secondary-action"
          onClick={() => {
            setFileName("");
            setSelectedFile(null);
            setPatientName("");
            setDoctorName("");
            setUploadProgress(0);
            setNotes("");
            setTouched(false);
            setErrorMessage("");
          }}
        >
          Clear form
        </button>
      </div>
    </div>
  );
}
