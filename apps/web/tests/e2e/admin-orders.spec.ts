import { expect, test } from "@playwright/test";

import { mockAdminOrders, setAuthSession } from "./helpers";

test.describe("admin orders", () => {
  test("renders order operations and allows status action", async ({ page }) => {
    await setAuthSession(page, "admin");
    await mockAdminOrders(page);

    await page.goto("/admin/orders");
    await expect(page.getByRole("heading", { name: "Order operations" })).toBeVisible();
    await expect(page.getByText("ORD-PLAY-001")).toBeVisible();

    await page.getByRole("button", { name: "Mark paid" }).click();
    await expect(page.getByText("ORD-PLAY-001 updated.")).toBeVisible();
  });
});
