"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import { DegradedState } from "@/components/degraded-state";
import { LoadingPanel } from "@/components/loading-panel";
import {
  createAddress,
  deleteAddress,
  fetchAddresses,
  getStoredAuthToken,
  updateAddress,
  type ApiAddress
} from "@/lib/api";

import styles from "./page.module.css";

const initialForm = {
  label: "",
  recipient: "",
  line1: "",
  city: "",
  state: "",
  pincode: "",
  phone_number: ""
};

function buildAddressSummary(address: ApiAddress) {
  return [address.line1, address.city, address.state, address.pincode].filter(Boolean).join(", ");
}

export default function AccountAddressesPage() {
  const [addresses, setAddresses] = useState<ApiAddress[]>([]);
  const [form, setForm] = useState(initialForm);
  const [editingAddressId, setEditingAddressId] = useState<number | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");
  const [successMessage, setSuccessMessage] = useState("");
  const isAuthenticated = Boolean(getStoredAuthToken());

  const defaultAddressId = useMemo(
    () => addresses.find((address) => address.is_default)?.id ?? addresses[0]?.id ?? null,
    [addresses]
  );

  async function loadAddresses() {
    const data = await fetchAddresses();
    setAddresses(data);
    setErrorMessage("");
  }

  useEffect(() => {
    if (!isAuthenticated) {
      setIsLoading(false);
      return;
    }

    void loadAddresses()
      .catch((error: Error) => setErrorMessage(error.message))
      .finally(() => setIsLoading(false));
  }, [isAuthenticated]);

  async function handleCreateAddress() {
    setErrorMessage("");
    setSuccessMessage("");
    setIsSaving(true);

    try {
      if (editingAddressId) {
        const updated = await updateAddress(editingAddressId, form);
        setAddresses((current) =>
          current.map((item) => (item.id === updated.id ? updated : item))
        );
        setSuccessMessage(`${updated.label} updated successfully.`);
      } else {
        const created = await createAddress({
          ...form,
          is_default: addresses.length === 0
        });
        setAddresses((current) => [
          created,
          ...current.map((item) => ({
            ...item,
            is_default: created.is_default ? false : item.is_default
          }))
        ]);
        setSuccessMessage("Address saved to your account.");
      }

      setForm(initialForm);
      setEditingAddressId(null);
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : editingAddressId ? "Could not update address." : "Could not save address.");
    } finally {
      setIsSaving(false);
    }
  }

  function beginEdit(address: ApiAddress) {
    setErrorMessage("");
    setSuccessMessage("");
    setEditingAddressId(address.id);
    setForm({
      label: address.label ?? "",
      recipient: address.recipient ?? "",
      line1: address.line1 ?? "",
      city: address.city ?? "",
      state: address.state ?? "",
      pincode: address.pincode ?? "",
      phone_number: address.phone_number ?? ""
    });
  }

  function resetForm() {
    setForm(initialForm);
    setEditingAddressId(null);
    setErrorMessage("");
    setSuccessMessage("");
  }

  async function makeDefault(address: ApiAddress) {
    setErrorMessage("");
    setSuccessMessage("");

    try {
      const updated = await updateAddress(address.id, { is_default: true });
      setAddresses((current) =>
        current.map((item) => (item.id === updated.id ? updated : { ...item, is_default: false }))
      );
      setSuccessMessage(`${updated.label} is now your default delivery address.`);
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Could not update default address.");
    }
  }

  async function removeAddress(addressId: number) {
    setErrorMessage("");
    setSuccessMessage("");

    try {
      await deleteAddress(addressId);
      setAddresses((current) => current.filter((item) => item.id !== addressId));
      setSuccessMessage("Address removed.");
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Could not remove address.");
    }
  }

  const summaryCards = [
    {
      label: "Saved addresses",
      value: String(addresses.length),
      meta: "Delivery locations ready for checkout"
    },
    {
      label: "Default address",
      value: addresses.find((address) => address.is_default)?.label ?? "Not set",
      meta: "Used first during checkout"
    },
    {
      label: "Cities covered",
      value: String(new Set(addresses.map((address) => address.city).filter(Boolean)).size),
      meta: "Useful when you split deliveries between home and work"
    }
  ];

  return (
    <main className={`page-shell ${styles.addressesPage}`}>
      <div className={`breadcrumb ${styles.breadcrumb}`}>Home / Account / Addresses</div>

      <section className={`soft-section ${styles.addressesShell}`}>
        <div className={styles.heroHeader}>
          <div>
            <p className="eyebrow">Account</p>
            <h1 className={`page-title ${styles.heroTitle}`}>Saved addresses</h1>
            <p className={styles.heroCopy}>
              Keep home, work, and family delivery locations ready so checkout stays fast and mistakes stay low.
            </p>
          </div>
          <div className={styles.heroActions}>
            <Link href="/account" className={styles.primaryAction}>
              Back to account
            </Link>
            <Link href="/cart" className={styles.secondaryAction}>
              Go to cart
            </Link>
          </div>
        </div>

        {!isAuthenticated ? (
          <div className="empty-cart-box">
            <h2>Login to manage addresses</h2>
            <p>Your delivery locations will appear here after customer login.</p>
            <div className="success-actions">
              <Link href="/login" className="primary-action">
                Login
              </Link>
            </div>
          </div>
        ) : isLoading ? (
          <LoadingPanel
            title="Loading saved addresses"
            description="Fetching your delivery locations and checkout defaults."
          />
        ) : errorMessage && addresses.length === 0 ? (
          <DegradedState
            title="Could not load addresses"
            description={errorMessage}
            onRetry={() => {
              setIsLoading(true);
              setErrorMessage("");
              void loadAddresses()
                .catch((error: Error) => setErrorMessage(error.message))
                .finally(() => setIsLoading(false));
            }}
            secondaryHref="/account"
            secondaryLabel="Back to account"
          />
        ) : (
          <div className={styles.contentGrid}>
            <section className={styles.summaryGrid}>
              {summaryCards.map((card) => (
                <article key={card.label} className={styles.summaryCard}>
                  <p>{card.label}</p>
                  <strong>{card.value}</strong>
                  <span>{card.meta}</span>
                </article>
              ))}
            </section>

            <section className={styles.formPanel}>
              <div className={styles.panelHeader}>
                <div>
                  <p className={styles.panelKicker}>{editingAddressId ? "Edit address" : "Add address"}</p>
                  <h2>{editingAddressId ? "Update this delivery location" : "Create a new delivery location"}</h2>
                </div>
              </div>

              <div className={styles.formGrid}>
                <label className={styles.field}>
                  <span>Label</span>
                  <input
                    value={form.label}
                    onChange={(event) => setForm((current) => ({ ...current, label: event.target.value }))}
                    placeholder="Home, Work, Parents"
                  />
                </label>
                <label className={styles.field}>
                  <span>Recipient</span>
                  <input
                    value={form.recipient}
                    onChange={(event) => setForm((current) => ({ ...current, recipient: event.target.value }))}
                    placeholder="Full name"
                  />
                </label>
                <label className={`${styles.field} ${styles.fieldWide}`}>
                  <span>Address line</span>
                  <input
                    value={form.line1}
                    onChange={(event) => setForm((current) => ({ ...current, line1: event.target.value }))}
                    placeholder="House number, street, landmark"
                  />
                </label>
                <label className={styles.field}>
                  <span>City</span>
                  <input
                    value={form.city}
                    onChange={(event) => setForm((current) => ({ ...current, city: event.target.value }))}
                    placeholder="Mumbai"
                  />
                </label>
                <label className={styles.field}>
                  <span>State</span>
                  <input
                    value={form.state}
                    onChange={(event) => setForm((current) => ({ ...current, state: event.target.value }))}
                    placeholder="Maharashtra"
                  />
                </label>
                <label className={styles.field}>
                  <span>Pincode</span>
                  <input
                    value={form.pincode}
                    onChange={(event) => setForm((current) => ({ ...current, pincode: event.target.value }))}
                    placeholder="400001"
                  />
                </label>
                <label className={styles.field}>
                  <span>Phone number</span>
                  <input
                    value={form.phone_number}
                    onChange={(event) => setForm((current) => ({ ...current, phone_number: event.target.value }))}
                    placeholder="9876543210"
                  />
                </label>
              </div>

              <div className={styles.actionRow}>
                <button type="button" className={styles.primaryButton} onClick={handleCreateAddress} disabled={isSaving}>
                  {isSaving ? (editingAddressId ? "Updating..." : "Saving...") : editingAddressId ? "Update address" : "Save address"}
                </button>
                <button type="button" className={styles.secondaryButton} onClick={resetForm} disabled={isSaving}>
                  {editingAddressId ? "Cancel edit" : "Clear form"}
                </button>
              </div>

              {errorMessage ? <div className={styles.errorBox}>{errorMessage}</div> : null}
              {!errorMessage && successMessage ? <div className={styles.successBox}>{successMessage}</div> : null}
            </section>

            <section className={styles.listPanel}>
              <div className={styles.panelHeader}>
                <div>
                  <p className={styles.panelKicker}>Saved list</p>
                  <h2>Your delivery locations</h2>
                </div>
              </div>

              {addresses.length === 0 ? (
                <div className={styles.emptyState}>
                  No saved addresses yet. Add your first delivery location to speed up checkout.
                </div>
              ) : (
                <div className={styles.addressGrid}>
                  {addresses.map((address) => {
                    const isDefault = address.id === defaultAddressId;

                    return (
                      <article key={address.id} className={isDefault ? styles.addressCardDefault : styles.addressCard}>
                        <div className={styles.addressHeader}>
                          <div>
                            <p className={styles.addressEyebrow}>Delivery point</p>
                            <h3>{address.label}</h3>
                            <p className={styles.addressRecipient}>{address.recipient}</p>
                          </div>
                          {isDefault ? <span className={styles.defaultBadge}>Default</span> : null}
                        </div>

                        <div className={styles.infoStack}>
                          <div className={styles.infoCard}>
                            <span>Address</span>
                            <strong>{buildAddressSummary(address)}</strong>
                          </div>
                          <div className={styles.infoRow}>
                            <div className={styles.infoCard}>
                              <span>Phone</span>
                              <strong>{address.phone_number || "Not added"}</strong>
                            </div>
                            <div className={styles.infoCard}>
                              <span>State</span>
                              <strong>{address.state || "Not provided"}</strong>
                            </div>
                          </div>
                        </div>

                        <div className={styles.actionRow}>
                          <button type="button" className={styles.secondaryButton} onClick={() => beginEdit(address)}>
                            Edit
                          </button>
                          {!address.is_default ? (
                            <button type="button" className={styles.secondaryButton} onClick={() => makeDefault(address)}>
                              Make default
                            </button>
                          ) : (
                            <span className={styles.positiveNote}>Primary checkout address</span>
                          )}
                          <button type="button" className={styles.ghostButton} onClick={() => removeAddress(address.id)}>
                            Remove
                          </button>
                        </div>
                      </article>
                    );
                  })}
                </div>
              )}
            </section>
          </div>
        )}
      </section>
    </main>
  );
}
