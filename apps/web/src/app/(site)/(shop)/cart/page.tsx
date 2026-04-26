"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { FiArrowRight, FiPackage, FiShield, FiTruck } from "react-icons/fi";

import { AddToCartButton } from "@/components/add-to-cart-button";
import { useCart } from "@/components/cart-provider";
import { OrderSummaryCard } from "@/components/order-summary-card";
import { fetchCatalogProducts, type ApiCatalogProductSummary } from "@/lib/api";

function formatPrice(value: string) {
  const amount = Number.parseFloat(value);
  return Number.isNaN(amount) ? value : Number.isInteger(amount) ? String(amount) : amount.toFixed(2);
}

function discountFromPrices(mrp: string, salePrice: string) {
  const mrpValue = Number.parseFloat(mrp);
  const saleValue = Number.parseFloat(salePrice);

  if (Number.isNaN(mrpValue) || Number.isNaN(saleValue) || mrpValue <= 0 || saleValue >= mrpValue) {
    return "0% OFF";
  }

  return `${Math.round(((mrpValue - saleValue) / mrpValue) * 100)}% OFF`;
}

export default function CartPage() {
  const { cartItems, itemCount, removeItem, requiresPrescriptionCount, updateQty } = useCart();
  const [recommendations, setRecommendations] = useState<ApiCartRecommendation[]>([]);

  useEffect(() => {
    void fetchCatalogProducts()
      .then((products) => {
        const nextRecommendations = products
          .filter((product) => !cartItems.some((item) => item.slug === product.slug))
          .slice(0, 3)
          .map((product: ApiCatalogProductSummary) => ({
            slug: product.slug,
            name: product.name,
            off: discountFromPrices(product.mrp, product.sale_price),
            mrp: formatPrice(product.mrp),
            price: formatPrice(product.sale_price),
            brand: product.brand?.name ?? product.manufacturer ?? "TrueCare",
            salt: product.composition || product.category.name,
            category: product.category.slug,
            form: product.dosage_form || "Product",
            useFor: product.category.name,
            tags: [product.stock_status.replace(/_/g, " "), product.requires_prescription ? "Prescription required" : "OTC"],
            meta: `${product.manufacturer || product.brand?.name || "TrueCare"} | ${product.pack_size || "Pack details"}`,
            rx: product.requires_prescription,
            pack: product.pack_size || "Pack of 1",
            uses: [product.category.name]
          }));

        if (nextRecommendations.length > 0) {
          setRecommendations(nextRecommendations);
        } else {
          setRecommendations([]);
        }
      })
      .catch(() => {
        setRecommendations([]);
      });
  }, [cartItems]);

  return (
    <main className="page-shell">
      <div className="breadcrumb">Home / Cart</div>

      <section className="cart-layout">
        <div className="cart-main">
          <div className="section-title-row">
            <h1 className="page-title">Your cart</h1>
            <span className="section-link">{itemCount} items</span>
          </div>

          {requiresPrescriptionCount > 0 ? (
            <div className="cart-alert">
              Prescription medicines are in your cart. Upload or attach a valid prescription before
              final order placement.
            </div>
          ) : null}

          {cartItems.length > 0 ? (
            <div className="cart-list">
              {cartItems.map((item) => (
                <article key={item.slug} className="cart-item">
                  <div className="cart-item-image" />
                  <div className="cart-item-copy">
                    <div className="cart-item-header">
                      <div>
                        <h3>{item.name}</h3>
                        <p>{item.meta}</p>
                      </div>
                      {item.rx ? <span className="rx-tag">Prescription required</span> : null}
                    </div>

                    <div className="cart-item-footer">
                      <div className="qty-box">
                        <button type="button" onClick={() => updateQty(item.slug, item.qty - 1)}>
                          -
                        </button>
                        <span>{item.qty}</span>
                        <button type="button" onClick={() => updateQty(item.slug, item.qty + 1)}>
                          +
                        </button>
                      </div>
                      <div className="cart-price-block">
                        <span className="mrp">MRP Rs. {item.mrp}</span>
                        <strong>Rs. {(Number(item.price) * item.qty).toFixed(2)}</strong>
                      </div>
                    </div>

                    <div className="cart-item-links">
                      <button type="button" className="inline-action" onClick={() => removeItem(item.slug)}>
                        Remove
                      </button>
                      <Link href={`/medicine/${item.slug}`} className="inline-action">
                        Review product
                      </Link>
                      <Link href="/upload-prescription" className="inline-action">
                        {item.rx ? "Attach prescription" : "See substitutes"}
                      </Link>
                    </div>
                  </div>
                </article>
              ))}
            </div>
          ) : (
            <section className="soft-section">
              <div className="empty-cart-box">
                <h2>Your cart is empty</h2>
                <p>Add medicines from search, category, or product pages to build your order.</p>
                <div className="success-actions">
                  <Link href="/search" className="primary-action">
                    Search medicines
                  </Link>
                  <Link href="/categories/health-conditions/heart-care" className="secondary-action">
                    Browse categories
                  </Link>
                </div>
              </div>
            </section>
          )}

          <div className="coupon-strip">
            <div>
              <strong>Apply coupon or offer</strong>
              <p>Add savings before you continue to checkout.</p>
            </div>
            <button type="button" className="secondary-action">
              See offers
            </button>
          </div>

          <section className="cart-support-strip">
            <article className="cart-support-card">
              <span><FiTruck /></span>
              <div>
                <strong>Delivery rechecked at checkout</strong>
                <p>ETA and serviceability are confirmed again for your selected address.</p>
              </div>
            </article>
            <article className="cart-support-card">
              <span><FiShield /></span>
              <div>
                <strong>Prescription review stays in flow</strong>
                <p>Required Rx items remain visible all the way through review and confirmation.</p>
              </div>
            </article>
            <article className="cart-support-card">
              <span><FiPackage /></span>
              <div>
                <strong>Recommended add-ons update live</strong>
                <p>Quickly add everyday care items before you continue to address and payment.</p>
              </div>
            </article>
          </section>

          <section className="soft-section">
            <div className="section-title-row">
              <h2>Recommended for you</h2>
              <Link href="/categories" className="section-link">
                View all
              </Link>
            </div>
            {recommendations.length > 0 ? (
              <div className="mini-suggestion-grid">
                {recommendations.map((product) => (
                  <div key={product.slug} className="mini-suggestion-card">
                    <div className="mini-suggestion-image" />
                    <strong>{product.name}</strong>
                    <span>Rs. {product.price}</span>
                    <AddToCartButton
                      product={product}
                      label="Add"
                      className="mini-suggestion-button"
                    />
                  </div>
                ))}
              </div>
            ) : (
              <div className="empty-cart-box">
                <h2>Recommendations will appear here</h2>
                <p>We show live catalog suggestions here when related products are available.</p>
              </div>
            )}
          </section>
        </div>

        <OrderSummaryCard
          ctaLabel="Continue to Address"
          ctaHref="/checkout/address"
          helperText={cartItems.length > 0 ? "Address, payment, and review stay editable before order placement." : undefined}
        />
      </section>
    </main>
  );
}

type ApiCartRecommendation = {
  slug: string;
  name: string;
  off: string;
  mrp: string;
  price: string;
  brand: string;
  salt: string;
  category: string;
  form: string;
  useFor: string;
  tags: string[];
  meta: string;
  rx: boolean;
  pack: string;
  uses: string[];
};
