import { PrescriptionStatusView } from "@/components/prescription-status-view";

export default function PrescriptionSubmittedPage() {
  return (
    <main className="page-shell">
      <div className="breadcrumb">Home / Upload Prescription / Submitted</div>
      <PrescriptionStatusView mode="submitted" />
    </main>
  );
}
