import { PrescriptionUploadForm } from "@/components/prescription-upload-form";
import { uploadPrescriptionContent } from "@/lib/storefront-content";

export default function UploadPrescriptionPage() {
  return (
    <main className="page-shell">
      <div className="breadcrumb">Home / Upload Prescription</div>

      <section className="rx-upload-layout">
        <div className="rx-info-panel">
          <p className="eyebrow">{uploadPrescriptionContent.eyebrow}</p>
          <h1>{uploadPrescriptionContent.title}</h1>
          <p>{uploadPrescriptionContent.intro}</p>

          <div className="rx-how-grid">
            {uploadPrescriptionContent.steps.map((step, index) => (
              <div key={step.title} className="rx-how-card">
                <strong>
                  {index + 1}. {step.title}
                </strong>
                <span>{step.body}</span>
              </div>
            ))}
          </div>

          <div className="rx-rules-card">
            <h3>Before you upload</h3>
            <ul className="clean-list">
              {uploadPrescriptionContent.beforeUpload.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          </div>

          <div className="rx-guidance-grid">
            {uploadPrescriptionContent.guidanceCards.map((item) => (
              <article key={item.title} className="rx-guidance-card">
                <strong>{item.title}</strong>
                <p>{item.body}</p>
              </article>
            ))}
          </div>
        </div>

        <PrescriptionUploadForm />
      </section>
    </main>
  );
}
