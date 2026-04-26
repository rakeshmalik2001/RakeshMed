import { expect, test } from "@playwright/test";

import { mockAdminInventory, mockPharmacistQueue, setAuthSession } from "./helpers";

test.describe("ops flow", () => {
  test("renders admin inventory with production-style controls", async ({ page }) => {
    await setAuthSession(page, "admin");
    await mockAdminInventory(page);

    await page.goto("/admin/inventory");

    await expect(page.getByRole("heading", { name: "Inventory management" })).toBeVisible();
    await expect(page.getByRole("button", { name: "Raise low-stock threshold" })).toBeVisible();
    await expect(page.getByRole("button", { name: "Lower low-stock threshold" })).toBeVisible();
  });

  test("renders pharmacist prescription queue", async ({ page }) => {
    await setAuthSession(page, "pharmacist");
    await mockPharmacistQueue(page);

    await page.goto("/pharmacist/prescriptions");

    await expect(page.getByRole("heading", { name: "Pending review cases" })).toBeVisible();
    await expect(page.getByText("RX-PLAY-001")).toBeVisible();
  });
});
