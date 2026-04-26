"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { DegradedState } from "@/components/degraded-state";
import { LoadingPanel } from "@/components/loading-panel";
import { useCart } from "@/components/cart-provider";
import { useAuthSession } from "@/hooks/use-auth-session";
import { useOrderRefresh } from "@/hooks/use-order-refresh";
import {
  cancelOrder,
  confirmOrderPayment,
  createOrderPaymentSession,
  downloadOrderInvoice,
  fetchOrderById,
  requestOrderRefund,
  retryOrderPayment,
  verifyOrderPayment,
  type ApiDeliveryEvent,
  type ApiOrder,
  type ApiOrderEvent,
  type ApiPaymentSession,
  type ApiRefundRequest
} from "@/lib/api";
import {
  formatOrderStatusLabel,
  getPaymentStatusDescription,
  getPaymentStatusLabel,
  isOrderAwaitingPaymentUpdate
} from "@/lib/order-status";

import styles from "./page.module.css";

function formatCurrency(value: string) {
  const amount = Number.parseFloat(value);

  if (Number.isNaN(amount)) {
    return value;
  }

  return amount.toFixed(2);
}

function formatDate(value?: string | null) {
  if (!value) {
    return "Not available";
  }

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

type RazorpayCheckoutResponse = {
  razorpay_payment_id: string;
  razorpay_order_id: string;
  razorpay_signature: string;
};

type RazorpayCheckoutOptions = {
  amount: number;
  currency: string;
  description: string;
  key: string;
  name: string;
  order_id: string;
  prefill?: {
    contact?: string;
    email?: string;
    name?: string;
  };
};

declare global {
  interface Window {
    Razorpay?: new (
      options: RazorpayCheckoutOptions & {
        handler: (response: RazorpayCheckoutResponse) => void;
        modal?: { ondismiss?: () => void };
      }
    ) => {
      on: (event: "payment.failed", handler: () => void) => void;
      open: () => void;
    };
  }
}

let razorpayScriptPromise: Promise<void> | null = null;

function loadRazorpayCheckoutScript() {
  if (typeof window === "undefined") {
    return Promise.reject(new Error("Razorpay Checkout is only available in the browser."));
  }

  if (window.Razorpay) {
    return Promise.resolve();
  }

  if (!razorpayScriptPromise) {
    razorpayScriptPromise = new Promise((resolve, reject) => {
      const script = document.createElement("script");
      script.src = "https://checkout.razorpay.com/v1/checkout.js";
      script.async = true;
      script.onload = () => resolve();
      script.onerror = () => reject(new Error("Could not load Razorpay Checkout."));
      document.body.appendChild(script);
    });
  }

  return razorpayScriptPromise;
}

async function openRazorpayCheckout(options: RazorpayCheckoutOptions) {
  await loadRazorpayCheckoutScript();

  if (!window.Razorpay) {
    throw new Error("Razorpay Checkout is not available.");
  }

  return await new Promise<RazorpayCheckoutResponse>((resolve, reject) => {
    let settled = false;
    const RazorpayCheckout = window.Razorpay as NonNullable<typeof window.Razorpay>;
    const checkout = new RazorpayCheckout({
      ...options,
      handler: (response) => {
        settled = true;
        resolve(response);
      },
      modal: {
        ondismiss: () => {
          if (!settled) {
            reject(new Error("Razorpay checkout was closed before payment completed."));
          }
        }
      }
    });

    checkout.on("payment.failed", () => {
      settled = true;
      reject(new Error("Razorpay reported that the payment failed."));
    });
    checkout.open();
  });
}

function TimelineList({ events }: { events: Array<ApiOrderEvent | ApiDeliveryEvent> }) {
  return (
    <div className={styles.timelineList}>
      {events.map((event) => (
        <div key={`${"event_type" in event ? event.event_type : event.status}-${event.created_at}`} className={styles.timelineItem}>
          <div className={styles.timelineDot} />
          <div className={styles.timelineContent}>
            <strong>{event.summary}</strong>
            <p>{event.actor_name || "System event"}</p>
          </div>
          <span>{formatDate(event.created_at)}</span>
        </div>
      ))}
    </div>
  );
}

function RefundList({ refunds }: { refunds: ApiRefundRequest[] }) {
  return (
    <div className={styles.listShell}>
      {refunds.map((refund) => (
        <div key={refund.id} className={styles.listRow}>
          <div>
            <strong>{refund.reason}</strong>
            <p>{refund.requested_by_name || "Customer request"}</p>
          </div>
          <span className={styles.infoBadge}>{formatOrderStatusLabel(refund.status)}</span>
        </div>
      ))}
    </div>
  );
}

export default function OrderDetailPage({ params }: { params: Promise<{ orderId: string }> }) {
  const { syncLastOrderFromApi } = useCart();
  const [orderId, setOrderId] = useState<string>("");
  const [order, setOrder] = useState<ApiOrder | null>(null);
  const [paymentSession, setPaymentSession] = useState<ApiPaymentSession | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isActing, setIsActing] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [refundReason, setRefundReason] = useState("Payment issue or delivery problem");
  const session = useAuthSession();
  const isAuthenticated = session.isAuthenticated;
  const sessionUser = session.user;
  const latestPaymentAttempt = order?.payment_attempts[0] ?? null;
  const activePaymentProvider = paymentSession?.provider || latestPaymentAttempt?.provider || "";
  const { isRefreshing, lastCheckedAt } = useOrderRefresh({
    enabled: isAuthenticated && isOrderAwaitingPaymentUpdate(order),
    orderId,
    onUpdate: (nextOrder) => {
      setOrder(nextOrder);
      syncLastOrderFromApi(nextOrder);
    }
  });

  useEffect(() => {
    void params.then((resolved) => setOrderId(resolved.orderId));
  }, [params]);

  useEffect(() => {
    if (!orderId) {
      return;
    }

    if (!isAuthenticated) {
      setIsLoading(false);
      return;
    }

    void fetchOrderById(orderId)
      .then((data) => {
        if (!data) {
          setLoadError("Order not found.");
          setOrder(null);
          return;
        }

        setOrder(data);
        syncLastOrderFromApi(data);
        setLoadError(null);
      })
      .catch((fetchError: Error) => {
        setLoadError(fetchError.message);
      })
      .finally(() => {
        setIsLoading(false);
      });
  }, [isAuthenticated, orderId, syncLastOrderFromApi]);

  async function handleConfirmPayment() {
    if (!order) {
      return;
    }

    setIsActing(true);
    try {
      setActionError(null);
      const updated =
        activePaymentProvider === "razorpay"
          ? await fetchOrderById(order.order_number)
          : await confirmOrderPayment(order.order_number);
      if (!updated) {
        throw new Error("Could not refresh payment status.");
      }
      setOrder(updated);
      syncLastOrderFromApi(updated);
    } catch (error) {
      setActionError(error instanceof Error ? error.message : "Could not confirm payment.");
    } finally {
      setIsActing(false);
    }
  }

  async function startOrRetryPayment(mode: "start" | "retry") {
    if (!order) {
      return;
    }

    setIsActing(true);
    try {
      setActionError(null);
      const nextSession =
        mode === "start"
          ? await createOrderPaymentSession(order.order_number)
          : await retryOrderPayment(order.order_number);
      setPaymentSession(nextSession);

      if (nextSession.provider === "razorpay" && nextSession.provider_order_id) {
        const paymentResponse = await openRazorpayCheckout({
          amount: Math.round(Number.parseFloat(nextSession.amount) * 100),
          currency: nextSession.provider_currency || "INR",
          description: `${mode === "retry" ? "Payment retry" : "Payment"} for order ${order.order_number}`,
          key: nextSession.provider_key,
          name: process.env.NEXT_PUBLIC_COMPANY_NAME || "TrueCare Health Services Private Limited",
          order_id: nextSession.provider_order_id,
          prefill: {
            contact: sessionUser?.phone_number || undefined,
            email: sessionUser?.email || undefined,
            name: order.recipient || sessionUser?.full_name || undefined
          }
        });
        const updated = await verifyOrderPayment(order.order_number, {
          payment_reference: nextSession.payment_reference,
          razorpay_order_id: paymentResponse.razorpay_order_id,
          razorpay_payment_id: paymentResponse.razorpay_payment_id,
          razorpay_signature: paymentResponse.razorpay_signature
        });
        setOrder(updated);
        syncLastOrderFromApi(updated);
        setPaymentSession(null);
      } else if (nextSession.checkout_url) {
        window.open(nextSession.checkout_url, "_blank", "noopener,noreferrer");
      }

      if (mode === "retry") {
        const refreshed = await fetchOrderById(order.order_number);
        if (refreshed) {
          setOrder(refreshed);
          syncLastOrderFromApi(refreshed);
        }
      }
    } catch (error) {
      setActionError(error instanceof Error ? error.message : "Could not continue payment.");
    } finally {
      setIsActing(false);
    }
  }

  async function handleRequestRefund() {
    if (!order) {
      return;
    }

    setIsActing(true);
    try {
      setActionError(null);
      const updated = await requestOrderRefund(order.order_number, refundReason);
      setOrder(updated);
      syncLastOrderFromApi(updated);
    } catch (error) {
      setActionError(error instanceof Error ? error.message : "Could not request a refund.");
    } finally {
      setIsActing(false);
    }
  }

  async function handleCancelOrder() {
    if (!order) {
      return;
    }

    setIsActing(true);
    try {
      setActionError(null);
      const updated = await cancelOrder(order.order_number);
      setOrder(updated);
      syncLastOrderFromApi(updated);
    } catch (error) {
      setActionError(error instanceof Error ? error.message : "Could not cancel this order.");
    } finally {
      setIsActing(false);
    }
  }

  async function handleDownloadInvoice() {
    if (!order?.invoice) {
      return;
    }

    setIsActing(true);
    try {
      setActionError(null);
      const blob = await downloadOrderInvoice(order.order_number);
      const url = window.URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = `${order.invoice.invoice_number}.html`;
      anchor.click();
      window.URL.revokeObjectURL(url);
    } catch (error) {
      setActionError(error instanceof Error ? error.message : "Could not download the invoice.");
    } finally {
      setIsActing(false);
    }
  }

  return (
    <main className={`page-shell ${styles.detailPage}`}>
      <div className={`breadcrumb ${styles.breadcrumb}`}>Home / Account / Orders / {orderId || "Detail"}</div>

      <section className={`soft-section ${styles.detailShell}`}>
        <div className={styles.heroHeader}>
          <div>
            <p className="eyebrow">Account</p>
            <h1 className={`page-title ${styles.heroTitle}`}>Order detail and tracking</h1>
            <p className={styles.heroCopy}>
              See payment progress, shipment updates, invoice details, refund requests, and the full order timeline in
              one structured view.
            </p>
          </div>
          <div className={styles.heroActions}>
            <Link href="/account/orders" className={styles.primaryAction}>
              Back to orders
            </Link>
            <Link href="/account" className={styles.secondaryAction}>
              Account home
            </Link>
          </div>
        </div>

        {!isAuthenticated ? (
          <div className="empty-cart-box">
            <h2>Login to view this order</h2>
            <p>You need to login with OTP to open order details and tracking information.</p>
            <div className="success-actions">
              <Link href="/login" className="primary-action">
                Login
              </Link>
            </div>
          </div>
        ) : isLoading ? (
          <LoadingPanel
            title="Loading order details"
            description="Fetching order status, payment progress, item details, shipment updates, and invoice information."
          />
        ) : loadError || !order ? (
          <DegradedState
            title="Could not load this order"
            description={loadError ?? "Order not found."}
            secondaryHref="/account/orders"
            secondaryLabel="Back to orders"
          />
        ) : (
          <>
            <div className={styles.summaryGrid}>
              <article className={styles.summaryCard}>
                <p>Order number</p>
                <strong>{order.order_number}</strong>
                <span>Placed on {formatDate(order.created_at)}</span>
              </article>
              <article className={styles.summaryCard}>
                <p>Status</p>
                <strong>{formatOrderStatusLabel(order.status)}</strong>
                <span>Fulfillment: {formatOrderStatusLabel(order.fulfillment_status)}</span>
              </article>
              <article className={styles.summaryCard}>
                <p>Payment</p>
                <strong>{getPaymentStatusLabel(order.payment_method, order.payment_status)}</strong>
                <span>{order.payment_method} checkout</span>
              </article>
              <article className={styles.summaryCard}>
                <p>Total</p>
                <strong>Rs. {formatCurrency(order.total)}</strong>
                <span>{order.items.reduce((sum, item) => sum + item.qty, 0)} items</span>
              </article>
            </div>

            <div className={styles.detailGrid}>
              <section className={styles.panel}>
                <div className={styles.panelHeader}>
                  <div>
                    <p className={styles.panelKicker}>Delivery</p>
                    <h2>Address and shipment details</h2>
                  </div>
                  {order.tracking_reference ? <span className={styles.infoBadge}>{order.tracking_reference}</span> : null}
                </div>
                <div className={styles.infoStack}>
                  <div className={styles.infoCard}>
                    <span>Recipient</span>
                    <strong>{order.recipient}</strong>
                    <p>
                      {order.line1}, {order.city} - {order.pincode}
                    </p>
                  </div>
                  <div className={styles.infoCard}>
                    <span>Address label</span>
                    <strong>{order.address_label || "Saved address"}</strong>
                    <p>Tracking reference: {order.tracking_reference || "Will appear after dispatch"}</p>
                  </div>
                  {order.delivery_shipment ? (
                    <>
                      <div className={styles.infoCard}>
                        <span>Carrier</span>
                        <strong>{order.delivery_shipment.carrier_name}</strong>
                        <p>
                          {formatOrderStatusLabel(order.delivery_shipment.status)} | {order.delivery_shipment.service_level}
                        </p>
                      </div>
                      <div className={styles.infoCard}>
                        <span>ETA window</span>
                        <strong>
                          {formatDate(order.delivery_shipment.eta_start)} - {formatDate(order.delivery_shipment.eta_end)}
                        </strong>
                        <p>{order.delivery_shipment.eta_label || "ETA pending"}</p>
                      </div>
                      {order.delivery_shipment.failure_reason ? (
                        <div className={styles.alertCard}>
                          <strong>Delivery issue</strong>
                          <p>{order.delivery_shipment.failure_reason}</p>
                        </div>
                      ) : null}
                      {order.delivery_shipment.next_attempt_at ? (
                        <div className={styles.infoCard}>
                          <span>Next attempt</span>
                          <strong>{formatDate(order.delivery_shipment.next_attempt_at)}</strong>
                        </div>
                      ) : null}
                    </>
                  ) : null}
                </div>
              </section>

              <section className={styles.panel}>
                <div className={styles.panelHeader}>
                  <div>
                    <p className={styles.panelKicker}>Payment</p>
                    <h2>Payment status and actions</h2>
                  </div>
                </div>
                <div className={styles.gatewayCard}>
                  <strong data-testid="payment-status-summary">
                    {getPaymentStatusLabel(order.payment_method, order.payment_status)}
                  </strong>
                  <p>{getPaymentStatusDescription(order)}</p>
                  {isOrderAwaitingPaymentUpdate(order) ? (
                    <p className={styles.helperText} data-testid="order-payment-autorefresh-note">
                      {isRefreshing
                        ? "Checking for a gateway update..."
                        : "This page checks for payment updates automatically every 10 seconds."}
                      {lastCheckedAt ? ` Last checked at ${formatDate(lastCheckedAt)}.` : ""}
                    </p>
                  ) : null}
                </div>
                <div className={styles.billingGrid}>
                  <div className={styles.infoCard}>
                    <span>Subtotal</span>
                    <strong>Rs. {formatCurrency(order.subtotal)}</strong>
                  </div>
                  <div className={styles.infoCard}>
                    <span>Discount</span>
                    <strong className={styles.positiveValue}>- Rs. {formatCurrency(order.discount)}</strong>
                  </div>
                  <div className={styles.infoCard}>
                    <span>Delivery fee</span>
                    <strong>Rs. {formatCurrency(order.delivery_fee)}</strong>
                  </div>
                  <div className={styles.infoCard}>
                    <span>Prescription review</span>
                    <strong>{order.requires_prescription_count > 0 ? `${order.requires_prescription_count} item(s)` : "Not needed"}</strong>
                  </div>
                </div>
                {order.payment_attempts.length > 0 ? (
                  <div className={styles.listShell}>
                    {order.payment_attempts.map((attempt) => (
                      <div key={attempt.payment_reference} className={styles.listRow}>
                        <div>
                          <strong>{attempt.provider}</strong>
                          <p>{attempt.payment_reference}</p>
                        </div>
                        <span className={styles.infoBadge}>{formatOrderStatusLabel(attempt.status)}</span>
                      </div>
                    ))}
                  </div>
                ) : null}
                {paymentSession ? (
                  <div className={styles.gatewayCard}>
                    <strong>Payment session ready</strong>
                    <p>
                      Provider: {paymentSession.provider} | Reference: {paymentSession.payment_reference}
                    </p>
                    <p>Amount payable: Rs. {formatCurrency(paymentSession.amount)}</p>
                    {paymentSession.provider !== "razorpay" && paymentSession.checkout_url ? (
                      <div className={styles.actionRow}>
                        <a
                          href={paymentSession.checkout_url}
                          className={styles.primaryAction}
                          target="_blank"
                          rel="noreferrer"
                        >
                          Open secure payment page
                        </a>
                      </div>
                    ) : null}
                  </div>
                ) : null}
                <div className={styles.actionRow}>
                  {order.payment_method !== "COD" && order.payment_status !== "paid" && order.status !== "cancelled" ? (
                    <button type="button" className={styles.secondaryButton} onClick={() => void startOrRetryPayment("start")} disabled={isActing}>
                      {isActing ? "Preparing..." : "Open payment page"}
                    </button>
                  ) : null}
                  {order.payment_method !== "COD" && (order.payment_status === "failed" || order.payment_status === "pending") && order.status !== "cancelled" ? (
                    <button type="button" className={styles.secondaryButton} onClick={() => void startOrRetryPayment("retry")} disabled={isActing}>
                      {isActing ? "Retrying..." : "Create fresh payment link"}
                    </button>
                  ) : null}
                  {order.payment_method !== "COD" && order.payment_status !== "paid" && order.status !== "cancelled" ? (
                    <button data-testid="refresh-payment-status-button" type="button" className={styles.primaryButton} onClick={handleConfirmPayment} disabled={isActing}>
                      {isActing ? "Refreshing..." : "Refresh payment status"}
                    </button>
                  ) : null}
                  {order.payment_status === "paid" ? (
                    <button type="button" className={styles.secondaryButton} onClick={handleRequestRefund} disabled={isActing}>
                      {isActing ? "Submitting..." : "Request refund"}
                    </button>
                  ) : null}
                  {order.status !== "cancelled" ? (
                    <button type="button" className={styles.secondaryButton} onClick={handleCancelOrder} disabled={isActing}>
                      Cancel order
                    </button>
                  ) : null}
                </div>
                {actionError ? (
                  <div className={styles.alertCard}>
                    <strong>Action could not be completed</strong>
                    <p>{actionError}</p>
                  </div>
                ) : null}
                {order.payment_status === "paid" ? (
                  <div className={styles.infoCard}>
                    <span>Refund request reason</span>
                    <input
                      className={styles.inlineInput}
                      value={refundReason}
                      onChange={(event) => setRefundReason(event.target.value)}
                    />
                  </div>
                ) : null}
              </section>
            </div>

            <div className={styles.detailGrid}>
              <section className={styles.panel}>
                <div className={styles.panelHeader}>
                  <div>
                    <p className={styles.panelKicker}>Items</p>
                    <h2>What is in this order</h2>
                  </div>
                </div>
                <div className={styles.listShell}>
                  {order.items.map((item) => (
                    <div key={`${order.order_number}-${item.slug}`} className={styles.listRow}>
                      <div>
                        <strong>{item.name}</strong>
                        <p>
                          Quantity {item.qty}
                          {item.rx ? " | Prescription required" : ""}
                        </p>
                      </div>
                      <span className={styles.priceValue}>Rs. {(Number(item.price) * item.qty).toFixed(2)}</span>
                    </div>
                  ))}
                </div>
              </section>

              <section className={styles.panel}>
                <div className={styles.panelHeader}>
                  <div>
                    <p className={styles.panelKicker}>Invoice</p>
                    <h2>Customer invoice</h2>
                  </div>
                </div>
                {order.invoice ? (
                  <div className={styles.infoStack}>
                    <div className={styles.infoCard}>
                      <span>Invoice number</span>
                      <strong>{order.invoice.invoice_number}</strong>
                    </div>
                    <div className={styles.infoCard}>
                      <span>Issued on</span>
                      <strong>{formatDate(order.invoice.issued_at)}</strong>
                    </div>
                    <div className={styles.infoCard}>
                      <span>Invoice total</span>
                      <strong>Rs. {formatCurrency(order.invoice.total)}</strong>
                    </div>
                    <div className={styles.actionRow}>
                      <button type="button" className={styles.primaryButton} onClick={handleDownloadInvoice} disabled={isActing}>
                        {isActing ? "Preparing..." : "Download invoice"}
                      </button>
                    </div>
                  </div>
                ) : (
                  <div className={styles.emptyState}>The invoice will appear here once payment is completed for this order.</div>
                )}
              </section>
            </div>

            {order.delivery_shipment ? (
              <section className={styles.panel}>
                <div className={styles.panelHeader}>
                  <div>
                    <p className={styles.panelKicker}>Tracking</p>
                    <h2>Shipment timeline</h2>
                  </div>
                </div>
                {order.delivery_shipment.events.length > 0 ? (
                  <TimelineList events={order.delivery_shipment.events} />
                ) : (
                  <div className={styles.emptyState}>Tracking events will appear after the shipment is assigned.</div>
                )}
              </section>
            ) : null}

            <section className={styles.panel}>
              <div className={styles.panelHeader}>
                <div>
                  <p className={styles.panelKicker}>Timeline</p>
                  <h2>Order event history</h2>
                </div>
              </div>
              {order.timeline && order.timeline.length > 0 ? (
                <TimelineList events={order.timeline} />
              ) : (
                <div className={styles.emptyState}>No timeline events recorded yet.</div>
              )}
            </section>

            <section className={styles.panel}>
              <div className={styles.panelHeader}>
                <div>
                  <p className={styles.panelKicker}>Refunds</p>
                  <h2>Refund requests</h2>
                </div>
              </div>
              {order.refund_requests && order.refund_requests.length > 0 ? (
                <RefundList refunds={order.refund_requests} />
              ) : (
                <div className={styles.emptyState}>No refund requests raised yet.</div>
              )}
            </section>

            {order.payment_method !== "COD" && order.payment_status !== "paid" ? (
              <section className={styles.panel}>
                <div className={styles.panelHeader}>
                  <div>
                    <p className={styles.panelKicker}>Payment help</p>
                    <h2>If payment still looks pending</h2>
                  </div>
                </div>
                <div className={styles.alertCard}>
                  <p>
                    Open the payment page to complete your gateway step. If the payment succeeds but this page still
                    shows pending, use <strong>Refresh payment status</strong> or wait a few seconds for the page to
                    update automatically.
                  </p>
                </div>
              </section>
            ) : null}
          </>
        )}
      </section>
    </main>
  );
}
