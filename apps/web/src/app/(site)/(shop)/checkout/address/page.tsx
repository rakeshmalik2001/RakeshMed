"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { CheckoutStepper } from "@/components/checkout-stepper";
import { useCart } from "@/components/cart-provider";
import { OrderSummaryCard } from "@/components/order-summary-card";
import { useAuthSession } from "@/hooks/use-auth-session";
import {
  AUTH_REDIRECT_STORAGE_KEY,
  createAddress,
  fetchServiceability,
  getStoredAuthToken,
  type ApiServiceability
} from "@/lib/api";

type AddressFormState = {
  label: string;
  recipient: string;
  line1: string;
  city: string;
  state: string;
  pincode: string;
  phoneNumber: string;
};

const initialForm: AddressFormState = {
  label: "Home",
  recipient: "",
  line1: "",
  city: "",
  state: "",
  pincode: "",
  phoneNumber: ""
};

export default function CheckoutAddressPage() {
  const router = useRouter();
  const session = useAuthSession();
  const { addresses, saveAddress, selectedAddressId, selectAddress } = useCart();
  const [showNewAddressForm, setShowNewAddressForm] = useState(false);
  const [form, setForm] = useState<AddressFormState>(initialForm);
  const [submitting, setSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");
  const [serviceability, setServiceability] = useState<ApiServiceability | null>(null);

  useEffect(() => {
    if (!session.hydrated || session.isAuthenticated) {
      return;
    }

    window.sessionStorage.setItem(AUTH_REDIRECT_STORAGE_KEY, "/checkout/address");
    router.replace("/login");
  }, [router, session.hydrated, session.isAuthenticated]);

  useEffect(() => {
    const activeAddress = addresses.find((item) => item.id === selectedAddressId);
    const pincode = activeAddress?.pincode || form.pincode;
    if (!pincode) {
      return;
    }
    void fetchServiceability(pincode)
      .then((data) => setServiceability(data))
      .catch(() => setServiceability(null));
  }, [addresses, selectedAddressId, form.pincode]);

  if (!session.hydrated || !session.isAuthenticated) {
    return null;
  }

  async function handleAddAddress() {
    setErrorMessage("");

    if (!form.recipient.trim() || !form.line1.trim() || !form.city.trim() || !form.pincode.trim()) {
      setErrorMessage("Complete recipient, address line, city, and pincode.");
      return;
    }

    setSubmitting(true);

    try {
      const token = getStoredAuthToken();

      if (token) {
        const address = await createAddress({
          label: form.label,
          recipient: form.recipient,
          line1: form.line1,
          city: form.city,
          state: form.state,
          pincode: form.pincode,
          phone_number: form.phoneNumber,
          is_default: addresses.length === 0
        });

        saveAddress({
          id: String(address.id),
          label: address.label,
          recipient: address.recipient,
          line1: address.line1,
          city: address.city,
          pincode: address.pincode,
          isDefault: address.is_default
        });
      } else {
        const nextId = `local-${Date.now()}`;
        saveAddress({
          id: nextId,
          label: form.label,
          recipient: form.recipient,
          line1: form.line1,
          city: form.city,
          pincode: form.pincode,
          isDefault: addresses.length === 0
        });
      }

      setForm(initialForm);
      setShowNewAddressForm(false);
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Could not save address.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="page-shell">
      <div className="breadcrumb">Home / Checkout / Address</div>
      <CheckoutStepper current="address" />

      <section className="checkout-layout">
        <div className="checkout-main">
          <div className="section-title-row">
            <div>
              <h1 className="page-title">Select delivery address</h1>
              <p>Choose a saved address or add a new one for this order.</p>
            </div>
          </div>

          <div className="address-grid">
            {addresses.length === 0 ? (
              <article className="address-card">
                <strong>No saved addresses yet</strong>
                <p>Add a delivery address to continue with this order.</p>
              </article>
            ) : null}

            {addresses.map((address) => (
              <article
                key={address.id}
                className={`address-card ${selectedAddressId === address.id ? "active" : ""}`}
              >
                <div className="address-card-header">
                  <strong>{address.label}</strong>
                  {address.isDefault ? <span className="small-pill">Default</span> : null}
                </div>
                <p>
                  {address.recipient}, {address.line1}, {address.city} - {address.pincode}
                </p>
                <div className="address-card-actions">
                  <span>{selectedAddressId === address.id ? "Used for this order" : "Available for delivery"}</span>
                  <button type="button" className="address-select-button" onClick={() => selectAddress(address.id)}>
                    {selectedAddressId === address.id ? "Selected" : "Deliver here"}
                  </button>
                </div>
              </article>
            ))}

            <article className="address-card add-new">
              <strong>+ Add new address</strong>
              <p>Create a new delivery address and use it for this order.</p>
              <button
                type="button"
                className="secondary-action"
                onClick={() => setShowNewAddressForm((current) => !current)}
              >
                {showNewAddressForm ? "Close form" : "Add address"}
              </button>
            </article>
          </div>

          {showNewAddressForm ? (
            <section className="review-card wide" style={{ marginTop: 20 }}>
              <h3>Add delivery address</h3>
              <div className="rx-form-grid">
                <label className="rx-field">
                  <span>Label</span>
                  <input value={form.label} onChange={(event) => setForm((current) => ({ ...current, label: event.target.value }))} />
                </label>
                <label className="rx-field">
                  <span>Recipient</span>
                  <input value={form.recipient} onChange={(event) => setForm((current) => ({ ...current, recipient: event.target.value }))} />
                </label>
                <label className="rx-field wide">
                  <span>Address line</span>
                  <input value={form.line1} onChange={(event) => setForm((current) => ({ ...current, line1: event.target.value }))} />
                </label>
                <label className="rx-field">
                  <span>City</span>
                  <input value={form.city} onChange={(event) => setForm((current) => ({ ...current, city: event.target.value }))} />
                </label>
                <label className="rx-field">
                  <span>State</span>
                  <input value={form.state} onChange={(event) => setForm((current) => ({ ...current, state: event.target.value }))} />
                </label>
                <label className="rx-field">
                  <span>Pincode</span>
                  <input value={form.pincode} onChange={(event) => setForm((current) => ({ ...current, pincode: event.target.value }))} />
                </label>
                <label className="rx-field">
                  <span>Phone number</span>
                  <input value={form.phoneNumber} onChange={(event) => setForm((current) => ({ ...current, phoneNumber: event.target.value }))} />
                </label>
              </div>

              {errorMessage ? <p className="auth-error" style={{ marginTop: 12 }}>{errorMessage}</p> : null}

              <div className="success-actions" style={{ marginTop: 16 }}>
                <button type="button" className="primary-action" onClick={handleAddAddress} disabled={submitting}>
                  {submitting ? "Saving..." : "Save address"}
                </button>
                <button type="button" className="secondary-action" onClick={() => setShowNewAddressForm(false)}>
                  Cancel
                </button>
              </div>
            </section>
          ) : null}

          <div className="checkout-note">
            {serviceability?.is_serviceable
              ? `Delivery available${serviceability.zone?.name ? ` via ${serviceability.zone.name}` : ""}. ETA ${serviceability.eta_label}.${serviceability.cod_available ? " COD supported." : " COD not available."}`
              : "Delivery ETA and medicine availability will be revalidated for the selected pincode."}
          </div>
        </div>

        <OrderSummaryCard
          ctaLabel="Continue to Payment"
          ctaHref="/checkout/payment"
          ctaDisabled={addresses.length === 0}
          helperText="You can still change the address later from the review step."
        />
      </section>
    </main>
  );
}
