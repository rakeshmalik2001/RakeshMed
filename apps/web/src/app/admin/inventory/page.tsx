"use client";

import { useEffect, useState } from "react";

import {
  fetchAdminInventory,
  getStoredAuthToken,
  getStoredAuthUser,
  updateInventoryItem,
  type ApiInventoryItem
} from "@/lib/api";

type StockFilter = "" | "in_stock" | "low_stock" | "out_of_stock";

export default function AdminInventoryPage() {
  const [items, setItems] = useState<ApiInventoryItem[]>([]);
  const [filter, setFilter] = useState<StockFilter>("");
  const [query, setQuery] = useState("");
  const [isLoading, setIsLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState("");
  const [successMessage, setSuccessMessage] = useState("");
  const [activeAdjustmentKey, setActiveAdjustmentKey] = useState("");
  const isAuthenticated = Boolean(getStoredAuthToken());
  const role = getStoredAuthUser()?.role;

  async function loadInventory(nextFilter: StockFilter = filter) {
    const data = await fetchAdminInventory(nextFilter);
    const normalizedQuery = query.trim().toLowerCase();
    setItems(
      normalizedQuery
        ? data.filter((item) =>
            `${item.name} ${item.sku} ${item.category.name} ${item.manufacturer}`.toLowerCase().includes(normalizedQuery)
          )
        : data
    );
  }

  useEffect(() => {
    if (!isAuthenticated) {
      setIsLoading(false);
      return;
    }

    void loadInventory()
      .catch((error: Error) => setErrorMessage(error.message))
      .finally(() => setIsLoading(false));
  }, [isAuthenticated]);

  if (!isAuthenticated) {
    return (
      <div className="empty-cart-box">
        <h2>Login required</h2>
        <p>Inventory controls are available only after authenticated admin login.</p>
      </div>
    );
  }

  if (role !== "admin" && role !== "catalog_manager" && role !== "warehouse_operator" && role !== "support_agent") {
    return (
      <div className="empty-cart-box">
        <h2>Permission required</h2>
        <p>Your current account does not have inventory access.</p>
      </div>
    );
  }

  async function handleAdjustInventory(
    item: ApiInventoryItem,
    payload: Parameters<typeof updateInventoryItem>[1],
    successLabel: string
  ) {
    setErrorMessage("");
    setSuccessMessage("");
    setActiveAdjustmentKey(`${item.id}`);

    try {
      const updated = await updateInventoryItem(item.id, payload);
      setItems((current) => current.map((entry) => (entry.id === updated.id ? updated : entry)));
      setSuccessMessage(`${updated.name} ${successLabel}.`);
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Could not update inventory.");
    } finally {
      setActiveAdjustmentKey("");
    }
  }

  async function handleToggleLive(item: ApiInventoryItem) {
    setErrorMessage("");
    setSuccessMessage("");
    setActiveAdjustmentKey(`${item.id}-publish`);

    try {
      const updated = await updateInventoryItem(item.id, {
        is_active: !item.is_active
      });
      setItems((current) => current.map((entry) => (entry.id === updated.id ? updated : entry)));
      setSuccessMessage(`${updated.name} ${updated.is_active ? "published" : "paused"} for sale.`);
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Could not update product availability.");
    } finally {
      setActiveAdjustmentKey("");
    }
  }

  return (
    <>
      <section className="soft-section">
        <div className="section-title-row">
          <div>
            <p className="eyebrow">Admin</p>
            <h1 className="page-title">Inventory management</h1>
          </div>
          <div className="delivery-inline">
            <input
              value={query}
              className="checkout-inline-input"
              onChange={(event) => setQuery(event.target.value)}
              placeholder="Search product, SKU, category, manufacturer"
            />
            <select
              value={filter}
              className="checkout-inline-input"
              onChange={(event) => setFilter(event.target.value as StockFilter)}
            >
              <option value="">All stock states</option>
              <option value="in_stock">In stock</option>
              <option value="low_stock">Low stock</option>
              <option value="out_of_stock">Out of stock</option>
            </select>
            <button type="button" className="secondary-action" onClick={() => void loadInventory(filter)}>
              Apply
            </button>
          </div>
        </div>

        {errorMessage ? <p className="auth-error">{errorMessage}</p> : null}
        {!errorMessage && successMessage ? <p className="auth-success">{successMessage}</p> : null}

        {isLoading ? (
          <div className="empty-cart-box">
            <h2>Loading inventory</h2>
            <p>Fetching live stock status and publish state across products.</p>
          </div>
        ) : (
          <div className="review-grid">
            {items.map((item) => (
              <article key={item.id} className="review-card wide">
                <div className="section-title-row">
                  <div>
                    <h3>{item.name}</h3>
                    <p>{item.sku} | {item.category.name}</p>
                  </div>
                  <strong>{item.is_active ? "Live" : "Paused"}</strong>
                </div>
                <div className="review-item">
                  <span>Current stock state</span>
                  <strong>{item.stock_status.replace(/_/g, " ")}</strong>
                </div>
                <div className="review-item">
                  <span>Available / On hand</span>
                  <strong>
                    {item.total_available} / {item.total_on_hand}
                  </strong>
                </div>
                <div className="review-item">
                  <span>Reserved / Threshold</span>
                  <strong>
                    {item.total_reserved} / {item.low_stock_threshold}
                  </strong>
                </div>
                <div className="review-item">
                  <span>Price / Prescription</span>
                  <strong>
                    Rs. {item.sale_price} | {item.requires_prescription ? "Required" : "Not required"}
                  </strong>
                </div>

                <div className="info-panel" style={{ marginTop: 16 }}>
                  <p className="eyebrow">Location inventory</p>
                  <div className="placeholder-module-grid">
                    {item.location_items.map((locationItem) => (
                      <article key={locationItem.id} className="placeholder-module-card">
                        <strong>
                          {locationItem.location.name} ({locationItem.location.code})
                        </strong>
                        <p>
                          On hand {locationItem.quantity_on_hand} | Reserved {locationItem.reserved_quantity} | Available{" "}
                          {locationItem.available_quantity}
                        </p>
                        <div className="success-actions" style={{ marginTop: 12 }}>
                          <button
                            type="button"
                            className="secondary-action"
                            onClick={() =>
                              void handleAdjustInventory(
                                item,
                                {
                                  location_id: locationItem.location.id,
                                  quantity_delta: 5,
                                  movement_type: "restock",
                                  notes: "Operator restock adjustment"
                                },
                                `restocked by 5 units at ${locationItem.location.code}`
                              )
                            }
                          >
                            +5
                          </button>
                          <button
                            type="button"
                            className="secondary-action"
                            onClick={() =>
                              void handleAdjustInventory(
                                item,
                                {
                                  location_id: locationItem.location.id,
                                  quantity_delta: -5,
                                  movement_type: "adjustment",
                                  notes: "Operator stock adjustment"
                                },
                                `reduced by 5 units at ${locationItem.location.code}`
                              )
                            }
                          >
                            -5
                          </button>
                          <button
                            type="button"
                            className="secondary-action"
                            onClick={() =>
                              void handleAdjustInventory(
                                item,
                                {
                                  location_id: locationItem.location.id,
                                  quantity_on_hand: 0,
                                  movement_type: "manual_count",
                                  notes: "Manual stock count reset"
                                },
                                `zeroed at ${locationItem.location.code}`
                              )
                            }
                          >
                            Set 0
                          </button>
                        </div>
                      </article>
                    ))}
                  </div>
                </div>

                <div className="success-actions" style={{ marginTop: 16 }}>
                  <button
                    type="button"
                    className="secondary-action"
                    onClick={() =>
                      void handleAdjustInventory(
                        item,
                        {
                          threshold_quantity: item.low_stock_threshold + 1,
                          notes: "Raised low-stock threshold"
                        },
                        `threshold increased to ${item.low_stock_threshold + 1}`
                      )
                    }
                    disabled={activeAdjustmentKey === `${item.id}`}
                  >
                    Raise low-stock threshold
                  </button>
                  <button
                    type="button"
                    className="secondary-action"
                    onClick={() =>
                      void handleAdjustInventory(
                        item,
                        {
                          threshold_quantity: Math.max(0, item.low_stock_threshold - 1),
                          notes: "Lowered low-stock threshold"
                        },
                        `threshold decreased to ${Math.max(0, item.low_stock_threshold - 1)}`
                      )
                    }
                    disabled={activeAdjustmentKey === `${item.id}`}
                  >
                    Lower low-stock threshold
                  </button>
                  <button type="button" className="secondary-action" onClick={() => void handleToggleLive(item)}>
                    {item.is_active ? "Pause sale" : "Resume sale"}
                  </button>
                </div>
              </article>
            ))}
          </div>
        )}
      </section>
    </>
  );
}
