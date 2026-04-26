"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { CheckoutStepper } from "@/components/checkout-stepper";
import { useCart } from "@/components/cart-provider";
import { OrderSummaryCard } from "@/components/order-summary-card";
import { useAuthSession } from "@/hooks/use-auth-session";
import {
  AUTH_REDIRECT_STORAGE_KEY,
  createPaymentMethod,
  fetchPaymentMethods,
  getStoredAuthToken,
  type ApiSavedPaymentMethod
} from "@/lib/api";

export default function CheckoutPaymentPage() {
  const router = useRouter();
  const session = useAuthSession();
  const { paymentMethod, setPaymentMethod, upiId, setUpiId } = useCart();
  const [savedMethods, setSavedMethods] = useState<ApiSavedPaymentMethod[]>([]);
  const [errorMessage, setErrorMessage] = useState("");
  const [successMessage, setSuccessMessage] = useState("");
  const [savingMethod, setSavingMethod] = useState(false);
  const [verifyingUpi, setVerifyingUpi] = useState(false);
  const [isUpiVerified, setIsUpiVerified] = useState(false);

  useEffect(() => {
    if (!session.hydrated || session.isAuthenticated) {
      return;
    }

    window.sessionStorage.setItem(AUTH_REDIRECT_STORAGE_KEY, "/checkout/payment");
    router.replace("/login");
  }, [router, session.hydrated, session.isAuthenticated]);

  const methods = [
    {
      key: "UPI",
      title: "UPI",
      description: "Fast, preferred, and often eligible for instant offers."
    },
    {
      key: "CARD",
      title: "Credit / Debit Card",
      description: "Secure card checkout through gateway integration."
    },
    {
      key: "COD",
      title: "Cash on Delivery",
      description: "Available only for eligible orders and pincodes."
    },
    {
      key: "WALLET",
      title: "Wallet",
      description: "Use cashback offers and wallet promotions."
    }
  ] as const;

  useEffect(() => {
    if (!getStoredAuthToken()) {
      return;
    }

    void fetchPaymentMethods()
      .then((data) => setSavedMethods(data))
      .catch(() => {
        // keep checkout usable even if saved method fetch fails
      });
  }, []);

  useEffect(() => {
    if (paymentMethod !== "UPI") {
      return;
    }

    setIsUpiVerified(false);
  }, [paymentMethod, upiId]);

  if (!session.hydrated || !session.isAuthenticated) {
    return null;
  }

  async function handleVerifyUpi() {
    setErrorMessage("");
    setSuccessMessage("");

    const candidate = upiId.trim().toLowerCase();
    const upiPattern = /^[a-z0-9._-]{2,256}@[a-z]{2,64}$/i;

    if (!candidate) {
      setErrorMessage("Enter a UPI ID before verifying.");
      setIsUpiVerified(false);
      return;
    }

    if (!upiPattern.test(candidate)) {
      setErrorMessage("Enter a valid UPI ID like name@bank.");
      setIsUpiVerified(false);
      return;
    }

    setVerifyingUpi(true);

    try {
      await new Promise((resolve) => setTimeout(resolve, 350));
      setUpiId(candidate);
      setIsUpiVerified(true);
      setSuccessMessage("UPI ID verified for checkout.");
    } finally {
      setVerifyingUpi(false);
    }
  }

  async function handleSaveMethod() {
    setErrorMessage("");
    setSuccessMessage("");

    if (!getStoredAuthToken()) {
      setErrorMessage("Login to save payment methods for future orders.");
      return;
    }

    if (paymentMethod === "UPI" && !upiId.trim()) {
      setErrorMessage("Enter a valid UPI ID before saving.");
      return;
    }

    setSavingMethod(true);

    try {
      const created = await createPaymentMethod(
        paymentMethod === "UPI"
          ? {
              method_type: "UPI",
              label: `UPI - ${upiId.trim()}`,
              upi_id: upiId.trim(),
              is_default: savedMethods.length === 0
            }
          : paymentMethod === "CARD"
            ? {
                method_type: "CARD",
                label: "Primary card",
                masked_details: "**** **** **** 4242",
                is_default: savedMethods.length === 0
              }
            : {
                method_type: "WALLET",
                label: "Wallet balance",
                masked_details: "Wallet",
                is_default: savedMethods.length === 0
              }
      );

      setSavedMethods((current) => [created, ...current.filter((item) => item.id !== created.id)]);
      setSuccessMessage("Payment method saved.");
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Could not save payment method.");
    } finally {
      setSavingMethod(false);
    }
  }

  return (
    <main className="page-shell">
      <div className="breadcrumb">Home / Checkout / Payment</div>
      <CheckoutStepper current="payment" />

      <section className="checkout-layout">
        <div className="checkout-main">
          <div className="section-title-row">
            <div>
              <h1 className="page-title">Choose payment method</h1>
              <p>Pick the payment method for this order and optionally save it for later.</p>
            </div>
          </div>

          {savedMethods.length > 0 ? (
            <section className="review-card wide" style={{ marginBottom: 20 }}>
              <h3>Saved payment methods</h3>
              <div className="payment-methods">
                {savedMethods.map((method) => (
                  <button
                    key={method.id}
                    type="button"
                    className={`payment-card ${paymentMethod === method.method_type && (method.method_type !== "UPI" || upiId === method.upi_id) ? "active" : ""}`}
                    onClick={() => {
                      setPaymentMethod(method.method_type);
                      if (method.method_type === "UPI") {
                        setUpiId(method.upi_id);
                      }
                    }}
                  >
                    <strong>{method.label}</strong>
                    <p>{method.upi_id || method.masked_details || method.method_type}</p>
                  </button>
                ))}
              </div>
            </section>
          ) : null}

          <div className="payment-methods">
            {methods.map((method) => (
              <button
                key={method.key}
                type="button"
                className={`payment-card ${paymentMethod === method.key ? "active" : ""}`}
                onClick={() => setPaymentMethod(method.key)}
              >
                <strong>{method.title}</strong>
                <p>{method.description}</p>
              </button>
            ))}
          </div>

          <div className="gateway-box">
            <strong>Selected: {methods.find((method) => method.key === paymentMethod)?.title}</strong>
            <p>
              {paymentMethod === "UPI"
                ? "Recommended for faster checkout and better payment success rate."
                : paymentMethod === "COD"
                  ? "Cash collection happens on delivery only if the order and pincode are eligible."
                  : "You can continue to review and confirm this payment choice before placing the order."}
            </p>
            {paymentMethod === "UPI" ? (
              <div className="delivery-inline">
                <input
                  value={upiId}
                  onChange={(event) => {
                    setUpiId(event.target.value);
                    if (errorMessage) {
                      setErrorMessage("");
                    }
                    if (successMessage) {
                      setSuccessMessage("");
                    }
                  }}
                  className="checkout-inline-input"
                  placeholder="Enter UPI ID"
                />
                <button type="button" className="primary-action" onClick={handleVerifyUpi} disabled={verifyingUpi}>
                  {verifyingUpi ? "Verifying..." : isUpiVerified ? "Verified" : "Verify"}
                </button>
              </div>
            ) : null}

            {paymentMethod !== "COD" ? (
              <div className="success-actions" style={{ marginTop: 16 }}>
                <button type="button" className="secondary-action" onClick={handleSaveMethod} disabled={savingMethod}>
                  {savingMethod ? "Saving..." : "Save for later"}
                </button>
              </div>
            ) : null}

            {errorMessage ? <p className="auth-error" style={{ marginTop: 12 }}>{errorMessage}</p> : null}
            {!errorMessage && successMessage ? (
              <p className="auth-success" style={{ marginTop: 12 }}>{successMessage}</p>
            ) : null}
          </div>
        </div>

        <OrderSummaryCard
          ctaLabel="Continue to Review"
          ctaHref="/checkout/review"
          helperText="Payment is confirmed only after the final review step."
        />
      </section>
    </main>
  );
}
