import { PrescriptionStatusView } from "@/components/prescription-status-view";

export default function PrescriptionApprovedPage() {
  return (
    <main className="page-shell">
      <div className="breadcrumb">Home / Upload Prescription / Approved</div>
      <PrescriptionStatusView mode="approved" />
    </main>
  );
}
