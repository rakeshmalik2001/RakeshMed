type CheckoutStepperProps = {
  current: "address" | "payment" | "review" | "success";
};

const steps = [
  { id: "address", label: "Address" },
  { id: "payment", label: "Payment" },
  { id: "review", label: "Review" },
  { id: "success", label: "Success" }
] as const;

export function CheckoutStepper({ current }: CheckoutStepperProps) {
  const currentIndex = steps.findIndex((step) => step.id === current);

  return (
    <div className="checkout-stepper">
      {steps.map((step, index) => {
        const state =
          index < currentIndex ? "done" : index === currentIndex ? "active" : "upcoming";

        return (
          <div key={step.id} className={`step-item ${state}`}>
            <span className="step-badge">{index + 1}</span>
            <span>{step.label}</span>
          </div>
        );
      })}
    </div>
  );
}
