"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import {
  decideAdminRefund,
  fetchAdminOrderById,
  getStoredAuthToken,
  getStoredAuthUser,
  updateAdminOrder,
  type ApiOrder
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

export default function AdminOrderDetailPage({ params }: { params: Promise<{ orderId: string }> }) {
  const [orderId, setOrderId] = useState("");
  const [order, setOrder] = useState<ApiOrder | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isActing, setIsActing] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");
  const [successMessage, setSuccessMessage] = useState("");
  const isAuthenticated = Boolean(getStoredAuthToken());
  const role = getStoredAuthUser()?.role;

  useEffect(() => {
    void params.then((resolved) => setOrderId(resolved.orderId));
  }, [params]);

  useEffect(() => {
    if (!isAuthenticated || !orderId) {
      setIsLoading(false);
      return;
    }

    void fetchAdminOrderById(orderId)
      .then((data) => {
        if (!data) {
          setErrorMessage("Order not found.");
          return;
        }
        setOrder(data);
      })
      .catch((error: Error) => setErrorMessage(error.message))
      .finally(() => setIsLoading(false));
  }, [isAuthenticated, orderId]);

  if (!isAuthenticated) {
    return (
      <div className="empty-cart-box">
        <h2>Login required</h2>
        <p>Admin order detail is available only after authenticated admin login.</p>
      </div>
    );
  }

  if (role !== "admin" && role !== "catalog_manager" && role !== "finance" && role !== "support_agent" && role !== "warehouse_operator") {
    return (
      <div className="empty-cart-box">
        <h2>Permission required</h2>
        <p>Your current account does not have admin order detail access.</p>
      </div>
    );
  }

  async function handleUpdate(
    payload: Partial<Pick<ApiOrder, "status" | "payment_status" | "fulfillment_status" | "tracking_reference" | "notes">>
  ) {
    if (!order) {
      return;
    }

    setIsActing(true);
    setErrorMessage("");
    setSuccessMessage("");

    try {
      const updated = await updateAdminOrder(order.order_number, payload);
      setOrder(updated);
      setSuccessMessage(`${updated.order_number} updated.`);
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Could not update order.");
    } finally {
      setIsActing(false);
    }
  }

  async function handleRefund(status: "approved" | "rejected" | "processed") {
    if (!order) {
      return;
    }

    setIsActing(true);
    setErrorMessage("");
    setSuccessMessage("");

    try {
      const updated = await decideAdminRefund(order.order_number, {
        status,
        resolution_notes: status === "rejected" ? "Refund rejected by admin review." : "Refund handled by admin operations."
      });
      setOrder(updated);
      setSuccessMessage(`Refund status updated to ${status}.`);
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Could not update refund.");
    } finally {
      setIsActing(false);
    }
  }

  if (isLoading) {
    return (
      <div className="empty-cart-box">
        <h2>Loading order detail</h2>
        <p>Fetching payment attempts, items, and admin controls.</p>
      </div>
    );
  }

  if (errorMessage || !order) {
    return (
      <div className="empty-cart-box">
        <h2>Could not load admin order detail</h2>
        <p>{errorMessage || "Order unavailable."}</p>
      </div>
    );
  }

  return (
    <section className="soft-section">
      <div className="section-title-row">
        <div>
          <p className="eyebrow">Admin</p>
          <h1 className="page-title">Order {order.order_number}</h1>
        </div>
        <Link href="/admin/orders" className="section-link">
          Back to orders
        </Link>
      </div>

      {errorMessage ? <p className="auth-error">{errorMessage}</p> : null}
      {!errorMessage && successMessage ? <p className="auth-success">{successMessage}</p> : null}

      <div className="review-grid">
        <article className="review-card">
          <h3>Customer</h3>
          <p>{order.recipient}</p>
          <div className="summary-row">
            <span>Placed on</span>
            <strong>{formatDate(order.created_at)}</strong>
          </div>
        </article>

        <article className="review-card">
          <h3>Status</h3>
          <p>{order.status.replace(/_/g, " ")}</p>
          <div className="summary-row">
            <span>Payment</span>
            <strong>{order.payment_status.replace(/_/g, " ")}</strong>
          </div>
          <div className="summary-row">
            <span>Fulfillment</span>
            <strong>{order.fulfillment_status.replace(/_/g, " ")}</strong>
          </div>
          <div className="summary-row">
            <span>Inventory</span>
            <strong>{order.inventory_status.replace(/_/g, " ")}</strong>
          </div>
        </article>

        <article className="review-card wide">
          <h3>Delivery details</h3>
          <p>
            {order.recipient}, {order.line1}, {order.city} - {order.pincode}
          </p>
          <div className="summary-row">
            <span>Address label</span>
            <strong>{order.address_label || "Saved address"}</strong>
          </div>
          <div className="summary-row">
            <span>Tracking reference</span>
            <strong>{order.tracking_reference || "Awaiting dispatch"}</strong>
          </div>
        </article>

        <article className="review-card wide">
          <h3>Items</h3>
          {order.items.map((item) => (
            <div key={`${order.order_number}-${item.slug}`} className="review-item">
              <span>{item.name} x {item.qty}</span>
              <strong>Rs. {(Number(item.price) * item.qty).toFixed(2)}</strong>
            </div>
          ))}
        </article>

        <article className="review-card wide">
          <h3>Payment attempts</h3>
          {order.payment_attempts.length === 0 ? (
            <p>No payment attempts recorded yet.</p>
          ) : (
            order.payment_attempts.map((attempt) => (
              <div key={attempt.payment_reference} className="review-item">
                <span>{attempt.provider} | {attempt.payment_reference}</span>
                <strong>{attempt.status}</strong>
              </div>
            ))
          )}
        </article>

        <article className="review-card wide">
          <h3>Delivery shipment</h3>
          {order.delivery_shipment ? (
            <>
              <div className="review-item">
                <span>{order.delivery_shipment.carrier_name} | {order.delivery_shipment.service_level}</span>
                <strong>{order.delivery_shipment.status.replace(/_/g, " ")}</strong>
              </div>
              <div className="review-item">
                <span>ETA window</span>
                <strong>{formatDate(order.delivery_shipment.eta_start ?? "")} - {formatDate(order.delivery_shipment.eta_end ?? "")}</strong>
              </div>
              {order.delivery_shipment.events.slice(0, 4).map((event) => (
                <div key={`${event.status}-${event.created_at}`} className="review-item">
                  <span>{event.summary}<br />{event.actor_name}</span>
                  <strong>{formatDate(event.created_at)}</strong>
                </div>
              ))}
            </>
          ) : (
            <p>Shipment will appear after the order enters the delivery queue.</p>
          )}
        </article>

        <article className="review-card wide">
          <h3>Order timeline</h3>
          {order.timeline && order.timeline.length > 0 ? (
            order.timeline.map((event) => (
              <div key={`${event.event_type}-${event.created_at}`} className="review-item">
                <span>{event.summary}<br />{event.actor_name}</span>
                <strong>{formatDate(event.created_at)}</strong>
              </div>
            ))
          ) : (
            <p>No audit events recorded yet.</p>
          )}
        </article>

        <article className="review-card wide">
          <h3>Refund requests</h3>
          {order.refund_requests && order.refund_requests.length > 0 ? (
            order.refund_requests.map((refund) => (
              <div key={refund.id} className="review-item">
                <span>{refund.reason}<br />{refund.requested_by_name}</span>
                <strong>{refund.status}</strong>
              </div>
            ))
          ) : (
            <p>No refund requests recorded yet.</p>
          )}
        </article>

        <article className="review-card wide">
          <h3>Admin actions</h3>
          <div className="success-actions">
            <button type="button" className="secondary-action" onClick={() => void handleUpdate({ status: "confirmed" })} disabled={isActing}>
              Confirm order
            </button>
            <button type="button" className="secondary-action" onClick={() => void handleUpdate({ payment_status: "paid" })} disabled={isActing}>
              Mark paid
            </button>
            <button
              type="button"
              className="secondary-action"
              onClick={() => void handleUpdate({ fulfillment_status: "packed" })}
              disabled={isActing}
            >
              Mark packed
            </button>
            <button
              type="button"
              className="secondary-action"
              onClick={() =>
                void handleUpdate({
                  fulfillment_status: "shipped",
                  tracking_reference: order.tracking_reference || `TRK-${order.order_number}`
                })
              }
              disabled={isActing}
            >
              Mark shipped
            </button>
            <button
              type="button"
              className="secondary-action"
              onClick={() => void handleUpdate({ fulfillment_status: "delivered" })}
              disabled={isActing}
            >
              Mark delivered
            </button>
            <button type="button" className="secondary-action" onClick={() => void handleUpdate({ payment_status: "failed" })} disabled={isActing}>
              Mark failed
            </button>
            <button type="button" className="secondary-action" onClick={() => void handleUpdate({ status: "cancelled" })} disabled={isActing}>
              Cancel order
            </button>
            <button data-testid="approve-refund-button" type="button" className="secondary-action" onClick={() => void handleRefund("approved")} disabled={isActing}>
              Approve refund
            </button>
            <button type="button" className="secondary-action" onClick={() => void handleRefund("processed")} disabled={isActing}>
              Mark refunded
            </button>
            <button type="button" className="secondary-action" onClick={() => void handleRefund("rejected")} disabled={isActing}>
              Reject refund
            </button>
          </div>
        </article>
      </div>
    </section>
  );
}
