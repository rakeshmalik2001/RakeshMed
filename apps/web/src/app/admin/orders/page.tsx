"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import {
  fetchAdminOrders,
  getStoredAuthToken,
  getStoredAuthUser,
  updateAdminOrder,
  type ApiOrder
} from "@/lib/api";

type OrderFilter = "" | "placed" | "pending_prescription_review" | "confirmed" | "cancelled";
type PaymentFilter = "" | "pending" | "paid" | "failed" | "cod_pending";
type FulfillmentFilter = "" | "queued" | "packed" | "shipped" | "delivered" | "returned" | "cancelled";

export default function AdminOrdersPage() {
  const [orders, setOrders] = useState<ApiOrder[]>([]);
  const [filter, setFilter] = useState<OrderFilter>("");
  const [paymentFilter, setPaymentFilter] = useState<PaymentFilter>("");
  const [fulfillmentFilter, setFulfillmentFilter] = useState<FulfillmentFilter>("");
  const [isLoading, setIsLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState("");
  const [successMessage, setSuccessMessage] = useState("");
  const isAuthenticated = Boolean(getStoredAuthToken());
  const role = getStoredAuthUser()?.role;
  const visibleOrders = paymentFilter
    ? orders.filter((order) => order.payment_status === paymentFilter)
    : orders;

  async function loadOrders(nextFilter: OrderFilter = filter, nextFulfillmentFilter: FulfillmentFilter = fulfillmentFilter) {
    const data = await fetchAdminOrders(nextFilter, nextFulfillmentFilter);
    setOrders(data);
  }

  useEffect(() => {
    if (!isAuthenticated) {
      setIsLoading(false);
      return;
    }

    void loadOrders()
      .catch((error: Error) => setErrorMessage(error.message))
      .finally(() => setIsLoading(false));
  }, [isAuthenticated]);

  if (!isAuthenticated) {
    return (
      <div className="empty-cart-box">
        <h2>Login required</h2>
        <p>Order operations are available only after authenticated admin login.</p>
      </div>
    );
  }

  if (role !== "admin" && role !== "catalog_manager" && role !== "finance" && role !== "support_agent" && role !== "warehouse_operator") {
    return (
      <div className="empty-cart-box">
        <h2>Permission required</h2>
        <p>Your current account does not have order operations access.</p>
      </div>
    );
  }

  async function handleOrderUpdate(
    order: ApiOrder,
    payload: Partial<Pick<ApiOrder, "status" | "payment_status" | "fulfillment_status" | "tracking_reference" | "notes">>
  ) {
    setErrorMessage("");
    setSuccessMessage("");

    try {
      const updated = await updateAdminOrder(order.order_number, payload);
      setOrders((current) => current.map((item) => (item.order_number === updated.order_number ? updated : item)));
      setSuccessMessage(`${updated.order_number} updated.`);
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Could not update order.");
    }
  }

  return (
    <section className="soft-section">
      <div className="section-title-row">
        <div>
          <p className="eyebrow">Admin</p>
          <h1 className="page-title">Order operations</h1>
        </div>
        <div className="delivery-inline">
          <select
            value={filter}
            className="checkout-inline-input"
            onChange={(event) => setFilter(event.target.value as OrderFilter)}
            data-testid="admin-orders-status-filter"
          >
            <option value="">All orders</option>
            <option value="placed">Placed</option>
            <option value="pending_prescription_review">Pending prescription review</option>
            <option value="confirmed">Confirmed</option>
            <option value="cancelled">Cancelled</option>
          </select>
          <select
            value={paymentFilter}
            className="checkout-inline-input"
            onChange={(event) => setPaymentFilter(event.target.value as PaymentFilter)}
            data-testid="admin-orders-payment-filter"
          >
            <option value="">All payment states</option>
            <option value="pending">Pending</option>
            <option value="paid">Paid</option>
            <option value="failed">Failed</option>
            <option value="cod_pending">COD pending</option>
          </select>
          <select
            value={fulfillmentFilter}
            className="checkout-inline-input"
            onChange={(event) => setFulfillmentFilter(event.target.value as FulfillmentFilter)}
            data-testid="admin-orders-fulfillment-filter"
          >
            <option value="">All fulfillment states</option>
            <option value="queued">Queued</option>
            <option value="packed">Packed</option>
            <option value="shipped">Shipped</option>
            <option value="delivered">Delivered</option>
            <option value="returned">Returned</option>
            <option value="cancelled">Cancelled</option>
          </select>
          <button
            type="button"
            className="secondary-action"
            onClick={() => void loadOrders(filter, fulfillmentFilter)}
            data-testid="admin-orders-apply-filters-button"
          >
            Apply
          </button>
        </div>
      </div>

      {errorMessage ? <p className="auth-error">{errorMessage}</p> : null}
      {!errorMessage && successMessage ? <p className="auth-success">{successMessage}</p> : null}

      {isLoading ? (
        <div className="empty-cart-box">
          <h2>Loading orders</h2>
          <p>Fetching the latest customer orders for support and finance operations.</p>
        </div>
      ) : (
          <div className="review-grid">
          {visibleOrders.map((order) => (
            <article key={order.order_number} className="review-card wide">
              <div className="section-title-row">
                <div>
                  <h3>{order.order_number}</h3>
                  <p>{order.recipient} | {order.city}</p>
                </div>
                <strong>Rs. {order.total}</strong>
              </div>
              <div className="review-item">
                <span>Status</span>
                <strong>{order.status.replace(/_/g, " ")}</strong>
              </div>
              <div className="review-item">
                <span>Payment</span>
                <strong>{order.payment_method} / {order.payment_status.replace(/_/g, " ")}</strong>
              </div>
              <div className="review-item">
                <span>Fulfillment</span>
                <strong>{order.fulfillment_status.replace(/_/g, " ")}</strong>
              </div>
              <div className="review-item">
                <span>Inventory</span>
                <strong>{order.inventory_status.replace(/_/g, " ")}</strong>
              </div>
              <div className="review-item">
                <span>Prescription review</span>
                <strong>{order.requires_prescription_count > 0 ? `${order.requires_prescription_count} item(s)` : "Not needed"}</strong>
              </div>
              <div className="review-item">
                <span>Tracking</span>
                <strong>{order.tracking_reference || "Awaiting assignment"}</strong>
              </div>
              <div className="success-actions">
                <Link
                  href={`/admin/orders/${order.order_number}`}
                  className="primary-action"
                  data-testid={`admin-order-detail-link-${order.order_number}`}
                >
                  Open detail
                </Link>
                <button
                  type="button"
                  className="secondary-action"
                  onClick={() => void handleOrderUpdate(order, { status: "confirmed" })}
                  data-testid={`admin-order-confirm-button-${order.order_number}`}
                >
                  Mark confirmed
                </button>
                <button
                  type="button"
                  className="secondary-action"
                  onClick={() => void handleOrderUpdate(order, { payment_status: "paid" })}
                  data-testid={`admin-order-paid-button-${order.order_number}`}
                >
                  Mark paid
                </button>
                <button
                  type="button"
                  className="secondary-action"
                  onClick={() => void handleOrderUpdate(order, { fulfillment_status: "packed" })}
                  data-testid={`admin-order-packed-button-${order.order_number}`}
                >
                  Mark packed
                </button>
                <button
                  type="button"
                  className="secondary-action"
                  onClick={() => void handleOrderUpdate(order, { fulfillment_status: "shipped" })}
                  data-testid={`admin-order-shipped-button-${order.order_number}`}
                >
                  Mark shipped
                </button>
                <button
                  type="button"
                  className="secondary-action"
                  onClick={() => void handleOrderUpdate(order, { fulfillment_status: "delivered" })}
                  data-testid={`admin-order-delivered-button-${order.order_number}`}
                >
                  Mark delivered
                </button>
                <button
                  type="button"
                  className="secondary-action"
                  onClick={() => void handleOrderUpdate(order, { status: "cancelled" })}
                  data-testid={`admin-order-cancel-button-${order.order_number}`}
                >
                  Cancel order
                </button>
              </div>
            </article>
          ))}
        </div>
      )}
    </section>
  );
}
