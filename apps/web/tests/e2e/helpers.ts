import type { Page } from "@playwright/test";

const API_BASE = "http://localhost:8000/api/v1";
const APP_ORIGIN = "http://127.0.0.1:3000";
const AUTH_TOKEN_STORAGE_KEY = "rakeshmed-auth-token";
const AUTH_USER_STORAGE_KEY = "rakeshmed-auth-user";
const AUTH_EXPIRES_AT_STORAGE_KEY = "rakeshmed-auth-expires-at";
const AUTH_STORAGE_EVENT = "rakeshmed-auth-storage-change";

function jsonHeaders() {
  return {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "GET,POST,PATCH,PUT,DELETE,OPTIONS",
    "Access-Control-Allow-Headers": "*",
    "Cache-Control": "no-store"
  };
}

async function fulfillJson(route: Parameters<Page["route"]>[1] extends (route: infer T, ...args: never[]) => unknown ? T : never, payload: unknown, status = 200) {
  if (route.request().method() === "OPTIONS") {
    await route.fulfill({
      status: 204,
      headers: jsonHeaders()
    });
    return;
  }

  await route.fulfill({
    status,
    headers: jsonHeaders(),
    json: payload
  });
}

type AuthRole =
  | "customer"
  | "admin"
  | "finance"
  | "pharmacist"
  | "catalog_manager"
  | "warehouse_operator"
  | "support_agent";

export function buildAuthStorageState(role: AuthRole) {
  return {
    cookies: [],
    origins: [
      {
        origin: APP_ORIGIN,
        localStorage: [
          {
            name: AUTH_TOKEN_STORAGE_KEY,
            value: "playwright-token"
          },
          {
            name: AUTH_USER_STORAGE_KEY,
            value: JSON.stringify({
              id: 1,
              phone_number: "7002579537",
              full_name: "Playwright User",
              role,
              is_phone_verified: true,
              session_expires_at: "2099-01-01T00:00:00Z"
            })
          },
          {
            name: AUTH_EXPIRES_AT_STORAGE_KEY,
            value: "2099-01-01T00:00:00Z"
          }
        ]
      }
    ]
  };
}

export async function mockCatalog(page: Page) {
  await page.route("**/catalog/products/**", async (route) => {
    const url = new URL(route.request().url());
    const query = (url.searchParams.get("q") ?? "").toLowerCase();

    if (query === "zzzzzz" || query === "definitely-missing-product") {
      await fulfillJson(route, []);
      return;
    }

    await fulfillJson(route, [
        {
          id: 1,
          name: "Paracetamol 650 Tablet",
          slug: "paracetamol-650-tablet",
          sku: "PCM-650",
          category: {
            id: 10,
            name: "Pain Relief",
            slug: "pain-relief",
            description: "",
            parent: null,
            sort_order: 1
          },
          brand: {
            id: 20,
            name: "TrueCare",
            slug: "truecare",
            description: ""
          },
          composition: "Paracetamol",
          dosage_form: "Tablet",
          strength: "650 mg",
          pack_size: "15 tablets",
          manufacturer: "TrueCare Labs",
          mrp: "120.00",
          sale_price: "96.00",
          requires_prescription: false,
          is_otc: true,
          stock_status: "in_stock"
        }
      ]);
  });

  await page.route("**/catalog/categories/**", async (route) => {
    await fulfillJson(route, [
        {
          id: 1,
          name: "Health Conditions",
          slug: "health-conditions",
          description: "",
          parent: null,
          sort_order: 1
        },
        {
          id: 2,
          name: "Pain Relief",
          slug: "pain-relief",
          description: "",
          parent: 1,
          sort_order: 1
        }
      ]);
  });
}

export async function mockOtpAuth(page: Page) {
  await page.route(`${API_BASE}/auth/send-otp/`, async (route) => {
    await fulfillJson(route, {
        status: "sent",
        phone_number: "7002579537",
        purpose: "login",
        expires_at: "2099-01-01T00:00:00Z",
        otp_code: "123456"
    });
  });

  await page.route(`${API_BASE}/auth/verify-otp/`, async (route) => {
    await fulfillJson(route, {
        status: "verified",
        token: "playwright-token",
        expires_at: "2099-01-01T00:00:00Z",
        user: {
          id: 1,
          phone_number: "7002579537",
          full_name: "Playwright User",
          role: "customer",
          is_phone_verified: true,
          session_expires_at: "2099-01-01T00:00:00Z"
        }
    });
  });
}

export async function setAuthSession(page: Page, role: AuthRole) {
  const payload = {
    tokenKey: AUTH_TOKEN_STORAGE_KEY,
    userKey: AUTH_USER_STORAGE_KEY,
    expiryKey: AUTH_EXPIRES_AT_STORAGE_KEY,
    authEvent: AUTH_STORAGE_EVENT,
    roleValue: role
  };

  if (page.url() === "about:blank") {
    await page.addInitScript(
      ({ tokenKey, userKey, expiryKey, authEvent, roleValue }) => {
        window.localStorage.setItem(tokenKey, "playwright-token");
        window.localStorage.setItem(
          userKey,
          JSON.stringify({
            id: 1,
            phone_number: "7002579537",
            full_name: "Playwright User",
            role: roleValue,
            is_phone_verified: true,
            session_expires_at: "2099-01-01T00:00:00Z"
          })
        );
        window.localStorage.setItem(expiryKey, "2099-01-01T00:00:00Z");
        window.dispatchEvent(new Event(authEvent));
      },
      payload
    );
    return;
  }

  await page.evaluate(
    ({ tokenKey, userKey, expiryKey, authEvent, roleValue }) => {
      window.localStorage.setItem(tokenKey, "playwright-token");
      window.localStorage.setItem(
        userKey,
        JSON.stringify({
          id: 1,
          phone_number: "7002579537",
          full_name: "Playwright User",
          role: roleValue,
          is_phone_verified: true,
          session_expires_at: "2099-01-01T00:00:00Z"
        })
      );
      window.localStorage.setItem(expiryKey, "2099-01-01T00:00:00Z");
      window.dispatchEvent(new Event(authEvent));
    },
    payload
  );

  await page.reload();
}

export async function mockCustomerFlows(page: Page) {
  await page.route("**/cart/**", async (route) => {
    await fulfillJson(route, {
        items: [
          {
            slug: "paracetamol-650-tablet",
            name: "Paracetamol 650 Tablet",
            off: "20% OFF",
            mrp: "120.00",
            price: "96.00",
            meta: "TrueCare Labs | 15 tablets",
            rx: false,
            qty: 1
          }
        ],
        item_count: 1,
        requires_prescription_count: 0,
        subtotal: "120.00",
        discount: "24.00",
        delivery: "40.00",
        total: "136.00"
    });
  });

  await page.route(/\/api\/v1\/auth\/addresses\/?$/, async (route) => {
    await fulfillJson(route, [
        {
          id: 11,
          label: "Home",
          recipient: "Playwright User",
          line1: "Test Residency",
          city: "Mumbai",
          state: "Maharashtra",
          pincode: "400001",
          phone_number: "9999999999",
          is_default: true
        }
      ]);
  });

  await page.route("**/delivery/serviceability/**", async (route) => {
    await fulfillJson(route, {
        pincode: "400001",
        is_serviceable: true,
        cod_available: true,
        zone: {
          code: "MUM",
          name: "Mumbai Core",
          city: "Mumbai",
          state: "Maharashtra"
        },
        eta_label: "Tomorrow"
    });
  });

  await page.route("**/orders/checkout/", async (route) => {
    await fulfillJson(route, {
        order_number: "TC-PLAY-001",
        status: "placed",
        payment_method: "UPI",
        payment_status: "pending",
        inventory_status: "allocated",
        fulfillment_status: "queued",
        tracking_reference: "",
        address_label: "Home",
        recipient: "Playwright User",
        line1: "Test Residency",
        city: "Mumbai",
        pincode: "400001",
        upi_id: "playwright@upi",
        notes: "",
        subtotal: "96.00",
        discount: "24.00",
        delivery_fee: "40.00",
        total: "136.00",
        requires_prescription_count: 0,
        created_at: "2026-04-21T10:00:00Z",
        items: [
          {
            slug: "paracetamol-650-tablet",
            name: "Paracetamol 650 Tablet",
            off: "20% OFF",
            mrp: "120.00",
            price: "96.00",
            meta: "TrueCare Labs | 15 tablets",
            rx: false,
            qty: 1
          }
        ],
        payment_attempts: [],
        delivery_shipment: null,
        timeline: [],
        refund_requests: []
    });
  });
}

export async function mockPrescriptionAccount(page: Page) {
  await page.route(`${API_BASE}/prescriptions/`, async (route) => {
    await fulfillJson(route, [
      {
        reference_code: "RX-PLAY-001",
        patient_name: "Playwright User",
        doctor_name: "Dr Example",
        notes: "Use after food",
        status: "approved",
        review_priority: "normal",
        review_eta_hours: 2,
        uploaded_file_name: "rx.jpg",
        uploaded_file_type: "image/jpeg",
        uploaded_file_size_bytes: 145000,
        file_access_url: "https://files.example.test/rx.jpg",
        created_at: "2026-04-21T10:00:00Z"
      }
    ]);
  });

  await page.route(`${API_BASE}/prescriptions/RX-PLAY-001/`, async (route) => {
    await fulfillJson(route, {
      reference_code: "RX-PLAY-001",
      patient_name: "Playwright User",
      doctor_name: "Dr Example",
      notes: "Use after food",
      status: "approved",
      review_priority: "normal",
      review_eta_hours: 2,
      uploaded_file_name: "rx.jpg",
      uploaded_file_type: "image/jpeg",
      uploaded_file_size_bytes: 145000,
      file_access_url: "https://files.example.test/rx.jpg",
      created_at: "2026-04-21T10:00:00Z",
      reviewed_at: "2026-04-21T12:00:00Z",
      reviews: [
        {
          id: 1,
          decision: "approved",
          notes: "Approved for dispensing",
          substitute_guidance: "Same salt available if needed",
          reviewer_name: "Pharmacist Example",
          created_at: "2026-04-21T12:00:00Z"
        }
      ]
    });
  });
}

export async function mockPrescriptionUpload(page: Page) {
  await page.route(`${API_BASE}/prescriptions/`, async (route) => {
    await fulfillJson(route, {
      reference_code: "RX-UP-001",
      patient_name: "Playwright User",
      doctor_name: "Dr Example",
      notes: "Use after food",
      status: "pending_review",
      review_priority: "normal",
      review_eta_hours: 2,
      uploaded_file_name: "rx-upload.jpg",
      uploaded_file_type: "image/jpeg",
      uploaded_file_size_bytes: 145000,
      file_access_url: "https://files.example.test/rx-upload.jpg",
      created_at: "2026-04-21T10:00:00Z"
    });
  });
}

export async function mockAccountOrder(page: Page) {
  let paymentStatus = "pending";

  await page.route(`${API_BASE}/orders/TC-PLAY-001/payment/session/`, async (route) => {
    await route.fulfill({
      json: {
        order_number: "TC-PLAY-001",
        payment_method: "UPI",
        payment_status: paymentStatus,
        amount: "136.00",
        provider: "gateway",
        provider_key: "pk_test",
        payment_reference: "pay_playwright_001",
        checkout_url: "https://payments.example.test/checkout"
      }
    });
  });

  await page.route(`${API_BASE}/orders/TC-PLAY-001/payment/retry/`, async (route) => {
    await route.fulfill({
      json: {
        order_number: "TC-PLAY-001",
        payment_method: "UPI",
        payment_status: "pending",
        amount: "136.00",
        provider: "gateway",
        provider_key: "pk_test",
        payment_reference: "pay_playwright_002",
        checkout_url: "https://payments.example.test/retry"
      }
    });
  });

  await page.route(`${API_BASE}/orders/TC-PLAY-001/payment/confirm/`, async (route) => {
    paymentStatus = "paid";
    await route.fulfill({
      json: {
        order_number: "TC-PLAY-001",
        status: "confirmed",
        payment_method: "UPI",
        payment_status: "paid",
        inventory_status: "allocated",
        fulfillment_status: "queued",
        tracking_reference: "",
        address_label: "Home",
        recipient: "Playwright User",
        line1: "Test Residency",
        city: "Mumbai",
        pincode: "400001",
        upi_id: "playwright@upi",
        notes: "",
        subtotal: "96.00",
        discount: "24.00",
        delivery_fee: "40.00",
        total: "136.00",
        requires_prescription_count: 0,
        created_at: "2026-04-21T10:00:00Z",
        items: [
          {
            slug: "paracetamol-650-tablet",
            name: "Paracetamol 650 Tablet",
            off: "20% OFF",
            mrp: "120.00",
            price: "96.00",
            meta: "TrueCare Labs | 15 tablets",
            rx: false,
            qty: 1
          }
        ],
        payment_attempts: [
          {
            provider: "gateway",
            payment_reference: "pay_playwright_001",
            status: "captured",
            amount: "136.00",
            initiated_at: "2026-04-21T10:05:00Z",
            confirmed_at: "2026-04-21T10:06:00Z"
          }
        ],
        delivery_shipment: null,
        timeline: [],
        refund_requests: []
      }
    });
  });

  await page.route(`${API_BASE}/orders/TC-PLAY-001/`, async (route) => {
    await route.fulfill({
      json: {
        order_number: "TC-PLAY-001",
        status: paymentStatus === "paid" ? "confirmed" : "placed",
        payment_method: "UPI",
        payment_status: paymentStatus,
        inventory_status: "allocated",
        fulfillment_status: "queued",
        tracking_reference: "",
        address_label: "Home",
        recipient: "Playwright User",
        line1: "Test Residency",
        city: "Mumbai",
        pincode: "400001",
        upi_id: "playwright@upi",
        notes: "",
        subtotal: "96.00",
        discount: "24.00",
        delivery_fee: "40.00",
        total: "136.00",
        requires_prescription_count: 0,
        created_at: "2026-04-21T10:00:00Z",
        items: [
          {
            slug: "paracetamol-650-tablet",
            name: "Paracetamol 650 Tablet",
            off: "20% OFF",
            mrp: "120.00",
            price: "96.00",
            meta: "TrueCare Labs | 15 tablets",
            rx: false,
            qty: 1
          }
        ],
        payment_attempts: [
          {
            provider: "gateway",
            payment_reference: paymentStatus === "paid" ? "pay_playwright_001" : "pay_playwright_pending",
            status: paymentStatus === "paid" ? "captured" : "pending",
            amount: "136.00",
            initiated_at: "2026-04-21T10:05:00Z",
            confirmed_at: paymentStatus === "paid" ? "2026-04-21T10:06:00Z" : null
          }
        ],
        delivery_shipment: null,
        timeline: [],
        refund_requests: []
      }
    });
  });
}

export async function mockAdminInventory(page: Page) {
  await page.route(`${API_BASE}/inventory/admin/items/**`, async (route) => {
    if (route.request().method() === "PATCH") {
      await route.fulfill({
        json: {
          id: 31,
          name: "Paracetamol 650 Tablet",
          slug: "paracetamol-650-tablet",
          sku: "PCM-650",
          category: {
            id: 10,
            name: "Pain Relief",
            slug: "pain-relief",
            description: "",
            parent: null,
            sort_order: 1
          },
          brand: {
            id: 20,
            name: "TrueCare",
            slug: "truecare",
            description: ""
          },
          manufacturer: "TrueCare Labs",
          pack_size: "15 tablets",
          requires_prescription: false,
          is_active: true,
          stock_status: "in_stock",
          mrp: "120.00",
          sale_price: "96.00",
          total_on_hand: 100,
          total_reserved: 10,
          total_available: 90,
          low_stock_threshold: 12,
          location_items: [
            {
              id: 1,
              location: {
                id: 101,
                name: "Mumbai Main",
                code: "MUM-1",
                kind: "warehouse",
                is_active: true
              },
              quantity_on_hand: 100,
              reserved_quantity: 10,
              inbound_quantity: 0,
              available_quantity: 90,
              updated_at: "2026-04-21T10:00:00Z"
            }
          ],
          updated_at: "2026-04-21T10:00:00Z"
        }
      });
      return;
    }

    await route.fulfill({
      json: [
        {
          id: 31,
          name: "Paracetamol 650 Tablet",
          slug: "paracetamol-650-tablet",
          sku: "PCM-650",
          category: {
            id: 10,
            name: "Pain Relief",
            slug: "pain-relief",
            description: "",
            parent: null,
            sort_order: 1
          },
          brand: {
            id: 20,
            name: "TrueCare",
            slug: "truecare",
            description: ""
          },
          manufacturer: "TrueCare Labs",
          pack_size: "15 tablets",
          requires_prescription: false,
          is_active: true,
          stock_status: "in_stock",
          mrp: "120.00",
          sale_price: "96.00",
          total_on_hand: 100,
          total_reserved: 10,
          total_available: 90,
          low_stock_threshold: 10,
          location_items: [
            {
              id: 1,
              location: {
                id: 101,
                name: "Mumbai Main",
                code: "MUM-1",
                kind: "warehouse",
                is_active: true
              },
              quantity_on_hand: 100,
              reserved_quantity: 10,
              inbound_quantity: 0,
              available_quantity: 90,
              updated_at: "2026-04-21T10:00:00Z"
            }
          ],
          updated_at: "2026-04-21T10:00:00Z"
        }
      ]
    });
  });
}

export async function mockAdminOrders(page: Page) {
  await page.route(`${API_BASE}/orders/admin-orders/**`, async (route) => {
    const url = route.request().url();

    if (route.request().method() === "POST" || route.request().method() === "PATCH") {
      await route.fulfill({
        json: {
          order_number: "ORD-PLAY-001",
          status: "confirmed",
          payment_method: "UPI",
          payment_status: "paid",
          inventory_status: "allocated",
          fulfillment_status: "packed",
          tracking_reference: "TRACK-PLAY-001",
          address_label: "Home",
          recipient: "Playwright User",
          line1: "Test Residency",
          city: "Mumbai",
          pincode: "400001",
          upi_id: "playwright@upi",
          notes: "",
          subtotal: "96.00",
          discount: "24.00",
          delivery_fee: "40.00",
          total: "136.00",
          requires_prescription_count: 1,
          created_at: "2026-04-21T10:00:00Z",
          items: [],
          payment_attempts: [],
          timeline: [],
          refund_requests: []
        }
      });
      return;
    }

    if (url.includes("/ORD-PLAY-001/")) {
      await route.fulfill({
        json: {
          order_number: "ORD-PLAY-001",
          status: "placed",
          payment_method: "UPI",
          payment_status: "pending",
          inventory_status: "allocated",
          fulfillment_status: "queued",
          tracking_reference: "",
          address_label: "Home",
          recipient: "Playwright User",
          line1: "Test Residency",
          city: "Mumbai",
          pincode: "400001",
          upi_id: "playwright@upi",
          notes: "",
          subtotal: "96.00",
          discount: "24.00",
          delivery_fee: "40.00",
          total: "136.00",
          requires_prescription_count: 1,
          created_at: "2026-04-21T10:00:00Z",
          items: [
            {
              slug: "paracetamol-650-tablet",
              name: "Paracetamol 650 Tablet",
              off: "20% OFF",
              mrp: "120.00",
              price: "96.00",
              meta: "TrueCare Labs | 15 tablets",
              rx: false,
              qty: 1
            }
          ],
          payment_attempts: [
            {
              provider: "gateway",
              payment_reference: "pay_play_001",
              status: "pending",
              amount: "136.00",
              initiated_at: "2026-04-21T10:00:00Z",
              confirmed_at: null
            }
          ],
          delivery_shipment: null,
          timeline: [],
          refund_requests: [
            {
              id: 1,
              reason: "Duplicate payment",
              status: "requested",
              amount: "136.00",
              resolution_notes: "",
              requested_by_name: "Playwright User",
              created_at: "2026-04-21T10:10:00Z",
              updated_at: "2026-04-21T10:10:00Z",
              processed_at: null
            }
          ]
        }
      });
      return;
    }

    await route.fulfill({
      json: [
        {
          order_number: "ORD-PLAY-001",
          status: "placed",
          payment_method: "UPI",
          payment_status: "pending",
          inventory_status: "allocated",
          fulfillment_status: "queued",
          tracking_reference: "",
          address_label: "Home",
          recipient: "Playwright User",
          line1: "Test Residency",
          city: "Mumbai",
          pincode: "400001",
          upi_id: "playwright@upi",
          notes: "",
          subtotal: "96.00",
          discount: "24.00",
          delivery_fee: "40.00",
          total: "136.00",
          requires_prescription_count: 1,
          created_at: "2026-04-21T10:00:00Z",
          items: [],
          payment_attempts: [],
          timeline: [],
          refund_requests: []
        }
      ]
    });
  });
}

export async function mockFinanceFlows(page: Page) {
  await page.route(`${API_BASE}/orders/admin-reconciliation/**`, async (route) => {
    if (route.request().method() === "POST") {
      await route.fulfill({
        json: {
          provider: "gateway",
          captured_total: "136.00",
          refunded_total: "0.00",
          pending_refund_count: 1,
          duplicate_webhooks: 0,
          processed_webhooks: 2,
          unmatched_paid_orders: 0,
          created_by_label: "Playwright Finance",
          notes: "Checkpoint saved",
          created_at: "2026-04-21T12:00:00Z"
        }
      });
      return;
    }

    await route.fulfill({
      json: {
        provider: "gateway",
        attempt_count: 1,
        captured_total: "136.00",
        refunded_total: "0.00",
        pending_refund_count: 1,
        duplicate_webhooks: 0,
        processed_webhooks: 2,
        unmatched_paid_orders: 0,
        latest_webhooks: [
          {
            provider: "gateway",
            event_id: "evt_001",
            event_type: "payment.captured",
            payment_reference: "pay_play_001",
            order_number: "ORD-PLAY-001",
            was_duplicate: false,
            processed_at: "2026-04-21T10:06:00Z",
            created_at: "2026-04-21T10:06:00Z"
          }
        ],
        snapshot_history: [
          {
            provider: "gateway",
            captured_total: "136.00",
            refunded_total: "0.00",
            pending_refund_count: 1,
            duplicate_webhooks: 0,
            processed_webhooks: 2,
            unmatched_paid_orders: 0,
            created_by_label: "Playwright Finance",
            notes: "Checkpoint saved",
            created_at: "2026-04-21T12:00:00Z"
          }
        ],
        settlement_history: [
          {
            id: 71,
            provider: "gateway",
            batch_reference: "SET-PLAY-001",
            period_start: "2026-04-21T00:00:00Z",
            period_end: "2026-04-21T23:59:59Z",
            total_captured: "136.00",
            total_refunded: "0.00",
            total_net: "136.00",
            status: "draft",
            created_by_name: "Playwright Finance",
            notes: "Daily closeout",
            created_at: "2026-04-21T12:00:00Z",
            entries: []
          }
        ]
      }
    });
  });

  await page.route(`${API_BASE}/orders/admin-settlements/**`, async (route) => {
    const url = route.request().url();

    if (route.request().method() === "POST" && url.endsWith("/admin-settlements/")) {
      await route.fulfill({
        json: {
          id: 71,
          provider: "gateway",
          batch_reference: "SET-PLAY-001",
          period_start: "2026-04-21T00:00:00Z",
          period_end: "2026-04-21T23:59:59Z",
          total_captured: "136.00",
          total_refunded: "0.00",
          total_net: "136.00",
          status: "draft",
          created_by_name: "Playwright Finance",
          notes: "Daily closeout",
          created_at: "2026-04-21T12:00:00Z",
          entries: []
        }
      });
      return;
    }

    if (route.request().method() === "POST" && url.includes("/update/")) {
      await route.fulfill({
        json: {
          id: 71,
          provider: "gateway",
          batch_reference: "SET-PLAY-001",
          period_start: "2026-04-21T00:00:00Z",
          period_end: "2026-04-21T23:59:59Z",
          total_captured: "136.00",
          total_refunded: "0.00",
          total_net: "136.00",
          status: "closed",
          created_by_name: "Playwright Finance",
          notes: "Daily closeout",
          created_at: "2026-04-21T12:00:00Z",
          entries: [
            {
              order_number: "ORD-PLAY-001",
              payment_reference: "pay_play_001",
              gross_amount: "136.00",
              refund_amount: "0.00",
              net_amount: "136.00",
              settlement_status: "closed",
              refund_status: "none",
              created_at: "2026-04-21T12:00:00Z"
            }
          ]
        }
      });
      return;
    }

    if (url.includes("/71/")) {
      await route.fulfill({
        json: {
          id: 71,
          provider: "gateway",
          batch_reference: "SET-PLAY-001",
          period_start: "2026-04-21T00:00:00Z",
          period_end: "2026-04-21T23:59:59Z",
          total_captured: "136.00",
          total_refunded: "0.00",
          total_net: "136.00",
          status: "draft",
          created_by_name: "Playwright Finance",
          notes: "Daily closeout",
          created_at: "2026-04-21T12:00:00Z",
          entries: [
            {
              order_number: "ORD-PLAY-001",
              payment_reference: "pay_play_001",
              gross_amount: "136.00",
              refund_amount: "0.00",
              net_amount: "136.00",
              settlement_status: "draft",
              refund_status: "none",
              created_at: "2026-04-21T12:00:00Z"
            }
          ]
        }
      });
      return;
    }

    await route.fulfill({
      json: [
        {
          id: 71,
          provider: "gateway",
          batch_reference: "SET-PLAY-001",
          period_start: "2026-04-21T00:00:00Z",
          period_end: "2026-04-21T23:59:59Z",
          total_captured: "136.00",
          total_refunded: "0.00",
          total_net: "136.00",
          status: "draft",
          created_by_name: "Playwright Finance",
          notes: "Daily closeout",
          created_at: "2026-04-21T12:00:00Z",
          entries: []
        }
      ]
    });
  });
}

export async function mockPharmacistQueue(page: Page) {
  await page.route(`${API_BASE}/prescriptions/pharmacist/queue/**`, async (route) => {
    const url = route.request().url();

    if (url.includes("/RX-PLAY-001/review/")) {
      await route.fulfill({
        json: {
          reference_code: "RX-PLAY-001",
          patient_name: "Playwright User",
          doctor_name: "Dr Example",
          notes: "Daily medicine",
          status: "approved",
          review_priority: "normal",
          review_eta_hours: 2,
          uploaded_file_name: "rx.jpg",
          created_at: "2026-04-21T10:00:00Z",
          reviews: [
            {
              id: 1,
              decision: "approved",
              notes: "Approved for dispensing",
              substitute_guidance: "Same salt available",
              reviewer_name: "Pharmacist Example",
              created_at: "2026-04-21T12:00:00Z"
            }
          ]
        }
      });
      return;
    }

    if (url.includes("/RX-PLAY-001/")) {
      await route.fulfill({
        json: {
          reference_code: "RX-PLAY-001",
          patient_name: "Playwright User",
          doctor_name: "Dr Example",
          notes: "Daily medicine",
          status: "pending_review",
          review_priority: "normal",
          review_eta_hours: 2,
          uploaded_file_name: "rx.jpg",
          uploaded_file_type: "image/jpeg",
          uploaded_file_size_bytes: 145000,
          file_access_url: "https://files.example.test/rx.jpg",
          created_at: "2026-04-21T10:00:00Z",
          reviewed_at: null,
          clarification_message: "",
          reviews: []
        }
      });
      return;
    }

    await route.fulfill({
      json: [
        {
          reference_code: "RX-PLAY-001",
          patient_name: "Playwright User",
          doctor_name: "Dr Example",
          notes: "Daily medicine",
          status: "pending_review",
          review_priority: "normal",
          review_eta_hours: 2,
          uploaded_file_name: "rx.jpg",
          created_at: "2026-04-21T10:00:00Z"
        }
      ]
    });
  });
}
