"use client";

import { useCart } from "@/components/cart-provider";
import type { StorefrontProduct } from "@/lib/storefront-data";

type AddToCartButtonProps = {
  product: Pick<StorefrontProduct, "slug" | "name" | "off" | "mrp" | "price" | "meta" | "rx">;
  className?: string;
  label?: string;
};

export function AddToCartButton({
  product,
  className = "add-button",
  label = "Add"
}: AddToCartButtonProps) {
  const { addItem, getItemQuantity } = useCart();
  const quantity = getItemQuantity(product.slug);

  return (
    <button type="button" className={className} onClick={() => addItem(product)}>
      {quantity > 0 ? `Added (${quantity})` : label}
    </button>
  );
}
