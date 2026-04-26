import { expect, test } from "@playwright/test";

import { mockAdminOrders, setAuthSession } from "./helpers";

test.describe("admin order detail", () => {
  test("renders detail view and supports admin actions", async ({ page }) => {
    await setAuthSession(page, "admin");
    await mockAdminOrders(page);

    await page.goto("/admin/orders/ORD-PLAY-001");
    await expect(page.getByRole("heading", { name: "Order ORD-PLAY-001" })).toBeVisible();
    await expect(page.getByText("Duplicate payment")).toBeVisible();

    await page.getByTestId("approve-refund-button").click();
    await expect(page.getByText("Refund status updated to approved.")).toBeVisible();
  });
});
