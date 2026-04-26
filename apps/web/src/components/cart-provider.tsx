"use client";

import {
  createContext,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode
} from "react";

import {
  AUTH_STORAGE_EVENT,
  type ApiOrder,
  createOrderFromCart,
  fetchAddresses,
  fetchCart,
  getStoredAuthToken,
  replaceCart
} from "@/lib/api";
import type { StorefrontProduct } from "@/lib/storefront-data";

type CartItem = {
  slug: string;
  name: string;
  off: string;
  mrp: string;
  price: string;
  meta: string;
  rx: boolean;
  qty: number;
};

type SavedAddress = {
  id: string;
  label: string;
  recipient: string;
  line1: string;
  city: string;
  pincode: string;
  isDefault?: boolean;
};

type PaymentMethod = "UPI" | "CARD" | "COD" | "WALLET";

type PlacedOrder = {
  id: string;
  addressId: string;
  addressLabel: string;
  paymentMethod: PaymentMethod;
  paymentStatus: string;
  status: string;
  itemCount: number;
  total: number;
  requiresPrescriptionCount: number;
};

type PrescriptionStatus = "submitted" | "pending" | "approved" | "rejected";

type PrescriptionSubmissionInput = {
  fileName: string;
  patientName: string;
  doctorName: string;
  notes: string;
};

type PrescriptionRecord = PrescriptionSubmissionInput & {
  id: string;
  status: PrescriptionStatus;
  submittedAt: string;
  reviewEtaMinutes: number;
};

type CartContextValue = {
  cartItems: CartItem[];
  itemCount: number;
  requiresPrescriptionCount: number;
  subtotal: number;
  discount: number;
  delivery: number;
  total: number;
  addItem: (product: Pick<StorefrontProduct, "slug" | "name" | "off" | "mrp" | "price" | "meta" | "rx">) => void;
  removeItem: (slug: string) => void;
  updateQty: (slug: string, qty: number) => void;
  clearCart: () => void;
  getItemQuantity: (slug: string) => number;
  addresses: SavedAddress[];
  saveAddress: (address: SavedAddress) => void;
  selectedAddressId: string;
  selectAddress: (id: string) => void;
  paymentMethod: PaymentMethod;
  setPaymentMethod: (method: PaymentMethod) => void;
  upiId: string;
  setUpiId: (value: string) => void;
  lastOrder: PlacedOrder | null;
  syncLastOrderFromApi: (order: ApiOrder) => void;
  placeOrder: () => Promise<PlacedOrder>;
  latestPrescription: PrescriptionRecord | null;
  savePrescriptionRecord: (record: PrescriptionRecord) => void;
};

const STORAGE_KEY = "netmeds-cart";
const CHECKOUT_STORAGE_KEY = "netmeds-checkout";
const PRESCRIPTION_STORAGE_KEY = "netmeds-prescription";

const CartContext = createContext<CartContextValue | null>(null);

function toNumber(value: string) {
  return Number.parseFloat(value);
}

function mapApiOrderToPlacedOrder(
  order: ApiOrder,
  fallback: {
    addressId?: string;
    addressLabel?: string;
  } = {}
): PlacedOrder {
  return {
    id: order.order_number,
    addressId: fallback.addressId ?? "",
    addressLabel: order.address_label || fallback.addressLabel || "Saved address",
    paymentMethod: order.payment_method,
    paymentStatus: order.payment_status,
    status: order.status,
    itemCount: order.items.reduce((sum, item) => sum + item.qty, 0),
    total: Number(order.total),
    requiresPrescriptionCount: order.requires_prescription_count
  };
}

export function CartProvider({ children }: { children: ReactNode }) {
  const [cartItems, setCartItems] = useState<CartItem[]>([]);
  const [addresses, setAddresses] = useState<SavedAddress[]>([]);
  const [authToken, setAuthToken] = useState<string | null>(null);
  const [selectedAddressId, setSelectedAddressId] = useState("");
  const [paymentMethod, setPaymentMethod] = useState<PaymentMethod>("UPI");
  const [upiId, setUpiId] = useState("");
  const [lastOrder, setLastOrder] = useState<PlacedOrder | null>(null);
  const [latestPrescription, setLatestPrescription] = useState<PrescriptionRecord | null>(null);
  const [hasHydratedCart, setHasHydratedCart] = useState(false);
  const [hasResolvedRemoteCart, setHasResolvedRemoteCart] = useState(false);
  const localCartSnapshotRef = useRef<CartItem[]>([]);

  useEffect(() => {
    const syncAuthToken = () => {
      setAuthToken(getStoredAuthToken());
    };

    syncAuthToken();
    window.addEventListener("storage", syncAuthToken);
    window.addEventListener(AUTH_STORAGE_EVENT, syncAuthToken);

    return () => {
      window.removeEventListener("storage", syncAuthToken);
      window.removeEventListener(AUTH_STORAGE_EVENT, syncAuthToken);
    };
  }, []);

  useEffect(() => {
    const saved = window.localStorage.getItem(STORAGE_KEY);

    if (!saved) {
      setHasHydratedCart(true);
      return;
    }

    try {
      const parsed = JSON.parse(saved) as CartItem[];
      localCartSnapshotRef.current = parsed;
      setCartItems(parsed);
    } catch {
      window.localStorage.removeItem(STORAGE_KEY);
    } finally {
      setHasHydratedCart(true);
    }
  }, []);

  useEffect(() => {
    if (!hasHydratedCart || hasResolvedRemoteCart) {
      return;
    }

    if (!authToken) {
      setHasResolvedRemoteCart(true);
      return;
    }

    void fetchCart()
      .then(async (cart) => {
        if (cart.items.length > 0) {
          setCartItems(
            cart.items.map((item) => ({
              ...item,
              price: item.price,
              mrp: item.mrp,
            }))
          );
          return;
        }

        if (localCartSnapshotRef.current.length > 0) {
          const syncedCart = await replaceCart({
            items: localCartSnapshotRef.current.map((item) => ({
              slug: item.slug,
              name: item.name,
              off: item.off,
              mrp: item.mrp,
              price: item.price,
              meta: item.meta,
              rx: item.rx,
              qty: item.qty
            }))
          });

          setCartItems(
            syncedCart.items.map((item) => ({
              ...item,
              price: item.price,
              mrp: item.mrp,
            }))
          );
        }
      })
      .catch(() => {
        // keep local fallback cart state
      })
      .finally(() => {
        setHasResolvedRemoteCart(true);
      });
  }, [authToken, hasHydratedCart, hasResolvedRemoteCart]);

  useEffect(() => {
    if (!authToken) {
      return;
    }

    void fetchAddresses()
      .then((remoteAddresses) => {
        if (!remoteAddresses.length) {
          return;
        }

        const mappedAddresses = remoteAddresses.map((address) => ({
          id: String(address.id),
          label: address.label,
          recipient: address.recipient,
          line1: address.line1,
          city: address.city,
          pincode: address.pincode,
          isDefault: address.is_default
        }));

        setAddresses(mappedAddresses);
        const selectedStillExists = mappedAddresses.some((address) => address.id === selectedAddressId);
        if (!selectedStillExists) {
          const defaultAddress = mappedAddresses.find((address) => address.isDefault) ?? mappedAddresses[0];
          setSelectedAddressId(defaultAddress.id);
        }
      })
      .catch(() => {
        // keep the local address list unchanged if backend addresses are unavailable
      });
  }, [authToken, selectedAddressId]);

  useEffect(() => {
    const savedCheckout = window.localStorage.getItem(CHECKOUT_STORAGE_KEY);

    if (!savedCheckout) {
      return;
    }

    try {
      const parsed = JSON.parse(savedCheckout) as {
        selectedAddressId?: string;
        paymentMethod?: PaymentMethod;
        upiId?: string;
        lastOrder?: PlacedOrder | null;
      };

      if (parsed.selectedAddressId) {
        setSelectedAddressId(parsed.selectedAddressId);
      }
      if (parsed.paymentMethod) {
        setPaymentMethod(parsed.paymentMethod);
      }
      if (parsed.upiId) {
        setUpiId(parsed.upiId);
      }
      if (parsed.lastOrder) {
        setLastOrder(parsed.lastOrder);
      }
    } catch {
      window.localStorage.removeItem(CHECKOUT_STORAGE_KEY);
    }
  }, []);

  useEffect(() => {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(cartItems));
  }, [cartItems]);

  useEffect(() => {
    if (!hasHydratedCart || !hasResolvedRemoteCart) {
      return;
    }

    if (!authToken) {
      return;
    }

    void replaceCart({
      items: cartItems.map((item) => ({
        slug: item.slug,
        name: item.name,
        off: item.off,
        mrp: item.mrp,
        price: item.price,
        meta: item.meta,
        rx: item.rx,
        qty: item.qty
      }))
    }).catch(() => {
      // local state remains the source of truth if sync fails
    });
  }, [authToken, cartItems, hasHydratedCart, hasResolvedRemoteCart]);

  useEffect(() => {
    window.localStorage.setItem(
      CHECKOUT_STORAGE_KEY,
      JSON.stringify({ selectedAddressId, paymentMethod, upiId, lastOrder })
    );
  }, [lastOrder, paymentMethod, selectedAddressId, upiId]);

  useEffect(() => {
    const savedPrescription = window.localStorage.getItem(PRESCRIPTION_STORAGE_KEY);

    if (!savedPrescription) {
      return;
    }

    try {
      const parsed = JSON.parse(savedPrescription) as PrescriptionRecord | null;
      setLatestPrescription(parsed);
    } catch {
      window.localStorage.removeItem(PRESCRIPTION_STORAGE_KEY);
    }
  }, []);

  useEffect(() => {
    window.localStorage.setItem(PRESCRIPTION_STORAGE_KEY, JSON.stringify(latestPrescription));
  }, [latestPrescription]);

  const value = useMemo<CartContextValue>(() => {
    const subtotal = cartItems.reduce((sum, item) => sum + toNumber(item.mrp) * item.qty, 0);
    const discountedSubtotal = cartItems.reduce((sum, item) => sum + toNumber(item.price) * item.qty, 0);
    const delivery = cartItems.length > 0 ? 40 : 0;
    const total = discountedSubtotal + delivery;

    return {
      cartItems,
      itemCount: cartItems.reduce((sum, item) => sum + item.qty, 0),
      requiresPrescriptionCount: cartItems.filter((item) => item.rx).length,
      subtotal,
      discount: subtotal - discountedSubtotal,
      delivery,
      total,
      addItem: (product) => {
        setCartItems((current) => {
          const existing = current.find((item) => item.slug === product.slug);

          if (existing) {
            return current.map((item) =>
              item.slug === product.slug ? { ...item, qty: item.qty + 1 } : item
            );
          }

          return [...current, { ...product, qty: 1 }];
        });
      },
      removeItem: (slug) => {
        setCartItems((current) => current.filter((item) => item.slug !== slug));
      },
      updateQty: (slug, qty) => {
        setCartItems((current) =>
          current.flatMap((item) => {
            if (item.slug !== slug) {
              return [item];
            }

            if (qty <= 0) {
              return [];
            }

            return [{ ...item, qty }];
          })
        );
      },
      clearCart: () => setCartItems([]),
      getItemQuantity: (slug) => cartItems.find((item) => item.slug === slug)?.qty ?? 0,
      addresses,
      saveAddress: (address) => {
        setAddresses((current) => {
          const hasDefault = current.some((item) => item.isDefault);
          const nextAddress = address.isDefault || !hasDefault ? { ...address, isDefault: true } : address;
          const rest = current
            .filter((item) => item.id !== nextAddress.id)
            .map((item) => (nextAddress.isDefault ? { ...item, isDefault: false } : item));
          return [nextAddress, ...rest];
        });
        setSelectedAddressId(address.id);
      },
      selectedAddressId,
      selectAddress: (id) => setSelectedAddressId(id),
      paymentMethod,
      setPaymentMethod,
      upiId,
      setUpiId,
      lastOrder,
      syncLastOrderFromApi: (order) => {
        setLastOrder((current) =>
          mapApiOrderToPlacedOrder(order, {
            addressId: current?.addressId,
            addressLabel: current?.addressLabel
          })
        );
      },
      placeOrder: async () => {
        const selectedAddress = addresses.find((address) => address.id === selectedAddressId) ?? addresses[0];
        const token = getStoredAuthToken();

        if (!selectedAddress) {
          throw new Error("Add and select a delivery address before placing this order.");
        }

        if (!token) {
          throw new Error("Please login before placing an order.");
        }

        const order = await createOrderFromCart({
          address: {
            label: selectedAddress.label,
            recipient: selectedAddress.recipient,
            line1: selectedAddress.line1,
            city: selectedAddress.city,
            pincode: selectedAddress.pincode
          },
          payment_method: paymentMethod,
          upi_id: paymentMethod === "UPI" ? upiId : undefined
        });

        const nextOrder = mapApiOrderToPlacedOrder(order, {
          addressId: selectedAddressId,
          addressLabel: selectedAddress.label
        });

        setLastOrder(nextOrder);
        setCartItems([]);
        return nextOrder;
      },
      latestPrescription,
      savePrescriptionRecord: (record) => {
        setLatestPrescription(record);
      }
    };
  }, [addresses, cartItems, lastOrder, latestPrescription, paymentMethod, selectedAddressId, upiId]);

  return <CartContext.Provider value={value}>{children}</CartContext.Provider>;
}

export function useCart() {
  const context = useContext(CartContext);

  if (!context) {
    throw new Error("useCart must be used inside CartProvider");
  }

  return context;
}
