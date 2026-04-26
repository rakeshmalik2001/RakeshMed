"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { DegradedState } from "@/components/degraded-state";
import { LoadingPanel } from "@/components/loading-panel";
import {
  fetchNotifications,
  getStoredAuthToken,
  markAllNotificationsRead,
  markNotificationRead,
  type ApiNotification
} from "@/lib/api";

function formatDate(value: string) {
  try {
    return new Intl.DateTimeFormat("en-IN", {
      day: "2-digit",
      month: "short",
      year: "numeric",
      hour: "numeric",
      minute: "2-digit"
    }).format(new Date(value));
  } catch {
    return value;
  }
}

export default function AccountNotificationsPage() {
  const [notifications, setNotifications] = useState<ApiNotification[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isActing, setIsActing] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");
  const isAuthenticated = Boolean(getStoredAuthToken());

  async function loadNotifications() {
    const data = await fetchNotifications();
    setNotifications(data);
  }

  useEffect(() => {
    if (!isAuthenticated) {
      setIsLoading(false);
      return;
    }

    void loadNotifications()
      .catch((error: Error) => setErrorMessage(error.message))
      .finally(() => setIsLoading(false));
  }, [isAuthenticated]);

  async function handleMarkAllRead() {
    setIsActing(true);
    setErrorMessage("");
    try {
      await markAllNotificationsRead();
      await loadNotifications();
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Could not update notifications.");
    } finally {
      setIsActing(false);
    }
  }

  async function handleMarkRead(notificationId: number) {
    setIsActing(true);
    setErrorMessage("");
    try {
      await markNotificationRead(notificationId, true);
      await loadNotifications();
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Could not update notification.");
    } finally {
      setIsActing(false);
    }
  }

  return (
    <main className="page-shell">
      <div className="breadcrumb">Home / Account / Notifications</div>

      <section className="soft-section">
        <div className="section-title-row">
          <div>
            <p className="eyebrow">Account</p>
            <h1 className="page-title">Notifications and Updates</h1>
          </div>
          <div className="success-actions">
            <Link href="/account" className="section-link">
              Back to account
            </Link>
            <button type="button" className="secondary-action" onClick={() => void handleMarkAllRead()} disabled={isActing}>
              Mark all read
            </button>
          </div>
        </div>

        {!isAuthenticated ? (
          <div className="empty-cart-box">
            <h2>Login to view notifications</h2>
            <p>Order updates, payment changes, and support messages will appear here after OTP login.</p>
            <Link href="/login" className="primary-action">
              Login
            </Link>
          </div>
        ) : isLoading ? (
          <LoadingPanel
            title="Loading notifications"
            description="Fetching the latest order, payment, and account updates."
          />
        ) : errorMessage ? (
          <DegradedState
            title="Could not load notifications"
            description={errorMessage}
            onRetry={() => {
              setIsLoading(true);
              setErrorMessage("");
              void loadNotifications()
                .catch((error: Error) => setErrorMessage(error.message))
                .finally(() => setIsLoading(false));
            }}
            secondaryHref="/account"
            secondaryLabel="Back to account"
          />
        ) : notifications.length === 0 ? (
          <div className="empty-cart-box">
            <h2>No notifications yet</h2>
            <p>Your latest updates will appear here once orders, payments, and prescription events start moving.</p>
          </div>
        ) : (
          <div className="review-grid">
            {notifications.map((notification) => (
              <article key={notification.id} className="review-card wide">
                <div className="section-title-row">
                  <div>
                    <h3>{notification.title}</h3>
                    <p>{notification.body}</p>
                  </div>
                  <strong>{notification.is_read ? "Read" : "Unread"}</strong>
                </div>
                <div className="summary-row">
                  <span>{notification.kind.replace(/_/g, " ")}</span>
                  <strong>{formatDate(notification.created_at)}</strong>
                </div>
                <div className="success-actions">
                  {notification.link ? (
                    <a href={notification.link} className="primary-action">
                      Open
                    </a>
                  ) : null}
                  {!notification.is_read ? (
                    <button
                      type="button"
                      className="secondary-action"
                      onClick={() => void handleMarkRead(notification.id)}
                      disabled={isActing}
                    >
                      Mark read
                    </button>
                  ) : null}
                </div>
              </article>
            ))}
          </div>
        )}
      </section>
    </main>
  );
}
