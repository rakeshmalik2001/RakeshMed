"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { DegradedState } from "@/components/degraded-state";
import { LoadingPanel } from "@/components/loading-panel";
import {
  fetchAddresses,
  fetchMe,
  fetchNotifications,
  fetchOrders,
  fetchMyPrescriptions,
  getStoredAuthToken,
  logout,
  type ApiAddress,
  type ApiNotification,
  type ApiOrder,
  type ApiPrescriptionRecord,
  type AuthUser
} from "@/lib/api";

import styles from "./page.module.css";

function humanizeStatus(value?: string) {
  if (!value) {
    return "Not available";
  }

  return value.replace(/_/g, " ");
}

export default function AccountPage() {
  const router = useRouter();
  const [user, setUser] = useState<AuthUser | null>(null);
  const [orders, setOrders] = useState<ApiOrder[]>([]);
  const [addresses, setAddresses] = useState<ApiAddress[]>([]);
  const [notifications, setNotifications] = useState<ApiNotification[]>([]);
  const [prescriptions, setPrescriptions] = useState<ApiPrescriptionRecord[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isLoggingOut, setIsLoggingOut] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");
  const isAuthenticated = Boolean(getStoredAuthToken());

  async function loadAccountDashboard() {
    const [accountUser, accountOrders, accountAddresses, accountNotifications, accountPrescriptions] =
      await Promise.all([fetchMe(), fetchOrders(), fetchAddresses(), fetchNotifications(true), fetchMyPrescriptions()]);
    setUser(accountUser);
    setOrders(accountOrders);
    setAddresses(accountAddresses);
    setNotifications(accountNotifications);
    setPrescriptions(accountPrescriptions);
  }

  useEffect(() => {
    if (!isAuthenticated) {
      setIsLoading(false);
      return;
    }

    void loadAccountDashboard()
      .catch((error: Error) => {
        setErrorMessage(error.message);
      })
      .finally(() => {
        setIsLoading(false);
      });
  }, [isAuthenticated]);

  async function handleLogout() {
    setIsLoggingOut(true);
    setErrorMessage("");

    try {
      await logout();
      router.push("/login");
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Could not end your session.");
    } finally {
      setIsLoggingOut(false);
    }
  }

  const summaryCards = [
    {
      label: "Orders placed",
      value: String(orders.length),
      metaLabel: "Recent status",
      metaValue: orders[0] ? humanizeStatus(orders[0].status) : "No orders yet"
    },
    {
      label: "Prescription uploads",
      value: String(prescriptions.length),
      metaLabel: "Latest review state",
      metaValue: prescriptions[0] ? humanizeStatus(prescriptions[0].status) : "No uploads yet"
    },
    {
      label: "Saved addresses",
      value: String(addresses.length),
      metaLabel: "Default",
      metaValue: addresses.find((address) => address.is_default)?.label ?? "Not set"
    },
    {
      label: "Unread notifications",
      value: String(notifications.length),
      metaLabel: "Latest",
      metaValue: notifications[0]?.title ?? "No new updates"
    }
  ];

  const quickLinks = [
    { href: "/account/orders", label: "Order history", tone: "primary" },
    { href: "/account/addresses", label: "Saved addresses", tone: "secondary" },
    { href: "/account/payment-methods", label: "Payment methods", tone: "secondary" },
    { href: "/account/prescriptions", label: "Prescriptions", tone: "secondary" },
    { href: "/account/notifications", label: "Notifications", tone: "secondary" },
    { href: "/upload-prescription", label: "Upload prescription", tone: "secondary" }
  ] as const;

  return (
    <main className={`page-shell ${styles.accountPage}`}>
      <div className={`breadcrumb ${styles.breadcrumb}`}>Home / Account</div>

      <section className={`soft-section ${styles.heroPanel}`}>
        <div className={styles.heroHeader}>
          <div>
            <p className="eyebrow">Account</p>
            <h1 className={`page-title ${styles.heroTitle}`}>Customer account dashboard</h1>
            <p className={styles.heroCopy}>
              Keep track of orders, prescriptions, saved addresses, payment preferences, and account activity from one
              cleaner customer workspace.
            </p>
          </div>
          <div className={styles.heroActions}>
            <Link href="/account/orders" className={styles.heroActionPrimary}>
              View orders
            </Link>
            <Link href="/search" className={styles.heroActionSecondary}>
              Browse medicines
            </Link>
          </div>
        </div>

        {!isAuthenticated ? (
          <div className="empty-cart-box">
            <h2>Login to open your account</h2>
            <p>Orders, prescription uploads, saved addresses, and support shortcuts will appear here after OTP login.</p>
            <div className="success-actions">
              <Link href="/login" className="primary-action">
                Login
              </Link>
              <Link href="/search" className="secondary-action">
                Browse medicines
              </Link>
            </div>
          </div>
        ) : isLoading ? (
          <LoadingPanel
            title="Loading account details"
            description="Fetching customer profile, orders, addresses, notifications, and prescriptions."
          />
        ) : errorMessage ? (
          <DegradedState
            title="Could not load your account"
            description={errorMessage}
            onRetry={() => {
              setIsLoading(true);
              setErrorMessage("");
              void loadAccountDashboard()
                .catch((error: Error) => setErrorMessage(error.message))
                .finally(() => setIsLoading(false));
            }}
            secondaryHref="/search"
            secondaryLabel="Browse medicines"
          />
        ) : (
          <div className={styles.accountGrid}>
            <section className={styles.profileCard}>
              <div className={styles.profileHeader}>
                <div className={styles.profileBadge}>{(user?.full_name || "C").slice(0, 1).toUpperCase()}</div>
                <div>
                  <p className={styles.profileEyebrow}>Profile snapshot</p>
                  <h2>{user?.full_name || "Customer"}</h2>
                  <p className={styles.profileMeta}>{user?.phone_number}</p>
                </div>
              </div>
              <div className={styles.profileDetails}>
                <div>
                  <span>Role</span>
                  <strong>{user?.role ?? "customer"}</strong>
                </div>
                <div>
                  <span>Email</span>
                  <strong>{user?.email || "Not added"}</strong>
                </div>
              </div>
              <div className={styles.profileActions}>
                <Link href="/account/profile" className={styles.secondaryButton}>
                  Edit profile
                </Link>
                <button type="button" className={styles.secondaryButton} onClick={handleLogout} disabled={isLoggingOut}>
                  {isLoggingOut ? "Signing out..." : "Logout"}
                </button>
              </div>
            </section>

            <section className={styles.summaryGrid}>
              {summaryCards.map((card) => (
                <article key={card.label} className={styles.summaryCard}>
                  <p>{card.label}</p>
                  <strong>{card.value}</strong>
                  <div className={styles.summaryMeta}>
                    <span>{card.metaLabel}</span>
                    <b>{card.metaValue}</b>
                  </div>
                </article>
              ))}
            </section>

            <section className={styles.panel}>
              <div className={styles.panelHeader}>
                <div>
                  <p className={styles.panelKicker}>Quick actions</p>
                  <h3>Go where customers actually need to go</h3>
                </div>
              </div>
              <div className={styles.quickLinkGrid}>
                {quickLinks.map((link) => (
                  <Link
                    key={link.href}
                    href={link.href}
                    className={link.tone === "primary" ? styles.primaryQuickLink : styles.quickLink}
                  >
                    {link.label}
                  </Link>
                ))}
              </div>
            </section>

            <section className={styles.panel}>
              <div className={styles.panelHeader}>
                <div>
                  <p className={styles.panelKicker}>Orders</p>
                  <h3>Latest order activity</h3>
                </div>
                <Link href="/account/orders" className={styles.inlineLink}>
                  See all
                </Link>
              </div>
              <div className={styles.listShell}>
                {orders.slice(0, 4).map((order) => (
                  <div key={order.order_number} className={styles.listRow}>
                    <div>
                      <strong>{order.order_number}</strong>
                      <p>{order.created_at ? new Date(order.created_at).toLocaleString() : "Recently placed"}</p>
                    </div>
                    <span className={styles.statusPill}>{humanizeStatus(order.status)}</span>
                  </div>
                ))}
                {orders.length === 0 ? <div className={styles.emptyState}>No orders yet.</div> : null}
              </div>
            </section>

            <section className={styles.panel}>
              <div className={styles.panelHeader}>
                <div>
                  <p className={styles.panelKicker}>Prescriptions</p>
                  <h3>Recent uploads and review states</h3>
                </div>
                <Link href="/account/prescriptions" className={styles.inlineLink}>
                  See all
                </Link>
              </div>
              <div className={styles.listShell}>
                {prescriptions.slice(0, 4).map((prescription) => (
                  <div key={prescription.id} className={styles.listRow}>
                    <div>
                      <strong>{prescription.reference_code}</strong>
                      <p>{prescription.patient_name || "Prescription upload"}</p>
                    </div>
                    <span className={styles.statusPill}>{humanizeStatus(prescription.status)}</span>
                  </div>
                ))}
                {prescriptions.length === 0 ? <div className={styles.emptyState}>No prescriptions uploaded yet.</div> : null}
              </div>
            </section>

            <section className={styles.panel}>
              <div className={styles.panelHeader}>
                <div>
                  <p className={styles.panelKicker}>Addresses</p>
                  <h3>Delivery preferences</h3>
                </div>
                <Link href="/account/addresses" className={styles.inlineLink}>
                  Manage
                </Link>
              </div>
              <div className={styles.listShell}>
                {addresses.slice(0, 3).map((address) => (
                  <div key={address.id} className={styles.listRow}>
                    <div>
                      <strong>{address.label}</strong>
                      <p>
                        {address.line1}, {address.city} {address.pincode}
                      </p>
                    </div>
                    {address.is_default ? <span className={styles.statusPill}>Default</span> : null}
                  </div>
                ))}
                {addresses.length === 0 ? <div className={styles.emptyState}>No saved addresses yet.</div> : null}
              </div>
            </section>

            <section className={styles.panel}>
              <div className={styles.panelHeader}>
                <div>
                  <p className={styles.panelKicker}>Notifications</p>
                  <h3>Latest updates</h3>
                </div>
                <Link href="/account/notifications" className={styles.inlineLink}>
                  Open inbox
                </Link>
              </div>
              <div className={styles.listShell}>
                {notifications.slice(0, 4).map((notification) => (
                  <div key={notification.id} className={styles.listRow}>
                    <div>
                      <strong>{notification.title}</strong>
                      <p>{notification.body}</p>
                    </div>
                    {!notification.is_read ? <span className={styles.statusPill}>Unread</span> : null}
                  </div>
                ))}
                {notifications.length === 0 ? <div className={styles.emptyState}>No new updates.</div> : null}
              </div>
            </section>
          </div>
        )}
      </section>
    </main>
  );
}
