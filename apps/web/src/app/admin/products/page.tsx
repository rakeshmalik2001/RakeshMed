"use client";

import { useEffect, useState } from "react";

import {
  createAdminProduct,
  fetchAdminProducts,
  fetchCatalogBrands,
  fetchCatalogCategories,
  getStoredAuthToken,
  getStoredAuthUser,
  updateAdminProduct,
  type AdminProductPayload,
  type ApiAdminProduct,
  type ApiCatalogBrand,
  type ApiCatalogCategory
} from "@/lib/api";

const initialForm: AdminProductPayload = {
  name: "",
  slug: "",
  sku: "",
  category_slug: "",
  brand_slug: "",
  composition: "",
  dosage_form: "",
  strength: "",
  pack_size: "",
  manufacturer: "",
  description: "",
  warnings: "",
  side_effects: "",
  storage_instructions: "",
  mrp: "0.00",
  sale_price: "0.00",
  requires_prescription: false,
  is_otc: false,
  is_active: true,
  stock_status: "in_stock"
};

export default function AdminProductsPage() {
  const [products, setProducts] = useState<ApiAdminProduct[]>([]);
  const [categories, setCategories] = useState<ApiCatalogCategory[]>([]);
  const [brands, setBrands] = useState<ApiCatalogBrand[]>([]);
  const [query, setQuery] = useState("");
  const [form, setForm] = useState<AdminProductPayload>(initialForm);
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");
  const [successMessage, setSuccessMessage] = useState("");
  const isAuthenticated = Boolean(getStoredAuthToken());
  const role = getStoredAuthUser()?.role;

  async function loadProducts(search = "") {
    const data = await fetchAdminProducts(search);
    setProducts(data);
  }

  useEffect(() => {
    if (!isAuthenticated) {
      setIsLoading(false);
      return;
    }

    void Promise.all([loadProducts(), fetchCatalogCategories(), fetchCatalogBrands()])
      .then(([, categoryData, brandData]) => {
        setCategories(categoryData);
        setBrands(brandData);
        if (!form.category_slug && categoryData[0]) {
          setForm((current) => ({ ...current, category_slug: categoryData[0].slug }));
        }
      })
      .catch((error: Error) => setErrorMessage(error.message))
      .finally(() => setIsLoading(false));
  }, [isAuthenticated]);

  if (!isAuthenticated) {
    return (
      <div className="empty-cart-box">
        <h2>Login required</h2>
        <p>Catalog management is available only after authenticated admin login.</p>
      </div>
    );
  }

  if (role !== "admin" && role !== "catalog_manager" && role !== "support_agent") {
    return (
      <div className="empty-cart-box">
        <h2>Permission required</h2>
        <p>Your current account does not have product management access.</p>
      </div>
    );
  }

  async function handleCreateProduct() {
    setErrorMessage("");
    setSuccessMessage("");
    setIsSaving(true);

    try {
      const created = await createAdminProduct(form);
      setProducts((current) => [created, ...current]);
      setForm((current) => ({
        ...initialForm,
        category_slug: current.category_slug,
        brand_slug: current.brand_slug
      }));
      setSuccessMessage("Product created in the live catalog.");
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Could not create product.");
    } finally {
      setIsSaving(false);
    }
  }

  async function toggleProduct(product: ApiAdminProduct, patch: Partial<AdminProductPayload>) {
    setErrorMessage("");
    setSuccessMessage("");

    try {
      const updated = await updateAdminProduct(product.id, patch);
      setProducts((current) => current.map((item) => (item.id === updated.id ? updated : item)));
      setSuccessMessage(`${updated.name} updated.`);
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Could not update product.");
    }
  }

  return (
    <>
      <section className="soft-section">
        <div className="section-title-row">
          <div>
            <p className="eyebrow">Admin</p>
            <h1 className="page-title">Product management</h1>
          </div>
          <div className="delivery-inline">
            <input
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              className="checkout-inline-input"
              placeholder="Search by name, SKU, or manufacturer"
            />
            <button type="button" className="secondary-action" onClick={() => void loadProducts(query)}>
              Search
            </button>
          </div>
        </div>

        <article className="review-card wide">
          <h3>Add live product</h3>
          <div className="checkout-form-grid">
            <label className="checkout-field">
              <span>Name</span>
              <input value={form.name} onChange={(event) => setForm((current) => ({ ...current, name: event.target.value }))} />
            </label>
            <label className="checkout-field">
              <span>Slug</span>
              <input value={form.slug} onChange={(event) => setForm((current) => ({ ...current, slug: event.target.value }))} />
            </label>
            <label className="checkout-field">
              <span>SKU</span>
              <input value={form.sku} onChange={(event) => setForm((current) => ({ ...current, sku: event.target.value }))} />
            </label>
            <label className="checkout-field">
              <span>Category</span>
              <select value={form.category_slug} onChange={(event) => setForm((current) => ({ ...current, category_slug: event.target.value }))}>
                {categories.map((category) => (
                  <option key={category.id} value={category.slug}>
                    {category.name}
                  </option>
                ))}
              </select>
            </label>
            <label className="checkout-field">
              <span>Brand</span>
              <select value={form.brand_slug ?? ""} onChange={(event) => setForm((current) => ({ ...current, brand_slug: event.target.value || null }))}>
                <option value="">No brand</option>
                {brands.map((brand) => (
                  <option key={brand.id} value={brand.slug}>
                    {brand.name}
                  </option>
                ))}
              </select>
            </label>
            <label className="checkout-field">
              <span>Manufacturer</span>
              <input value={form.manufacturer} onChange={(event) => setForm((current) => ({ ...current, manufacturer: event.target.value }))} />
            </label>
            <label className="checkout-field">
              <span>Composition</span>
              <input value={form.composition} onChange={(event) => setForm((current) => ({ ...current, composition: event.target.value }))} />
            </label>
            <label className="checkout-field">
              <span>Pack size</span>
              <input value={form.pack_size} onChange={(event) => setForm((current) => ({ ...current, pack_size: event.target.value }))} />
            </label>
            <label className="checkout-field">
              <span>MRP</span>
              <input value={form.mrp} onChange={(event) => setForm((current) => ({ ...current, mrp: event.target.value }))} />
            </label>
            <label className="checkout-field">
              <span>Sale price</span>
              <input value={form.sale_price} onChange={(event) => setForm((current) => ({ ...current, sale_price: event.target.value }))} />
            </label>
          </div>
          <div className="success-actions">
            <button type="button" className="primary-action" onClick={handleCreateProduct} disabled={isSaving}>
              {isSaving ? "Creating..." : "Create product"}
            </button>
          </div>
          {errorMessage ? <p className="auth-error">{errorMessage}</p> : null}
          {!errorMessage && successMessage ? <p className="auth-success">{successMessage}</p> : null}
        </article>
      </section>

      {isLoading ? (
        <div className="empty-cart-box">
          <h2>Loading products</h2>
          <p>Fetching live catalog rows for admin operations.</p>
        </div>
      ) : (
        <section className="soft-section" style={{ marginTop: 24 }}>
          <div className="section-title-row">
            <div>
              <p className="eyebrow">Live Catalog</p>
              <h2>Publish and stock controls</h2>
            </div>
          </div>

          <div className="review-grid">
            {products.map((product) => (
              <article key={product.id} className="review-card wide">
                <div className="section-title-row">
                  <div>
                    <h3>{product.name}</h3>
                    <p>{product.sku} | {product.category.name}</p>
                  </div>
                  <strong>Rs. {product.sale_price}</strong>
                </div>
                <div className="review-item">
                  <span>Status</span>
                  <strong>{product.is_active ? "Published" : "Draft"}</strong>
                </div>
                <div className="review-item">
                  <span>Stock</span>
                  <strong>{product.stock_status.replace(/_/g, " ")}</strong>
                </div>
                <div className="review-item">
                  <span>Prescription</span>
                  <strong>{product.requires_prescription ? "Required" : "Not required"}</strong>
                </div>
                <div className="success-actions">
                  <button
                    type="button"
                    className="secondary-action"
                    onClick={() => void toggleProduct(product, { is_active: !product.is_active })}
                  >
                    {product.is_active ? "Unpublish" : "Publish"}
                  </button>
                  <button
                    type="button"
                    className="secondary-action"
                    onClick={() =>
                      void toggleProduct(product, {
                        stock_status:
                          product.stock_status === "in_stock"
                            ? "low_stock"
                            : product.stock_status === "low_stock"
                              ? "out_of_stock"
                              : "in_stock"
                      })
                    }
                  >
                    Cycle stock state
                  </button>
                </div>
              </article>
            ))}
          </div>
        </section>
      )}
    </>
  );
}
