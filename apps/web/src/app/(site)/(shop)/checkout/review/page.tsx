"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { useCart } from "@/components/cart-provider";
import { CheckoutStepper } from "@/components/checkout-stepper";
import { OrderSummaryCard } from "@/components/order-summary-card";
import { useAuthSession } from "@/hooks/use-auth-session";
import { AUTH_REDIRECT_STORAGE_KEY, getStoredAuthToken } from "@/lib/api";

export default function CheckoutReviewPage() {
  const router = useRouter();
  const session = useAuthSession();
  const [errorMessage, setErrorMessage] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const {
    addresses,
    cartItems,
    paymentMethod,
    placeOrder,
    requiresPrescriptionCount,
    selectedAddressId,
    upiId
  } = useCart();
  const isAuthenticated = Boolean(getStoredAuthToken());
  const selectedAddress = addresses.find((address) => address.id === selectedAddressId) ?? addresses[0];
  const hasSelectedAddress = Boolean(selectedAddress);
  const paymentLabel =
    paymentMethod === "UPI"
      ? `UPI (${upiId})`
      : paymentMethod === "CARD"
        ? "Credit / Debit Card"
        : paymentMethod === "COD"
          ? "Cash on Delivery"
          : "Wallet";

  useEffect(() => {
    if (!session.hydrated || session.isAuthenticated) {
      return;
    }

    window.sessionStorage.setItem(AUTH_REDIRECT_STORAGE_KEY, "/checkout/review");
    router.replace("/login");
  }, [router, session.hydrated, session.isAuthenticated]);

  if (!session.hydrated || !session.isAuthenticated) {
    return null;
  }

  return (
    <main className="page-shell">
      <div className="breadcrumb">Home / Checkout / Review</div>
      <CheckoutStepper current="review" />

      <section className="checkout-layout">
        <div className="checkout-main">
          <div className="section-title-row">
            <h1 className="page-title">Review and place order</h1>
          </div>

          <div className="review-grid">
            <div className="review-card">
              <h3>Delivery address</h3>
              {selectedAddress ? (
                <p>
                  {selectedAddress.recipient}, {selectedAddress.line1}, {selectedAddress.city} - {selectedAddress.pincode}
                </p>
              ) : (
                <p>Add a delivery address before placing this order.</p>
              )}
              <Link href="/checkout/address" className="section-link">
                {selectedAddress ? "Change address" : "Add address"}
              </Link>
            </div>

            <div className="review-card">
              <h3>Payment method</h3>
              <p>{paymentLabel}</p>
              <Link href="/checkout/payment" className="section-link">
                Change payment
              </Link>
            </div>

            <div className="review-card wide">
              <h3>Prescription status</h3>
              <p>
                {requiresPrescriptionCount} medicine(s) require prescription review. Validation will
                continue after upload confirmation.
              </p>
              <div className="summary-row">
                <span>Attached prescription</span>
                <strong className="positive">
                  {requiresPrescriptionCount > 0 ? "Required" : "Not required"}
                </strong>
              </div>
            </div>

            <div className="review-card wide">
              <h3>Items in this order</h3>
              {cartItems.map((item) => (
                <div key={item.slug} className="review-item">
                  <span>
                    {item.name} x {item.qty}
                  </span>
                  <strong>Rs. {(Number(item.price) * item.qty).toFixed(2)}</strong>
                </div>
              ))}
            </div>
            {errorMessage ? (
              <div className="review-card wide">
                <h3>Could not place order</h3>
                <p>{errorMessage}</p>
              </div>
            ) : null}
          </div>
        </div>

        <OrderSummaryCard
          ctaLabel={isSubmitting ? "Placing order..." : "Place Order"}
          ctaDisabled={!isAuthenticated || !hasSelectedAddress || isSubmitting}
          helperText="You can still go back and change address or payment before placing the order."
          onCta={async () => {
            setErrorMessage("");
            setIsSubmitting(true);
            try {
              await placeOrder();
              router.push("/checkout/success");
            } catch (error) {
              setErrorMessage(error instanceof Error ? error.message : "Could not place your order.");
            } finally {
              setIsSubmitting(false);
            }
          }}
        />
      </section>
    </main>
  );
}
