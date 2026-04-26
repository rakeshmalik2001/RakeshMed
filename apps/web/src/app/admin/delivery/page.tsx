"use client";

import { useEffect, useState } from "react";

import {
  fetchAdminShipments,
  getStoredAuthToken,
  getStoredAuthUser,
  updateAdminShipment,
  type ApiDeliveryShipment
} from "@/lib/api";

type ShipmentFilter = "" | "queued" | "assigned" | "picked_up" | "in_transit" | "out_for_delivery" | "delivered" | "failed" | "returned" | "cancelled";
type ShipmentStatus = Exclude<ShipmentFilter, "">;

function formatDate(value?: string | null) {
  if (!value) {
    return "Pending";
  }
  try {
    return new Intl.DateTimeFormat("en-IN", {
      day: "2-digit",
      month: "short",
      hour: "numeric",
      minute: "2-digit"
    }).format(new Date(value));
  } catch {
    return value;
  }
}

export default function AdminDeliveryPage() {
  const [shipments, setShipments] = useState<ApiDeliveryShipment[]>([]);
  const [filter, setFilter] = useState<ShipmentFilter>("");
  const [readyOnly, setReadyOnly] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState("");
  const [successMessage, setSuccessMessage] = useState("");
  const isAuthenticated = Boolean(getStoredAuthToken());
  const role = getStoredAuthUser()?.role;

  async function loadShipments(nextFilter: ShipmentFilter = filter, nextReadyOnly: boolean = readyOnly) {
    const data = await fetchAdminShipments(nextFilter, nextReadyOnly);
    setShipments(data);
  }

  useEffect(() => {
    if (!isAuthenticated) {
      setIsLoading(false);
      return;
    }
    void loadShipments()
      .catch((error: Error) => setErrorMessage(error.message))
      .finally(() => setIsLoading(false));
  }, [isAuthenticated]);

  if (!isAuthenticated) {
    return <div className="empty-cart-box"><h2>Login required</h2><p>Delivery operations are available only after authenticated admin login.</p></div>;
  }

  if (role !== "admin" && role !== "warehouse_operator" && role !== "support_agent" && role !== "finance") {
    return <div className="empty-cart-box"><h2>Permission required</h2><p>Your current account does not have delivery operations access.</p></div>;
  }

  async function handleShipmentUpdate(shipment: ApiDeliveryShipment, status: ShipmentStatus) {
    setErrorMessage("");
    setSuccessMessage("");
    try {
      const updated = await updateAdminShipment(shipment.order_number, {
        status,
        tracking_reference: shipment.tracking_reference || `TRK-${shipment.order_number}`
      });
      setShipments((current) => current.map((item) => (item.id === updated.id ? updated : item)));
      setSuccessMessage(`${updated.order_number} shipment updated.`);
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Could not update shipment.");
    }
  }

  return (
    <section className="soft-section">
      <div className="section-title-row">
        <div>
          <p className="eyebrow">Admin</p>
          <h1 className="page-title">Delivery operations</h1>
        </div>
        <div className="delivery-inline">
          <select value={filter} className="checkout-inline-input" onChange={(event) => setFilter(event.target.value as ShipmentFilter)}>
            <option value="">All shipment states</option>
            <option value="queued">Queued</option>
            <option value="assigned">Assigned</option>
            <option value="picked_up">Picked up</option>
            <option value="in_transit">In transit</option>
            <option value="out_for_delivery">Out for delivery</option>
            <option value="delivered">Delivered</option>
            <option value="failed">Failed</option>
            <option value="returned">Returned</option>
            <option value="cancelled">Cancelled</option>
          </select>
          <label className="checkout-inline-input" style={{ display: "inline-flex", alignItems: "center", gap: 8 }}>
            <input type="checkbox" checked={readyOnly} onChange={(event) => setReadyOnly(event.target.checked)} />
            Ready only
          </label>
          <button type="button" className="secondary-action" onClick={() => void loadShipments(filter, readyOnly)}>
            Apply
          </button>
        </div>
      </div>

      {errorMessage ? <p className="auth-error">{errorMessage}</p> : null}
      {!errorMessage && successMessage ? <p className="auth-success">{successMessage}</p> : null}

      {isLoading ? (
        <div className="empty-cart-box">
          <h2>Loading shipment queue</h2>
          <p>Fetching live delivery assignments and dispatch activity.</p>
        </div>
      ) : (
        <div className="review-grid">
          {shipments.map((shipment) => (
            <article key={shipment.id} className="review-card wide">
              <div className="section-title-row">
                <div>
                  <h3>{shipment.order_number}</h3>
                  <p>{shipment.recipient} | {shipment.city} - {shipment.pincode}</p>
                </div>
                <strong>{shipment.status.replace(/_/g, " ")}</strong>
              </div>
              <div className="review-item">
                <span>Carrier</span>
                <strong>{shipment.carrier_name} / {shipment.service_level}</strong>
              </div>
              <div className="review-item">
                <span>Tracking</span>
                <strong>{shipment.tracking_reference || "Will be assigned on dispatch"}</strong>
              </div>
              <div className="review-item">
                <span>ETA</span>
                <strong>{shipment.eta_label || `${formatDate(shipment.eta_start)} to ${formatDate(shipment.eta_end)}`}</strong>
              </div>
              <div className="review-item">
                <span>Reattempts</span>
                <strong>{shipment.reattempt_count}</strong>
              </div>
              <div className="review-item">
                <span>Zone</span>
                <strong>{shipment.zone?.name || "Unmapped"}</strong>
              </div>
              <div className="review-item">
                <span>Dispatch readiness</span>
                <strong>{shipment.is_dispatch_ready ? "Ready" : "Blocked"}</strong>
              </div>
              {shipment.failure_reason ? (
                <div className="review-item">
                  <span>Failure reason</span>
                  <strong>{shipment.failure_reason}</strong>
                </div>
              ) : null}
              {shipment.next_attempt_at ? (
                <div className="review-item">
                  <span>Next attempt</span>
                  <strong>{formatDate(shipment.next_attempt_at)}</strong>
                </div>
              ) : null}
              {shipment.eta_end && new Date(shipment.eta_end).getTime() < Date.now() && shipment.status !== "delivered" ? (
                <div className="review-item">
                  <span>SLA</span>
                  <strong>Breached ETA window</strong>
                </div>
              ) : null}
              {shipment.dispatch_blockers.length > 0 ? (
                <div className="review-item">
                  <span>Blockers</span>
                  <strong>{shipment.dispatch_blockers.join(", ")}</strong>
                </div>
              ) : null}
              <div className="success-actions">
                <button type="button" className="secondary-action" onClick={() => void handleShipmentUpdate(shipment, "assigned")}>
                  Assign
                </button>
                <button type="button" className="secondary-action" onClick={() => void handleShipmentUpdate(shipment, "in_transit")}>
                  Dispatch
                </button>
                <button type="button" className="secondary-action" onClick={() => void handleShipmentUpdate(shipment, "out_for_delivery")}>
                  Out for delivery
                </button>
                <button type="button" className="secondary-action" onClick={() => void handleShipmentUpdate(shipment, "delivered")}>
                  Mark delivered
                </button>
                <button type="button" className="secondary-action" onClick={() => void handleShipmentUpdate(shipment, "failed")}>
                  Mark failed
                </button>
                <button type="button" className="secondary-action" onClick={() => void handleShipmentUpdate(shipment, "queued")}>
                  Schedule reattempt
                </button>
                <button type="button" className="secondary-action" onClick={() => void handleShipmentUpdate(shipment, "returned")}>
                  Mark RTO
                </button>
              </div>
            </article>
          ))}
        </div>
      )}
    </section>
  );
}
