import { PrescriptionStatusView } from "@/components/prescription-status-view";

export default function PrescriptionRejectedPage() {
  return (
    <main className="page-shell">
      <div className="breadcrumb">Home / Upload Prescription / Rejected</div>
      <PrescriptionStatusView mode="rejected" />
    </main>
  );
}
