const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api/v1";

export const AUTH_TOKEN_STORAGE_KEY = "rakeshmed-auth-token";
export const AUTH_USER_STORAGE_KEY = "rakeshmed-auth-user";
export const AUTH_LOGIN_PHONE_STORAGE_KEY = "rakeshmed-login-phone";
export const AUTH_REDIRECT_STORAGE_KEY = "rakeshmed-auth-redirect";
export const AUTH_EXPIRES_AT_STORAGE_KEY = "rakeshmed-auth-expires-at";
export const AUTH_STORAGE_EVENT = "rakeshmed-auth-storage-change";

export type ApiPrescriptionRecord = {
  id?: number;
  reference_code: string;
  patient_name: string;
  doctor_name: string;
  notes?: string;
  status: "submitted" | "pending_review" | "clarification_required" | "approved" | "rejected";
  review_priority: "normal" | "high" | "urgent";
  review_eta_hours: number;
  uploaded_file_name: string;
  uploaded_file_url?: string;
  uploaded_file_type?: string;
  uploaded_file_size_bytes?: number;
  file_access_url?: string;
  created_at: string;
  reviewed_at?: string | null;
};

export type ApiPrescriptionReview = {
  id: number;
  decision: string;
  notes: string;
  substitute_guidance: string;
  reviewer_name: string;
  created_at: string;
};

export type ApiPrescriptionDetail = ApiPrescriptionRecord & {
  clarification_message?: string;
  reviews: ApiPrescriptionReview[];
};

export type CreatePrescriptionPayload = {
  patient_name: string;
  doctor_name: string;
  notes: string;
  file: File;
};

export type AuthUser = {
  id: number;
  phone_number: string;
  email?: string | null;
  full_name: string;
  role: string;
  is_phone_verified: boolean;
  session_expires_at?: string | null;
};

export type UpdateProfilePayload = {
  full_name?: string;
  email?: string;
};

export type ApiAddress = {
  id: number;
  label: string;
  recipient: string;
  line1: string;
  city: string;
  state: string;
  pincode: string;
  phone_number: string;
  is_default: boolean;
};

export type CreateAddressPayload = {
  label: string;
  recipient: string;
  line1: string;
  city: string;
  state?: string;
  pincode: string;
  phone_number?: string;
  is_default?: boolean;
};

export type UpdateAddressPayload = Partial<CreateAddressPayload>;

export type ApiSavedPaymentMethod = {
  id: number;
  method_type: "UPI" | "CARD" | "WALLET";
  label: string;
  upi_id: string;
  masked_details: string;
  is_default: boolean;
  is_active: boolean;
};

export type CreatePaymentMethodPayload = {
  method_type: "UPI" | "CARD" | "WALLET";
  label: string;
  upi_id?: string;
  masked_details?: string;
  is_default?: boolean;
};

export type UpdatePaymentMethodPayload = Partial<CreatePaymentMethodPayload> & {
  is_active?: boolean;
};

export type SendOtpPayload = {
  phone_number: string;
  purpose?: "login" | "signup" | "reset";
};

export type SendOtpResponse = {
  status: string;
  phone_number: string;
  purpose: string;
  expires_at: string;
  otp_code?: string;
};

export type VerifyOtpPayload = {
  phone_number: string;
  otp_code: string;
  purpose?: "login" | "signup" | "reset";
  full_name?: string;
  email?: string;
};

export type VerifyOtpResponse = {
  status: string;
  token: string;
  expires_at?: string | null;
  user: AuthUser;
};

export type ApiCatalogCategory = {
  id: number;
  name: string;
  slug: string;
  description: string;
  parent: number | null;
  sort_order: number;
};

export type ApiCatalogBrand = {
  id: number;
  name: string;
  slug: string;
  description: string;
};

export type ApiCatalogProductSummary = {
  id: number;
  name: string;
  slug: string;
  sku: string;
  category: ApiCatalogCategory;
  brand: ApiCatalogBrand | null;
  composition: string;
  dosage_form: string;
  strength: string;
  pack_size: string;
  manufacturer: string;
  mrp: string;
  sale_price: string;
  requires_prescription: boolean;
  is_otc: boolean;
  stock_status: "in_stock" | "low_stock" | "out_of_stock";
};

export type ApiCatalogProductDetail = ApiCatalogProductSummary & {
  description: string;
  warnings: string;
  side_effects: string;
  storage_instructions: string;
  substitutes: ApiCatalogProductSummary[];
};

export type ApiCartItem = {
  slug: string;
  name: string;
  off: string;
  mrp: string;
  price: string;
  meta: string;
  rx: boolean;
  qty: number;
};

export type ApiCart = {
  items: ApiCartItem[];
  item_count: number;
  requires_prescription_count: number;
  subtotal: string;
  discount: string;
  delivery: string;
  total: string;
};

export type ReplaceCartPayload = {
  items: ApiCartItem[];
};

export type CheckoutAddressPayload = {
  label?: string;
  recipient: string;
  line1: string;
  city: string;
  pincode: string;
};

export type CheckoutPayload = {
  address: CheckoutAddressPayload;
  payment_method: "UPI" | "CARD" | "COD" | "WALLET";
  upi_id?: string;
  notes?: string;
};

export type ReviewPrescriptionPayload = {
  decision: "pending_review" | "clarification_required" | "approved" | "rejected";
  notes?: string;
  substitute_guidance?: string;
  clarification_message?: string;
};

export type ApiOrderItem = ApiCartItem;

export type ApiOrder = {
  order_number: string;
  status: string;
  payment_method: "UPI" | "CARD" | "COD" | "WALLET";
  payment_status: string;
  inventory_status: string;
  fulfillment_status: string;
  tracking_reference: string;
  address_label: string;
  recipient: string;
  line1: string;
  city: string;
  pincode: string;
  upi_id: string;
  notes: string;
  subtotal: string;
  discount: string;
  delivery_fee: string;
  total: string;
  requires_prescription_count: number;
  created_at: string;
  items: ApiOrderItem[];
  payment_attempts: ApiPaymentAttempt[];
  delivery_shipment?: ApiDeliveryShipment | null;
  timeline?: ApiOrderEvent[];
  refund_requests?: ApiRefundRequest[];
  invoice?: ApiInvoice | null;
};

export type ApiDeliveryZone = {
  id: number;
  name: string;
  code: string;
  pincode_prefix: string;
  city: string;
  state: string;
  eta_min_hours: number;
  eta_max_hours: number;
  cod_available: boolean;
  is_active: boolean;
};

export type ApiDeliveryEvent = {
  status: string;
  summary: string;
  meta: Record<string, unknown>;
  actor_name: string;
  created_at: string;
};

export type ApiDeliveryShipment = {
  id: number;
  order_number: string;
  recipient: string;
  city: string;
  pincode: string;
  carrier_name: string;
  service_level: string;
  status: string;
  is_dispatch_ready: boolean;
  dispatch_blockers: string[];
  eta_label: string;
  tracking_reference: string;
  status_notes: string;
  failure_reason: string;
  reattempt_count: number;
  eta_start?: string | null;
  eta_end?: string | null;
  next_attempt_at?: string | null;
  assigned_at?: string | null;
  dispatched_at?: string | null;
  delivered_at?: string | null;
  failed_at?: string | null;
  updated_at: string;
  zone?: ApiDeliveryZone | null;
  events: ApiDeliveryEvent[];
};

export type ApiServiceability = {
  pincode: string;
  is_serviceable: boolean;
  cod_available: boolean;
  zone: {
    code: string;
    name: string;
    city: string;
    state: string;
  } | null;
  eta_label: string;
  eta_start?: string | null;
  eta_end?: string | null;
};

export type UpdateDeliveryShipmentPayload = {
  carrier_name?: string;
  service_level?: "standard" | "express";
  status?:
    | "queued"
    | "assigned"
    | "picked_up"
    | "in_transit"
    | "out_for_delivery"
    | "delivered"
    | "failed"
    | "returned"
    | "cancelled";
  tracking_reference?: string;
  status_notes?: string;
};

export type ApiAdminSummary = {
  total_orders: number;
  today_orders: number;
  total_revenue: string;
  pending_prescription_review: number;
  catalog_products: number;
  customers: number;
  saved_addresses: number;
  saved_payment_methods: number;
  low_stock_products: number;
  out_of_stock_products: number;
  queued_fulfillment_orders: number;
  shipped_orders: number;
  dispatch_ready_shipments: number;
  delivery_in_transit: number;
  delivery_failed: number;
  delivery_returned: number;
  delivery_reattempt_due: number;
  delivery_sla_breached: number;
  recent_orders: ApiOrder[];
};

export type ApiPaymentSession = {
  order_number: string;
  payment_method: string;
  payment_status: string;
  amount: string;
  provider: string;
  provider_key: string;
  payment_reference: string;
  checkout_url: string;
  provider_order_id?: string;
  provider_currency?: string;
};

export type VerifyOrderPaymentPayload = {
  payment_reference?: string;
  razorpay_order_id?: string;
  razorpay_payment_id?: string;
  razorpay_signature?: string;
};

export type ApiPaymentAttempt = {
  provider: string;
  payment_reference: string;
  status: string;
  amount: string;
  initiated_at: string;
  confirmed_at?: string | null;
};

export type ApiOrderEvent = {
  event_type: string;
  actor_name: string;
  summary: string;
  meta: Record<string, unknown>;
  created_at: string;
};

export type ApiRefundRequest = {
  id: number;
  reason: string;
  status: string;
  amount: string;
  resolution_notes: string;
  requested_by_name: string;
  created_at: string;
  updated_at: string;
  processed_at?: string | null;
};

export type ApiInvoice = {
  invoice_number: string;
  status: string;
  recipient: string;
  line1: string;
  city: string;
  pincode: string;
  subtotal: string;
  discount: string;
  delivery_fee: string;
  tax_amount: string;
  total: string;
  snapshot: {
    order_number?: string;
    payment_method?: string;
    payment_status?: string;
    items?: Array<{
      name: string;
      slug: string;
      qty: number;
      mrp: string;
      sale_price: string;
      line_total: string;
      requires_prescription: boolean;
    }>;
  };
  issued_at: string;
};

export type ApiNotification = {
  id: number;
  kind: string;
  title: string;
  body: string;
  link: string;
  meta: Record<string, unknown>;
  is_read: boolean;
  created_at: string;
  read_at?: string | null;
};

export type ApiAdminPaymentAttempt = ApiPaymentAttempt & {
  order_number: string;
  recipient: string;
  order_status: string;
  payment_method: string;
  payment_status: string;
};

export type RefundDecisionPayload = {
  status: "approved" | "rejected" | "processed";
  resolution_notes?: string;
};

export type ApiPaymentWebhookEvent = {
  provider: string;
  event_id: string;
  event_type: string;
  payment_reference: string;
  order_number: string;
  was_duplicate: boolean;
  processed_at?: string | null;
  created_at: string;
};

export type ApiReconciliationSnapshot = {
  provider: string;
  captured_total: string;
  refunded_total: string;
  pending_refund_count: number;
  duplicate_webhooks: number;
  processed_webhooks: number;
  unmatched_paid_orders: number;
  created_by_label: string;
  notes: string;
  created_at: string;
};

export type ApiReconciliationSummary = {
  provider: string;
  attempt_count: number;
  captured_total: string;
  refunded_total: string;
  pending_refund_count: number;
  duplicate_webhooks: number;
  processed_webhooks: number;
  unmatched_paid_orders: number;
  latest_webhooks: ApiPaymentWebhookEvent[];
  snapshot_history: ApiReconciliationSnapshot[];
  settlement_history: ApiSettlementBatch[];
};

export type ApiSettlementEntry = {
  order_number: string;
  payment_reference: string;
  gross_amount: string;
  refund_amount: string;
  net_amount: string;
  settlement_status: string;
  refund_status: string;
  created_at: string;
};

export type ApiSettlementBatch = {
  id: number;
  provider: string;
  batch_reference: string;
  period_start: string;
  period_end: string;
  total_captured: string;
  total_refunded: string;
  total_net: string;
  status: string;
  created_by_name: string;
  notes: string;
  created_at: string;
  entries: ApiSettlementEntry[];
};

export type CreateSettlementBatchPayload = {
  provider?: string;
  period_start?: string;
  period_end?: string;
  notes?: string;
};

export type UpdateSettlementBatchPayload = {
  status?: "draft" | "processing" | "closed";
  notes?: string;
};

export type ApiAdminProduct = {
  id: number;
  name: string;
  slug: string;
  sku: string;
  category: ApiCatalogCategory;
  category_slug: string;
  brand: ApiCatalogBrand | null;
  brand_slug?: string | null;
  composition: string;
  dosage_form: string;
  strength: string;
  pack_size: string;
  manufacturer: string;
  description: string;
  warnings: string;
  side_effects: string;
  storage_instructions: string;
  mrp: string;
  sale_price: string;
  requires_prescription: boolean;
  is_otc: boolean;
  is_active: boolean;
  stock_status: "in_stock" | "low_stock" | "out_of_stock";
};

export type AdminProductPayload = {
  name: string;
  slug: string;
  sku: string;
  category_slug: string;
  brand_slug?: string | null;
  composition?: string;
  dosage_form?: string;
  strength?: string;
  pack_size?: string;
  manufacturer?: string;
  description?: string;
  warnings?: string;
  side_effects?: string;
  storage_instructions?: string;
  mrp: string;
  sale_price: string;
  requires_prescription?: boolean;
  is_otc?: boolean;
  is_active?: boolean;
  stock_status?: "in_stock" | "low_stock" | "out_of_stock";
};

export type ApiInventoryItem = {
  id: number;
  name: string;
  slug: string;
  sku: string;
  category: ApiCatalogCategory;
  brand: ApiCatalogBrand | null;
  manufacturer: string;
  pack_size: string;
  requires_prescription: boolean;
  is_active: boolean;
  stock_status: "in_stock" | "low_stock" | "out_of_stock";
  mrp: string;
  sale_price: string;
  total_on_hand: number;
  total_reserved: number;
  total_available: number;
  low_stock_threshold: number;
  location_items: ApiInventoryLocationItem[];
  updated_at: string;
};

export type InventoryUpdatePayload = {
  location_id?: number;
  quantity_delta?: number;
  quantity_on_hand?: number;
  reserved_quantity?: number;
  inbound_quantity?: number;
  threshold_quantity?: number;
  is_active?: boolean;
  reference?: string;
  notes?: string;
  movement_type?:
    | "restock"
    | "adjustment"
    | "sale_allocation"
    | "sale_release"
    | "sale_complete"
    | "return"
    | "damage"
    | "transfer_in"
    | "transfer_out"
    | "manual_count";
};

export type ApiInventoryLocationItem = {
  id: number;
  location: {
    id: number;
    name: string;
    code: string;
    kind: string;
    is_active: boolean;
  };
  quantity_on_hand: number;
  reserved_quantity: number;
  inbound_quantity: number;
  available_quantity: number;
  updated_at: string;
};

type FetchCatalogProductsOptions = {
  category?: string;
  brand?: string;
  q?: string;
  prescriptionRequired?: boolean;
};

function buildHeaders(token?: string) {
  return {
    "Content-Type": "application/json",
    ...(token ? { Authorization: `Token ${token}` } : {})
  };
}

function notifyAuthStorageChanged() {
  if (typeof window === "undefined") {
    return;
  }

  window.dispatchEvent(new Event(AUTH_STORAGE_EVENT));
}

export function getStoredAuthToken() {
  if (typeof window === "undefined") {
    return null;
  }

  const expiresAt = window.localStorage.getItem(AUTH_EXPIRES_AT_STORAGE_KEY);
  if (expiresAt) {
    const expiryTime = Date.parse(expiresAt);
    if (!Number.isNaN(expiryTime) && expiryTime <= Date.now()) {
      clearStoredAuth();
      return null;
    }
  }

  return window.localStorage.getItem(AUTH_TOKEN_STORAGE_KEY);
}

export function setStoredAuthToken(token: string, expiresAt?: string | null) {
  if (typeof window === "undefined") {
    return;
  }

  window.localStorage.setItem(AUTH_TOKEN_STORAGE_KEY, token);
  if (expiresAt) {
    window.localStorage.setItem(AUTH_EXPIRES_AT_STORAGE_KEY, expiresAt);
  } else {
    window.localStorage.removeItem(AUTH_EXPIRES_AT_STORAGE_KEY);
  }
  notifyAuthStorageChanged();
}

export function clearStoredAuth() {
  if (typeof window === "undefined") {
    return;
  }

  window.localStorage.removeItem(AUTH_TOKEN_STORAGE_KEY);
  window.localStorage.removeItem(AUTH_USER_STORAGE_KEY);
  window.localStorage.removeItem(AUTH_EXPIRES_AT_STORAGE_KEY);
  notifyAuthStorageChanged();
}

export function getStoredAuthUser() {
  if (typeof window === "undefined") {
    return null;
  }

  if (!getStoredAuthToken()) {
    return null;
  }

  const raw = window.localStorage.getItem(AUTH_USER_STORAGE_KEY);
  if (!raw) {
    return null;
  }

  try {
    return JSON.parse(raw) as AuthUser;
  } catch {
    window.localStorage.removeItem(AUTH_USER_STORAGE_KEY);
    return null;
  }
}

export function setStoredAuthUser(user: AuthUser) {
  if (typeof window === "undefined") {
    return;
  }

  window.localStorage.setItem(AUTH_USER_STORAGE_KEY, JSON.stringify(user));
  notifyAuthStorageChanged();
}

async function parseErrorMessage(response: Response, fallbackMessage: string) {
  try {
    const errorBody = (await response.json()) as Record<string, unknown>;
    if (typeof errorBody.detail === "string") {
      return errorBody.detail;
    }

    for (const value of Object.values(errorBody)) {
      if (typeof value === "string") {
        return value;
      }
      if (Array.isArray(value)) {
        const firstString = value.find((entry) => typeof entry === "string");
        if (typeof firstString === "string") {
          return firstString;
        }
      }
    }
  } catch {
    // ignore parse failure
  }

  return fallbackMessage;
}

async function handleAuthFailure(response: Response) {
  if (response.status === 401 || response.status === 403) {
    clearStoredAuth();
  }
}

function shouldRetryReadRequest(response: Response | null, error: unknown, attempt: number, maxRetries: number) {
  if (attempt >= maxRetries) {
    return false;
  }

  if (response) {
    return response.status >= 500 || response.status === 429;
  }

  return error instanceof TypeError;
}

async function readJsonWithRetry<T>(
  input: string,
  init: RequestInit,
  fallbackMessage: string,
  maxRetries = 1
): Promise<T> {
  let lastError: unknown;

  for (let attempt = 0; attempt <= maxRetries; attempt += 1) {
    let response: Response | null = null;

    try {
      response = await fetch(input, init);

      if (response.ok) {
        return (await response.json()) as T;
      }

      if (!shouldRetryReadRequest(response, null, attempt, maxRetries)) {
        await handleAuthFailure(response);
        throw new Error(await parseErrorMessage(response, fallbackMessage));
      }
    } catch (error) {
      lastError = error;

      if (!shouldRetryReadRequest(response, error, attempt, maxRetries)) {
        throw error instanceof Error ? error : new Error(fallbackMessage);
      }
    }

    await new Promise((resolve) => setTimeout(resolve, 250 * (attempt + 1)));
  }

  throw lastError instanceof Error ? lastError : new Error(fallbackMessage);
}

export async function sendOtp(payload: SendOtpPayload) {
  const response = await fetch(`${API_BASE_URL}/auth/send-otp/`, {
    method: "POST",
    headers: buildHeaders(),
    body: JSON.stringify({ purpose: "login", ...payload })
  });

  if (!response.ok) {
    throw new Error(await parseErrorMessage(response, "Could not send OTP."));
  }

  return (await response.json()) as SendOtpResponse;
}

export async function verifyOtp(payload: VerifyOtpPayload) {
  const response = await fetch(`${API_BASE_URL}/auth/verify-otp/`, {
    method: "POST",
    headers: buildHeaders(),
    body: JSON.stringify({ purpose: "login", ...payload })
  });

  if (!response.ok) {
    throw new Error(await parseErrorMessage(response, "Could not verify OTP."));
  }

  const data = (await response.json()) as VerifyOtpResponse;
  setStoredAuthToken(data.token, data.expires_at ?? data.user.session_expires_at ?? null);
  setStoredAuthUser(data.user);
  return data;
}

export async function fetchMe() {
  const token = getStoredAuthToken();

  if (!token) {
    throw new Error("Please login before loading your account.");
  }

  const user = await readJsonWithRetry<AuthUser>(
    `${API_BASE_URL}/auth/me/`,
    {
      method: "GET",
      headers: buildHeaders(token),
      cache: "no-store"
    },
    "Could not load your account."
  );
  setStoredAuthUser(user);
  if (user.session_expires_at) {
    setStoredAuthToken(token, user.session_expires_at);
  }
  return user;
}

export async function updateMe(payload: UpdateProfilePayload) {
  const token = getStoredAuthToken();

  if (!token) {
    throw new Error("Please login before updating your profile.");
  }

  const response = await fetch(`${API_BASE_URL}/auth/me/`, {
    method: "PATCH",
    headers: buildHeaders(token),
    body: JSON.stringify(payload)
  });

  if (!response.ok) {
    await handleAuthFailure(response);
    throw new Error(await parseErrorMessage(response, "Could not update your profile."));
  }

  const user = (await response.json()) as AuthUser;
  setStoredAuthUser(user);
  if (user.session_expires_at) {
    setStoredAuthToken(token, user.session_expires_at);
  }
  return user;
}

export async function sendCustomerActivityHeartbeat(tabId: string) {
  const token = getStoredAuthToken();

  if (!token) {
    return null;
  }

  const response = await fetch(`${API_BASE_URL}/auth/activity/heartbeat/`, {
    method: "POST",
    headers: buildHeaders(token),
    body: JSON.stringify({ tab_id: tabId }),
    keepalive: true
  });

  if (!response.ok) {
    if (response.status === 401 || response.status === 403) {
      clearStoredAuth();
    }
    return null;
  }

  return (await response.json()) as {
    status: string;
    counted_seconds?: number;
    total_seconds?: number;
    total_label?: string;
    reason?: string;
  };
}

export async function fetchNotifications(unreadOnly = false) {
  const token = getStoredAuthToken();

  if (!token) {
    throw new Error("Please login before loading notifications.");
  }

  const searchParams = new URLSearchParams();
  if (unreadOnly) {
    searchParams.set("unread", "true");
  }

  return await readJsonWithRetry<ApiNotification[]>(
    buildCatalogUrl("/notifications/", searchParams),
    {
      method: "GET",
      headers: buildHeaders(token),
      cache: "no-store"
    },
    "Could not load notifications."
  );
}

export async function markNotificationRead(notificationId: number, isRead = true) {
  const token = getStoredAuthToken();

  if (!token) {
    throw new Error("Please login before updating notifications.");
  }

  const response = await fetch(`${API_BASE_URL}/notifications/${notificationId}/`, {
    method: "PATCH",
    headers: buildHeaders(token),
    body: JSON.stringify({ is_read: isRead })
  });

  if (!response.ok) {
    await handleAuthFailure(response);
    throw new Error(await parseErrorMessage(response, "Could not update notification."));
  }

  return (await response.json()) as ApiNotification;
}

export async function markAllNotificationsRead() {
  const token = getStoredAuthToken();

  if (!token) {
    throw new Error("Please login before updating notifications.");
  }

  const response = await fetch(`${API_BASE_URL}/notifications/mark-all-read/`, {
    method: "POST",
    headers: buildHeaders(token)
  });

  if (!response.ok) {
    await handleAuthFailure(response);
    throw new Error(await parseErrorMessage(response, "Could not mark notifications as read."));
  }
}

export async function fetchAddresses() {
  const token = getStoredAuthToken();

  if (!token) {
    throw new Error("Please login before loading addresses.");
  }

  return await readJsonWithRetry<ApiAddress[]>(
    `${API_BASE_URL}/auth/addresses/`,
    {
      method: "GET",
      headers: buildHeaders(token),
      cache: "no-store"
    },
    "Could not load saved addresses."
  );
}

export async function createAddress(payload: CreateAddressPayload) {
  const token = getStoredAuthToken();

  if (!token) {
    throw new Error("Please login before saving an address.");
  }

  const response = await fetch(`${API_BASE_URL}/auth/addresses/`, {
    method: "POST",
    headers: buildHeaders(token),
    body: JSON.stringify(payload)
  });

  if (!response.ok) {
    await handleAuthFailure(response);
    throw new Error(await parseErrorMessage(response, "Could not save address."));
  }

  return (await response.json()) as ApiAddress;
}

export async function updateAddress(addressId: number, payload: UpdateAddressPayload) {
  const token = getStoredAuthToken();

  if (!token) {
    throw new Error("Please login before updating addresses.");
  }

  const response = await fetch(`${API_BASE_URL}/auth/addresses/${addressId}/`, {
    method: "PATCH",
    headers: buildHeaders(token),
    body: JSON.stringify(payload)
  });

  if (!response.ok) {
    await handleAuthFailure(response);
    throw new Error(await parseErrorMessage(response, "Could not update address."));
  }

  return (await response.json()) as ApiAddress;
}

export async function deleteAddress(addressId: number) {
  const token = getStoredAuthToken();

  if (!token) {
    throw new Error("Please login before removing addresses.");
  }

  const response = await fetch(`${API_BASE_URL}/auth/addresses/${addressId}/`, {
    method: "DELETE",
    headers: buildHeaders(token)
  });

  if (!response.ok) {
    await handleAuthFailure(response);
    throw new Error(await parseErrorMessage(response, "Could not remove address."));
  }
}

export async function fetchPaymentMethods() {
  const token = getStoredAuthToken();

  if (!token) {
    throw new Error("Please login before loading payment methods.");
  }

  const response = await fetch(`${API_BASE_URL}/auth/payment-methods/`, {
    method: "GET",
    headers: buildHeaders(token),
    cache: "no-store"
  });

  if (!response.ok) {
    throw new Error(await parseErrorMessage(response, "Could not load payment methods."));
  }

  return (await response.json()) as ApiSavedPaymentMethod[];
}

export async function createPaymentMethod(payload: CreatePaymentMethodPayload) {
  const token = getStoredAuthToken();

  if (!token) {
    throw new Error("Please login before saving a payment method.");
  }

  const response = await fetch(`${API_BASE_URL}/auth/payment-methods/`, {
    method: "POST",
    headers: buildHeaders(token),
    body: JSON.stringify(payload)
  });

  if (!response.ok) {
    await handleAuthFailure(response);
    throw new Error(await parseErrorMessage(response, "Could not save payment method."));
  }

  return (await response.json()) as ApiSavedPaymentMethod;
}

export async function updatePaymentMethod(paymentMethodId: number, payload: UpdatePaymentMethodPayload) {
  const token = getStoredAuthToken();

  if (!token) {
    throw new Error("Please login before updating payment methods.");
  }

  const response = await fetch(`${API_BASE_URL}/auth/payment-methods/${paymentMethodId}/`, {
    method: "PATCH",
    headers: buildHeaders(token),
    body: JSON.stringify(payload)
  });

  if (!response.ok) {
    await handleAuthFailure(response);
    throw new Error(await parseErrorMessage(response, "Could not update payment method."));
  }

  return (await response.json()) as ApiSavedPaymentMethod;
}

export async function deletePaymentMethod(paymentMethodId: number) {
  const token = getStoredAuthToken();

  if (!token) {
    throw new Error("Please login before removing payment methods.");
  }

  const response = await fetch(`${API_BASE_URL}/auth/payment-methods/${paymentMethodId}/`, {
    method: "DELETE",
    headers: buildHeaders(token)
  });

  if (!response.ok) {
    await handleAuthFailure(response);
    throw new Error(await parseErrorMessage(response, "Could not remove payment method."));
  }
}

export async function createPrescription(payload: CreatePrescriptionPayload, onProgress?: (percentage: number) => void) {
  const token = getStoredAuthToken();

  if (!token) {
    throw new Error("Please complete login with OTP before uploading a prescription.");
  }

  const formData = new FormData();
  formData.append("patient_name", payload.patient_name);
  formData.append("doctor_name", payload.doctor_name);
  formData.append("notes", payload.notes);
  formData.append("file", payload.file);

  return await new Promise<ApiPrescriptionRecord>((resolve, reject) => {
    const request = new XMLHttpRequest();
    request.open("POST", `${API_BASE_URL}/prescriptions/`);
    request.setRequestHeader("Authorization", `Token ${token}`);
    request.responseType = "json";
    request.upload.onprogress = (event) => {
      if (event.lengthComputable && onProgress) {
        onProgress(Math.round((event.loaded / event.total) * 100));
      }
    };
    request.onload = () => {
      if (request.status >= 200 && request.status < 300) {
        resolve(request.response as ApiPrescriptionRecord);
        return;
      }
      const detail =
        (request.response && typeof request.response === "object" && "detail" in request.response && typeof request.response.detail === "string"
          ? request.response.detail
          : "Prescription upload failed.");
      reject(new Error(detail));
    };
    request.onerror = () => reject(new Error("Prescription upload failed."));
    request.send(formData);
  });
}

export async function fetchMyPrescriptions() {
  const token = getStoredAuthToken();

  if (!token) {
    throw new Error("Please login before viewing prescription uploads.");
  }

  const response = await fetch(buildCatalogUrl("/prescriptions/"), {
    method: "GET",
    headers: buildHeaders(token),
    cache: "no-store"
  });

  if (!response.ok) {
    throw new Error(await parseErrorMessage(response, "Could not load prescription uploads."));
  }

  return (await response.json()) as ApiPrescriptionRecord[];
}

export async function fetchMyPrescription(referenceCode: string) {
  const token = getStoredAuthToken();

  if (!token) {
    throw new Error("Please login before viewing prescription details.");
  }

  const response = await fetch(buildCatalogUrl(`/prescriptions/${referenceCode}/`), {
    method: "GET",
    headers: buildHeaders(token),
    cache: "no-store"
  });

  if (!response.ok) {
    throw new Error(await parseErrorMessage(response, "Could not load prescription detail."));
  }

  return (await response.json()) as ApiPrescriptionDetail;
}

export async function fetchPharmacistQueue(statusFilter = "") {
  const token = getStoredAuthToken();

  if (!token) {
    throw new Error("Please login before viewing the pharmacist queue.");
  }

  const searchParams = new URLSearchParams();
  if (statusFilter) {
    searchParams.set("status", statusFilter);
  }

  const response = await fetch(buildCatalogUrl("/prescriptions/pharmacist/queue/", searchParams), {
    method: "GET",
    headers: buildHeaders(token),
    cache: "no-store"
  });

  if (!response.ok) {
    throw new Error(await parseErrorMessage(response, "Could not load pharmacist queue."));
  }

  return (await response.json()) as ApiPrescriptionRecord[];
}

export async function fetchPharmacistPrescription(referenceCode: string) {
  const token = getStoredAuthToken();

  if (!token) {
    throw new Error("Please login before viewing prescription details.");
  }

  const response = await fetch(buildCatalogUrl(`/prescriptions/pharmacist/queue/${referenceCode}/`), {
    method: "GET",
    headers: buildHeaders(token),
    cache: "no-store"
  });

  if (response.status === 404) {
    return null;
  }

  if (!response.ok) {
    throw new Error(await parseErrorMessage(response, "Could not load prescription detail."));
  }

  return (await response.json()) as ApiPrescriptionDetail;
}

export async function reviewPrescription(referenceCode: string, payload: ReviewPrescriptionPayload) {
  const token = getStoredAuthToken();

  if (!token) {
    throw new Error("Please login before reviewing prescriptions.");
  }

  const response = await fetch(buildCatalogUrl(`/prescriptions/pharmacist/queue/${referenceCode}/review/`), {
    method: "POST",
    headers: buildHeaders(token),
    body: JSON.stringify(payload)
  });

  if (!response.ok) {
    throw new Error(await parseErrorMessage(response, "Could not submit prescription review."));
  }

  return (await response.json()) as ApiPrescriptionDetail;
}

function buildCatalogUrl(path: string, searchParams?: URLSearchParams) {
  return `${API_BASE_URL}${path}${searchParams && searchParams.toString() ? `?${searchParams.toString()}` : ""}`;
}

export async function fetchCatalogProducts(options: FetchCatalogProductsOptions = {}) {
  const searchParams = new URLSearchParams();

  if (options.category) {
    searchParams.set("category", options.category);
  }
  if (options.brand) {
    searchParams.set("brand", options.brand);
  }
  if (options.q) {
    searchParams.set("q", options.q);
  }
  if (typeof options.prescriptionRequired === "boolean") {
    searchParams.set("prescription_required", String(options.prescriptionRequired));
  }

  return await readJsonWithRetry<ApiCatalogProductSummary[]>(
    buildCatalogUrl("/catalog/products/", searchParams),
    {
      method: "GET",
      headers: buildHeaders(),
      cache: "no-store"
    },
    "Could not load products."
  );
}

export async function fetchCatalogCategories() {
  return await readJsonWithRetry<ApiCatalogCategory[]>(
    buildCatalogUrl("/catalog/categories/"),
    {
      method: "GET",
      headers: buildHeaders(),
      cache: "no-store"
    },
    "Could not load categories."
  );
}

export async function fetchCatalogBrands() {
  const response = await fetch(buildCatalogUrl("/catalog/brands/"), {
    method: "GET",
    headers: buildHeaders(),
    cache: "no-store"
  });

  if (!response.ok) {
    throw new Error(await parseErrorMessage(response, "Could not load brands."));
  }

  return (await response.json()) as ApiCatalogBrand[];
}

export async function fetchCatalogProductBySlug(slug: string) {
  const response = await fetch(buildCatalogUrl(`/catalog/products/${slug}/`), {
    method: "GET",
    headers: buildHeaders(),
    cache: "no-store"
  });

  if (response.status === 404) {
    return null;
  }

  if (!response.ok) {
    throw new Error(await parseErrorMessage(response, "Could not load product details."));
  }

  return (await response.json()) as ApiCatalogProductDetail;
}

export async function fetchCart() {
  const token = getStoredAuthToken();

  if (!token) {
    throw new Error("Please login before loading the cart.");
  }

  const response = await fetch(buildCatalogUrl("/cart/"), {
    method: "GET",
    headers: buildHeaders(token),
    cache: "no-store"
  });

  if (!response.ok) {
    throw new Error(await parseErrorMessage(response, "Could not load cart."));
  }

  return (await response.json()) as ApiCart;
}

export async function replaceCart(payload: ReplaceCartPayload) {
  const token = getStoredAuthToken();

  if (!token) {
    throw new Error("Please login before syncing the cart.");
  }

  const response = await fetch(buildCatalogUrl("/cart/replace/"), {
    method: "PUT",
    headers: buildHeaders(token),
    body: JSON.stringify(payload)
  });

  if (!response.ok) {
    throw new Error(await parseErrorMessage(response, "Could not sync cart."));
  }

  return (await response.json()) as ApiCart;
}

export async function createOrderFromCart(payload: CheckoutPayload) {
  const token = getStoredAuthToken();

  if (!token) {
    throw new Error("Please login before placing an order.");
  }

  const response = await fetch(buildCatalogUrl("/orders/checkout/"), {
    method: "POST",
    headers: buildHeaders(token),
    body: JSON.stringify(payload)
  });

  if (!response.ok) {
    throw new Error(await parseErrorMessage(response, "Could not place order."));
  }

  return (await response.json()) as ApiOrder;
}

export async function fetchOrders() {
  const token = getStoredAuthToken();

  if (!token) {
    throw new Error("Please login before viewing orders.");
  }

  const response = await fetch(buildCatalogUrl("/orders/"), {
    method: "GET",
    headers: buildHeaders(token),
    cache: "no-store"
  });

  if (!response.ok) {
    throw new Error(await parseErrorMessage(response, "Could not load orders."));
  }

  return (await response.json()) as ApiOrder[];
}

export async function fetchOrderById(orderId: string) {
  const token = getStoredAuthToken();

  if (!token) {
    throw new Error("Please login before viewing order details.");
  }

  const response = await fetch(buildCatalogUrl(`/orders/${orderId}/`), {
    method: "GET",
    headers: buildHeaders(token),
    cache: "no-store"
  });

  if (response.status === 404) {
    return null;
  }

  if (!response.ok) {
    throw new Error(await parseErrorMessage(response, "Could not load order details."));
  }

  return (await response.json()) as ApiOrder;
}

export async function cancelOrder(orderId: string) {
  const token = getStoredAuthToken();

  if (!token) {
    throw new Error("Please login before cancelling orders.");
  }

  const response = await fetch(buildCatalogUrl(`/orders/${orderId}/cancel/`), {
    method: "POST",
    headers: buildHeaders(token)
  });

  if (!response.ok) {
    throw new Error(await parseErrorMessage(response, "Could not cancel the order."));
  }

  return (await response.json()) as ApiOrder;
}

export async function createOrderPaymentSession(orderId: string) {
  const token = getStoredAuthToken();

  if (!token) {
    throw new Error("Please login before starting payment.");
  }

  const response = await fetch(buildCatalogUrl(`/orders/${orderId}/payment/session/`), {
    method: "POST",
    headers: buildHeaders(token)
  });

  if (!response.ok) {
    throw new Error(await parseErrorMessage(response, "Could not start payment session."));
  }

  return (await response.json()) as ApiPaymentSession;
}

export async function retryOrderPayment(orderId: string) {
  const token = getStoredAuthToken();

  if (!token) {
    throw new Error("Please login before retrying payment.");
  }

  const response = await fetch(buildCatalogUrl(`/orders/${orderId}/payment/retry/`), {
    method: "POST",
    headers: buildHeaders(token)
  });

  if (!response.ok) {
    throw new Error(await parseErrorMessage(response, "Could not start payment retry."));
  }

  return (await response.json()) as ApiPaymentSession;
}

export async function confirmOrderPayment(orderId: string) {
  const token = getStoredAuthToken();

  if (!token) {
    throw new Error("Please login before confirming payment.");
  }

  const response = await fetch(buildCatalogUrl(`/orders/${orderId}/payment/confirm/`), {
    method: "POST",
    headers: buildHeaders(token)
  });

  if (!response.ok) {
    throw new Error(await parseErrorMessage(response, "Could not confirm payment."));
  }

  return (await response.json()) as ApiOrder;
}

export async function verifyOrderPayment(orderId: string, payload: VerifyOrderPaymentPayload) {
  const token = getStoredAuthToken();

  if (!token) {
    throw new Error("Please login before verifying payment.");
  }

  const response = await fetch(buildCatalogUrl(`/orders/${orderId}/payment/verify/`), {
    method: "POST",
    headers: buildHeaders(token),
    body: JSON.stringify(payload)
  });

  if (!response.ok) {
    throw new Error(await parseErrorMessage(response, "Could not verify payment."));
  }

  return (await response.json()) as ApiOrder;
}

export async function requestOrderRefund(orderId: string, reason: string) {
  const token = getStoredAuthToken();

  if (!token) {
    throw new Error("Please login before requesting a refund.");
  }

  const response = await fetch(buildCatalogUrl(`/orders/${orderId}/refund/`), {
    method: "POST",
    headers: buildHeaders(token),
    body: JSON.stringify({ reason })
  });

  if (!response.ok) {
    throw new Error(await parseErrorMessage(response, "Could not request a refund."));
  }

  return (await response.json()) as ApiOrder;
}

export async function downloadOrderInvoice(orderId: string) {
  const token = getStoredAuthToken();

  if (!token) {
    throw new Error("Please login before downloading invoices.");
  }

  const response = await fetch(buildCatalogUrl(`/orders/${orderId}/invoice/`), {
    method: "GET",
    headers: buildHeaders(token),
    cache: "no-store"
  });

  if (!response.ok) {
    throw new Error(await parseErrorMessage(response, "Could not download the invoice."));
  }

  return await response.blob();
}

export async function fetchAdminSummary() {
  const token = getStoredAuthToken();

  if (!token) {
    throw new Error("Please login before viewing admin metrics.");
  }

  const response = await fetch(buildCatalogUrl("/orders/admin-summary/"), {
    method: "GET",
    headers: buildHeaders(token),
    cache: "no-store"
  });

  if (!response.ok) {
    throw new Error(await parseErrorMessage(response, "Could not load admin summary."));
  }

  return (await response.json()) as ApiAdminSummary;
}

export async function fetchAdminProducts(query = "") {
  const token = getStoredAuthToken();

  if (!token) {
    throw new Error("Please login before viewing admin products.");
  }

  const searchParams = new URLSearchParams();
  if (query) {
    searchParams.set("q", query);
  }

  const response = await fetch(buildCatalogUrl("/catalog/admin/products/", searchParams), {
    method: "GET",
    headers: buildHeaders(token),
    cache: "no-store"
  });

  if (!response.ok) {
    throw new Error(await parseErrorMessage(response, "Could not load admin products."));
  }

  return (await response.json()) as ApiAdminProduct[];
}

export async function fetchAdminOrders(status = "", fulfillmentStatus = "") {
  const token = getStoredAuthToken();

  if (!token) {
    throw new Error("Please login before viewing admin orders.");
  }

  const searchParams = new URLSearchParams();
  if (status) {
    searchParams.set("status", status);
  }
  if (fulfillmentStatus) {
    searchParams.set("fulfillment_status", fulfillmentStatus);
  }

  const response = await fetch(buildCatalogUrl("/orders/admin-orders/", searchParams), {
    method: "GET",
    headers: buildHeaders(token),
    cache: "no-store"
  });

  if (!response.ok) {
    throw new Error(await parseErrorMessage(response, "Could not load admin orders."));
  }

  return (await response.json()) as ApiOrder[];
}

export async function fetchAdminOrderById(orderId: string) {
  const token = getStoredAuthToken();

  if (!token) {
    throw new Error("Please login before viewing admin order details.");
  }

  const response = await fetch(buildCatalogUrl(`/orders/admin-orders/${orderId}/`), {
    method: "GET",
    headers: buildHeaders(token),
    cache: "no-store"
  });

  if (response.status === 404) {
    return null;
  }

  if (!response.ok) {
    throw new Error(await parseErrorMessage(response, "Could not load admin order detail."));
  }

  return (await response.json()) as ApiOrder;
}

export async function fetchAdminPayments(status = "") {
  const token = getStoredAuthToken();

  if (!token) {
    throw new Error("Please login before viewing admin payments.");
  }

  const searchParams = new URLSearchParams();
  if (status) {
    searchParams.set("status", status);
  }

  const response = await fetch(buildCatalogUrl("/orders/admin-payments/", searchParams), {
    method: "GET",
    headers: buildHeaders(token),
    cache: "no-store"
  });

  if (!response.ok) {
    throw new Error(await parseErrorMessage(response, "Could not load payment attempts."));
  }

  return (await response.json()) as ApiAdminPaymentAttempt[];
}

export async function fetchAdminReconciliation() {
  const token = getStoredAuthToken();

  if (!token) {
    throw new Error("Please login before viewing reconciliation.");
  }

  const response = await fetch(buildCatalogUrl("/orders/admin-reconciliation/"), {
    method: "GET",
    headers: buildHeaders(token),
    cache: "no-store"
  });

  if (!response.ok) {
    throw new Error(await parseErrorMessage(response, "Could not load reconciliation summary."));
  }

  return (await response.json()) as ApiReconciliationSummary;
}

export async function fetchAdminReconciliationWithFilters(filters: {
  provider?: string;
  from?: string;
  to?: string;
}) {
  const token = getStoredAuthToken();

  if (!token) {
    throw new Error("Please login before viewing reconciliation.");
  }

  const searchParams = new URLSearchParams();
  if (filters.provider) {
    searchParams.set("provider", filters.provider);
  }
  if (filters.from) {
    searchParams.set("from", filters.from);
  }
  if (filters.to) {
    searchParams.set("to", filters.to);
  }

  const response = await fetch(buildCatalogUrl("/orders/admin-reconciliation/", searchParams), {
    method: "GET",
    headers: buildHeaders(token),
    cache: "no-store"
  });

  if (!response.ok) {
    throw new Error(await parseErrorMessage(response, "Could not load reconciliation summary."));
  }

  return (await response.json()) as ApiReconciliationSummary;
}

export async function createAdminReconciliationSnapshot(notes = "") {
  const token = getStoredAuthToken();

  if (!token) {
    throw new Error("Please login before capturing reconciliation.");
  }

  const response = await fetch(buildCatalogUrl("/orders/admin-reconciliation/"), {
    method: "POST",
    headers: buildHeaders(token),
    body: JSON.stringify({ notes })
  });

  if (!response.ok) {
    throw new Error(await parseErrorMessage(response, "Could not capture reconciliation snapshot."));
  }

  return (await response.json()) as ApiReconciliationSnapshot;
}

export async function downloadAdminReconciliationCsv() {
  const token = getStoredAuthToken();

  if (!token) {
    throw new Error("Please login before exporting reconciliation.");
  }

  const response = await fetch(buildCatalogUrl("/orders/admin-reconciliation/export/"), {
    method: "GET",
    headers: buildHeaders(token),
    cache: "no-store"
  });

  if (!response.ok) {
    throw new Error(await parseErrorMessage(response, "Could not export reconciliation CSV."));
  }

  return await response.blob();
}

export async function downloadAdminReconciliationCsvWithFilters(filters: {
  provider?: string;
  from?: string;
  to?: string;
}) {
  const token = getStoredAuthToken();

  if (!token) {
    throw new Error("Please login before exporting reconciliation.");
  }

  const searchParams = new URLSearchParams();
  if (filters.provider) {
    searchParams.set("provider", filters.provider);
  }
  if (filters.from) {
    searchParams.set("from", filters.from);
  }
  if (filters.to) {
    searchParams.set("to", filters.to);
  }

  const response = await fetch(buildCatalogUrl("/orders/admin-reconciliation/export/", searchParams), {
    method: "GET",
    headers: buildHeaders(token),
    cache: "no-store"
  });

  if (!response.ok) {
    throw new Error(await parseErrorMessage(response, "Could not export reconciliation CSV."));
  }

  return await response.blob();
}

export async function fetchAdminSettlementBatches(filters: {
  provider?: string;
  from?: string;
  to?: string;
} = {}) {
  const token = getStoredAuthToken();

  if (!token) {
    throw new Error("Please login before viewing settlements.");
  }

  const searchParams = new URLSearchParams();
  if (filters.provider) {
    searchParams.set("provider", filters.provider);
  }
  if (filters.from) {
    searchParams.set("from", filters.from);
  }
  if (filters.to) {
    searchParams.set("to", filters.to);
  }

  const response = await fetch(buildCatalogUrl("/orders/admin-settlements/", searchParams), {
    method: "GET",
    headers: buildHeaders(token),
    cache: "no-store"
  });

  if (!response.ok) {
    throw new Error(await parseErrorMessage(response, "Could not load settlement batches."));
  }

  return (await response.json()) as ApiSettlementBatch[];
}

export async function createAdminSettlementBatch(payload: CreateSettlementBatchPayload) {
  const token = getStoredAuthToken();

  if (!token) {
    throw new Error("Please login before creating settlement batches.");
  }

  const response = await fetch(buildCatalogUrl("/orders/admin-settlements/"), {
    method: "POST",
    headers: buildHeaders(token),
    body: JSON.stringify(payload)
  });

  if (!response.ok) {
    throw new Error(await parseErrorMessage(response, "Could not create settlement batch."));
  }

  return (await response.json()) as ApiSettlementBatch;
}

export async function downloadAdminSettlementBatchCsv(batchId: number) {
  const token = getStoredAuthToken();

  if (!token) {
    throw new Error("Please login before exporting settlement batches.");
  }

  const response = await fetch(buildCatalogUrl(`/orders/admin-settlements/${batchId}/export/`), {
    method: "GET",
    headers: buildHeaders(token),
    cache: "no-store"
  });

  if (!response.ok) {
    throw new Error(await parseErrorMessage(response, "Could not export settlement CSV."));
  }

  return await response.blob();
}

export async function fetchAdminSettlementBatchById(batchId: number) {
  const token = getStoredAuthToken();

  if (!token) {
    throw new Error("Please login before viewing settlement detail.");
  }

  const response = await fetch(buildCatalogUrl(`/orders/admin-settlements/${batchId}/`), {
    method: "GET",
    headers: buildHeaders(token),
    cache: "no-store"
  });

  if (!response.ok) {
    throw new Error(await parseErrorMessage(response, "Could not load settlement detail."));
  }

  return (await response.json()) as ApiSettlementBatch;
}

export async function updateAdminSettlementBatch(batchId: number, payload: UpdateSettlementBatchPayload) {
  const token = getStoredAuthToken();

  if (!token) {
    throw new Error("Please login before updating settlement detail.");
  }

  const response = await fetch(buildCatalogUrl(`/orders/admin-settlements/${batchId}/update/`), {
    method: "POST",
    headers: buildHeaders(token),
    body: JSON.stringify(payload)
  });

  if (!response.ok) {
    throw new Error(await parseErrorMessage(response, "Could not update settlement batch."));
  }

  return (await response.json()) as ApiSettlementBatch;
}

export async function updateAdminOrder(
  orderId: string,
  payload: Partial<Pick<ApiOrder, "status" | "payment_status" | "fulfillment_status" | "tracking_reference" | "notes">>
) {
  const token = getStoredAuthToken();

  if (!token) {
    throw new Error("Please login before updating admin orders.");
  }

  const response = await fetch(buildCatalogUrl(`/orders/admin-orders/${orderId}/`), {
    method: "PATCH",
    headers: buildHeaders(token),
    body: JSON.stringify(payload)
  });

  if (!response.ok) {
    throw new Error(await parseErrorMessage(response, "Could not update the order."));
  }

  return (await response.json()) as ApiOrder;
}

export async function decideAdminRefund(orderId: string, payload: RefundDecisionPayload) {
  const token = getStoredAuthToken();

  if (!token) {
    throw new Error("Please login before updating refunds.");
  }

  const response = await fetch(buildCatalogUrl(`/orders/admin-orders/${orderId}/refund/`), {
    method: "POST",
    headers: buildHeaders(token),
    body: JSON.stringify(payload)
  });

  if (!response.ok) {
    throw new Error(await parseErrorMessage(response, "Could not update the refund request."));
  }

  return (await response.json()) as ApiOrder;
}

export async function createAdminProduct(payload: AdminProductPayload) {
  const token = getStoredAuthToken();

  if (!token) {
    throw new Error("Please login before creating products.");
  }

  const response = await fetch(buildCatalogUrl("/catalog/admin/products/"), {
    method: "POST",
    headers: buildHeaders(token),
    body: JSON.stringify(payload)
  });

  if (!response.ok) {
    throw new Error(await parseErrorMessage(response, "Could not create product."));
  }

  return (await response.json()) as ApiAdminProduct;
}

export async function updateAdminProduct(productId: number, payload: Partial<AdminProductPayload>) {
  const token = getStoredAuthToken();

  if (!token) {
    throw new Error("Please login before updating products.");
  }

  const response = await fetch(buildCatalogUrl(`/catalog/admin/products/${productId}/`), {
    method: "PATCH",
    headers: buildHeaders(token),
    body: JSON.stringify(payload)
  });

  if (!response.ok) {
    throw new Error(await parseErrorMessage(response, "Could not update product."));
  }

  return (await response.json()) as ApiAdminProduct;
}

export async function fetchAdminInventory(stockStatus = "") {
  const token = getStoredAuthToken();

  if (!token) {
    throw new Error("Please login before viewing inventory.");
  }

  const searchParams = new URLSearchParams();
  if (stockStatus) {
    searchParams.set("stock_status", stockStatus);
  }

  const response = await fetch(buildCatalogUrl("/inventory/admin/items/", searchParams), {
    method: "GET",
    headers: buildHeaders(token),
    cache: "no-store"
  });

  if (!response.ok) {
    throw new Error(await parseErrorMessage(response, "Could not load inventory."));
  }

  return (await response.json()) as ApiInventoryItem[];
}

export async function fetchServiceability(pincode: string) {
  const searchParams = new URLSearchParams();
  if (pincode) {
    searchParams.set("pincode", pincode);
  }

  const response = await fetch(buildCatalogUrl("/delivery/serviceability/", searchParams), {
    method: "GET",
    headers: buildHeaders(),
    cache: "no-store"
  });

  if (!response.ok) {
    throw new Error(await parseErrorMessage(response, "Could not check serviceability."));
  }

  return (await response.json()) as ApiServiceability;
}

export async function fetchAdminShipments(status = "", readyOnly = false) {
  const token = getStoredAuthToken();

  if (!token) {
    throw new Error("Please login before viewing delivery shipments.");
  }

  const searchParams = new URLSearchParams();
  if (status) {
    searchParams.set("status", status);
  }
  if (readyOnly) {
    searchParams.set("ready", "true");
  }

  const response = await fetch(buildCatalogUrl("/delivery/admin/shipments/", searchParams), {
    method: "GET",
    headers: buildHeaders(token),
    cache: "no-store"
  });

  if (!response.ok) {
    throw new Error(await parseErrorMessage(response, "Could not load delivery shipments."));
  }

  return (await response.json()) as ApiDeliveryShipment[];
}

export async function updateAdminShipment(orderId: string, payload: UpdateDeliveryShipmentPayload) {
  const token = getStoredAuthToken();

  if (!token) {
    throw new Error("Please login before updating delivery shipments.");
  }

  const response = await fetch(buildCatalogUrl(`/delivery/admin/shipments/${orderId}/`), {
    method: "PATCH",
    headers: buildHeaders(token),
    body: JSON.stringify(payload)
  });

  if (!response.ok) {
    throw new Error(await parseErrorMessage(response, "Could not update delivery shipment."));
  }

  return (await response.json()) as ApiDeliveryShipment;
}

export async function updateInventoryItem(productId: number, payload: InventoryUpdatePayload) {
  const token = getStoredAuthToken();

  if (!token) {
    throw new Error("Please login before updating inventory.");
  }

  const response = await fetch(buildCatalogUrl(`/inventory/admin/items/${productId}/`), {
    method: "PATCH",
    headers: buildHeaders(token),
    body: JSON.stringify(payload)
  });

  if (!response.ok) {
    throw new Error(await parseErrorMessage(response, "Could not update inventory item."));
  }

  return (await response.json()) as ApiInventoryItem;
}

export async function logout() {
  const token = getStoredAuthToken();

  if (!token) {
    clearStoredAuth();
    return { status: "logged_out" };
  }

  const response = await fetch(`${API_BASE_URL}/auth/logout/`, {
    method: "POST",
    headers: buildHeaders(token)
  });

  clearStoredAuth();

  if (!response.ok) {
    throw new Error(await parseErrorMessage(response, "Could not end your session."));
  }

  return (await response.json()) as { status: string };
}
