import { PrescriptionStatusView } from "@/components/prescription-status-view";

export default function PrescriptionPendingPage() {
  return (
    <main className="page-shell">
      <div className="breadcrumb">Home / Upload Prescription / Pending</div>
      <PrescriptionStatusView mode="pending" />
    </main>
  );
}
