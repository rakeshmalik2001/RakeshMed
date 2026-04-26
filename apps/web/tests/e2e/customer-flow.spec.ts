import { expect, test } from "@playwright/test";

import { mockAccountOrder, mockCatalog, mockCustomerFlows, setAuthSession } from "./helpers";

test.describe("customer flow", () => {
  test("shows real zero-state search results when live catalog returns none", async ({ page }) => {
    await mockCatalog(page);

    await page.goto("/search?q=zzzzzz");

    await expect(page.getByRole("heading", { name: "Not finding your medicine?" })).toBeVisible();
    await expect(page.getByText("Showing 0 results")).toBeVisible();
  });

  test.describe("authenticated customer flow", () => {
    test("supports checkout review and success with mocked live APIs", async ({ page }) => {
      await mockCatalog(page);
      await mockCustomerFlows(page);
      await setAuthSession(page, "customer");
      await page.addInitScript(() => {
        window.localStorage.setItem(
          "netmeds-cart",
          JSON.stringify([
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
          ])
        );
      });

      await page.goto("/checkout/address");
      await expect(page.getByText("Playwright User, Test Residency, Mumbai - 400001")).toBeVisible();

      await page.goto("/checkout/review");
      await expect(page.getByRole("heading", { name: "Review and place order" })).toBeVisible();
      await page.getByTestId("summary-cta-button").click();

      await expect(page).toHaveURL(/\/checkout\/success$/);
      await expect(page.getByText("UPI payment pending confirmation")).toBeVisible();
      await expect(page.getByTestId("checkout-success-payment-note")).toBeVisible();
      await expect(page.getByTestId("checkout-success-primary-action")).toHaveText("Open order details");
    });

    test("allows payment session refresh on account order detail", async ({ page }) => {
      await mockCustomerFlows(page);
      await mockAccountOrder(page);
      await setAuthSession(page, "customer");

      await page.goto("/account/orders/TC-PLAY-001");
      await expect(page.getByRole("button", { name: "Open payment page" })).toBeVisible();
      await expect(page.getByTestId("payment-status-summary")).toHaveText("UPI payment pending confirmation");
      await page.getByTestId("refresh-payment-status-button").click();
      await expect(page.getByText("Paid")).toBeVisible();
    });
  });
});
