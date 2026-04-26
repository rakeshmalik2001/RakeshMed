"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { DegradedState } from "@/components/degraded-state";
import { LoadingPanel } from "@/components/loading-panel";
import { fetchMe, getStoredAuthToken, updateMe, type AuthUser } from "@/lib/api";

import styles from "./page.module.css";

export default function AccountProfilePage() {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");
  const [successMessage, setSuccessMessage] = useState("");
  const isAuthenticated = Boolean(getStoredAuthToken());

  async function loadProfile() {
    const accountUser = await fetchMe();
    setUser(accountUser);
    setFullName(accountUser.full_name ?? "");
    setEmail(accountUser.email ?? "");
  }

  useEffect(() => {
    if (!isAuthenticated) {
      setIsLoading(false);
      return;
    }

    void loadProfile()
      .catch((error: Error) => setErrorMessage(error.message))
      .finally(() => setIsLoading(false));
  }, [isAuthenticated]);

  async function handleSaveProfile() {
    setErrorMessage("");
    setSuccessMessage("");
    setIsSaving(true);

    try {
      const updated = await updateMe({
        full_name: fullName.trim(),
        email: email.trim()
      });
      setUser(updated);
      setSuccessMessage("Profile updated.");
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Could not update profile.");
    } finally {
      setIsSaving(false);
    }
  }

  return (
    <main className={`page-shell ${styles.profilePage}`}>
      <div className={`breadcrumb ${styles.breadcrumb}`}>Home / Account / Profile</div>

      <section className={`soft-section ${styles.profileShell}`}>
        <div className={styles.heroHeader}>
          <div>
            <p className="eyebrow">Account</p>
            <h1 className={`page-title ${styles.heroTitle}`}>Profile settings</h1>
            <p className={styles.heroCopy}>
              Keep your customer details up to date so checkout, prescription communication, and support follow-ups stay
              accurate.
            </p>
          </div>
          <div className={styles.heroActions}>
            <Link href="/account" className={styles.primaryAction}>
              Back to account
            </Link>
            <Link href="/account/orders" className={styles.secondaryAction}>
              View orders
            </Link>
          </div>
        </div>

        {!isAuthenticated ? (
          <div className="empty-cart-box">
            <h2>Login to manage your profile</h2>
            <p>Your phone number, name, and email preferences will appear here after OTP login.</p>
            <div className="success-actions">
              <Link href="/login" className="primary-action">
                Login
              </Link>
            </div>
          </div>
        ) : isLoading ? (
          <LoadingPanel title="Loading profile" description="Fetching your account information." />
        ) : errorMessage && !user ? (
          <DegradedState
            title="Could not load profile"
            description={errorMessage}
            onRetry={() => {
              setIsLoading(true);
              setErrorMessage("");
              void loadProfile()
                .catch((error: Error) => setErrorMessage(error.message))
                .finally(() => setIsLoading(false));
            }}
            secondaryHref="/account"
            secondaryLabel="Back to account"
          />
        ) : (
          <div className={styles.profileGrid}>
            <section className={styles.profileCard}>
              <div className={styles.profileHeader}>
                <div className={styles.profileBadge}>{(user?.full_name || "C").slice(0, 1).toUpperCase()}</div>
                <div>
                  <p className={styles.profileEyebrow}>Customer profile</p>
                  <h2>{user?.full_name || "Customer"}</h2>
                  <p className={styles.profileMeta}>{user?.phone_number}</p>
                </div>
              </div>
              <div className={styles.profileHighlights}>
                <div>
                  <span>Role</span>
                  <strong>{user?.role || "customer"}</strong>
                </div>
                <div>
                  <span>Phone verified</span>
                  <strong>{user?.is_phone_verified ? "Verified" : "Pending"}</strong>
                </div>
              </div>
            </section>

            <section className={styles.formPanel}>
              <div className={styles.panelHeader}>
                <div>
                  <p className={styles.panelKicker}>Profile form</p>
                  <h3>Update your saved details</h3>
                </div>
              </div>

              <div className={styles.formGrid}>
                <label className={styles.field}>
                  <span>Phone number</span>
                  <input value={user?.phone_number ?? ""} disabled />
                  <small>Phone number is tied to OTP login and cannot be edited here.</small>
                </label>
                <label className={styles.field}>
                  <span>Full name</span>
                  <input value={fullName} onChange={(event) => setFullName(event.target.value)} placeholder="Your full name" />
                </label>
                <label className={`${styles.field} ${styles.fieldWide}`}>
                  <span>Email</span>
                  <input value={email} onChange={(event) => setEmail(event.target.value)} placeholder="name@example.com" />
                  <small>Used for receipts, account updates, and password reset support.</small>
                </label>
              </div>

              <div className={styles.actionRow}>
                <button type="button" className={styles.primaryButton} onClick={handleSaveProfile} disabled={isSaving}>
                  {isSaving ? "Saving..." : "Save profile"}
                </button>
                <Link href="/account" className={styles.secondaryButton}>
                  Cancel
                </Link>
              </div>

              {errorMessage ? <div className={styles.errorBox}>{errorMessage}</div> : null}
              {!errorMessage && successMessage ? <div className={styles.successBox}>{successMessage}</div> : null}
            </section>
          </div>
        )}
      </section>
    </main>
  );
}
