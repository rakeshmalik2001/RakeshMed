"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { DegradedState } from "@/components/degraded-state";
import { LoadingPanel } from "@/components/loading-panel";
import {
  createPaymentMethod,
  deletePaymentMethod,
  fetchPaymentMethods,
  getStoredAuthToken,
  updatePaymentMethod,
  type ApiSavedPaymentMethod
} from "@/lib/api";

import styles from "./page.module.css";

type MethodType = "UPI" | "CARD" | "WALLET";

function getMethodDescription(option: MethodType) {
  if (option === "UPI") {
    return "Fast bank collection with your preferred UPI handle.";
  }

  if (option === "CARD") {
    return "Keep a masked debit or credit card ready for checkout.";
  }

  return "Choose a wallet preference for quick repeat purchases.";
}

export default function AccountPaymentMethodsPage() {
  const [methods, setMethods] = useState<ApiSavedPaymentMethod[]>([]);
  const [methodType, setMethodType] = useState<MethodType>("UPI");
  const [label, setLabel] = useState("");
  const [upiId, setUpiId] = useState("");
  const [maskedDetails, setMaskedDetails] = useState("");
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");
  const [successMessage, setSuccessMessage] = useState("");
  const isAuthenticated = Boolean(getStoredAuthToken());

  useEffect(() => {
    if (!isAuthenticated) {
      setIsLoading(false);
      return;
    }

    void fetchPaymentMethods()
      .then((data) => {
        setMethods(data);
        setErrorMessage("");
      })
      .catch((error: Error) => setErrorMessage(error.message))
      .finally(() => setIsLoading(false));
  }, [isAuthenticated]);

  async function handleSaveMethod() {
    setErrorMessage("");
    setSuccessMessage("");
    setIsSaving(true);

    try {
      const created = await createPaymentMethod({
        method_type: methodType,
        label: label || (methodType === "UPI" ? "Primary UPI" : methodType === "CARD" ? "Primary Card" : "Wallet"),
        upi_id: methodType === "UPI" ? upiId : undefined,
        masked_details: methodType !== "UPI" ? maskedDetails || (methodType === "CARD" ? "**** **** **** 4242" : "Wallet balance") : undefined,
        is_default: methods.length === 0
      });
      setMethods((current) => [created, ...current.map((item) => ({ ...item, is_default: created.is_default ? false : item.is_default }))]);
      setLabel("");
      setUpiId("");
      setMaskedDetails("");
      setSuccessMessage("Payment method saved.");
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Could not save payment method.");
    } finally {
      setIsSaving(false);
    }
  }

  async function makeDefault(method: ApiSavedPaymentMethod) {
    setErrorMessage("");
    setSuccessMessage("");

    try {
      const updated = await updatePaymentMethod(method.id, { is_default: true });
      setMethods((current) => current.map((item) => (item.id === updated.id ? updated : { ...item, is_default: false })));
      setSuccessMessage(`${updated.label} is now your default payment method.`);
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Could not update payment method.");
    }
  }

  async function removeMethod(methodId: number) {
    setErrorMessage("");
    setSuccessMessage("");

    try {
      await deletePaymentMethod(methodId);
      setMethods((current) => current.filter((item) => item.id !== methodId));
      setSuccessMessage("Payment method removed.");
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Could not remove payment method.");
    }
  }

  const summaryCards = [
    {
      label: "Saved methods",
      value: String(methods.length),
      meta: "Ready for faster repeat checkout"
    },
    {
      label: "Default method",
      value: methods.find((method) => method.is_default)?.label ?? "Not set",
      meta: "Used first at checkout"
    },
    {
      label: "Active methods",
      value: String(methods.filter((method) => method.is_active).length),
      meta: "Available for your next order"
    }
  ];

  return (
    <main className={`page-shell ${styles.paymentPage}`}>
      <div className={`breadcrumb ${styles.breadcrumb}`}>Home / Account / Payment Methods</div>

      <section className={`soft-section ${styles.paymentShell}`}>
        <div className={styles.heroHeader}>
          <div>
            <p className="eyebrow">Account</p>
            <h1 className={`page-title ${styles.heroTitle}`}>Saved payment methods</h1>
            <p className={styles.heroCopy}>
              Keep your preferred UPI, card, or wallet choices ready so repeat medicine purchases take fewer steps.
            </p>
          </div>
          <div className={styles.heroActions}>
            <Link href="/account" className={styles.primaryAction}>
              Back to account
            </Link>
            <Link href="/cart" className={styles.secondaryAction}>
              Open cart
            </Link>
          </div>
        </div>

        {!isAuthenticated ? (
          <div className="empty-cart-box">
            <h2>Login to manage payment methods</h2>
            <p>Saved UPI, card, and wallet choices will appear here after OTP login.</p>
            <div className="success-actions">
              <Link href="/login" className="primary-action">
                Login
              </Link>
            </div>
          </div>
        ) : isLoading ? (
          <LoadingPanel
            title="Loading payment methods"
            description="Fetching your saved checkout preferences."
          />
        ) : errorMessage && methods.length === 0 ? (
          <DegradedState
            title="Could not load payment methods"
            description={errorMessage}
            onRetry={() => {
              setIsLoading(true);
              setErrorMessage("");
              void fetchPaymentMethods()
                .then((data) => {
                  setMethods(data);
                  setErrorMessage("");
                })
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
                  <p className={styles.panelKicker}>Add method</p>
                  <h2>Save a payment preference</h2>
                </div>
              </div>

              <div className={styles.methodSelector}>
                {(["UPI", "CARD", "WALLET"] as MethodType[]).map((option) => (
                  <button
                    key={option}
                    type="button"
                    className={methodType === option ? styles.methodCardActive : styles.methodCard}
                    onClick={() => setMethodType(option)}
                  >
                    <span>{option}</span>
                    <strong>
                      {option === "UPI"
                        ? "UPI"
                        : option === "CARD"
                          ? "Card"
                          : "Wallet"}
                    </strong>
                    <p>{getMethodDescription(option)}</p>
                  </button>
                ))}
              </div>

              <div className={styles.formGrid}>
                <label className={styles.field}>
                  <span>Label</span>
                  <input value={label} onChange={(event) => setLabel(event.target.value)} placeholder="Primary UPI" />
                </label>
                {methodType === "UPI" ? (
                  <label className={styles.field}>
                    <span>UPI ID</span>
                    <input value={upiId} onChange={(event) => setUpiId(event.target.value)} placeholder="name@upi" />
                  </label>
                ) : (
                  <label className={styles.field}>
                    <span>{methodType === "CARD" ? "Masked card" : "Wallet detail"}</span>
                    <input
                      value={maskedDetails}
                      onChange={(event) => setMaskedDetails(event.target.value)}
                      placeholder={methodType === "CARD" ? "**** **** **** 4242" : "Wallet balance"}
                    />
                  </label>
                )}
              </div>

              <div className={styles.actionRow}>
                <button type="button" className={styles.primaryButton} onClick={handleSaveMethod} disabled={isSaving}>
                  {isSaving ? "Saving..." : "Save payment method"}
                </button>
                <button
                  type="button"
                  className={styles.secondaryButton}
                  onClick={() => {
                    setLabel("");
                    setUpiId("");
                    setMaskedDetails("");
                  }}
                  disabled={isSaving}
                >
                  Clear form
                </button>
              </div>

              {errorMessage ? <div className={styles.errorBox}>{errorMessage}</div> : null}
              {!errorMessage && successMessage ? <div className={styles.successBox}>{successMessage}</div> : null}
            </section>

            {methods.length === 0 ? (
              <section className={styles.listPanel}>
                <div className={styles.panelHeader}>
                  <div>
                    <p className={styles.panelKicker}>Saved list</p>
                    <h2>Your payment methods</h2>
                  </div>
                </div>
                <div className={styles.emptyState}>No saved methods yet. Add your preferred option to speed up checkout.</div>
              </section>
            ) : (
              <section className={styles.listPanel}>
                <div className={styles.panelHeader}>
                  <div>
                    <p className={styles.panelKicker}>Saved list</p>
                    <h2>Your payment methods</h2>
                  </div>
                </div>

                <div className={styles.methodGrid}>
                  {methods.map((method) => (
                    <article key={method.id} className={method.is_default ? styles.savedCardDefault : styles.savedCard}>
                      <div className={styles.savedCardHeader}>
                        <div>
                          <p className={styles.savedCardKicker}>{method.method_type}</p>
                          <h3>{method.label}</h3>
                          <p className={styles.savedCardMeta}>
                            {method.upi_id || method.masked_details || method.method_type}
                          </p>
                        </div>
                        {method.is_default ? <span className={styles.defaultBadge}>Default</span> : null}
                      </div>

                      <div className={styles.savedCardInfo}>
                        <div className={styles.infoCard}>
                          <span>Type</span>
                          <strong>{method.method_type}</strong>
                        </div>
                        <div className={styles.infoCard}>
                          <span>Status</span>
                          <strong>{method.is_active ? "Active" : "Inactive"}</strong>
                        </div>
                      </div>

                      <div className={styles.actionRow}>
                        {!method.is_default ? (
                          <button type="button" className={styles.secondaryButton} onClick={() => makeDefault(method)}>
                            Make default
                          </button>
                        ) : (
                          <span className={styles.positiveNote}>Primary checkout method</span>
                        )}
                        <button type="button" className={styles.ghostButton} onClick={() => removeMethod(method.id)}>
                          Remove
                        </button>
                      </div>
                    </article>
                  ))}
                </div>
              </section>
            )}
          </div>
        )}
      </section>
    </main>
  );
}
